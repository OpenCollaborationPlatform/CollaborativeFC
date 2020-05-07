# ************************************************************************
# *   Copyright (c) Stefan Troeger (stefantroeger@gmx.net) 2019          *
# *                                                                      *
# *   This library is free software; you can redistribute it and/or      *
# *   modify it under the terms of the GNU Library General Public        *
# *   License as published by the Free Software Foundation; either       *
# *   version 2 of the License, or (at your option) any later version.   *
# *                                                                      *
# *   This library  is distributed in the hope that it will be useful,   *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of     *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the      *
# *   GNU Library General Public License for more details.               *
# *                                                                      *
# *   You should have received a copy of the GNU Library General Public  *
# *   License along with this library; see the file COPYING.LIB. If not, *
# *   write to the Free Software Foundation, Inc., 59 Temple Place,      *
# *   Suite 330, Boston, MA  02111-1307, USA                             *
# ************************************************************************

import asyncio, logging
import FreeCAD, os
from Documents.AsyncRunner import BatchedOrderedRunner, DocumentOrderedRunner
import Documents.Property as Property

class FreeCADOnlineObject():
    
    def __init__(self, name, onlinedoc, objGroup, parentOnlineObj = None):
        
        self.logger = logging.getLogger(objGroup[:-1] + " " + name)
                
        #check which type of runner to use 
        if os.getenv('FC_OCP_SYNC_MODE', "0") == "1":
            self.logger.info('Use non-default sync mode "Document-Sync"')
            self.sender     = DocumentOrderedRunner.getSenderRunner(onlinedoc.id)
            self.receiver   = DocumentOrderedRunner.getReceiverRunner(onlinedoc.id) 
        
        else:
            if parentOnlineObj is None:
                self.sender     = BatchedOrderedRunner() #used by the object to sync outgoing events
                self.receiver   = BatchedOrderedRunner() #used by the object to sync incoming events
            else:
                self.sender     = parentOnlineObj.sender
                self.receiver   = parentOnlineObj.receiver
                       
        self.docId           = onlinedoc.id
        self.data            = onlinedoc.data
        self.connection      = onlinedoc.connection
        self.name            = name
        self.objGroup        = objGroup 
        self.dynPropCache    = {}
        self.statusPropCache = {}
        self.propChangeCache = {}


    async def _asyncSetup(self, typeid, values, infos):
        #creates the object in the ocp node
    
        self.logger.debug(f"New object {self.name} ({typeid})")

        try:           
            uri = u"ocp.documents.edit.{0}".format(self.docId)
            await self.connection.session.call(uri + u".call.Document.{0}.NewObject".format(self.objGroup), self.name, typeid)
            
            #create all properties that need setup           
            await self._asyncCreateProperties(False, list(values.keys()), list(infos.values()))
        
        except Exception as e:
            self.logger.error("Setup error: {0}".format(e))
           
    
    async def _asyncCreateProperty(self, dyn, prop, info):
        #adds a property with its property info
        #could be added as normal or as dynamic property, dependend on dyn boolean
        
        try:            
            if dyn:
                self.logger.debug("Create dynamic property {0} ({1})".format(prop, info["typeid"]))
                fnc = "CreateDynamicProperty"
            else:
                self.logger.debug("Setup default property {0} ({1})".format(prop, info["typeid"]))
                fnc = "SetupProperty"
                
            uri = f"ocp.documents.edit.{self.docId}.call.Document.{self.objGroup}.{self.name}.Properties.{fnc}"
            await self.connection.session.call(uri, prop, info["typeid"], info["group"], info["docu"], info["status"])
        
        except Exception as e:
            self.logger.error("Create property {0} failed: {1}".format(prop, e))
    
    
    async def _asyncCreateProperties(self, dyn, props, infos):
        #adds a list of properties and a list with their property infos
        #could be added as normal or as dynamic property, dependend on dyn boolean
        
        try:            
            if dyn:
                self.logger.debug(f"Create dynamic properties {props}")
                fnc = "CreateDynamicProperties"
            else:
                self.logger.debug(f"Setup default properties {props}")
                fnc = "SetupProperties"
                
            uri = f"ocp.documents.edit.{self.docId}.call.Document.{self.objGroup}.{self.name}.Properties.{fnc}"
            await self.connection.session.call(uri, props, infos)
        
        except Exception as e:
            self.logger.error("Setup property {0} failed: {1}".format(prop, e))
    
    
    async def _asyncRemoveProperty(self, prop):
        try:        
            self.logger.debug(f"Remove property {prop}")
            uri = u"ocp.documents.edit.{0}.call.Document.{1}.{2}.Properties.RemoveDynamicProperty".format(self.docId, self.objGroup, self.name)
            await self.connection.session.call(uri, prop)
        
        except Exception as e:
            self.logger.error("Remove property {0} failed: {1}".format(prop, e))
        
    
    def _addDynamicPropertyCreation(self, prop, info):
        #caches the dynamic property creation to be executed as batch later
        #we can do this way of batching as created properties are not important order wise:
        #it is only important that they are created before use. As the first dynamic property creation 
        #is in oder, it is guranteed that all the following ones are earlier than needed, which is ok for this
        #type of operation
        
        #add property with info to the cache. 
        self.dynPropCache[prop] = info
        
        #if there was no entry before we start a cache processing. If there is something in the cache already
        #we are sure processing was already startet
        if len(self.dynPropCache) == 1:
            #add it to the dyn property creation cache. If it is the first entry we also start the
            self.sender.run(self.__asyncCreateDynamicPropertiesFromCache)
        
        
    async def __asyncCreateDynamicPropertiesFromCache(self):
        
        if len(self.dynPropCache) == 0:
            return
        try:
            props = self.dynPropCache.copy()
            self.dynPropCache.clear()
            
            keys   = list(props.keys())
            values = list(props.values())
            
            if len(props) == 1:
                await self._asyncCreateProperty(True, keys[0], values[0])
            
            else:
                await self._asyncCreateProperties(True, keys, values)

        except Exception as e:
            self.logger.error("Create dyn property from cache failed: {0}".format(e))
            
            
    def _addPropertyStatusChange(self, prop, status):
        
        #add property with status to the cache. 
        self.statusPropCache[prop] = status
        
        #if there was no entry before we start a cache processing. If there is something in the cache already
        #we are sure processing was already startet
        if len(self.statusPropCache) == 1:
            #add it to the dyn property creation cache. If it is the first entry we also start the 
            self.sender.run(self.__asyncStatusPropertiesFromCache)
        
        
    async def __asyncStatusPropertiesFromCache(self):
        
        if len(self.statusPropCache) == 0:
            return
        try:
            props = self.statusPropCache.copy()
            self.statusPropCache.clear()
            
            keys   = list(props.keys())
            values = list(props.values())
                        
            uri = f"ocp.documents.edit.{self.docId}.call.Document.{self.objGroup}.{self.name}.Properties."
            if len(props) == 1:
                self.logger.debug("Change property status {0}".format(keys[0]))
                uri += keys[0] + ".status"
                await self.connection.session.call(uri, values[0])
            
            else:
                self.logger.debug("Change batched property status: {0}".format(keys))
                uri += "SetStatus"
                await self.connection.session.call(uri, keys, values)
                
        except Exception as e:
            self.logger.error("Change property status from cache failed: {0}".format(e))
            
    
    def _addPropertyChange(self, prop, value):
        
        #add property with status to the cache. 
        self.propChangeCache[prop] = value
    
    
    async def __getCidForData(self, data):
               
        #store the data for the processing!
        datakey = self.data.addData(data)
        
        #get the cid!
        uri = f"ocp.documents.edit.{self.docId}.rawdata.CidByBinary"
        cid = await self.connection.session.call(uri, self.data.uri, datakey)
        return cid
        
    
    async def _asyncPropertyChangeFromCache(self):
                 
        if not self.propChangeCache:
            return

        props = self.propChangeCache.copy()
        self.propChangeCache.clear()
               
        #get the cids for the binary properties in parallel
        tasks = []
        for prop in props:
            if isinstance(props[prop], bytearray):  
                
                async def run(props, prop):
                    cid = await self.__getCidForData(props[prop])
                    props[prop] = cid
                    
                tasks.append(run(props, prop))

        if tasks:
            await asyncio.wait(tasks)
        
        #now batchwrite all properties in correct order
        if len(props) == 1:
            prop = list(props.keys())[0]
            await self._asyncWriteProperty(prop, props[prop])
        else:
            await self._asyncWriteProperties(list(props.keys()), list(props.values()))

        
    async def _asyncWriteProperty(self, prop, value):
        
        try:
            #value = Property.convertPropertyToWamp(self.obj, prop)
            uri = u"ocp.documents.edit.{0}".format(self.docId)
        
            if isinstance(value, bytearray):
                self.logger.debug("Write binary property {0}".format(prop))
                
                #store the data for the processing!
                datakey = self.data.addData(value)
                
                #than we need the id of the property where we add the data
                calluri = uri + u".call.Document.{0}.{1}.Properties.{2}.GetValue".format( self.objGroup, self.name, prop)
                propid = await self.connection.session.call(calluri)
                if propid == None or propid == "":
                    raise Exception("Property {0} does return valid binary data ID".format(prop))
                
                #call "SetBinary" for the property
                await self.connection.session.call(uri + u".rawdata.{0}.SetByBinary".format(propid), self.data.uri, datakey)
                
            else:
                #simple POD property: just add it!
                self.logger.debug(f"Write property {prop}")
                uri += u".call.Document.{0}.{1}.Properties.{2}.SetValue".format(self.objGroup, self.name, prop)
                await self.connection.session.call(uri, value)
        
        except Exception as e:
            self.logger.error("Writing property error ({1}, {2}): {0}".format(e, self.name, prop))
   
   
    async def _asyncWriteProperties(self, props, values):
        #note: does not work for binary properties!
        
        try:
            self.logger.debug("Write batch properties {0}".format(props))
            uri = u"ocp.documents.edit.{0}.call.Document.{1}.{2}.Properties.SetValues".format(self.docId, self.objGroup, self.name)
            await self.connection.session.call(uri, props, values)
            
        except Exception as e:
            self.logger.error("Writing property batch error: {0}".format(e))
     
     
    async def _asyncAddDynamcExtension(self, extension, props):
        
        try:           
            uri = f"ocp.documents.edit.{self.docId}"
            
            #add the extension must be done: a changed property could result in use of the extension
            self.logger.debug("Add extension {0}".format(extension))
            calluri = uri + u".call.Document.{0}.{1}.Extensions.Append".format(self.objGroup, self.name)
            await self.connection.session.call(calluri, extension)
            
            #the props can be created by a single call
            infos = []
            for prop in props:
                infos.append(Property.createPropertyInfo(self.obj, prop))
                
            await self._asyncCreateProperties(False, props, infos)            

                
        except Exception as e:
            self.logger.error("Adding extension failed: {0}".format(e))
     
     
    async def _asyncRemove(self):
        try:
            self.logger.debug("Remove")
            uri = u"ocp.documents.edit.{0}".format(self.docId)
            await self.connection.session.call(uri + u".call.Document.{0}.RemoveObject".format(self.objGroup), self.name)
        
        except Exception as e:
            self.logger.error("Removing error: {0}".format(e))
            
    
    async def waitTillCloseout(self, timeout = 10):
        #wait till all current async tasks are finished. Note that it also wait for task added during the wait period.
        #throws an error on timeout.
        
        await asyncio.wait([self.sender.waitTillCloseout(timeout), self.receiver.waitTillCloseout(timeout)])


class OnlineObject(FreeCADOnlineObject):
    
    def __init__(self, obj, onlinedoc):
        
        super().__init__(obj.Name, onlinedoc, "Objects")
        self.recomputeCache = {}
        self.odoc           = onlinedoc
        self.obj            = obj
        
        self.sender.registerBatchHandler("_addPropertyChange", self._asyncPropertyChangeFromCache)
        
        
    def setup(self):
        values = {}
        infos = {}
        for prop in self.obj.PropertiesList:
            values[prop] = Property.convertPropertyToWamp(self.obj, prop)
            infos[prop]  = Property.createPropertyInfo(self.obj, prop)
            
        self.sender.run(self._asyncSetup, self.obj.TypeId, values, infos)
    
    
    def remove(self):
        self.sender.run(self._asyncRemove)
        
    
    def createDynamicProperty(self, prop):
        info = Property.createPropertyInfo(self.obj, prop)        
        self._addDynamicPropertyCreation(prop, info)
    
    
    def removeDynamicProperty(self, prop):
        #we need to make sure the remove comes after the creation
        self.sender.run(self._asyncRemoveProperty, prop)
    
    
    def addDynamicExtension(self, extension, props):
        self.sender.run(self._asyncAddDynamcExtension, extension, props)
    
    
    def changeProperty(self, prop):
        value = Property.convertPropertyToWamp(self.obj, prop)
        self.sender.run(self._addPropertyChange, prop, value)

 
    def changePropertyStatus(self, prop):
        info = Property.createPropertyInfo(self.obj, prop)        
        self._addPropertyStatusChange(prop, info["status"])
        
    
    def recompute(self):
      
        self.sender.run(self.__asyncRecompute)
               
            
    async def __asyncRecompute(self):
        
        try:
            self.logger.debug("Recompute")                
            uri = u"ocp.documents.edit.{0}.call.Document.Objects.{1}.onRecomputed".format(self.docId, self.name)
            await self.connection.session.call(uri)
        
        except Exception as e:
            self.logger.error("Recompute exception: {0}".format(e))
            

class OnlineViewProvider(FreeCADOnlineObject):
    
    def __init__(self, obj, onlineobj, onlinedoc):        
        super().__init__(obj.Object.Name, onlinedoc, "ViewProviders", parentOnlineObj=onlineobj)
        self.obj = obj
        self.proxydata = None   #as FreeCAD 0.18 does not forward viewprovider proxy changes we need a way to identify changes
          
        self.sender.registerBatchHandler("__vpAddPropChange", self._asyncPropertyChangeFromCache)

        
    def setup(self):
        
        if float(".".join(FreeCAD.Version()[0:2])) == 0.18:
            #part of the FC 0.18 no proxy change event workaround
            if hasattr(self.obj, 'Proxy'):
                self.proxydata = self.obj.Proxy
        
        #collect all property values and infos
        values = {}
        infos = {}
        for prop in self.obj.PropertiesList:
            values[prop] = Property.convertPropertyToWamp(self.obj, prop)
            infos[prop]  = Property.createPropertyInfo(self.obj, prop)
            
        self.sender.run(self._asyncSetup, self.obj.TypeId, values, infos)
    
    
    def remove(self):
        self.sender.run(self._asyncRemove)
        
    
    def createDynamicProperty(self, prop):
        info = Property.createPropertyInfo(self.obj, prop)        
        self._addDynamicPropertyCreation(prop, info)
    
    
    def removeDynamicProperty(self, prop):
        self.sender.run(self._asyncRemoveProperty, prop)
    
    
    def addDynamicExtension(self, extension, props):
        self.sender.run(self._asyncAddDynamcExtension, extension, props)
    
    
    def changeProperty(self, prop):
        
        value = Property.convertPropertyToWamp(self.obj, prop)
        
        if float(".".join(FreeCAD.Version()[0:2])) == 0.18:
            #work around missing proxy callback in ViewProvider. This may add to some delay, as proxy change is ony forwarded 
            #when annother property changes afterwards, however, at least the order of changes is keept
            if hasattr(self.obj, 'Proxy'):
                if not self.proxydata is self.obj.Proxy:
                    self.proxydata = self.obj.Proxy
                    self.sender.run(self.__vpAddPropChange, 'Proxy', self.obj.dumpPropertyContent('Proxy'))
            
        
        self.sender.run(self.__vpAddPropChange, prop, value)


    def changePropertyStatus(self, prop):
        info = Property.createPropertyInfo(self.obj, prop)        
        self._addPropertyStatusChange(prop, info["status"])
    

    def __vpAddPropChange(self, prop, value):
        #indirection to have different function name as parent object in runner
        self._addPropertyChange(prop, value)

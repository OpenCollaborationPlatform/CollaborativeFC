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
from Documents.AsyncRunner import BatchedOrderedRunner, DocumentRunner
import Documents.Property as Property

class FreeCADOnlineObject():
    
    def __init__(self, name, onlinedoc, objGroup, parentOnlineObj = None):
        
        self.logger = logging.getLogger(objGroup[:-1] + " " + name)
                
        #check which type of runner to use 
        if os.getenv('FC_OCP_SYNC_MODE', "0") == "1":
            self.logger.info('Use non-default sync mode "Document-Sync"')
            self.runner     = DocumentRunner.getSenderRunner(onlinedoc.id, self.logger)
        
        else:
            if parentOnlineObj is None:
                self.runner     = BatchedOrderedRunner(self.logger) #used by the object to sync outgoing events
            else:
                self.runner     = parentOnlineObj.runner
                       
        self.docId           = onlinedoc.id
        self.data            = onlinedoc.data
        self.connection      = onlinedoc.connection
        self.name            = name
        self.objGroup        = objGroup 
        self.dynPropCache    = {}
        self.statusPropCache = {}
        self.propChangeCache = {}
        self.propChangeOutlist = []

    async def _docPrints(self):
        uri = u"ocp.documents.{0}.prints".format(self.docId)
        vals = await self.connection.session.call(uri)
        for val in vals:
            self.logger.debug(val)

    async def _asyncSetup(self, typeid, values, infos):
        #creates the object in the ocp node
    
        self.logger.debug(f"New object {self.name} ({typeid})")

        try:           
            uri = u"ocp.documents.{0}".format(self.docId)
            await self.connection.session.call(uri + u".content.Document.{0}.NewObject".format(self.objGroup), self.name, typeid)
            
            #create all properties that need setup           
            await self.__asyncCreateProperties(False, list(values.keys()), list(infos.values()))
        
        except Exception as e:
            self.logger.error("Setup error: {0}".format(e))
           
    
    async def __asyncCreateProperty(self, dyn, prop, info):
        #adds a property with its property info
        #could be added as normal or as dynamic property, dependend on dyn boolean
        
        try:            
            if dyn:
                self.logger.debug(f"Create dynamic property {prop}")
                fnc = "CreateDynamicProperty"
            else:
                self.logger.debug(f"Setup default property {prop}")
                fnc = "SetupProperty"
                
            uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.{self.name}.Properties.{fnc}"
            await self.connection.session.call(uri, prop, info["typeid"], info["group"], info["docu"], info["status"])
        
        except Exception as e:
            self.logger.error("Create property {0} failed: {1}".format(prop, e))
    
    
    async def __asyncCreateProperties(self, dyn, props, infos):
        #adds a list of properties and a list with their property infos
        #could be added as normal or as dynamic property, dependend on dyn boolean
        
        try:            
            if dyn:
                self.logger.debug(f"Create dynamic properties {props}")
                fnc = "CreateDynamicProperties"
            else:
                self.logger.debug(f"Setup default properties {props}")
                fnc = "SetupProperties"
                
            uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.{self.name}.Properties.{fnc}"
            await self.connection.session.call(uri, props, infos)
        
        except Exception as e:
            self.logger.error(f"Setup properties failed: {e}")
    
    
    async def _asyncRemoveProperty(self, prop):
        try:        
            self.logger.debug(f"Remove property {prop}")
            uri = u"ocp.documents.{0}.content.Document.{1}.{2}.Properties.RemoveDynamicProperty".format(self.docId, self.objGroup, self.name)
            await self.connection.session.call(uri, prop)
        
        except Exception as e:
            self.logger.error("Remove property {0} failed: {1}".format(prop, e))
        
    
    def _addDynamicPropertyCreation(self, prop, info):
        #caches the dynamic property creation to be executed as batch later
        self.dynPropCache[prop] = info
        
        
    async def _asyncCreateDynamicPropertiesFromCache(self):
        
        if len(self.dynPropCache) == 0:
            return
        try:
            props = self.dynPropCache.copy()
            self.dynPropCache.clear()
            
            keys   = list(props.keys())
            values = list(props.values())
            
            if len(props) == 1:
                await self.__asyncCreateProperty(True, keys[0], values[0])
            
            else:
                await self.__asyncCreateProperties(True, keys, values)

        except Exception as e:
            self.logger.error("Create dyn property from cache failed: {0}".format(e))
            
            
    def _addPropertyStatusChange(self, prop, status):
        #add property with status to the cache. 
        self.statusPropCache[prop] = status
        
        
    async def _asyncStatusPropertiesFromCache(self):
        
        if len(self.statusPropCache) == 0:
            return
        try:
            props = self.statusPropCache.copy()
            self.statusPropCache.clear()
            
            keys   = list(props.keys())
            values = list(props.values())
            
            uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.{self.name}.Properties."
            
            if  float(".".join(FreeCAD.Version()[0:2])) >= 0.19:
                #0.19 directly supports status
                if len(props) == 1:
                    self.logger.debug("Change property status {0}".format(keys[0]))
                    uri += keys[0] + ".status"
                    await self.connection.session.call(uri, values[0])
                
                else:
                    self.logger.debug("Change batched property status: {0}".format(keys))
                    uri += "SetStatus"
                    failed = await self.connection.session.call(uri, keys, values)
                    if failed:
                        raise Exception(f"Properties {failed} failed")
            else:
                #0.18 only supports editor mode subset of status
                if len(props) == 1:
                    self.logger.debug("Change property status {0}".format(keys[0]))
                    uri += keys[0] + ".SetEditorMode"
                    await self.connection.session.call(uri, values[0])
                
                else:
                    self.logger.debug("Change batched property status: {0}".format(keys))
                    uri += "SetEditorModes"
                    failed = await self.connection.session.call(uri, keys, values)
                    if failed:
                        raise Exception(f"Properties {failed} failed")
                
        except Exception as e:
            self.logger.error("Change property status from cache failed: {0}".format(e))
            
    
    def _addPropertyChange(self, prop, value, outlist):
        
        #add property with status to the cache. 
        self.propChangeCache[prop] = value
        self.propChangeOutlist = outlist #we are only interested in the last set outlist, not intermediate steps
    
    
    async def __getCidForData(self, data):
               
        #store the data for the processing!
        datakey = self.data.addData(data)
        
        #get the cid!
        uri = f"ocp.documents.{self.docId}.raw.CidByBinary"
        cid = await self.connection.session.call(uri, self.data.uri, datakey)
        return cid
        
    
    async def _asyncPropertyChangeFromCache(self):
                 
        if not self.propChangeCache:
            return

        #copy everything before first async op
        props = self.propChangeCache.copy()
        self.propChangeCache.clear()
        out = self.propChangeOutlist.copy()
               
        try:
                
            #get the cids for the binary properties in parallel
            tasks = []
            for prop in props:
                if isinstance(props[prop], bytearray): 
                    
                    async def run(props, prop):
                        cid = await self.__getCidForData(props[prop])
                        props[prop] = cid
                        
                    tasks.append(run(props, prop))

            #also in parallel: query the current outlist
            if self.objGroup == "Objects":
                outlist = []
                async def getOutlist():
                    uri = f"ocp.documents.{self.docId}.content.Document.DAG.GetObjectOutList"
                    outlist = await self.connection.session.call(uri, self.name)
                    outlist.sort()
                    
                tasks.append(getOutlist())


            #execute all parallel tasks
            if tasks:
                await asyncio.wait(tasks)
            
            #now batchwrite all properties in correct order
            if len(props) == 1:
                prop = list(props.keys())[0]
                await self._asyncWriteProperty(prop, props[prop])
            else:
                await self._asyncWriteProperties(list(props.keys()), list(props.values()))

            #finally process the outlist
            if self.objGroup == "Objects":
                out.sort()
                if out != outlist:
                    self.logger.debug(f"Set Outlist")
                    uri = f"ocp.documents.{self.docId}.content.Document.DAG.SetObjectOutList"
                    await self.connection.session.call(uri, self.name, out)
                
        except Exception as e:
            self.logger.error(f"Batch writing properties for {self.name} failed: {e}")
        
        
    async def _asyncWriteProperty(self, prop, value):
        
        try:       
            #simple POD property: just add it!
            self.logger.debug(f"Write property {prop}")
            uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.{self.name}.Properties.{prop}.SetValue"
            await self.connection.session.call(uri, value)           
        
        except Exception as e:
            self.logger.error("Writing property error ({1}, {2}): {0}".format(e, self.name, prop))
   
   
    async def _asyncWriteProperties(self, props, values):
        #note: does not work for binary properties!
        
        try:
            self.logger.debug("Write batch properties {0}".format(props))
            uri = u"ocp.documents.{0}.content.Document.{1}.{2}.Properties.SetValues".format(self.docId, self.objGroup, self.name)
            failed = await self.connection.session.call(uri, props, values)
            if failed:
                raise Exception(f"Properties {failed} failed")
            
        except Exception as e:
            self.logger.error("Writing property batch error: {0}".format(e))
     
     
    async def _asyncAddDynamcExtension(self, extension, props):
        
        try:           
            uri = f"ocp.documents.{self.docId}"
            
            #add the extension must be done: a changed property could result in use of the extension
            self.logger.debug("Add extension {0}".format(extension))
            calluri = uri + u".content.Document.{0}.{1}.Extensions.Append".format(self.objGroup, self.name)
            await self.connection.session.call(calluri, extension)
            
            #the props can be created by a single call
            infos = []
            for prop in props:
                infos.append(Property.createPropertyInfo(self.obj, prop))
                
            await self.__asyncCreateProperties(False, props, infos)            

                
        except Exception as e:
            self.logger.error("Adding extension failed: {0}".format(e))
     
     
    async def _asyncRemove(self):
        try:
            self.logger.debug("Remove")
            uri = u"ocp.documents.{0}".format(self.docId)
            await self.connection.session.call(uri + u".content.Document.{0}.RemoveObject".format(self.objGroup), self.name)
        
        except Exception as e:
            self.logger.error("Removing error: {0}".format(e))
            
    
    async def waitTillCloseout(self, timeout = 10):
        #wait till all current async tasks are finished. Note that it also wait for task added during the wait period.
        #throws an error on timeout.        
        await self.runner.waitTillCloseout(timeout)
        
    async def close(self):   
        await self.runner.close()
        
    def synchronize(self, syncer):
        self.runner.sync(syncer)


class OnlineObject(FreeCADOnlineObject):
    
    def __init__(self, obj, onlinedoc):
        
        super().__init__(obj.Name, onlinedoc, "Objects")
        self.recomputeCache = {}
        self.odoc           = onlinedoc
        self.obj            = obj
        
        self.runner.registerBatchHandler("_addPropertyChange", self._asyncPropertyChangeFromCache)
        self.runner.registerBatchHandler("_addDynamicPropertyCreation", self._asyncCreateDynamicPropertiesFromCache)
        self.runner.registerBatchHandler("_addPropertyStatusChange", self._asyncStatusPropertiesFromCache)
        
        
    def setup(self, syncer=None, restart=None):
        values = {}
        infos = {}
        for prop in self.obj.PropertiesList:
            values[prop] = Property.convertPropertyToWamp(self.obj, prop)
            infos[prop]  = Property.createPropertyInfo(self.obj, prop)
            
        #check if we need to handle a document syncronisation
        if syncer:
            self.runner.sync(syncer)
            
        self.runner.run(self._asyncSetup, self.obj.TypeId, values, infos)
        
        if restart:
            self.runner.run(restart.asyncRestart)
        
        #check if there are properties that need the defult values uploaded
        props = Property.getNonDefaultValueProperties(self.obj)
        for prop in props:
            self.runner.run(self._addPropertyChange, prop, Property.convertPropertyToWamp(self.obj, prop), [])
    
    
    def remove(self):
        self.runner.run(self._asyncRemove)
        
        #we cannot use the runner to run close on itself, because it would wait for itself till it finishs: 
        #that is a guaranteed timeout
        async def __closeout():
            #waits till runner finished all tasks and than closes it
            await self.runner.close()
            
        asyncio.ensure_future(__closeout())
        

    def createDynamicProperty(self, prop):
        info = Property.createPropertyInfo(self.obj, prop)
        self.runner.run(self._addDynamicPropertyCreation, prop, info)
    
    
    def removeDynamicProperty(self, prop):
        #we need to make sure the remove comes after the creation
        self.runner.run(self._asyncRemoveProperty, prop)
    
    
    def addDynamicExtension(self, extension, props):
        self.runner.run(self._asyncAddDynamcExtension, extension, props)
    
    
    def changeProperty(self, prop):
        value = Property.convertPropertyToWamp(self.obj, prop)
        outlist = [obj.Name for obj in self.obj.OutList]
        self.runner.run(self._addPropertyChange, prop, value, outlist)

 
    def changePropertyStatus(self, prop):
        info = Property.createPropertyInfo(self.obj, prop)        
        self.runner.run(self._addPropertyStatusChange, prop, info["status"])
        
    
    def recompute(self):      
        self.runner.run(self.__asyncRecompute)
               
            
    async def __asyncRecompute(self):
        
        try:
            self.logger.debug("Recompute")                
            uri = u"ocp.documents.{0}.content.Document.Objects.{1}.onObjectRecomputed".format(self.docId, self.name)
            await self.connection.session.call(uri)
        
        except Exception as e:
            self.logger.error("Recompute exception: {0}".format(e))
            

class OnlineViewProvider(FreeCADOnlineObject):
    
    def __init__(self, obj, onlineobj, onlinedoc):        
        super().__init__(obj.Object.Name, onlinedoc, "ViewProviders", parentOnlineObj=onlineobj)
        self.obj = obj
        self.proxydata = None   #as FreeCAD 0.18 does not forward viewprovider proxy changes we need a way to identify changes
        
        self.runner.registerBatchHandler("_addPropertyChangeVP", self._asyncPropertyChangeFromCache)
        self.runner.registerBatchHandler("_addDynamicPropertyCreationVP", self._asyncCreateDynamicPropertiesFromCache)
        self.runner.registerBatchHandler("_addPropertyStatusChangeVP", self._asyncStatusPropertiesFromCache)
          
    def setup(self, sync=None):
        
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
            
        #check if we need to handle a syncronisation
        if sync:
            self.runner.sync(sync)
            
        self.runner.run(self._asyncSetup, self.obj.TypeId, values, infos)
        
        #check if there are properties that need the defult values uploaded
        props = Property.getNonDefaultValueProperties(self.obj)
        for prop in props:
            self.runner.run(self._addPropertyChange(prop, Property.convertPropertyToWamp(self.obj, prop), []))  

    
    def remove(self):
        self.runner.run(self._asyncRemove)
        
    
    def createDynamicProperty(self, prop):
        info = Property.createPropertyInfo(self.obj, prop)        
        self.runner.run(self._addDynamicPropertyCreationVP, prop, info)
    
    
    def removeDynamicProperty(self, prop):
        self.runner.run(self._asyncRemoveProperty, prop)
    
    
    def addDynamicExtension(self, extension, props):
        self.runner.run(self._asyncAddDynamcExtension, extension, props)
    
    
    def changeProperty(self, prop):
        
        value = Property.convertPropertyToWamp(self.obj, prop)
        
        if float(".".join(FreeCAD.Version()[0:2])) == 0.18:
            #work around missing proxy callback in ViewProvider. This may add to some delay, as proxy change is ony forwarded 
            #when annother property changes afterwards, however, at least the order of changes is keept
            if hasattr(self.obj, 'Proxy'):
                if not self.proxydata is self.obj.Proxy:
                    self.proxydata = self.obj.Proxy
                    self.runner.run(self._addPropertyChangeVP, 'Proxy', self.obj.dumpPropertyContent('Proxy'), [])
            
        
        self.runner.run(self._addPropertyChangeVP, prop, value, [])


    def changePropertyStatus(self, prop):
        info = Property.createPropertyInfo(self.obj, prop)        
        self.runner.run(self._addPropertyStatusChangeVP, prop, info["status"])


    #indirections for batch handler, as we use the shared runner with our document object and should not 
    #override the registered batch handlers there
    def _addPropertyChangeVP(self, *args):
        self._addPropertyChange(*args)
        
    def _addDynamicPropertyCreationVP(self, *args):
        self._addDynamicPropertyCreation(*args)
        
    def _addPropertyStatusChangeVP(self, *args):
        self._addPropertyStatusChange(*args)

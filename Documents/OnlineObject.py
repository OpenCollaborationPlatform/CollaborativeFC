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

# This module provides FC object translation layers between the synchronous FreeCAD execution and asynchronous 
# OCP node document. The classes provide a normal python API and create and execute async actions from 
# those calls. The sync API is non blocking, and all errors and cleanups are also processed async.


import FreeCAD
import asyncio, logging, os, traceback
import Documents.Batcher  as Batcher
import Documents.Property as Property
import Documents.Object   as Object
from Documents.AsyncRunner import BatchedOrderedRunner, DocumentRunner
from Documents.Writer import OCPObjectWriter
from Documents.Reader import OCPObjectReader
from Utils.Errorhandling import isOCPError, OCPErrorHandler, attachErrorData


class FreeCADOnlineObject(OCPErrorHandler):
    
    def __init__(self, name, onlinedoc, objGroup, parentOnlineObj = None):
        
        super().__init__()
        
        self.logger = logging.getLogger(objGroup[:-1] + " " + name)
                
        # check which type of async runner to use 
        if os.getenv('FC_OCP_SYNC_MODE', "0") == "1":
            self.logger.info('Use non-default sync mode "Document-Sync"')
            self._runner     = DocumentRunner.getSenderRunner(onlinedoc.id, self.logger)
        
        else:
            if parentOnlineObj is None:
                self._runner     = BatchedOrderedRunner(self.logger) #used by the object to sync outgoing events
            else:
                self._runner     = parentOnlineObj._runner

        self._registerSubErrorhandler(self._runner)

        self.Writer = OCPObjectWriter(name, objGroup, onlinedoc, self.logger)
        self.Reader = OCPObjectReader(name, objGroup, onlinedoc, self.logger)

    # Error Handling
    # ##############

    # All async functions are processed in the objects async runner. All occuring errors are 
    # upstreamed to us and handled in the following function.
    
    def _handleError(self, source, error, data):
        
        # after any error we need to ensure FreeCAD and Node status match
        self._runner.run(self.download)
        
        if "ocp_message" in data:
                        
            err = data["ocp_message"]
            printdata = data.copy()
            del printdata["ocp_message"]
            del printdata["exception"]
            self.logger.Error(f"{err}: {printdata}")
        
        super()._handleError(source, error, data)
    

    # Common FreeCAD object functionality
    # ###################################

    async def _docPrints(self):
        try:
            uri = u"ocp.documents.{0}.prints".format(self._docId)
            vals = await self.connection.api.call(uri)
            for val in vals:
                self.logger.debug(val)
        except Exception as e:
            attachErrorData(e, "ocp_message", "Retreiving JavaScript prints failed")
            self._processException(e)


    async def waitTillCloseout(self, timeout = 10):
        #wait till all current async tasks are finished. Note that it also wait for task added during the wait period.
        #throws an error on timeout.        
        await self._runner.waitTillCloseout(timeout)

        
    async def close(self):   
        await self._runner.close()

        
    def synchronize(self, syncer):
        self._runner.sync(syncer)
        
    
    async def download(self, obj):
        # Loads the OCP node data for this object into the FreeCAD one. If changes exist 
        # the local version will be overridden, hene can be used to reset a object
        # Note: this function works async, but cannot handle any changes during execution,
        #       neither on the node nor in the FC object
        
        try:
            self.logger.debug(f"Download")
            
            #first check if we are available online to setup. Could happen that e.g. we load before the viewprovider was uploaded
            if not await self.Reader.isAvailable():
                return
            
            #add the extensions (do that before properties, as extensions adds props too)
            extensions = await self.Reader.extensions()
            for extension in extensions:
                self.logger.debug(f"Add extension {extension}")
                Object.createExtension(obj, extension)
            
            oProps = await self.Reader.propertyList()
            if not oProps:
                #no properties mean we loaded directly after object creation, before default property setup. Nothing is written yet
                return
            defProps = self.obj.PropertiesList
            
            # check if we need to remove some local props
            remove = set(defProps) - set(oProps)
            if remove:
                self.logger.debug(f"Local object has too many properties, remove {remove}")
                Object.removeDynamicProperties(obj, remove)
                    
            # create the dynamic properties
            add = set(oProps) - set(defProps)
            infos = await self.Reader.propertiesInfos(add)
            self.logger.debug(f"Create and set dynamic properties {add}")
            Object.createDynamicProperties(obj, add, infos)
            
            # set all property values. Note that data can be None in case the property was never written (default value)
            values = await self.Reader.properties(oProps)
            writeProps  = []
            writeValues = []
            for prop, value in zip(oProps, values):
                if value:
                    writeProps.append(prop)
                    writeValues.append(value)

            self.logger.debug(f"Read properties {writeProps}")
            Object.setProperties(obj, writeProps, writeValues)
            
            # set the correct status for the non-dnamic properties
            infos = await self.Reader.propertiesInfos(defProps)
            status = [info["status"] for info in infos]
            self.logger.debug(f"Set status of default properties {defProps} to {status}")
            for prop, stat in zip(defProps, status):
                Object.setPropertyStatus(obj, prop, stat)

            self.logger.debug(f"Object download finished")
            
        except Exception as e:
            attachErrorData(e, "ocp_message", "Downloading object failed")
            raise e
      

    async def upload(self, obj):
        # Creates and uploads the object data into the ocp node
        # Note: this function works async, but cannot handle any changes during execution,
        #       neither on the node nor in the FC object
        
        try:
            #first check if we are available online.
            if await self.Writer.isAvailable():
                raise Exception("Object already setup, cannot upload")
            
            #setup object and all properties
            infos = []
            for prop in obj.PropertiesList:
                infos.append(Property.createInformation(obj, prop))
            
            await self.Writer.setup(obj.TypeId, obj.PropertiesList, infos)
            
            #we process the other tasks in parallel
            tasks = []
            
            #upload all extensions
            ext = Object.getExtensions(obj)
            for e in ext:
                tasks.append(self.Writer.addExtension(e))
            
            #write all properties.
            props = obj.PropertiesList
            for prop in props:
                value = Property.convertPropertyToWamp(obj, prop)
                self.Writer.changeProperty(prop, value, obj.OutList)
            
            tasks.append(self.Writer.processPropertyChanges())

            if tasks:
                await asyncio.gather(*tasks)
      
        except Exception as e:
            attachErrorData(e, "ocp_message", "Uploading object failed")
            raise e
        

class OnlineObject(FreeCADOnlineObject):
    
    def __init__(self, obj, onlinedoc):
        
        super().__init__(obj.Name, onlinedoc, "Objects")
    
        self.recomputeCache = {}
        self.obj            = obj
        
        batchers = [Batcher.EquallityBatcher("OnlineObject.__addDynamicProperty", self.Writer.processDynamicPropertyAdditions),
                    Batcher.EquallityBatcher("OnlineObject.__changeProperty", self.Writer.processPropertyChanges),
                    Batcher.EquallityBatcher("OnlineObject.__changePropertyStatus", self.Writer.processPropertyStatusChanges)
        ]
        
        for batcher in batchers:
            self._runner.registerBatcher(batcher)

        cbs = [b.copy() for b in batchers]            
        self._runner.registerBatcher(Batcher.MultiBatcher(cbs))

        
    def setup(self, syncer=None):
        # setup the FC object on the OCP node including all properties
        
        infos = []
        for prop in self.obj.PropertiesList:
            infos.append(Property.createInformation(self.obj, prop))
            
        #check if we need to handle a document syncronisation
        if syncer:
            self._runner.sync(syncer)
            
        self._runner.run(self.Writer.setup, self.obj.TypeId, self.obj.PropertiesList, infos)
        
        #check if there are properties that need the default values uploaded
        props = Property.getNonDefaultValueProperties(self.obj)
        for prop in props:
            self._runner.run(self.Writer.changeProperty, prop, Property.convertPropertyToWamp(self.obj, prop), [])

    
    def isSettingUp(self):
        return self.Writer.setupStage
    
    def remove(self):
        self._runner.run(self.Writer.remove)
        
        #we cannot use the runner to run close on itself, because it would wait for itself till it finishes: 
        #that is a guaranteed timeout
        async def __closeout():
            #waits till runner finished all tasks and than closes it
            await self._runner.close()
            
        asyncio.ensure_future(__closeout())
        

    def createDynamicProperty(self, prop):
        info = Property.createInformation(self.obj, prop)
        self._runner.run(self.__addDynamicProperty, prop, info)
        
    def __addDynamicProperty(self, prop, info):
        #indirection for batcher named tasks
        self.Writer.addDynamicProperty(prop, info)
    
    
    def removeDynamicProperty(self, prop):
        #we need to make sure the remove comes after the creation
        self._runner.run(self.Writer.removeProperty, prop)
    
    
    def addDynamicExtension(self, extension, props):
        infos = []
        for prop in props:
            infos.append(Property.createInformation(self.obj, prop))
        self._runner.run(self.Writer.addExtension, extension, props, infos)
    
    
    def changeProperty(self, prop):
        value = Property.convertPropertyToWamp(self.obj, prop)
        outlist = [obj.Name for obj in self.obj.OutList]
        self._runner.run(self.__changeProperty, prop, value, outlist)
        
    def __changeProperty(self, prop, value, outlist):
        #indirection for batcher named tasks
        self.Writer.changeProperty(prop, value, outlist)

 
    def changePropertyStatus(self, prop):
        info = Property.createInformation(self.obj, prop)        
        self._runner.run(self.__changePropertyStatus, prop, info["status"])
        
    def __changePropertyStatus(self, prop, info):
        #indirection for batcher named tasks
        self.Writer.changePropertyStatus(prop, info)
        
    
    def recompute(self):      
        self._runner.run(self.Writer.objectRecomputed)
     
     

class OnlineViewProvider(FreeCADOnlineObject):
    
    def __init__(self, obj, onlineobj, onlinedoc):        
        super().__init__(obj.Object.Name, onlinedoc, "ViewProviders", parentOnlineObj=onlineobj)
        self.obj = obj
        self.proxydata = None   #as FreeCAD 0.18 does not forward viewprovider proxy changes we need a way to identify changes
        
        batchers = [Batcher.EquallityBatcher("OnlineViewProvider.__addDynamicProperty", self.Writer.processDynamicPropertyAdditions),
                    Batcher.EquallityBatcher("OnlineViewProvider.__changeProperty", self.Writer.processPropertyChanges),
                    Batcher.EquallityBatcher("OnlineViewProvider.__changePropertyStatus", self.Writer.processPropertyStatusChanges)
        ]
        
        for batcher in batchers:
            self._runner.registerBatcher(batcher)
            
        cbs = [b.copy() for b in batchers]            
        self._runner.registerBatcher(Batcher.MultiBatcher(cbs))
        
          
    def setup(self, sync=None):
        
        if float(".".join(FreeCAD.Version()[0:2])) == 0.18:
            #part of the FC 0.18 no proxy change event workaround
            if hasattr(self.obj, 'Proxy'):
                self.proxydata = self.obj.Proxy
        
        #collect all property values and infos
        infos = []
        for prop in self.obj.PropertiesList:
            info = Property.createInformation(self.obj, prop)
            infos.append(info)
            
        #check if we need to handle a syncronisation
        if sync:
            self._runner.sync(sync)
         
        #setup ourself
        self._runner.run(self.Writer.setup, self.obj.TypeId, self.obj.PropertiesList, infos)
        
        #check if there are properties that need the default values uploaded
        props = Property.getNonDefaultValueProperties(self.obj)
        for prop in props:
            self._runner.run(self.Writer.changeProperty(prop, Property.convertPropertyToWamp(self.obj, prop), []))  

    
    def remove(self):
        self._runner.run(self.Writer.remove)
        
    
    def createDynamicProperty(self, prop):
        info = Property.createInformation(self.obj, prop)        
        self._runner.run(self.__addDynamicProperty, prop, info)
    
    
    def removeDynamicProperty(self, prop):
        self._runner.run(self.Writer.removeProperty, prop)
    
    
    def addDynamicExtension(self, extension, props):
        infos = []
        for prop in props:
            infos.append(Property.createInformation(self.obj, prop))
        self._runner.run(self.Writer.addExtension, extension, props, infos)
    
    
    def changeProperty(self, prop):
        
        value = Property.convertPropertyToWamp(self.obj, prop)
        
        if float(".".join(FreeCAD.Version()[0:2])) == 0.18:
            #work around missing proxy callback in ViewProvider. This may add to some delay, as proxy change is only forwarded 
            #when another property changes afterwards, however, at least the order of changes is kept
            if hasattr(self.obj, 'Proxy'):
                if not self.proxydata is self.obj.Proxy:
                    self.proxydata = self.obj.Proxy
                    self._runner.run(self.__changeProperty, 'Proxy', self.obj.dumpPropertyContent('Proxy'), [])
            
        
        self._runner.run(self.__changeProperty, prop, value, [])


    def changePropertyStatus(self, prop):
        info = Property.createInformation(self.obj, prop)        
        self._runner.run(self.__changePropertyStatus, prop, info["status"])
        
        
    def __changePropertyStatus(self, prop, info):
        #indirection for batcher named tasks
        self.Writer.changePropertyStatus(prop, info)

    def __changeProperty(self, prop, value, outlist):
        #indirection for batcher named tasks
        self.Writer.changeProperty(prop, value, outlist)
        
    def __addDynamicProperty(self, prop, info):
        #indirection for batcher named tasks
        self.Writer.addDynamicProperty(prop, info)
        

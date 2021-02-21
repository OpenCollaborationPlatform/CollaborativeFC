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

import FreeCAD, logging, os, asyncio, traceback
import Documents.Property       as Property
import Documents.Object         as Object
import Documents.AsyncRunner    as AsyncRunner
import Documents.Helper         as Helper
import Documents.Observer       as Observer
from Documents.OnlineObject import OnlineObject
from Documents.OnlineObject import OnlineViewProvider
from autobahn.wamp.types    import SubscribeOptions, CallOptions
from autobahn.wamp          import ApplicationError

class OnlineObserver():
    
    def __init__(self, odoc):
      
        self.onlineDoc = odoc
        self.logger = logging.getLogger("Online observer " + odoc.id[-5:])
        self.runners = {}
        
        asyncio.ensure_future(self.__asyncInit())
       

    async def __asyncInit(self):
        
        self.callbacks = {
                "Objects.onObjectCreated": self.__cbNewObject,
                "Objects.onObjectRemoved": self.__cbRemoveObject,
                "Objects..onSetupFinished": self.__cbObjectOnSetupFinished,
                "Objects..onObjectRecomputed": self.__cbObjectRecomputed,
                "Objects..onExtensionCreated": self.__cbCreateObjextExtension,
                "Objects..onExtensionRemoved": self.__cbRemoveObjextExtension,       
                "Objects...onDynamicPropertyCreated": self.__cbCreateObjectDynProperty,
                "Objects...onDynamicPropertiesCreated": self.__cbCreateObjectDynProperties,
                "Objects...onDynamicPropertyRemoved": self.__cbRemoveObjectDynProperty,
                "Objects...onDatasChanged": self.__cbChangeMultiObject,
                "Objects....onDataChanged": self.__cbChangeObject, 
                "Objects....onStatusChanged": self.__cbChangePropStatus,
                "ViewProviders..onSetupFinished": self.__cbViewProviderOnSetupFinished,
                "ViewProviders..onExtensionCreated": self.__cbCreateViewProviderExtension,
                "ViewProviders..onExtensionRemoved": self.__cbRemoveViewProviderExtension,
                "ViewProviders...onDynamicPropertyCreated": self.__cbCreateViewProviderDynProperty,
                "ViewProviders...onDynamicPropertiesCreated": self.__cbCreateViewProviderDynProperties,
                "ViewProviders...onDynamicPropertyRemoved": self.__cbRemoveViewProviderDynProperty,
                "ViewProviders...onDatasChanged": self.__cbChangeMultiViewProdiver,
                "ViewProviders....onDataChanged": self.__cbChangeViewProvider,
                "ViewProviders....onStatusChanged": self.__cbChangeViewProvierPropStatus,                
            }
        
        self.docCBs = {
            }
        
        if os.getenv('FC_OCP_SYNC_MODE', "0") == "1":
            self.synced = True
        else:
            self.synced = False
        
        try:
            # careful: any change here must be also changed for close and unsubscribe!
            key = f"observer {self.onlineDoc.id}"
            uri = f"ocp.documents.{self.onlineDoc.id}.content.Document."            
            for cb in self.callbacks.keys():
                await self.onlineDoc.connection.api.subscribe(key, self.__run, uri+cb, options=SubscribeOptions(match="wildcard", details_arg="details"))

            #self.onlineDoc.connection.api.subscribe(self.__runDocProperties, uri+"Properties", options=SubscribeOptions(match="prefix", details_arg="details"))
           
        except Exception as e:
            self.logger.error("Setup failed: ", e)

     
    async def close(self):
        tasks = []
        for runner in self.runners.values():
            tasks.append(runner.close())
        
        tasks.append(self.onlineDoc.connection.api.closeKey(f"observer {self.onlineDoc.id}"))
            
        if tasks:
            await asyncio.gather(*tasks)
            
        self.runners = []
     
        
    async def __run(self, *args, details=None):
    
        #the path are all topics after Document.Objects.
        path = details.topic.split(".")[5:]    
        #key is the one used in the callback map
        key = path.pop(0) + "."*len(path) + path[-1]
        
        #check if we should handle the callback (last key is callback name)
        if key not in self.callbacks:
            return
        
        #if object and property names are provided, add them to argument list
        if len(path) == 2 or len(path) == 3:
            #.MyObject.onEventName  or .MyObject.Properties.onEventName
            args = (path[0],) + args  #first key is object name
                
        elif len(path) == 4:
            #.MyObject.Properties.MyProperty.onEventName
            args = (path[0], path[2],) + args  #first key is object name, third key is property name

        fnc = self.callbacks[key]
        self.getRunner(args[0]).run(fnc, *args) #first argument is name
        
    
    async def __runDocProperties(self, *args, details=None):
        
        #keys are all topics after Document.Properties.
        keys = details.topic.split(".")[6:]
        
        if keys[-1] not in self.docCBs:
            return
        
        #if object and property names are provided, add them to argument list
        if len(keys) == 2:
            #.MyProperty.onEventName
            args = (keys[0],) + args #first key is object name
            
        fnc = self.docCBs[keys[-1]]
        AsyncRunner.DocumentRunner.getReceiverRunner(self.onlineDoc.id, self.logger).run(fnc, *args)
            

    def getRunner(self, name):
        
        if not name in self.runners:
            if self.synced:
                self.runners[name] = AsyncRunner.DocumentRunner.getReceiverRunner(self.onlineDoc.id, self.logger)
            else:
                self.runners[name] = AsyncRunner.OrderedRunner(self.logger)
                
        return self.runners[name]
    
    
    async def closeRunner(self, name):
        
        if name in self.runners and not self.synced:
            await self.runners[name].close()
            del self.runners[name]


    async def waitTillCloseout(self, timeout = 10):
        coros = []
        for runner in self.runners:
            coros.append(self.runners[runner].waitTillCloseout(timeout))
            
        if coros:
            await asyncio.wait(coros)

     
    #Callbacks for DML events
    #******************************************************************************************************************************************************
     
    async def __cbNewObject(self, name, typeID):
        try:
            self.logger.debug(f"Object ({name}): New ({typeID})")
            
            #maybe the object exists already (e.g. auto created by annother added object like App::Part Origin)
            if hasattr(self.onlineDoc.document, name):
                #TODO: check if typeid matches
                return
            
            #we do not add App origins, lines and planes, as they are only Autocreated from parts and bodies
            #hence they will be created later then the parent is added
            if typeID in ["App::Origin", "App::Line", "App::Plane"]:
                return
                       
            #add the object we want
            with Observer.blocked(self.onlineDoc.document):
                obj = self.onlineDoc.document.addObject(typeID, name)
                
                #remove touched status. could happen that other objects like origins have been created automatically
                for added in Observer.createdObjectsWhileDeactivated(self.onlineDoc.document):
                    if added.TypeId == "App::Origin":
                        added.recompute() #recompute origin to get viewprovider size correctly (auto updated without change callback)
                    added.purgeTouched()
            
            
            oobj = OnlineObject(obj, self.onlineDoc)
            self.onlineDoc.objects[obj.Name] = oobj
            
            #create the online view provider for that object
            if obj.ViewObject:
                ovp = OnlineViewProvider(obj.ViewObject, oobj, self.onlineDoc)
                self.onlineDoc.viewproviders[obj.Name] = ovp                       

            
        except Exception as e:
            self.logger.error(f"Object ({name}): Add object online callback failed: {e}")
    

    async def __cbRemoveObject(self, name):
        
        try:
            self.logger.debug(f"Object ({name}): Remove")
            
            #remove FC object first
            with Observer.blocked(self.onlineDoc.document):
                self.onlineDoc.document.removeObject(name)
                   
            #remove online object
            oobj = self.onlineDoc.objects[name]
            await oobj.close()
            del(self.onlineDoc.objects[name])
            
            #remove online viewprovider (we do not intercept the special viewprovider removed event)
            if name in self.onlineDoc.viewproviders:
                del self.onlineDoc.viewproviders[name]
                
            #and our own runner. cannot call from here, as we are running in this runner ourself. hence waitTillCloseout would block
            asyncio.ensure_future(self.closeRunner(name))
            
        except Exception as e:
            self.logger.error(f"Object ({name}): Remove object online callback failed: {e}")
        
        
    async def __cbChangeObject(self, name, prop, value):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
        
        await self.__setProperty(obj, prop, value, f"Object ({name})")
        
        
    async def __cbChangeMultiObject(self, name, props, values):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
        
        await self.__setProperties(obj, props, values, f"Object ({name})")
 
 
    async def __cbChangePropStatus(self, name, prop, status):
        
        try:
            obj = self.onlineDoc.document.getObject(name)
            if obj is None:
                return
            
            self.logger.debug(f"Object ({name}): Change property {prop} status to {status}")
            Object.setPropertyStatus(obj, prop, status)
            
        except Exception as e:
            self.logger.error(f"Setting property status failed: {e}")
 
 
    async def __cbCreateObjectDynProperty(self, name, prop, typeID, group, documentation, status):        
        try:
            obj = self.onlineDoc.document.getObject(name)
            if obj is None:
                self.logger.error(f"Object ({name}): Should add dynamic property {prop} for not existing object")
                return
        
            self.logger.debug(f"Object ({name}): Create dynamic property {prop}")
            Object.createDynamicProperty(obj, prop, typeID, group, documentation, status)
        
        except Exception as e:
            self.logger.error(f"Dynamic property adding failed: {e}")
        
    
    async def __cbCreateObjectDynProperties(self, name, props, infos):

        try:
            obj = self.onlineDoc.document.getObject(name)
            if obj is None:
                self.logger.error(f"Object ({name}): Should add dynamic properties for not existing object: {props}")
                return
            
            self.logger.debug(f"Object ({name}): Create dynamic properties {props}")
            for i in range(0, len(props)):
                info = infos[i]
                Object.createDynamicProperty(obj, props[i], info["typeid"], info["group"], info["docu"], info["status"])
                
        except Exception as e:
            self.logger.error(f"Dynamic properties adding failed: {e}")      
    
    
    async def __cbRemoveObjectDynProperty(self, name, prop):
        
        try:
            obj = self.onlineDoc.document.getObject(name)
            if obj is None:
                self.logger.error(f"Object ({name}): Should remove dyn property {prop} for not existing object")
                return
            
            self.logger.debug(f"Object ({name}): Remove dynamic property {prop}")
            Object.removeDynamicProperty(obj, prop)
            
        except Exception as e:
            self.logger.error(f"Dyn property removing failed: {e.message}")

    
    async def __cbCreateObjextExtension(self, name, ext):
        
        try:
            obj = self.onlineDoc.document.getObject(name)
            if obj is None:
                self.logger.error(f"Object ({name}): Should add extension for not existing object")
                return
            
            self.logger.debug(f"Object ({name}): Add extension {ext}")
            Object.createExtension(obj, ext)
            
        except Exception as e:
            self.logger.error(f"Add extension failed: {e}")
    
    
    async def __cbRemoveObjextExtension(self, name, ext):
        
        try:
            obj = self.onlineDoc.document.getObject(name)
            if obj is None:
                self.logger.error(f"Object ({name}): Should remove extension {ext} for not existing object")
                return
            
            self.logger.debug(f"Object ({name}): Remove extension {ext}")
            Object.removeExtension(obj, ext)
            
        except Exception as e:
            self.logger.error(f"Remove extension failed: {e}")
    
    
    async def __cbObjectRecomputed(self, name):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"Object ({name}): Recomputed object does not exist")
            return
        
        self.logger.debug(f"Object ({name}): Recomputed")
        
        #we try to fix some known problems
        if obj.isDerivedFrom("Sketcher::SketchObject"):
            #we need to reassign geometry to fix the invalid sketch
            obj.Geometry = obj.Geometry
            
        #definitely purge purgeTouched.
        if hasattr(obj, "purgeTouched"):
            obj.purgeTouched()
            
            
    async def __cbObjectOnSetupFinished(self, name):
        #FreeCAD python object often get new properties with new versions. This is usually handled in the 
        #"onDocumentRestored" by checking if all properties are available and adding them if not. To enable 
        #cross version compatibility we need to call this function to ensure all relevant properties are avaiable
        #Note:  ideally we would not disable the the doc observer to just catch the new probs. However, it is highly 
        #       likely that some other parallel running coroutine did this. Hence we need to figure out the new properties
        #       ourself
        try:
            obj = self.onlineDoc.document.getObject(name)
            self.logger.debug(f"Object ({name}): Finish Setup")
            
            if hasattr(obj, "Proxy") and hasattr(obj.Proxy, "onDocumentRestored"):
                with Observer.blocked(self.onlineDoc.document):
                    props = obj.PropertiesList
                    obj.Proxy.onDocumentRestored(obj)
                    newprops = set(obj.PropertiesList) - set(props)
                    
                    oobj = self.onlineDoc.objects[name]
                    for prop in newprops:
                        oobj.createDynamicProperty(prop)
                        oobj.changeProperty(prop)
            
        except Exception as e:
            self.logger.error(f"Object ({name}): Version upgade after setup failed: {e}")

       
    async def __cbChangeViewProvider(self, name, prop, value):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
 
        await self.__setProperty(obj.ViewObject, prop, value, f"ViewProvider ({name})")
     
    
    async def __cbChangeMultiViewProdiver(self, name, props, values):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
               
        await self.__setProperties(obj.ViewObject, props, values, f"ViewProvider ({name})")
     
    
    async def __cbChangeViewProvierPropStatus(self, name, prop, status):
        
        try:
            obj = self.onlineDoc.document.getObject(name)
            if not obj or not obj.ViewObject:
                return
            
            self.logger.debug(f"ViewProvider ({name}): Change property {prop} status to ({status})")
            Object.setPropertyStatus(obj.ViewObject, prop, status)
            
        except Exception as e:
            self.logger.error(f"Setting property status failed: {e}")
     
    
    async def __cbCreateViewProviderDynProperty(self, name, prop, typeID, group, documentation, status):
        
        try:
            obj = self.onlineDoc.document.getObject(name)
            if obj is None:
                self.logger.error(f"ViewProvider ({name}): Should add dynamic property {prop} for not existing viewprovider")
                return
            
            self.logger.debug(f"ViewProvider ({name}): Add dynamic property {prop}")
            Object.createDynamicProperty(obj.ViewObject, prop, typeID, group, documentation, status)
            
        except Exception as e:
            self.logger.error("Dynamic propert adding failed: {0}".format(e))
        
    
    
    async def __cbCreateViewProviderDynProperties(self, name, props, infos):

        try:
            obj = self.onlineDoc.document.getObject(name)
            if obj is None:
                self.logger.error(f"ViewProvider ({name}): Should add dyn properties for not existing viewprovider {props}")
                return
            
            self.logger.debug(f"ViewProvider ({name}): Add dynamic properties {props}")
            
            for i in range(0, len(props)):
                info = infos[i]
                Object.createDynamicProperty(obj.ViewObject, props[i], info["typeid"], info["group"], info["docu"], info["status"])
                
        except Exception as e:
            self.logger.error("Dynamic properties adding failed: {0}".format(e))
            
    
    async def __cbRemoveViewProviderDynProperty(self, name, prop):
        
        try:
            obj = self.onlineDoc.document.getObject(name)
            if obj is None:
                self.logger.error(f"ViewProvider ({name}): Should remove dynamic property {prop} for not existing viewprovider")
                return
            
            self.logger.debug(f"ViewProvider ({name}): Remove dynamic property {prop}")
            Object.removeDynamicProperty(obj.ViewObject, prop)
        
        except Exception as e:
            self.logger.error(f"Dynamic property removing callback failed: {e.message}")
    

    async def __cbCreateViewProviderExtension(self, name, ext):
        
        try:
            obj = self.onlineDoc.document.getObject(name)
            if obj is None:
                self.logger.error(f"ViewProvider ({name}): Should create extension {ext} for not existing viewprovider")
                return
            
            self.logger.debug(f"ViewProvider ({name}): Create extension {ext}")
            Object.createExtension(obj.ViewObject, ext)
            
        except Exception as e:
            self.logger.error(f"Add extension failed: {e}")
    
    
    async def __cbRemoveViewProviderExtension(self, name, ext):
        
        try:
            obj = self.onlineDoc.document.getObject(name)
            if obj is None:
                self.logger.error(f"ViewProvider ({name}): Should remove extension {ext} for not existing object")
                return
            
            self.logger.debug(f"ViewProvider ({name}): Remove extension {ext}")
            Object.removeExtension(obj.ViewObject, ext)

        except Exception as e:
            self.logger.error(f"Remove extension failed: {e}")


    async def __cbViewProviderOnSetupFinished(self, name):
        #see object equivalent for explanaiton
        try:
            obj = self.onlineDoc.document.getObject(name).ViewObject
            self.logger.debug(f"ViewProvider ({name}): Finish Setup")
            if hasattr(obj, "Proxy") and hasattr(obj.Proxy, "onDocumentRestored"):
                with Observer.blocked(self.onlineDoc.document):
                    props = obj.PropertiesList
                    obj.Proxy.onDocumentRestored(obj)
                    newprops = set(obj.PropertiesList) - set(props)
                    
                    ovp = self.onlineDoc.viewproviders[name]
                    for prop in newprops:
                        ovp.createDynamicProperty(prop)
                        ovp.changeProperty(prop)
            
        except Exception as e:
            self.logger.error(f"Object ({name}): Version upgade after setup failed: {e}")
            
        finally:           
            Observer.activateFor(self.onlineDoc.document)


    async def __cbChangeDocProperty(self, name):
        print("Changed document property event")
     
     
     
    #Internal functions for the online oberser
    #******************************************************************************************************************************************************

    async def __getBinaryValues(self, values):
        #checks all values for binary Cid's and fetches the real data to replace it with
        
        if not isinstance(values, list):
            values = [values]
        
        tasks = []
        for index, value in enumerate(values):
            
            if isinstance(value, str) and value.startswith("ocp_cid"):                   
                
                async def worker(index, cid):
                    class Data():
                        def __init__(self): 
                            self.data = bytes()
                                    
                        def progress(self, update):
                            self.data += bytes(update)
                            
                    #get the binary data
                    uri = f"ocp.documents.{self.onlineDoc.id}.raw.BinaryByCid"
                    dat = Data()
                    opt = CallOptions(on_progress=dat.progress)
                    result = await self.onlineDoc.connection.api.call(uri, cid, options=opt)
                    if result is not None:
                        dat.progress(result)
                        
                    values[index] = dat.data
                    
                tasks.append(worker(index, value))
        
        if tasks:
            tasks = [asyncio.create_task(task) for task in tasks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            exceptions = [i for i in results if isinstance(i, Exception)]
            if exceptions:
                self.logger.error(f"Getting binary data from node failed: {exceptions[0]}")
                raise exceptions[0]
        
        if len(values) == 1:
            return values[0]
        return values


    async def __setProperty(self, obj, prop,  value, logentry):
        
        try:                      
            self.logger.debug(f"{logentry}: Set property {prop}")
            
            value = await self.__getBinaryValues(value)
            Object.setProperty(obj, prop, value)

        except Exception as e:
            self.logger.error(f"{logentry} Set property {prop} error: {e}")
    
    
    async def __setProperties(self, obj, props, values, logentry):
        
        try:      
            self.logger.debug(f"{logentry}: Set properties {props}")
            
            values = await self.__getBinaryValues(values)
            Object.setProperties(obj, props, values)
           
        except Exception as e:
            self.logger.error(f"{logentry} Set properties {props} error: {e}")

           
 

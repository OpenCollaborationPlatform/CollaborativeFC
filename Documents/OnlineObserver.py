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
import Documents.AsyncRunner    as AsyncRunner
import Documents.Helper         as Helper
from Documents.OnlineObject import OnlineObject
from Documents.OnlineObject import OnlineViewProvider
from autobahn.wamp.types    import SubscribeOptions, CallOptions
from autobahn.wamp          import ApplicationError

class OnlineObserver():
    
    def __init__(self, observer, odoc):
      
        self.docObserver = observer
        self.onlineDoc = odoc
        self.logger = logging.getLogger("Online observer " + odoc.id[-5:])
        self.runners = {}
        
        self.callbacks = {
                "Objects.onObjectCreated": self.__cbNewObject,
                "Objects.onObjectRemoved": self.__cbRemoveObject,
                "Objects..onObjectRecomputed": self.__cbObjectRecomputed,
                "Objects..onExtensionCreated": self.__cbCreateObjextExtension,
                "Objects..onExtensionRemoved": self.__cbRemoveObjextExtension,       
                "Objects...onDynamicPropertyCreated": self.__cbCreateObjectDynProperty,
                "Objects...onDynamicPropertiesCreated": self.__cbCreateObjectDynProperties,
                "Objects...onDynamicPropertyRemoved": self.__cbRemoveObjectDynProperty,
                "Objects...onDatasChanged": self.__cbChangeMultiObject,
                "Objects....onDataChanged": self.__cbChangeObject, 
                "Objects....onStatusChanged": self.__cbChangePropStatus,
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
            uri = f"ocp.documents.{odoc.id}.content.Document."
            
            for cb in self.callbacks.keys():
                odoc.connection.session.subscribe(self.__run, uri+cb, options=SubscribeOptions(match="wildcard", details_arg="details"))

            #odoc.connection.session.subscribe(self.__runDocProperties, uri+"Properties", options=SubscribeOptions(match="prefix", details_arg="details"))
           
        except Exception as e:
            self.logger.error("Setup failed: ", e)
              
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
            self.docObserver.deactivateFor(self.onlineDoc.document)
            obj = self.onlineDoc.document.addObject(typeID, name)
            oobj = OnlineObject(obj, self.onlineDoc)
            self.onlineDoc.objects[obj.Name] = oobj
            
            #create the online view provider for that object
            if obj.ViewObject:
                ovp = OnlineViewProvider(obj.ViewObject, oobj, self.onlineDoc)
                self.onlineDoc.viewproviders[obj.Name] = ovp
                       
            #remove touched status. could happen that other objects like origins have been created automatically
            for added in self.docObserver.createdObjectsWhileDeactivated(self.onlineDoc.document):
                if added.TypeId == "App::Origin":
                    added.recompute() #recompute origin to get viewprovider size correctly (auto updated without change callback)
                added.purgeTouched()
            
        except Exception as e:
            self.logger.error(f"Object ({name}): Add object online callback failed: {e}")
            
        finally:           
            self.docObserver.activateFor(self.onlineDoc.document)
    
    
    async def __cbRemoveObject(self, name):
        
        try:
            self.logger.debug(f"Object ({name}): Remove")
            
            #remove FC object first
            self.docObserver.deactivateFor(self.onlineDoc.document)
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
            
        finally:           
            self.docObserver.activateFor(self.onlineDoc.document)
        
        
    async def __cbChangeObject(self, name, prop, value):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
        
        await self.__setProperty(obj, name, prop, value, f"Object ({name})")
        
        
    async def __cbChangeMultiObject(self, name, props, values):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
        
        await self.__setProperties(obj, name, props, values, f"Object ({name})")
 
 
    async def __cbChangePropStatus(self, name, prop, status):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
        
        self.logger.debug(f"Object ({name}): Change property {prop} status to {status}")
        self.__setPropertyStatus(obj, prop, status)
 
 
    async def __cbCreateObjectDynProperty(self, name, prop, typeID, group, documentation, status):
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"Object ({name}): Should add dynamic property {prop} for not existing object")
            return
        
        self.logger.debug(f"Object ({name}): Create dynamic property {prop}")
        self.__createDynProperty(obj, prop, typeID, group, documentation, status)
        
    
    async def __cbCreateObjectDynProperties(self, name, props, infos):

        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"Object ({name}): Should add dynamic properties for not existing object: {props}")
            return
        
        self.logger.debug(f"Object ({name}): Create dynamic properties {props}")
        for i in range(0, len(props)):
            info = infos[i]
            self.__createDynProperty(obj, props[i], info["typeid"], info["group"], info["docu"], info["status"])
        
    
    
    async def __cbRemoveObjectDynProperty(self, name, prop):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"Object ({name}): Should remove dyn property {prop} for not existing object")
            return
        
        self.logger.debug(f"Object ({name}): Remove dynamic property {prop}")
        self.__removeDynProperty(obj, prop)

    
    async def __cbCreateObjextExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"Object ({name}): Should add extension for not existing object")
            return
        
        self.logger.debug(f"Object ({name}): Add extension {ext}")
        self.__createExtension(obj, ext)
    
    
    async def __cbRemoveObjextExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"Object ({name}): Should remove extension {ext} for not existing object")
            return
        
        self.logger.debug(f"Object ({name}): Remove extension {ext}")
        self.__removeExtension(obj, ext)
    
    
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
            
        
    async def __cbChangeViewProvider(self, name, prop, value):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
 
        await self.__setProperty(obj.ViewObject, name, prop, value, f"ViewProvider ({name})")
     
    
    async def __cbChangeMultiViewProdiver(self, name, props, values):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
               
        await self.__setProperties(obj.ViewObject, name, props, values, f"ViewProvider ({name})")
     
    
    async def __cbChangeViewProvierPropStatus(self, name, prop, status):
        
        obj = self.onlineDoc.document.getObject(name)
        if not obj or not obj.ViewObject:
            return
        
        self.logger.debug(f"ViewProvider ({name}): Change property {prop} status to ({status})")
        self.__setPropertyStatus(obj.ViewObject, prop, status)
     
    
    async def __cbCreateViewProviderDynProperty(self, name, prop, typeID, group, documentation, status):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"ViewProvider ({name}): Should add dynamic property {prop} for not existing viewprovider")
            return
        
        self.logger.debug(f"ViewProvider ({name}): Add dynamic property {prop}")
        self.__createDynProperty(obj.ViewObject, prop, typeID, group, documentation, status)
    
    
    async def __cbCreateViewProviderDynProperties(self, name, props, infos):

        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"ViewProvider ({name}): Should add dyn properties for not existing viewprovider {props}")
            return
        
        self.logger.debug(f"ViewProvider ({name}): Add dynamic properties {props}")
        
        for i in range(0, len(props)):
            info = infos[i]
            self.__createDynProperty(obj.ViewObject, props[i], info["typeid"], info["group"], info["docu"], info["status"])
            
    
    async def __cbRemoveViewProviderDynProperty(self, name, prop):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"ViewProvider ({name}): Should remove dynamic property {prop} for not existing viewprovider")
            return
        
        self.logger.debug(f"ViewProvider ({name}): Remove dynamic property {prop}")
        self.__removeDynProperty(obj.ViewObject, prop)    
    

    async def __cbCreateViewProviderExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"ViewProvider ({name}): Should create extension {ext} for not existing viewprovider")
            return
        
        self.logger.debug(f"ViewProvider ({name}): Create extension {ext}")
        self.__createExtension(obj.ViewObject, ext)
    
    
    async def __cbRemoveViewProviderExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"ViewProvider ({name}): Should remove extension {ext} for not existing object")
            return
        
        self.logger.debug(f"ViewProvider ({name}): Remove extension {ext}")
        self.__removeExtension(obj.ViewObject, ext)


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
                    result = await self.onlineDoc.connection.session.call(uri, cid, options=opt)
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


    async def __setProperty(self, obj, name, prop,  value, logentry):
        
        try:      
            if obj.isDerivedFrom("App::DocumentObject"):
                group = "Objects"
            else:
                group = "ViewProviders"
                
            #set it for the property
            self.docObserver.deactivateFor(self.onlineDoc.document)   
            self.logger.debug(f"{logentry}: Set property {prop}")
            
            value = await self.__getBinaryValues(value)
            Property.convertWampToProperty(obj, prop, value)

        except Exception as e:
            self.logger.error(f"{logentry} Set property {prop} error: {e}")

        finally:            
            self.docObserver.activateFor(self.onlineDoc.document)
            
            if hasattr(obj, "purgeTouched"):
                obj.purgeTouched()
    
    
    async def __setProperties(self, obj, name, props, values, logentry):
        
        try:      
            self.logger.debug(f"{logentry}: Set properties {props}")
            if obj.isDerivedFrom("App::DocumentObject"):
                group = "Objects"
            else:
                group = "ViewProviders"

            #set all values
            self.docObserver.deactivateFor(self.onlineDoc.document)   
            
            values = await self.__getBinaryValues(values)
            
            failed = []
            for index, prop in enumerate(props):
                Property.convertWampToProperty(obj, prop, values[index])
           
        except Exception as e:
            self.logger.error(f"{logentry} Set properties {props} error: {e}")

        finally:            
            self.docObserver.activateFor(self.onlineDoc.document)
            
            if hasattr(obj, "purgeTouched"):
                obj.purgeTouched()
           
    
    def __createDynProperty(self, obj, prop, typeID, group, documentation, status):
        
        try: 
            if hasattr(obj, prop):
                return
                
            self.docObserver.deactivateFor(self.onlineDoc.document)
            
            attributes = Property.statusToType(status)            
            obj.addProperty(typeID, prop, group, documentation, attributes)
            
            if float(".".join(FreeCAD.Version()[0:2])) >= 0.19:
                obj.setPropertyStatus(prop, status)
            else:
                mode = Property.statusToEditorMode(status)
                if mode:
                    obj.setEditorMode(prop, mode)
        
        
        except Exception as e:
            self.logger.error("Dynamic property adding failed: {0}".format(e))
            traceback.print_exc()
            
        finally:
            self.docObserver.activateFor(self.onlineDoc.document)
            if hasattr(obj, "purgeTouched"):
                obj.purgeTouched()
    
    
    def __removeDynProperty(self, obj, prop):
        
        try: 
            if not hasattr(obj, prop):
                return
                    
            self.docObserver.deactivateFor(self.onlineDoc.document)
            obj.removeProperty(prop)
            
        except Exception as e:
            self.logger.error(f"Dyn property removing callback failed: {e.message}")
            
        finally:
            self.docObserver.activateFor(self.onlineDoc.document)
            if hasattr(obj, "purgeTouched"):
                obj.purgeTouched()
            
    
    def __createExtension(self, obj, ext):
        
        try:
            if obj.hasExtension(ext):
                return
    
            self.docObserver.deactivateFor(self.onlineDoc.document)

            if  float(".".join(FreeCAD.Version()[0:2])) >= 0.19:
                obj.addExtension(ext)
            else:
                obj.addExtension(ext, None)
            
        except Exception as e:
            self.logger.error("Add extension callback failed: ", e)
            
        finally:
            self.docObserver.activateFor(self.onlineDoc.document)
            if hasattr(obj, "purgeTouched"):
                obj.purgeTouched()
    
    
    def __removeExtension(self, obj, ext):
              
        try:
            if not obj.hasExtension(ext):
                return
        
            self.docObserver.deactivateFor(self.onlineDoc.document)
            obj.removeExtension(ext, None)
            
        except Exception as e:
            self.logger.error("Remove extension callback failed: ", e)
            
        finally:
            self.docObserver.activateFor(self.onlineDoc.document)
            if hasattr(obj, "purgeTouched"):
                obj.purgeTouched()


    def __setPropertyStatus(self, obj, prop, status):

        try:
            self.docObserver.deactivateFor(self.onlineDoc.document)
            
            if  float(".".join(FreeCAD.Version()[0:2])) >= 0.19:
                #to set the status multiple things need to happen:
                # 1. remove all string status entries we do not support
                supported = obj.getPropertyStatus()
                filterd = [s for s in status if not isinstance(s, str) or s in supported]

                # 2. check which are to be added, and add those
                current = obj.getPropertyStatus(prop)
                add = [s for s in filterd if not s in current]
                obj.setPropertyStatus(prop, add)
                
                # 3. check which are to be removed, and remove those
                remove = [s for s in current if not s in filterd]
                signed = [-s for s in remove if isinstance(s, int) ]
                signed += ["-"+s for s in remove if isinstance(s, str) ]
                obj.setPropertyStatus(prop, signed)                
            
            else:
                obj.setEditorMode(prop, Property.statusToEditorMode(status))
        
        finally:            
            self.docObserver.activateFor(self.onlineDoc.document)
            if hasattr(obj, "purgeTouched"):
                obj.purgeTouched()

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
import Documents.Property as Property
import Documents.AsyncRunner as AsyncRunner
from Documents.OnlineObject import OnlineObject
from Documents.OnlineObject import OnlineViewProvider
from autobahn.wamp.types    import SubscribeOptions, CallOptions

class OnlineObserver():
    
    def __init__(self, observer, odoc):
      
        self.docObserver = observer
        self.onlineDoc = odoc
        self.logger = logging.getLogger("Online observer " + odoc.id[-5:])
        self.runners = {}
        
        self.callbacks = {
                "Objects.onObjectCreated": self.__newObject,
                "Objects.onObjectRemoved": self.__removeObject,
                "Objects..onObjectRecomputed": self.__objectRecomputed,
                "Objects..onExtensionCreated": self.__createObjextExtension,
                "Objects..onExtensionRemoved": self.__removeObjextExtension,       
                "Objects...onDynamicPropertyCreated": self.__createObjectDynProperty,
                "Objects...onDynamicPropertiesCreated": self.__createObjectDynProperties,
                "Objects...onDynamicPropertyRemoved": self.__removeObjectDynProperty,
                "Objects...onDatasChanged": self.__changeMultiObject,
                "Objects....onDataChanged": self.__changeObject, 
                "Objects....onStatusChanged": self.__changePropStatus,
                "ViewProviders..onExtensionCreated": self.__createViewProviderExtension,
                "ViewProviders..onExtensionRemoved": self.__removeViewProviderExtension,
                "ViewProviders...onDynamicPropertyCreated": self.__createViewProviderDynProperty,
                "ViewProviders...onDynamicPropertiesCreated": self.__createViewProviderDynProperties,
                "ViewProviders...onDynamicPropertyRemoved": self.__removeViewProviderDynProperty,
                "ViewProviders...onDatasChanged": self.__changeMultiViewProdiver,
                "ViewProviders....onDataChanged": self.__changeViewProvider,
                "ViewProviders....onStatusChanged": self.__changeViewProvierPropStatus,                
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
        AsyncRunner.DocumentOrderedRunner.getSenderRunner(self.onlineDoc.id, self.logger).run(fnc, *args)
            

    def getRunner(self, name):
        
        if not name in self.runners:
            if self.synced:
                self.runners[name] = AsyncRunner.DocumentOrderedRunner.getSenderRunner(self.onlineDoc.id, self.logger)
            else:
                self.runners[name] = AsyncRunner.OrderedRunner(self.logger)
                
        return self.runners[name]

    async def waitTillCloseout(self, timeout = 10):
        coros = []
        for runner in self.runners:
            coros.append(self.runners[runner].waitTillCloseout(timeout))
            
        if coros:
            await asyncio.wait(coros)

        
    async def __newObject(self, name, typeID):
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
            
            obj.purgeTouched()
            
        except Exception as e:
            self.logger.error(f"Object ({name}): Add object online callback failed: {e}")
            
        finally:           
            self.docObserver.activateFor(self.onlineDoc.document)
    
    
    async def __removeObject(self, name):
        try:
            self.logger.debug(f"Object ({name}): Remove")
            
            self.docObserver.deactivateFor(self.onlineDoc.document)
            self.onlineDoc.document.removeObject(name)
            del(self.onlineDoc.objects[name])
            
        except Exception as e:
            self.logger.error(f"Object ({name}): Remove object online callback failed: {e}")
            
        finally:           
            self.docObserver.activateFor(self.onlineDoc.document)
        
        
    async def __changeObject(self, name, prop):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
        
        await self.__setProperty(obj, name, prop, f"Object ({name})")
        
        
    async def __changeMultiObject(self, name, props):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
        
        await self.__setProperties(obj, name, props, f"Object ({name})")
 
 
    async def __changePropStatus(self, name, prop, status):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
        
        self.logger.debug(f"Object ({name}): Change property {prop} status to {status}")
        self.__setPropertyStatus(obj, prop, status)
 
 
    async def __createObjectDynProperty(self, name, prop, typeID, group, documentation, status):
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"Object ({name}): Should add dynamic property {prop} for not existing object")
            return
        
        self.logger.debug(f"Object ({name}): Create dynamic property {prop}")
        self.__createDynProperty(obj, prop, typeID, group, documentation, status)
        
    
    async def __createObjectDynProperties(self, name, props, infos):

        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"Object ({name}): Should add dynamic properties for not existing object: {props}")
            return
        
        self.logger.debug(f"Object ({name}): Create dynamic properties {props}")
        for i in range(0, len(props)):
            info = infos[i]
            self.__createDynProperty(obj, props[i], info["typeid"], info["group"], info["docu"], info["status"])
        
    
    
    async def __removeObjectDynProperty(self, name, prop):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"Object ({name}): Should remove dyn property {prop} for not existing object")
            return
        
        self.logger.debug(f"Object ({name}): Remove dynamic property {prop}")
        self.__removeDynProperty(obj, prop)

    
    async def __createObjextExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"Object ({name}): Should add extension for not existing object")
            return
        
        self.logger.debug(f"Object ({name}): Add extension {ext}")
        self.__createExtension(obj, ext)
    
    
    async def __removeObjextExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"Object ({name}): Should remove extension {ext} for not existing object")
            return
        
        self.logger.debug(f"Object ({name}): Remove extension {ext}")
        self.__removeExtension(obj, ext)
    
    
    async def __objectRecomputed(self, name):
        
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
            
        
    async def __changeViewProvider(self, name, prop):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
 
        await self.__setProperty(obj.ViewObject, name, prop, f"ViewProvider ({name})")
     
    
    async def __changeMultiViewProdiver(self, name, props):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
               
        await self.__setProperties(obj.ViewObject, name, props, f"ViewProvider ({name})")
     
    
    async def __changeViewProvierPropStatus(self, name, prop, status):
        
        obj = self.onlineDoc.document.getObject(name)
        if not obj or not obj.ViewObject:
            return
        
        self.logger.debug(f"ViewProvider ({name}): Change property {prop} status to ({status})")
        self.__setPropertyStatus(obj.ViewObject, prop, status)
     
    
    async def __createViewProviderDynProperty(self, name, prop, typeID, group, documentation, status):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"ViewProvider ({name}): Should add dynamic property {prop} for not existing viewprovider")
            return
        
        self.logger.debug(f"ViewProvider ({name}): Change property {prop}")
        self.__createDynProperty(obj.ViewObject, prop, typeID, group, documentation, status)
    
    
    async def __createViewProviderDynProperties(self, name, props, infos):

        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"ViewProvider ({name}): Should add dyn properties for not existing viewprovider {props}")
            return
        
        self.logger.debug(f"ViewProvider ({name}): Add dynamic properties {props}")
        
        for i in range(0, len(props)):
            info = infos[i]
            self.__createDynProperty(obj.ViewObject, props[i], info["typeid"], info["group"], info["docu"], info["status"])
            
    
    async def __removeViewProviderDynProperty(self, name, prop):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"ViewProvider ({name}): Should remove dynamic property {prop} for not existing viewprovider")
            return
        
        self.logger.debug(f"ViewProvider ({name}): Remove dynamic property {prop}")
        self.__removeDynProperty(obj.ViewObject, prop)    
    

    async def __createViewProviderExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"ViewProvider ({name}): Should create extension {ext} for not existing viewprovider")
            return
        
        self.logger.debug(f"ViewProvider ({name}): Create extension {ext}")
        self.__createExtension(obj.ViewObject, ext)
    
    
    async def __removeViewProviderExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error(f"ViewProvider ({name}): Should remove extension {ext} for not existing object")
            return
        
        self.logger.debug(f"ViewProvider ({name}): Remove extension {ext}")
        self.__removeExtension(obj.ViewObject, ext)


    async def __changeDocProperty(self, name):
        print("Changed document property event")
        

    async def __getPropertyValue(self, group, objname, prop):
        
        uri = u"ocp.documents.{0}.content.Document.{1}.".format(self.onlineDoc.id, group)
        calluri = uri + f"{objname}.Properties.{prop}.GetValue"
        val = await self.onlineDoc.connection.session.call(calluri)
        binary =  isinstance(val, str) and val.startswith("ocp_cid")

        if binary:                    
            class Data():
                def __init__(self): 
                    self.data = bytes()
                            
                def progress(self, update):
                    self.data += bytes(update)
                    
            #get the binary data
            uri = f"ocp.documents.{self.onlineDoc.id}.raw.BinaryByCid"
            dat = Data()
            opt = CallOptions(on_progress=dat.progress)
            val = await self.onlineDoc.connection.session.call(uri, val, options=opt)
            if val is not None:
                dat.progress(val)
                    
            return dat.data
        
        else:
            return val


    async def __setProperty(self, obj, name, prop, logentry):
        
        try:      
            if obj.isDerivedFrom("App::DocumentObject"):
                group = "Objects"
            else:
                group = "ViewProviders"
                
            value = await self.__getPropertyValue(group, name, prop)
                
            #set it for the property
            self.docObserver.deactivateFor(self.onlineDoc.document)   
            self.logger.debug(f"{logentry}: Set property {prop}")
            Property.convertWampToProperty(obj, prop, value)

        except Exception as e:
            self.logger.error(f"{logentry} Set property {prop} error: {e}")

        finally:            
            self.docObserver.activateFor(self.onlineDoc.document)
            
            if hasattr(obj, "purgeTouched"):
                obj.purgeTouched()
    
    
    async def __setProperties(self, obj, name, props, logentry):
        
        try:      
            self.logger.debug(f"{logentry}: Set properties {props}")
            if obj.isDerivedFrom("App::DocumentObject"):
                group = "Objects"
            else:
                group = "ViewProviders"
                
            uri = u"ocp.documents.{0}.content.Document.{1}.".format(self.onlineDoc.id, group)
                        
            #get all the values of the properties
            tasks = []
            values = {}
            for prop in props:
                        
                async def  run(results, group, name, prop):
                    try:
                        val = await self.__getPropertyValue(group, name, prop)
                        results[prop] = val
                    except Exception as e:
                        pass
                    
                tasks.append(run(values, group, name, prop))
                
            if tasks:
                await asyncio.wait(tasks)

            #set all values
            self.docObserver.deactivateFor(self.onlineDoc.document)   
            failed = []
            for prop  in props:
                if prop in values:
                    Property.convertWampToProperty(obj, prop, values[prop])
                else:
                    failed.append(prop)
                    
            if failed:
                raise Exception(f"Properties {failed} failed")

        except Exception as e:
            self.logger.error(f"{logentry} Set properties {props} error: {e}")

        finally:            
            self.docObserver.activateFor(self.onlineDoc.document)
            
            if hasattr(obj, "purgeTouched"):
                obj.purgeTouched()
           
    
    def __createDynProperty(self, obj, prop, typeID, group, documentation, status):
        
        if hasattr(obj, prop):
            return
        
        try:                 
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
        
        if not hasattr(obj, prop):
            return
        
        try:                   
            self.docObserver.deactivateFor(self.onlineDoc.document)
            obj.removeProperty(prop)
            
        except Exception as e:
            self.logger.error("Dyn property removing callback failed: ", e)
            
        finally:
            self.docObserver.activateFor(self.onlineDoc.document)
            if hasattr(obj, "purgeTouched"):
                obj.purgeTouched()
            
    
    def __createExtension(self, obj, ext):
        
        if obj.hasExtension(ext):
            return
        
        try:      
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
              
        if not obj.hasExtension(ext):
            return
        
        try:      
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

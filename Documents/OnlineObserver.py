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

import FreeCAD, logging, os
import Documents.Property as Property
import Documents.AsyncRunner as AsyncRunner
from Documents.OnlineObject import OnlineObject
from autobahn.wamp.types    import SubscribeOptions, CallOptions

class OnlineObserver():
    
    def __init__(self, observer, odoc):
      
        self.docObserver = observer
        self.onlineDoc = odoc
        self.logger = logging.getLogger("Online observer " + odoc.id[-5:])
        
        self.callbacks = {
                "Objects.onCreated": self.__newObject,
                "Objects.onRemoved": self.__removeObject, 
                "Objects.onPropChanged": self.__changeObject, 
                "Objects.onPropStatusChanged": self.__changePropStatus,
                "Objects.onDynamicPropertyCreated": self.__createObjectDynProperty,
                "Objects.onDynamicPropertiesCreated": self.__createObjectDynProperties,
                "Objects.onDynamicPropertyRemoved": self.__removeObjectDynProperty,
                "Objects.onExtensionCreated": self.__createObjextExtension,
                "Objects.onExtensionRemoved": self.__removeObjextExtension,
                "Objects.onObjectRecomputed": self.__objectRecomputed,
                
                "ViewProviders.onPropChanged": self.__changeViewProvider,
                "ViewProviders.onPropStatusChanged": self.__changeViewProvierPropStatus,
                "ViewProviders.onDynamicPropertyCreated": self.__createViewProviderDynProperty,
                "ViewProviders.onDynamicPropertiesCreated": self.__createViewProviderDynProperties,
                "ViewProviders.onDynamicPropertyRemoved": self.__removeViewProviderDynProperty,
                "ViewProviders.onExtensionCreated": self.__createViewProviderExtension,
                "ViewProviders.onExtensionRemoved": self.__removeViewProviderExtension,
                
                "Properties.onChangedProperty": self.__changeDocProperty
            }
        
        if os.getenv('FC_OCP_SYNC_MODE', "0") == "1":
            self.synced = True
        else:
            self.synced = False
        
        try:
            uri = f"ocp.documents.edit.{odoc.id}.events.Document."
            
            #we do not prefix subscribe to uri only as this catches all events on document level, also those we do not handle here
            odoc.connection.session.subscribe(self.__run, uri+"Objects", options=SubscribeOptions(match="prefix", details_arg="details"))
            odoc.connection.session.subscribe(self.__run, uri+"ViewProviders", options=SubscribeOptions(match="prefix", details_arg="details"))
            odoc.connection.session.subscribe(self.__run, uri+"Properties", options=SubscribeOptions(match="prefix", details_arg="details"))
           
        except Exception as e:
            self.logger.error("Setup failed: ", e)
        
    async def __run(self, *args, details=None):
    
        key = ('.').join(details.topic.split(".")[-2:])
        if not key in self.callbacks:
            return

        fnc = self.callbacks[key]
        AsyncRunner.DocumentOrderedRunner.getSenderRunner(self.onlineDoc.id).run(fnc, *args)

        
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
               
        #property changes need to be partially synced:
        # as the node needs to be called for values (or even binary data) it takes a while and the call is async.
        # However, things like Proxy need to be set in the correct order, as this triggers certain setups like "attach".
        # Without that other property changes may not have the correct object state 
        #if "PropertyPythonObject" in obj.getTypeIdOfProperty(prop):
        #    self.onlineDoc.objects[name].sender.runAsyncAsSetup(self.__setProperty(obj, name, prop, f"Object ({name})"))
        #else:
        #    self.onlineDoc.objects[name].sender.runAsync(self.__setProperty(obj, name, prop, f"Object ({name})"))
        await self.__setProperty(obj, name, prop, f"Object ({name})")
 
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
               
        #see __changeObject for explanation
        #if "PropertyPythonObject" in obj.ViewObject.getTypeIdOfProperty(prop):
        #    self.onlineDoc.objects[name].sender.runAsyncAsSetup(self.__setProperty(obj.ViewObject, name, prop, f"ViewProvider ({name})"))
        #else:
        #    self.onlineDoc.objects[name].sender.runAsync(self.__setProperty(obj.ViewObject, name, prop, f"ViewProvider ({name})"))
        await self.__setProperty(obj.ViewObject, name, prop, f"ViewProvider ({name})")
     
    
    async def __changeViewProvierPropStatus(self, name, prop, status):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
        
        self.logger.debug(f"ViewProvider ({name}): Change property {prop} status to ({status})")
        self.__setPropertyStatus(obj.ViewObject, name, prop, status)
     
    
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
        

    async def __setProperty(self, obj, name, prop, logentry):
        
        try:      
            if obj.isDerivedFrom("App::DocumentObject"):
                group = "Objects"
            else:
                group = "ViewProviders"
                
            uri = u"ocp.documents.edit.{0}.call.Document.{1}.".format(self.onlineDoc.id, group)
                        
            calluri = uri + f"{name}.Properties.{prop}.IsBinary"
            binary = await self.onlineDoc.connection.session.call(calluri)
            
            calluri = uri + f"{name}.Properties.{prop}.GetValue"
            val = await self.onlineDoc.connection.session.call(calluri)
                       
            if binary:
                
                class Data():
                    def __init__(self): 
                        self.data = bytes()
                        
                    def progress(self, update):
                        self.data += bytes(update)
                
                #get the binary data
                uri = f"ocp.documents.edit.{self.onlineDoc.id}.rawdata.BinaryByCid"
                dat = Data()
                opt = CallOptions(on_progress=dat.progress)
                val = await self.onlineDoc.connection.session.call(uri, val, options=opt)
                if val is not None:
                    dat.progress(val)
                
                #set it for the property
                self.docObserver.deactivateFor(self.onlineDoc.document)   
                self.logger.debug(f"{logentry}: Set binary property {prop}")
                Property.convertWampToProperty(obj, prop, dat.data)
                                
            else:
                self.docObserver.deactivateFor(self.onlineDoc.document)
                self.logger.debug(f"{logentry}: Set property {prop} with {val}")
                Property.convertWampToProperty(obj, prop, val)

        except Exception as e:
            self.logger.error(f"{logentry} Set property {prop} error: {e}")

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
                obj.setPropertyStatus(prop, Property.statusToIntList(status))
            else:
                mode = Property.statusToEditorMode(status)
                if len(mode) > 0:
                    obj.setEditorMode(prop, mode)
        
        
        except Exception as e:
            self.logger.error("Dynamic property adding failed: {0}".format(e))
            
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
        
        if not hasattr(obj, prop):
            return
        
        try:
            self.docObserver.deactivateFor(self.onlineDoc.document)
            
            if  float(".".join(FreeCAD.Version()[0:2])) >= 0.19:
                obj.setPropertyStatus(prop, Property.statusToList(status))
            
            else:
                obj.setEditorMode(prop, Property.statusToEditorMode(status))
        
        finally:
            
            self.docObserver.activateFor(self.onlineDoc.document)
            if hasattr(obj, "purgeTouched"):
                obj.purgeTouched()

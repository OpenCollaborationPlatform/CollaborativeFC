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

import FreeCAD, logging
import Documents.Property as Property
from Documents.OnlineObject import OnlineObject
from autobahn.wamp.types    import CallOptions

class OnlineObserver():
    
    def __init__(self, observer, odoc):
      
        self.docObserver = observer
        self.onlineDoc = odoc
        self.logger = logging.getLogger("Online observer " + odoc.id[-5:])
        
        try:
            #setup all events we listen on!    
            uri = u"ocp.documents.edit.{0}.events.".format(odoc.id)
            odoc.connection.session.subscribe(self.__newObject, uri+"Document.Objects.onCreated")
            odoc.connection.session.subscribe(self.__removeObject, uri+"Document.Objects.onRemoved")
            odoc.connection.session.subscribe(self.__changeObject, uri+"Document.Objects.onPropChanged")
            odoc.connection.session.subscribe(self.__createObjectDynProperty, uri+"Document.Objects.onDynamicPropertyCreated")
            odoc.connection.session.subscribe(self.__createObjectDynProperties, uri+"Document.Objects.onDynamicPropertiesCreated")
            odoc.connection.session.subscribe(self.__removeObjectDynProperty, uri+"Document.Objects.onDynamicPropertyRemoved")
            odoc.connection.session.subscribe(self.__createObjextExtension, uri+"Document.Objects.onExtensionCreated")
            odoc.connection.session.subscribe(self.__removeObjextExtension, uri+"Document.Objects.onExtensionRemoved")
            odoc.connection.session.subscribe(self.__objectRecomputed, uri+"Document.Objects.onObjectRecomputed")
            
            odoc.connection.session.subscribe(self.__changeViewProvider, uri+"Document.ViewProviders.onPropChanged")
            odoc.connection.session.subscribe(self.__createViewProviderDynProperty,   uri+"Document.ViewProviders.onDynamicPropertyCreated")
            odoc.connection.session.subscribe(self.__createViewProviderDynProperties, uri+"Document.ViewProviders.onDynamicPropertiesCreated")
            odoc.connection.session.subscribe(self.__removeViewProviderDynProperty, uri+"Document.ViewProviders.onDynamicPropertyRemoved")
            odoc.connection.session.subscribe(self.__createViewProviderExtension, uri+"Document.ViewProviders.onExtensionCreated")
            odoc.connection.session.subscribe(self.__removeViewProviderExtension, uri+"Document.ViewProviders.onExtensionRemoved")
            
            odoc.connection.session.subscribe(self.__changeDocProperty, uri+"Document.Properties.onChangedProperty")
            
        except Exception as e:
            self.logger.error("Setup failed: ", e)
        
        
    def __newObject(self, name, typeID):
        try:
            self.logger.debug("Object: New {0} ({1})".format(name, typeID))
            
            #maybe the object exists already (e.g. auto created by annother added object like App::Part Origin)
            if hasattr(self.onlineDoc.document, name):
                return
            
            #we do not add App origins, lines and planes, as they are only Autocreated from parts and bodie
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
            self.logger.error("Add object online callback failed: {0}".format(e))
            
        finally:           
            self.docObserver.activateFor(self.onlineDoc.document)
    
    
    def __removeObject(self, name):
        try:
            self.logger.debug("Object: Remove {0}".format(name))
            
            self.docObserver.deactivateFor(self.onlineDoc.document)
            self.onlineDoc.document.removeObject(name)
            del(self.onlineDoc[name])
            
        except Exception as e:
            self.logger.error("Remove object online callback failed: {0}".format(e))
            
        finally:           
            self.docObserver.activateFor(self.onlineDoc.document)
        
        
    async def __changeObject(self, name, prop):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
        
        self.logger.debug("Object: Change {0} property {1}".format(name, prop))
        await self.__readProperty(obj, name, prop)
 
 
    def __createObjectDynProperty(self, name, prop, ptype, typeID, group, documentation):
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error("Should add dynamic property {0} for not existing object {1}".format(prop, name))
            return
        
        self.logger.debug("Object: Create dynamic property in {0}: {1}".format(name, prop))
        self.__createDynProperty(obj, prop, ptype, typeID, group, documentation)
        
    
    def __createObjectDynProperties(self, name, props, infos):

        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error("Should add dynamic properties for not existing object {1}: {0}".format(props, name))
            return
        
        self.logger.debug("Object: Create dynamic properties in {0}: {1}".format(name, props))
        for i in range(0, len(props)):
            info = infos[i]
            self.__createDynProperty(obj, props[i], info["ptype"], info["typeid"], info["group"], info["docu"])
        
    
    
    def __removeObjectDynProperty(self, name, prop):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error("Should remove dyn property {0} for not existing object {1}".format(prop, name))
            return
        
        self.logger.debug("Object: Remove dynamic property {0} in {1}".format(prop, name))
        self.__removeDynProperty(obj, prop)

    
    def __createObjextExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error("Should add extension for not existing object")
            return
        
        self.logger.debug("Object: Add extension {0} to {1}".format(ext, name))
        self.__createExtension(obj, ext)
    
    
    def __removeObjextExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error("Should remove extension {0} for not existing object {1}".format(ext, name))
            return
        
        self.logger.debug("Object: Remove extension {0} from {1}".format(ext, name))
        self.__removeExtension(obj, ext)
    
    
    def __objectRecomputed(self, name):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error("Recomputed object {0} does not exist".format(name))
            return
        
        self.logger.debug("Object: Recompute {0} finished".format(name))
        
        #we try to fix some known problems
        if obj.isDerivedFrom("Sketcher::SketchObject"):
            #we need to reassign geometry to fix the invalid sketch
            obj.Geometry = obj.Geometry
            
        
    async def __changeViewProvider(self, name, prop):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
        
        self.logger.debug("ViewProvider: Change {0} property {1}".format(name, prop))
        await self.__readProperty(obj.ViewObject, name, prop)
        
    
    def __createViewProviderDynProperty(self, name, prop, ptype, typeID, group, documentation):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error("Should add dynamic property {0} for not existing viewprovider {1}".format(prop, name))
            return
        
        self.logger.debug("ViewProvider: Change {0} property {0}".format(name, prop))
        self.__createDynProperty(obj.ViewObject, prop, ptype, typeID, group, documentation)
    
    
    def __createViewProviderDynProperties(self, name, props, infos):

        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error("Should add dyn properties for not existing viewprovider {0}: {1}".format(name, props))
            return
        
        self.logger.debug("ViewProvider: Add dynamic properties to {0}: {1}".format(name, props))
        
        for i in range(0, len(props)):
            info = infos[i]
            self.__createDynProperty(obj.ViewObject, props[i], info["ptype"], info["typeid"], info["group"], info["docu"])
            
    
    def __removeViewProviderDynProperty(self, name, prop):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error("Should remove dynamic property {0} for not existing viewprovider {1}".format(prop, name))
            return
        
        self.logger.debug("ViewProvider: Remove dynamic property {0} from {1}".format(prop, name))
        self.__removeDynProperty(obj.ViewObject, prop)
    
    

    def __createViewProviderExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error("Should create extension {0} for not existing viewprovider {1}".format(ext, name))
            return
        
        self.logger.debug("ViewProvider: Create extension {0} in {1}".format(ext, name))
        self.__createExtension(obj.ViewObject, ext)
    
    
    def __removeViewProviderExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            self.logger.error("Should remove extension {0} for not existing object {1}".format(ext, name))
            return
        
        self.logger.debug("ViewProvider: Remove extension {0} in {1}".format(ext, name))
        self.__removeExtension(obj.ViewObject, ext)


    def __changeDocProperty(self, name):
        print("Cahnged document property event")
        

    async def __readProperty(self, obj, name, prop):
        
        try:      
            if obj.isDerivedFrom("App::DocumentObject"):
                group = "Objects"
            else:
                group = "ViewProviders"
                
            uri = u"ocp.documents.edit.{0}.call.Document.{1}.".format(self.onlineDoc.id, group)
            
            calluri = uri + "{0}.Properties.{1}.IsBinary".format(name, prop)
            binary = await self.onlineDoc.connection.session.call(calluri)
            
            calluri = uri + "{0}.Properties.{1}.GetValue".format(name, prop)
            val = await self.onlineDoc.connection.session.call(calluri)
                       
            if binary:
                
                class Data():
                    def __init__(self): 
                        self.data = bytes()
                        
                    def progress(self, update):
                        self.data += bytes(update)
                
                #get the binary data
                uri = u"ocp.documents.edit.{0}.rawdata.".format(self.onlineDoc.id)
                dat = Data()
                opt = CallOptions(on_progress=dat.progress)
                val = await self.onlineDoc.connection.session.call(uri + "{0}.ReadBinary".format(val), options=opt)
                if val is not None:
                    dat.progress(val)
                
                #set it for the property
                self.docObserver.deactivateFor(self.onlineDoc.document)   
                Property.convertWampToProperty(obj, prop, dat.data)
                
            else:
                self.docObserver.deactivateFor(self.onlineDoc.document)
                Property.convertWampToProperty(obj, prop, val)

        except Exception as e:
            self.logger.error("Read property {0} error: {1}".format(prop, e))

        finally:
            self.docObserver.activateFor(self.onlineDoc.document)
            if hasattr(obj, "purgeTouched"):
                obj.purgeTouched()
            
    
    def __createDynProperty(self, obj, prop, ptype, typeID, group, documentation):
        
        if hasattr(obj, prop):
            return
        
        try:                 
            self.docObserver.deactivateFor(self.onlineDoc.document)
            obj.addProperty(typeID, prop, group, documentation)
            
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
            print("Dyn property removing callback failed: ", e)
            
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
            print("Add extension callback failed: ", e)
            
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
            print("Remove extension callback failed: ", e)
            
        finally:
            self.docObserver.activateFor(self.onlineDoc.document)
            if hasattr(obj, "purgeTouched"):
                obj.purgeTouched()

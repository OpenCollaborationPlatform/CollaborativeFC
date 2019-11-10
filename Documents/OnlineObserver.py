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

import FreeCAD
from Documents.OnlineObject import OnlineObject
from autobahn.wamp.types    import CallOptions

class OnlineObserver():
    
    def __init__(self, observer, odoc):
      
        self.docObserver = observer
        self.onlineDoc = odoc
        
        try:
            #setup all events we listen on!    
            uri = u"ocp.documents.edit.{0}.events.".format(odoc.id)
            odoc.connection.session.subscribe(self.__newObject, uri+"Document.Objects.onCreated")
            odoc.connection.session.subscribe(self.__removeObject, uri+"Document.Objects.onRemoved")
            odoc.connection.session.subscribe(self.__changeObject, uri+"Document.Objects.onPropChanged")
            odoc.connection.session.subscribe(self.__createObjectDynProperty, uri+"Document.Objects.onDynamicPropertyCreated")
            odoc.connection.session.subscribe(self.__removeObjectDynProperty, uri+"Document.Objects.onDynamicPropertyRemoved")
            odoc.connection.session.subscribe(self.__createObjextExtension, uri+"Document.Objects.onExtensionCreated")
            odoc.connection.session.subscribe(self.__removeObjextExtension, uri+"Document.Objects.onExtensionRemoved")
            
            odoc.connection.session.subscribe(self.__changeViewProvider, uri+"Document.ViewProviders.onPropChanged")
            odoc.connection.session.subscribe(self.__createViewProviderDynProperty, uri+"Document.ViewProviders.onDynamicPropertyCreated")
            odoc.connection.session.subscribe(self.__removeViewProviderDynProperty, uri+"Document.ViewProviders.onDynamicPropertyRemoved")
            odoc.connection.session.subscribe(self.__createViewProviderExtension, uri+"Document.ViewProviders.onExtensionCreated")
            odoc.connection.session.subscribe(self.__removeViewProviderExtension, uri+"Document.ViewProviders.onExtensionRemoved")
            
            odoc.connection.session.subscribe(self.__changeDocProperty, uri+"Document.Properties.onChangedProperty")
            
        except Exception as e:
            print("Setup of online observer failed: ", e)
        
        
    async def __newObject(self, name, typeID):
        try:
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
            
            #remove the objects we did not want and were created automatically!
            delObjs = self.docObserver.getInactiveCreatedDocObjects(self.onlineDoc.document)
            delObjs.remove(name)
            for remove in delObjs:
                self.onlineDoc.document.removeObject(remove)
            
            obj.purgeTouched()
            
        except Exception as e:
            print("Add object online callback failed: ", e)
            
        finally:           
            self.docObserver.activateFor(self.onlineDoc.document)
    
    
    async def __removeObject(self, name):
        try:
            self.docObserver.deactivateFor(self.onlineDoc.document)
            self.onlineDoc.document.removeObject(name)
            del(self.onlineDoc[name])
            
        except Exception as e:
            print("Remove object online callback failed: ", e)
            
        finally:           
            self.docObserver.activateFor(self.onlineDoc.document)
        
        
    async def __changeObject(self, name, prop):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
        
        await self.__readProperty(obj, name, prop)
 
 
    async def __createObjectDynProperty(self, name, prop, ptype, typeID, group, documentation):
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            print("Should add dyn property for not existing object")
            return
        
        await self.__createDynProperty(obj, name, prop, ptype, typeID, group, documentation)
    
    
    async def __removeObjectDynProperty(self, name, prop):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            print("Should remove dyn property for not existing object")
            return
        
        await self.__removeDynProperty(obj, prop)

    
    async def __createObjextExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            print("Should add extension for not existing object")
            return
        
        await self.__createExtension(obj, ext)
    
    
    async def __removeObjextExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            print("Should remove extension for not existing object")
            return
        
        await self.__removeExtension(obj, ext)
    
        
    async def __changeViewProvider(self, name, prop):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            return
        
        await self.__readProperty(obj.ViewObject, name, prop)
        
    
    async def __createViewProviderDynProperty(self, name, prop, ptype, typeID, group, documentation):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            print("Should add dyn property for not existing viewprovider")
            return
        
        await self.__createDynProperty(obj.ViewObject, name, prop, ptype, typeID, group, documentation)
    
    
    async def __removeViewProviderDynProperty(self, name, prop):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            print("Should remove dyn property for not existing viewprovider")
            return
        
        await self.__removeDynProperty(obj.ViewObject, prop)
    
    

    async def __createViewProviderExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            print("Should create extension for not existing viewprovider")
            return
        
        await self.__createExtension(obj.ViewObject, ext)
    
    
    async def __removeViewProviderExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            print("Should remove extension for not existing object")
            return
        
        await self.__removeExtension(obj.ViewObject, ext)


    async def __changeDocProperty(self, name):
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
                obj.restorePropertyContent(prop, dat.data)
                
            else:
                self.docObserver.deactivateFor(self.onlineDoc.document)
                setattr(obj, prop, val)

        except Exception as e:
            print("Read property error: ", e)

        finally:
            self.docObserver.activateFor(self.onlineDoc.document)
            if hasattr(obj, "purgeTouched"):
                obj.purgeTouched()
            
    
    async def __createDynProperty(self, obj, name, prop, ptype, typeID, group, documentation):
        
        if hasattr(obj, prop):
            return
        
        try:                 
            self.docObserver.deactivateFor(self.onlineDoc.document)
            obj.addProperty(typeID, prop, group, documentation)
            
        except Exception as e:
            print("Dyn property adding callback failed: ", e)
            
        finally:
            self.docObserver.activateFor(self.onlineDoc.document)
            if hasattr(obj, "purgeTouched"):
                obj.purgeTouched()
    
    
    async def __removeDynProperty(self, obj, prop):
        
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
            
    
    async def __createExtension(self, obj, ext):
        
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
    
    
    async def __removeExtension(self, obj, ext):
              
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

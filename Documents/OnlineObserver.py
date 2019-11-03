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
        
        #setup all events we listen on!    
        uri = u"ocp.documents.edit.{0}.events.".format(odoc.id)
        odoc.connection.session.subscribe(self.__newObject, uri+"Document.Objects.onCreated")
        odoc.connection.session.subscribe(self.__removeObject, uri+"Document.Objects.onRemoved")
        odoc.connection.session.subscribe(self.__changeObject, uri+"Document.Objects.onPropChanged")
        odoc.connection.session.subscribe(self.__createObjectDynProperty, uri+"Document.Objects.onDynamicPropertyCreated")
        odoc.connection.session.subscribe(self.__removeObjectDynProperty, uri+"Document.Objects.onDynamicPropertyRemoved")
        odoc.connection.session.subscribe(self.__createObjextExtension, uri+"Document.Objects.onExtensionCreated")
        odoc.connection.session.subscribe(self.__removeObjextExtension, uri+"Document.Objects.onExtensionRemoved")
        
        odoc.connection.session.subscribe(self.__newViewProvider, uri+"Document.ViewProviders.onCreated")
        odoc.connection.session.subscribe(self.__removeViewProvider, uri+"Document.ViewProviders.onRemoved")
        odoc.connection.session.subscribe(self.__changeViewProvider, uri+"Document.ViewProviders.onPropChanged")
        odoc.connection.session.subscribe(self.__createViewProviderDynProperty, uri+"Document.ViewProviders.onDynamicPropertyCreated")
        odoc.connection.session.subscribe(self.__removeViewProviderDynProperty, uri+"Document.ViewProviders.onDynamicPropertyRemoved")
        odoc.connection.session.subscribe(self.__createViewProviderExtension, uri+"Document.ViewProvider.onExtensionCreated")
        odoc.connection.session.subscribe(self.__removeViewProviderExtension, uri+"Document.ViewProvider.onExtensionRemoved")
        
        odoc.connection.session.subscribe(self.__changeDocProperty, uri+"Document.Properties.onChangedProperty")
        
        
    async def __newObject(self, name, typeID):
        try:
            print("New object " + name + " of type " + typeID)
            self.docObserver.deactivateFor(self.onlineDoc.document)
            obj = self.onlineDoc.document.addObject(typeID, name)
            
            oobj = OnlineObject(obj, self)
            self.onlineDoc.objects[obj.Name] = oobj
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
        
        try:      
            uri = u"ocp.documents.edit.{0}.call.".format(self.onlineDoc.id)
            
            calluri = uri + "Document.Objects.{0}.Properties.{1}.IsBinary".format(name, prop)
            binary = await self.onlineDoc.connection.session.call(calluri)
            
            calluri = uri + "Document.Objects.{0}.Properties.{1}.GetValue".format(name, prop)
            val = await self.onlineDoc.connection.session.call(calluri)
            
            print("Change object " + name + " prop " + prop)
            
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
                val = await self.onlineDoc.connection.session.call(uri + "Document.Objects.{0}.Properties.{1}.GetValue".format(name, prop))
                self.docObserver.deactivateFor(self.onlineDoc.document)
                setattr(obj, prop, val)

        except Exception as e:
            print("Online callback change object error: ", e)

        finally:
            self.docObserver.activateFor(self.onlineDoc.document)
            obj.purgeTouched()
 
 
    async def __createObjectDynProperty(self, name, prop):
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            print("Should add dyn property for not existing object")
            return
        
        try:      
            uri = u"ocp.documents.edit.{0}.call.".format(self.onlineDoc.id)
            calluri = uri + "Document.Objects.{0}.Properties.{1}.GetInfo".format(name, prop)
            info = await self.onlineDoc.connection.session.call(calluri)
            
            self.docObserver.deactivateFor(self.onlineDoc.document)
            obj.addProperty(info["id"], prop, info["group"], info["docu"])
            
        except Exception as e:
            print("Dyn property adding callback failed: ", e)
            
        finally:
            self.docObserver.activateFor(self.onlineDoc.document)
            obj.purgeTouched()
    
    
    async def __removeObjectDynProperty(self, name, prop):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            print("Should remove dyn property for not existing object")
            return
        
        try:      
            self.docObserver.deactivateFor(self.onlineDoc.document)
            obj.removeProperty(prop)
            
        except Exception as e:
            print("Dyn property removing callback failed: ", e)
            
        finally:
            self.docObserver.activateFor(self.onlineDoc.document)
            obj.purgeTouched()

    
    async def __createObjextExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            print("Should add extension for not existing object")
            return
        
        if obj.hasExtension(ext):
            return
        
        try:      
            self.docObserver.deactivateFor(self.onlineDoc.document)
            obj.addExtension(ext, None)
            
        except Exception as e:
            print("Add extension callback failed: ", e)
            
        finally:
            self.docObserver.activateFor(self.onlineDoc.document)
            obj.purgeTouched()
    
    
    async def __removeObjextExtension(self, name, ext):
        
        obj = self.onlineDoc.document.getObject(name)
        if obj is None:
            print("Should remove extension for not existing object")
            return
        
        if not obj.hasExtension(ext):
            return
        
        try:      
            self.docObserver.deactivateFor(self.onlineDoc.document)
            obj.removeExtension(ext, None)
            
        except Exception as e:
            print("Remove extension callback failed: ", e)
            
        finally:
            self.docObserver.activateFor(self.onlineDoc.document)
            obj.purgeTouched()
    
 
    async def __newViewProvider(self, name):
        print("New vp event received")
    
    
    async def __removeViewProvider(self, name):
        print("Removed vp event received")
        
        
    async def __changeViewProvider(self, name, prop):
        print("Changed vp event received")
        
    
    async def __createViewProviderDynProperty(self, name, prop):
        pass
    
    
    async def __removeViewProviderDynProperty(self, name, prop):
        pass
    
    
    async def __changeDocProperty(self, name):
        print("Cahnged vp property event")


    async def __createViewProviderExtension(self, name, ext):
        pass
    
    
    async def __removeViewProviderExtension(self, name, ext):
        pass

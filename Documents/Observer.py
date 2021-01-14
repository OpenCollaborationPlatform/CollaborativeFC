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

import asyncio
import FreeCAD, FreeCADGui

class ObserverManager():
    
    def __init__(self, uiobs, obs):
        self.obs = obs 
        self.uiobs = uiobs 
        
        
    def activateFor(self, doc):       
        self.obs.activateFor(doc)
        self.uiobs.activateFor(FreeCADGui.getDocument(doc.Name))        
        
        
    def deactivateFor(self, doc):
        self.obs.deactivateFor(doc)
        self.uiobs.deactivateFor(FreeCADGui.getDocument(doc.Name))  
    
    
class ObserverBase():
    
    __fc018_extensions = {"App::GroupExtensionPython": ["ExtensionProxy", "Group"], 
                          "App::GeoFeatureGroupExtensionPython": ["ExtensionProxy", "Group"],
                          "App::OriginGroupExtensionPython": ["ExtensionProxy", "Group", "Origin"],
                          "Gui::ViewProviderGeoFeatureGroupExtensionPython": ["ExtensionProxy"],
                          "Gui::ViewProviderGroupExtensionPython": ["ExtensionProxy"],
                          "Gui::ViewProviderOriginGroupExtensionPython": ["ExtensionProxy"],
                          "Part::AttachExtensionPython": ["ExtensionProxy", "AttacherType", "Support", "MapMode", "MapReversed", "MapPathParameter", "AttachmentOffset"],
                          "PartGui::ViewProviderAttachExtensionPython": ["ExtensionProxy"]}
    
    def __init__(self, handler):
        
        self.handler = handler
        self.inactive = []
        self.objExtensions = {}


    def activateFor(self, doc):
       
        while doc in self.inactive:
           self.inactive.remove(doc)
                
        
    def deactivateFor(self, doc):
        
        self.inactive.append(doc)
        
        
    def isDeactivatedFor(self, doc):
        
        if doc in self.inactive:
            return True 
        
        return False
    
    def fc018GetNewExtensions(self, obj):
        #this function checks if there are new extensions in the given object and returns them (or empty list if none are new)
        #if new ones are available it than saves the current state of extensions and compares to this new state next time its called. 
        #Note: works only for 0.18 as this checks only for 0.18 extensions!
        
        #make sure all objects have a list
        if not obj in self.objExtensions:
            self.objExtensions[obj] = []
            
        before = self.objExtensions[obj]
        
        now = []
        for extension in self.__fc018_extensions.keys():
            try: 
                if obj.hasExtension(extension):
                    now.append(extension)
            except:
                #it raises if no such exception is registered,  wht could happen if a module is not yet loaded
                continue
                           
        #get the new ones
        added = [item for item in now if item not in before]
        
        #store the current extensions
        self.objExtensions[obj] = now
        
        return added
    
    
    def fc018GetPropertiesForExtension(self, extension):
        #for freecad 0.18 it returns the properties a certain extension adds to a object
        return self.__fc018_extensions[extension]


class DocumentObserver(ObserverBase):
    
    def __init__(self, handler):
        super().__init__(handler)
        
    def slotCreatedDocument(self, doc):
        
        if self.isDeactivatedFor(doc):
            return
        
        #print("Observed new document")
        self.handler.onFCDocumentOpened(doc)
        

    def slotDeletedDocument(self, doc):
        
        if self.isDeactivatedFor(doc):
            return
        
        #print("Observer close document")
        self.handler.onFCDocumentClosed(doc)


    #def slotRelabelDocument(self, doc):
        #pass


    def slotCreatedObject(self, obj):
        
        doc = obj.Document
        if self.isDeactivatedFor(doc):
            return
        
        #print("Observer add document object ", obj.Name)  
        odoc = self.handler.getOnlineDocument(doc)
        if odoc:
            odoc.newObject(obj)


    def slotDeletedObject(self, obj):
        
        doc = obj.Document
        if self.isDeactivatedFor(doc):
            return
        
        #print("Observer remove document object ", obj.Name)        
        odoc = self.handler.getOnlineDocument(doc)
        if odoc:
            odoc.removeObject(obj)


    def slotChangedObject(self, obj, prop):
        
        doc = obj.Document
        if self.isDeactivatedFor(doc):
            return                
        
        #print("Observer changed document object ( ", obj.Name, ", ", prop, " ) into state ", obj.State)
        odoc = self.handler.getOnlineDocument(doc)
        if not odoc:
            return
            
        #0.18 workaround: get new extensions (in >=0.19 there are observer events for that)
        if float(".".join(FreeCAD.Version()[0:2])) == 0.18:
            added = self.fc018GetNewExtensions(obj)
            for extension in added:
                props = self.fc018GetPropertiesForExtension(extension)
                odoc.addDynamicExtension(obj, extension, props)
            
        #finally call change object!
        odoc.changeObject(obj, prop)


    def slotAppendDynamicProperty(self, obj, prop):    
               
        doc = obj.Document
        if self.isDeactivatedFor(doc):
            return
                
        odoc = self.handler.getOnlineDocument(doc)
        if not odoc:
            return
        if obj.isDerivedFrom("App::DocumentObject"):
            odoc.newDynamicProperty(obj, prop)
        else:
            odoc.newViewProviderDynamicProperty(obj, prop)
            
    
    def slotRemoveDynamicProperty(self, obj, prop):   
               
        doc = obj.Document
        if self.isDeactivatedFor(doc):
            return
        
        #print("Observer remove dyn property ( ", obj.Name, ", ", prop, " )")
            
        odoc = self.handler.getOnlineDocument(doc)
        if not odoc:
            return
        
        if obj.isDerivedFrom("App::DocumentObject"):
            odoc.removeDynamicProperty(obj, prop)
        else:
            odoc.removeViewProviderDynamicProperty(obj, prop)


    def slotChangePropertyEditor(self, obj, prop):
        
        #this gets called when the editor mode, or status, of the property changes
        doc = obj.Document
        if self.isDeactivatedFor(doc):
            return          
        
        odoc = self.handler.getOnlineDocument(doc)
        if not odoc:
            return
        
        if obj.isDerivedFrom("App::DocumentObject"):
            odoc.changePropertyStatus(obj, prop)
        else:
            odoc.changeViewProviderPropertyStatus(obj, prop)
        

    def slotRecomputedObject(self, obj):
               
        doc = obj.Document
        if self.isDeactivatedFor(doc):
            return
        
        odoc = self.handler.getOnlineDocument(doc)
        if odoc:
            odoc.recomputObject(obj)
    
    
    def slotBeforeAddingDynamicExtension(self, obj,  extension):
        #works for >=0.19       
        #store the current properties to figure out later which ones were added by the extension
        self.propertiesBeforeExtension = obj.PropertiesList

    
    def slotAddedDynamicExtension(self, obj, extension):
        #works for >=0.19, both DocumentObject and ViewProviders
        
        doc = obj.Document
        if self.isDeactivatedFor(doc):
            return          
        
        odoc = self.handler.getOnlineDocument(doc)
        if not odoc:
            return

        #calculate the properties that were added by the extension
        props = [item for item in obj.PropertiesList if item not in self.propertiesBeforeExtension]        
        
        #handle it!
        if obj.isDerivedFrom("App::DocumentObject"):
            odoc.addDynamicExtension(obj, extension, props)
        else:
            odoc.addViewProviderDynamicExtension(obj, extension, props)
        
    
    
    def slotRecomputedDocument(self, doc):
        
        if self.isDeactivatedFor(doc):
            return
        
        odoc = self.handler.getOnlineDocument(doc)
        if odoc:
            odoc.recomputeDocument()
    
    #def slotUndoDocument(self, doc):
        #pass
    
    #def slotRedoDocument(self, doc):
        #pass
    
    #def slotOpenTransaction(self, doc, name):
        #pass
    
    #def slotCommitTransaction(self, doc):
        #pass
    
    #def slotAbortTransaction(self, doc):
        #pass
    
    #def slotBeforeChangeDocument(self, doc, prop):
        #pass
        
    #def slotChangedDocument(self, doc, prop):
        #pass
    
    #def slotBeforeChangeObject(self, obj, prop):
        #pass
    
    
    #def slotStartSaveDocument(self, obj, name):
        #pass
    
    #def slotFinishSaveDocument(self, obj, name):
        #pass


class GUIDocumentObserver(ObserverBase):
    
    def __init__(self, handler):
        super().__init__(handler)
 
       
    def slotCreatedDocument(self, doc):
        pass
      
    def slotDeletedDocument(self, doc):
        pass
      
    def slotRelabelDocument(self, doc):
        pass
      
    def slotRenameDocument(self, doc):
        pass
      
    def slotActivateDocument(self, doc):
        pass
      
    def slotCreatedObject(self, vp):
        
        doc = vp.Document
        if self.isDeactivatedFor(doc):
            return
        
        odoc = self.handler.getOnlineDocument(doc)
        if odoc:
            odoc.newViewProvider(vp)
            

    def slotDeletedObject(self, obj):
        pass
 
 
    def slotChangedObject(self, vp, prop):
               
        #we need to check if any document has this vp, as accessing it before 
        #creation crashes freecad
        if not self.handler.hasOnlineViewProvider(vp):
            return
        
        doc = vp.Document
        if self.isDeactivatedFor(doc):
            return

        odoc = self.handler.getOnlineDocument(doc)
        if not odoc:
            return
        
        #0.18 workaround: get new extensions (in >=0.19 there are observer events for that)
        if float(".".join(FreeCAD.Version()[0:2])) == 0.18:
            added = self.fc018GetNewExtensions(vp)
            for extension in added:
                props = self.fc018GetPropertiesForExtension(extension)
                odoc.addViewProviderDynamicExtension(vp, extension, props)
               
        #finally call change object!    
        odoc.changeViewProvider(vp, prop)
      
    def slotInEdit(self, obj):
        pass
    
    def slotResetEdit(self, obj):
        pass

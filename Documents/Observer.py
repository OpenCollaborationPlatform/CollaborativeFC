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

class DocumentObserver():
    
    def __init__(self, handler):
        
        self.handler = handler
        self.inactive = []

    def activateFor(self, doc):
       
        while doc in self.inactive:
           self.inactive.remove(doc)
        
        
    def deactivateFor(self, doc):
        
        self.inactive.append(doc)
        
        
    def isDeactivatedFor(self, doc):
        
        if doc in self.inactive:
            return True 
        
        return False


    def slotCreatedDocument(self, doc):
        
        if self.isDeactivatedFor(doc):
            return
        
        print("Observed new document")
        self.handler.openFCDocument(doc)
        

    def slotDeletedDocument(self, doc):
        
        if self.isDeactivatedFor(doc):
            return
        
        print("Observer close document")
        self.handler.closeFCDocument(doc)


    #def slotRelabelDocument(self, doc):
        #pass


    def slotCreatedObject(self, obj):
        
        doc = obj.Document
        if self.isDeactivatedFor(doc):
            return
        
        print("Observer add document object ", obj.Name)  
        odoc = self.handler.getOnlineDocument(doc)
        if odoc:
            odoc.newObject(obj)


    def slotDeletedObject(self, obj):
        
        doc = obj.Document
        if self.isDeactivatedFor(doc):
            return
        
        print("Observer remove document object ", obj.Name)        
        odoc = self.handler.getOnlineDocument(doc)
        if odoc:
            odoc.removeObject(obj)


    def slotChangedObject(self, obj, prop):
        
        doc = obj.Document
        if self.isDeactivatedFor(doc):
            return
          
        
        print("Observer changed document object ( ", obj.Name, ", ", prop, " )")        
        odoc = self.handler.getOnlineDocument(doc)
        if not odoc:
            return
            
        #finally call change object!    
        odoc.changeObject(obj, prop)


    def slotAppendDynamicProperty(self, obj, prop):    
        
        doc = obj.Document
        if self.isDeactivatedFor(doc):
            return
        
        if obj.isDerivedFrom("App::DocumentObject"):
            print("Observer new dyn property ( ", obj.Name, ", ", prop, " )")
            
        odoc = self.handler.getOnlineDocument(doc)
        if odoc and obj.isDerivedFrom("App::DocumentObject"):
            odoc.newDynamicProperty(obj, prop)
    
    
    def slotRemoveDynamicProperty(self, obj, prop):   
        
        doc = obj.Document
        if self.isDeactivatedFor(doc):
            return
        
        if obj.isDerivedFrom("App::DocumentObject"):
            print("Observer remove dyn property ( ", obj.Name, ", ", prop, " )")
            
        odoc = self.handler.getOnlineDocument(doc)
        if odoc and obj.isDerivedFrom("App::DocumentObject"):
            odoc.removeDynamicProperty(obj, prop)


    def slotRecomputedObject(self, obj):
        print("Observer recomputed object ", obj.Name)
        
        doc = obj.Document
        if self.isDeactivatedFor(doc):
            return
        
        odoc = self.handler.getOnlineDocument(doc)
        if odoc:
            odoc.recomputObject(obj)
        
    #def slotRecomputedDocument(self, doc):
        #pass
    
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
    
    #def slotChangePropertyEditor(self, obj, prop):
        #pass
    
    #def slotStartSaveDocument(self, obj, name):
        #pass
    
    #def slotFinishSaveDocument(self, obj, name):
        #pass


class GUIDocumentObserver():
    
    def __init__(self, handler):
        
        self.handler = handler
        self.inactive = []


    def activateFor(self, doc):
       
        while doc in self.inactive:
           self.inactive.remove(doc)
        
        
    def deactivateFor(self, doc):
        
        self.inactive.append(doc)
        
        
    def isDeactivatedFor(self, doc):
        
        if doc in self.inactive:
            return True 
        
        return False
       
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
        
        print("Observer add viewprovider object ", vp.Object.Name)  
        odoc = self.handler.getOnlineDocument(doc)
        if odoc:
            odoc.newViewProvider(vp)
            

    def slotDeletedObject(self, obj):
        print("Object deleted")
        pass
        #if obj.Object is not None:
        #    print("viewprovider removed for object ", obj.Object.Name)

    def slotChangedObject(self, vp, prop):
        
        #we need to check if any document has this vp, as accessing it before 
        #creation crashes freecad
        print("changed vp called")
        if not self.handler.hasOnlineViewProvider(vp):
            return
        
        doc = vp.Document
        if self.isDeactivatedFor(doc):
            return

        print("Observer changed viewprovider ( ", vp, ", ", prop, " )")
        odoc = self.handler.getOnlineDocument(doc)
        if not odoc:
            return
            
        #finally call change object!    
        odoc.changeViewProvider(vp, prop)
      
    def slotInEdit(self, obj):
        pass
    
    def slotResetEdit(self, obj):
        pass

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

class DocumentObserver():
    
    def __init__(self, handler):
        self.handler = handler

    def slotCreatedDocument(self, doc):
        print("Observed new document")
        self.handler.openFCDocument(doc)
        

    def slotDeletedDocument(self, doc):
        print("Observer close document")
        self.handler.closeFCDocument(doc)

    #def slotRelabelDocument(self, doc):
        #pass

    #def slotCreatedObject(self, obj):
        #pass

    #def slotDeletedObject(self, obj):
        #pass

    #def slotChangedObject(self, obj, prop):
        #pass

    #def slotCreatedDocument(self, doc):
        #pass
    
    #def slotDeletedDocument(self, doc):
        #pass
    
    #def slotRelabelDocument(self, doc):
        #pass
    
    #def slotActivateDocument(self, doc):
        #pass
    
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
    
    #def slotCreatedObject(self, obj):
        #pass
    
    #def slotDeletedObject(self, obj):
        #pass
    
    #def slotChangedObject(self, obj, prop):
        #pass
    
    #def slotBeforeChangeObject(self, obj, prop):
        #pass
    
    #def slotRecomputedObject(self, obj):
        #pass
    
    #def slotAppendDynamicProperty(self, obj, prop):    
        #pass
    
    #def slotRemoveDynamicProperty(self, obj, prop):   
        #pass
    
    #def slotChangePropertyEditor(self, obj, prop):
        #pass
    
    #def slotStartSaveDocument(self, obj, name):
        #pass
    
    #def slotFinishSaveDocument(self, obj, name):
        #pass

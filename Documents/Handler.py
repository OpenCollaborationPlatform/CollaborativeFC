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
import asyncio

class DocumentHandler():
    #data structure that handles all documents for collaboration:
    # - the local ones that are unshared
    # - the ones we have been invited too but not yet joined
    # - the ones open at the node but not yet in FC
    # - the one we share
    
    def __init__(self, connection):               
        self.documents = [] #empty list for all our document handling status, each doc is a map: {id, status, onlinedoc, doc}
        self.updatefuncs = []
        self.connection = connection
        
        #add the observer 
        self.observer = self.DocumentObserver(self)
        FreeCAD.addDocumentObserver(self.observer)
        
        #TODO check all local documents available, as this may be startet after the user opened documents in freecad
                
        #lets initialize the async stuff!
        asyncio.ensure_future(self.asyncInit())
        
          
    def closeFCDocument(self, doc):
        asyncio.ensure_future(self.asyncCloseDoc())
        

    def openFCDocument(self, doc):
        #If a document was opened in freecad this function makes it known to the Handler. 
        docmap = {"id": None, "status": "local", "onlinedoc": None, "fcdoc": doc}
        self.documents.append(docmap)
        print("Call update!")
        self.Update()        
        
    def addUpdateFunc(self, func):
        self.updatefuncs.append(func)
    
    def updated():
        for f in self.updatefuncs:
            f()
    
    def getDocMap(self, key, val):
        #returns the docmap for the given key/value pair, e.g. "fcdoc":doc. Careful: if status is used
        #the first matching docmap is returned
        for docmap in self.documents: 
            if docmap[key] == val:
                return docmap 
        
        raise Exception('no such document found')
       
    async def asyncInit(self):
        #get a list of open documents of the node and add them to the list
        
        try:
            #we register ourself for some key events
            await self.connection.session.register(u"ocp.documents.opened", self.asyncOnDocumentOpened)
            await self.connection.session.register(u"ocp.documents.invited", self.asyncOnDocumentInvited)

            res = await self.connection.session.call(u"ocp.documents.list")
            for doc in res:
                docmap = {"id": res, "status": "node", "onlinedoc": None, "fcdoc": None}
                self.documents.append(docmap)
            
            self.updated()
            
        except Exception as e:
            print("Async init error: {0}".format(e))
    
    async def asyncCloseDoc(self, doc):
        #try to disconnect before remove
        docmap = self.getDocMap('fcdoc', doc)
        try:
            if docmap['status'] is 'shared':
                await docmap['onlinedoc'].unload()
                await self.connection.session.call(u"ocp.documents.close", docmap['id'])           
        finally:
            self.documents.remove(docmap)
            self.updated()

       
    async def asyncCollaborateOnDoc(self, key, val):
        
        try:
            docmap = self.getDocMap(key, val)
            status = docmap['status']
            if status is "local":
                res = await self.connection.session.call(u"ocp.documents.create")
                docmap['id'] = res
                docmap['onlinedoc'] = OnlineDocument(res, doc)
                await docmap['onlinedoc'].load()
                
            elif status is 'node':
                doc = FreeCAD.newDocument()
                docmap['fcdoc'] = doc
                docmap['onlinedoc'] = OnlineDoc(docmap['id'], doc)
                await docmap['onlinedoc'].load() 
                
            elif status is 'invited':
                await self.connection.session.call(u"ocp.documents.open", docmap['id'])
                doc = FreeCAD.newDocument()
                docmap['fcdoc'] = doc
                docmap['onlinedoc'] = OnlineDoc(docmap['id'], doc)
                await docmap['onlinedoc'].startup() 

            docmap['status'] = "shared"
            self.Update()
            
        except Exception as e:
            print("call error: {0}".format(e))
  
            
            
    async def asyncOnDocumentOpened(self):
        pass
    
    async def asyncOnDocumentInvited(self):
        pass
    
    
    class DocumentObserver():
    
        def __init__(self, handler):
            self.handler = handler

        def slotCreatedDocument(self, doc):
            print("Observed new document")
            self.handler.openFCDocument(doc)
            

        def slotDeletedDocument(self, doc):
            self.handler.closeFCDocument(doc)

        def slotRelabelDocument(self, doc):
            pass

        def slotCreatedObject(self, obj):
            pass

        def slotDeletedObject(self, obj):
            pass

        def slotChangedObject(self, obj, prop):
            pass

        def slotCreatedDocument(self, doc):
            pass
        
        def slotDeletedDocument(self, doc):
            pass
        
        def slotRelabelDocument(self, doc):
            pass
        
        def slotActivateDocument(self, doc):
            pass
        
        def slotRecomputedDocument(self, doc):
            pass
        
        def slotUndoDocument(self, doc):
            pass
        
        def slotRedoDocument(self, doc):
            pass
        
        def slotOpenTransaction(self, doc, name):
            pass
        
        def slotCommitTransaction(self, doc):
            pass
        
        def slotAbortTransaction(self, doc):
            pass
        
        def slotBeforeChangeDocument(self, doc, prop):
            pass
            
        def slotChangedDocument(self, doc, prop):
            pass
        
        def slotCreatedObject(self, obj):
            pass
        
        def slotDeletedObject(self, obj):
            pass
        
        def slotChangedObject(self, obj, prop):
            pass
        
        def slotBeforeChangeObject(self, obj, prop):
            pass
        
        def slotRecomputedObject(self, obj):
            pass
        
        def slotAppendDynamicProperty(self, obj, prop):    
            pass
        
        def slotRemoveDynamicProperty(self, obj, prop):   
            pass
        
        def slotChangePropertyEditor(self, obj, prop):
            pass
        
        def slotStartSaveDocument(self, obj, name):
            pass
        
        def slotFinishSaveDocument(self, obj, name):
            pass

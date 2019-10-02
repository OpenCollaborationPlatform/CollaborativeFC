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

import FreeCAD, asyncio, os
from Documents.Observer import DocumentObserver
from Documents.OnlineDocument import OnlineDocument

class DocumentHandler():
    #data structure that handles all documents for collaboration:
    # - the local ones that are unshared
    # - the ones we have been invited too but not yet joined
    # - the ones open at the node but not yet in FC
    # - the one we share
    
    def __init__(self, connection, collab_path):               
        self.documents = [] #empty list for all our document handling status, each doc is a map: {id, status, onlinedoc, doc}
        self.updatefuncs = []
        self.connection = connection
        self.collab_path = collab_path
        
        #add the observer 
        self.observer = DocumentObserver(self)
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
        self.update()
        
    def addUpdateFunc(self, func):
        self.updatefuncs.append(func)
    
    def update(self):
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
                docmap = {"id": doc, "status": "node", "onlinedoc": None, "fcdoc": None}
                self.documents.append(docmap)
            
            self.update()
            
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
            self.update()

       
    async def asyncCollaborateOnDoc(self, docmap):
        
        try:
            status = docmap['status']
            if status is "local":
                dmlpath = os.path.join(self.collab_path, "Dml")
                res = await self.connection.session.call(u"ocp.documents.create", dmlpath)
                docmap['id'] = res
                docmap['onlinedoc'] = OnlineDocument(res, docmap['fcdoc'], self.connection)
                await docmap['onlinedoc'].asyncLoad()
                
            elif status is 'node':
                doc = FreeCAD.newDocument()
                docmap['fcdoc'] = doc
                docmap['onlinedoc'] = OnlineDoc(docmap['id'], doc, self.connection)
                await docmap['onlinedoc'].asyncLoad() 
                
            elif status is 'invited':
                await self.connection.session.call(u"ocp.documents.open", docmap['id'])
                doc = FreeCAD.newDocument()
                docmap['fcdoc'] = doc
                docmap['onlinedoc'] = OnlineDoc(docmap['id'], doc, self.connection)
                await docmap['onlinedoc'].asyncUnload() 

            docmap['status'] = "shared"
            self.update()
            
        except Exception as e:
            print("collaborate error: {0}".format(e))
  
            
            
    async def asyncOnDocumentOpened(self):
        pass
    
    async def asyncOnDocumentInvited(self):
        pass

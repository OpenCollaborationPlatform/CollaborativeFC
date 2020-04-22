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

import FreeCAD, FreeCADGui, asyncio, os

from Documents.Dataservice      import DataService
from Documents.Observer         import DocumentObserver, GUIDocumentObserver, ObserverManager
from Documents.OnlineDocument   import OnlineDocument

import uuid
from autobahn.wamp.types import CallResult

class Entity():
    ''' data structure describing a entity in the collaboration framework. A entity is a things that can be calloborated on, e.g.:
        - A local Freecad document
        - A invited ocp document on the node
        - A open document on the node, not available locally 
        - etc.
    '''
        
    def __init__(self, id = None, status = 'unknown', onlinedoc = None, fcdoc = None ):
        self.id = id
        self.status = status
        self.onlinedoc = onlinedoc
        self.fcdoc = fcdoc
        

class Manager():
    #Manager that handles all entities for collaboration:
    # - the local ones that are unshared
    # - the ones we have been invited too but not yet joined
    # - the ones open at the node but not yet in FC
    # - the one we share
    
    def __init__(self, collab_path):               
        self.__entities = [] #empty list for all our document handling status, each doc is a map: {id, status, onlinedoc, doc}
        self.__updatefuncs = []
        self.__connection = None
        self.__collab_path = collab_path
        self.__blockObserver = False
        self.__uuid = uuid.uuid4()
        self.__dataservice = None

        
        #add the observer 
        self.__observer = DocumentObserver(self)
        self.__guiObserver = GUIDocumentObserver(self)
        FreeCAD.addDocumentObserver(self.__observer)
        FreeCADGui.addDocumentObserver(self.__guiObserver)
    
    #component API
    #**********************************************************************
    
    async def setConnection(self, con):
        self.__connection = con
        self.__dataservice = DataService(self.__uuid, con)
        #TODO check all local documents available, as this may be called after the user opened documents in freecad     
              
        try:
            #we register ourself for some key events
            await self.__connection.session.subscribe(self.onOCPDocumentOpened, u"ocp.documents.opened")
            await self.__connection.session.subscribe(self.onOCPDocumentClosed, u"ocp.documents.closed")
            await self.__connection.session.subscribe(self.onOCPDocumentInvited, u"ocp.documents.invited")

            res = await self.__connection.session.call(u"ocp.documents.list")
            if res == None:
                doclist = []
            elif type(res) == str:
                doclist = [res]
            elif type(res) == CallResult:
                doclist = res.results
            
            for doc in doclist:
                entity = Entity(id = doc, status = "node", onlinedoc = None, fcdoc = None)
                self.__entities.append(entity)
            
            self.__update()
            
        except Exception as e:
            print("Document Handler connection init error: {0}".format(e))

    async def removeConnection(self):
        self.__connection = None
        self.__dataservice = None
        self.__entities = {}
        

    #update notification handling
    #**********************************************************************
    
    def addUpdateFunc(self, func):
        self.__updatefuncs.append(func)
    
    def __update(self):
        for f in self.__updatefuncs:
            f()


    #FreeCAD event handling: Not blocking (used by document observers)
    #**********************************************************************
    
    def onFCDocumentOpened(self, doc):
        
        if not self.__connection:
            return 
        
        if self.__blockObserver:
            return
        
        #If a document was opened in freecad this function makes it known to the Handler. 
        entity = Entity(id = None, status = "local", onlinedoc = None, fcdoc = doc)
        self.__entities.append(entity)
        self.__update()
        
        
    def onFCDocumentClosed(self, doc):
        
        if not self.__connection:
            return 
        
        if self.__blockObserver:
            return
        
        async def coro(entity):
            
            #stop collaboration first
            await self.stopCollaborate(entity)
        
            #as the doc was closed completely we also delete it from this handler
            #TODO: the change should depend on state: it still could be open on the node, than it needs to stay in the handler
            entity = self.getEntity(key, value)
            self.__entities.remove(entity)
  
            #finally inform about that update.
            self.__update()
            
        asyncio.ensure_future(coro(self.getEntity('fcdoc', doc)))
       


    #OCP event handling  (used as wamp event callbacks)
    #**********************************************************************
    
    async def onOCPDocumentOpened(self):
        #TODO add new doc to docmap
        self.__update()
        
        
    async def onOCPDocumentClosed(self):
        #TODO add new doc to docmap
        self.__update()
    
    async def onOCPDocumentInvited(self):
        #TODO add new doc to docmap
        self.__update()
        
    
    
    #Document handling API: Async
    #**********************************************************************
    
    def getOnlineDocument(self, fcdoc):
        #return the correcponding OnlineDocument for a given FreeCAD local Document. Returns None is none is available
        
        #check if it is a GuiDocument and use the App one instead
        if hasattr(fcdoc, "ActiveView"):
            fcdoc = fcdoc.Document
        
        #get the online document for a certain freecad document, or None if not available
        try:
            entity = self.getEntity('fcdoc', fcdoc)
            return entity.onlinedoc
        except:
            return None

    
    def hasOnlineViewProvider(self, fcvp):
        
        #returns if the given FreeCAD viewprovider has a corresponding OnlineViewProvider
        for entity in self.__entities: 
            if entity.onlinedoc and entity.onlinedoc.hasViewProvider(fcvp):
                return True
        
        return False
 
 
    def getEntities(self):
        return self.__entities


    async def collaborate(self, entity):
        #for the entity collaboration is started. That means:
        # - Created in OCP when open local only
        # - Opened in FC if open on node
        # - Opened on node and created in FC when invited
        # - Doing nothing if already shared
    
        if not self.__connection:
            return 
        
        obs = ObserverManager(self.__guiObserver, self.__observer)
            
        if entity.status == "local":
            dmlpath = os.path.join(self.__collab_path, "Dml")
            res = await self.__connection.session.call(u"ocp.documents.create", dmlpath)
            entity.id = res
            entity.onlinedoc = OnlineDocument(res, entity.fcdoc, obs, self.__connection, self.__dataservice)
            await entity.onlinedoc.asyncSetup()
                
        elif entity.status == 'node':
            self.__blockObserver = True
            doc = FreeCAD.newDocument()
            self.__blockObserver = False
            entity.fcdoc = doc
            entity.onlinedoc = OnlineDocument(entity.id, doc, obs, self.__connection, self.__dataservice)
            await entity.onlinedoc.asyncLoad() 
                
        elif entity.status == 'invited':
            await self.__connection.session.call(u"ocp.documents.open", entity.id)
            self.__blockObserver = True
            doc = FreeCAD.newDocument()
            self.__blockObserver = False
            entity.fcdoc = doc
            entity.onlinedoc = OnlineDocument(entity.id, doc, obs, self.__connection, self.__dataservice)
            await entity.onlinedoc.asyncUnload() 

        entity.status = "shared"
        self.__update()
            

    async def stopCollaborate(self, entity):
        #For the shared entity, this call stops the collaboration by closing it on the node, but keeping it local.
        #Should be called if collaboration is ended but work goes on.
        
        if not self.__connection:
            return 
        
        try:
            if entity.status == 'shared':
                await entity.onlinedoc.asyncUnload()
                await self.__connection.session.call(u"ocp.documents.close", entity.id)
            
            entity.status = "local"
            self.__update()
        
        except Exception as e:
            print("Close document id error: {0}".format(e))
          

    def getEntity(self, key, val):
        #returns the entity for the given key/value pair, e.g. "fcdoc":doc. Careful: if status is used
        #the first matching docmap is returned
        for entity in self.__entities: 
            if getattr(entity, key) is not None:
                return entity
        
        raise Exception('no such entity found')

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

import Utils
from Documents.Dataservice      import DataService
from Documents.OnlineDocument   import OnlineDocument
from Manager import ManagedDocument

from Qasync import asyncSlot
from PySide import QtCore
import uuid
from autobahn.wamp.types import CallResult
from enum import Enum, auto


class Entity():
    ''' data structure describing a entity in the collaboration framework. A entity is a things that can be calloborated on, e.g.:
        - A local Freecad document
        - A invited ocp document on the node
        - A open document on the node, not available locally 
        - etc.
    '''
    
    class Status(Enum):
        unknown = auto()
        local   = auto()    # entity is available only in local freecad session
        node    = auto()    # entity is available only on ocp node (has a manager, but no onlinedoc)
        invited = auto()    # entity is not even open on the ocp node, but someone else added the node as a member of a document
        shared  = auto()    # entity is open on ocp node and in local freecad session (has a manager and a onlinedoc)
        
    def __init__(self, id = None, status = Status.unknown, onlinedoc = None, fcdoc = None, manager = None ):
        
        self.id = id
        self.status = status
        self.fcdoc = fcdoc
        self.onlinedoc = onlinedoc
        self.manager = manager
        self.uuid = str(uuid.uuid4())
        

class Manager(QtCore.QObject, Utils.AsyncSlotObject):
    #Manager that handles all entities for collaboration:
    # - the local ones that are unshared
    # - the ones we have been invited too but not yet joined
    # - the ones open at the node but not yet in FC
    # - the one we share
       
    def __init__(self, collab_path, connection):  
        
        QtCore.QObject.__init__(self)
        
        self.__entities = [] #empty list for all our document handling status, each doc is a map: {id, status, onlinedoc, doc}
        self.__connection = None
        self.__collab_path = collab_path
        self.__blockLocalEvents = False
        self.__uuid = uuid.uuid4()
        self.__dataservice = DataService(self.__uuid, connection)
        self.__connection = connection
        
        self.__connection.api.connectedChanged.connect(self.__connectionChanged)
        asyncio.ensure_future(self.__asyncInit())   
    
    
    async def __asyncInit(self):
        
        await self.__dataservice.setup()
              
        try:
            #we register ourself for some key events
            await self.__connection.api.subscribe("manager", self.onOCPDocumentCreated, u"ocp.documents.created")
            await self.__connection.api.subscribe("manager", self.onOCPDocumentOpened, u"ocp.documents.opened")
            await self.__connection.api.subscribe("manager", self.onOCPDocumentClosed, u"ocp.documents.closed")
            await self.__connection.api.subscribe("manager", self.onOCPDocumentInvited, u"ocp.documents.invited")

            await self.__handleConnectionChanged()
            
        except Exception as e:
            print("Document Handler connection init error: {0}".format(e))

    
    @asyncSlot()
    async def __connectionChanged(self):
        await self.__handleConnectionChanged()
        
        
    async def __handleConnectionChanged(self):
        # Updates the entities according to the conenction status
        #
        # Required as async function as __asyncInit cannot call asyncSlot, as it would spawn a task
        # from within a task
        
        if self.__connection.api.connected:
            
            # all open documents
            doclist = await self.__connection.api.call(u"ocp.documents.list")
            for doc in doclist:
                if not self.hasEntity("id", doc):
                    entity = Entity(id = doc, status = Entity.Status.node, onlinedoc = None,
                                    fcdoc = None, manager=ManagedDocument(doc, self.__connection))
                    
                    await entity.manager.setup()
                    self.__entities.append(entity)
                    self.documentAdded.emit(entity.uuid)
                    
            # all invited documents
            doclist = await self.__connection.api.call(u"ocp.documents.invitations")
            for doc in doclist:
                if not self.hasEntity("id", doc):
                    entity = Entity(id = doc, status = Entity.Status.invited, onlinedoc = None,
                                    fcdoc = None, manager=None)
                    
                    self.__entities.append(entity)
                    self.documentAdded.emit(entity.uuid)
                
        else:
            for entity in self.__entities:
                    
                if entity.status == Entity.Status.invited:
                    self.__entities.remove(entity)
                    self.documentRemoved.emit(entity.uuid)
                    
                if entity.status == Entity.Status.node:
                    await entity.manager.close()
                    entity.manager = None
                    self.__entities.remove(entity)
                    self.documentRemoved.emit(entity.uuid)
                    
                if entity.status == Entity.Status.shared:
                    await entity.onlinedoc.close()
                    await entity.manager.close()
                    entity.onlinedoc = None
                    entity.manager = None 
                    entity.id = None
                    entity.status = Entity.Status.local
                    self.documentChanged.emit(entity.uuid)


    #FreeCAD event handling: Not blocking (used by document observers)
    #**********************************************************************
    
    def onFCDocumentOpened(self, doc):
        
        if not self.__connection:
            return 
        
        if self.__blockLocalEvents:
            return
        
        #If a document was opened in freecad this function makes it known to the Handler. 
        entity = Entity(id = None, status = Entity.Status.local, onlinedoc = None, fcdoc = doc, manager=None)
        self.__entities.append(entity)
        self.documentAdded.emit(entity.uuid)
        
        
    def onFCDocumentClosed(self, doc):
        
        if not self.__connection:
            return 
        
        if self.__blockLocalEvents:
            return
        
        entity = self.getEntity('fcdoc', doc)
        
        if entity.status == Entity.Status.local:
            # we can remove the entity if it is local only
            self.__entities.remove(entity)
            self.documentRemoved.emit(entity.uuid)
            
        elif entity.status == Entity.Status.shared:
            # but if shared we change it to be on node only
            entity.status = Entity.Status.node
            entity.fcdoc = None
            if entity.onlinedoc:
                asyncio.ensure_future(entity.onlinedoc.close())
                entity.onlinedoc = None 
                
            self.documentChanged.emit(entity.uuid)
 



    #OCP event handling  (used as wamp event callbacks)
    #**********************************************************************
    
    async def onOCPDocumentCreated(self, id):

        #could be that we alread have this id (e.g. if we created it ourself)
        if self.hasEntity('id', id):
            return
               
        entity = Entity(id = id, status = Entity.Status.node, onlinedoc = None, 
                        fcdoc = None, manager=ManagedDocument(id, self.__connection))
        await entity.manager.setup()
        self.__entities.append(entity)
        self.documentAdded.emit(entity.uuid)

        
    async def onOCPDocumentOpened(self, id): 
        # opened means a new node document in our node that was created by someone else, we just joined.
        # hence the processing is exactly the same as created
        return await self.onOCPDocumentCreated(id)
            
        
    async def onOCPDocumentClosed(self, id):
        
        
        if not self.hasEntity('id', id):
            return 
        
        entity = self.getEntity('id', id)
        if entity.onlinedoc:
            await entity.onlinedoc.close()
            entity.onlinedoc = None
        
        if entity.manager:
            await entity.manager.close()
            entity.manager = None
        
        invitations = await self.__connection.api.call(u"ocp.documents.invitations")
        
        if entity.status == Entity.Status.node:
            # check if we are invited
            if id in invitations:
                entity.status = Entity.Status.invited
                self.documentChanged.emit(entity.uuid)
            else:
                self.__entities.remove(entity)
                self.documentRemoved.emit(entity.uuid)
               
        elif entity.status == Entity.Status.shared:
            #it was shared before, hence now with it being closed on the node it is only availble locally          
            entity.status = Entity.Status.local
            entity.id = None
            self.documentChanged.emit(entity.uuid)
            
            if id in invitations:
                #we have now a local one + the invitation
                await self.onOCPDocumentInvited(id, True)
            
        else:
            # in case it is anything else than status==node || invited something went wrong, and removing it is fine
            self.__entities.remove(entity)
            self.documentRemoved.emit(entity.uuid)
        
    
    async def onOCPDocumentInvited(self, doc, add):
       
        if add:
            if self.hasEntity('id', doc):
                return 
            
            entity = Entity(id = doc, status = Entity.Status.invited, onlinedoc = None,
                                    fcdoc = None, manager=None)
                    
            self.__entities.append(entity)
            self.documentAdded.emit(entity.uuid)
            
        else:
            if not self.hasEntity('id', doc):
                return
            
            if entity.status != Entity.Status.invited:
                return 
            
            self.__entities.remove(entity)
            self.documentRemoved.emit(entity.uuid)        
        
    
    
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


    async def collaborate(self, entity, documentname = "Unnamed"):
        #for the entity collaboration is started. That means:
        # - Created/opened in OCP when open local only
        # - Opened in FC if open on node
        # - Opened on node and created in FC when invited
        # - Doing nothing if already shared
                    
        if entity.status == Entity.Status.local:
            dmlpath = os.path.join(self.__collab_path, "Dml")
            res = await self.__connection.api.call(u"ocp.documents.create", dmlpath)
            
            #it could have been that we already received the "documentCreated" event, and hence have a new entity created.
            #that would be wrong! 
            if self.hasEntity("id", res):
                self.__entities.remove(self.getEntity("id", res))
                self.documentRemoved.emit(self.getEntity("id", res).uuid)
            
            entity.id = res
            entity.onlinedoc = OnlineDocument(res, entity.fcdoc, self.__connection, self.__dataservice)
            await entity.onlinedoc.setup()
            entity.manager = ManagedDocument(res, self.__connection)
            await entity.manager.setup()
            await entity.onlinedoc.asyncSetup()
                
        elif entity.status == Entity.Status.node:
            self.__blockLocalEvents = True
            entity.fcdoc = FreeCAD.newDocument(documentname)
            self.__blockLocalEvents = False
            entity.onlinedoc = OnlineDocument(entity.id, entity.fcdoc, self.__connection, self.__dataservice)
            await entity.onlinedoc.setup()
            await entity.onlinedoc.asyncLoad() 
                
        elif entity.status == Entity.Status.invited:
            await self.__connection.api.call(u"ocp.documents.open", entity.id)
            self.__blockLocalEvents = True
            entity.fcdoc = FreeCAD.newDocument(documentname)
            self.__blockLocalEvents = False
            entity.onlinedoc = OnlineDocument(entity.id, entity.fcdoc, self.__connection, self.__dataservice)
            await entity.onlinedoc.setup()
            entity.manager = ManagedDocument(entity.id, self.__connection)
            await entity.manager.setup()
            await entity.onlinedoc.asyncLoad() 

        entity.status = Entity.Status.shared
        self.documentChanged.emit(entity.uuid)
        
   
    async def stopCollaborate(self, entity):
        # For the shared entity, this call stops the collaboration by closing it on the node, but keeping it local.
        # For node entity it cloese it for good.
        
        if not self.__connection.api.connected:
            return 
        
        # we do not do any entity work, as this is handled by the ocp event callbacks we trigger

        if entity.status == Entity.Status.shared or entity.status == Entity.Status.node:
            await self.__connection.api.call(u"ocp.documents.close", entity.id)
            
        else:
            raise Exception(f"Cannot stop colaboration when status is {entity.status.name}")

    

    def getEntity(self, key, val):
        #returns the entity for the given key/value pair, e.g. "fcdoc":doc. Careful: if status is used
        #the first matching docmap is returned
        for entity in self.__entities: 
            if getattr(entity, key) == val:
                return entity
        
        return None

    def hasEntity(self, key, val):
        #returns the entity for the given key/value pair, e.g. "fcdoc":doc. Careful: if status is used
        #the first matching docmap is returned
        for entity in self.__entities: 
            if getattr(entity, key) == val:
                return True
        
        return False
    
    def entityStatus(self, name):
        # returns the entity status enum value from name
        # (helper class to not need to import Entity)
        
        return Entity.Status[name]
    
    
    # QT implementation
    # **************************************************************************************************

    documentAdded   = QtCore.Signal(str)
    documentRemoved = QtCore.Signal(str)
    documentChanged = QtCore.Signal(str)
    
    @Utils.AsyncSlot(str)
    async def toggleCollaborateSlot(self, uuid):
        entity = self.getEntity("uuid", uuid)
        if entity.status == Entity.Status.shared or entity.status == Entity.Status.node:
            await self.stopCollaborate(entity)
        else:
            await self.collaborate(entity)
        
    @Utils.AsyncSlot(str)
    async def toggleOpenSlot(self, uuid):
        entity = self.getEntity("uuid", uuid)
        if entity.fcdoc:
            # we simply close it. the doc observer callbacks handle all the entity stuff
            FreeCAD.closeDocument(entity.fcdoc.Name)
        else:
            # we can reuse collaborate, as it opens a document for a node status entity anyway
            await self.collaborate(entity)
        

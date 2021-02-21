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
from Documents.OnlineDocument   import OnlineDocument

from qasync import asyncSlot
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
        local   = auto()
        node    = auto()
        invited = auto()
        shared  = auto()   
        
    def __init__(self, id = None, status = Status.unknown, onlinedoc = None, fcdoc = None ):
        
        self.id = id
        self.status = status
        self.onlinedoc = onlinedoc
        self.fcdoc = fcdoc
        

class Manager(QtCore.QAbstractListModel):
    #Manager that handles all entities for collaboration:
    # - the local ones that are unshared
    # - the ones we have been invited too but not yet joined
    # - the ones open at the node but not yet in FC
    # - the one we share
    
    def __init__(self, collab_path, connection):  
        
        QtCore.QAbstractListModel.__init__(self)
        
        self.__entities = [] #empty list for all our document handling status, each doc is a map: {id, status, onlinedoc, doc}
        self.__connection = None
        self.__collab_path = collab_path
        self.__blockLocalEvents = False
        self.__uuid = uuid.uuid4()
        self.__dataservice = DataService(self.__uuid, connection)
        self.__connection = connection
        
        self.__connection.api.connectedChanged.connect(self.__connectionChanged)
        asyncio.ensure_future(self.__asyncInit(connection))   
    
    
    async def __asyncInit(self, con):
              
        try:
            #we register ourself for some key events
            await self.__connection.api.subscribe("manager", self.onOCPDocumentCreated, u"ocp.documents.created")
            await self.__connection.api.subscribe("manager", self.onOCPDocumentOpened, u"ocp.documents.opened")
            await self.__connection.api.subscribe("manager", self.onOCPDocumentClosed, u"ocp.documents.closed")
            await self.__connection.api.subscribe("manager", self.onOCPDocumentInvited, u"ocp.documents.invited")

            if self.__connection.api.connected:
                self.layoutAboutToBeChanged.emit()
                doclist = await self.__connection.api.call(u"ocp.documents.list")
            
                for doc in doclist:
                    entity = Entity(id = doc, status = Entity.Status.node, onlinedoc = None, fcdoc = None)
                    self.__entities.append(entity)
                    
                self.layoutChanged.emit()
            
            
        except Exception as e:
            print("Document Handler connection init error: {0}".format(e))

    
    @asyncSlot()
    async def __connectionChanged(self):
        
        self.layoutAboutToBeChanged.emit()
        if self.__connection.api.connected:
            
            doclist = await self.__connection.api.call(u"ocp.documents.list")
            for doc in doclist:
                if not self.hasEntity("id", doc):
                    entity = Entity(id = doc, status = Entity.Status.node, onlinedoc = None, fcdoc = None)
                    self.__entities.append(entity)
                
        else:
            for entity in self.__entities:
                if entity.status == Entity.Status.node or entity.status == Entity.Status.invited:
                    self.__entities.remove(entity)
                if entity.status == Entity.Status.shared:
                    entity.status = Entity.Status.unknown
          
        self.layoutChanged.emit()
        

    #FreeCAD event handling: Not blocking (used by document observers)
    #**********************************************************************
    
    def onFCDocumentOpened(self, doc):
        
        if not self.__connection:
            return 
        
        if self.__blockLocalEvents:
            return
        
        #If a document was opened in freecad this function makes it known to the Handler. 
        entity = Entity(id = None, status = Entity.Status.local, onlinedoc = None, fcdoc = doc)
        self.layoutAboutToBeChanged.emit()
        self.__entities.append(entity)
        self.layoutChanged.emit()
        
        
    def onFCDocumentClosed(self, doc):
        
        if not self.__connection:
            return 
        
        if self.__blockLocalEvents:
            return
        
        entity = self.getEntity('fcdoc', doc)
        
        self.layoutAboutToBeChanged.emit()
        if entity.status == Entity.Status.local:
            #we can remove the entity if it is local only
            self.__entities.remove(entity)
            
        elif entity.status == Entity.Status.shared:
            #but if shared we change it to be on node only
            entity.status = Entity.Status.node
            entity.fcdoc = None
            if entity.onlinedoc:
                asyncio.ensure_future(entity.onlinedoc.close())
                entity.onlinedoc = None #garbage collect takes care of online doc and obj
 
        self.layoutChanged.emit()



    #OCP event handling  (used as wamp event callbacks)
    #**********************************************************************
    
    async def onOCPDocumentCreated(self, id):

        #could be that we alread have this id (e.g. if we created it ourself)
        if self.hasEntity('id', id):
            return
        
        self.layoutAboutToBeChanged.emit()
        
        entity = Entity(id = id, status = Entity.Status.node, onlinedoc = None, fcdoc = None)
        self.__entities.append(entity)
        
        self.layoutChanged.emit()
        
        
    async def onOCPDocumentOpened(self, id): 
        # opened means a new node document in our node that was created by someone else, we just joined.
        # hence the processing is exactly the same as created
        return self.onOCPDocumentCreated(id)
            
        
    async def onOCPDocumentClosed(self, id):
        
        #we do not check if entity exists, as a raise does not bother us
        entity = self.getEntity('id', id)
        
        self.layoutAboutToBeChanged.emit()
        
        if entity.status == Entity.Status.node or entity.status == Entity.Status.invited:
            #it if is a pure node document we can remove it
            self.__entities.remove(entity)     
        
        elif entity.status == Entity.Status.shared:
            #it was shared before, hence now with it being closed on the node it is only availble locally
            if entity.onlinedoc:
                await entity.onlinedoc.close()
                entity.onlinedoc = None
                
            entity.status = Entity.Status.local
            entity.id = None
            
        self.layoutChanged.emit()
             
        
    
    def onOCPDocumentInvited(self):
        #TODO not implemented on note yet
        pass
        
    
    
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
             
        self.layoutAboutToBeChanged.emit()
        
        if entity.status == Entity.Status.local:
            dmlpath = os.path.join(self.__collab_path, "Dml")
            res = await self.__connection.api.call(u"ocp.documents.create", dmlpath)
            
            #it could have been that we already received the "documentCreated" event, and hence have a new entity created.
            #that would be wrong! 
            if self.hasEntity("id", res):
                self.__entities.remove(self.getEntity("id", res))
            
            entity.id = res
            entity.onlinedoc = OnlineDocument(res, entity.fcdoc, self.__connection, self.__dataservice)
            await entity.onlinedoc.asyncSetup()
                
        elif entity.status == Entity.Status.node:
            self.__blockLocalEvents = True
            doc = FreeCAD.newDocument(documentname)
            self.__blockLocalEvents = False
            entity.fcdoc = doc
            entity.onlinedoc = OnlineDocument(entity.id, doc, self.__connection, self.__dataservice)
            await entity.onlinedoc.asyncLoad() 
                
        elif entity.status == Entity.Status.invited:
            await self.__connection.api.call(u"ocp.documents.open", entity.id)
            self.__blockLocalEvents = True
            doc = FreeCAD.newDocument(documentname)
            self.__blockLocalEvents = False
            entity.fcdoc = doc
            entity.onlinedoc = OnlineDocument(entity.id, doc, self.__connection, self.__dataservice)
            await entity.onlinedoc.asyncLoad() 

        entity.status = Entity.Status.shared
        self.layoutChanged.emit()
   
   
    async def stopCollaborate(self, entity):
        # For the shared entity, this call stops the collaboration by closing it on the node, but keeping it local.
        # For node entity it cloese it for good.
        
        if not self.__connection.api.connected:
            return 
        
        try:
            # we do not do any entity work, as this is handled by the ocp event callbacks we trigger
            
            if entity.status == Entity.Status.shared or entity.status == Entity.Status.node:
                await self.__connection.api.call(u"ocp.documents.close", entity.id)
                
            else:
                raise Exception(f"Cannot stop colaboration when status is {entity.status.name}")
        
        except Exception as e:
            print("Stop collaboration error: {0}".format(e))
    

    def getEntity(self, key, val):
        #returns the entity for the given key/value pair, e.g. "fcdoc":doc. Careful: if status is used
        #the first matching docmap is returned
        for entity in self.__entities: 
            if getattr(entity, key) == val:
                return entity
        
        raise Exception(f'no such entity found: {key} == {val}')

    def hasEntity(self, key, val):
        #returns the entity for the given key/value pair, e.g. "fcdoc":doc. Careful: if status is used
        #the first matching docmap is returned
        for entity in self.__entities: 
            if getattr(entity, key) == val:
                return True
        
        return False
    
    
    # QT Model implementation
    # **************************************************************************************************

    collabborateFinished        = QtCore.Signal()
    stopCollabborateFinished    = QtCore.Signal()

    class ModelRole(Enum):
        status  = auto()
        name    = auto()
        members = auto()
        joined  = auto()
        isOpen  = auto()

    
    def roleNames(self):
        #return the QML accessible entries        
        return {Manager.ModelRole.status.value: QtCore.QByteArray(bytes("status", 'utf-8')),
                Manager.ModelRole.name.value: QtCore.QByteArray(bytes("name", 'utf-8')),
                Manager.ModelRole.members.value: QtCore.QByteArray(bytes("members", 'utf-8')),
                Manager.ModelRole.joined.value: QtCore.QByteArray(bytes("joined", 'utf-8')),
                Manager.ModelRole.isOpen.value: QtCore.QByteArray(bytes("isOpen", 'utf-8'))}
    
    def data(self, index, role):
        #return the data for the given index and role
        
        #index = PySide2.QtCore.QModelIndex
        entity = self.__entities[index.row()]
        role = Manager.ModelRole(role)
        
        if role == Manager.ModelRole.status:
            return entity.status.name
        
        if role == Manager.ModelRole.name:
            if entity.fcdoc != None:
                return entity.fcdoc.Name
            if entity.id != None:
                return entity.id
                        
            return "Unknown name"
        
        if role == Manager.ModelRole.members:
            return 0
        
        if role == Manager.ModelRole.joined:
            return 0
        
        if role == Manager.ModelRole.isOpen:
            return not entity.fcdoc is None

    def rowCount(self, index):
        return len(self.__entities)
    
    @asyncSlot(int)
    async def collaborateSlot(self, idx):
        entity = self.__entities[idx]
        await self.collaborate(entity)
        self.collabborateFinished.emit()
    
    @asyncSlot(int)
    async def stopCollaborateSlot(self, idx):
        entity = self.__entities[idx]
        await self.stopCollaborate(entity)
        self.stopCollabborateFinished.emit()
        
    @asyncSlot(int)
    async def openSlot(self, idx):
        entity = self.__entities[idx]
        if entity.fcdoc:
            return
        
        # we can reuse collaborate, as it opens a document for a node status entity anyway
        await self.collaborate(entity)
        
    @asyncSlot(int)
    async def closeSlot(self, idx):
        entity = self.__entities[idx]
        if entity.fcdoc:
            # we simply close it. the doc observer callbacks handle all the entity stuff
            FreeCAD.closeDocument(entity.fcdoc.Name)
        
        

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
from Utils.Errorhandling import OCPErrorHandler, attachErrorData
from OCP import OCPConnection
from Documents.Dataservice      import DataService
from Documents.OnlineDocument   import OnlineDocument
from Manager.Entity  import Entity

from Qasync import asyncSlot
from PySide import QtCore
import uuid
from autobahn.wamp.types import CallResult
from enum import Enum, auto


class _EventBlocker():
    # helper class to block local events from the manager
    
    def __init__(self, manager):
        self.__manager = manager
          
    def __enter__(self):
        self.__manager._blockLocalEvents = True
      
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.__manager._blockLocalEvents = False


class Manager(QtCore.QObject, OCPErrorHandler):
    #Manager that handles all entities for collaboration:
    # - the local ones that are unshared
    # - the ones we have been invited too but not yet joined
    # - the ones open at the node but not yet in FC
    # - the one we share
    

    documentAdded   = QtCore.Signal(str)

    
    def __init__(self, collab_path, connection: OCPConnection):  
        
        QtCore.QObject.__init__(self)
        OCPErrorHandler.__init__(self)
        
        self.__entities = [] #empty list for all our document handling status, each doc is a map: {id, status, onlinedoc, doc}
        self.__connection = None
        self.__collab_path = collab_path
        self._blockLocalEvents = False
        self.__uuid = uuid.uuid4()
        self.__dataservice = DataService(self.__uuid, connection)
        self.__connection = connection
        
        self.__connection.api.connectedChanged.connect(self.__connectionChanged)
        asyncio.ensure_future(self.__asyncInit())   
    
    
    def _handleError(self, source, error, data):
        
        if "ocp_message" in data:
            err = data["ocp_message"]
            printdata = data.copy()
            del printdata["ocp_message"]
            del printdata["exception"]
            print(f"{err}: {printdata}")
            
        OCPErrorHandler._handleError(self, source, error, data)
    
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
            attachErrorData(e, "ocp_message",  "Initalizing document manager failed")
            self._processException(e)

    def _removeEntity(self, entity):
        
        if entity in self.__entities:
            self.__entities.remove(entity)
    
    @asyncSlot()
    async def __connectionChanged(self):
        await self.__handleConnectionChanged()
        
        
    async def __handleConnectionChanged(self):
        # Updates the entities according to the connection status
        #
        # Required as async function as __asyncInit cannot call asyncSlot, as it would spawn a task
        # from within a task
        
        try:
            if self.__connection.api.connected:
                
                # all open documents
                doclist = await self.__connection.api.call(u"ocp.documents.list")
                for doc in doclist:
                    if not self.hasEntity("id", doc):
                        entity = Entity(self.__connection, self.__dataservice, self.__collab_path, _EventBlocker(self))
                        entity.finished.connect(lambda e=entity: self._removeEntity(e))
                        self.__entities.append(entity)
                        self.documentAdded.emit(entity.uuid)
                        
                        entity.start(id = doc)
                        
                # all invited documents
                doclist = await self.__connection.api.call(u"ocp.documents.invitations")
                for doc in doclist:
                    if not self.hasEntity("id", doc):
                        entity = Entity(self.__connection, self.__dataservice, self.__collab_path, _EventBlocker(self))     
                        entity.finished.connect(lambda e=entity: self._removeEntity(e))
                        self.__entities.append(entity)
                        self.documentAdded.emit(entity.uuid)
                        
                        entity.start(id = doc)
            
        except Exception as e:
            attachErrorData(e, "ocp_message", "Processing connection change failed")
            self._processException(e)


    #FreeCAD event handling: Not blocking (used by document observers)
    #**********************************************************************
    
    def onFCDocumentOpened(self, doc):
        
        if not self.__connection:
            return 
        
        if self._blockLocalEvents:
            return
        
        #If a document was opened in freecad this function makes it known to the Handler. 
        entity = Entity(self.__connection, self.__dataservice, self.__collab_path, _EventBlocker(self))
        entity.finished.connect(lambda e=entity: self._removeEntity(e))
        self.__entities.append(entity)       
        self.documentAdded.emit(entity.uuid)
        
        # process the state change
        entity.start(fcdoc = doc)
        
        
    def onFCDocumentClosed(self, doc):
        
        if not self.__connection:
            return 
        
        if self._blockLocalEvents:
            return
        
        entity = self.getEntity('fcdocument', doc)
        if entity:
            entity.processEvent(Entity.Events.closed)
 

    #OCP event handling  (used as wamp event callbacks)
    #**********************************************************************
    
    def onOCPDocumentCreated(self, id):
   
        #could be that we already have this id (e.g. if we created it ourself)
        if self.hasEntity('id', id):
            return
               
        entity = Entity(self.__connection, self.__dataservice, self.__collab_path, _EventBlocker(self))
        entity.finished.connect(lambda e=entity: self._removeEntity(e))
        self.__entities.append(entity)
        self.documentAdded.emit(entity.uuid)
        
        entity.start(id = id)
        
    def onOCPDocumentOpened(self, id): 
        # same as created: setup the entity and let it figure out everything itself
        return self.onOCPDocumentCreated(id)
            
        
    def onOCPDocumentClosed(self, id):
        
        
        if not self.hasEntity('id', id):
            return 
        
        entity = self.getEntity('id', id)
        entity.processEvent(Entity.Events.closed)
        
    
    def onOCPDocumentInvited(self, doc, add):
       
        if add:
            # same as created: setup the entity and let it figure out everything itself
            return self.onOCPDocumentCreated(id)
            
        else:
            if not self.hasEntity('id', doc):
                return
            
            entity = self.getEntity('id', id)
            entity.processEvent(Entity.Events.closed)

    
    # Entity access
    # **********************************************************************
    
    def getEntities(self):
        return self.__entities
   

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


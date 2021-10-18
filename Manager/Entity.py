# ************************************************************************
# *   Copyright (c) Stefan Troeger (stefantroeger@gmx.net) 2021          *
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

import uuid
import Utils.StateMachine as SM
from NodeDocument import NodeDocumentManager
from Documents.OnlineDocument import OnlineDocument

class Entity(SM.StateMachine):
    ''' data structure describing a entity in the collaboration framework. A entity is a things that can be calloborated on, e.g.:
        - A local Freecad document
        - A invited ocp document on the node
        - A open document on the node, not available locally 
        - etc.
    '''
    
    class States(SM.States):
        
        Undefined = SM.InitialState()                       # Initial state, events are used to setup fully
        Local     = SM.State()                              # Entity is local document only
        Removed   = SM.FinalState()                         # Invalid entity, it was removed from the entity manager
        
        class Online(SM.ParallelStates):                    #  Entity is available on the OCP node
                       
            class Status(SM.GroupedStates):                 # States to define the exact status on the node
                Unknown = SM.InitialState()                 # Entity exists and is online, but its unclear what state it has on the node
                Invited = SM.State()                        # Invided document on node
                Shared  = SM.State()                        # Shared document: Fully setup on node
                
            class Document(SM.GroupedStates):               # Corresponding FC document for the node doc
                Close = SM.InitialState()
                Open  = SM.State()
            
            class Errors(SM.GroupedStates):                 # Error handling 
                Working             = SM.InitialState()     # No error
                ConnectionError     = SM.State()            # Problems with connection of the node to the other peers: User feedback required
                EditError           = SM.State()            # User Editing did produce an error: Report only

        
    class Events(SM.Events):
        collaborate = SM.Transitions() # Event for starting collaboration (set uuid before when a given should be used)
        stopcollab  = SM.Transitions() # Event for stopping collaboration
        fcopend     = SM.Transitions() # FC document opened (set fcdocument before)
        fcclosed    = SM.Transitions() # FC document closed
        invited     = SM.Transitions() # Initializes the entity as invited (set uuid before)
        removed     = SM.Transitions() # Cleans up the entity and makes it invalid. Cannot be revived afterwards
        
        editerror  = SM.Transitions()  # Error that should be reportet to the user, but does not require intervention
        conerror   = SM.Transitions()  # Some kind of connection problem, to be handled by user (or wait till connection works again)


    def __init__(self, connection, dataservice):
        
        super().__init__()
        
        self._connection = connection
        self._dataservice  = dataservice
        self._id = id
        self._onlinedoc = None
        self._manager = None

        self.uuid       = str(uuid.uuid4())
        self.error      = None
        self.fcdocument = None
        
        self.addTransition(Entity.States.Undefined, Entity.States.Online.Status.Invited, Entity.Events.invited)
        self.addTransition(Entity.States.Online.Status.Unknown, Entity.States.Online.Status.Invited, Entity.Events.invited)
        self.addTransition(Entity.States.Undefined, Entity.States.Online.Status.Shared, Entity.Events.collaborate)
        self.addTransition(Entity.States.Local, Entity.States.Online.Status.Shared, Entity.Events.collaborate)
        self.addTransition(Entity.States.Online.Status.Unknown, Entity.States.Online.Status.Shared, Entity.Events.collaborate)
        self.addTransition(Entity.States.Online.Status.Invited, Entity.States.Online.Status.Shared, Entity.Events.collaborate)
        
        self.addTransition(Entity.States.Online, Entity.States.Local, Entity.Events.stopcollab)
        
        self.addTransition(Entity.States.Undefined, Entity.States.Local, Entity.Events.fcopend)
        self.addTransition(Entity.States.Online.Document.Close, Entity.States.Online.Document.Open, Entity.Events.fcopend)
        self.addTransition(Entity.States.Online.Document.Open, Entity.States.Online.Document.Close, Entity.Events.fcclosed)
        
        # Closeout
        self.addTransition(Entity.States.Undefined, Entity.States.Removed,  Entity.Events.removed)
        self.addTransition(Entity.States.Local, Entity.States.Removed,  Entity.Events.removed)
        self.addTransition(Entity.States.Online, Entity.States.Removed,  Entity.Events.removed)
        
        
    @SM.onEnter(Entity.States.Online)
    def _enterOnline(self):
        self._manager = NodeDocumentManager(self.id, self._connection)
        
    @SM.onExit(Entity.States.Online)
    async def _exitOnline(self):
        manager = self._manager
        self.manager = None
        await manager.close()
        
    @SM.onEnter(Entity.States.Online.Status.Shared)
    def _enterShared(self):
        self._onlinedoc = OnlineDocument(self.id, self._connection, self._dataservice)
        
    @SM.onExit(Entity.States.Online.Status.Shared)
    async def _exitShared(self):
        odoc = self._onlinedoc
        self,_onlinedoc = None
        await odoc.close()        
     
    @SM.onExit(Entity.States.Online.Document.Open)
    def onExitDocument(self):
        self.fcdocument = None
     
    @SM.onEnter(Entity.States.Removed)
    async def _enterRemoved(self):
        if self._manager:
            await self._manager.close()
        if self._onlinedoc:
            await self._onlinedoc._close()
    
    @property
    def node_document_manager(self):
        if not self._manager:
            raise Exception("No nodemanager available if not in Online statae")
        
        return self._manager

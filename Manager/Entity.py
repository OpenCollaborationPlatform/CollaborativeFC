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

import asyncio, uuid, os
import FreeCAD
from PySide2 import QtCore
import Utils.StateMachine as SM
from Manager.NodeDocument import NodeDocumentManager
from Documents.OnlineDocument import OnlineDocument

class Entity(SM.StateMachine):
    ''' data structure describing a entity in the collaboration framework. A entity is a things that can be calloborated on, e.g.:
        - A local Freecad document
        - A invited ocp document on the node
        - A open document on the node, not available locally 
        - etc.
    '''
    
    # State Machine UML: www.plantuml.com/plantuml/png/XLHTQzim57tNhxZjGny6-GEcX4AtmM2iM_eOGl7acrMWI46MEqh9VvybtoZ7hklv8P7EERgw7pw-QsCTOdUmgbz4fll0_LyZkmqV_4k_a-rthsjBRuhwPq0-U_shu_1AjxVwsHlDwtLcjvzsj5gj2mz7lhd8mTKMevXMU-TOfvi1l_uPlEQslQQwbSm4IQ8nKicMlACVlc5ragppZjumxcF_sxLII7faCNjlEZxKM5G5gcXW4f1PhBseCeCDU36fq0ykVt3ME8Rae4ySMKVezOpcIsEYGdosbzQtsCho857bNMdeVuC-lZez5nFmAc_ehudFuvZOE2aJAO4ok-6ZDRg_lQBjrLutNky-a8vltawq9xKqzOSZksanW5LvKrepn8CXXE23Z10hstJE6VT7lHzPFZ71xmTF6E_csAzrhEs5EAKNNkufBfR_Z6NpLlJqPDC2gLn3ObmUIV5qJnMtdlj7DpTqPPhTM8K6HkLOk3v_Js1oEIjQMTv7v7Lwyngbn4DoZJWdfMg6vLWWtacypokWttT0eX6SyqTst5oOHE7G4wy0eLLtnBpsjR7SB2dgtpx4gG0oQBnZfSexJlWTAMq1kkVHio9HWCaD44RIN1P9fikQQROoHpHUQIfWX3QMT1O4aWhogUva6qaXBNDsU4ow9UHydvGIIvRKYnahuX3IJXM8mCBbN8-1KSl92wOcj2Gg0IeABDwvn5mNTqkql5Ngx4OmUIc8Kwg0oRp0mjBePP4qUwp1vfodZfw7huXWOas9Bivhu8YwOzTq1_iF
    
    class States(SM.States):
        
        Created       = SM.InitialState()               # Entry point, used only to have a defined initial state
        Removed       = SM.FinalState()                 # Invalid entity, it was removed from the entity manager
        
        class Local(SM.GroupedStates):                  # Entity exists local in FreeCAD only
            
            Detect        = SM.InitialState()           # State to decide which kind of local document the entity is
            Internal      = SM.State()                  # Interal entity only, no node representation
            Disconnected  = SM.State()                  # Currently local only, but was on node before disconnect
            CreateProcess = SM.ProcessState()           # Creates the document on the node
        
        class Node(SM.ParallelStates):                  #  Entity is available on the OCP node, incl. error handling
                       
            class Status(SM.GroupedStates):             # States to define the exact status on the node
                Detect       = SM.InitialProcessState() # Entity exists and is online, but its unclear what state it has on the node
                Invited      = SM.State()               # Invided document on node
                OpenProcess  = SM.ProcessState()        # Opens the document on the node
               
                class Online(SM.GroupedStates):
                    Detect       = SM.InitialState()    # Check if online document is in replication or edit mode
                    Replicate    = SM.State()           # Document is replicated on the node, but not edited in the application
                    Edit         = SM.State()           # Edit state: document is ready for concurrent edit
                    SyncProcess  = SM.ProcessState()    # Syncing FreeCAD document to Node status
                    CloseProcess = SM.ProcessState()    # Closes the document on the node
            
            class Error(SM.GroupedStates):              # Error handling 
                Running         = SM.InitialState()     # No error
                ConnectionError = SM.State()            # Problems with connection of the node to the other peers: User feedback required
                EditError       = SM.State()            # User Editing did produce an error: Report only
                FatalError      = SM.State()            # Severe error that requires document shutdown and stop of everything

        
    class Events(SM.Events):
        
        open            = SM.Event()  # active:  state machine should open the entity
        opened          = SM.Event()  # passive: document was opened outside, entity state should resemble that
        close           = SM.Event()  # active:  The entity shoul be closed
        closed          = SM.Event()  # passive: document was closed outside, entity state should represent that
        
        # Connection events
        connected       = SM.Event()  # API connection esablished
        disconnected    = SM.Event()  # API connection removed
        reconnect       = SM.Event()  # If the node failed due to connection problems, but everythign works again (Used with connectionError)
        
        # Process events
        abort    = SM.Event()  # process to be abortet
        _done    = SM.Event()  # process suceeded
        _failed  = SM.Event()  # process failed
        _invited = SM.Event()  # node status is invited
        _online  = SM.Event()  # node status is online 
        
        # Error events
        editError       = SM.Event()  # Error that should be reportet to the user, but does not require intervention
        connectionError = SM.Event()  # Some kind of connection problem, to be handled by user (or wait till connection works again)
        fatalError      = SM.Event()  # Fatal error that requires shutdown of the document
        
        #initialization events
        _local         = SM.Event()  # Initial state is local
        _node          = SM.Event()  # Initial state is online


    def __init__(self, connection, dataservice, collab_path, eventblocker):
        
        super().__init__()
               
        self.__connection = connection
        self._dataservice  = dataservice
        self._id = None
        self._onlinedoc = None
        self._manager = None
        self._blocker = eventblocker
        self.__collab_path = collab_path

        self.uuid       = str(uuid.uuid4())
        self.error      = None
        self.fcdocument = None
        
        # startup transitions
        self.addTransition(Entity.States.Created, Entity.States.Local, Entity.Events._local)
        self.addTransition(Entity.States.Created, Entity.States.Node, Entity.Events._node)
        
        # local state interals
        self.addTransition(Entity.States.Local.Detect, Entity.States.Local.Internal, condition = lambda sm: self.fcdocument and not sm._id)
        self.addTransition(Entity.States.Local.Detect, Entity.States.Local.Disconnected, condition = lambda sm: self.fcdocument and sm._id)
        self.addTransition(Entity.States.Local.Detect, Entity.States.Removed, condition = lambda sm: not self.fcdocument)
        self.addTransition(Entity.States.Local.Internal, Entity.States.Local.CreateProcess, Entity.Events.open)
        self.addTransition(Entity.States.Local.CreateProcess, Entity.States.Local.Internal, Entity.Events.abort)
        self.addTransition(Entity.States.Local.CreateProcess, Entity.States.Local.Internal, Entity.Events._failed)
        self.addTransition(Entity.States.Local.CreateProcess, Entity.States.Node.Status.Online.Edit, Entity.Events._done)
        self.addTransition(Entity.States.Local.Disconnected, Entity.States.Node, self.__connection.api.reconnected)
        self.addTransition(Entity.States.Local, Entity.States.Removed, Entity.Events.closed)
        
        # node state internals
        self.addTransition(Entity.States.Node, Entity.States.Local, self.__connection.api.disconnected)
        self.addTransition(Entity.States.Node.Status.Detect, Entity.States.Node.Status.Online, Entity.Events._online)
        self.addTransition(Entity.States.Node.Status.Detect, Entity.States.Node.Status.Invited, Entity.Events._invited)
        self.addTransition(Entity.States.Node.Status.Detect, Entity.States.Local, Entity.Events._local)
        self.addTransition(Entity.States.Node.Status.Invited, Entity.States.Node.Status.Online, Entity.Events.opened)
        self.addTransition(Entity.States.Node.Status.Invited, Entity.States.Node.Status.OpenProcess, Entity.Events.open)
        self.addTransition(Entity.States.Node.Status.Invited, Entity.States.Removed, Entity.Events.closed)
        self.addTransition(Entity.States.Node.Status.OpenProcess, Entity.States.Node.Status.Detect, Entity.Events.abort)
        self.addTransition(Entity.States.Node.Status.OpenProcess, Entity.States.Node.Status.Detect, Entity.Events._failed)
        self.addTransition(Entity.States.Node.Status.OpenProcess, Entity.States.Node.Status.Online, Entity.Events._done)

        # node.online state status internals
        self.addTransition(Entity.States.Node.Status.Online.Detect, Entity.States.Node.Status.Online.Replicate, condition = lambda sm: sm.fcdocument is None)
        self.addTransition(Entity.States.Node.Status.Online.Detect, Entity.States.Node.Status.Online.SyncProcess, condition = lambda sm: sm.fcdocument is not None)
        self.addTransition(Entity.States.Node.Status.Online.SyncProcess, Entity.States.Node.Status.Online.Replicate, Entity.Events._failed)
        self.addTransition(Entity.States.Node.Status.Online.SyncProcess, Entity.States.Node.Status.Online.Replicate, Entity.Events.abort)
        self.addTransition(Entity.States.Node.Status.Online.SyncProcess, Entity.States.Node.Status.Online.Edit, Entity.Events._done)
        self.addTransition(Entity.States.Node.Status.Online.Replicate, Entity.States.Node.Status.Detect, Entity.Events.closed)
        self.addTransition(Entity.States.Node.Status.Online.Replicate, Entity.States.Node.Status.Online.SyncProcess, Entity.Events.opened)
        self.addTransition(Entity.States.Node.Status.Online.Edit, Entity.States.Node.Status.Online.Replicate, Entity.Events.closed)
        self.addTransition(Entity.States.Node.Status.Online.Edit, Entity.States.Node.Status.Online.CloseProcess, Entity.Events.close)
        self.addTransition(Entity.States.Node.Status.Online.Replicate, Entity.States.Node.Status.Online.CloseProcess, Entity.Events.close)
        self.addTransition(Entity.States.Node.Status.Online.CloseProcess, Entity.States.Node.Status.Detect, Entity.Events.abort)
        self.addTransition(Entity.States.Node.Status.Online.CloseProcess, Entity.States.Node.Status.Detect, Entity.Events._failed)
        self.addTransition(Entity.States.Node.Status.Online.CloseProcess, Entity.States.Node.Status.Detect, Entity.Events._done)
        
        # node state error internals
        self.addTransition(Entity.States.Node.Error.Running, Entity.States.Node.Error.EditError, Entity.Events.editError)
        self.addTransition(Entity.States.Node.Error.EditError, Entity.States.Node.Error.Running)
        self.addTransition(Entity.States.Node.Error.Running, Entity.States.Node.Error.ConnectionError, Entity.Events.connectionError)
        self.addTransition(Entity.States.Node.Error.ConnectionError, Entity.States.Node.Error.Running, Entity.Events.reconnect)
        self.addTransition(Entity.States.Node.Error.Running, Entity.States.Node.Error.FatalError, Entity.Events.fatalError)
        self.addTransition(Entity.States.Node.Error.EditError, Entity.States.Node.Error.FatalError, Entity.Events.fatalError)
        self.addTransition(Entity.States.Node.Error.ConnectionError, Entity.States.Node.Error.FatalError, Entity.Events.fatalError)
      

    def start(self, fcdoc=None, id=None):
        # Set the initial state of the entity
        
        # initialize the 
        if fcdoc:
            self.fcdocument = fcdoc
            if not id:
                self.processEvent(Entity.Events._local)
                return
        if id:
            self._id = id
            if self.__connection.api.connected:
                self.processEvent(Entity.Events._node)
            else:
                self.processEvent(Entity.Events._local)
            return
        
        raise Exception("Either fcdoc or id must be provided to set initial state")


    # Local substatus
    # ###############
    
    @SM.onEnter(States.Local.CreateProcess)
    async def _createDoc(self):
        # create document on node, load all available local data into it and finish. 
        # _done event leads directly to "Edit" state
        
        try:
            dmlpath = os.path.join(self.__collab_path, "Dml")
            self._id = await self.__connection.api.call(u"ocp.documents.create", dmlpath)
            
            if not self._onlinedoc:
                self._onlinedoc = OnlineDocument(self._id, self.fcdocument, self.__connection, self._dataservice)
                await self._onlinedoc.setup()
            
            # Load data into node
            await self._onlinedoc.asyncSetup()
                
            self.processEvent(Entity.Events._done)

        except asyncio.CancelledError:
            try:
                if self._onlinedoc:
                    await asyncio.wait_for(self._onlinedoc.close(), timeout=1)
            finally:
                self._onlinedoc = None
                self.processEvent(Entity.Events.abort)
            
        except Exception as e:
            try:
                if self._onlinedoc:
                    await asyncio.wait_for(self._onlinedoc.close(), timeout=1)
            finally:
                self._onlinedoc = None          
                self.error = e
                self.processEvent(Entity.Events._failed)


    @SM.transition(States.Local.Internal, States.Removed, Events.close)
    def _closeLocalDoc(self):
        with self._blocker:
            if self.fcdocument:
                FreeCAD.closeDocument(self.fcdocument.Name)
                self.fcdocument=None
    
    @SM.transition(States.Local.Disconnected, States.Local.Internal, Events.close)
    def _closeDisconnectedDoc(self):
        self._id = None

    # Node substatus
    # ##############
           
    @SM.onEnter(States.Node.Status.Detect)
    async def _detectNodeStatus(self):

        try:
            status = await self.__connection.api.call(u"ocp.documents.status", self._id)
            if status == "open":
                self.processEvent(Entity.Events._online)
            elif status == "invited":
                # if we are invited and have a local document, we need to spawn a new entity
                # this could happen if we have a close event in edit state, where only the 
                # node part is closed
                if not self.fcdocument:
                    self.processEvent(Entity.Events._invited)
                else:
                    id = self.id
                    self.id = None
                    self._onSpwanInvitedEntity(id)
                    self.processEvent(Entity.Events._local)
            else:
                # go local. If there is no fcdocument we go to removed from there
                self.processEvent(Entity.Events._local)
        
        except Exception as e:
            print("detect error: ", e)
            self.processEvent(Entity.Events._local)


    @SM.onEnter(States.Node.Status.OpenProcess)
    async def _openInvited(self):
               
        try:
            await self.__connection.api.call(u"ocp.documents.open", self._id)
            self.processEvent(Entity.Events._done)
       
        except asyncio.CancelledError:
            self.processEvent(Entity.Events.abort)
        except Exception as e:
            self.error = e
            self.processEvent(Entity.Events._failed)


    # Node Online substatus
    # #####################

    @SM.onEnter(States.Node.Status.Online)
    def _enterOnline1(self):
        # we need to setup the manager imediately, not with asyncio delay, as other callbacks for the state
        # may acces it
        self._manager = NodeDocumentManager(self._id, self.__connection)

    @SM.onEnter(States.Node.Status.Online)
    async def _enterOnline2(self):
        # setup the manager delayed after creation
        await self._manager.setup()
        
    @SM.onExit(States.Node.Status.Online)
    async def _exitOnline(self):
        manager = self._manager
        self._manager = None
        await manager.close()
    
    @SM.onEnter(States.Node.Status.Online.SyncProcess)
    async def _syncDoc(self):
        
        try:
            if not self._onlinedoc:
                self._onlinedoc = OnlineDocument(self._id, self.fcdocument, self.__connection, self._dataservice)
                await self._onlinedoc.setup()
            
            await self._onlinedoc.asyncLoad()
            self.processEvent(Entity.Events._done)
                
        except asyncio.CancelledError:
            try:
                if self._onlinedoc:
                    await asyncio.wait_for(self._onlinedoc.close(), timeout=1)
            finally:
                self._onlinedoc = None
                self.processEvent(Entity.Events.abort)
            
        except Exception as e:
            try:
                if self._onlinedoc:
                    await asyncio.wait_for(self._onlinedoc.close(), timeout=1)
            finally:
                self._onlinedoc = None          
                self.error = e
                self.processEvent(Entity.Events._failed)


    @SM.onExit(States.Node.Status.Online.Edit)
    async def _exitShared(self):
        try:
            odoc = self._onlinedoc
            self._onlinedoc = None
            await asyncio.wait_for(odoc.close(), timeout=5)
        except Exception as e:
            print("Failed close online doc: ", e)
            
    @SM.transition(States.Node.Status.Online.Replicate, States.Node.Status.Online.SyncProcess, Events.open)
    def _openDoc(self):
        with self._blocker:
            self.fcdocument = FreeCAD.newDocument("Unnamed")
 
            
    @SM.onEnter(States.Node.Status.Online.CloseProcess)
    async def _closeNode(self):
               
        try:
            await self.__connection.api.call(u"ocp.documents.close", self._id)
            self.processEvent(Entity.Events._done)
       
        except asyncio.CancelledError:
            self.processEvent(Entity.Events.abort)
        except Exception as e:
            self.error = e
            self.processEvent(Entity.Events._failed)
 
 
    # Cleanup and general stuff
    # #########################
 
    _onSpwanInvitedEntity = QtCore.Signal(str)
 
    @SM.onFinish
    async def _close(self):
        if self._manager:
            await self._manager.close()
        if self._onlinedoc:
            await self._onlinedoc._close()
    
    @property
    def node_document_manager(self):
        
        # if called in StateMachine __init__ we may not yet have it defined
        if not hasattr(self, "_manager"):
            return None

        return self._manager
    
    @property
    def online_document(self):
        
        # if called in StateMachine __init__ we may not yet have it defined
        if not hasattr(self, "_onlinedoc"):
            return None

        return self._onlinedoc
    
    @property
    def id(self):
        # if called in StateMachine __init__ we may not yet have it defined
        if not hasattr(self, "_id"):
            return None

        return self._id
    
    @property
    def status(self) -> str:
        # returns the the name of the currently active status
        
        # relevant: local, removed, invited, shared
        relevant = [Entity.States.Local,  Entity.States.Node.Status.Invited,  Entity.States.Node.Status.Online.Replicate, Entity.States.Node.Status.Online.Edit, Entity.States.Removed]
        active = self.activeStates

        for state in relevant:
            if state in active:
                # return only name after last .
                return state.name.split('.')[-1]
            
        return "Unknown"
    
    async def collaborate(self, timeout = 10):
        # convienience function to bring the entity into collaboration state
        
        if Entity.States.Node.Status.Online.Edit in self.activeStates:
            return
        
        elif Entity.States.Local in self.activeStates:
            
            self.processEvent(Entity.Events.open)
            await self.state(Entity.States.Node.Status.Online.Edit).waitTillActive(timeout = timeout)
            return
        
        elif Entity.States.Node.Status.Invited in self.activeStates:
            
            self.processEvent(Entity.Events.open)
            await self.state(Entity.States.Node.Status.Online.Replicate).waitTillActive(timeout = timeout)
            self.processEvent(Entity.Events.open)
            await self.state(Entity.States.Node.Status.Online.Edit).waitTillActive(timeout = timeout)
            return
        
        elif Entity.States.Node.Status.Online.Replicate in self.activeStates:
            self.processEvent(Entity.Events.open)
            await self.state(Entity.States.Node.Status.Online.Edit).waitTillActive(timeout = timeout)
            return
        
        
        raise Exception("Current state does not allow collaboration")


    async def stopCollaboration(self, timeout = 10):
        #convinience function to stop collaboration 
        
        if Entity.States.Local in self.activeStates:
            return
        
        elif Entity.States.Node.Status.Online in self.activeStates:
            self.processEvent(Entity.Events.close)
            await self.state(Entity.States.Local).waitTillActive(timeout = timeout)
            return
        
        raise Exception("Current state does not allow closing the collaboration")
            

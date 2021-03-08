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

import asyncio
import Helper
from enum import Enum, auto
from PySide import QtCore
from qasync import asyncSlot

class ManagedDocument(QtCore.QObject, Helper.AsyncSlotObject):
    # Helps to manage documents on the OCP node, manages naming and peers
    
    class __Peer():
        def __init__(self, id, auth, joined):
            self.nodeid = id
            self.auth = auth
            self.joined = joined
    
    def __init__(self, id, connection):
        QtCore.QObject.__init__(self)
        
        self.peers = []
        self.__docId = id
        self.__connection = connection
        self.__readyEvt = asyncio.Event()
        
        connection.api.connectedChanged.connect(self.__connectChanged)
        asyncio.ensure_future(self.__asyncInit())
    
    
    async def __asyncInit(self):
        
        # fetch the currently registered peers as well as the active ones
        # (no await, as is async slot)
        self.__connectChanged()
        
        # subscribe to peer update, registration and active
        self.__subkey = f"ManagedDocument_{self.__docId}"
        await self.__connection.api.subscribe(self.__subkey, self.__peerAuthChanged,  f"ocp.documents.{self.__docId}.peerAuthChanged")
        await self.__connection.api.subscribe(self.__subkey, self.__peerActivityChanged,  f"ocp.documents.{self.__docId}.peerActivityChanged")
        await self.__connection.api.subscribe(self.__subkey, self.__peerAdded,  f"ocp.documents.{self.__docId}.peerAdded")
        await self.__connection.api.subscribe(self.__subkey, self.__peerRemoved,  f"ocp.documents.{self.__docId}.peerRemoved")
        self.__readyEvt.set()
      
    async def ready(self):
        await self.__readyEvt.wait()

    async def close(self):
        #unsubscribe the events
        await self.__connection.api.closeKey(self.__subkey)
    
    
    # Managing functions
    # *************************************************************
    
    async def addPeer(self, peer, auth):
        
        uri = f"ocp.documents.{self.__docId}.addPeer"
        await self.__connection.api.call(uri, peer, auth)
    
    async def removePeer(self, peer):
        
        uri = f"ocp.documents.{self.__docId}.removePeer"
        await self.__connection.api.call(uri, peer)
    
    async def changePeerAuth(self, peer, auth):
        
        uri = f"ocp.documents.{self.__docId}.setPeerAuth"
        await self.__connection.api.call(uri, peer, auth)
    
        
    # Callbacks, OCP API and node document
    # *************************************************************
    
    @asyncSlot()
    async def __connectChanged(self):
        
        if self.__connection.api.connected:
            readPeers = await self.__connection.api.call(f"ocp.documents.{self.__docId}.listPeers", auth="Read")
            writePeers = await self.__connection.api.call(f"ocp.documents.{self.__docId}.listPeers", auth="Write")
            joinedPeers = await self.__connection.api.call(f"ocp.documents.{self.__docId}.listPeers", joined=True)
            
            for peer in readPeers:
                self.peers.append(ManagedDocument.__Peer(peer, "Read", peer in joinedPeers))
            
            for peer in writePeers:
                self.peers.append(ManagedDocument.__Peer(peer, "Write", peer in joinedPeers))
            
            self.memberCountChanged.emit()
            self.joinedCountChanged.emit()
            
        else:
            self.peers = []
            self.memberCountChanged.emit()
            self.joinedCountChanged.emit()
            
            
    async def __peerAuthChanged(self, id, auth):
        peer = self.__getPeer(id)
        if peer:
            peer.auth = auth
            self.peerChanged.emit(peer)
    
    async def __peerActivityChanged(self, peer, joined):
        peer = self.__getPeer(id)
        if peer:
            peer.joined = joined        
            self.peerChanged.emit(peer)
            self.joinedCountChanged.emit()
    
    async def __peerAdded(self, id, auth):
        self.peers.append(ManagedDocument.__Peer(id, auth, False))
            
        self.peerAdded.emit(id)
        self.__memberCountChanged.emit()
    
    async def __peerRemoved(self, id):
        peer = self.__getPeer(id)
        if peer:
            self.peers.remove(peer)
            self.peerRemoved.emit(id)
            self.memberCountChanged.emit()


    def getPeer(self, id):
        for peer in self.peers:
            if peer.nodeid == id:
                return  peer
        
        return None

    # Qt Implementations
    # **********************************************************************
    
    peerAdded   = QtCore.Signal(str)
    peerRemoved = QtCore.Signal(str)
    peerChanged = QtCore.Signal(str)

    def __getName(self):
        return "ToBeImplemented"
    
    def __getMemberCount(self):
        return len(self.peers)
    
    def __getJoinedCount(self):     
        count = 0
        for peer in self.peers:
            if peer.joined:
                count += 1

        return count
    
    nameChanged         = QtCore.Signal()
    memberCountChanged  = QtCore.Signal()
    joinedCountChanged  = QtCore.Signal()
    
    name        = QtCore.Property(str, __getName, notify=nameChanged)
    memberCount = QtCore.Property(int, __getMemberCount, notify=memberCountChanged)
    joinedCount = QtCore.Property(int, __getJoinedCount, notify=joinedCountChanged)

    @Helper.AsyncSlot(str)
    def setNameSlot(self, name):
        print(f"SetName with {name}")

    @Helper.AsyncSlot(str)
    async def removePeerSlot(self, peer):
        await self.removePeer(peer)

    @Helper.AsyncSlot(str)
    async def togglePeerRigthsSlot(self, peer):
        
        auth = self.peers.peerAuth(peer)
        if auth == "Write":
            await self.changePeerAuth(peer, "Read")
        else:
            await self.changePeerAuth(peer, "Write")

    @Helper.AsyncSlot(str, bool)
    async def addPeerSlot(self, id, edit):
        auth = "Read"
        if edit:
            auth = "Write"
                
        await self.addPeer(id, auth)

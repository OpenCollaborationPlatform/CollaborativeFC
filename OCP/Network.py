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

import asyncio
from PySide import QtCore
from qasync import asyncSlot

class Network(QtCore.QObject):
    # Provides information about the OCP network. Uses the API conenction to the OCP node
       
    def __init__(self, api, logger):        
        
        QtCore.QObject.__init__(self)
        
        # internal state
        self.__api    = api
        self.__peers  = QtCore.QStringListModel()
        self.__addrs  = QtCore.QStringListModel()
        self.__id     = "Unknown"
        self.__logger = logger
        self.__reachability = "Unknown"
        
        self.__api.connectedChanged.connect(self.__apiChanged)
        
        asyncio.ensure_future(self.__asyncInit())
        
        
    async def __asyncInit(self):
        # connect all events we want to listen on
        await self.__api.subscribe("network", self.__reachabilityChange, "ocp.p2p.reachabilityChanged")
        await self.__api.subscribe("network", self.__peerConnected, "ocp.p2p.peerConnected")
        await self.__api.subscribe("network", self.__peerDisconnected, "ocp.p2p.peerDisconnected")


    def testSlot(self):
        pass


    @asyncSlot()
    async def __apiChanged(self):
        
        if self.__api.connected:
            peers = await self.__api.call("ocp.p2p.peers")
            self.__logger.debug(f"Connected to {len(peers)} peers")
            self.__peers.setStringList(peers)
            self.__peerCountChanged.emit()
            
            addrs = await self.__api.call("ocp.p2p.addresses", False)
            self.__addrs.setStringList(addrs)
            
            id = await self.__api.call("ocp.p2p.id")            
            reach = await self.__api.call("ocp.p2p.reachability")
            
        
        else:
            self.__peers.setStringList([])
            self.__peerCountChanged.emit()
            self.__addrs.setStringList([])
            id  = "Unknown"
            reach = "Unknown"
            
        if self.__reachability != reach:
            self.__reachability = reach
            self.__reachabilityChanged.emit()
                
        if self.__id != id:
            self.__id  = id
            self.__nodeIdChanged.emit()
    

    async def __reachabilityChange(self, status):
        self.__reachability  = status
        self.__reachabilityChanged.emit()
    
    async def __peerConnected(self, peer):
        
        self.__logger.debug(f"Connected to peer {peer}")
        peers = self.__peers.stringList()
        if not peer in peers:
            peers.append(peer)
            self.__peers.setStringList(peers)
            self.__peerCountChanged.emit()
        
    async def __peerDisconnected(self, peer):
        
        self.__logger.debug(f"Disconnected from peer {peer}")
        
        peers = self.__peers.stringList()
        if peer in peers:
            peers.remove(peer)
            self.__peers.setStringList(peers)
            self.__peerCountChanged.emit()
        
    
    
    # Qt Property/Signal API used from the UI
    # ********************************************************************************************
    
    # signals for property change (needed to have QML update on property change) and asyncslot finish
    __nodeIdChanged       = QtCore.Signal()
    __reachabilityChanged = QtCore.Signal()
    __peerCountChanged    = QtCore.Signal()
    

    @QtCore.Property(str, notify=__reachabilityChanged)
    def reachability(self):
        return self.__reachability
    
    @QtCore.Property(str, notify=__nodeIdChanged)
    def nodeId(self):
        return self.__id
    
    @QtCore.Property(int, notify=__peerCountChanged)
    def peerCount(self):
        return self.__peers.rowCount()
   
    def peersGetter(self):
        return self.__peers

    peers = QtCore.Property(QtCore.QObject, peersGetter, constant=True)
    
    def addressesGetter(self):
        return self.__addrs

    addresses = QtCore.Property(QtCore.QObject, addressesGetter, constant=True)
    

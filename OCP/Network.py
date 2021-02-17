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
        self.__id     = "unknown"
        self.__logger = logger
        self.__reachability = "not reachable"
        
        
        #slot = self.__apiChanged
        #print(slot)
        
        #print(dir(self.__api.connectedChanged))
        #self.__api.testSignal.connect(self.testSlot)
        
        asyncio.ensure_future(self.__asyncInit())
        
        
    async def __asyncInit(self):
        # connect all events we want to listen on
        await self.__api.subscribe(self.reachabilityChanged, "ocp.p2p.reachabilityChanged")
        await self.__api.subscribe(self.connectionChanged, "ocp.p2p.peerChanged")


    def testSlot(self):
        pass

    @asyncSlot()
    async def __apiChanged(self):
        
        if self.__api.connected:
            peers = await self.__api.call("ocp.p2p.peers")
            self.__peers.setStringList(peers)
            
            peers = await self.__api.call("ocp.p2p.addresses")
            self.__addrs.setStringList(peers)
            
            id = await self.__api.call("ocp.p2p.id")            
            reach = await self.__api.call("ocp.p2p.reachability")
            
        
        else:
            self.__peers.setStringList([])
            self.__addrs.setStringList([])
            id  = "unknown"
            reach = "not reachable"
            
        if self.__reachability != reach:
            self.__reachability = id
            self.__reachabilityChanged.emit()
                
        if self.__id != id:
            self.__id  = id
            self.__idChanged.emit()
    

    async def reachabilityChanged(self, status):
        print(f"reachability changed: {status}")
    
    async def connectionChanged(self, peer, status):
        print(f"connection changed: {peer}, {status}")
    
    
    # Qt Property/Signal API used from the UI
    # ********************************************************************************************
    
    #signals for property change (needed to have QML update on property change) and asyncslot finish
    #__idChanged           = QtCore.Signal()
    #__reachabilityChanged = QtCore.Signal()
    

    #@QtCore.Property(str, notify=__reachabilityChanged)
    #def reachability(self):
    #    return self.__reachability
    
    #def peersGetter(self):
    #    return self.__peers

    #peers = QtCore.Property(QtCore.QObject, peersGetter, constant=True)
    
    #def addressesGetter(self):
    #    return self.__addrs

    #addresses = QtCore.Property(QtCore.QObject, addressesGetter, constant=True)
    

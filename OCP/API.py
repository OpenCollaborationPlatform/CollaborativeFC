
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


import asyncio, logging
from autobahn.asyncio.component import Component
from PySide2 import QtCore
from qasync import asyncSlot
import FreeCAD

class API(QtCore.QObject):
    #Class to handle the WAMP connection to the OCP node
       
    def __init__(self, node, logger):
        
        QtCore.QObject.__init__(self)
        
        self.__node = node
        self.__wamp = None
        self.__session = None        
        self.__readyEvent = asyncio.Event()
        self.__registered = []
        self.__subscribed = []
        self.__logger = logger
        self.__settings = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod").GetGroup("Collaboration")

        # connect to node ready events for auto reconnect
        self.__node.runningChanged.connect(self.__nodeChange)

    
    async def waitTillReady(self):
        await self.__readyEvent.wait()
        
   
    async def connectToNode(self):
        
        self.__logger.debug(f"Try to connect")
        
        if not self.__node.running:
            raise Exception("Cannot connect API if node is not running")
        
        if self.connected:
            return
        
        #make the OCP node connection!            
        uri = f"ws://{self.__node.apiUri}:{self.__node.apiPort}/ws"
        self.__wamp = Component(  transports={
                                    "url":uri,
                                    "serializers": ['msgpack'],
                                    "initial_retry_delay": 10
                                },
                                realm = "ocp")
        self.__wamp.on('join', self.__onJoin)
        self.__wamp.on('leave', self.__onLeave)
        self.__wamp.on('ready', self.__onReady)

        #run the component
        self.__wamp.start()
        
        
    async def disconnectFromNode(self):

        # close the connection
        self.__logger.debug(f"Try to disconnect")
        if self.__wamp:
            await self.__wamp.stop()
            self.__wamp = None
   
    
    async def register(self, *args, **kwargs):
        # Registers an API function. It stays registered over multiple session and reconnects
        
        self.__logger.debug(f"Register function {args[1]}")
        self.__registered.append((args, kwargs))
        if self.connected:
            return await self.__session.register(*args, **kwargs)
    
    
    async def subscribe(self, *args, **kwargs):
        # Subscribe to API event. It stays subscribed over multiple session and reconnects
        
        self.__logger.debug(f"Subscribe event {args[1]}")
        self.__subscribed.append((args, kwargs))
        if self.connected:
            return await self.__session.subscribe(*args, **kwargs)
            
            
    async def call(self, *args, **kwargs):
        # calls api function
        
        self.__logger.debug(f"Call {args[0]}")
        if not self.connected: 
            raise Exception("Not connected to Node, cannot call API function")
        
        return await self.__session.call(*args, **kwargs)
        
    
    # Node callbacks
    # ********************************************************************************************
    
    @asyncSlot()
    async def __nodeChange(self):
        
        self.__logger.debug(f"Node change callback, node running: {self.__node.running}")
        
        if self.reconnect and self.__node.running:
            await self.connectToNode()
            
        if self.__wamp and not self.__node.running:
            await self.disconnectFromNode()
    
    
    # Wamp callbacks
    # ********************************************************************************************
    
    async def __onJoin(self, session, details):
       
        self.__logger.debug(f"Join WAMP session")
        self.__session = session
        
        # register all functions
        for args in self.__registered:
            await self.__session.register(*(args[0]), **(args[1]))
            
        # subscribe to all events
        for args in self.__subscribed:
            await self.__session.subscribe(*(args[0]), **(args[1]))
                    
            
    async def __onLeave(self, session, reason):
        
        self.__readyEvent.clear()
        self.__session = None
        self.connectedChanged.emit()            
        self.__logger.info("connection closed")
        
            
    async def __onReady(self, *args):
        self.connectedChanged.emit()
        self.__readyEvent.set()
        self.__logger.info("connection ready")
       
        
    # Qt Property/Signal API used from the UI
    # ********************************************************************************************
    
    #signals for property change (needed to have QML update on property change)
    connectedChanged         = QtCore.Signal()
    __reconnectChanged       = QtCore.Signal()
    __connectSlotFinished    = QtCore.Signal()
    __disconnectSlotFinished = QtCore.Signal()

    @QtCore.Property(bool, notify=connectedChanged)
    def connected(self):
        return self.__session != None
    
    
    def getReconnect(self):
        return self.__settings.GetBool("APIReconnect", True)
    
    def setReconnect(self, value):
       self.__settings.SetBool("APIReconnect", value)
       self.__reconnectChanged.emit()
       
    reconnect = QtCore.Property(bool, getReconnect, setReconnect, notify=__reconnectChanged)
 
    @asyncSlot()
    async  def disconnectSlot(self):
        await self.disconnectFromNode()
        self.__disconnectSlotFinished.emit()
        
    @asyncSlot()
    async def connectSlot(self):

        await self.connectToNode()
        await self.waitTillReady()
        self.__connectSlotFinished.emit()
        
            
        

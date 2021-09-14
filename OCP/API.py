
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
from autobahn import wamp
from PySide2 import QtCore
from Qasync import asyncSlot
import Utils
import FreeCAD


class API(QtCore.QObject, Utils.AsyncSlotObject):
    #Class to handle the WAMP connection to the OCP node
       
    def __init__(self, node, logger):
        
        QtCore.QObject.__init__(self)
        
        self.__node = node
        self.__wamp = None
        self.__session = None        
        self.__readyEvent = asyncio.Event()
        self.__registered = {}          # key: [(args, kwargs)]
        self.__registeredSessions = {}  # key: [sessions]
        self.__subscribed = {}
        self.__subscribedSessions = {}
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
        self.__wamp.on('disconnect', self.__onDisconnect)
        self.__wamp.on('ready', self.__onReady)

        #run the component
        self.__wamp.start()
        
        
    async def disconnectFromNode(self):

        # close the connection
        self.__logger.debug(f"Try to disconnect")
        if self.__wamp:
            await self.__wamp.stop()
            self.__wamp = None
   
    
    async def register(self, key, *args, **kwargs):
        # Registers an API function. It stays registered over multiple session and reconnects
        # Can be unregistered with the given key. Note: multiple register and subscribe calls can be 
        # made with a single key
                
        self.__registered[key] = self.__registered.get(key, []) + [(args, kwargs)]
        if self.connected:
            try:
                self.__registeredSessions[key] = self.__registeredSessions.get(key, [])  + [await self.__session.register(*args, **kwargs)]
            except:
                pass
    
    
    async def subscribe(self, key, *args, **kwargs):
        # Subscribe to API event. It stays subscribed over multiple session and reconnects
               
        self.__subscribed[key] = self.__subscribed.get(key, []) + [(args, kwargs)]
        if self.connected:
            try:
                self.__subscribedSessions[key] = self.__subscribedSessions.get(key, [])  + [await self.__session.subscribe(*args, **kwargs)]
            except:
                pass
    
    
    async def closeKey(self, key):

        if key in self.__registered:
            #remove register entries and close sessions
            del self.__registered[key]
            for session in self.__registeredSessions.pop(key, []):
                await session.unregister()          
        
        if key in self.__subscribed:
            #remove subscribe entries and close sessions
            del self.__subscribed[key]
            for session in self.__subscribedSessions.pop(key, []):
                await session.unsubscribe()

            
    async def call(self, *args, **kwargs):
        # calls api function
        
        if not self.connected: 
            raise Exception("Not connected to Node, cannot call API function")
        
        # add a default timeout if the caller did no do already
        if "options" in kwargs:
            opts = kwargs["options"]
            if not opts.timeout:
                opts.timeout = 5000
        else:
            kwargs["options"] = wamp.CallOptions(timeout=5000)
            
        # call
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
        for key, argsList in self.__registered.items():
            
            sessions = []
            for args in argsList:
                sessions.append(await self.__session.register(*(args[0]), **(args[1])))
            
            self.__registeredSessions[key] = sessions
            
        # subscribe to all events
        for key, argsList in self.__subscribed.items():
            
            sessions = []
            for args in argsList:
                sessions.append(await self.__session.subscribe(*(args[0]), **(args[1])))
            
            self.__subscribedSessions[key] = sessions
                    
            
    async def __onLeave(self, session, reason):
        
        self.__logger.debug(f"Leave WAMP session: {reason}")
        
        # clear all registered and subscribed session objects
        self.__registeredSessions = {}
        self.__subscribedSessions = {}
        
        self.__readyEvent.clear()
        self.__session = None
        
        self.connectedChanged.emit()            
        
        
    async def __onDisconnect(self, *args, **kwargs):
        self.__logger.info("API closed")
        
        
    async def __onReady(self, *args):
        self.connectedChanged.emit()
        self.__readyEvent.set()
        self.__logger.info("API ready")
       
        
    # Qt Property/Signal API used from the UI
    # ********************************************************************************************
    
    #signals for property change (needed to have QML update on property change)
    connectedChanged         = QtCore.Signal()
    __reconnectChanged       = QtCore.Signal()


    @QtCore.Property(bool, notify=connectedChanged)
    def connected(self):
        return self.__session != None
    
    
    def getReconnect(self):
        return self.__settings.GetBool("APIReconnect", True)
    
    QtCore.Slot(bool)
    def setReconnect(self, value):
       self.__settings.SetBool("APIReconnect", value)
       self.__reconnectChanged.emit()
       
    reconnect = QtCore.Property(bool, getReconnect, setReconnect, notify=__reconnectChanged)
 
    @Utils.AsyncSlot()
    async  def toggleConnectedSlot(self):
        if self.connected:
            await self.disconnectFromNode()
        else:
            await self.connectToNode()
            await self.waitTillReady()           


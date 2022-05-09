
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


import asyncio, logging, uuid
from asyncio.queues import Queue
from autobahn.asyncio.component import Component
from autobahn import wamp
from PySide2 import QtCore
from Qasync import asyncSlot
import Utils
import FreeCAD

class _Session():
    # Abstraction of a wamp session with extra functionality for reconnecting
    
    def __init__(self, id, index, readyCB, leaveCB):
        
        self.__id  = id
        self.index = index
        self.__readyCB = readyCB
        self.__leaveCB = leaveCB
        
        self.__wamp = None
        self.__session = None
        
        self.__registered = {}          # key: [(args, kwargs)]
        self.__registeredSessions = {}  # key: [sessions]
        self.__subscribed = {}
        self.__subscribedSessions = {}

    @property
    def connected(self):
        return self.__session != None

    def connect(self, uri, port):
        
        if self.connected:
            return

        url = f"ws://{uri}:{port}/ws"
        self.__wamp = Component(transports={
                                    "url":url,
                                    "serializers": ['msgpack'],
                                    "initial_retry_delay": 10
                                },
                                realm = "ocp",
                                authentication={
                                    "anonymous": {
                                        "authid": str(self.__id),
                                    }
                                },
                                )
        self.__wamp.on('join', self.__onJoin)
        self.__wamp.on('leave', self.__onLeave)
        self.__wamp.start()


    async def disconnect(self):
        
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
        
        if not self.connected: 
            raise Exception("Not connected to Node, cannot call API function")
        
        # add a default timeout if the caller did no do already
        if "options" in kwargs:
            opts = kwargs["options"]
            if not opts.timeout:
                opts.timeout = 10000
        else:
            kwargs["options"] = wamp.CallOptions(timeout=10000)
            
        # call
        return await self.__session.call(*args, **kwargs)


    # Wamp callbacks
    # ********************************************************************************************
    
    async def __onJoin(self, session, details):
       
        self.__session = session
        
        res = await session.call("wamp.session.get", details.session)
        print(res)
        
        # in case we get a subscribe/register call during execution
        registered = self.__registered.copy()
        subscribed = self.__subscribed.copy()
        
        # register all functions
        for key, argsList in registered.items():
            
            sessions = []
            for args in argsList:
                sessions.append(await self.__session.register(*(args[0]), **(args[1])))
            
            self.__registeredSessions[key] = sessions
            
        # subscribe to all events
        for key, argsList in subscribed.items():
            
            sessions = []
            for args in argsList:
                sessions.append(await self.__session.subscribe(*(args[0]), **(args[1])))
            
            self.__subscribedSessions[key] = sessions
            
        self.__readyCB(self.index)                    
            
    async def __onLeave(self, session, reason):
               
        # clear all registered and subscribed session objects
        self.__registeredSessions = {}
        self.__subscribedSessions = {}
        self.__session = None
        
        self.__leaveCB(self.index)


class API(QtCore.QObject, Utils.AsyncSlotObject):
    #Class to handle the WAMP connection to the OCP node
    
    _numSessions = 100
    
    def __init__(self, node, logger):
        
        QtCore.QObject.__init__(self)

        self.__id = uuid.uuid4()        
        self.__sessions = [_Session(self.__id, i, self.__onReady, self.__onLeave) for i in range(API._numSessions)]
        self.__queue = Queue(API._numSessions)
        self.__waiting = 0
        
        self.__node = node
        self.__readyEvent = asyncio.Event()
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
        
        # close the connection
        for session in self.__sessions:
            session.connect(self.__node.apiUri, self.__node.apiPort)
                
        
    async def disconnectFromNode(self):

        # close the connection
        for session in self.__sessions:
            await session.disconnect()
   
    
    async def register(self, key, *args, **kwargs):
        # Registers an API function. It stays registered over multiple session and reconnects
        # Can be unregistered with the given key. Note: multiple register and subscribe calls can be 
        # made with a single key
        
        regopts = [isinstance(s,wamp.RegisterOptions) for s in args]
        if any(regopts):
            opts = args[regopts.index(True)]
            opts.invoke = 'roundrobin'        
        elif "options" in kwargs:
            opts = kwargs["options"]
            opts.invoke = 'roundrobin'
        else:
            args.append(wamp.RegisterOptions(invoke='roundrobin'))
                
        for session in self.__sessions[1:]:
            await session.register(key, *args, **kwargs)
    
    
    async def subscribe(self, key, *args, **kwargs):
        # Subscribe to API event. It stays subscribed over multiple session and reconnects
        
        await self.__sessions[0].subscribe(key, *args, **kwargs)
    
    
    async def closeKey(self, key):
        # remove all registered and subscribed functions for the given key

        for session in self.__sessions:
            await session.closeKey(key)
            
    async def call(self, *args, **kwargs):
        # calls api function
                
        if not self.connected:
            raise Exception("Not connected to Node, cannot call API function")
        
        # get the next valid session. This means poping sessions until we get a connected one.
        # Note: It can happen that we disconnect while waiting for a session. This means the queue 
        # get emptied and we will wait forever. To prevent this, None object will be added to the queue
        # in this event. Receiving this means we raise an "not connected error"           
        
        self.__waiting += 1
        
        session = await self.__queue.get()
        while session and not session.connected:
            session = await self.__queue.get()
          
        if session is None:
            raise Exception("Not connected to Node, cannot call API function")
        
        try:
            self.__waiting -= 1
            result = await session.call(*args, **kwargs)
            return result

        finally:
            if session.connected:
                self.__queue.put_nowait(session)
 
            
    # Node callbacks
    # ********************************************************************************************
    
    @asyncSlot()
    async def __nodeChange(self):
        
        self.__logger.debug(f"Node change callback, node running: {self.__node.running}")
        
        if self.reconnect and self.__node.running:
            await self.connectToNode()
            
        if self.connected and not self.__node.running:
            await self.disconnectFromNode()
    
    
    # Session callbacks
    # ********************************************************************************************
    
    def __onReady(self, sessionidx):
       
        self.__queue.put_nowait(self.__sessions[sessionidx])
        
        if not self.__readyEvent.is_set():
            self.reconnected.emit()
            self.connectedChanged.emit()
            self.__readyEvent.set()
            self.__logger.info("WAMP API ready")
                    
            
    def __onLeave(self, sessionidx):
               
        if not self.connected:
            self.__logger.debug(f"Leave WAMP session: {reason}")
            
            # clear all registered and subscribed session objects
            self.__registeredSessions = {}
            self.__subscribedSessions = {}
            
            self.__readyEvent.clear()
            
            self.disconnected.emit()
            self.connectedChanged.emit()
            
            # close all waiting calls, as there will be no more sessions in the queue
            for v in [None]*self.__waiting:
                self.__queue.put_nowait(v)
            
            self.__logger.info("WAMP API closed")

        
    # Qt Property/Signal API used from the UI
    # ********************************************************************************************
    
    #signals for property change (needed to have QML update on property change)
    connectedChanged         = QtCore.Signal()
    reconnected              = QtCore.Signal()
    disconnected             = QtCore.Signal()
    __reconnectChanged       = QtCore.Signal()


    @QtCore.Property(bool, notify=connectedChanged)
    def connected(self):
        return any([s.connected for s in self.__sessions])
    
    
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


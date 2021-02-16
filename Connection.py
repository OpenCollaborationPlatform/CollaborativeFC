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


import asyncio, txaio, os
from autobahn.asyncio.component import Component
from qasync import QEventLoop
from PySide import QtCore
from qasync import asyncSlot
from OCP.Node import OCPNode


#Class to handle all connection matters to the ocp node
#must be provided all components that need to use this connection
class OCPConnection(QtCore.QObject):
       
    def __init__(self, *argv):
        
        QtCore.QObject.__init__(self)
        
        self.__node = OCPNode()
        self.session = None 
        
        #make sure asyncio and qt work together
        app = QtCore.QCoreApplication.instance()
        loop = QEventLoop(app)
        txaio.config.loop = loop #workaround as component.start(loop=) does not propagate the loop correctly
        asyncio.set_event_loop(loop)       
        
        #run the conenction asyncronously but not blocking
        #self.__readyEvent = asyncio.Event()
        #asyncio.ensure_future(self.__startup())
   
    
    async def ready(self):
        await self.__readyEvent.wait()
        
   
    async def __startup(self):

        #run the node
        await self.__node.run()
        
        #make the OCP node connection!            
        uri = f"ws://{self.__node.apiUri}:{self.__node.apiPort}/ws"
        self.__wamp = Component(  transports={
                                    "url":uri,
                                    "serializers": ['msgpack']
                                },
                                realm = "ocp")
        self.__wamp.on('join', self.__onJoin)
        self.__wamp.on('leave', self.__onLeave)

        #blocks till all wamp handling is finsihed
        await self.__wamp.start()
        
        
    async def __shutdown(self):

        # close the connection
        await self.__wamp.stop()
        self.__wamp = None
        
        # close the node
        await self.__node.shutdown()
        
    
    # Wamp callbacks
    # ********************************************************************************************
    
    async def __onJoin(self, session, details):
        print("Connection to OCP node established")
       
        self.session = session
        self.connectedChanged.emit()
        self.__readyEvent.set()
            
            
    async def __onLeave(self, session, reason):
        print("Connection to OCP node lost: ", reason)
        
        self.__readyEvent.clear()
        self.session = None
        self.connectedChanged.emit()           
       
        
    # Qt Property/Signal API used from the UI
    # ********************************************************************************************
    
    #signals for property change (needed to have QML update on property change)
    connectedChanged = QtCore.Signal()
    shutdownFinished = QtCore.Signal()
    startupFinished  = QtCore.Signal()

    @QtCore.Property(bool, notify=connectedChanged)
    def connected(self):
        return self.session != None
    
    def nodeGetter(self):
        return self.__node

    node = QtCore.Property(QtCore.QObject, nodeGetter, constant=True)

    @asyncSlot
    async  def shutdown(self):
        await self.__shutdown()
        self.shutdownFinished.emit()
        
    @asyncSlot
    async def startup(self):
        
        async def signaler():
            await self.ready()
            self.startupFinished.emit()
        
        asyncio.ensure_future(signaler())
        
        #note: calling startup blocks till shutdown. But asyncslot uses ensure future, so this is ok
        await self.__startup()
        
            
        

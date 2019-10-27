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


import asyncio, subprocess
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from asyncqt import QEventLoop
from PySide import QtCore

#Helper class to call the running node via CLI
class OCPNode():
    
    def __init__(self):
        #initialize the ocp node!
        self.ocp = '/home/stefan/Projects/Go/CollaborationNode/CollaborationNode'

    def init(self):
        subprocess.call([self.ocp, 'init'])

    def port(self):
        output = subprocess.check_output([self.ocp, 'config', 'connection.port'])
        port = output.decode('ascii').replace('\n', "") 
        return port
      
    def uri(self):
        output = subprocess.check_output([self.ocp, 'config', 'connection.uri'])
        uri = output.decode('ascii').replace('\n', "") 
        return uri 
    
    def start(self):
        output = subprocess.check_output([self.ocp])
        if len(output.decode('ascii').split('\n')) < 3:
            subprocess.Popen([self.ocp, 'start'])
            
    def setup(self):
        self.init()
        self.start()

#The wamp session for the connection to the OCP node
class OCPSession(ApplicationSession):

    def __init__(self, cfg):
        super().__init__(cfg)
        self.parent = cfg.extra['parent']
        self.parent.session = self

    async def onJoin(self, details):
        self.parent.onJoin()
        print("We have joined, yeahh!")

    def onDisconnect(self):
        self.parent.onLeave()
        print("We have disconnected")

#Class to handle all connection matters to the ocp node
# must be provided all components that need to use this connection
class OCPConnection():
        
    def __init__(self, *argv):
        
        self.node = OCPNode()
        self.session = None 
        self.components = list(argv)        
        
        #make sure asyncio and qt work together
        app = QtCore.QCoreApplication.instance()
        loop = QEventLoop(app)
        asyncio.set_event_loop(loop)
        
        #setup the node
        self.node.setup()
        
        #make the connection!
        uri = "ws://" + self.node.uri() + ":" + self.node.port() + "/ws"
        self.runner = ApplicationRunner(uri, "ocp", extra={'parent': self})
        coro = self.runner.run(OCPSession, start_loop=False)
        asyncio.get_event_loop().run_until_complete(coro)
        
    def onJoin(self):
        #startup all relevant components
        for comp in self.components:
            comp.setConnection(self)
            
    def onLeave(self):
        #startup all relevant components
        for comp in self.components:
            comp.removeConnection()

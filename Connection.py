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


import asyncio, subprocess, os
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from autobahn.wamp.serializer import MsgPackSerializer
from asyncqt import QEventLoop
from PySide import QtCore

#Helper class to call the running node via CLI
class OCPNode():
    
    def __init__(self):
        self.ocp = '/home/stefan/Projects/Go/CollaborationNode/CollaborationNode'
        self.test = False
        
        #for testing we need to connect to a dedicated node       
        if os.getenv('OCP_TEST_RUN', "0") == "1":
            #we are in testing mode! check out the required node to connect to
            print("OCP test mode detected")
            self.test = True
            self.conf = os.getenv("OCP_TEST_NODE_CONFIG", "none")
            
            if self.conf == "none":
                raise("Testmode is set, but no config file name provided")

    def init(self):

        if self.test:
            #no initialisation needed in test run!
            print("Test mode: no initialization required")
            return
            
        subprocess.call([self.ocp, 'init'])


    def port(self):
        
        args = [self.ocp, 'config', '-o', 'connection.port']
        if self.test:
            args.append("--config")
            args.append(self.conf)
            
        output = subprocess.check_output(args)
        port = output.decode('ascii').replace('\n', "") 
        return port
    
      
    def uri(self):
        
        args = [self.ocp, 'config', '-o', 'connection.uri']
        if self.test:
            args.append("--config")
            args.append(self.conf)
            
        output = subprocess.check_output(args)
        uri = output.decode('ascii').replace('\n', "") 
        return uri 
    
    
    def start(self):
        
        if self.test:
            #in test mode we do not start our own node!
            print("Test mode: no own node startup!")
            return
        
        args = [self.ocp]
        output = subprocess.check_output(args)
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
        
        
#The wamp session for the connection to the OCP node
class OCPTestSession(ApplicationSession):

    def __init__(self, cfg):
        super().__init__(cfg)


    async def onJoin(self, details):
        print("Connection to test server established")


    def onDisconnect(self):
        print("Connection to test server lost")
        

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
        try:
            uri = "ws://" + self.node.uri() + ":" + self.node.port() + "/ws"
            msgpack = MsgPackSerializer()
            self.runner = ApplicationRunner(uri, "ocp", extra={'parent': self}, serializers=[msgpack])
            coro = self.runner.run(OCPSession, start_loop=False)
            asyncio.get_event_loop().run_until_complete(coro)
            
            if os.getenv('OCP_TEST_RUN', "0") == "1":
                uri = os.getenv('OCP_TEST_SERVER_URI', '')
                self.runner = ApplicationRunner(uri, "ocptest")
                coro = self.runner.run(OCPTestSession, start_loop=False)
                asyncio.get_event_loop().run_until_complete(coro)
            
        except Exception as e:
            print("Unable to connect to OCP network: " + str(e))

        
    def onJoin(self):
        #startup all relevant components
        for comp in self.components:
            comp.setConnection(self)
            
    def onLeave(self):
        #startup all relevant components
        for comp in self.components:
            comp.removeConnection()

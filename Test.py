# ************************************************************************
# *   Copyright (c) Stefan Troeger (stefantroeger@gmx.net) 2020          *
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

import asyncio, os, logging
from autobahn.asyncio.component import Component
from autobahn.wamp.types import SubscribeOptions

import FreeCAD, FreeCADGui

class ErrorFilter(logging.Filter):
    #Logging filter that raises exception when Error occurs

    def filter(self, record):
        if record.levelname == "ERROR":
            raise Exception(f"Error was logged for {record.name}: {record.getMessage()}")
        
        return True
    

class Handler():
    
    def __init__(self, connection, manager):
           
        if os.getenv('OCP_TEST_RUN', "0") != "1":
            raise Exception("Test Handler created, but test environment variable not set")
          
        self.__manager = manager  
        self.__session = None
        self.__logger  = logging.getLogger("Test handler")
        
        #register the Error raise filter to ensure that during testing all errror messages lead to test stop
        #Note: Attach to handler, as adding to logger itself does not propagate to child loggers
        #logging.getLogger().handlers[0].addFilter(ErrorFilter())
        
        #run the handler
        asyncio.ensure_future(self._startup(connection))
        
          
    async def _startup(self, connection):
        
        
        self.__connection = connection
        await connection.api.waitTillReady()
        
        #register ourself to the OCP node
        await connection.api.subscribe("testhandler", self.__receiveSync, "ocp.documents..content.Document.sync", options=SubscribeOptions(match="wildcard"))
        
        #connect to testserver       
        uri = os.getenv('OCP_TEST_SERVER_URI', '')
        self.test = Component(transports=uri, realm = "ocptest")
        self.test.on('join', self.__onJoin)
        self.test.on('leave', self.__onLeave)
        
        self.test.start()
    
    
    async def __onJoin(self, session, details):
        #litte remark that we joined (needed for test executable, it waits for this)
        FreeCAD.Console.PrintMessage("Connection to OCP test server established\n")
        
        #store the session for later use
        self.__session = session
        
        #get all the testing functions in this class!
        methods = [func for func in dir(self) if callable(getattr(self, func))]
        rpcs = [rpc for rpc in methods if '_rpc' in rpc]
    
        #build the correct uri 
        uri = os.getenv('OCP_TEST_RPC_ADDRESS', '')
        if uri == '':
            raise ('No rpc uri set for testing')
        
        for rpc in rpcs:
            rpc_uri = uri + "." + rpc[len('_rpc'):]
            await session.register(getattr(self, rpc), rpc_uri)
    
        #inform test framework that we are set up!
        try:
            await session.call("ocp.test.triggerEvent", uri, True)
        except Exception as e:
            print("Exception in event call: ", str(e))
        
    
    async def __onLeave(self, session, reason):
        
        self.__session = None
        
        #inform test framework that we are not here anymore!
        await session.call("ocp.test.triggerEvent", os.getenv('OCP_TEST_RPC_ADDRESS', ''), False)


    async def waitTillCloseout(self, docId, timeout=30):
        # wait till all tasks in the document with given ID are finished
        try:
            for entity in self.__manager.getEntities():
                if entity.onlinedoc != None and entity.id == docId:
                    await entity.onlinedoc.waitTillCloseout(timeout)
                    return True
            
            return False
                    
        except Exception as e: 
            print(f"Trigger syncronize failed, cannot wait for closeout of current actions: {e}")
            return False


    async def synchronize(self, docId, numFCs):
        #Syncronize all other involved FC instances. When this returns one can call waitForSync on the TestServer. The numFCs must not 
        #include the FC instance it is called on, only the remaining ones
        #Note:
        #   We trigger the FC instances to sync themself via the DML doc. This is to make sure that the sync is called only after all 
        #   operations have been received by the FC instance. 
        #   1. Do all known opeations
        #   2. Emit sync event in DML document
        
        self.__logger.debug(f"Start syncronisation for: {docId[-5:]}")
                
        #we wait till all tasks are finished
        if not await self.waitTillCloseout(docId):
            return
 
        #register the sync with the testserver
        await self.__session.call("ocp.test.registerSync", docId, numFCs)
        
        #and now issue the event that all FC instances know that they should sync.
        self.__logger.debug(f"Work done, trigger sync events via dml: {docId[-5:]}")
        uri = f"ocp.documents.{docId}.content.Document.sync"
        await self.__connection.api.call(uri, docId)

     
    async def  __receiveSync(self, docId):
        #received a sync event from DML document
        # 1. Wait till all actions are finished
        # 2. Inform the TestServer, that we are finished
        
        self.__logger.debug(f"Request for sync received: {docId[-5:]}")
        #await asyncio.sleep(0.05)
        
        #wait till everything is done!
        try:
            entities = self.__manager.getEntities()
            for entity in entities:
                if entity.id == docId:
                    await entity.onlinedoc.waitTillCloseout(30)
                    
        except Exception as e: 
            print(f"Participation in syncronize failed, cannot wait for closeout of current actions: {e}")
            return

        #call testserver that we received and executed the sync!
        self.__logger.debug("Work done, send sync event")
        await self.__session.call("ocp.test.sync", docId)

    
    async def _rpcShareDocument(self, name):
        pass
    
    async def _rpcUnshareDocument(self, name):
        pass
    
    
    async def _rpcAddNodeToDocument(self):
        pass
    
    async def _rpcExecuteCode(self, code):
        
        code.insert(0, "import FreeCADGui as Gui")
        code.insert(0, "import FreeCAD as App")
        
        exec(
            f'async def __ex(): ' +
            ''.join(f'\n {line}' for line in code)
        )

        return await locals()['__ex']()



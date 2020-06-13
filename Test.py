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

import asyncio, os
from autobahn.asyncio.component import Component
from autobahn.wamp.types import SubscribeOptions

import FreeCAD, FreeCADGui

class Handler():
    
    def __init__(self, connection, manager):
           
        if os.getenv('OCP_TEST_RUN', "0") != "1":
            raise Exception("Test Handler created, but test environment variable not set")
          
        self.__manager = manager  
        self.__session = None
        
        asyncio.ensure_future(self._startup(connection))
        
          
    async def _startup(self, connection):
        
        self.__connection = connection
        await connection.ready()
        
        #register ourself to the OCP node
        await connection.session.subscribe(self.__receiveSync, "ocp.documents.edit..events.Document.sync", options=SubscribeOptions(match="wildcard"))
        
        #connect to testserver       
        uri = os.getenv('OCP_TEST_SERVER_URI', '')
        self.test = Component(transports=uri, realm = "ocptest")
        self.test.on('join', self.__onJoin)
        self.test.on('leave', self.__onLeave)
        
        #block till all handling is done
        await self.test.start()
    
    
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
        print("trigger event: ", uri)
        try:
            await session.call("ocp.test.triggerEvent", uri, True)
        except Exception as e:
            print("Exception in event call: ", str(e))
        
    
    async def __onLeave(self, session, reason):
        
        self.__session = None
        
        #inform test framework that we are not here anymore!
        await session.call("ocp.test.triggerEvent", os.getenv('OCP_TEST_RPC_ADDRESS', ''), False)


    async def synchronize(self, docId, numFCs):
                
        #we wait till all tasks are finished
        coros =  []
        for entity in self.__manager.getEntities():
            if entity.onlinedoc != None:
                coros.append(entity.onlinedoc.waitTillCloseout(20))
                
        await asyncio.wait(coros)
 
        #register the sync with the testserver
        await self.__session.call("ocp.test.registerSync", docId, numFCs)
        
        #and now issue the event
        uri = f"ocp.documents.edit.{docId}.call.Document.sync"
        await self.__connection.session.call(uri, docId)

     
    async def  __receiveSync(self, docId):
        
        #wait till everything is done!
        entities = self.__manager.getEntities()
        for entity in entities:
            if entity.id == docId:
                await entity.onlinedoc.waitTillCloseout(20)
                
        #wait for online observer as well
        

        #call testserver that we received and executed the sync!
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



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

import FreeCAD, FreeCADGui

class Handler():
    
    def __init__(self, connection, dochandler):
           
        if os.getenv('OCP_TEST_RUN', "0") != "1":
            raise Exception("Test Handler created, but test environment variable not set")
          
        self.dochandler = dochandler          
        asyncio.ensure_future(self._startup(connection))
        
          
    async def _startup(self, connection):
        
        await connection.ready()
        
        uri = os.getenv('OCP_TEST_SERVER_URI', '')
        self.test = Component(transports=uri, realm = "ocptest")
        self.test.on('join', self.onJoin)
        self.test.on('leave', self.onLeave)
        
        #block till all handling is done
        await self.test.start()
    
    
    async def onJoin(self, session, details):
        #litte remark that we joined (needed for test executable, it waits for this)
        FreeCAD.Console.PrintMessage("Connection to OCP test server established\n")
        
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
        
    
    async def onLeave(self, session, reason):
        #inform test framework that we are not here anymore!
        await session.call("ocp.test.triggerEvent", os.getenv('OCP_TEST_RPC_ADDRESS', ''), False)

    
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



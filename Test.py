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

class Handler():
    
    def __init__(self, dochandler):
           
        if os.getenv('OCP_TEST_RUN', "0") != "1":
            raise Exception("Test Handler created, but test environment variable not set")
          
        self.dochandler = dochandler          
        asyncio.ensure_future(self._startup())
        
          
    async def _startup(self):
        
        uri = os.getenv('OCP_TEST_SERVER_URI', '')
        self.test = Component(transports=uri, realm = "ocptest")
        self.test.on('join', self.onJoin)
        self.test.on('leave', self.onLeave)
        
        #block till all handling is done
        await self.test.start()
    
    
    async def onJoin(self, session, details):
        
        #get all the testing functions in this class!
        methods = [func for func in dir(self) if callable(getattr(self, func))]
        rpcs = [rpc for rpc in methods if '_rpc' in rpc]
    
        #build the correct uri 
        uri = os.getenv('OCP_TEST_RPC_ADDRESS', '')
        if uri == '':
            raise ('No rpc uri set for testing')
        
        for rpc in rpcs:
            rpc_uri = uri + "." + rpc[len('_rpc'):]
            session.register(getattr(self, rpc), uri)
    
    
    async def onLeave(self, session, reason):
        pass


    async def _rpcNewSharedDocument(self):
        pass
    
    async def _rpcUserToDocument(self):
        pass
    
    async def _rpcJoinSharedDocument(self):
        pass

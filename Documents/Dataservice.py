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

import asyncio
from autobahn.wamp.types import RegisterOptions

class DataService():
    
    def __init__(self, fcid, connection):
        self.__keyCntr = 0
        self.__data = {}
        self.uri = u'freecad.{0}.dataUpload'.format(fcid)
        self.__connection = connection
        self.__readyEvt = asyncio.Event()
        
        asyncio.ensure_future(self.__asyncInit())
        
    async def __asyncInit(self):
        await self.__connection.api.register("dataservice", self.__dataUpload, self.uri, RegisterOptions(details_arg='details'))
        self.__readyEvt.set()
    
    async def ready(self):
        await self.__readyEvt.wait()
    
    async def close(self):
        await self.__connection.api.closeKey("dataservice")
    
    def addData(self, data):
        key = self.__keyCntr
        self.__data[key] = data
        self.__keyCntr += 1
        return key
        
    def getData(self, key):
        if key not in self.__data:
            return bytearray()
        
        data = self.__data[key]
        del self.__data[key]
        return data
    
    async def __dataUpload(self, key, details=None):

        if details.progress:
            data = self.getData(key)
            size = 1024*256 #should be 0.25mb
            for i in range(0, len(data), size):
                block = data[i:i+size]
                details.progress(bytes(block))
                
        else: 
            return bytes(self.getData(key))

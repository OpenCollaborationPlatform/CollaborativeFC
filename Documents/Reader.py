#  ************************************************************************
#  *   Copyright (c) Stefan Troeger (stefantroeger@gmx.net) 2021          *
#  *                                                                      *
#  *   This library is free software; you can redistribute it and/or      *
#  *   modify it under the terms of the GNU Library General Public        *
#  *   License as published by the Free Software Foundation; either       *
#  *   version 2 of the License, or (at your option) any later version.   *
#  *                                                                      *
#  *   This library  is distributed in the hope that it will be useful,   *
#  *   but WITHOUT ANY WARRANTY; without even the implied warranty of     *
#  *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the      *
#  *   GNU Library General Public License for more details.               *
#  *                                                                      *
#  *   You should have received a copy of the GNU Library General Public  *
#  *   License along with this library; see the file COPYING.LIB. If not, *
#  *   write to the Free Software Foundation, Inc., 59 Temple Place,      *
#  *   Suite 330, Boston, MA  02111-1307, USA                             *
#  ************************************************************************

import asyncio, FreeCAD
import Documents.Property as Property
from autobahn.wamp.types  import CallOptions

class OCPObjectReader():
    ''' Reads object data from the OCP node document
    
        This class provides async functions to read FreeCAD object data from the OCP node. It uses the 
        online documents connection to the node to inquire the object. 
        
        Notes:        
        1. A reader is responsible for a single named freecad object
        2. Reader can be DocumentObject or ViewProvider
           
        Init:
        name      - Name of the FC object
        fytype    - type of FC object as used in DML ("Object" or "ViewProvider")
        onlinedoc - The onlinedocument that handles the FC document the FC object belongs to
        logger    - The logger to use for messaging
    '''
    
    
    def __init__(self, name, fctype, onlinedoc, logger):
        
        self.logger             = logger
        self.docId              = onlinedoc.id
        self.connection         = onlinedoc.connection
        self.name               = name
        self.objGroup           = fctype
  
    async def isAvailable(self):
        try:
            uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.Has"
            return await self.connection.api.call(uri, self.name)
        except Exception as e:
            self.logger.error(f"Queriying availablitiy failed: {e}")
    
    
    async def propertyList(self):
        # returns a list of all property names in the object
        
        try:
            uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.{self.name}.Properties.Keys"
            return await self.connection.api.call(uri)
        
        except Exception as e:
            self.logger.error(f"Fetching property list failed: {e}")
    
    
    async def property(self,  prop):
        # reads the given property
        
        try:
            uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.{self.name}.Properties.{prop}.GetValue"
            value = await self.connection.api.call(uri)
            return await self.__getBinaryValues(value)
        
        except Exception as e:
            self.logger.error(f"Reading property {prop} failed: {e}")
    
    
    async def properties(self,  props):
        # reads all the properties and returns a list of values ordered like the properties
        
        try:
            values = [None]*len(props)
            async def fetch(index, prop):
                uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.{self.name}.Properties.{prop}.GetValue"
                values[index] = await self.connection.api.call(uri)
            
            tasks = []
            for i, prop in enumerate(props):
                tasks.append(fetch(i, prop))
                
            if tasks:
                await asyncio.gather(*tasks)
                
            return await self.__getBinaryValues(values)
        
        except Exception as e:
            self.logger.error(f"Reading properties {props} failed: {e}")
    
    
    async def propertyInfo(self, prop):
        # returns the property info structure for given property
        
        try:
            uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.{self.name}.Properties.{prop}.GetInfo"
            return await self.connection.api.call(uri)
        
        except Exception as e:
            self.logger.error(f"Reading property info for {prop} failed: {e}")
            
    
    async def propertiesInfos(self, props):
        # returns the info structs for all the properties in the same order
        
        try:
            infos = [None]*len(props)
            async def fetch(index, prop):
                uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.{self.name}.Properties.{prop}.GetInfo"
                infos[index] = await self.connection.api.call(uri)
            
            tasks = []
            for i, prop in enumerate(props):
                tasks.append(fetch(i, prop))
                
            if tasks:
                await asyncio.gather(*tasks)
                
            return infos
        
        except Exception as e:
            self.logger.error(f"Reading properties infos for {props} failed: {e}")
        

    async def extensions(self):
        # returns all registered extensions
        try:
            uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.{self.name}.Extensions.GetAll"
            return await self.connection.api.call(uri)
        
        except Exception as e:
            self.logger.error(f"Fetching object extensions failed: {e}")
        
        
    # internal functions
    # ****************************************+++
    
    async def __getBinaryValues(self, values):
        # checks all values for binary Cid's and fetches the real data to replace it with
        
        if not isinstance(values, list):
            values = [values]
        
        tasks = []
        for index, value in enumerate(values):
            
            if isinstance(value, str) and value.startswith("ocp_cid"):                   
                
                async def worker(index, cid):
                    class Data():
                        def __init__(self): 
                            self.data = bytes()
                                    
                        def progress(self, update):
                            self.data += bytes(update)
                            
                    # get the binary data
                    uri = f"ocp.documents.{self.docId}.raw.BinaryByCid"
                    dat = Data()
                    opt = CallOptions(on_progress=dat.progress)
                    result = await self.connection.api.call(uri, cid, options=opt)
                    if result is not None:
                        dat.progress(result)
                        
                    values[index] = dat.data
                    
                tasks.append(worker(index, value))
        
        if tasks:
            tasks = [asyncio.create_task(task) for task in tasks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            exceptions = [i for i in results if isinstance(i, Exception)]
            if exceptions:
                self.logger.error(f"Getting binary data from node failed: {exceptions[0]}")
                raise exceptions[0]
        
        if len(values) == 1:
            return values[0]
        return values

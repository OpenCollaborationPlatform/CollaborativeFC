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
import Documents.Property as Property
from Documents.OnlineObserver import OnlineObserver
from Documents.OnlineObject import OnlineObject
from autobahn.wamp.exception import ApplicationError

class OnlineDocument():

    def __init__(self, id, doc, observer, connection, dataservice):
        self.id = id
        self.document = doc
        self.connection = connection 
        self.objIds = {}
        self.data = dataservice
        self.onlineObs = OnlineObserver(observer, self)
        self.objects = {}
        
        print("new online document created")
    
    
    def newObject(self, obj):
        #create the async runner for that object
        oobj = OnlineObject(obj, self)
        self.objects[obj.Name] = oobj
        oobj.setup()
     
     
    def removeObject(self, obj):
        #create the async runner for that object
        oobj = self.objects[obj.Name]
        del(self.objects[obj.Name])
        oobj.remove()
        
        
    def changeObject(self, obj, prop):
        if obj.Name not in self.objects:
            return
        
        oobj = self.objects[obj.Name]
        oobj.changeProperty(prop)
    
    
    def newDynamicProperty(self, obj, prop):
        if obj.Name not in self.objects:
            return
        
        oobj = self.objects[obj.Name]
        oobj.createDynamicProperty(prop)
        
        
    def removeDynamicProperty(self, obj, prop):
        if obj.Name not in self.objects:
            return
        
        oobj = self.objects[obj.Name]
        oobj.removeDynamicProperty(prop)


    def recomputObject(self, obj):
        if obj.Name not in self.objects:
            return
        
        oobj = self.objects[obj.Name]
        oobj.recompute()
        

    async def asyncSetup(self):
        #loads the freecad doc into the online doc 
        pass
    
    async def asyncLoad(self):
        #loads the online doc into the freecad doc
        pass
    
    async def asyncUnload(self):
        pass
    
    async def asyncGetDocumentPeers(self):
        try:
            res = await self.connection.session.call(u"ocp.documents.{0}.listPeers".format(self.id))
            return res.results[0]
        
        except Exception as e:
            print("Listing peers error: {0}".format(e))
            return []      
 

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

import asyncio, logging
import Documents.Property as Property
from Documents.OnlineObserver import OnlineObserver
from Documents.OnlineObject import OnlineObject, OnlineViewProvider
from autobahn.wamp.exception import ApplicationError

class OnlineDocument():
    ''' Describing a FreeCAD document in the OCP framework. Properties can be changed or objects added/removed 
        like with a normal FreeCAD document, with the difference, that all changes are mirrored to all collabrators.
        Changes to the online doc do not change anything on the local one. The intenion is to mirror all user changes 
        done to the local document'''

    def __init__(self, id, doc, observer, connection, dataservice):
        self.id = id
        self.document = doc
        self.connection = connection 
        self.objIds = {}
        self.data = dataservice
        self.onlineObs = OnlineObserver(observer, self)
        self.objects = {}
        self.viewproviders = {}
        self.logger = logging.getLogger("Document " + id[-5:])
        
        self.logger.debug("Created")
 
  
    def shouldExcludeTypeId(self, typeid):
        #we do not add App origins, lines and planes, as they are only Autocreated from parts and bodies
        if typeid in ["App::Origin", "App::Line", "App::Plane"]:
                return True
            
        return False
    
    def newObject(self, obj):
        
        if self.shouldExcludeTypeId(obj.TypeId):
            return
        
        self.logger.debug("New object {0}".format(obj.Name))
        
        #create the async runner for that object
        oobj = OnlineObject(obj, self)
        self.objects[obj.Name] = oobj
        oobj.setup()
     
     
    def removeObject(self, obj):
        
        if self.shouldExcludeTypeId(obj.TypeId):
            return
        
        #create the async runner for that object
        oobj = self.objects[obj.Name]
        del(self.objects[obj.Name])
        oobj.remove()
        
        
    def changeObject(self, obj, prop):
        
        if self.shouldExcludeTypeId(obj.TypeId):
            return
        
        if obj.Name not in self.objects:
            return
        
        oobj = self.objects[obj.Name]
        oobj.changeProperty(prop)
    
    
    def changePropertyStatus(self, obj, prop):
        
        if self.shouldExcludeTypeId(obj.TypeId):
            return
        
        if obj.Name not in self.objects:
            return
        
        oobj = self.objects[obj.Name]
        oobj.changePropertyStatus(prop)
    
    
    def newDynamicProperty(self, obj, prop):
        
        if self.shouldExcludeTypeId(obj.TypeId):
            return
        
        if obj.Name not in self.objects:
            return
        
        oobj = self.objects[obj.Name]
        oobj.createDynamicProperty(prop)
        
        
    def removeDynamicProperty(self, obj, prop):
        
        if self.shouldExcludeTypeId(obj.TypeId):
            return
        
        if obj.Name not in self.objects:
            return
        
        oobj = self.objects[obj.Name]
        oobj.removeDynamicProperty(prop)


    def addDynamicExtension(self, obj, extension, props):
        if self.shouldExcludeTypeId(obj.TypeId):
            return
        
        if obj.Name not in self.objects:
            return
        
        oobj = self.objects[obj.Name]
        oobj.addDynamicExtension(extension, props)
        

    def recomputObject(self, obj):
        
        if self.shouldExcludeTypeId(obj.TypeId):
            return
        
        if obj.Name not in self.objects:
            return
        
        oobj = self.objects[obj.Name]
        oobj.recompute()
    
    
    def hasViewProvider(self, vp):
        ovps = self.viewproviders.values()
        for ovp in ovps:
            if ovp.obj is vp:
                return True
        
        return False
    
    
    def newViewProvider(self, vp):
        
        if self.shouldExcludeTypeId(vp.Object.TypeId):
            return
        
        #create the online view provider for that object
        ovp = OnlineViewProvider(vp, self)
        self.viewproviders[vp.Object.Name] = ovp
        ovp.setup()
     
     
    def removeViewProvider(self, vp):
        
        if self.shouldExcludeTypeId(vp.Object.TypeId):
            return
        
        #create the async runner for that object
        ovp = self.viewproviders[vp.Object.Name]
        del(self.viewproviders[vp.Object.Name])
        ovp.remove()
        
        
    def changeViewProvider(self, vp, prop):
        
        if self.shouldExcludeTypeId(vp.Object.TypeId):
            return
        
        if vp.Object.Name not in self.viewproviders:
            return
        
        ovp = self.viewproviders[vp.Object.Name]
        ovp.changeProperty(prop)
    
    
    def changeViewProviderPropertyStatus(self, vp, prop):
        
        if self.shouldExcludeTypeId(vp.Object.TypeId):
            return
        
        if vp.Object.Name not in self.viewproviders:
            return
        
        ovp = self.viewproviders[vp.Object.Name]
        ovp.changePropertyStatus(prop)
        
    
    def newViewProviderDynamicProperty(self, vp, prop):
        
        if self.shouldExcludeTypeId(vp.Object.TypeId):
            return
        
        if vp.Object.Name not in self.viewproviders:
            return
        
        ovp = self.viewproviders[vp.Object.Name]
        ovp.createDynamicProperty(prop)
        
        
    def removeViewProviderDynamicProperty(self, vp, prop):
        
        if self.shouldExcludeTypeId(vp.Object.TypeId):
            return
        
        if vp.Object.Name not in self.viewproviders:
            return
        
        ovp = self.viewproviders[vp.Object.Name]
        ovp.removeDynamicProperty(prop)


    def addViewProviderDynamicExtension(self, vp, extension, props):
        if self.shouldExcludeTypeId(vp.Object.TypeId):
            return
        
        if vp.Object.Name not in self.viewproviders:
            return
        
        ovp = self.viewproviders[vp.Object.Name]
        ovp.addDynamicExtension(extension, props)


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
            return await self.connection.session.call(u"ocp.documents.{0}.listPeers".format(self.id))
        
        except Exception as e:
            self.logger.error("Getting peers error: {0}".format(e))
            return []
        
        
    async def waitTillCloseout(self, timeout = 10):
        #wait till all current async tasks are finished. Note that it also wait for task added during the wait period.
        #throws an error on timeout.
        
        coros = []
        for obj in list(self.objects.values()):
            coros.append(obj.waitTillCloseout(timeout))
 
        await asyncio.wait(coros)

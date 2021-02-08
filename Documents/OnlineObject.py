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

# This module provides FC object translation layers beween the syncronous FreeCAD execution and asyncronous 
# OCP node document. The classes provide a normal python API and create and execute async actions from 
# those calls. The sync API is non blocking, and all errors and cleanups are also processed async.


import FreeCAD
import asyncio, logging, os
import Documents.Batcher as Batcher
import Documents.Property as Property
from Documents.AsyncRunner import BatchedOrderedRunner, DocumentRunner
from Documents.Writer import OCPObjectWriter


class FreeCADOnlineObject():
    
    def __init__(self, name, onlinedoc, objGroup, parentOnlineObj = None):
        
        self.logger = logging.getLogger(objGroup[:-1] + " " + name)
                
        # check which type of async runner to use 
        if os.getenv('FC_OCP_SYNC_MODE', "0") == "1":
            self.logger.info('Use non-default sync mode "Document-Sync"')
            self._runner     = DocumentRunner.getSenderRunner(onlinedoc.id, self.logger)
        
        else:
            if parentOnlineObj is None:
                self._runner     = BatchedOrderedRunner(self.logger) #used by the object to sync outgoing events
            else:
                self._runner     = parentOnlineObj._runner

        self.Writer = OCPObjectWriter(name, objGroup, onlinedoc, self.logger)


    async def _docPrints(self):
        uri = u"ocp.documents.{0}.prints".format(self._docId)
        vals = await self.connection.session.call(uri)
        for val in vals:
            self.logger.debug(val)


    async def waitTillCloseout(self, timeout = 10):
        #wait till all current async tasks are finished. Note that it also wait for task added during the wait period.
        #throws an error on timeout.        
        await self._runner.waitTillCloseout(timeout)

        
    async def close(self):   
        await self._runner.close()

        
    def synchronize(self, syncer):
        self._runner.sync(syncer)


class OnlineObject(FreeCADOnlineObject):
    
    def __init__(self, obj, onlinedoc):
        
        super().__init__(obj.Name, onlinedoc, "Objects")
        self.recomputeCache = {}
        self.obj            = obj
        
        batchers = [Batcher.EquallityBatcher("OnlineObject.__addDynamicProperty", self.Writer.processDynamicPropertyAdditions),
                    Batcher.EquallityBatcher("OnlineObject.__changeProperty", self.Writer.processPropertyChanges),
                    Batcher.EquallityBatcher("OnlineObject.__changePropertyStatus", self.Writer.processPropertyStatusChanges)
        ]
        
        for batcher in batchers:
            self._runner.registerBatcher(batcher)

        cbs = [b.copy() for b in batchers]            
        self._runner.registerBatcher(Batcher.MultiBatcher(cbs))
        
        
    def setup(self, syncer=None):
        values = {}
        infos = {}
        for prop in self.obj.PropertiesList:
            values[prop] = Property.convertPropertyToWamp(self.obj, prop)
            infos[prop]  = Property.createInformation(self.obj, prop)
            
        #check if we need to handle a document syncronisation
        if syncer:
            self._runner.sync(syncer)
            
        self._runner.run(self.Writer.setup, self.obj.TypeId, values, infos)
        
        #check if there are properties that need the defult values uploaded
        props = Property.getNonDefaultValueProperties(self.obj)
        for prop in props:
            self._runner.run(self.Writer.changeProperty, prop, Property.convertPropertyToWamp(self.obj, prop), [])

    
    def isSettingUp(self):
        return self.Writer.setupStage
    
    def remove(self):
        self._runner.run(self.Writer.remove)
        
        #we cannot use the runner to run close on itself, because it would wait for itself till it finishs: 
        #that is a guaranteed timeout
        async def __closeout():
            #waits till runner finished all tasks and than closes it
            await self._runner.close()
            
        asyncio.ensure_future(__closeout())
        

    def createDynamicProperty(self, prop):
        info = Property.createInformation(self.obj, prop)
        self._runner.run(self.__addDynamicProperty, prop, info)
        
    def __addDynamicProperty(self, prop, info):
        #indirection for batcher named tasks
        self.Writer.addDynamicProperty(prop, info)
    
    
    def removeDynamicProperty(self, prop):
        #we need to make sure the remove comes after the creation
        self._runner.run(self.Writer.removeProperty, prop)
    
    
    def addDynamicExtension(self, extension, props):
        infos = []
        for prop in props:
            infos.append(Property.createInformation(self.obj, prop))
        self._runner.run(self.Writer.addExtension, extension, props, infos)
    
    
    def changeProperty(self, prop):
        value = Property.convertPropertyToWamp(self.obj, prop)
        outlist = [obj.Name for obj in self.obj.OutList]
        self._runner.run(self.__changeProperty, prop, value, outlist)
        
    def __changeProperty(self, prop, value, outlist):
        #indirection for batcher named tasks
        self.Writer.changeProperty(prop, value, outlist)

 
    def changePropertyStatus(self, prop):
        info = Property.createInformation(self.obj, prop)        
        self._runner.run(self.__changePropertyStatus, prop, info["status"])
        
    def __changePropertyStatus(self, prop, info):
        #indirection for batcher named tasks
        self.Writer.changePropertyStatus(prop, info)
        
    
    def recompute(self):      
        self._runner.run(self.Writer.objectRecomputed)
     
     

class OnlineViewProvider(FreeCADOnlineObject):
    
    def __init__(self, obj, onlineobj, onlinedoc):        
        super().__init__(obj.Object.Name, onlinedoc, "ViewProviders", parentOnlineObj=onlineobj)
        self.obj = obj
        self.proxydata = None   #as FreeCAD 0.18 does not forward viewprovider proxy changes we need a way to identify changes
        
        batchers = [Batcher.EquallityBatcher("OnlineViewProvider.__addDynamicProperty", self.Writer.processDynamicPropertyAdditions),
                    Batcher.EquallityBatcher("OnlineViewProvider.__changeProperty", self.Writer.processPropertyChanges),
                    Batcher.EquallityBatcher("OnlineViewProvider.__changePropertyStatus", self.Writer.processPropertyStatusChanges)
        ]
        
        for batcher in batchers:
            self._runner.registerBatcher(batcher)
            
        cbs = [b.copy() for b in batchers]            
        self._runner.registerBatcher(Batcher.MultiBatcher(cbs))
        
          
    def setup(self, sync=None):
        
        if float(".".join(FreeCAD.Version()[0:2])) == 0.18:
            #part of the FC 0.18 no proxy change event workaround
            if hasattr(self.obj, 'Proxy'):
                self.proxydata = self.obj.Proxy
        
        #collect all property values and infos
        values = {}
        infos = {}
        for prop in self.obj.PropertiesList:
            values[prop] = Property.convertPropertyToWamp(self.obj, prop)
            infos[prop]  = Property.createInformation(self.obj, prop)
            
        #check if we need to handle a syncronisation
        if sync:
            self._runner.sync(sync)
         
        #setup ourself
        self._runner.run(self.Writer.setup, self.obj.TypeId, values, infos)
        
        #check if there are properties that need the defult values uploaded
        props = Property.getNonDefaultValueProperties(self.obj)
        for prop in props:
            self._runner.run(self.Writer.changeProperty(prop, Property.convertPropertyToWamp(self.obj, prop), []))  

    
    def remove(self):
        self._runner.run(self.Writer.remove)
        
    
    def createDynamicProperty(self, prop):
        info = Property.createInformation(self.obj, prop)        
        self._runner.run(self.__addDynamicProperty, prop, info)
    
    
    def removeDynamicProperty(self, prop):
        self._runner.run(self.Writer.removeProperty, prop)
    
    
    def addDynamicExtension(self, extension, props):
        infos = []
        for prop in props:
            infos.append(Property.createInformation(self.obj, prop))
        self._runner.run(self.Writer.addExtension, extension, props, infos)
    
    
    def changeProperty(self, prop):
        
        value = Property.convertPropertyToWamp(self.obj, prop)
        
        if float(".".join(FreeCAD.Version()[0:2])) == 0.18:
            #work around missing proxy callback in ViewProvider. This may add to some delay, as proxy change is ony forwarded 
            #when annother property changes afterwards, however, at least the order of changes is keept
            if hasattr(self.obj, 'Proxy'):
                if not self.proxydata is self.obj.Proxy:
                    self.proxydata = self.obj.Proxy
                    self._runner.run(self.__changeProperty, 'Proxy', self.obj.dumpPropertyContent('Proxy'), [])
            
        
        self._runner.run(self.__changeProperty, prop, value, [])


    def changePropertyStatus(self, prop):
        info = Property.createInformation(self.obj, prop)        
        self._runner.run(self.__changePropertyStatus, prop, info["status"])
        
        
    def __changePropertyStatus(self, prop, info):
        #indirection for batcher named tasks
        self.Writer.changePropertyStatus(prop, info)

    def __changeProperty(self, prop, value, outlist):
        #indirection for batcher named tasks
        self.Writer.changeProperty(prop, value, outlist)
        
    def __addDynamicProperty(self, prop, info):
        #indirection for batcher named tasks
        self.Writer.addDynamicProperty(prop, info)
        

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

import asyncio, logging, os, traceback
import Documents.Property   as Property
import Documents.Syncer     as Syncer
import Documents.Observer   as Observer
from Documents.OnlineObserver   import OnlineObserver
from Documents.OnlineObject     import OnlineObject, OnlineViewProvider
from Documents.AsyncRunner      import DocumentRunner
from Utils.Errorhandling        import OCPErrorHandler, attachErrorData

from autobahn.wamp.exception    import ApplicationError

class OnlineDocument(OCPErrorHandler):
    ''' Describing a FreeCAD document in the OCP framework. Properties can be changed or objects added/removed 
        like with a normal FreeCAD document, with the difference, that all changes are mirrored to all collabrators.
        Changes to the online doc do not change anything on the local one. The intenion is to mirror all user changes 
        done to the local document'''

    def __init__(self, id, doc, connection, dataservice):
        
        super().__init__()
        
        self.id = id
        self.document = doc
        self.connection = connection 
        self.objIds = {}
        self.data = dataservice
        self.onlineObs = OnlineObserver(self)
        self.objects = {}
        self.viewproviders = {}
        self.logger = logging.getLogger("Document " + id[-5:])
        self.sync = None        
        self.synced = os.getenv('FC_OCP_SYNC_MODE', "0") == "1"
            
        #Online documents cannot use the FreeCAD Transaction framework
        doc.UndoMode = 0
        
        self.logger.debug("Created")
        if self.synced:
            self.logger.info('Use non-default sync mode "Document-Sync"')
 
    async def setup(self):
        await self.onlineObs.setup()
 
    async def close(self):
        # we close the online doc. That means closing the observer and all objects/viewproviders
        
        try:
            tasks = []
            tasks.append(self.onlineObs.close())
            
            for obj in self.objects.values():
                tasks.append(obj.close())
            
            for vp in self.viewproviders.values():
                tasks.append(vp.close())
    
            if tasks:
                await asyncio.gather(*tasks)
                
            self.objects = []
            self.viewproviders = []
        
        except Exception as e:
            attachErrorData(e, "ocp_message", "Closing document failed")
            self._processException(e)
  
    
    def _handleError(self, source, error, data):
        
        # after any error we need to ensure FreeCAD and Node status match
        self._runner.run(self.download)
        
        if sorce is self and "ocp_message" in data:
                        
            err = data["ocp_message"]
            printdata = data.copy()
            del printdata["ocp_message"]
            del printdata["exception"]
            self.logger.Error(f"{err}: {printdata}")
        
        super()._handleError(source, error, data)
  
  
    def shouldExcludeTypeId(self, typeid):
        #we do not add App origins, lines and planes, as they are only Autocreated from parts and bodies
        if typeid in ["App::Origin", "App::Line", "App::Plane"]:
                return True
            
        return False
    
    def newObject(self, obj):
        
        if self.shouldExcludeTypeId(obj.TypeId):
            return
                
        #create the async runner for that object
        oobj = OnlineObject(obj, self)
        self.objects[obj.Name] = oobj
        self._registerSubErrorhandler(oobj)
        
        if not self.synced:
            #create the syncer that blocks all runners till this object is created. This is required to ensure no property access the object
            #before its creation
            block = Syncer.BlockSyncer()
            for entry in self.objects.values():
                if not entry.isSettingUp():
                    entry.synchronize(block)
                    
            #we need to block till the last document recompute is done, to ensure that we are not part of that recompute cycle
            #Note:  Do not use full syncer, as this includes an AcknowledgeSyncer which is setup for the amount of objects.
            #       Adding it to the new object adds an additional Acknowledge, which may lead to the fact that the recompute happens
            #       before all other runners are done
            if self.sync:
                oobj.setup(self.sync.Block)
            else:
                oobj.setup()
            
            #release all other online objects after setup finished
            oobj.synchronize(Syncer.RestartBlockSyncer(block))
            
        else:
            oobj.setup()
     
     
    def removeObject(self, obj):
        
        if self.shouldExcludeTypeId(obj.TypeId):
            return
        
        if not obj.Name in self.objects:
            self.logger.error(f"Should remove object {obj.Name} but is not part of online document")
        
        #ensure all other objects are finished before we remove, as it could be that one of those objects has a property change that refers to the object to be removed
        ackno = Syncer.AcknowledgeSyncer(len(self.objects)-1)
        for name, entry in self.objects.items():
            if name != obj.Name:
                entry.synchronize(ackno)
        
        #remove the async runner for that object after all other current objects are done
        oobj = self.objects[obj.Name]
        del(self.objects[obj.Name])
        oobj.synchronize(Syncer.WaitAcknowledgeSyncer(ackno))
        oobj.remove()
        self._unregisterSubErrorhandler(oobj)
        
        #as well as the online observer one
        asyncio.ensure_future(self.onlineObs.closeRunner(obj.Name))
        
        
    def changeObject(self, obj, prop):
               
        if self.shouldExcludeTypeId(obj.TypeId):
            return
        
        if obj.Name not in self.objects:
            if prop == "Label":
                #No error here: the label change callback comes always before the new object callback
                return
            else:
                self.logger.error(f"Property {prop} change but object does not exist in online document")
                return
        
        oobj = self.objects[obj.Name]
        oobj.changeProperty(prop)
    
    
    def changePropertyStatus(self, obj, prop):
        
        if self.shouldExcludeTypeId(obj.TypeId):
            return
        
        if obj.Name not in self.objects:
            self.logger.error(f"OnlineDocument called for object {obj.Name}, but is not setup")
            return
        
        oobj = self.objects[obj.Name]
        oobj.changePropertyStatus(prop)
    
    
    def newDynamicProperty(self, obj, prop):
        
        if self.shouldExcludeTypeId(obj.TypeId):
            return
        
        if obj.Name not in self.objects:
            self.logger.error(f"OnlineDocument called for object {obj.Name}, but is not setup")
            return
        
        oobj = self.objects[obj.Name]
        oobj.createDynamicProperty(prop)
        
        
    def removeDynamicProperty(self, obj, prop):
        
        if self.shouldExcludeTypeId(obj.TypeId):
            return
        
        if obj.Name not in self.objects:
            self.logger.error(f"OnlineDocument called for object {obj.Name}, but is not setup")
            return
        
        oobj = self.objects[obj.Name]
        oobj.removeDynamicProperty(prop)


    def addDynamicExtension(self, obj, extension, props):
        if self.shouldExcludeTypeId(obj.TypeId):
            return
        
        if obj.Name not in self.objects:
            self.logger.error(f"OnlineDocument called for object {obj.Name}, but is not setup")
            return
        
        oobj = self.objects[obj.Name]
        oobj.addDynamicExtension(extension, props)
        

    def recomputObject(self, obj):
        
        if self.shouldExcludeTypeId(obj.TypeId):
            return
        
        if obj.Name not in self.objects:
            self.logger.error(f"OnlineDocument called for object {obj.Name}, but is not setup")
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
        #Setups and uploads a new ViewProvider
        
        if self.shouldExcludeTypeId(vp.Object.TypeId):
            return
        
        #get the corresponding online object
        if not vp.Object.Name in self.objects:
            raise Exception("Cannot add viewprovider for non existing object")
        
        #create the online view provider for that object
        ovp = OnlineViewProvider(vp, self.objects[vp.Object.Name], self)
        self.viewproviders[vp.Object.Name] = ovp
        ovp.setup() #no sync, as it uses the OnlineObject runner, which is synced
        
     
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
            self.logger.error(f"OnlineDocument called for viewprovider {vp.Object.Name}, but is not setup")
            return
        
        ovp = self.viewproviders[vp.Object.Name]
        ovp.changeProperty(prop)
    
    
    def changeViewProviderPropertyStatus(self, vp, prop):
        
        if self.shouldExcludeTypeId(vp.Object.TypeId):
            return
        
        if vp.Object.Name not in self.viewproviders:
            self.logger.error(f"OnlineDocument called for viewprovider {vp.Object.Name}, but is not setup")
            return
        
        ovp = self.viewproviders[vp.Object.Name]
        ovp.changePropertyStatus(prop)
        
    
    def newViewProviderDynamicProperty(self, vp, prop):
        
        if self.shouldExcludeTypeId(vp.Object.TypeId):
            return
        
        if vp.Object.Name not in self.viewproviders:
            self.logger.error(f"OnlineDocument called for viewprovider {vp.Object.Name}, but is not setup")
            return
        
        ovp = self.viewproviders[vp.Object.Name]
        ovp.createDynamicProperty(prop)
        
        
    def removeViewProviderDynamicProperty(self, vp, prop):
        
        if self.shouldExcludeTypeId(vp.Object.TypeId):
            return
        
        if vp.Object.Name not in self.viewproviders:
            self.logger.error(f"OnlineDocument called for viewprovider {vp.Object.Name}, but is not setup")
            return
        
        ovp = self.viewproviders[vp.Object.Name]
        ovp.removeDynamicProperty(prop)


    def addViewProviderDynamicExtension(self, vp, extension, props):
        if self.shouldExcludeTypeId(vp.Object.TypeId):
            return
        
        if vp.Object.Name not in self.viewproviders:
            self.logger.error(f"OnlineDocument called for viewprovider {vp.Object.Name}, but is not setup")
            return
        
        ovp = self.viewproviders[vp.Object.Name]
        ovp.addDynamicExtension(extension, props)
        
        
    def recomputeDocument(self):
        
        #the document has been fully recomputed. That means we have received all object changes that belong to 
        #a certain transaction. Therefor we can now close this transaction.
        #This means:
        # - we need to wait till all online objects finished the changes, they have till now
        # - we need to make sure no online object processes any new changes before the transaction is closed
               
        #sync all document objects! (not viewproviders, those are not transactioned)
        if not self.synced:
            self.sync = Syncer.AcknowledgeBlockSyncer(len(self.objects))
            for obj in self.objects.values():
                obj.synchronize(self.sync)
                
            asyncio.ensure_future(self.__recomputeDocument(self.sync))
        
        else:
            runner = DocumentRunner.getSenderRunner(self.id, self.logger)
            runner.run(self.__recomputeDocument(self.sync))
            
        
        
    async def __recomputeDocument(self, sync):
        
        try:     
            #wait till all objects have done their work
            if sync:
                await sync.wait()
        
            #close the transaction
            self.logger.debug("Close transaction")
            uri = f"ocp.documents.{self.id}.content.Transaction.IsOpen"
            if await self.connection.api.call(uri):
                uri = f"ocp.documents.{self.id}.content.Transaction.Close"
                await self.connection.api.call(uri)

        except Exception as e:
            attachErrorData(e, "ocp_message", "Closing transaction failed")
            self._processException(e)
            
        finally:
            if sync:
                sync.restart()
                self.sync = None


    async def _docPrints(self):
        
        try:
            uri = f"ocp.documents.{self.id}.prints"
            vals = await self.connection.api.call(uri)
            for val in vals:
                self.logger.debug(val)
        
        except Exception as e:
            attachErrorData(e, "ocp_message", "Accessing JavaScript prints failed")
            self._processException(e)        


    async def asyncSetup(self):
        # Loads the existing FreeCAD doc into the ocp node
        try:                
            for fcobj in self.document.Objects:
                
                if self.shouldExcludeTypeId(fcobj.TypeId):
                    continue
                
                tasks = []
                
                #create and setup the online object
                oobj = OnlineObject(fcobj, self)
                self.objects[fcobj.Name] = oobj
                tasks.append(oobj.upload(fcobj))
                    
                if fcobj.ViewObject:
                    ovp = OnlineViewProvider(fcobj.ViewObject, self.objects[fcobj.Name], self)
                    self.viewproviders[fcobj.Name] = ovp
                    tasks.append(ovp.upload(fcobj.ViewObject))

                # TODO: setup document properties
                
                if tasks:
                    await asyncio.gather(*tasks)
            
        except Exception as e:
            attachErrorData(e, "ocp_message", "Unable to setup document")
            self._processException(e)

            
                   
    async def asyncLoad(self):
        # loads the online doc into the freecad doc
        
        try:
            #first we need to get into view mode for the document, to have a steady picture of the current state of things and
            #to not get interrupted
            await self.connection.api.call(f"ocp.documents.{self.id}.view", True)
            
            #create all document objects!
            uri = f"ocp.documents.{self.id}.content.Document.Objects.GetObjectTypes"
            objs = await self.connection.api.call(uri)
   
            tasks = []              
            with Observer.blocked(self.document):
                for name, objtype in objs.items():
                    
                    if hasattr(self.document, name):
                        self.document.removeObject(name)
                    
                    # create the FC object
                    fcobj = self.document.addObject(objtype, name)
                    if fcobj.Name != name:
                        raise Exception("Cannot setup object, name wrong")

                    # create and load the online object
                    oobj = OnlineObject(fcobj, self)
                    self.objects[name] = oobj
                    tasks.append(oobj.download(fcobj))
                    
                    # create and load the online viewprovider
                    if fcobj.ViewObject:
                        ovp = OnlineViewProvider(fcobj.ViewObject, self.objects[name], self)
                        self.viewproviders[name] = ovp
                        tasks.append(ovp.download(fcobj.ViewObject))
              
            #TODO: load document properties
              
            # we do this outside of the observer blocking context, as the object loads block themself
            if tasks:
                await asyncio.gather(*tasks)
        
        except Exception as e:
            attachErrorData(e, "ocp_message", "Unable to load document")
            self._processException(e) 
            
        finally:
            await self.connection.api.call(f"ocp.documents.{self.id}.view", False)
        
    
    async def asyncUnload(self):
        pass
    
    async def asyncGetDocumentPeers(self):
        try:
            return await self.connection.api.call(u"ocp.documents.{0}.listPeers".format(self.id))
        
        except Exception as e:
            attachErrorData(e, "ocp_message", "Retreiving peers failed")
            self._processException(e) 
            return []
        
        
    async def waitTillCloseout(self, timeout = 10):
        #wait till all current async tasks are finished. Note that it also wait for task added during the wait period.
        #throws an error on timeout.
        
        try:
            coros = []
            for obj in list(self.objects.values()):
                coros.append(obj.waitTillCloseout(timeout))
                
            for obj in list(self.viewproviders.values()):
                coros.append(obj.waitTillCloseout(timeout))

            coros.append(self.onlineObs.waitTillCloseout(timeout))

            if len(coros)>0:
                await asyncio.gather(*coros)
        
        except Exception as e:
            self._processException(e) 

# ************************************************************************
# *   Copyright (c) Stefan Troeger (stefantroeger@gmx.net) 2021          *
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

import asyncio, FreeCAD
import Documents.Property as Property

class OCPObjectWriter():
    ''' Writes object data to the OCP node document
    
        This class provides async functions to write FreeCAD object data into the OCP node. It uses the 
        online documents connection to the node to setup and update the object. 
        
        Notes:        
        1. A writer is responsible for a single named freecad object
        2. Writer can be DocumentObject or ViewProvider
        3. Most functions directly execute the action on the node
        4. Some functions are cached, that means multiple calls are collected together till a 
           cache execution function is called 
           
        Init:
        name      - Name of the FC object
        fytype    - type of FC object as used in DML ("Object" or "ViewProvider")
        onlinedoc - The onlinedocument that handles the FC document the FC object belongs to
        logger    - The logger to use for messaging
    '''
    
    
    def __init__(self, name, fctype, onlinedoc, logger):
        # Setups the writer
        # name      - Name of the FC object
        # fytype    - type of FC object as used in DML ("Object" or "ViewProvider")
        # onlinedoc - The onlinedocument that handles the FC document the FC object belongs to
        # logger    - The logger to use for messaging
        
        self.logger             = logger
        self.docId              = onlinedoc.id
        self.data               = onlinedoc.data
        self.connection         = onlinedoc.connection
        self.name               = name
        self.objGroup           = fctype
        self.dynPropCache       = {}
        self.statusPropCache    = {}
        self.propChangeCache    = {}
        self.propChangeOutlist  = []
        self.setupStage         = True

    
    async def isAvailable(self):
        try:
            uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.Has"
            return await self.connection.session.call(uri, self.name)
        except Exception as e:
            self.logger.error(f"Queriying availablitiy failed: {e}")
            

    async def setup(self, typeid, properties, infos):
        #creates the object in the ocp node
    
        self.logger.debug(f"New object {self.name} ({typeid})")

        try:           
            uri = u"ocp.documents.{0}".format(self.docId)
            await self.connection.session.call(uri + u".content.Document.{0}.NewObject".format(self.objGroup), self.name, typeid)
            
            #create all properties that need setup           
            await self.__createProperties(False, properties, infos)
            
            self.setupStage = False
        
        except Exception as e:
            self.logger.error("Setup error: {0}".format(e))
           
    
    async def __createProperty(self, dynamic, prop, info):
        #adds a new property with its property information
        #could be added as normal or as dynamic property, dependend on dyn boolean
        
        # Note: no try/catch, as method is private and the error is always catched from caller
        if dynamic:
            self.logger.debug(f"Create dynamic property {prop}")
            fnc = "CreateDynamicProperty"
        else:
            self.logger.debug(f"Setup default property {prop}")
            fnc = "SetupProperty"
            
        uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.{self.name}.Properties.{fnc}"
        await self.connection.session.call(uri, prop, info["typeid"], info["group"], info["docu"], info["status"])

    
    
    async def __createProperties(self, dynamic, props, infos):
        #adds a list of properties and a list with their property infos
        #could be added as normal or as dynamic property, dependend on "dynamic" boolean
        
        # Note: no try/catch, as method is private and the error is always catched from caller
        if dynamic:
            self.logger.debug(f"Create dynamic properties {props}")
            fnc = "CreateDynamicProperties"
        else:
            self.logger.debug(f"Setup default properties {props}")
            fnc = "SetupProperties"
            
        uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.{self.name}.Properties.{fnc}"
        await self.connection.session.call(uri, props, infos)

    
    async def removeProperty(self, prop):
        try:        
            self.logger.debug(f"Remove property {prop}")
            uri = u"ocp.documents.{0}.content.Document.{1}.{2}.Properties.RemoveDynamicProperty".format(self.docId, self.objGroup, self.name)
            await self.connection.session.call(uri, prop)
        
        except Exception as e:
            self.logger.error("Remove property {0} failed: {1}".format(prop, e))
        
    
    def addDynamicProperty(self, prop, info):
        #caches the dynamic property creation to be executed as batch later
        self.dynPropCache[prop] = info
        
        
    async def processDynamicPropertyAdditions(self):
        # Processes all added dynamic properties
        
        if len(self.dynPropCache) == 0:
            return
        try:
            props = self.dynPropCache.copy()
            self.dynPropCache.clear()
            
            keys   = list(props.keys())
            values = list(props.values())
            
            if len(props) == 1:
                await self.__createProperty(True, keys[0], values[0])
            
            else:
                await self.__createProperties(True, keys, values)

        except Exception as e:
            self.logger.error(f"Create dynamic property from cache failed: {e}")
            
            
    def changePropertyStatus(self, prop, status):
        #add property with status to the cache. 
        self.statusPropCache[prop] = status
        
        
    async def processPropertyStatusChanges(self):
        #Processes all changed property stati
        
        if len(self.statusPropCache) == 0:
            return
        try:
            props = self.statusPropCache.copy()
            self.statusPropCache.clear()
            
            keys   = list(props.keys())
            values = list(props.values())
            
            uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.{self.name}.Properties."
            
            if  float(".".join(FreeCAD.Version()[0:2])) >= 0.19:
                #0.19 directly supports status
                if len(props) == 1:
                    self.logger.debug("Change property status {0}".format(keys[0]))
                    uri += keys[0] + ".status"
                    await self.connection.session.call(uri, values[0])
                
                else:
                    self.logger.debug("Change batched property status: {0}".format(keys))
                    uri += "SetStatus"
                    failed = await self.connection.session.call(uri, keys, values)
                    if failed:
                        raise Exception(f"Properties {failed} failed")
            else:
                #0.18 only supports editor mode subset of status
                if len(props) == 1:
                    self.logger.debug("Change property status {0}".format(keys[0]))
                    uri += keys[0] + ".SetEditorMode"
                    await self.connection.session.call(uri, values[0])
                
                else:
                    self.logger.debug("Change batched property status: {0}".format(keys))
                    uri += "SetEditorModes"
                    failed = await self.connection.session.call(uri, keys, values)
                    if failed:
                        raise Exception(f"Properties {failed} failed")
                
        except Exception as e:
            self.logger.error("Change property status from cache failed: {0}".format(e))
            
    
    def changeProperty(self, prop, value, outlist):        
        #change a property to new value and outlist. Note: Value must be already in serializabe format
        
        self.propChangeCache[prop] = value
        self.propChangeOutlist = outlist #we are only interested in the last set outlist, not intermediate steps
    
    
    async def __getCidForData(self, data):               
        #store the data for the processing!
        
        #make the data available in the provider
        datakey = self.data.addData(data)
        
        #get the cid!
        uri = f"ocp.documents.{self.docId}.raw.CidByBinary"
        cid = await self.connection.session.call(uri, self.data.uri, datakey)
        return cid
        
    
    async def processPropertyChanges(self):
        # Process all property changes
                 
        if not self.propChangeCache:
            return

        #copy everything before first async op
        props = self.propChangeCache.copy()
        self.propChangeCache.clear()
        out = self.propChangeOutlist.copy()
               
        try:
                
            #get the cids for the binary properties in parallel
            tasks = []
            for prop in props:
                if isinstance(props[prop], bytearray): 
                    
                    async def run(props, prop):
                        cid = await self.__getCidForData(props[prop])
                        props[prop] = cid
                        
                    tasks.append(run(props, prop))

            #also in parallel: query the current outlist
            if self.objGroup == "Objects":
                outlist = []
                async def getOutlist():
                    uri = f"ocp.documents.{self.docId}.content.Document.DAG.GetObjectOutList"
                    outlist = await self.connection.session.call(uri, self.name)
                    outlist.sort()
                    
                tasks.append(getOutlist())


            #execute all parallel tasks
            if tasks:
                await asyncio.wait(tasks)
            
            #now batchwrite all properties in correct order
            if len(props) == 1:
                prop = list(props.keys())[0]
                self.logger.debug(f"Write property {prop}")
                uri = f"ocp.documents.{self.docId}.content.Document.{self.objGroup}.{self.name}.Properties.{prop}.SetValue"
                await self.connection.session.call(uri, list(props.values())[0])
            else:
                self.logger.debug(f"Write properties {list(props.keys())}")
                uri = u"ocp.documents.{0}.content.Document.{1}.{2}.Properties.SetValues".format(self.docId, self.objGroup, self.name)
                failed = await self.connection.session.call(uri, list(props.keys()), list(props.values()))
                if failed:
                    raise Exception(f"Properties {failed} failed")

            #finally process the outlist
            if self.objGroup == "Objects":
                out.sort()
                if out != outlist:
                    self.logger.debug(f"Set Outlist")
                    uri = f"ocp.documents.{self.docId}.content.Document.DAG.SetObjectOutList"
                    await self.connection.session.call(uri, self.name, out)
                
        except Exception as e:
            self.logger.error(f"Batch writing properties {list(props.keys())} failed: {e}")
        
        
    async def addExtension(self, extension, props=None, infos=None):
        #adds the extension including the new properties
        
        try:           
            uri = f"ocp.documents.{self.docId}"
            
            #add the extension must be done: a changed property could result in use of the extension
            self.logger.debug("Add extension {0}".format(extension))
            calluri = uri + u".content.Document.{0}.{1}.Extensions.Append".format(self.objGroup, self.name)
            await self.connection.session.call(calluri, extension)
            if props and infos:
                await self.__createProperties(False, props, infos)
                
        except Exception as e:
            self.logger.error("Adding extension failed: {0}".format(e))
     
     
    async def remove(self):
        try:
            self.logger.debug("Remove")
            uri = u"ocp.documents.{0}".format(self.docId)
            await self.connection.session.call(uri + u".content.Document.{0}.RemoveObject".format(self.objGroup), self.name)
        
        except Exception as e:
            self.logger.error("Removing error: {0}".format(e))


            
    async def objectRecomputed(self):
        
        try:
            self.logger.debug("Recompute")                
            uri = f"ocp.documents.{self.docId}.content.Document.Objects.{self.name}.onObjectRecomputed"
            await self.connection.session.call(uri)
        
        except Exception as e:
            self.logger.error("Recompute exception: {0}".format(e))

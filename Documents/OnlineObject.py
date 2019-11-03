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
from Documents.AsyncRunner import AsyncRunner
import Documents.Property as Property

class OnlineObject():
    
    def __init__(self, obj, onlinedoc):
        
        self.changed        = set()
        self.runner         = AsyncRunner()
        self.docId          = onlinedoc.id
        self.data           = onlinedoc.data
        self.obj            = obj
        self.requriesSetup  = False
        self.connection     = onlinedoc.connection
    
    
    def setup(self):
        self.requriesSetup = True
        self.runner.runAsyncAsSetup(self.__asyncSetup())
    
    
    def remove(self):
        self.runner.runAsyncAsCloseout(self.__asyncRemove(self.obj.Name))
        
    
    def createDynamicProperty(self, prop):
        self.runner.runAsync(self.__asyncCreateProperty(prop, True))
        self.changed.add(prop)
    
    
    def removeDynamicProperty(self, prop):
        self.runner.runAsync(self.__asyncRemoveProperty(prop))
    
    
    def changeProperty(self, prop):
        self.changed.add(prop)
    
    
    def recompute(self):
        self.runner.runAsyncAsCloseout(self.__recompute())

        
    async def __asyncSetup(self):
        try:
            uri = u"ocp.documents.edit.{0}".format(self.docId)
            await self.connection.session.call(uri + u".call.Document.Objects.NewObject",self.obj.Name, self.obj.TypeId)
        
        except Exception as e:
            print("Setup object error: {0}".format(e))


    async def __asyncFinalizeSetup(self, changed):
        
        try:
            #Let's check which properties are not yet setup (meaning are not dynamic)
            calluri = u"ocp.documents.edit.{0}.call.Document.Objects.{1}.Properties.Keys".format(self.docId, self.obj.Name)
            onlineProps = await self.connection.session.call(calluri)
            allProps = self.obj.PropertiesList
            reqSetup = set(allProps) - set(onlineProps)
                        
            #create all properties that need setup
            tasks = []
            for prop in reqSetup:
                tasks.append(self.__asyncCreateProperty(prop, False))
                
            await asyncio.wait(tasks)
            
            #write all properties that are not part of a change write
            reqWrite = set(allProps) - changed
            tasks = []
            for prop in reqWrite:
                tasks.append(self.__asyncWriteProperty(prop))
            
            await asyncio.wait(tasks)
            self.requriesSetup = False  
        
        except Exception as e:
            print("Finalizing setup failed: ", e)
    
    
    async def __updateExtensions(self):
        #we need to check if the correct set of extensions is known and change it if not
        #as we do not have a correct event for adding/removing extensions this is the only way
        
        try:
            uri = u"ocp.documents.edit.{0}".format(self.docId)

            extensions = ["App::GroupExtensionPython", "App::GeoFeatureGroupExtensionPython", "App::OriginGroupExtensionPython"]
            availExt = []
            for ext in extensions:
                if self.obj.hasExtension(ext):
                    availExt.append(ext)
            
            tasks = []
            calluri = uri + u".call.Document.Objects.{0}.Extensions.GetAll".format(self.obj.Name)
            knownExt = await self.connection.session.call(calluri)
            remExt = set(knownExt) - set(availExt)
            for ext in remExt:
                calluri = uri + u".call.Document.Objects.{0}.Extensions.RemoveByName".format(self.obj.Name)
                tasks.append(self.connection.session.call(calluri, ext))
            
            addExt = set(availExt) - set(knownExt)
            for ext in addExt:
                calluri = uri + u".call.Document.Objects.{0}.Extensions.Append".format(self.obj.Name)
                tasks.append(self.connection.session.call(calluri, ext))
            
            if len(tasks) > 0:
                await asyncio.wait(tasks)
        
        except Exception as e:
            print("UpdateExtensions failed: ", e)
            
     
    async def __asyncRemove(self, name):
        try:
            uri = u"ocp.documents.edit.{0}".format(self.docId)
            await self.connection.session.call(uri + u".call.Document.Objects.RemoveObject", name)
        
        except Exception as e:
            print("Removing object error: {0}".format(e))


    async def __asyncCreateProperty(self, prop, dyn):
        try:
            docu = self.obj.getDocumentationOfProperty(prop)
            #emode = obj.getEditorMode(prop)
            group = self.obj.getGroupOfProperty(prop)
            typeid = self.obj.getTypeIdOfProperty(prop)
            ptype = '-'.join(self.obj.getTypeOfProperty(prop))
            
            if dyn:
                print("new dynamic object " + self.obj.Name + " property " + prop +" (" + typeid + ")")
                fnc = "CreateDynamicProperty"
            else:
                print("setup object " + self.obj.Name + " property " + prop +" (" + typeid + ")")
                fnc = "SetupProperty"
                
            uri = u"ocp.documents.edit.{0}.call.Document.Objects.{1}.Properties.{2}".format(self.docId, self.obj.Name, fnc)
            await self.connection.session.call(uri, prop, ptype, typeid, group, docu)
        
        except Exception as e:
            print("Setup property ", prop, " of object ", self.obj.Name, " failed: ", e)
    
    
    async def __asyncRemoveProperty(self, prop):
        try:        
            print("remove object " + obj.Name + " property " + prop)
            uri = u"ocp.documents.edit.{0}.call.Document.Objects.{1}.Properties.RemoveDynamicProperty".format(self.id, obj.Name)
            await self.connection.session.call(uri, prop,)
        
        except Exception as e:
            print("Remove property ", prop, " of object ", obj.Name, " failed: ", e)
        
        
    async def __asyncWriteProperty(self, prop):      
        
        try:
            value = Property.convertPropertyToWamp(self.obj, prop)
            uri = u"ocp.documents.edit.{0}".format(self.docId)
        
            if isinstance(value, bytearray):
                #store the data for the processing!
                datakey = self.data.addData(value)
                
                #than we need the id of the property where we add the data
                calluri = uri + u".call.Document.Objects.{0}.Properties.{1}.GetValue".format(self.obj.Name, prop)
                propid = await self.connection.session.call(calluri)
                
                #call "SetBinary" for the property
                await self.connection.session.call(uri + u".rawdata.{0}.SetByBinary".format(propid), self.data.uri, datakey)
                
            else:
                #simple POD property: just add it!
                uri += u".call.Document.Objects.{0}.Properties.{1}.SetValue".format(self.obj.Name, prop)
                await self.connection.session.call(uri, value)
        
        except Exception as e:
            print("Writing property error: {0}".format(e))
            
            
    async def __recompute(self):
        
        try:
            #to enable async change of object while we process this recompute we copy the set of changes
            changed = self.changed.copy()
            self.changed.clear()
            
            if self.requriesSetup:
                await self.__asyncFinalizeSetup(changed)
            
            #handle the extensions
            await self.__updateExtensions()
            
            #after recompute all changes are commited          
            tasks = []
            for prop in changed:
                tasks.append(self.__asyncWriteProperty(prop))
            
            await asyncio.wait(tasks)
        
        except Exception as e:
            print("Recompute exception: ", e)

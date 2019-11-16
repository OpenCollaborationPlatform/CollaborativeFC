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

class FreeCADOnlineObject():
    
    def __init__(self, name, onlinedoc, objGroup):
        self.docId          = onlinedoc.id
        self.data           = onlinedoc.data
        self.connection     = onlinedoc.connection
        self.runner         = AsyncRunner()
        self.name           = name
        self.objGroup       = objGroup 
        self.dynPropCache   = {}


    async def _asyncSetup(self, typeid, values, infos):
        #creates the object in the ocp node
    
        try:
            uri = u"ocp.documents.edit.{0}".format(self.docId)
            await self.connection.session.call(uri + u".call.Document.{0}.NewObject".format(self.objGroup), self.name, typeid)
            
            #create all properties that need setup
            tasks = []
            for prop in values.keys():
                tasks.append(self._asyncCreateProperty(False, prop, infos[prop]))
            await asyncio.wait(tasks)
            
            #write the props if requried
            tasks = []
            for prop in values:
                tasks.append(self._asyncWriteProperty(prop, values[prop]))
            if len(tasks) > 0:
                await asyncio.wait(tasks)
        
        except Exception as e:
            print("Setup error: {0}".format(e))
           
    
    async def _asyncCreateProperty(self, dyn, prop, info):
        try:            
            if dyn:
                print("new dynamic " + self.objGroup + " " + self.name + " property " + prop +" (" + info["typeid"] + ")")
                fnc = "CreateDynamicProperty"
            else:
                print("setup " + self.objGroup + " "+ self.name + " property " + prop +" (" + info["typeid"] + ")")
                fnc = "SetupProperty"
                
            uri = u"ocp.documents.edit.{0}.call.Document.{1}.{2}.Properties.{3}".format(self.docId, self.objGroup, self.name, fnc)
            await self.connection.session.call(uri, prop, info["ptype"], info["typeid"], info["group"], info["docu"])
        
        except Exception as e:
            print("Setup property ", prop, " of object ", self.name, " failed: ", e)
    
    
    async def _asyncRemoveProperty(self, prop):
        try:        
            print("remove " + self.objGroup + " " + self.name + " property " + prop)
            uri = u"ocp.documents.edit.{0}.call.Document.{1}.{2}.Properties.RemoveDynamicProperty".format(self.id, self.objGroup, self.name)
            await self.connection.session.call(uri, prop,)
        
        except Exception as e:
            print("Remove property ", prop, " of object ", self.name, " failed: ", e)
        
    
    def addDynamicPropertyCreation(self, prop, info):
        #add property with info to the cache. 
        self.dynPropCache[prop] = info
        
        #if there was no entry before we start a cache processing. If there is something in the cache already
        #we are sure processing was already startet
        if len(self.dynPropCache) == 1:
            #add it to the dyn property creation cache. If it is the first entry we also start the 
            self.runner.runAsyncAsIntermediateSetup(self._asyncCreateDynamicPropertiesFromCache())
        
        
    async def _asyncCreateDynamicPropertiesFromCache(self):
        
        if len(self.dynPropCache) == 0:
            return
        
        props = self.dynPropCache.copy()
        self.dynPropCache.clear()
        
        if len(props) == 1:
            await self._asyncCreateProperty(True, props.keys()[0], props.values()[0])
        else:
            print("Create batched dynamic properties: ", props.keys())
            uri = u"ocp.documents.edit.{0}.call.Document.{1}.{2}.Properties.CreateDynamicProperties".format(self.docId, self.objGroup, self.name)
            await self.connection.session.call(uri, list(props.keys()), list(props.values()))
            
        
    async def _asyncWriteProperty(self, prop, value):
        
        print("Write ", prop, " property ", prop)
        try:
            #value = Property.convertPropertyToWamp(self.obj, prop)
            uri = u"ocp.documents.edit.{0}".format(self.docId)
        
            if isinstance(value, bytearray):
                #store the data for the processing!
                datakey = self.data.addData(value)
                
                #than we need the id of the property where we add the data
                calluri = uri + u".call.Document.{0}.{1}.Properties.{2}.GetValue".format( self.objGroup, self.name, prop)
                propid = await self.connection.session.call(calluri)
                
                #call "SetBinary" for the property
                await self.connection.session.call(uri + u".rawdata.{0}.SetByBinary".format(propid), self.data.uri, datakey)
                
            else:
                #simple POD property: just add it!
                uri += u".call.Document.{0}.{1}.Properties.{2}.SetValue".format(self.objGroup, self.name, prop)
                await self.connection.session.call(uri, value)
        
        except Exception as e:
            print("Writing property error: {0}".format(e))
   
       
    async def _updateExtensions(self, obj):
        #we need to check if the correct set of extensions is known and change it if not
        #as we do not have a correct event for adding/removing extensions this is the only way
        
        try:
            uri = u"ocp.documents.edit.{0}".format(self.docId)

            #a list of all known python extensions and the properties they add
            extensions = {"App::GroupExtensionPython": ["ExtensionProxy", "Group"], 
                          "App::GeoFeatureGroupExtensionPython": ["ExtensionProxy", "Group"],
                          "App::OriginGroupExtensionPython": ["ExtensionProxy", "Group", "Origin"],
                          "Gui::ViewProviderGeoFeatureGroupExtensionPython": ["ExtensionProxy"],
                          "Gui::ViewProviderGroupExtensionPython": ["ExtensionProxy"],
                          "Gui::ViewProviderOriginGroupExtensionPython": ["ExtensionProxy"],
                          "Part::AttachExtensionPython": ["ExtensionProxy", "AttacherType", "Support", "MapMode", "MapReversed", "MapPathParameter", "AttachmentOffset"],
                          "PartGui::ViewProviderAttachExtensionPython": ["ExtensionProxy"]}

            availExt = []
            for ext in extensions.keys():
                #need try/except as hasExtension can fail if e.g. PartGui is not yet loaded but we ask for it
                try:
                    if obj.hasExtension(ext):
                        availExt.append(ext)
                except:
                    pass
            
            tasks = []
            calluri = uri + u".call.Document.{0}.{1}.Extensions.GetAll".format(self.objGroup, self.name)
            knownExt = await self.connection.session.call(calluri)
   
            #axtensions can only be added dynamically
            addedProps = []
            addExt = set(availExt) - set(knownExt)
            for ext in addExt:
                print("Add ", self.objGroup, " extension ", ext)
                calluri = uri + u".call.Document.{0}.{1}.Extensions.Append".format(self.objGroup, self.name)
                tasks.append(self.connection.session.call(calluri, ext))
                
                for prop in extensions[ext]:
                    addedProps.append(prop)
                    info = Property.createPropertyInfo(obj, prop)        
                    tasks.append(self._asyncCreateProperty(False, prop, info))
            
            if len(tasks) > 0:
                await asyncio.wait(tasks)
            
            #write the default values for the extension properties
            tasks = []
            for prop in addedProps:
                value = Property.convertPropertyToWamp(obj, prop)
                tasks.append(self._asyncWriteProperty(prop, value))
            
            if len(tasks) > 0:
                await asyncio.wait(tasks)
        
        except Exception as e:
            print("UpdateExtensions failed: ", e)
            
     
    async def _asyncRemove(self, name):
        try:
            uri = u"ocp.documents.edit.{0}".format(self.docId)
            await self.connection.session.call(uri + u".call.Document.{0}.RemoveObject".format(self.objGroup), name)
        
        except Exception as e:
            print("Removing object error: {0}".format(e))


class OnlineObject(FreeCADOnlineObject):
    
    def __init__(self, obj, onlinedoc):
        
        super().__init__(obj.Name, onlinedoc, "Objects")
        self.changed        = set()
        self.odoc           = onlinedoc
        self.obj            = obj
        
        
    def setup(self):
        values = {}
        infos = {}
        for prop in self.obj.PropertiesList:
            values[prop] = Property.convertPropertyToWamp(self.obj, prop)
            infos[prop]  = Property.createPropertyInfo(self.obj, prop)
            
        self.runner.runAsyncAsSetup(self._asyncSetup(self.obj.TypeId, values, infos))
    
    
    def remove(self):
        self.runner.runAsyncAsCloseout(self._asyncRemove(self.obj.Name))
        
    
    def createDynamicProperty(self, prop):
        info = Property.createPropertyInfo(self.obj, prop)        
        self.addDynamicPropertyCreation(prop, info)
    
    
    def removeDynamicProperty(self, prop):
        self.runner.runAsync(self._asyncRemoveProperty(prop))
    
    
    def changeProperty(self, prop):
        
        #if this change touched the object, we are able to wait for the revompute. Otherwise 
        #no recompute will be triggered and hence the change would not be forwarded. That happens 
        #f.e. with App::Parts group property on drag n drop. So let's check for it.
        if "Up-to-date" in self.obj.State:
            value = Property.convertPropertyToWamp(self.obj, prop)
            self.runner.runAsync(self._asyncWriteProperty(prop, value))
            
        else:
            self.changed.add(prop)
    
    
    def recompute(self):
        #to enable async change of object while we process this recompute we copy the set of changes
        changed = self.changed.copy()
        self.changed.clear()
        
        #collect all the values
        values = {}
        for prop in changed:
            values[prop] = Property.convertPropertyToWamp(self.obj, prop)
            
        self.runner.runAsyncAsCloseout(self.__asyncRecompute(values))
               
            
    async def __asyncRecompute(self, values):
        
        try:          
            #handle the extensions if required
            if "ExtensionProxy" in values.keys():
                await self._updateExtensions(self.obj)
            
            #after recompute all changes are commited          
            tasks = []
            for prop in values:
                tasks.append(self._asyncWriteProperty(prop, values[prop]))
            
            if len(tasks) > 0:
                await asyncio.wait(tasks)
                
            uri = u"ocp.documents.edit.{0}.call.Document.Objects.{1}.onRecomputed".format(self.docId, self.name)
            await self.connection.session.call(uri)
        
        except Exception as e:
            print("Recompute exception: ", e)
            

class OnlineViewProvider(FreeCADOnlineObject):
    
    def __init__(self, obj, onlinedoc):        
        super().__init__(obj.Object.Name, onlinedoc, "ViewProviders")
        self.obj = obj
        self.proxydata = bytearray()   #as FreeCAD 0.18 does not forward viewprovider proxy changes we need a way to identify changes
          
        
    def setup(self):
        
        #part of the FC 0.18 no proxy change event workaround
        if hasattr(self.obj, 'Proxy'):
            self.proxydata = self.obj.dumpPropertyContent('Proxy')
        
        #collect all property values and infos
        values = {}
        infos = {}
        for prop in self.obj.PropertiesList:
            values[prop] = Property.convertPropertyToWamp(self.obj, prop)
            infos[prop]  = Property.createPropertyInfo(self.obj, prop)
            
        self.runner.runAsyncAsSetup(self._asyncSetup(self.obj.TypeId, values, infos))
    
    
    def remove(self):
        self.runner.runAsyncAsCloseout(self._asyncRemove(self.obj.Name))
        
    
    def createDynamicProperty(self, prop):
        info = Property.createPropertyInfo(self.obj, prop)        
        self.addDynamicPropertyCreation(prop, info)
    
    
    def removeDynamicProperty(self, prop):
        self.runner.runAsyncAsIntermediateSetup(self._asyncRemoveProperty(prop))
    
    
    def changeProperty(self, prop):
        
        #work around missing extension callbacks
        if prop == "ExtensionProxy":
            self.runner.runAsyncAsSetup(self._updateExtensions(self.obj))
        
        #work around missing proxy callback. This may add to some delay, as proxy change is ony forwarded 
        #when annother property changes afterwards, however, at least the order of changes is keept
        if hasattr(self.obj, 'Proxy'):
            proxydata = self.obj.dumpPropertyContent('Proxy')
            if not proxydata == self.proxydata:
                self.proxydata = proxydata
                self.runner.runAsync(self._asyncWriteProperty('Proxy', proxydata))
        
        print("change view provider property ", prop)
        value = Property.convertPropertyToWamp(self.obj, prop)
        self.runner.runAsync(self._asyncWriteProperty(prop, value))

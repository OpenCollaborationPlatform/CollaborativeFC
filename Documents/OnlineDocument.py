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

import Documents.Property as Property
from autobahn.wamp.types import RegisterOptions
from autobahn.wamp.exception import ApplicationError

class DataStore():
    
    def __init__(self):
        self.keyCntr = 0
        self.data = {}
    
    def addData(self, data):
        key = self.keyCntr
        self.data[key] = data
        self.keyCntr += 1
        return key
        
    def getData(self, key):
        if key not in self.data:
            return bytearray()
        
        data = self.data[key]
        del self.data[key]
        return data

class OnlineDocument():

    def __init__(self, id, doc, connection, fcuuid):
        self.id = id
        self.document = doc
        self.connection = connection 
        self.objIds = {}
        self.store = DataStore()
        self.fcUuid = fcuuid
        
        try:
            #connect the data upload method
            connection.session.register(self.__dataUpload, 
                                        u'freecad.{0}.{1}.dataUpload'.format(str(self.fcUuid), id),  
                                        RegisterOptions(details_arg='details'))
        except Exception as e:
            print("Online document startup error: {}".format(e))
        
        print("new online document created")
    
    async def __dataUpload(self, key, details=None):

        if details.progress:
                   
            data = self.store.getData(key)
            size = 1024*256 #should be 0.25mb
            for i in range(0, len(data), size):
                block = data[i:i+size]
                await details.progress(bytes(block))
                
        else: 
            return bytes(self.store.getData(key))
    
    
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

    async def asyncNewObject(self, obj):
        try:
            uri = u"ocp.documents.edit.{0}".format(self.id)
            
            #create the object
            objid = await self.connection.session.call(uri + u".methods.Document.Objects.NewObject", obj.Name)
            self.objIds[obj] = objid

            #add all the properties
            for prop in obj.PropertiesList:
                
                docu = obj.getDocumentationOfProperty(prop)
                #emode = obj.getEditorMode(prop)
                group = obj.getGroupOfProperty(prop)
                typeid = obj.getTypeIdOfProperty(prop)
                ptype = '-'.join(obj.getTypeOfProperty(prop))
                
                print("add/write object " + obj.Name + " property " + prop +" (" + typeid + ")")
                await self.connection.session.call(uri + u".methods.{0}.NewProperty".format(objid), prop, ptype, typeid, group, docu)
                await self.asyncWriteProperty(obj, prop)
                
        
        except Exception as e:
            print("Adding object error: {0}".format(e))
         
         
    async def asyncWriteProperty(self, obj, prop):
       
        value = Property.convertPropertyToWamp(obj, prop)  
        uri = u"ocp.documents.edit.{0}".format(self.id)
        objid = self.objIds[obj]
        
        try:
            if isinstance(value, bytearray):
                #store the data for the processing!
                datakey = self.store.addData(value)
                
                #than we need the id of the property where we add the data
                propid = await self.connection.session.call(uri + u".methods.{0}.GetProperty".format(objid), prop)
                
                #call "SetBinary" for the property
                datauri = u'freecad.{0}.{1}.dataUpload'.format(str(self.fcUuid), self.id)
                await self.connection.session.call(uri + u".rawdata.{0}.SetByBinary".format(propid), datauri, datakey)
                
            else:
                #simple POD property: just add it!
                await self.connection.session.call(uri + u".methods.{0}.SetProperty".format(objid), prop, value)
        
        except Exception as e:
            print("Writing property error: {0}".format(e))
            
    
    async def asyncReadProperty(self, obj, prop):
        pass

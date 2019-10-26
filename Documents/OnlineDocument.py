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

class OnlineDocument():

    def __init__(self, id, doc, connection):
        self.id = id
        self.document = doc
        self.connection = connection
        print("new online document created")
    
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
            objid = await self.connection.session.call(uri + u".methods.Document.DocumentObjects.New", obj.Name)

            #add all the properties
            for prop in obj.PropertiesList:
                
                docu = obj.getDocumentationOfProperty(prop)
                #emode = obj.getEditorMode(prop)
                group = obj.getGroupOfProperty(prop)
                typeid = obj.getTypeIdOfProperty(prop)
                ptype = '-'.join(obj.getTypeOfProperty(prop))
                
                await self.connection.session.call(uri + u".methods.{0}.AddProperty".format(objid), prop, ptype, typeid, group, docu)
                
        
        except Exception as e:
            print("Adding object error: {0}".format(e))
            return []

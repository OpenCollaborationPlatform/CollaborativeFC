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

# Set of functions to unify interaction with FreeCAD objects. The methods here work 
# all for DocumentObjects as well as ViewProviders

import Documents.Property as Property
import Documents.Observer as Observer
import FreeCAD, FreeCADGui
from contextlib import contextmanager

__FC018_Extensions = ["App::GroupExtensionPython", "App::GeoFeatureGroupExtensionPython", 
                      "App::OriginGroupExtensionPython", "Gui::ViewProviderGeoFeatureGroupExtensionPython",
                      "Gui::ViewProviderGroupExtensionPython", "Gui::ViewProviderOriginGroupExtensionPython", 
                      "Part::AttachExtensionPython", "PartGui::ViewProviderAttachExtensionPython"]


#Simplify object cleanup by making it a context
@contextmanager
def __fcobject_cleanup(obj):
    try: 
        yield
    finally: 
        if obj.TypeId  == "Spreadsheet::Sheet":
            obj.recompute()  #Spreadsheet setup dynamic alias properties in recompute
            
        elif hasattr(obj, "purgeTouched"):
            obj.purgeTouched()

# Simplify object handling by combining observer blockingand object cleanup
@contextmanager
def __fcobject_processing(obj):
    with Observer.blocked(obj.Document) as a, __fcobject_cleanup(obj) as b:
        yield (a, b)



def createDynamicProperty(obj, prop, typeID, group, documentation, status):
        
    if hasattr(obj, prop):
        return
        
    with __fcobject_processing(obj):
        
        attributes = Property.statusToType(status)            
        obj.addProperty(typeID, prop, group, documentation, attributes)
        
        if float(".".join(FreeCAD.Version()[0:2])) >= 0.19:
            obj.setPropertyStatus(prop, status)
        else:
            mode = Property.statusToEditorMode(status)
            if mode:
                obj.setEditorMode(prop, mode)


def createDynamicProperties(obj, props, infos):
    
    with __fcobject_processing(obj):
        for prop, info in zip(props, infos):
            if prop in obj.PropertiesList:
                continue
                            
            attributes = Property.statusToType(info["status"])            
            obj.addProperty(info["id"], prop, info["group"], info["docu"], attributes)
            
            if float(".".join(FreeCAD.Version()[0:2])) >= 0.19:
                obj.setPropertyStatus(prop, info["status"])
            else:
                mode = Property.statusToEditorMode(info["status"])
                if mode:
                    obj.setEditorMode(prop, mode)
   

def removeDynamicProperty(obj, prop):
    
    if not prop in obj.PropertiesList:
        return
            
    with __fcobject_processing(obj):
        obj.removeProperty(prop)

            
def removeDynamicProperties(obj, props):
    
    with __fcobject_processing(obj):
        for prop in props:
            if not prop in obj.PropertiesList:
                continue
    
            obj.removeProperty(prop)
        

def createExtension(obj, ext):
    
    if obj.hasExtension(ext):
        return

    with __fcobject_processing(obj):

        if  float(".".join(FreeCAD.Version()[0:2])) >= 0.19:
            obj.addExtension(ext)
        else:
            obj.addExtension(ext, None)


def removeExtension(obj, ext):
            
    if not obj.hasExtension(ext):
        return

    with __fcobject_processing(obj):
        obj.removeExtension(ext, None)


def setProperty(obj, prop, value):
        
    with __fcobject_processing(obj):
        Property.convertWampToProperty(obj, prop, value)

    
def setProperties(obj, props, values):
        
    with __fcobject_processing(obj):
        for prop, value in zip(props, values):
            Property.convertWampToProperty(obj, prop, value)
           

def setPropertyStatus(obj, prop, status):

    with __fcobject_processing(obj):
    
        if  float(".".join(FreeCAD.Version()[0:2])) >= 0.19:
            #to set the status multiple things need to happen:
            # 1. remove all string status entries we do not support
            supported = obj.getPropertyStatus()
            filtered = [s for s in status if not isinstance(s, str) or s in supported]

            # 2. check which are to be added, and add those
            current = obj.getPropertyStatus(prop)
            add = [s for s in filtered if not s in current]
            obj.setPropertyStatus(prop, add)
            
            # 3. check which are to be removed, and remove those
            remove = [s for s in current if not s in filtered]
            signed = [-s for s in remove if isinstance(s, int) ]
            signed += ["-"+s for s in remove if isinstance(s, str) ]
            obj.setPropertyStatus(prop, signed)                
        
        else:
            obj.setEditorMode(prop, Property.statusToEditorMode(status))


def getExtensions(obj):
    
    if  float(".".join(FreeCAD.Version()[0:2])) >= 0.19:
       
        allExt    = [e.Name for e in FreeCAD.Base.TypeId.getAllDerivedFrom("App::Extension")]
        pythonExt = [e for e in allExt if "Python" in e]
    
    else:
        pythonExt = __FC018_Extensions 
       
    return [e for e in pythonExt if obj.hasExtension(e)]

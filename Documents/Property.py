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
#

import FreeCAD as App

__typeToStatusMap__ = {
    "NoRecompute": 23,
    "ReadOnly": 24,
    "Transient": 25,
    "Hidden": 26,
    "Output": 27
}

#list of proeprty types which do not have a consistant default value
__non_default_property_types__ = [
    "App::PropertyUUID"
]

def createPropertyInfo(obj, prop):
    info = {}
    info["docu"] = obj.getDocumentationOfProperty(prop)
    info["group"] = obj.getGroupOfProperty(prop)
    info["typeid"] = obj.getTypeIdOfProperty(prop)
    
    status = []
    if  float(".".join(App.Version()[0:2])) >= 0.19:
        status = obj.getPropertyStatus(prop)
    else:
        #add the types (those are static status entries in >=0.19)
        for pt in obj.getTypeOfProperty(prop):
            status.append(__typeToStatusMap__[pt])
            
        #add the two variable status fields that are already supported in 0.18
        for edit in obj.getEditorMode(prop):
            status.append(edit)

    info["status"] = status
       
    return info

def statusToType(status):
    #converts a status list, as returned by "getPropertyStatus", into a attribute bit list as used by property type
    
    statusBitMap = {
        24: 1,
        25: 2,
        26: 4, 
        27: 8, 
        23: 16,
        22: 32
    }
    
    attributes = 0
    for stat in status:
        if stat in statusBitMap:
            attributes  |= statusBitMap[stat]
            
    return attributes


def statusToEditorMode(status):
    
    modes = []
    if "ReadOnly" in status:
        modes.append("ReadOnly")
    if "Hidden" in status:
        modes.append("Hidden")
            
    return modes


def convertPropertyToWamp(obj, prop):
    #converts the property to a wamp usable form
    typeId = obj.getTypeIdOfProperty(prop)
    converter = __PropertyToWamp.get(typeId, __toRaw)
    result = converter(obj, prop)
    return result


def convertWampToProperty(obj, prop, value):
    
    if not prop in obj.PropertiesList:
        raise Exception(f"Object {obj.Name} does not have property {prop}")
    
    #we do not set read-only properties
    if  float(".".join(App.Version()[0:2])) >= 0.19:
        if "Immutable" in obj.getPropertyStatus(prop) or 24 in obj.getPropertyStatus(prop):
            return
    else:
        if "ReadOnly" in obj.getTypeOfProperty(prop):
            return
    
    #converts the wamp data in usable form and assigns it to the property
    typeId = obj.getTypeIdOfProperty(prop)
    converter = __PropertyFromWamp.get(typeId, __fromRaw)
    converter(obj, prop, value)


def getNonDefaultValueProperties(obj):
    
    result = []
    
    #all properties with types that have changing default value
    for prop in obj.PropertiesList:
        if obj.getTypeIdOfProperty(prop) in __non_default_property_types__:
            result.append(prop)   
     
    return result


def __toFloat(obj, prop):
    return float(obj.getPropertyByName(prop))


def __toInt(obj, prop):
    return int(obj.getPropertyByName(prop))


def __toBool(obj, prop):
    return bool(obj.getPropertyByName(prop))


def __toString(obj, prop):
    return str(obj.getPropertyByName(prop))


def __toRaw(obj, prop):
   return obj.dumpPropertyContent(prop, Compression=9)

def __linkToString(obj, prop):
    linked = getattr(obj, prop)
    if not linked:
        return ""
    
    return linked.Name

def __toJson(obj, prop):
    
    import json
    value = getattr(obj, prop)
    return json.dumps(value)
    

__PropertyToWamp = {
"App::PropertyFloat": __toFloat,
"App::PropertyPrecision": __toFloat,
"App::PropertyQuantity": __toFloat,
"App::PropertyAngle": __toFloat,
"App::PropertyDistance": __toFloat,
"App::PropertyLength": __toFloat,
"App::PropertyArea": __toFloat,
"App::PropertyVolume": __toFloat,
"App::PropertySpeed": __toFloat,
"App::PropertyAcceleration": __toFloat,
"App::PropertyForce": __toFloat,
"App::PropertyPressure": __toFloat,
"App::PropertyInteger": __toInt,
"App::PropertyPercent": __toInt,
"App::PropertyBool": __toBool,
"App::PropertyPath": __toString,
"App::PropertyString": __toString,
"App::PropertyUUID": __toString,
"App::PropertyLink": __linkToString,
"App::PropertyLinkChild": __linkToString,
"App::PropertyLinkGlobal": __linkToString,
"App::PropertyExpressionEngine": __toJson
}


def __fromPOD(obj, prop, value):
    setattr(obj, prop, value)


def __fromRaw(obj, prop, value):
    return obj.restorePropertyContent(prop, value)


def __fromLinkString(obj, prop, value):
    if value == "":
        setattr(obj, prop, None)
        return
    
    doc = obj.Document 
    if not hasattr(doc, value):
        raise Exception(f"Document has no object {value}")
    
    linked = doc.getObject(value)
    setattr(obj, prop, linked)
    
    
def __exprFromJson(obj, prop, value):
    
    import json
    load_exprs = json.loads(value)
    
    #clear all expressions
    current_exprs = obj.ExpressionEngine
    for expr in current_exprs:
        obj.setExpression(expr[0], None)
    
    for expr in load_exprs:
        obj.setExpression(expr[0], expr[1])

        

__PropertyFromWamp = {
"App::PropertyFloat": __fromPOD,
"App::PropertyPrecision": __fromPOD,
"App::PropertyQuantity": __fromPOD,
"App::PropertyAngle": __fromPOD,
"App::PropertyDistance": __fromPOD,
"App::PropertyLength": __fromPOD,
"App::PropertyArea": __fromPOD,
"App::PropertyVolume": __fromPOD,
"App::PropertySpeed": __fromPOD,
"App::PropertyAcceleration": __fromPOD,
"App::PropertyForce": __fromPOD,
"App::PropertyPressure": __fromPOD,
"App::PropertyInteger": __fromPOD,
"App::PropertyPercent": __fromPOD,
"App::PropertyBool": __fromPOD,
"App::PropertyPath": __fromPOD,
"App::PropertyString": __fromPOD,
"App::PropertyUUID": __fromPOD,
"App::PropertyLink": __fromLinkString,
"App::PropertyLinkChild": __fromLinkString,
"App::PropertyLinkGlobal": __fromLinkString,
"App::PropertyExpressionEngine": __exprFromJson
}

#['App::PropertyBoolList', 'App::PropertyFloatList', 'App::PropertyFloatConstraint', 'App::PropertyQuantityConstraint', 'App::PropertyFrequency', 'App::PropertyVacuumPermittivity', 'App::PropertyInteger', 'App::PropertyIntegerConstraint', 'App::PropertyEnumeration', 'App::PropertyIntegerList', 'App::PropertyIntegerSet', 'App::PropertyMap', 'App::PropertyPersistentObject', 'App::PropertyFont', 'App::PropertyStringList',  'App::PropertyLinkHidden', 'App::PropertyLinkSub', 'App::PropertyLinkSubChild', 'App::PropertyLinkSubGlobal', 'App::PropertyLinkSubHidden', 'App::PropertyLinkList', 'App::PropertyLinkListChild', 'App::PropertyLinkListGlobal', 'App::PropertyLinkListHidden', 'App::PropertyLinkSubList', 'App::PropertyLinkSubListChild', 'App::PropertyLinkSubListGlobal', 'App::PropertyLinkSubListHidden', 'App::PropertyXLink', 'App::PropertyXLinkSub', 'App::PropertyXLinkSubList', 'App::PropertyXLinkList', 'App::PropertyMatrix', 'App::PropertyVector', 'App::PropertyVectorDistance', 'App::PropertyPosition', 'App::PropertyDirection', 'App::PropertyVectorList', 'App::PropertyPlacement', 'App::PropertyPlacementList', 'App::PropertyPlacementLink', 'App::PropertyColor', 'App::PropertyColorList', 'App::PropertyMaterial', 'App::PropertyMaterialList', ' 'App::PropertyFile', 'App::PropertyFileIncluded', 'App::PropertyPythonObject', 'App::PropertyExpressionEngine', 'Part::PropertyPartShape', 'Part::PropertyGeometryList', 'Part::PropertyShapeHistory', 'Part::PropertyFilletEdges', 'TechDraw::PropertyGeomFormatList', 'TechDraw::PropertyCenterLineList', 'TechDraw::PropertyCosmeticEdgeList', 'TechDraw::PropertyCosmeticVertexList', 'Mesh::PropertyNormalList', 'Mesh::PropertyCurvatureList', 'Mesh::PropertyMeshKernel', 'Fem::PropertyFemMesh', 'Fem::PropertyPostDataObject', 'Sketcher::PropertyConstraintList', 'Robot::PropertyTrajectory']

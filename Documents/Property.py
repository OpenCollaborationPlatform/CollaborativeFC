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

def createPropertyInfo(obj, prop):
    info = {}
    info["docu"] = obj.getDocumentationOfProperty(prop)
    info["group"] = obj.getGroupOfProperty(prop)
    info["typeid"] = obj.getTypeIdOfProperty(prop)
    info["ptype"] = '-'.join(obj.getTypeOfProperty(prop))
    
    return info

def convertPropertyToWamp(obj, prop):
    #converts the property to a wamp usable form
    
    typeId = obj.getTypeIdOfProperty(prop)
    converter = __PropertyToWamp.get(typeId, __toRaw)
    result = converter(obj, prop)
    return result


def convertWampToProperty(obj, prop, value):
    #converts the wamp data in usable form and assigns it to the property
    
    typeId = obj.getTypeIdOfProperty(prop)
    converter = __PropertyFromWamp.get(typeId, __fromRaw)
    converter(obj, prop, value)


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
"App::PropertyLinkGlobal": __linkToString
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
    linked = doc.getObject(value)
    setattr(obj, prop, linked)

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
"App::PropertyLinkGlobal": __fromLinkString
}

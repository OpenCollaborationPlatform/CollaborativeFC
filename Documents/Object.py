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

def createDynamicProperty(obj, prop, typeID, group, documentation, status):
        
    try: 
        if hasattr(obj, prop):
            return
            
        with Observer.blocked(obj.Document):
            
            attributes = Property.statusToType(status)            
            obj.addProperty(typeID, prop, group, documentation, attributes)
            
            if float(".".join(FreeCAD.Version()[0:2])) >= 0.19:
                obj.setPropertyStatus(prop, status)
            else:
                mode = Property.statusToEditorMode(status)
                if mode:
                    obj.setEditorMode(prop, mode)
        
    finally:
        if hasattr(obj, "purgeTouched"):
            obj.purgeTouched()


def removeDynamicProperty(obj, prop):
    
    try: 
        if not hasattr(obj, prop):
            return
                
        with Observer.blocked(obj.Document):
            obj.removeProperty(prop)
        
        
    finally:
        if hasattr(obj, "purgeTouched"):
            obj.purgeTouched()
        

def createExtension(obj, ext):
    
    try:
        if obj.hasExtension(ext):
            return

        with Observer.blocked(obj.Document):

            if  float(".".join(FreeCAD.Version()[0:2])) >= 0.19:
                obj.addExtension(ext)
            else:
                obj.addExtension(ext, None)

    finally:
        if hasattr(obj, "purgeTouched"):
            obj.purgeTouched()


def removeExtension(obj, ext):
            
    try:
        if not obj.hasExtension(ext):
            return
    
        with Observer.blocked(obj.Document):
            obj.removeExtension(ext, None)
        
    finally:
        if hasattr(obj, "purgeTouched"):
            obj.purgeTouched()



def setProperty(obj, prop, value):
        
    try:      
        with Observer.blocked(obj.Document):
            Property.convertWampToProperty(obj, prop, value)

    finally:           
        if hasattr(obj, "purgeTouched"):
            obj.purgeTouched()

    
def setProperties(obj, props, values):
        
    try:      
       with Observer.blocked(obj.Document):
           for index, prop in enumerate(props):
               Property.convertWampToProperty(obj, prop, values[index])

    finally:           
        if hasattr(obj, "purgeTouched"):
            obj.purgeTouched()
           

def setPropertyStatus(obj, prop, status):

    try:
        with Observer.blocked(obj.Document):
        
            if  float(".".join(FreeCAD.Version()[0:2])) >= 0.19:
                #to set the status multiple things need to happen:
                # 1. remove all string status entries we do not support
                supported = obj.getPropertyStatus()
                filterd = [s for s in status if not isinstance(s, str) or s in supported]

                # 2. check which are to be added, and add those
                current = obj.getPropertyStatus(prop)
                add = [s for s in filterd if not s in current]
                obj.setPropertyStatus(prop, add)
                
                # 3. check which are to be removed, and remove those
                remove = [s for s in current if not s in filterd]
                signed = [-s for s in remove if isinstance(s, int) ]
                signed += ["-"+s for s in remove if isinstance(s, str) ]
                obj.setPropertyStatus(prop, signed)                
            
            else:
                obj.setEditorMode(prop, Property.statusToEditorMode(status))
    
    finally:            
        if hasattr(obj, "purgeTouched"):
            obj.purgeTouched()


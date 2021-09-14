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

from enum import Enum, auto

# error classes:
class ErrorClass(Enum):
    internal = auto()
    connection = auto()
    application = auto()
    type = auto()
    user = auto()
    none = auto()

Key_Not_Available = "key_not_available"

def isOCPError(error, errclass: ErrorClass=ErrorClass.none, source: str=None, reason: str=None):
        
    if not hasattr(error, "error"):
        return False

    uri = error.error
    if not uri.startswith("ocp.error"):
        return False
    
    comps = uri.split(".")
    if errclass != ErrorClass.none and [2] != errclass.name:
        return False
        
    if source and comps[3] != source:
        return False
    
    if reason and comps[4] != reason:
        return False
    
    return True


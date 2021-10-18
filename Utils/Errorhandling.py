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
from autobahn import wamp

# error classes:
class ErrorClass(Enum):
    internal = auto()
    connection = auto()
    application = auto()
    type = auto()
    user = auto()
    wamp = auto()
    none = auto()

Key_Not_Available = "key_not_available"


class OCPError(RuntimeError):
    
    def __init__(self, exptn: wamp.ApplicationError):
       
        components = exptn.error.split(".")
        if not exptn.error.startswith("ocp.error"):
            self.errclass = ErrorClass.wamp
            self.source = "router"
            self.reason = components[-1]
        else:
            self.errclass = ErrorClass(components[2])
            self.source = components[3]
            self.reason = components[4]       
        
        self.message = "unknown failure"
        self.origin = str()
        self.arguments = []
        self.stack = []
        
        if len(exptn.args) == 4:
            self.message = exptn.args[0]
            self.origin = exptn.args[1]
            self.arguments = exptn.args[2]
            self.stack = exptn.args[3]
        
        super().__init__(exptn.error)
        
    def __str__(self):
         msg = self.error + ": " + self.message
         if self.arguments:
             msg += " ("
             for i in range(len(self.arguments)/2):
                 msg += str(self.args[i*2]) + ": " + str(self.args[i*2+1]) + ", "
             
             msg += ")"
             
         return msg
        

def isOCPError(error: Exception, errclass: ErrorClass=ErrorClass.none, source: str=None, reason: str=None) -> bool:
        
    if isinstance(error, OCPError):
        
        if errclass != ErrorClass.none and error.errclass != errclass:
            return False
        if source and source != error.source:
            return False
        if reason and reason != error.reason:
            return False     
        
        return True
        
    elif isinstance(error, wamp.ApplicationError):
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

    return False

       

class ErrorHandler():
    ''' Base class that allows unified error handling in a ownership hirarchy, e.g. allows catching errors in a ErrorHandler a object keeps 
        a reference of.    
    ''' 
    
    def __init__(self):
        pass
    
    def __handleError(self, error: Exception):
        pass
    
    def getErrorHandler(self):
        return self.__handleError
    
    pass

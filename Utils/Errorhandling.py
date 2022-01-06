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
from asyncio import CancelledError
from typing import Any

# error classes:
class OCPErrorClass(Enum):
    internal = auto()
    connection = auto()
    application = auto()
    type = auto()
    user = auto()
    wamp = auto()
    none = auto()

Key_Not_Available = "key_not_available"


class OCPError():
    
    def __init__(self, exptn: wamp.ApplicationError):
       
        components = exptn.error.split(".")
        if not exptn.error.startswith("ocp.error"):
            self.errclass = OCPErrorClass.wamp
            self.source = "router"
            self.reason = components[-1]
        else:
            self.errclass = OCPErrorClass[components[2]]
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
    
    def __repr__(self): 
        return self.__str__()
    
    def __str__(self):
         msg = str(self.errclass) + ": " + self.message
         if self.arguments:
             msg += " ("
             for i in range(int(len(self.arguments)/2)):
                 msg += str(self.arguments[i*2]) + ": " + str(self.arguments[i*2+1]) + ", "
             
             msg += ")"
             
         return msg
     
    def fullMessage(self):
         
         msg = self.__str__()
         msg += "\nOrigin: " + self.origin
         msg += "\nStack: \n"
         
         for s in self.stack:
             msg += s + "\n"
         
         return msg
        

def isOCPError(error: Exception, errclass: OCPErrorClass=OCPErrorClass.none, source: str=None, reason: str=None) -> bool:
        
    if isinstance(error, wamp.ApplicationError):
        uri = error.error
        if not uri.startswith("ocp.error"):
            return False
        
        comps = uri.split(".")
        if errclass != OCPErrorClass.none and [2] != errclass.name:
            return False
            
        if source and comps[3] != source:
            return False
        
        if reason and comps[4] != reason:
            return False
        
        return True

    return False


def attachErrorData(exception: Exception, key: str, value: Any):
    
    if not hasattr(exception, "_ocp_error_data"):
        exception._ocp_error_data = {}
        
    exception._ocp_error_data[key] = value
    
    return exception

   
class ErrorHandler():
    
    class Exceptions(Enum):
        Default    = auto()       # any unknown exception
        Canceled   = auto()       # asyncio Canceled error
    
    def __init__(self):
        self._parents     = []
        self.__subhandler = []
    
    def _registerSubErrorhandler(self, handler):
        self.__subhandler.append(handler)
        if not self in handler._parents:
            handler._parents.append(self)
    
    def _unregisterSubErrorhandler(self, handler):
        
        if handler in self.__subhandler:
            self.__subhandler.remove(handler)
            if self in handler._parents:
                handler._parents.remove(self)
    
    def __upstream(self, error: Enum, data: Any):
        
        if not self._parents:
            return
        
        for parent in self._parents:
            parent._handleError(self, error, data)
        
    def _extractErrorData(self, exception: Exception) -> dict[str, Any]:
        # Extracts all attached error data into a dictionary
        
        data = {}
        if  hasattr(exception, "_ocp_error_data"):
            data = exception._ocp_error_data
        
        data["exception"] = exception
        return data
        
    
    def _processException(self, exception: Exception):
        # Processes exceptions into errors. To override by subclasses

        if isinstance(exception, CancelledError):
            self._handleError(self, ErrorHandler.Exceptions.Canceled, self._extractErrorData(exception))
        else:
            self._handleError(self, ErrorHandler.Exceptions.Default, self._extractErrorData(exception))
    
    
    def _handleError(self, source, error: Enum, data: dict[str, Any]):
        # Receives all errors created in any subhandler.
        # To be overriden
        self.__upstream(error, data)


class WampErrorHandler(ErrorHandler):

    class WampError(Enum):
        General = auto
        Timeout = auto()
        Application = auto()
        

    def _processException(self, exception: Exception):
        # Processes exceptions into errors.
        
        if not isinstance(exception, wamp.Error):
            super()._processException(exception)
        
        data = self._extractErrorData(exception)
        data["arguments"] = exception.args
        
        if isinstance(exception, wamp.ApplicationError):
            if exception.error == wamp.ApplicationError.CANCELED:
                self._handleError(self, WampErrorHandler.WampError.Timeout, data)
            
            else:
                self._handleError(self, WampErrorHandler.WampError.Application, data)
        
        else:
            self._handleError(self, WampErrorHandler.WampError.General, data)
            

class OCPErrorHandler(WampErrorHandler):
    
    class OCPError(Enum):
        Application = auto()        
        Connection = auto()
        Internal = auto()
            
    def _processException(self, exception: Exception):
        # Processes exceptions into errors.
        
        
        if not isOCPError(exception):
            super()._processException(exception)
            return 
        
        data = self._extractErrorData(exception)
        data["OCPError"] = OCPError(exception)
        
        if isOCPError(exception, errclass=OCPErrorClass.application):
            self._handleError(self, OCPErrorHandler.OCPError.Application, data)
            
        elif isOCPError(exception, errclass=OCPErrorClass.connection):
            self._handleError(self, OCPErrorHandler.OCPError.Connection, data)
        
        else:
            self._handleError(self, OCPErrorHandler.OCPError.Internal, data)
            
            

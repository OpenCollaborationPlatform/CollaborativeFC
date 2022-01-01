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


import asyncio, txaio, os, logging
from autobahn.asyncio.component import Component
from Qasync import QEventLoop
from PySide import QtCore
from Qasync import asyncSlot
from OCP.Node       import Node
from OCP.API        import API
from OCP.Network    import Network


#Class to handle all connection matters to the ocp node
#must be provided all components that need to use this connection
class OCPConnection(QtCore.QObject):
       
    def __init__(self, *argv):
        
        QtCore.QObject.__init__(self)
        
        self.__logger   = logging.getLogger("OCP")
        self.__node     = Node(self.__logger.getChild("Node"))
        self.__api      = API(self.__node, self.__logger.getChild("API"))
        self.__network  = Network(self.__api, self.__logger.getChild("Network"))
    
    def start(self):
        self.__node.start()
        
    def stop(self):
        self.__node.stop()
        
    # Qt Property/Signal API used from the UI
    # ********************************************************************************************
    def nodeGetter(self):
        return self.__node

    node = QtCore.Property(QtCore.QObject, nodeGetter, constant=True)


    def apiGetter(self):
        return self.__api

    api = QtCore.Property(QtCore.QObject, apiGetter, constant=True)


    def networkGetter(self):
        return self.__network

    network = QtCore.Property(QtCore.QObject, networkGetter, constant=True)

 

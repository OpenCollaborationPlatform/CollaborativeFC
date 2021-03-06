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

import FreeCADGui, asyncio, os
from PySide2 import QtCore, QtGui, QtWidgets

from Interface.DocumenWidget import DocWidget, DocView


class UIWidget(QtWidgets.QFrame):
    
    def __init__(self, manager, connection):
        
        super().__init__()
        
        self.__connection = connection
        self.__manager = manager

        # We are a popup, make sure we look like it
        self.setContentsMargins(1,1,1,1)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Popup)
        self.setGeometry(0, 0, 375, 500)   
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)
        
        self.ui = FreeCADGui.PySideUic.loadUi(":/Collaboration/Ui/Controls.ui")
        
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.ui)
        self.setLayout(layout)
        
        # setup document management
        self.__docView = DocView(manager)
        self.ui.docArea.setWidget(self.__docView)
        self.__manager.documentAdded.connect(self.__docView.onDocumentAdded)
        self.__manager.documentRemoved.connect(self.__docView.onDocumentRemoved)
        self.__manager.documentChanged.connect(self.__docView.onDocumentChanged)
        
        # setup node, api and network
        self.ui.peerView.setVisible(False)
        self.ui.logsView.setVisible(False)
        self.ui.nodeButton.clicked.connect(lambda c: self.ui.stack.setCurrentIndex(0))
        self.ui.docButton.clicked.connect(lambda c: self.ui.stack.setCurrentIndex(1))
        
        self.__onNodeRunningChanged()
        self.__connection.node.logModelChanged.connect(lambda: self.ui.logsView.setModel(self.__connection.node.logModel))
        self.__connection.node.runningChanged.connect(self.__onNodeRunningChanged)
        self.ui.startupButton.released.connect(self.__connection.node.toggleRunningSlot)
        
        self.__onApiConnectedChanged()        
        self.__connection.api.connectedChanged.connect(self.__onApiConnectedChanged)
        self.ui.connectButton.released.connect(self.__connection.api.toggleConnectedSlot)
        self.ui.reconnectCheckbox.setChecked(self.__connection.api.reconnect)
        self.ui.reconnectCheckbox.toggled.connect(self.__connection.api.setReconnect)
        
        self.__onNetworkUpdates()
        self.__connection.network.peerCountChanged.connect(self.__onNetworkUpdates)
        self.__connection.network.nodeIdChanged.connect(self.__onNetworkUpdates)
        self.__connection.network.reachabilityChanged.connect(self.__onNetworkUpdates)
        self.ui.peerView.setModel(self.__connection.network.peers)
        
    
    def show(self):
        #try to find the correct position for the popup
        pos = QtGui.QCursor.pos()
        widget = QtWidgets.QApplication.widgetAt(pos)
        point = widget.rect().bottomLeft()
        global_point = widget.mapToGlobal(point)
        self.move(global_point)            
        super().show()


    # Qt slots 
    # ******************************************************************
        
    @QtCore.Slot()
    def __onNodeRunningChanged(self):
        # the node object changed its running status
        
        if self.__connection.node.running:
            self.ui.nodeIndicator.setPixmap(QtGui.QPixmap(":/Collaboration/Icons/indicator_on.svg"))
            self.ui.nodeLabel.setText("OCP node running")
            self.ui.startupButton.setText("Shutdown")
            self.ui.connectButton.setEnabled(True)
        else:
            self.ui.nodeIndicator.setPixmap(QtGui.QPixmap(":/Collaboration/Icons/indicator_off.svg"))
            self.ui.nodeLabel.setText("No OCP node running")
            self.ui.startupButton.setText("Startup")
            self.ui.connectButton.setEnabled(False)

    @QtCore.Slot()
    def __onApiConnectedChanged(self):
        # the api object changed its connected status
        
        if self.__connection.api.connected:
            self.ui.apiIndicator.setPixmap(QtGui.QPixmap(":/Collaboration/Icons/indicator_on.svg"))
            self.ui.apiLabel.setText("API connection established")
            self.ui.connectButton.setText("Disconnect")
            self.ui.startupButton.setEnabled(False)
        else:
            self.ui.apiIndicator.setPixmap(QtGui.QPixmap(":/Collaboration/Icons/indicator_off.svg"))
            self.ui.apiLabel.setText("API not connected to node")
            self.ui.connectButton.setText("Connect")
            self.ui.startupButton.setEnabled(True)

    @QtCore.Slot()
    def __onNetworkUpdates(self):
        self.ui.nodeIdLabel.setText(self.__connection.network.nodeId)
        self.ui.reachabilityLabel.setText(self.__connection.network.reachability)
        self.ui.peerCountLabel.setText(f"Connected to {self.__connection.network.peerCount} nodes.")
        
        if self.__connection.network.peerCount > 0:
            self.ui.networkIndicator.setPixmap(QtGui.QPixmap(":/Collaboration/Icons/indicator_on.svg"))
            self.ui.networkLabel.setText("Part of P2P network")
        else:
            self.ui.networkIndicator.setPixmap(QtGui.QPixmap(":/Collaboration/Icons/indicator_off.svg"))
            self.ui.networkLabel.setText("Cannot find P2P network")
        
        if self.__connection.network.reachability == "Public":
            self.ui.reachabilityIndicator.setPixmap(QtGui.QPixmap(":/Collaboration/Icons/indicator_on.svg"))
        else:
            self.ui.reachabilityIndicator.setPixmap(QtGui.QPixmap(":/Collaboration/Icons/indicator_off.svg"))
     
     
     

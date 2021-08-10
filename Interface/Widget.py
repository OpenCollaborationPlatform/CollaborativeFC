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

from Interface.AsyncSlotWidget import AsyncSlotPromoter
from Interface.DocView import DocView
from Interface.DocEdit import DocEdit
from Interface.Installer import InstallView


class UIWidget(QtWidgets.QFrame):
    
    def __init__(self):
        super().__init__()
        
        self.__docView = None
        self.__docEdit = None
       
        # We are a popup, make sure we look like it
        self.setContentsMargins(0,0,0,0)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Popup)
        self.setGeometry(0, 0, 375, 500)   
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)
        
        self.ui = FreeCADGui.PySideUic.loadUi(":/Collaboration/Ui/Controls.ui")
        
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        layout.addWidget(self.ui)
        layout.addWidget(QtWidgets.QSizeGrip(self), 0, QtCore.Qt.AlignBottom | QtCore.Qt.AlignRight)
        self.setLayout(layout)
        
        # Set the correct sizes dependent on system setting
        fontSize = 1.5*self.ui.nodeLabel.font().pointSize()
        largeFont = self.ui.nodeLabel.font()
        largeFont.setPointSize(fontSize)
        self.ui.nodeLabel.setFont(largeFont)
        largeSize  = QtGui.QFontMetrics(largeFont).ascent()
        self.ui.nodeIndicator.setMaximumSize(largeSize, largeSize)
        self.ui.apiLabel.setFont(largeFont)
        self.ui.apiIndicator.setMaximumSize(largeSize, largeSize)
        self.ui.networkLabel.setFont(largeFont)
        self.ui.networkIndicator.setMaximumSize(largeSize, largeSize)
        self.ui.reachabilityMainLabel.setFont(largeFont)
        self.ui.reachabilityLabel.setFont(largeFont)
        self.ui.reachabilityIndicator.setMaximumSize(largeSize, largeSize)
        
        # setup the installer
        self.__installer = InstallView()
        self.ui.stack.addWidget(self.__installer)
        self.ui.stack.setCurrentIndex(2)
        self.ui.tabWidget.setEnabled(False)
        
    def setup(self, manager, connection):
        
        self.__connection = connection
        self.__manager = manager
 
        # async slot handling for node/api
        self.__nodeAsyncWidget  = AsyncSlotPromoter(self.ui.nodeWidget)
        self.__nodeAsyncWidget.setAsyncObject(self.__connection.node)
        self.__apiAsyncWidget  = AsyncSlotPromoter(self.ui.apiWidget)
        self.__apiAsyncWidget.setAsyncObject(self.__connection.api)
 
        # setup document management
        self.__docView = DocView(manager)
        self.__docEdit = DocEdit(manager)
        self.ui.docArea.setWidget(self.__docView)
        self.ui.stack.addWidget(self.__docEdit)
        self.__docEdit.editFinished.connect(self.__onEditFihished)
        self.__docView.edit.connect(self.__onEdit) 
 
        # setup node, api and network
        self.ui.peerView.setVisible(False)
        self.ui.logsView.setVisible(False)
        self.ui.nodeButton.clicked.connect(lambda c: self.ui.stack.setCurrentIndex(0))
        self.ui.docButton.clicked.connect(lambda c: self.ui.stack.setCurrentIndex(1))
        
        self.__onNodeRunningChanged()
        self.__connection.node.logModelChanged.connect(lambda: self.ui.logsView.setModel(self.__connection.node.logModel))
        self.__connection.node.runningChanged.connect(self.__onNodeRunningChanged)
        self.__connection.node.p2pUriChanged.connect(self.__listenDetailsUpdate)
        self.__connection.node.p2pPortChanged.connect(self.__listenDetailsUpdate)
        self.__connection.node.apiUriChanged.connect(self.__listenDetailsUpdate)
        self.__connection.node.apiPortChanged.connect(self.__listenDetailsUpdate)
        self.ui.startupButton.released.connect(self.__connection.node.toggleRunningSlot)
        self.ui.p2pUri.editingFinished.connect(self.__p2pDataChanged)
        self.ui.p2pPort.editingFinished.connect(self.__p2pDataChanged)
        self.ui.apiUri.editingFinished.connect(self.__apiDataChanged)
        self.ui.apiPort.editingFinished.connect(self.__apiDataChanged)
        
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

        # don't show the installer anymore
        self.ui.stack.setCurrentIndex(0)
        self.ui.tabWidget.setEnabled(True)

    def setMissingPackages(self, packages):
        self.__installer.setMissingPackages(packages)
    
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
    
    def resizeEvent(self, event):
        QtWidgets.QFrame.resizeEvent(self, event)
        if self.__docView:
            self.__docView.setMaximumWidth(event.size().width()-24) # 12 = 2x6 ui margin within ui file

    @QtCore.Slot()
    def __onNodeRunningChanged(self):
        # the node object changed its running status
        
        if self.__connection.node.running:
            self.ui.nodeIndicator.setPixmap(QtGui.QPixmap(":/Collaboration/Icons/indicator_on.svg"))
            self.ui.nodeLabel.setText("OCP node running")
            self.ui.startupButton.setText("Shutdown")
            self.ui.connectButton.setEnabled(True)
            self.ui.p2pUri.setEnabled(False)
            self.ui.p2pPort.setEnabled(False)
            self.ui.apiUri.setEnabled(False)
            self.ui.apiPort.setEnabled(False)
        else:
            self.ui.nodeIndicator.setPixmap(QtGui.QPixmap(":/Collaboration/Icons/indicator_off.svg"))
            self.ui.nodeLabel.setText("No OCP node running")
            self.ui.startupButton.setText("Startup")
            self.ui.connectButton.setEnabled(False)
            self.ui.p2pUri.setEnabled(True)
            self.ui.p2pPort.setEnabled(True)
            self.ui.apiUri.setEnabled(True)
            self.ui.apiPort.setEnabled(True)

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
     
    @QtCore.Slot()
    def __p2pDataChanged(self):
        uri = self.ui.p2pUri.text()
        port = self.ui.p2pPort.text()
        if uri != self.__connection.node.p2pUri or port != self.__connection.node.p2pPort:
            self.__connection.node.setP2PDetails(uri, port)
        
    @QtCore.Slot()
    def __apiDataChanged(self):
        uri = self.ui.apiUri.text()
        port = self.ui.apiPort.text()
        if uri != self.__connection.node.apiUri or port != self.__connection.node.apiPort:
            self.__connection.node.setAPIDetails(uri, port)

    @QtCore.Slot()
    def __listenDetailsUpdate(self):
        self.ui.p2pPort.setText(self.__connection.node.p2pPort)
        self.ui.p2pUri.setText(self.__connection.node.p2pUri)
        self.ui.apiPort.setText(self.__connection.node.apiPort)
        self.ui.apiUri.setText(self.__connection.node.apiUri)
     
    @QtCore.Slot(str)
    def __onEdit(self, uuid):
        
        self.__docEdit.setEditable(uuid)
        self.ui.stack.setCurrentIndex(3)
        self.ui.tabWidget.setEnabled(False)
        
    @QtCore.Slot()
    def __onEditFihished(self):
       self.ui.tabWidget.setEnabled(True)
       self.ui.stack.setCurrentIndex(1)

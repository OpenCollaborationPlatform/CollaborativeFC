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

import FreeCADGui, asyncio, os
from PySide2 import QtCore, QtGui, QtWidgets

from Manager.Manager import Entity

class PeerView(QtWidgets.QWidget):
       
    def __init__(self, parent = None):
        
        QtWidgets.QWidget.__init__(self, parent)
        
        self.__docmanager = None
        self.__widgets = {}
        
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(2,2,2,2)
        layout.addStretch(1)
        layout.setSpacing(15)
        self.setLayout(layout)
        
    def setdocument(self, docmanager):
        
        if self.__docmanager:
            self.__docmanager.peerAdded.disconnect(self.__onPeerAdded)
            self.__docmanager.peerRemoved.disconnect(self.__onPeerRemoved)
            self.__docmanager.peerChanged.disconnect(self.__onPeerChanged)
            
        if self.__widgets:
            for widget in self.__widgets.values():
                widget.setVisible(False)
                self.layout().removeWidget(widget)
                widget.deleteLater()
            
            self.__widgets = {}
            
        self.__docmanager = docmanager
        self.__docmanager.peerAdded.connect(self.__onPeerAdded)
        self.__docmanager.peerRemoved.connect(self.__onPeerRemoved)
        self.__docmanager.peerChanged.connect(self.__onPeerChanged)
                
        for peer in docmanager.peers:
            widget = PeerWidget(self.__docmanager, peer.nodeid, self)
            self.__widgets[peer.nodeid] = widget
            self.layout().insertWidget(0, widget)


    @QtCore.Slot(str)
    def __onPeerAdded(self, peerId):
        widget = PeerWidget(self.__docmanager, peerId, self)
        self.__widgets[peerId] = widget
        self.layout().insertWidget(0, widget)
     
    @QtCore.Slot(str)
    def __onPeerRemoved(self, peerId):
        
        if not peerId in self.__widgets:
            return 
        
        widget = self.__widgets.pop(peerId, None)
        if widget:
            widget.setVisible(False)
            self.layout().removeWidget(widget)
            widget.deleteLater()
     
    @QtCore.Slot(str)
    def __onPeerChanged(self, peerId):
       
        if not peerId in self.__widgets:
            return 
        
        self.__widgets[peerId].update()


class PeerWidget(QtWidgets.QWidget):
       
    def __init__(self, docmanager, peerId, parent):
        
        super().__init__(parent)
        
        self.__docmanager = docmanager
        self.__peerId = peerId
        self.__name =  ""

        self.ui = FreeCADGui.PySideUic.loadUi(":/Collaboration/Ui/Peer.ui")
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.ui)
        self.setLayout(layout)
        
        # Set the correct sizes dependent on system setting
        fontSize = 1.2*self.ui.idLabel.font().pointSize()
        largeFont = self.ui.idLabel.font()
        largeFont.setPointSize(fontSize)
        self.ui.idLabel.setFont(largeFont)
        
        self.ui.removeButton.clicked.connect(lambda: self.__docmanager.removePeerSlot(self.__peerId))
        self.ui.rigthsButton.clicked.connect(lambda: self.__docmanager.togglePeerRigthsSlot(self.__peerId))

        self.update()
    
    
    def update(self):
        
        peer = self.__docmanager.getPeer(self.__peerId)
        if not peer:
            return
        
        self.__name = peer.nodeid
        self.ui.idLabel.setText(self.__name)
        self.ui.joinedLabel.setText(f"{peer.joined}")
        self.ui.rigthsLabel.setText(peer.auth)
        if peer.auth == "Write":
            self.ui.rigthsButton.setText("Set Read")
        else:
            self.ui.rigthsButton.setText("Set Write")


    def paintEvent(self, event):
        
        name = self.ui.idLabel.fontMetrics().elidedText(self.__name, QtCore.Qt.ElideRight, self.ui.idLabel.width())
        self.ui.idLabel.setText(name)
        QtWidgets.QWidget.paintEvent(self, event)
        

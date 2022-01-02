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

from Interface.AsyncSlotWidget import AsyncSlotWidget
from Interface.PeerView import PeerView

class DocEdit(QtWidgets.QWidget, AsyncSlotWidget):
    
    editFinished = QtCore.Signal()
    
    def __init__(self, manager, parent=None):
        
        QtWidgets.QWidget.__init__(self, parent)
        AsyncSlotWidget.__init__(self, self)
        
        self.__manager = manager

        self.ui = FreeCADGui.PySideUic.loadUi(":/Collaboration/Ui/DocumentEdit.ui")
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.ui)
        self.setLayout(layout)
        
        self.__peerView = PeerView()
        self.__peerView.setMaximumWidth(self.ui.peerArea.width())
        self.ui.peerArea.setWidget(self.__peerView)
        
        self.ui.closeButton.clicked.connect(lambda: self.editFinished.emit())
        self.ui.addButton.clicked.connect(self.__onAddPeer)
        self.ui.nameInput.editingFinished.connect(self.__onSetName)
    
    def setEditable(self, uuid):
        
        self.__editedEntity = self.__manager.getEntity("uuid", uuid)
        if not self.__editedEntity:
            return
        
        if self.__editedEntity.node_document_manager:
            self.__peerView.setdocument(self.__editedEntity.node_document_manager)
            self.setAsyncObject(self.__editedEntity.node_document_manager)
        
        self.ui.nameInput.setText(self.__editedEntity.node_document_manager.name)
    
    def resizeEvent(self, event):
        QtWidgets.QWidget.resizeEvent(self, event)
        self.__peerView.setMaximumWidth(event.size().width())
    
    @QtCore.Slot()
    def __onAddPeer(self):
        if not self.__editedEntity.manager:
            raise Exception("Document no available on node, cannot be edited")
        
        self.__editedEntity.node_document_manager.addPeerSlot(self.ui.nodeIdInput.text(), self.ui.editRightsInput.isChecked())
        self.ui.nodeIdInput.setText("")
        self.ui.editRightsInput.setChecked(False)
    
    @QtCore.Slot()
    def __onSetName(self):
        if not self.__editedEntity.node_document_manager:
            raise Exception("Document no available on node, cannot be edited")
        
        #if not self.__editedEntity.manager.name == self.ui.nameInput.text:
        #    self.__editedEntity.manager.setNameSlot(self.ui.nameInput.text)

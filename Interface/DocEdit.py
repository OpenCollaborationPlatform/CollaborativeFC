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

from Interface.PeerView import PeerView
from Manager.Manager import Entity

class DocEdit(QtWidgets.QWidget):
    
    editFinished = QtCore.Signal()
    
    def __init__(self, manager, parent=None):
        
        super().__init__(parent)
        
        self.__manager = manager

        self.ui = FreeCADGui.PySideUic.loadUi(":/Collaboration/Ui/DocumentEdit.ui")
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.ui)
        self.setLayout(layout)
        
        self.__peerView = PeerView()
        self.ui.peerArea.setWidget(self.__peerView)
        
        self.ui.closeButton.clicked.connect(lambda: self.editFinished.emit())
        self.ui.addButton.clicked.connect(self.__onAddPeer)
        self.ui.nameInput.editingFinished.connect(self.__onSetName)
    
    def setEditable(self, uuid):
        
        self.__editedEntity = self.__manager.getEntity("uuid", uuid)
        
        if self.__editedEntity.manager:
            self.__peerView.setdocument(self.__editedEntity.manager)
        
        if self.__editedEntity.fcdoc:
            self.ui.nameInput.setText(self.__editedEntity.fcdoc.Label)
        else:
            self.ui.nameInput.setText(self.__editedEntity.id)
            
    
    @QtCore.Slot()
    def __onAddPeer(self):
        if not self.__editedEntity.manager:
            raise Exception("Document no available on node, cannot be edited")
        
        self.__editedEntity.manager.addPeerSlot(self, self.ui.nodeIdInput.text, self.ui.editRigthsInput.checked)
    
    @QtCore.Slot()
    def __onSetName(self):
        if not self.__editedEntity.manager:
            raise Exception("Document no available on node, cannot be edited")
        
        self.__editedEntity.manager.setNameSlot(self, self.ui.nameInput.text)

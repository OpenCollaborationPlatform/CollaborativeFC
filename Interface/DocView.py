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
from Interface.AsyncSlotWidget import StateMachineProcessWidget
from Manager import Entity

class DocView(QtWidgets.QWidget):
    
    edit = QtCore.Signal(str)
    
    def __init__(self, manager, parent = None):
        
        QtWidgets.QWidget.__init__(self, parent)
        
        self.__manager = manager
        self.__widgets = {}
        
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addStretch(1)
        layout.setSpacing(15)
        self.setLayout(layout)
        
        self.__manager.documentAdded.connect(self.__onDocumentAdded)
        self.__manager.documentRemoved.connect(self.__onDocumentRemoved)

    @QtCore.Slot(str)
    def __onEdit(self, uuid):
        self.edit.emit(uuid)

    @QtCore.Slot(str)
    def __onDocumentAdded(self, uuid):
        widget = DocWidget(self.__manager.getEntity("uuid", uuid), self)
        self.__widgets[uuid] = widget
        self.layout().insertWidget(0, widget)
        widget.edit.connect(self.__onEdit)
     
    @QtCore.Slot(str)
    def __onDocumentRemoved(self, uuid):
        
        if not uuid in self.__widgets:
            return 
        
        widget = self.__widgets[uuid]
        widget.close()
        widget.edit.disconnect(self.__onEdit)
        widget.setVisible(False)
        self.layout().removeWidget(widget)
        widget.deleteLater()
     

class DocWidget(QtWidgets.QWidget, StateMachineProcessWidget):
    
    edit = QtCore.Signal(str)
    
    def __init__(self, entity, parent):
        
        StateMachineProcessWidget.__init__(self, parent)
        QtWidgets.QWidget.__init__(self, parent)
        
        self.__entity = entity
        self.__name = "document"
        self.setStateMachine(entity)

        self.ui = FreeCADGui.PySideUic.loadUi(":/Collaboration/Ui/Document.ui")
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.ui)
        self.setLayout(layout)
        
        # Set the correct sizes dependent on system setting
        fontSize = 1.2*self.ui.nameLabel.font().pointSize()
        largeFont = self.ui.nameLabel.font()
        largeFont.setPointSize(fontSize)
        self.ui.nameLabel.setFont(largeFont)
        largeSize = QtGui.QFontMetrics(largeFont).ascent()
        self.ui.statusIndicator.setMaximumSize(largeSize, largeSize)
                
        self.ui.openButton.clicked.connect(lambda: self.__entity.processEvent(Entity.Events.open))
        self.ui.closeButton.clicked.connect(lambda: self.__entity.processEvent(Entity.Events.close))
        #self.ui.editButton.clicked.connect(lambda: self.edit.emit(self.__uuid))
               
        
        # setup the ui
        # ############
        
        self.ui.onlinestatus.hide()
        self.__entity.state(Entity.States.Local).setAttributeValue(self.ui.statusLabel, "text", "Local document", reset = True)
        self.__entity.state(Entity.States.Node).setAttributeValue(self.ui.statusLabel, "text", "Loading...", reset = True)
        self.__entity.state(Entity.States.Node.Status.Invited).setAttributeValue(self.ui.statusLabel, "text", "Invited to join", reset = True)
        self.__entity.state(Entity.States.Node.Status.Invited).setAttributeValue(self.ui.closeButton, "enabled", False, reset=True)
        self.__entity.state(Entity.States.Node.Status.Online).setAttributeValue(self.ui.onlinestatus, "visible", True, reset = True)
        self.__entity.state(Entity.States.Node.Status.Online).setAttributeValue(self.ui.statusLabel, "visible", False, reset = True)
        self.__entity.state(Entity.States.Node.Status.Online).setAttributeValue(self.ui.statusIndicator, "pixmap", QtGui.QPixmap(":/Collaboration/Icons/indicator_on.svg"), reset=True)
        self.__entity.state(Entity.States.Node.Status.Online.Edit).setAttributeValue(self.ui.openButton, "enabled", False, reset=True)     
                
        
        # manager data
        def _manager_setup():
            self.ui.memberLabel.setText(f"{entity.node_document_manager.memberCount}")
            self.ui.joinedLabel.setText(f"{entity.node_document_manager.joinedCount}")
            self.ui.majorityLabel.setText(f"{entity.node_document_manager.majority}")
            entity.node_document_manager.memberCountChanged.connect(lambda: self.ui.memberLabel.setText(f"{entity.node_document_manager.memberCount}"))
            entity.node_document_manager.joinedCountChanged.connect(lambda: self.ui.joinedLabel.setText(f"{entity.node_document_manager.joinedCount}"))
            entity.node_document_manager.majorityChanged.connect(lambda: self.ui.majorityLabel.setText(f"{entity.node_document_manager.majority}"))
        
        entity.state(Entity.States.Node.Status.Online).entered.connect(_manager_setup)




    def paintEvent(self, event):
        
        name = self.ui.nameLabel.fontMetrics().elidedText(self.__name, QtCore.Qt.ElideRight, self.ui.nameLabel.width())
        self.ui.nameLabel.setText(name)
        QtWidgets.QWidget.paintEvent(self, event)
        

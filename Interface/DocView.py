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

class DocView(QtWidgets.QWidget):
    
    edit = QtCore.Signal(str)
    
    def __init__(self, manager, parent = None):
        
        QtWidgets.QWidget.__init__(self, parent)
        
        self.__manager = manager
        self.__widgets = {}
        
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(2,2,2,2)
        layout.addStretch(1)
        layout.setSpacing(15)
        self.setLayout(layout)
        
        self.__manager.documentAdded.connect(self.__onDocumentAdded)
        self.__manager.documentRemoved.connect(self.__onDocumentRemoved)
        self.__manager.documentChanged.connect(self.__onDocumentChanged)

    @QtCore.Slot(str)
    def __onEdit(self, uuid):
        self.edit.emit(uuid)

    @QtCore.Slot(str)
    def __onDocumentAdded(self, uuid):
        widget = DocWidget(self.__manager, uuid, self)
        self.__widgets[uuid] = widget
        self.layout().insertWidget(0, widget)
        widget.edit.connect(self.__onEdit)
     
    @QtCore.Slot(str)
    def __onDocumentRemoved(self, uuid):
        
        if not uuid in self.__widgets:
            return 
        
        widget = self.__widgets[uuid]
        widget.edit.disconnect(self.__onEdit)
        widget.setVisible(False)
        self.layout().removeWidget(widget)
        widget.deleteLater()
     
    @QtCore.Slot(str)
    def __onDocumentChanged(self, uuid):
        
        if not uuid in self.__widgets:
            return 
        
        self.__widgets[uuid].update()


class DocWidget(QtWidgets.QWidget):
    
    edit = QtCore.Signal(str)
    
    def __init__(self, manager, uuid, parent):
        
        super().__init__(parent)
        
        self.__manager = manager
        self.__uuid = uuid

        self.ui = FreeCADGui.PySideUic.loadUi(":/Collaboration/Ui/Document.ui")
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.ui)
        self.setLayout(layout)
        
        self.ui.shareButton.clicked.connect(lambda: self.__manager.toggleCollaborateSlot(self.__uuid))
        self.ui.docButton.clicked.connect(lambda: self.__manager.toggleOpenSlot(self.__uuid))
        self.ui.editButton.clicked.connect(lambda: self.edit.emit(self.__uuid))
        
        self.update()
    
    def update(self):
        
        entity = self.__manager.getEntity("uuid", self.__uuid)
        self.ui.statusLabel.setText(entity.status.name)
        
        if entity.manager:
            self.ui.memberLabel.setText(f"{entity.manager.memberCount}")
            self.ui.joinedLabel.setText(f"{entity.manager.joinedCount}")
        else:
            self.ui.memberLabel.setText("-")
            self.ui.joinedLabel.setText("-")

        if entity.fcdoc:
            self.ui.nameLabel.setText(entity.fcdoc.Label)
        else:
            self.ui.nameLabel.setText(entity.id)
            
        if entity.status == Entity.Status.shared:
            self.ui.shareButton.setText("Stop")
            self.ui.docButton.setText("Close")
            self.ui.editButton.setEnabled(True)
            self.ui.statusIndicator.setPixmap(QtGui.QPixmap(":/Collaboration/Icons/indicator_on.svg"))
            
        elif entity.status == Entity.Status.local:
            self.ui.shareButton.setText("Share")
            self.ui.docButton.setText("Close")
            self.ui.editButton.setEnabled(False)
            self.ui.statusIndicator.setPixmap(QtGui.QPixmap(":/Collaboration/Icons/indicator_off.svg"))
        
        elif entity.status == Entity.Status.node:
            self.ui.shareButton.setText("Stop")
            self.ui.docButton.setText("Open")
            self.ui.editButton.setEnabled(True)
            self.ui.statusIndicator.setPixmap(QtGui.QPixmap(":/Collaboration/Icons/indicator_off.svg"))
            
    

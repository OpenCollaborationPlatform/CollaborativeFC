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

import FreeCADGui, asyncio
from PySide import QtCore, QtGui
from PySide.QtUiTools import QUiLoader

from Interface.DocumentModel import DocumentModel

class UIWidget(QtGui.QFrame):
    
    def __init__(self, dochandler, parent=None):
        super().__init__(parent)

        self.connection = None
        self.dochandler = dochandler
        self.model = DocumentModel(self.dochandler)

        # We are a popup, make sure we look like it
        self.setContentsMargins(1,1,1,1)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Popup)
        self.setGeometry(0, 0, 375, 500)   
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        self.setFrameShadow(QtGui.QFrame.Raised)
        
        loader = QUiLoader()
        self.ui = loader.load(":/Collaboration/Ui/Widget.ui", self)
        
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.ui)
        self.setLayout(layout)
    
        #connect all ui elements
        self.ui.DocumentList.activated.connect(self.onSelectionChanged)
        self.ui.Collaborate.toggled.connect(self.onShared)

    def setConnection(self, con):
        self.connection = con
        self.ui.DocumentList.setModel(self.model)
        self.model.layoutChanged.emit
        
    def removeConnection(self):
        self.connection = None
        self.model = None
        model = QtCore.QStringListModel()
        model.setStringList([])
        self.ui.DocumentList.setModel(model)

    def show(self):
        #try to find the correct position for the popup
        pos = QtGui.QCursor.pos()
        widget = QtGui.QApplication.widgetAt(pos)
        point = widget.rect().bottomLeft()
        global_point = widget.mapToGlobal(point)
        self.move(global_point)            
        super().show()
        
    @QtCore.Slot(bool)
    def onShared(self, collaborate):
        
        if not self.connection:
            return
        
        indexs = self.ui.DocumentList.selectedIndexes()
        if len(indexs) is 0:
            return
        
        idx = indexs[0].row()
        docmap = self.dochandler.documents[idx]
        
        shared = docmap['status'] == "shared"
        if shared and collaborate:
            #we are done.. event thougth this should not have happend
            return
        
        if shared and not collaborate:
            asyncio.ensure_future(self.dochandler.asyncStopCollaborateOnDoc(docmap))
            return
            
        #we need to collaborate!
        asyncio.ensure_future(self.dochandler.asyncCollaborateOnDoc(docmap))
            
        
        
    @QtCore.Slot(int)    
    def onSelectionChanged(self, index):
        
        if not self.connection:
            return
        
        #change the doc info side to the selected doc!
        docmap = self.dochandler.documents[index.row()]
        
        shared = docmap['status'] == "shared"
        self.ui.Collaborate.setChecked(shared)
        
        #if shared:
        #    pass            
        #else:
        #    self.ui.UserList.model.setStringList( QStringList{} )
        
            


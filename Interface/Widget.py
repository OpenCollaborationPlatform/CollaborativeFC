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
from PySide import QtCore, QtGui
from PySide2.QtQuick import QQuickView

from Interface.DocumentModel import DocumentModel
from Documents.Manager import Entity

class UIWidget(QQuickView):
    
    def __init__(self, manager, connection, parent=None):
        super().__init__(parent)
        
        print("setup")

        self.__connection = connection
        self.__manager = manager
        self.__model = DocumentModel(self.__manager)

        # We are a popup, make sure we look like it
        self.setFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Popup | QtCore.Qt.CustomizeWindowHint)
        self.setGeometry(0, 0, 500, 700)   
        
        #setup Qml
        self.setResizeMode(QQuickView.SizeRootObjectToView)
        self.engine().rootContext().setContextProperty("connection", connection)
        self.engine().addImportPath("qrc:/Collaboration/Ui")
        self.setSource(QtCore.QUrl("qrc:/Collaboration/Ui/Main.qml"))
        
        #event used to hide the window when we get inactive
        self.activeChanged.connect(self.activeSlot)


    def activeSlot(self):
        if not self.isActive():
            self.hide()


    def show(self):
        #try to find the correct position for the popup
        pos = QtGui.QCursor.pos()
        widget = QtGui.QApplication.widgetAt(pos)
        point = widget.rect().bottomLeft()
        global_point = widget.mapToGlobal(point)
        self.setPosition(global_point)
        super().show()
        self.requestActivate()
        
    @QtCore.Slot(bool)
    def onShared(self, collaborate):
        
        if not self.__connection:
            return
        
        indexs = self.ui.DocumentList.selectedIndexes()
        if len(indexs) == 0:
            return
        
        idx = indexs[0].row()
        entity = self.__manager.getEntities()[idx]
        
        shared = entity.status == Entity.Status.shared
        if shared and collaborate:
            #we are done.. event thougth this should not have happend
            return
        
        if shared and not collaborate:
            asyncio.ensure_future(self.__manager.stopCollaborate(entity))
            return

        #we need to collaborate!
        asyncio.ensure_future(self.__manager.collaborate(entity))
            
        
        
    @QtCore.Slot(int)    
    def onSelectionChanged(self, index):
        
        if not self.__connection:
            return
        
        #change the entity info side to the selected doc!
        entity = self.__manager.getEntities()[index.row()]
        
        shared = entity.status == Entity.Status.shared
        self.ui.Collaborate.setChecked(shared)
        
        #if shared:
        #    pass            
        #else:
        #    self.ui.UserList.model.setStringList( QStringList{} )
        
            


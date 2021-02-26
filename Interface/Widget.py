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
from PySide2 import QtQml
from PySide2.QtQuick import QQuickView
from qasync import asyncClose


class UIWidget(QQuickView):
    
    def __init__(self, manager, connection):
        
        super().__init__()
        
        self.__connection = connection
        self.__manager = manager

        # We are a popup, make sure we look like it
        self.setFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Popup | QtCore.Qt.CustomizeWindowHint)
        self.setGeometry(0, 0, 500, 700)   
        
        #setup Qml
        self.setResizeMode(QQuickView.SizeRootObjectToView)
        self.rootContext().setContextProperty("connection", connection)
        self.rootContext().setContextProperty("ocpDocuments", manager)
        self.engine().addImportPath("qrc:/Collaboration/Ui")
        self.setSource(QtCore.QUrl("qrc:/Collaboration/Ui/Main.qml"))
        
        #event used to hide the window when we get inactive
        self.activeChanged.connect(self.activeSlot)        
        QtCore.QCoreApplication.instance().aboutToQuit.connect(self.exit)
        
        
    def show(self):       
        #try to find the correct position for the popup
        pos = QtGui.QCursor.pos()
        widget = QtGui.QApplication.widgetAt(pos)
        if widget:
            point = widget.rect().bottomLeft()
            global_point = widget.mapToGlobal(point)
            self.setPosition(global_point)
            
        super().show()
        self.requestActivate()
        
        
    @QtCore.Slot()
    def exit(self):
        self.deleteLater()
        

    @QtCore.Slot()
    def activeSlot(self):
        if not self.isActive():
            self.hide()
        


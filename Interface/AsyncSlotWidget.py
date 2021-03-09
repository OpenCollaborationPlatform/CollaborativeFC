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

import FreeCADGui, Helper
from PySide2 import QtWidgets, QtCore, QtGui

class BusyIndicator(QtWidgets.QWidget):
    
    def __init__(self, parent=None):
        
        QtWidgets.QWidget.__init__(self, parent)
        
        if parent:
            size = min(parent.height()/2, parent.width()/2, 50)
            self.setGeometry((parent.width()-size)/2, 
                             (parent.height()-size)/2,
                             size, size)
        else:
            size = 50
            self.setGeometry(0, 0, size, size)
        
        self.pixmap = QtGui.QPixmap("/home/stefan/Projects/Collaboration/Resources/Icons/busy.svg")
        self.pixmap = self.pixmap.scaled(size, size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.angle = 0
        
        self.animation = QtCore.QVariantAnimation()
        self.animation.setLoopCount(-1)
        self.animation.setDuration(500)
        self.animation.setStartValue(0)
        self.animation.setEndValue(180)
        self.animation.valueChanged.connect(self.__rotate)
        self.animation.start()
        
    def stop(self):
        self.animation.stop()
        self.hide()
        self.deleteLater()
        
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.translate( 0.5 * self.pixmap.width(), 0.5 * self.pixmap.height() );
        painter.rotate( -1*self.angle );
        painter.translate( -0.5 * self.pixmap.width(), -0.5 * self.pixmap.height() );
        painter.drawPixmap(self.rect(), self.pixmap)
                
    @QtCore.Slot(int)
    def __rotate(self, value):        
        self.angle = value
        self.update()
 
class ErrorBox(QtWidgets.QWidget):
    
    def __init__(self, error, message, parent=None):
        
        QtWidgets.QWidget.__init__(self, parent.parent())
        
        self.__parent = parent
        size = 150
        self.setGeometry((parent.width()-2*size)/2, (parent.height()-size)/2, 2*size, size)
        
        self.ui = FreeCADGui.PySideUic.loadUi(":/Collaboration/Ui/Error.ui")
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.ui)
        self.setLayout(layout)
        
        self.ui.errorLabel.setText(error)
        self.ui.msgLabel.setText(message)
        self.ui.okButton.clicked.connect(self.__onOk)
        
        self.__parent.setEnabled(False)
        
    @QtCore.Slot()
    def __onOk(self):
        self.hide()
        self.ui.okButton.clicked.disconnect(self.__onOk)
        self.ui.deleteLater()
        self.deleteLater()
        self.__parent.setEnabled(True)
        
        

class AsyncSlotWidget():
    # A base class to inherit from when AsyncSlotObjects are used and its
    # status shall be conveyed to the user
        
    def __init__(self, parent):
        
        self.__asyncObject = None
        self.__running = []
        self.__parent = parent
        
    def setAsyncObject(self, obj):
        
        if not issubclass(type(obj), Helper.AsyncSlotObject):
            raise Exception("AsyncSlotWidget requires a AsyncSlotObject to work")
        
        if self.__asyncObject:
            self.__asyncObject.onAsyncSlotStarted.disconnect(self.__onAsyncStart)
            self.__asyncObject.onAsyncSlotFinished.diconnect(self.__onAsyncStop)
            
            for run in self.__running:
                self.__onAsyncStop(run, "", "")
        
        self.__asyncObject = obj
        self.__asyncObject.onAsyncSlotStarted.connect(self.__onAsyncStart)
        self.__asyncObject.onAsyncSlotFinished.connect(self.__onAsyncStop)
        

    @QtCore.Slot(int)
    def __onAsyncStart(self, id):
        
        if not self.__running:        
            # start the indicator
            self.__parent.setEnabled(False)
            self.__progress = BusyIndicator(self.__parent)
            self.__progress.show()
            
        self.__running.append(id)
      
    @QtCore.Slot(int, str, str)
    def __onAsyncStop(self, id, err, msg):
        
        if not id in self.__running:
            return
        
        self.__running.remove(id)
        if not self.__running:
            self.__progress.stop()
            self.__parent.setEnabled(True)
            
        if err or msg:            
            err = ErrorBox(err, msg, self.__parent)
            err.show()
    

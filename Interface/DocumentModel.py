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

from PySide import QtCore, QtGui
from Documents.Manager import Entity

class DocumentModel(QtCore.QAbstractListModel):
    
    def __init__(self, manager):
        super().__init__()
        
        self.__manager = manager
        manager.addUpdateFunc(self.layoutChanged.emit)

    def data(self, index, role):
        
        if role == QtCore.Qt.DisplayRole:
            
            entity = self.__manager.getEntities()[index.row()]
            if entity.fcdoc != None:
                return entity.fcdoc.Name
            if entity.id != None:
                return entity.id
                        
            return "Unknown name"

        if role == QtCore.Qt.DecorationRole:
            entity = self.__manager.getEntities()[index.row()]
            if entity.status == Entity.Status.shared:
                return QtGui.QColor('green')
            if entity.status == Entity.Status.local:
                return QtGui.QColor('orange')
            if entity.status == Entity.Status.node:
                return QtGui.QColor('yellow')
            if entity.status == Entity.Status.invited:
                return QtGui.QColor('purple')
            
            return QtGui.QColor('black')

    def rowCount(self, index):
        return len(self.__manager.getEntities())

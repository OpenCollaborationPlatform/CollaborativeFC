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

class DocumentModel(QtCore.QAbstractListModel):
    
    def __init__(self, dochandler):
        super().__init__()
        
        self.dochandler = dochandler
        dochandler.addUpdateFunc(self.layoutChanged.emit)

    def data(self, index, role):
        
        if role == QtCore.Qt.DisplayRole:
            
            docmap = self.dochandler.document[index.row()]
            if docmap['fcdoc'] != None:
                return docmap['fcdoc'].Name
            if docmap['id'] != None:
                return docmap['id']
                        
            return "Unknown name"

        if role == QtCore.Qt.DecorationRole:
            docmap = self.dochandler.documents[index.row()]
            if docmap['status'] is 'shared':
                return QtGui.QColor('green')
            if docmap['status'] is 'local':
                return QtGui.QColor('orange')
            if docmap['status'] is 'node':
                return QtGui.QColor('yellow')
            if docmap['status'] is 'invited':
                return QtGui.QColor('purple')
            
            return QtGui.QColor('black')

    def rowCount(self, index):
        return len(self.dochandler.documents)

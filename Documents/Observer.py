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

from OnlineDocument import OnlineDocument
from Connection import connection
from PySide import QtGui


class DocumentObserver():
    __trackedDocs = dict()

    def slotCreatedDocument(self, doc):

        if connection.isConnected():
            msgBox = QtGui.QMessageBox()
            msgBox.setText("New Document created, shall it be tracked online?")
            msgBox.setInformativeText("This creates a history based document in your collaboration account?")
            msgBox.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            msgBox.setDefaultButton(QtGui.QMessageBox.Yes)
            ret = msgBox.exec_()

            if ret == QtGui.QMessageBox.Yes:
                self.__trackedDocs[doc.Uid] = OnlineDocument(doc)
                print "create document online"
                self.__trackedDocs[doc.Uid].create()

    def slotDeletedDocument(self, doc):
        print "well"

    def slotRelabelDocument(self, doc):
        print "well"

    def slotCreatedObject(self, obj):
        if obj.Document.Uid in self.__trackedDocs:
            self.__trackedDocs[obj.Document.Uid].newObject(obj)

    def slotDeletedObject(self, obj):
        if obj.Document.Uid in self.__trackedDocs:
            self.__trackedDocs[obj.Document.Uid].deletedObject(obj)

    def slotChangedObject(self, obj, prop):
        if obj.Document.Uid in self.__trackedDocs:
            self.__trackedDocs[obj.Document.Uid].changedObject(obj, prop)

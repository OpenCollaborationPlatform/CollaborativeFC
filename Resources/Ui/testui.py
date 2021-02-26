# This Python file uses the following encoding: utf-8

import os
import sys
from PySide2 import QtCore
from PySide2.QtQuick import QQuickView
from PySide2.QtGui import QGuiApplication

# Document models and data classes to mimic FreeCAD structure  for testing
# ************************************************************************


class Peers(QtCore.QAbstractListModel):
    # helper class to mimic types used in real application

    def __init__(self):
        QtCore.QAbstractListModel.__init__(self)

    def roleNames(self):
        # return the QML accessible entries
        return {0: QtCore.QByteArray(bytes("nodeid", 'utf-8')),
                1: QtCore.QByteArray(bytes("authorisation", 'utf-8')),
                2: QtCore.QByteArray(bytes("joined", 'utf-8'))}

    def data(self, index, role):
        # return the data for the given index and role
        if index.row():
            data = {0: "Qm1234567890", 1: "read/write", 2: True}
        else:
            data = {0: "Qm0987654321", 1: "read only", 2: True}

        return data[role]

    def rowCount(self, index):
        return 2


class Document(QtCore.QObject):
    def __init__(self, name):
        QtCore.QObject.__init__(self)
        self.__peers = Peers()
        self.__name = name

    def getPeers(self):
        return self.__peers

    def getName(self):
        return self.__name

    def getMemberCount(self):
        return 2

    def getJoinedCount(self):
        return 1

    nameChanged = QtCore.Signal()
    memberCountChanged = QtCore.Signal()
    joinedCountChanged = QtCore.Signal()

    name = QtCore.Property(str, getName, notify=nameChanged)
    peers = QtCore.Property(QtCore.QObject, getPeers, constant=True)
    memberCount = QtCore.Property(int, getMemberCount, notify=memberCountChanged)
    joinedCount = QtCore.Property(int, getJoinedCount, notify=joinedCountChanged)

    @QtCore.Slot(str)
    def setName(self, name):
        print(f"SetName with {name}")

    @QtCore.Slot(int)
    def removePeer(self, idx):
        print(f"Remove peer {idx}")

    @QtCore.Slot(int)
    def togglePeerRigths(self, idx):
        print(f"Toggle Peer Rigths {idx}")

    @QtCore.Slot(str, bool)
    def addPeer(self, id, edit):
        print(f"Add Peer {id}: {edit}")


class Manager(QtCore.QAbstractListModel):
    # helper class to mimic types used in real application

    def __init__(self):
        QtCore.QAbstractListModel.__init__(self)

    def roleNames(self):
        # return the QML accessible entries
        return {0: QtCore.QByteArray(bytes("status", 'utf-8')),
                1: QtCore.QByteArray(bytes("name", 'utf-8')),
                2: QtCore.QByteArray(bytes("isOpen", 'utf-8')),
                3: QtCore.QByteArray(bytes("document", 'utf-8'))}

    def data(self, index, role):
        # return the data for the given index and role
        if index.row():
            data = {0: "local", 1: "MyLocalDocument",
                    2: False, 3: Document("MyLocalDocument")}
        else:
            data = {0: "shared", 1: "MySharedDocument",
                    2: True, 3: Document("MySharedDocument")}

        return data[role]

    def rowCount(self, index):
        return 2

    @QtCore.Slot(int)
    def collaborateSlot(self, idx):
        print(f"Collaborate slot on index {idx}")

    @QtCore.Slot(int)
    def stopCollaborateSlot(self, idx):
        print(f"Stop collaborate slot on index {idx}")

    @QtCore.Slot(int)
    def openSlot(self, idx):
        print(f"Open slot on index {idx}")

    @QtCore.Slot(int)
    def closeSlot(self, idx):
        print(f"Close collaborate slot on index {idx}")


# Setup and run the  UI with all required FreeCAD data models
# ************************************************************************

if __name__ == '__main__':

    # Set up the application window
    app = QGuiApplication(sys.argv)
    QGuiApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    view = QQuickView()
    view.setResizeMode(QQuickView.SizeRootObjectToView)

    # Setup the data entities
    manager = Manager()
    view.rootContext().setContextProperty("ocpDocuments", manager)

    # Load the QML file
    qml_file = os.path.join(os.path.dirname(__file__), "Main.qml")
    view.setSource(QtCore.QUrl.fromLocalFile(os.path.abspath(qml_file)))

    # Show the window
    if view.status() == QQuickView.Error:
        sys.exit(-1)
    view.show()

    # execute and cleanup
    app.exec_()
    del view

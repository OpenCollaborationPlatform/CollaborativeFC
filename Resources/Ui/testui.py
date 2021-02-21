# This Python file uses the following encoding: utf-8

import os
import sys
from PySide2 import QtCore
from PySide2.QtQuick import QQuickView
from PySide2.QtGui import QGuiApplication


class Manager(QtCore.QAbstractListModel):
    # helper class to mimic types used in real application
    # for this simple test script

    def __init__(self):
        QtCore.QAbstractListModel.__init__(self)

    def roleNames(self):
        # return the QML accessible entries
        return {0: QtCore.QByteArray(bytes("status", 'utf-8')),
                1: QtCore.QByteArray(bytes("name", 'utf-8')),
                2: QtCore.QByteArray(bytes("members", 'utf-8')),
                3: QtCore.QByteArray(bytes("joined", 'utf-8')),
                4: QtCore.QByteArray(bytes("isOpen", 'utf-8'))}

    def data(self, index, role):
        # return the data for the given index and role
        data = {0: "local",
                1: "MyNamedDocument",
                2: 3,
                3: 2,
                4: False}

        return data[role]

    def rowCount(self, index):
        return 2

    @QtCore.Slot(int)
    def collaborateSlot(self, idx):
        print(f"Collaborate slot on index {idx}")

    @QtCore.Slot(int)
    def stopCollaborateSlot(self, idx):
        print(f"Stop collaborate slot on index {idx}")


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

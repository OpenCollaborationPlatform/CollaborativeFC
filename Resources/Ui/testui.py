# This Python file uses the following encoding: utf-8

import os
import sys
from PySide2 import QtCore
from PySide2.QtQuick import QQuickView
from PySide2.QtGui import QGuiApplication

if __name__ == '__main__':

    # Set up the application window
    app = QGuiApplication(sys.argv)
    QGuiApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    view = QQuickView()
    view.setResizeMode(QQuickView.SizeRootObjectToView)

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

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

import FreeCADGui, asyncio, os, importlib
from PySide2 import QtCore, QtGui, QtWidgets
from Utils import AsyncSlotObject, AsyncSlot

class _PipInstaller(QtCore.QObject, AsyncSlotObject):
    # Class to handle installation of packages via pip
    
    def __init__(self):

        AsyncSlotObject.__init__(self)
        QtCore.QObject.__init__(self)
        
        self.__process = None
        
        # models for visualisation
        self.requirementsModel = QtCore.QStringListModel()
        self.outputModel = QtCore.QStringListModel()
        
        # search the requirements.txt
        folder = os.path.dirname(os.path.dirname(__file__))
        self.__requirements = os.path.join(folder, "requirements.txt")
        with open(self.__requirements) as f:
            content = f.readlines()
            content = [line.strip() for line in content]
            self.requirementsModel.setStringList(content)
        
        
    @AsyncSlot()
    async def toggleSlot(self):        
        # install all requirements from requirements.txt
        
        if self.__process:
            self.__process.terminate()
            await self.__process.wait()
            self.__process = None
            
        else:
            cmd = f"pip install -r {self.__requirements}"
            self.__process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            
            #wait fetch all outputs and add it to the output model
            async def collector(process, model):
                while process.returncode == None:
                    try:
                        data = await asyncio.wait_for(process.stdout.readline(), timeout=1)
                    except asyncio.TimeoutError:
                        continue
                        
                    line = data.decode('ascii').rstrip()
                    if line == "":
                        await asyncio.sleep(0.1)
                        continue
                    
                    if model.insertRow(model.rowCount()):
                        index = model.index(model.rowCount() - 1, 0)
                        model.setData(index, line)
                    
            # runs till finished or process was canceled
            await collector(self.__process, self.outputModel)
            self.__process = None


class InstallView(QtWidgets.QWidget):
       
    def __init__(self, parent = None):
        
        QtWidgets.QWidget.__init__(self, parent)
        
        self.__installer = _PipInstaller()
        
        self.ui = FreeCADGui.PySideUic.loadUi(":/Collaboration/Ui/Installer.ui")
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.ui)
        self.setLayout(layout)
        
        self.ui.textView.setModel(self.__installer.requirementsModel)
        self.ui.button.clicked.connect(self.__installer.toggleSlot)
        
        self.__installer.onAsyncSlotStarted.connect(self.onStartSlot)
        self.__installer.onAsyncSlotFinished.connect(self.onStopSlot)
        
    @QtCore.Slot(int)
    def onStartSlot(self, id):
        self.ui.textView.setModel(self.__installer.outputModel)
        self.ui.button.setText("Cancel")
        
    @QtCore.Slot(int, str, str)
    def onStopSlot(self, id, err, msg):
        self.ui.textView.setModel(self.__installer.requirementsModel)
        self.ui.button.setText("Install")
        
        if not err and not msg:
            # globally import the infrastructure
            global Collaboration
            import Collaboration
            importlib.reload(Collaboration)


# ************************************************************************
# *   Copyright (c) Stefan Troeger (stefantroeger@gmx.net) 2016          *
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

import FreeCAD

class _CommandConnect:
    "the Collaboration command definition"
    def GetResources(self):
        from PySide import QtCore
        return {'Pixmap': ':/Collaboration/Icons/icon_small.svg',
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Collab_Connect","Connect to FreeCAD collaboration services"),
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("Collab_Connect","Establishes a connection to the FreeCAD collaboration server")}

    def IsActive(self):
        return True

    def Activated(self):
        from Interface import Browser
        Browser.browser.show()

if FreeCAD.GuiUp:
    import FreeCADGui
    FreeCADGui.addCommand('Connect',_CommandConnect())
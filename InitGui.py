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

__title__ = "FreeCAD Collaboration API"
__author__ = "Stefan Troeger"
__url__ = "http://www.freecadweb.org"


# handle basic logging
# *******************************************************
import logging, Qasync, sys
logging.basicConfig(level=logging.WARN, stream=sys.stdout, format="[%(levelname)8s] %(name)25s:   %(message)s")
logging.getLogger('Qasync').setLevel(logging.ERROR)
logging.getLogger('Qasync').setLevel(logging.ERROR)
logging.getLogger('asyncio').setLevel(logging.ERROR)
logging.getLogger('autobahn').setLevel(logging.ERROR)


# setup the qt based event loop for asyncio
# *******************************************************
import asyncio
from PySide2 import QtCore
__app = QtCore.QCoreApplication.instance()
__loop = Qasync.QEventLoop(__app, already_running=True)
asyncio.set_event_loop(__loop)


#import the collaboration infrastructure
#*******************************************************
import FreeCAD, Collaboration, Utils
import PartGui #needed for coin nodes


#setup the UI command
#*******************************************************
if FreeCAD.GuiUp:
    import FreeCADGui
    import Interface
    FreeCADGui.addCommand('Collaborate', Utils.CommandCollaboration(Interface.uiWidget))
    
# setup the toolbar
group = FreeCAD.ParamGet("User parameter:BaseApp/Workbench/Global/Toolbar")

# as the GUI for custom global toolbars always rename them to "Custom_X" we need to search if 
# a collaboration toolbar is already set up
alreadySetup = False
for i in range(1,1000):
    if group.HasGroup("Custom_" + str(i)):
        custom = group.GetGroup("Custom_" + str(i))
        if custom.GetBool("CollaborationAutoSetup", False):
            alreadySetup = True
        else:
            custom.RemBool("CollaborationAutoSetup")
    else:
        break

#if not already done add our global toolbar
if not alreadySetup:
    # add the toolbar and make it findable
    collab = group.GetGroup("Custom_" + str(i))
    collab.SetString("Name", "Collaboration Network")
    collab.SetBool("Active", True)
    collab.SetBool("CollaborationAutoSetup", True)
    
    # add the tools
    collab.SetString("Collaborate", "Command")

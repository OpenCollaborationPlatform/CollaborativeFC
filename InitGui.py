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


import FreeCADGui
import Commands
import os
from PySide import QtCore

#load resources
import Collaboration
path_collaboration = os.path.dirname(Collaboration.__file__)
path_resources = os.path.join( path_collaboration, 'Resources', 'resources.rcc')
resourcesLoaded = QtCore.QResource.registerResource(path_resources)

class CollaborationWorkbench ( Workbench ):
	"Collaboration workbench object"
	MenuText = "Collaboration"
	ToolTip = "Collaboration workbench"
	#Icon = FreeCAD.getResourceDir() + "Mod/Arch/Resources/icons/ArchWorkbench.svg"
	
	def Initialize(self):
            # load the module           
            self.collabtools = ["Collab_Connect"]
            
            def QT_TRANSLATE_NOOP(scope, text): return text
            self.appendToolbar(QT_TRANSLATE_NOOP("Workbench","Collaboration tools"),self.collabtools)
		
	def Activated(self):
            if hasattr(FreeCADGui,"collaborationToolBar"):
                FreeCADGui.collaborationToolBar.Activated()
            Msg("Collaboration workbench activated\n")
                
        def Deactivated(self):
            if hasattr(FreeCADGui,"collaborationToolBar"):
                FreeCADGui.collaborationToolBar.Deactivated()
            Msg("Collaboration workbench deactivated\n")
            
        def GetClassName(self):
            return "Gui::PythonWorkbench"

Gui.addWorkbench(CollaborationWorkbench())

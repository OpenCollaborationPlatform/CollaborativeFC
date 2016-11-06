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

__title__ = "FreeCAD Collaboration API"
__author__ = "Stefan Troeger"
__url__ = "http://www.freecadweb.org"

'''The Collaboration module provides functions to work on documents with others'''

import os
from PySide import QtCore

#needs to be done before anything access the icons in the resource
path_collaboration = os.path.dirname(__file__)
path_resources = os.path.join(path_collaboration, 'Resources', 'resources.rcc')
resourcesLoaded = QtCore.QResource.registerResource(path_resources)

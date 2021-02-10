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

import os, sys 

# make sure the vendor folder is used for dependencies
# *******************************************************
parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'Vendor')
sys.path.append(vendor_dir)


# setup all the collaboration infrastructure
# ******************************************
from PySide import QtCore
from Documents.Manager import Manager
import Documents.Observer as Observer
from Interface.Widget import UIWidget
from Connection import OCPConnection


#handle the resources required
#*******************************************************
QtCore.QResource.registerResource(os.path.join(os.path.dirname(__file__), 'Resources', 'resources.rcc'))


#The Collaboration module provides functions to work on documents with others
#for now use simple global variables!
manager     = Manager(os.path.dirname(__file__))
widget      = UIWidget(manager)
connection  = OCPConnection(manager, widget)

#initialize the global FreeCAD document observer
Observer.initialize(manager)

if os.getenv('OCP_TEST_RUN', "0") == "1":
    #connect to test server
    import Test
    tester = Test.Handler(connection, manager)

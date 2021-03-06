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


# make sure the vendor folder is used for dependencies
# *******************************************************
import sys, os
parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'Vendor')
sys.path.append(vendor_dir)


# handle basic logging first
# *******************************************************
import logging, qasync
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, format="[%(levelname)8s] %(name)25s:   %(message)s")
logging.getLogger('qasync').setLevel(logging.ERROR)


# setup the qt based event loop for asyncio
# *******************************************************
import asyncio, txaio
from PySide2 import QtCore
app = QtCore.QCoreApplication.instance()
loop = qasync.QEventLoop(app)
txaio.config.loop = loop #workaround as component.start(loop=) does not propagate the loop correctly
asyncio.set_event_loop(loop)       



# setup all the collaboration infrastructure
# ******************************************
from PySide import QtCore
from Manager.Manager import Manager
import Documents.Observer as Observer
from Interface.Widget import UIWidget
from OCP.Connection import OCPConnection


#handle the resources required
#******************************************************
from Resources import resources

#The Collaboration module provides functions to work on documents with others
#for now use simple global variables!
connection  = OCPConnection()
manager     = Manager(os.path.dirname(__file__), connection)
widget      = UIWidget(manager, connection)

#initialize the global FreeCAD document observer
Observer.initialize(manager)

if os.getenv('OCP_TEST_RUN', "0") == "1":
    #connect to test server
    import Test
    tester = Test.Handler(connection, manager)

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

# check if we have installed all required modules
# ******************************************************
try:
    import ocp
    import autobahn
    import msgpack
    import qasync
    import aiofiles
    __available = True
except Exception:
    # if we do not further initialize everything the installer stays visible in the UI
    __available = False


if __available:
    
    # txaio workaround
    # ******************************************
    import asyncio, txaio
    txaio.config.loop = asyncio.get_event_loop() #workaround as component.start(loop=) does not propagate the loop correctly


    # setup all the collaboration infrastructure
    # ******************************************
    import os
    from PySide import QtCore
    from Manager import Manager
    import Documents.Observer as Observer
    from OCP import OCPConnection


    #The Collaboration module provides functions to work on documents with others
    #for now use simple global variables!
    connection  = OCPConnection()
    manager     = Manager(os.path.dirname(__file__), connection)

    # bring the UI out of setup mode
    import Interface
    Interface.uiWidget.setup(manager, connection)

    #initialize the global FreeCAD document observer
    Observer.initialize(manager)

    if os.getenv('OCP_TEST_RUN', "0") == "1":
        #connect to test server
        import Test
        tester = Test.Handler(connection, manager)

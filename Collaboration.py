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
importfail = []
try:
    import ocp
except Exception:
    importfail.append("ocp")
    pass

try: 
    import autobahn
except Exception:
    importfail.append("autobahn[serialization]")
    pass

try: 
    import msgpack
except Exception:
    importfail.append("msgpack")
    pass

try:
    import aiofiles
except Exception:
    importfail.append("aiofiles")
    pass    

import Interface

if not importfail:
    
    import code, traceback, signal

    def debug(sig, frame):
        """Interrupt running process, and provide a python prompt for
        interactive debugging."""
        d={'_frame':frame}         # Allow access to frame object.
        d.update(frame.f_globals)  # Unless shadowed by global
        d.update(frame.f_locals)

        i = code.InteractiveConsole(d)
        message  = "Signal received : entering python shell.\nTraceback:\n"
        message += ''.join(traceback.format_stack(frame))
        i.interact(message)

    signal.signal(signal.SIGUSR1, debug)  # Register handler

        
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
    Interface.uiWidget.setup(manager, connection)

    #initialize the global FreeCAD document observer
    Observer.initialize(manager)
    
    # run the OCP framework!
    connection.start()

    if os.getenv('OCP_TEST_RUN', "0") == "1":
        #connect to test server
        import Test
        tester = Test.Handler(connection, manager)

else:
    Interface.uiWidget.setMissingPackages(importfail)

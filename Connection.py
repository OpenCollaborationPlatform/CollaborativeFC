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

import asyncio
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner
from asyncqt import QEventLoop
from PySide import QtCore

app = QtCore.QCoreApplication.instance()
loop = QEventLoop(app)
asyncio.set_event_loop(loop)

class Connection(ApplicationSession):

    async def onJoin(self, details):
        print("We have joined, yeahh!")

    def onDisconnect(self):
        print("We have disconnected")
    
    
runner = ApplicationRunner("ws://localhost:8000/ws", "ocp")
coro = runner.run(Connection, start_loop=False)
asyncio.get_event_loop().run_until_complete(coro)

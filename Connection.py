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

try:
    import asyncio
except ImportError:
    # Trollius >= 0.3 was renamed to asyncio
    import trollius as asyncio
    from trollius import From

import txaio
txaio.use_asyncio()

from autobahn.wamp import protocol
from autobahn.asyncio.websocket import WampWebSocketClientFactory
from autobahn.wamp.types import ComponentConfig
from autobahn.wamp.serializer import JsonSerializer
from autobahn.websocket.util import parse_url
from PySide import QtCore

import signal


class Connection():

    class Session(protocol.ApplicationSession):

        def onJoin(self, details):
            print("session joined")
            print(details)

            ui = self.config.extra['ui']
            ui.session = self
            ui.__onJoin()

            self.subscribe(ui.__onMessage, u'com.myapp.topic2')

        def onClose(self, wasClean):
            print("leave session")
            ui = self.config.extra['ui']
            ui.__onClose()

    def __init__(self):
        print "init"

        self.url = u"ws://localhost:9000/ws"
        self.realm = u"freecad"
        self.serializers = [JsonSerializer()]
        self.ssl = None

        self.__timer = QtCore.QTimer(None)
        self.__timer.timeout.connect(self.__onTimer)
        self.session = None

        # setup the connection stuff
        def create():
            cfg = ComponentConfig(self.realm, dict(ui=self))
            try:
                session = Connection.Session(cfg)
            except Exception:
                self.log.failure("App session could not be created! ")
                asyncio.get_event_loop().stop()
            else:
                return session

        isSecure, host, port, resource, path, params = parse_url(self.url)

        if self.ssl is None:
            self.ssl = isSecure
        else:
            if self.ssl and not isSecure:
                raise RuntimeError(
                    'ssl argument value passed to %s conflicts with the "ws:" '
                    'prefix of the url argument. Did you mean to use "wss:"?' %
                    self.__class__.__name__)
            ssl = self.ssl

        # 2) create a WAMP-over-WebSocket transport client factory
        self.factory = WampWebSocketClientFactory(create, self.url, self.serializers)
        self.loop = asyncio.get_event_loop()
        txaio.use_asyncio()
        txaio.config.loop = self.loop
        txaio.start_logging(level='info')

        try:
            self.loop.add_signal_handler(signal.SIGTERM, self.loop.stop)
        except NotImplementedError:
            # signals are not available on Windows
            pass

    def connect(self):

        if self.session:
            self.disconnect()

        isSecure, host, port, resource, path, params = parse_url(self.url)
        coro = self.loop.create_connection(self.factory, host, port, ssl=self.ssl)
        (self.transport, self.session) = self.loop.run_until_complete(coro)

        self.__timer.stop()
        self.__timer.setInterval(50)
        self.__timer.start()

    def disconnect(self):
        if self.session:
            self.session.disconnect()

    def isConnected(self):
        return self.session is not None

    def __onTimer(self):

        self.__timer.stop()
        # stop/run_forever compo ensures that the event queue is procesed once
        self.loop.stop()
        self.loop.run_forever()
        # go for the next timer event
        self.__timer.start()

    def __onJoin(self):
        print "YeAH YEAH YEAAAAAHHHH"

    def __onClose(self):
        self.__timer.stop()
        self.__timer.setInterval(500)
        self.__timer.start()
        self.session = None
        print "Ohh ohahahah wehhhhhh"

    def __onMessage(self, msg):
        print msg


# we provide a global connection object for everyone to use, as it is sensible to have
# a single connection only
connection = Connection()

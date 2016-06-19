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

from twisted.internet import reactor
from autobahn.twisted.wamp import ApplicationSession
from autobahn.twisted.websocket import WampWebSocketClientFactory
from twisted.internet.defer import inlineCallbacks
from autobahn.wamp.serializer import JsonSerializer
from autobahn.wamp.types import ComponentConfig
from autobahn.websocket.util import parse_url
from PySide import QtCore
import signal

import txaio
txaio.use_twisted()


class Connection():

    class Session(ApplicationSession):

        def onJoin(self, details):
            print("session joined")
            print(details)

            ui = self.config.extra['ui']
            assert isinstance(ui, Connection)
            ui.session = self
            ui.onJoin()

        def onClose(self, wasClean):
            print("leave session")
            ui = self.config.extra['ui']
            assert isinstance(ui, Connection)
            ui.onClose()

    def __init__(self):
        print "init"

        self.url = u"ws://localhost:9000/ws"
        self.realm = u"freecad"
        self.serializers = [JsonSerializer()]
        self.ssl = None
        self.proxy = None

        self.__timer = QtCore.QTimer(None)
        self.__timer.timeout.connect(self.__onTimer)
        self.session = None

        txaio.use_twisted()
        txaio.config.loop = reactor
        txaio.start_logging(level='info')

        self.__isSecure, self.__host, self.__port, resource, path, params = parse_url(self.url)

        # factory for use ApplicationSession
        extra = dict(ui=self)

        def create():
            cfg = ComponentConfig(realm=self.realm, extra=extra)
            try:
                session = Connection.Session(cfg)
            except Exception as e:
                print("Session could not be created")

            return session

        # create a WAMP-over-WebSocket transport client factory
        self.transport_factory = WampWebSocketClientFactory(create, url=self.url,
                                                            serializers=self.serializers,
                                                            proxy=self.proxy)
        # supress pointless log noise like
        self.transport_factory.noisy = False

        # build our errror collector to handle errors in the reactor
        class ErrorCollector(object):
            exception = None

            def __call__(self, failure):
                self.exception = failure.value
                reactor.stop()

        self.connect_error = ErrorCollector()

        # start with a unsecure connection
        if self.__isSecure:
            raise "Secure connections are not yet supported"

        reactor.startRunning(installSignalHandlers=0)

    def connect(self):

        if self.session:
            self.disconnect()

        from twisted.internet import reactor
        from twisted.internet.endpoints import TCP4ClientEndpoint
        client = TCP4ClientEndpoint(reactor, self.__host, self.__port)
        d = client.connect(self.transport_factory)
        d.addErrback(self.connect_error)

        self.__timer.stop()
        self.__timer.setInterval(50)
        self.__timer.start()

    def disconnect(self):
        if self.session:
            self.session.disconnect()
            # just in case we call disconnect from connect we should finish it before return
            reactor.runUntilCurrent()
            reactor.doIteration(0)

    def isConnected(self):
        return self.session is not None

    def __onTimer(self):

        self.__timer.stop()

        # handle all events
        reactor.runUntilCurrent()
        reactor.doIteration(0)

        # if we exited due to a connection error, raise that
        if self.connect_error.exception:
            raise self.connect_error.exception

        # go for the next timer event
        self.__timer.start()

    def onJoin(self):
        print "YeAH YEAH YEAAAAAHHHH"

    def onClose(self):
        self.__timer.stop()
        self.__timer.setInterval(500)
        self.__timer.start()
        self.session = None
        print "Ohh ohahahah wehhhhhh"


# we provide a global connection object for everyone to use, as it is sensible to have
# a single connection only
connection = Connection()

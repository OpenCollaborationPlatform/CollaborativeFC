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

import nacl.signing
import nacl.hash
import time
from interfaces import MessageProcessor, Multiplexer, ConnectionHandler
from log import Logger
from random import shuffle
from twisted.internet import task, reactor
from twisted.internet.task import LoopingCall
from txrudp.connection import HandlerFactory, Handler, State
from txrudp.crypto_connection import CryptoConnectionFactory
from txrudp.rudp import ConnectionMultiplexer
from zope.interface.verify import verifyObject
from zope.interface import implements


class FileHandlingProtocol(ConnectionMultiplexer):
    """
    A protocol extending the txrudp datagram protocol. This is the main protocol
    which gets passed into the twisted UDPServer. It handles the setup and tear down
    of all connections, parses messages coming off the wire and passes them off to
    the appropriate classes for processing.
    """
    implements(Multiplexer)

    def __init__(self, ip_address, nat_type):
        """
        Initialize the new protocol with the connection handler factory.

        Args:
                ip_address: a `tuple` of the (ip address, port) of ths node.
        """
        self.ip_address = ip_address
        self.nat_type = nat_type
        self.factory = self.ConnHandlerFactory(self.processors, nat_type, self.relay_node, self.ban_score)
        self.log = Logger(system=self)
        self.keep_alive_loop = LoopingCall(self.keep_alive)
        self.keep_alive_loop.start(30, now=False)
        ConnectionMultiplexer.__init__(self, CryptoConnectionFactory(self.factory), self.ip_address[0], False)

    class ConnHandler(Handler):
        implements(ConnectionHandler)

        def __init__(self, nat_type, *args, **kwargs):
            super(FileHandlingProtocol.ConnHandler, self).__init__(*args, **kwargs)
            self.log = Logger(system=self)
            self.connection = None
            self.addr = None
            self.on_connection_made()
            self.time_last_message = 0
            self.ping_interval = 30 if nat_type != FULL_CONE else 300

        def on_connection_made(self):
            if self.connection is None or self.connection.state == State.CONNECTING:
                return task.deferLater(reactor, .1, self.on_connection_made)
            if self.connection.state == State.CONNECTED:
                self.addr = str(self.connection.dest_addr[0]) + ":" + str(self.connection.dest_addr[1])
                self.log.info("connected to %s" % self.addr)

        def receive_message(self, datagram):
            try:
                self.log.info("Message received")
            except Exception:
                # If message isn't formatted property then ignore
                self.log.warning("received an invalid message from %s, ignoring" % self.addr)
                return False

        def handle_shutdown(self):
            try:
                self.connection.unregister()
            except Exception:
                pass

            if self.addr:
                self.log.info("connection with %s terminated" % self.addr)

        def keep_alive(self):
            """
            Let's check that this node has been active in the last 5 minutes. If not
            and if it's not in our routing table, we don't need to keep the connection
            open. Otherwise PING it to make sure the NAT doesn't drop the mapping.
            """
            t = time.time()
 
            #if t - self.time_last_message >= self.ping_interval:
            #    for processor in self.processors:
            #        if PING in processor and self.node is not None:
            #            processor.callPing(self.node)

 
    class ConnHandlerFactory(HandlerFactory):

        def __init__(self, nat_type):
            super(FileHandlingProtocol.ConnHandlerFactory, self).__init__()
            self.nat_type = nat_type

        def make_new_handler(self, *args, **kwargs):
            return FileHandlingProtocol.ConnHandler(self.nat_type)


    def keep_alive(self):
        for connection in self.values():
            if connection.state == State.CONNECTED:
                connection.handler.keep_alive()

    def send_message(self, datagram, address):
        """
        Sends a datagram over the wire to the given address. It will create a new rudp connection if one
        does not already exist for this peer.

        Args:
            datagram: the raw data to send over the wire
            address: a `tuple` of (ip address, port) of the recipient.
        """
        if address not in self:
            con = self.make_new_connection(self.ip_address, address, None)
        else:
            con = self[address]
 
        con.send_message(datagram)

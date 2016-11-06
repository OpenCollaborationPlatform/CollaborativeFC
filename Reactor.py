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

# qt4 reactor to drive twisted eventloop if available
#try:
    #import qt4reactor
    #qt4reactor.install()
#except:
#    pass

import sys
from PySide import QtCore
from twisted.internet import reactor

import txaio
txaio.use_twisted()

class ReactorDriver():

    def __init__(self):
        
        try:
            self.__ownLoop = ("qt4reactor" not in sys.modules)

            self.__timer = QtCore.QTimer(None)
            self.__timer.timeout.connect(self.__onTimer)

            txaio.use_twisted()
            txaio.config.loop = reactor
            txaio.start_logging(level='info')
            
            if self.__ownLoop:
                reactor.startRunning(installSignalHandlers=0)
            else:
                reactor.runReturn()
                
        except:
            print "excepion"

    def start(self):

        if self.__ownLoop:
            self.__timer.stop()
            self.__timer.setInterval(50)
            self.__timer.start()

    def stop(self):

        self.__timer.stop()
        self.__timer.setInterval(500)
        self.__timer.start()

    def __onTimer(self):

        assert(self.__ownLoop)
        self.__timer.stop()

        # handle all events and calls
        reactor.runUntilCurrent()
        reactor.doIteration(0)

        # go for the next timer event
        self.__timer.start()

# we provide a global connection object for everyone to use, as it is sensible to have
# a single connection only
driver = ReactorDriver()
driver.start()
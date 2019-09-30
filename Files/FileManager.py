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

from PortMapper import PortMapper
from Protocol import FileHandlingProtocol
from Utils import looping_retry


import stun
from log import Logger, FileLogObserver
from twisted.internet import reactor
from twisted.python import log, logfile

def startup():
    
    PORT = 9000
    
    # Define logging
    logFile = logfile.LogFile.fromFullPath(
        os.path.join(DATA_FOLDER, "debug.log")
        rotateLength=15000000,
        maxRotatedFiles=1)
    log.addObserver(FileLogObserver(logFile, level=LOGLEVEL).emit)
    log.addObserver(FileLogObserver(level=LOGLEVEL).emit)
    logger = Logger(system="OpenBazaard")

    # NAT traversal
    p = PortMapper()
    p.add_port_mapping(PORT, PORT, "UDP")
    logger.info("Finding NAT Type...")

    response = looping_retry(stun.get_ip_info, "0.0.0.0", PORT)
        
    logger.info("%s on %s:%s" % (response[0], response[1], response[2]))
    ip_address = response[1]
    port = response[2]

    if response[0] == "Full Cone":
        nat_type = FULL_CONE
    elif response[0] == "Restric NAT":
        nat_type = RESTRICTED
    else:
        nat_type = SYMMETRIC

    protocol = FileHandlingProtocol((ip_address, port), nat_type)
    looping_retry(reactor.listenUDP, port, protocol)
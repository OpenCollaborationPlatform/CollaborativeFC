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

from twisted.web.server import Site
from twisted.web.static import File
from twisted.internet import reactor, endpoints

class HttpServer(object):
    
    def __init__(self):
        import os
        path = os.path.dirname(os.path.abspath(__file__))
        self.resource = File(path)
        self.factory = Site(self.resource)
        self.endpoint = endpoints.TCP4ServerEndpoint(reactor, 8000)
        self.endpoint.listen(self.factory)

#provide singleton for global access        
server = HttpServer()

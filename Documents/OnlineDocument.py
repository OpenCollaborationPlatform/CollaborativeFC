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

from Connection import connection
from twisted.internet.defer import inlineCallbacks


class OnlineDocument():

    def __init__(self, doc):
        self.document = doc
        print "new online document created"
        
    def getUid(self):
        return self.document.Uid

    @inlineCallbacks
    def open(self):
        # this opens a remote document and loads the remote data into the given local document
        print("open")

    @inlineCallbacks
    def create(self):
        # this creates a new remote document from the local one
        try:
            data = dict(Uid=str(self.document.Uid))
            res = yield connection.session.call(u"fc.documents.create", data)
            print(res)
            res = yield connection.session.call(u"fc.documents.{0}.change".format(res), data)
            print(res)
        except Exception as e:
            print("call error: {0}".format(e))

    def newObject(self, obj):
        print("prop")
        print(type(prop))

    def deletedObject(self, obj):
        print("prop")
        print(type(prop))

    def changedObject(self, obj, prop):
        print("prop")
        print(type(prop))

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

class DocumentProvider():
    """
    This class adds a document to the collaboration infrastructure. It allows to make changes on
    that document remotely
    """
    
    def __init__(self, ):        
        # register out api on the router
        pass

    def ProvidedDocument(): 
        """ This class is initiated for every document we provide. Every document specific 
            action is handled here        
        """
        def __init__(self, doc):
            self.transactionOpen = False;
            self.onlineDoc = doc
            
        def openTransaction(self):
            if self.transactionOpen:
                return "Error: transaction in progress"
            
            return True;                
    
    @inlineCallbacks
    def setupDocument(self, doc):
        print("Online Document will be registered")
        print(doc)

        id_  = doc.getUid()
        pdoc = ProvidedDocument(doc)

        try:
            # synchronisation and content stuff
            session = connection.session
            yield session.register(pdoc.getContent, u'documents.{0}.getContent'.format(id_))
            
            # change management
            yield session.register(pdoc.openTransaction, u'documents.{0}.openTransaction'.format(id_))
            yield session.register(pdoc.openTransaction, u'documents.{0}.finishTransaction'.format(id_))
            yield session.register(pdoc.openTransaction, u'documents.{0}.newObject'.format(id_))
            yield session.register(pdoc.openTransaction, u'documents.{0}.deleteObject'.format(id_))
            
            print("registering succeeded!")
        except Exception as e:
            print("could not register procedure {0} in DocumentProvider".format(e))
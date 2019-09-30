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

from PySide import QtCore, QtGui, QtWebKit, QtNetwork
from PySide.QtCore import Qt, QObject, QUrl, Slot
from PySide.QtGui  import QFrame, QGridLayout, QSizeGrip
import FreeCAD, FreeCADGui

from Connection import connection

class BrowserDocumentObserver():
    
    def __init__(self, frame):
        self.frame = frame

    def slotCreatedDocument(self, doc):
        if not self.frame:
            raise Exception("No self.frame set for documentobserver call")
        
        self.frame.evaluateJavaScript(u'documents.emitOnCreated({0}, {1})'.format(doc.Label).format(doc.Uid));
        

    def slotDeletedDocument(self, doc):
        
        if not self.frame:
            raise Exception("No self.frame set for documentobserver call")
        
        self.frame.evaluateJavaScript(u'documents.emitOnDeleted({0}, {1})'.format(doc.Label).format(doc.Uid));

    def slotRelabelDocument(self, doc):
        
        if not self.frame:
            raise Exception("No self.frame set for documentobserver call")
        
        self.frame.evaluateJavaScript(u'documents.emitOnRelabeled({0}, {1})'.format(doc.Label).format(doc.Uid));

class Backend(QObject):
    
    def __init__(self, parent=None):
        super(Backend, self).__init__(parent)
      
    # User identification management
    # ******************************
    
    @Slot(unicode, unicode)
    def saveLoginData(self, token, profile):
        # store JWT and profile string to be accessible from python
        p = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Collaboration")
        p.SetString("Profile", profile.encode('utf-8'))
        p.SetString("JSONWebToken", token)
      
    @Slot()
    def clearLoginData(self):
        # clear all stored data for logout
        
        group = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Collaboration")
        group.SetString("JSONWebToken", "")
        group.SetString("Profile", "")
        
    @Slot(result=str)
    def getToken(self):
        # returned the stored JWT without any checks
        
        return FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Collaboration").GetString("JSONWebToken")
    
    @Slot(result=str)
    def getValidToken(self):
        # return the JWT if that the token has not expired
        
        token = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Collaboration").GetString("JSONWebToken");
        if(token):
            import jwt, time
            dec = jwt.decode(token, verify=False)
            if dec["exp"] < int(time.time()):
                self.clearLoginData()
                token = ""
            
        return token     
        
    @Slot(result=unicode)
    def getProfile(self):
        # returned the saved profile text
        
        profile = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Collaboration").GetString("Profile")
        return unicode(profile, 'utf-8')


    # Router Connection management
    # ****************************
    
    @Slot()
    def openConnection(self):
        # try to connect to the router
        connection.connect()
    
    @Slot()
    def closeConnection(self):
        # try to connect to the router
        connection.disconnect()
    
    
    # Document anagement
    # ****************************
    
    @Slot(result=unicode)
    def documentList(self):
        docs = FreeCAD.listDocuments();
        if not docs:
            return u'{}'
        
        result = dict();
        for name in docs:
            result[doc.Label] = doc.Uid;
            
        return json.dumps(result)
    
class BrowserWidget(QFrame):
    
    def __init__(self, parent=None):
        super(BrowserWidget, self).__init__(parent)
        QtWebKit.QWebSettings.globalSettings().setAttribute(QtWebKit.QWebSettings.DeveloperExtrasEnabled, True)
        self.initUI()
        
    def initUI(self):

        # We are a popup, make sure we look like it
        self.setContentsMargins(1,1,1,1)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setGeometry(0, 0, 375, 500)   
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        #setup the webview for the real UI
        hbox = QGridLayout()
        hbox.setContentsMargins(0,0,0,0)
        self.webView = QtWebKit.QWebView()
        self.webView.page().networkAccessManager().setCookieJar( QtNetwork.QNetworkCookieJar() )
        self.webView.page().mainFrame().javaScriptWindowObjectCleared.connect(self.addBackend)
        self.webView.loadFinished.connect(self.pageLoaded)
        self.observer = BrowserDocumentObserver(self.webView.page().mainFrame())
        hbox.addWidget(self.webView)
        self.setLayout(hbox)
        
        #resizable for more usser control
        sizeGrip = QSizeGrip(self);
        hbox.addWidget(sizeGrip, 0,0,1,1, Qt.AlignBottom | Qt.AlignRight)        
        
        #load the real UI
        self.loaded = False
        self.webView.load(QUrl("http://localhost:8000"))  
         
    def pageLoaded(self, ok):
        if not self.loaded:
            self.webView.load(QUrl("http://localhost:8000")) 
            self.loaded = True

    def addBackend(self):
        #install our javascript backend for js<->python communication
        self.webView.page().mainFrame().addToJavaScriptWindowObject('backend', Backend())

         
    def show(self):
        #try to find the correct position for the popup browser
        pos = QtGui.QCursor.pos()
        widget = QtGui.qApp.widgetAt(pos)
        point = widget.rect().bottomLeft()
        global_point = widget.mapToGlobal(point)
        self.move(global_point)            
        super(BrowserWidget, self).show()        
    
        
# provide a singleton for global access
browser = BrowserWidget(FreeCADGui.getMainWindow())
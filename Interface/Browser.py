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

from PySide import QtCore, QtGui, QtWebKit, QtNetwork
from PySide.QtCore import Qt, QObject, QUrl, Slot
from PySide.QtGui  import QFrame, QGridLayout, QSizeGrip
import FreeCAD

from Connection import connection

#class PersistantCookieJar(QtNetwork.QNetworkCookieJar()):
#    
#    def __init__(self):
#        super(PersistantCookieJar, self).__init()

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
        
    @Slot(result=str)
    def getProfile(self):
        # returned the saved profile text
        
        return FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Collaboration").GetString("Profile")


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
    
class BrowserWidget(QFrame):
    
    def __init__(self):
        super(BrowserWidget, self).__init__()
        QtWebKit.QWebSettings.globalSettings().setAttribute(QtWebKit.QWebSettings.DeveloperExtrasEnabled, True)
        self.initUI()
        
    def initUI(self):

        # We are a popup, make sure we look like it
        self.setContentsMargins(1,1,1,1)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setGeometry(0, 0, 300, 500)   
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        #setup the webview for the real UI
        hbox = QGridLayout()
        hbox.setContentsMargins(0,0,0,0)
        self.webView = QtWebKit.QWebView()
        self.webView.page().networkAccessManager().setCookieJar( QtNetwork.QNetworkCookieJar() )
        self.webView.loadFinished.connect(self.pageLoaded)
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
browser = BrowserWidget()
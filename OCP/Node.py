# ************************************************************************
# *   Copyright (c) Stefan Troeger (stefantroeger@gmx.net) 2021          *
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

import os, sys, logging, asyncio, collections, json
import aiofiles
import Helper
from qasync import asyncSlot
from PySide2 import QtCore

class LogReader(QtCore.QAbstractListModel):
    # Reads log updates from rotating log file and makes it accessible as Qt List Model
    
    RoleMessage = 1
    RoleLevel = 2
    RoleTime = 3
    RoleModule = 4
    RoleData = 5    
    
    def __init__(self, logpath):
        super().__init__()
        
        self.__path = logpath
        self.__fileNo = os.stat(logpath).st_ino
        self.__lines = collections.deque(maxlen=100)
        self.__shutdown = False
        self.__task = None
    
    def taskRun(self):
        self.__task = asyncio.ensure_future(self.follow())
        
    async def blockRun(self):
        await self.follow()
    
    async def close(self):
        
        self.__shutdown = True
        
        if self.__task:
            self.__task.cancel()
        
        if self.__file:
            await self.__file.close()

    async def follow(self):
        
        await asyncio.sleep(1)
        self.__file = await aiofiles.open(self.__path, "rb") # use rb to allow seek with offset from end
        await self.__file.seek(int(-10e3), 2) # only use last 10kB
        await self.__file.readline() # drop one line, as it is most likely truncated
        
        while True:
            
            if self.__shutdown:
                return
            
            newlines = []
            while True:
                try:
                    line = await self.__file.readline()
                    if not line:
                        break
                    
                    try:
                        newlines.append(json.loads(line))
                    except:
                        # not json,  parse the printed line
                        pass
                                   
                except Exception as e:
                    break
                        
            if newlines:
                # we do this here to not emit the signal on every new line. This is rather slow 
                # if we have a large log file
                self.layoutAboutToBeChanged.emit()
                self.__lines += newlines
                self.layoutChanged.emit()

            try:
                if self.__shutdown:
                    return
            
                #in case new file opened by rotating log provider
                if os.stat(self.__path).st_ino != self.__fileNo:
                    new = aiofiles.open(self.__path, "r")
                    await self.__file.close()
                    self.__file =new
                    self.__fileNo = os.stat(self.__path).st_ino
                    continue
                else:
                    await asyncio.sleep(2)
                
            except IOError:
                await asyncio.sleep(2)
                pass


    #implementation of ListModel
    #***************************
    
    def roleNames(self):
        #return the QML accessible entries
        
        return {LogReader.RoleLevel: QtCore.QByteArray(bytes("level", 'utf-8')),
                LogReader.RoleMessage: QtCore.QByteArray(bytes("message", 'utf-8')),
                LogReader.RoleTime: QtCore.QByteArray(bytes("time", 'utf-8')),
                LogReader.RoleModule: QtCore.QByteArray(bytes("module", 'utf-8')),
                LogReader.RoleData: QtCore.QByteArray(bytes("data", 'utf-8')),
                QtCore.Qt.DisplayRole: QtCore.QByteArray(bytes("display", 'utf-8'))}
    
    def data(self, index, role):
        #return the data for the given index and role
        
        #index = PySide2.QtCore.QModelIndex
        idx = index.row()
        if role == LogReader.RoleMessage:
            msg = self.__lines[idx]["@message"]
            return msg.rstrip()
        
        if role == LogReader.RoleLevel:
            return self.__lines[idx]["@level"]
        
        if role == LogReader.RoleTime:
            time = self.__lines[idx]["@timestamp"]
            return QtCore.QDateTime.fromString(time, QtCore.Qt.ISODateWithMs)
        
        if role == LogReader.RoleModule:
            entry  =  self.__lines[idx]
            if "@module" in entry:
                return entry["@module"]
            return ""
        
        if role == LogReader.RoleData:
            #return all entries without an @
            entry  =  self.__lines[idx]
            keys = [e for e in entry.keys() if not "@" in e]
            result = {}
            for key in keys:
                result[key] = entry[key]
            return result
        
        if role == QtCore.Qt.DisplayRole:
            msg = self.data(index, LogReader.RoleMessage)
            lvl = self.data(index, LogReader.RoleLevel)
            time = self.data(index, LogReader.RoleTime)
            mod = self.data(index, LogReader.RoleModule)
            
            return f"{time.time().toString()} [{lvl}] {mod}: {msg}"
            
            

    def rowCount(self, index):
        return len(self.__lines)

    

#Helper class to call the running node via CLI
class Node(QtCore.QObject, Helper.AsyncSlotObject):
    
    def __init__(self, logger):
        
        QtCore.QObject.__init__(self)
        
        parent_dir = os.path.abspath(os.path.dirname(__file__))
    
        # get the path to use for the OCP node
        if sys.platform == "linux" or sys.platform == "linux2":
            self.__ocp = os.path.join(parent_dir, "OCPNodeLinux")
        elif sys.platform == "darwin":
            self.__ocp = os.path.join(parent_dir, "OCPNodeMac")
        elif sys.platform == "win32":
            self.__ocp = os.path.join(parent_dir, "OCPNodeWindows.exe")
            
        #self.__ocp = "/home/stefan/Projects/Go/CollaborationNode/CollaborationNode"
               
        #for testing we need to connect to a dedicated node       
        self.__test = False
        if os.getenv('OCP_TEST_RUN', "0") == "1":
            #we are in testing mode! check out the required node to connect to
            print("OCP Node: test mode detected")
            self.__test = True
            self.__conf = os.getenv("OCP_TEST_NODE_CONFIG", "none")
            
            if self.__conf == "none":
                raise Exception("Testmode is set, but no config file name provided")
        
        # important internal properties
        self.__logger    = logging.getLogger("OCPNode")
        self.__poll      = asyncio.ensure_future(self.__updateLoop())
        self.__logFile   = ""
        self.__logReader = None
        self.__logger    = logger
        
        # Qt property storage
        self.__running   = False
        self.__p2pPort   = 0
        self.__p2pUri    = "unknown"
        self.__apiPort   = 0
        self.__apiUri    = "unknown"
        
        asyncio.ensure_future(self.__asyncInit())
        asyncio.ensure_future(self.__startLogging())
     
    
    async def __asyncInit(self):
        await self.__update()           
        
    async def __startLogging(self):
        # open logfile if available
        dir = await self.__fetchConfig("directory", self.running)  
        self.__logFile   = os.path.join(dir, "Logs",  "ocp.log")
        if os.path.isfile(self.__logFile) and not self.__logReader:
                self.__logReader = LogReader(self.__logFile)
                self.logModelChanged.emit()
                await self.__logReader.blockRun()

    async def run(self):
        # handles the full setup process till a OCP node is running       
        await self.__initializeNode()
        await self.__start()
        
   
    async def shutdown(self):
        
        if self.__test:
            #in test mode we do not start our own node!
            print("Test mode: no own node, cannot shut down!")
            return
        
        process = await asyncio.create_subprocess_shell(self.__ocp + " stop")        
        await asyncio.wait_for(process.wait(), timeout = 10)
        await self.__update()

    
    async def __initializeNode(self):
        # initializes the OCP node. This ensures that all setup is done, however, does not start the node itself.
        # This init is required before start can be called

        if self.__test:
            #no initialisation needed in test run!
            ("Test mode: no initialization required")
            return
        
        #check if init is required
        process = await asyncio.create_subprocess_shell(self.__ocp, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await process.communicate()
        
        if not out:
            raise Exception(f"Unable to communicate with OCP node: {err}")
        
        if "OCP directory not configured" in out.decode():
        
            process = await asyncio.create_subprocess_shell(self.__ocp + ' init', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            out, err = await process.communicate()
        
            if not out:
                raise Exception("Unable to call OCP network")
        
            if err and err.decode() != "":
                raise Exception("Unable to initialize OCP node:", err.decode())
            
            if "Node directory was initialized" not in out.decode():
                raise Exception("Unable to initialize OCP node:", out.decode())


    async def __fetchConfig(self, conf, online):
        # returns the port the OCP node is listening on for WAMP connection
        
        args = self.__ocp + ' config '
        if online: 
            args += '-o '
            
        args += conf
        
        if self.__test:
            args += " --config " + self.__conf
                    
        process = await asyncio.create_subprocess_shell(args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await process.communicate()
               
        if err and err.decode() != "":
            raise Exception("Error while fetching config from OCP node:", err.decode())
       
        if not out:
            raise Exception("Unable to receive config from OCP node")
               
        if "No node is currently running" in out.decode():
            raise Exception("No node running: cannot read online config")

        return out.decode().rstrip()
        
        
    async def __start(self):
        # checks if a OCP node is running, and starts up one if not

        if not self.__test and not await self.__checkRunning():
            
            #start it
            await asyncio.create_subprocess_shell(self.__ocp + " start -d -e -j", 
                                                  stdout=asyncio.subprocess.PIPE, 
                                                  stderr=asyncio.subprocess.PIPE)
            
            #and wait till setup fully
            try:
                async def indicator():
                    while True:
                        await asyncio.sleep(0.5)
                        if await self.__checkRunning():
                            return                         
            
                await asyncio.wait_for(indicator(), timeout = 10)             
                
            except asyncio.TimeoutError as e:
                raise Exception("OCP node startup timed out") from None
            
        # setup logging if required
        if not self.__logReader and os.path.isfile(self.__logFile):
            #setup logging
            dir = await self.__fetchConfig("directory", True)
            self.__logFile   = os.path.join(dir, "Logs",  "ocp.log")
            if os.path.isfile(self.__logFile) and not self.__logReader:
                self.__logReader = LogReader(self.__logFile)
                self.__logReader.taskRun()
                self.logModelChanged.emit()

        # get the latest information and notify that we are running!
        await self.__update()                    
              
    
    async def __checkRunning(self):
        # returns if a OCP node is running
        
        args = self.__ocp
        if self.__test:
            args += " --config " + self.__conf
            
        process = await asyncio.create_subprocess_shell(args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await process.communicate()
        
        if not out:
            raise Exception("Unable to call OCP network node")
        
        if err and err.decode() != "":
            raise Exception("Unable to call OCP network node: ", err.decode())
        
        return not "No node is currently running" in out.decode()
    
    
    async def __update(self):
               
        # we need to check if the node is running at the beginning, to get correct config data
        running = await self.__checkRunning()
        
        p2pPort = await self.__fetchConfig("p2p.port", running)
        if self.__p2pPort != p2pPort:
            self.__p2pPort = p2pPort
            self.p2pPortChanged.emit()
            
        p2pUri  = await self.__fetchConfig("p2p.uri", running)
        if self.__p2pUri != p2pUri:
            self.__p2pUri = p2pUri
            self.p2pUriChanged.emit()
            
        apiPort = await self.__fetchConfig("api.port", running)
        if self.__apiPort != apiPort:
            self.__apiPort = apiPort
            self.apiPortChanged.emit()
            
        apiUri  = await self.__fetchConfig("api.uri", running)
        if self.__apiUri != apiUri:
            self.__apiUri = apiUri
            self.apiUriChanged.emit()
            
        # we need to set the running change at the end, in case anyone looks for a change and tries to 
        # access connection data once the node is running
        if running != self.__running:
            self.__running = running
            self.runningChanged.emit()
        
    
    async def __updateLoop(self):
        while True:
            try:
                await asyncio.sleep(5)
                await self.__update()
            except:
                pass
    

    # Qt Property/Signal API used from the UI
    # ********************************************************************************************
    
    #signals for property change (needed to have QML update on property change) and asyncslot finish
    runningChanged          = QtCore.Signal()
    p2pUriChanged           = QtCore.Signal()
    p2pPortChanged          = QtCore.Signal()
    apiUriChanged           = QtCore.Signal()
    apiPortChanged          = QtCore.Signal()
    logModelChanged         = QtCore.Signal()


    @QtCore.Property(bool, notify=runningChanged)
    def running(self):
        return self.__running
    
    @QtCore.Property(str, notify=p2pUriChanged)
    def p2pUri(self):
        return self.__p2pUri
        
    @QtCore.Property(str, notify=p2pPortChanged)
    def p2pPort(self):
        return str(self.__p2pPort)
    
    @QtCore.Property(str, notify=apiUriChanged)
    def apiUri(self):
        return self.__apiUri
        
    @QtCore.Property(str, notify=apiPortChanged)
    def apiPort(self):
        return str(self.__apiPort)
    
    @QtCore.Property(QtCore.QObject, notify=logModelChanged)
    def logModel(self):
        return self.__logReader

    @Helper.AsyncSlot()
    async def toggleRunningSlot(self):
        if self.running:
            await self.shutdown()
        else:
            await self.run()
    
    @Helper.AsyncSlot()
    async def updateDetails(self):        
        await self.__update()        

    @Helper.AsyncSlot(str, str)
    async def setP2PDetails(self, uri, port):
        
        if await self.__checkRunning():
            raise Exception("Cannot set connection details while running")
        
        args = f"{self.__ocp} config write p2p.port {port}"
        if self.__test:
            args += " --config " + self.__conf
         
        process = await asyncio.create_subprocess_shell(args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await process.wait()
        
        args = f"{self.__ocp} config write p2p.uri {uri}"
        if self.__test:
            args += " --config " + self.__conf
         
        process = await asyncio.create_subprocess_shell(args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await process.wait()

    
    @Helper.AsyncSlot(str, str)
    async def setAPIDetails(self, uri, port):
        
        if await self.__checkRunning():
            raise Exception("Cannot set connection details while running")
        
        args = f"{self.__ocp} config write api.port {port}"
        if self.__test:
            args += " --config " + self.__conf
         
        process = await asyncio.create_subprocess_shell(args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await process.wait()
        
        args = f"{self.__ocp} config write api.uri {uri}"
        if self.__test:
            args += " --config " + self.__conf
         
        process = await asyncio.create_subprocess_shell(args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await process.wait()
        

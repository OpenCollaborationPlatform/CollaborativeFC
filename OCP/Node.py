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

import os, sys, logging, asyncio

def getNodePath():
    pass
    
#Helper class to call the running node via CLI
class OCPNode():
    
    def __init__(self):
        
        parent_dir = os.path.abspath(os.path.dirname(__file__))
    
        # get the path to use for the OCP node
        if sys.platform == "linux" or sys.platform == "linux2":
            self.ocp = os.path.join(parent_dir, "OCPNodeLinux")
        elif sys.platform == "darwin":
            self.ocp = os.path.join(parent_dir, "OCPNodeMac")
        elif sys.platform == "win32":
            self.ocp = os.path.join(parent_dir, "OCPNodeWindows.exe")
               
        #for testing we need to connect to a dedicated node       
        self.test = False
        if os.getenv('OCP_TEST_RUN', "0") == "1":
            #we are in testing mode! check out the required node to connect to
            print("OCP test mode detected")
            self.test = True
            self.conf = os.getenv("OCP_TEST_NODE_CONFIG", "none")
            
            if self.conf == "none":
                raise Exception("Testmode is set, but no config file name provided")

        self.logger = logging.getLogger("OCPNode")


    async def init(self):
        # initializes the OCP node. This ensures that all setup is done, however, does not start the node itself.
        # This init is required before start can be called

        if self.test:
            #no initialisation needed in test run!
            ("Test mode: no initialization required")
            return
        
        #check if init is required
        process = await asyncio.create_subprocess_shell(self.ocp, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await process.communicate()
        
        if not out:
            raise Exception(f"Unable to communicate with OCP node: {err}")
        
        if "OCP directory not configured" in out.decode():
        
            process = await asyncio.create_subprocess_shell(self.ocp + ' init', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            out, err = await process.communicate()
        
            if not out:
                raise Exception("Unable to call OCP network")
        
            if err and err.decode() != "":
                raise Exception("Unable to initialize OCP node:", err.decode())
            
            if "Node directory was initialized" not in out.decode():
                raise Exception("Unable to initialize OCP node:", out.decode())


    async def port(self):
        # returns the port the OCP node is listening on for WAMP connection
        
        args = self.ocp + ' config -o connection.port'
        if self.test:
            args += " --config " + self.conf
         
        process = await asyncio.create_subprocess_shell(args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await process.communicate()
        
        if not out:
            raise Exception("Unable to call OCP network")
        
        if err and err.decode() != "":
            raise Exception("Unable to get Port from OCP node:", err.decode())
        
        if "No node is currently running" in out.decode():
            raise Exception("No node running: cannot read port")

        return out.decode().rstrip()
    
      
    async def uri(self):
        # returns the adress the ocp is listening on for WAMP connection
        
        args = self.ocp + ' config -o connection.uri'
        if self.test:
            args += " --config " + self.conf
            
        process = await asyncio.create_subprocess_shell(args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await process.communicate()
        
        if not out:
            raise Exception("Unable to call OCP network")
        
        if err and err.decode() != "":
            raise Exception("Unable to get URI from OCP node:", err.decode())
        
        if "No node is currently running" in out.decode():
            raise Exception("No node running: cannot read port")
                            
        return out.decode().rstrip()
    
       
    async def start(self):
        # checks if a OCP node is running, and starts up one if not
        
        if self.test:
            #in test mode we do not start our own node!
            print("Test mode: no own node startup!")
            return
        
        if not await self.running():
            
            #start it
            process = await asyncio.create_subprocess_shell(self.ocp + " start -d", 
                                                            stdout=asyncio.subprocess.PIPE, 
                                                            stderr=asyncio.subprocess.PIPE)
            
            #and wait till setup fully
            try:
                async def indicator():
                    while True:
                        await asyncio.sleep(0.5)
                        if await self.running():
                            return                         
            
                await asyncio.wait_for(indicator(), timeout = 10)
                
            except asyncio.TimeoutError as e:
                raise Exception("OCP node startup timed out") from None
            
            

    async def run(self):
        # handles the full setup process till a OCP node is running
        
        await self.init()
        await self.start()
        
        
    async def running(self):
        # returns if a OCP node is running
        
        process = await asyncio.create_subprocess_shell(self.ocp, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await process.communicate()
        
        if not out:
            raise Exception("Unable to call OCP network node")
        
        if err and err.decode() != "":
            raise Exception("Unable to call OCP network node: ", err.decode())
        
        return not "No node is currently running" in out.decode()
    
    
    async def shutdown(self):
        
        if self.test:
            #in test mode we do not start our own node!
            print("Test mode: no own node, cannot shut down!")
            return
        
        process = await asyncio.create_subprocess_shell(self.ocp + " stop", 
                                                            stdout=asyncio.subprocess.PIPE, 
                                                            stderr=asyncio.subprocess.PIPE)
        
        await asyncio.wait_for(process.wait(), timeout = 10)
    

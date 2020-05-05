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

import asyncio

class TaskContext():
    def __init__(self, tasks):
        self.tasks = tasks

    async def __aenter__(self):
        #wait till all setup tasks are finished
        if len(self.tasks) > 0:
            await asyncio.wait(self.tasks)

    async def __aexit__(self, exc_type, exc, tb):
        pass
    

class DocumentSyncRunner():
    
    __sender   = {}
    __receiver = {}
    
    @classmethod
    def getSenderRunner(cls, docId):
        if not docId in DocumentSyncRunner.__sender:
            DocumentSyncRunner.__sender[docId] = SyncRunner()
        
        return DocumentSyncRunner.__sender[docId]
    
    @classmethod
    def getReceiverRunner(cls, docId):
        if not docId in DocumentSyncRunner.__receiver:
            DocumentSyncRunner.__receiver[docId] = SyncRunner()
        
        return DocumentSyncRunner.__receiver[docId]
   

    
class SyncRunner():
   
    #runns all tasks syncronous
    def __init__(self, parentrunner = None):
        
        self.__tasks         = []
        self.__syncEvent     = asyncio.Event() 
        self.__finishEvent   = asyncio.Event()
        
        asyncio.ensure_future(self.__run())

   
    async def waitTillCloseout(self, timeout = 10):
        await asyncio.wait_for(self.__finishEvent.wait(), timeout)
         

    async def __run(self):
        
        while True:
            
            self.__finishEvent.clear()
            
            #we grap the currently available tasks
            tasks = self.__tasks.copy()
            self.__tasks.clear()
            self.__syncEvent.clear()
        
            #work the tasks syncronous
            for task in tasks:
                await task
                
            if len(self.__tasks) == 0:
                self.__finishEvent.set()
            
            #wait till new tasks are given
            await self.__syncEvent.wait()
        
           
    def runAsyncAsSetup(self, awaitable):
        
        self.__tasks.append(awaitable)
        self.__syncEvent.set()
        
        
    def runAsyncAsIntermediateSetup(self, awaitable):
        
        self.__tasks.append(awaitable)
        self.__syncEvent.set()
        
        
    def runAsync(self, awaitable):
        
        self.__tasks.append(awaitable)
        self.__syncEvent.set()
        
        
    def runAsyncAsCloseout(self, awaitable):
        
        self.__tasks.append(awaitable)
        self.__syncEvent.set()
    
 

class AsyncRunner():
    
    def __init__(self, parentrunner = None):
        self.setupTasks = []
        self.intermediateSetupTasks = []
        self.allTasks = []
        self.__finishEvent = None
        self.__parentTasks = []
        if parentrunner is not None:
            #get a reference of all parentrunner tasks
            self.__parentTasks = parentrunner.allTasks
    
    
    async def __run(self, awaitable, ctx):
            async with ctx:
                await awaitable   
               

    async def waitTillCloseout(self, timeout = 10):
        #returns when all tasks are finished. Note that it also wait for all task that are added 
        #during the wait time. Throws TimeOutError if it takes longer than the provided timeout
        
        if len(self.allTasks) == 0:
            return
        
        try:
            self.__finishEvent = asyncio.Event()
            await asyncio.wait_for(self.__finishEvent.wait(), timeout)
        finally:
            self.__finishEvent = None
        
         
    def __removeTask(self, task):
        while task in self.setupTasks:
            self.setupTasks.remove(task)
            
        while task in self.allTasks:
            self.allTasks.remove(task)
            
        while task in self.intermediateSetupTasks:
            self.intermediateSetupTasks.remove(task)
        
        if self.__finishEvent  != None and len(self.allTasks) == 0:
            self.__finishEvent.set()
        
           
    def runAsyncAsSetup(self, awaitable):
        #runs after the already known setup tasks
        #setup tasks run in the same order as provided by this function
        
        ctx = TaskContext(self.setupTasks.copy() + self.__parentTasks.copy())
        t = asyncio.ensure_future(self.__run(awaitable, ctx))
        t.add_done_callback(self.__removeTask)
        self.setupTasks.append(t)
        self.allTasks.append(t)
        
        
    def runAsyncAsIntermediateSetup(self, awaitable):
        #runs after setup, before all normal tasks, however, in contrast to setup 
        #these tasks run async, hence not in order (and parallel)
        
        ctx = TaskContext(self.setupTasks.copy() + self.__parentTasks.copy())
        t = asyncio.ensure_future(self.__run(awaitable, ctx))
        t.add_done_callback(self.__removeTask)
        self.intermediateSetupTasks.append(t)
        self.allTasks.append(t)
        
        
    def runAsync(self, awaitable):
        #runs the awaitable after all setup & runAsyncAsIntermediateSetup tasks are done.
        #Execution is async, hence not in order. This mode is to be used as default
        
        ctx = TaskContext(self.setupTasks.copy() + self.intermediateSetupTasks.copy() + self.__parentTasks.copy())
        t = asyncio.ensure_future(self.__run(awaitable, ctx))
        t.add_done_callback(self.__removeTask)
        self.allTasks.append(t)
        
        
    def runAsyncAsCloseout(self, awaitable):
        #runs the awaitable after all other known tasks are done
        #This is for action that need to ensure nothing comes afterwards
        
        ctx = TaskContext(self.allTasks.copy() + self.__parentTasks.copy())
        t = asyncio.ensure_future(self.__run(awaitable, ctx))
        t.add_done_callback(self.__removeTask)
        self.allTasks.append(t)

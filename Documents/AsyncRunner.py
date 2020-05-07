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
    

class DocumentOrderedRunner():
    
    __sender   = {}
    __receiver = {}
    
    @classmethod
    def getSenderRunner(cls, docId):
        if not docId in DocumentOrderedRunner.__sender:
            DocumentOrderedRunner.__sender[docId] = OrderedRunner()
        
        return DocumentOrderedRunner.__sender[docId]
    
    @classmethod
    def getReceiverRunner(cls, docId):
        if not docId in DocumentOrderedRunner.__receiver:
            DocumentOrderedRunner.__receiver[docId] = OrderedRunner()
        
        return DocumentOrderedRunner.__receiver[docId]
   

    
class __SyncRunner():
   
    #runns all tasks syncronous
    def __init__(self):
        
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
        
           
    def run(self, awaitable):
        
        self.__tasks.append(awaitable)
        self.__syncEvent.set()


class BatchedOrderedRunner():
    #batched execution of tasks
    #Normally run received a function object of an async function and its arguments.
    #The functions are than processed in order one by one (each one awaited). If functions can be batched
    #together, this can be done in the following way:
    #1. register batch handler. This is a async function which is called after all batchable functions are executed
    #2. run functions that have a batchhandler assigned. Those functions must not be awaitables, but default functions.
    
    #runns all tasks syncronous and batches tasks together if possible
    def __init__(self):
        
        self.__tasks         = []
        self.__syncEvent     = asyncio.Event() 
        self.__finishEvent   = asyncio.Event()
        self.__batchHandler  = {}
        
        asyncio.ensure_future(self.__run())


    def registerBatchHandler(self, fncName, batchFnc):        
        self.__batchHandler[fncName] = batchFnc;

   
    async def waitTillCloseout(self, timeout = 10):
        await asyncio.wait_for(self.__finishEvent.wait(), timeout)
         

    async def __run(self):
        
        #initially we have no work
        self.__finishEvent.set()
        
        while True:
            
            #wait till new tasks are given
            await self.__syncEvent.wait()
            
            #inform that we are working
            self.__finishEvent.clear()
            
            #we grap the currently available tasks
            tasks = self.__tasks.copy()
            self.__tasks.clear()
            self.__syncEvent.clear()
                   
            #work the tasks in order
            task = tasks.pop(0)
            while task is not None:
                
                #check if we can batch tasks
                if task[0].__name__ in self.__batchHandler:
                    
                    #execute all batchable functions of this type
                    batchtask = task
                    while batchtask and batchtask[0].__name__ == task[0].__name__:
                        
                        batchtask[0](*batchtask[1])
                        if tasks:
                            batchtask = tasks.pop(0)
                        else:
                            batchtask = None
                            break
                    
                    #rund the batch handler
                    await self.__batchHandler[task[0].__name__]()
                    
                    #reset the outer loop
                    task = batchtask
                    continue
                
                else:
                    #not batchable, normal operation
                    await task[0](*task[1])
                    if tasks:
                        task = tasks.pop(0)
                    else:
                        task = None
            
            if not self.__tasks:
                self.__finishEvent.set()
        
           
    def run(self, fnc, *args):
        
        self.__tasks.append((fnc, args))
        self.__syncEvent.set()
        

class OrderedRunner(BatchedOrderedRunner):
    
    async def __run(self):
        
        while True:
            
            self.__finishEvent.clear()
            
            #we grap the currently available tasks
            tasks = self.__tasks.copy()
            self.__tasks.clear()
            self.__syncEvent.clear()
        
            #work the tasks in order
            #work the tasks syncronous
            for task in tasks:
                
                #execute the batch handler after each single comman
                if task[0].__name__ in self.__batchHandler:
                    task[0](*task[1])
                    await self.__batchHandler[task[0].__name__]()
                    
                else:
                    await task
                

            if len(self.__tasks) == 0:
                self.__finishEvent.set()
            
            #wait till new tasks are given
            await self.__syncEvent.wait()

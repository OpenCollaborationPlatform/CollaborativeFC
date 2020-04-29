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
    
    
class AsyncRunner():
    
    def __init__(self):
        self.setupTasks = []
        self.intermediateSetupTasks = []
        self.allTasks = []
        self.__finishEvent = None
    
    
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
        
        ctx = TaskContext(self.setupTasks.copy())
        t = asyncio.ensure_future(self.__run(awaitable, ctx))
        t.add_done_callback(self.__removeTask)
        self.setupTasks.append(t)
        self.allTasks.append(t)
        
        
    def runAsyncAsIntermediateSetup(self, awaitable):
        
        ctx = TaskContext(self.setupTasks.copy())
        t = asyncio.ensure_future(self.__run(awaitable, ctx))
        t.add_done_callback(self.__removeTask)
        self.intermediateSetupTasks.append(t)
        self.allTasks.append(t)
        
        
    def runAsync(self, awaitable):
        
        ctx = TaskContext(self.setupTasks.copy() + self.intermediateSetupTasks.copy())
        t = asyncio.ensure_future(self.__run(awaitable, ctx))
        t.add_done_callback(self.__removeTask)
        self.allTasks.append(t)
        
        
    def runAsyncAsCloseout(self, awaitable):
        
        ctx = TaskContext(self.allTasks.copy())
        t = asyncio.ensure_future(self.__run(awaitable, ctx))
        t.add_done_callback(self.__removeTask)
        self.allTasks.append(t)

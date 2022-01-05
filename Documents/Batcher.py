
from Utils.Errorhandling import OCPErrorHandler

#Batcher are used together with Batched Asyncrunner. They scan over the existing tasks of the runner and 
#batch them together when possible. For example a single "changeProperty" task can be batched with others into
#a "multiChangeProperty" call, hence reducing the amount of OCP node calls required.

async def executeBatchersOnTasks(batchers, tasks):
    #Runs the batcher with the largest number of batchable tasks on the tasklist, and returns how many task
    #have been executed
    
    #start all batchers
    for batcher in batchers:
        batcher.startBatching()                        
        for task in tasks:
            if not batcher.batch(task):
                break
            
        batcher.doneBatching()
    
    #and now use the one with the most batched tasks
    num = [batcher.numBatched() for batcher in batchers]
    maxBatched = max(num)
                    
    if maxBatched > 0:
        
        #run the lucky batcher
        idx = num.index(maxBatched)                              
        await batchers[idx].execute()
                    
    return maxBatched


class EquallityBatcher(OCPErrorHandler):
    #Batches multiple tasks with the same name (as provided in constructor). When used the batcher executes all batched 
    #tasks and afterwards the handler. The principal is that the batched themself do not execute an expensive operation
    #but fill some kind of cache, and the handler afterwards uses this cache to start optimized execution on it
    
    def __init__(self, taskName, handler):
        
        super().__init__()
        
        self.__func = taskName
        self.__handler = handler
        self.__tasks = []
        
        self.Name = taskName
        
    def startBatching(self):
        self.__tasks = []
        
        
    def batch(self, task):
        
        if task.name() == self.__func:
            self.__tasks.append(task)
            return True
        
        return False
        
        
    def doneBatching(self):
        pass
        
        
    async def execute(self):
        
        #first execute all batched functions
        for task in self.__tasks:
            self._registerSubErrorhandler(task)
            await task.execute()
            self._unregisterSubErrorhandler(task)
        
        #not execute the batchhandler
        try:
            await self.__handler()
        except Exception as e:
            self._processException(e)
        
    
    def numBatched(self):
        return len(self.__tasks)
    
    def copy(self):
        return EquallityBatcher(self.__func, self.__handler)
    

class MultiBatcher(OCPErrorHandler):
    #Batches together task of multiple batchers nondependent of order. As long as the tasks are 
    #handable by any of the batchers this batcher swallows it. During execute all  batchers are
    #executed in provided order
    
    def __init__(self, batchers):
        
        super().__init__()

        self.__batchers = batchers
        self.Name = f"MultiBatcher"
    
    def startBatching(self):
        for batcher in self.__batchers:
            batcher.startBatching()

        
    def batch(self, task):
        
        for batcher in self.__batchers:
            if batcher.batch(task):
                return True
        
        return False
    
    
    def doneBatching(self):
        for batcher in self.__batchers:
            batcher.doneBatching()

        
    async def execute(self):
        
        for batcher in self.__batchers:
            self._registerSubErrorhandler(batcher)
            await batcher.execute()        
            self._unregisterSubErrorhandler(batcher)
    
    
    def numBatched(self):
        vals  = [b.numBatched() for b in self.__batchers]
        return sum(vals)
    


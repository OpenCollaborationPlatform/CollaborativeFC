#Syncers are class to achieve syncronisation with multiple async runners and an outside process.
#They are intended to be used with Asyncrunners "synchronize" methods, which adds their "execute" method
#to the current task list

import asyncio
    
class AcknowledgeSyncer():
    #Allows to wait till num synced runners have executed the syncer. 
    #waitAllAchnowledge blocks till this happens. The runners are not blocked, 
    #they directly execute their tasks after the syncer.
    
    def __init__(self, num):
        self.count = num
        self.event = asyncio.Event()
        
        if self.count == 0:
            self.event.set()

    async def execute(self):
        self.count -= 1
        if self.count <= 0:
            self.event.set()

    async def waitAllAchnowledge(self, timeout = 60):
        await asyncio.wait_for(self.event.wait(), timeout)
        

class WaitAcknowledgeSyncer():
    #Waits till all AcknowledgeSyncers have acknowledged
    
    def __init__(self, ackSyncer, timeout = 60):
        self.__syncer = ackSyncer
        self.__timeout = timeout
        
    async def execute(self):
        await self.__syncer.waitAllAchnowledge(self.__timeout)


class BlockSyncer():
    #Blocks all synced runners until the restart method is called
    
    def __init__(self):
        self.event = asyncio.Event()

    async def execute(self):
        await self.event.wait()

    def restart(self):
        self.event.set()
        
    async def asyncRestart(self):
        self.restart()
        

class RestartBlockSyncer():
    #restarts a given BlockSyncer when executed
    
    def __init__(self, blockSyncer):
        self.__block = blockSyncer
        
    async def execute(self):
        self.__block.restart()


class AcknowledgeBlockSyncer():
    #Allows to wait for num runners to execute and than blocks then till restart is called
       
    def __init__(self, num):
        self.Acknowledge = AcknowledgeSyncer(num)
        self.Block = BlockSyncer()
       
    async def execute(self):
        await self.Acknowledge.execute()
        await self.Block.execute()
            
    async def wait(self):
        await self.Acknowledge.waitAllAchnowledge()
        
    def restart(self):
        self.Block.restart()
     

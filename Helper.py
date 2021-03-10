
import asyncio, functools, traceback
from autobahn.wamp import ApplicationError
from PySide2 import QtCore

Key_Not_Available = "key_not_available"

def isOCPError(error, errclass=None, source=None, reason=None):
        
    if not isinstance(error, ApplicationError):
        return False

    uri = error.error
    if not uri.startswith("ocp.error"):
        return False
    
    comps = uri.split(".")
    if errclass and comps[2] != errclass:
        return False
        
    if source and comps[3] != source:
        return False
    
    if reason and comps[4] != reason:
        return False
    
    return True


class AsyncSlotObject():
    # base class to add async functionality to QtObject derived classes (required for UI handling)

    _id_counter = 0
    onAsyncSlotFinished = QtCore.Signal(int, str, str)
    onAsyncSlotStarted  = QtCore.Signal(int)

    async def _runner(self, id, fnc, args, kwargs):
        # helper function to run async func and afterwards call the finished signal
        try:
            self.onAsyncSlotStarted.emit(id)
            await fnc(*args, **kwargs)
            self.onAsyncSlotFinished.emit(id, None, None)
            
        except ApplicationError as e:
            if not isOCPError(e):
                traceback.print_exc()
                
            self.onAsyncSlotFinished.emit(id, e.error, ' '.join([str(a) for a in e.args]))
            
        except Exception as e:
            traceback.print_exc()
            self.onAsyncSlotFinished.emit(id, None, f"{e}")


def AsyncSlot(*slotArgs):
    """Make a Qt async slot run on asyncio loop and emits on start/finish.
        - Return value is a unique int ID which is also provided to the finish signal on emit
        - Must be defined on a AsyncSlotObject, otherwise fails
        """

    def decorator(fnc):
        
        @QtCore.Slot(*slotArgs)
        @functools.wraps(fnc)
        def wrapper(*args, **kwargs):
            
            self = args[0]
            AsyncSlotObject._id_counter += 1                    
            asyncio.ensure_future(self._runner(AsyncSlotObject._id_counter, fnc, args, kwargs))
            return AsyncSlotObject._id_counter

        return wrapper

    return decorator

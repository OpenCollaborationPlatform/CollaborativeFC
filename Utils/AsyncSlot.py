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

from Utils.Errorhandling import isOCPError
import asyncio, functools, traceback
from PySide2 import QtCore

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

        except Exception as e: 
            
            if isOCPError(e):
                self.onAsyncSlotFinished.emit(id, e.error, ' '.join([str(a) for a in e.args]))
            else:
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


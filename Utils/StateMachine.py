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

import inspect, asyncio
from enum import Enum, auto
from PySide2 import QtCore



#   State Machine
#
#   Decorators: 
#   * onEnter(statename):
#       * Automatically connects the decorated function with the entered signal of the state
#       * When using a async function it will be canceled when the state is left before it is finished (fnc receives CancelledError exception)
#   * onExit(statename):
#       * Automatically connects the decorated function with the exited signal of the state
#       * When a async function is decoredet it will also run on exit, but never be canceled by the state maching
#
#
#
#

class StateTypes(Enum):
        Normal = auto()
        Initial = auto()
        Final = auto()
        Process = auto()
        Group = auto()
        Parallel = auto()
        

# ***********************************************************************************************************************
#                                                   Setup implementation                                               
# ***********************************************************************************************************************


class _StateDefBase():
    # Base class for all state defining classes
    
    type = [StateTypes.Normal]
    name = "unknown"
    
    def __repr__(self):
        return f"<State {self.name}: {[t.name for t in self.type]}>"
    
    def __str__(self):
        return self.name
    
    @classmethod
    def _add_state_name_prefix(cls, prefix):
        
        for entry in cls.__dict__:
            
            item = cls.__dict__[entry]
            if isinstance(item, _StateDefBase):
                cls.__dict__[entry].name = prefix + "." + cls.__dict__[entry].name
                
            if inspect.isclass(item) and issubclass(item, _StateDefBase):
                cls.__dict__[entry].name = prefix + "." + cls.__dict__[entry].name
                cls.__dict__[entry]._add_state_name_prefix(prefix)


class _StateDefMeta(type):
    #class to add the name of the class variable as class member
    
    def __new__(cls, name, bases, dic):
               
        # we go through the dict and check if we should add the name to the subclasses
        result = super().__new__(cls, name, bases, dic)
        
        for entry in result.__dict__:
            
            item = result.__dict__[entry]
            if isinstance(item, _StateDefBase):
                result.__dict__[entry].name = entry
                
            if inspect.isclass(item) and issubclass(item, _StateDefBase):
                result.__dict__[entry].name = entry
                result.__dict__[entry]._add_state_name_prefix(entry)
        
        return result
    
    def __repr__(self):
        # returns the repr string for classes
        return f"<State {self.name}: {[t.name for t in self.type]}>"
    
    def __str__(self):
        return self.name

    def __iter__(self):
        result = []
        for entry in self.__dict__:
            
            item = self.__dict__[entry]
            if isinstance(item, _StateDefBase) or (inspect.isclass(item) and issubclass(item, _StateDefBase)):
                result.append(self.__dict__[entry])
        
        return iter(result)

class State(_StateDefBase):
    type = [StateTypes.Normal]

class InitialState(_StateDefBase):
    type = [StateTypes.Initial]

class FinalState(_StateDefBase):
    type = [StateTypes.Final]
    
class ProcessState(_StateDefBase):
    type = [StateTypes.Process]
    
class InitialProcessState(_StateDefBase):
    type = [StateTypes.Initial, StateTypes.Process]
    
class FinalProcessState(_StateDefBase):
    type = [StateTypes.Final, StateTypes.Process]
    
class States(_StateDefBase, metaclass=_StateDefMeta):
    type = [StateTypes.Group]
    
class GroupedStates(_StateDefBase, metaclass=_StateDefMeta):
    type = [StateTypes.Group]

class ParallelStates(_StateDefBase, metaclass=_StateDefMeta):
    type = [StateTypes.Parallel]


class _EventDefBase():
    # Base class for all state defining classes
    
    name = "unknown"
    
    def __repr__(self):
        return f"<Event {self.name}>"
    
    def __str__(self):
        return f"<Event {self.name}>"
    

class _EventDefMeta(type):
    #class to add the name of the class variable as class member
    
    def __new__(cls, name, bases, dic):
               
        # we go through the dict and check if we should add the name to the subclasses
        result = super().__new__(cls, name, bases, dic)
        
        for entry in result.__dict__:
            
            item = result.__dict__[entry]
            if isinstance(item, _EventDefBase):
                result.__dict__[entry].name = entry
        
        return result
    
    def __repr__(self):
        # returns the repr string for classes
        return f"<Event {self.name}>"
    
    def __str__(self):
        return f"<Event {self.name}>"
    
    def __iter__(self):
        result = []
        for entry in self.__dict__:
            
            item = self.__dict__[entry]
            if isinstance(item, _EventDefBase):
                result.append(self.__dict__[entry])
        
        return iter(result)


# Parent class for Event definition
class Events(_EventDefBase, metaclass = _EventDefMeta):
    pass


class TransitionEvent(_EventDefBase):
    
    def __init__(self, *args):
        self._transition_touples = args
        super().__init__()
        
    def __iter__(self):
        return iter(self._transition_touples)

class Event(TransitionEvent):
    
    def __init__(self):
        super().__init__()


# ***********************************************************************************************************************
#                                                   Logic implementation                                       
# ***********************************************************************************************************************


class _Transition(QtCore.QObject):
    # Rerepresenting a transition from a state to annother
    
    executed = QtCore.Signal()
    
    def __init__(self, target, condition = None):
        super().__init__()
        self._targets = [(target, condition)]
       
    def _addConditionalTarget(self, target, condition):
        # add annother target based on condition. Fails is existing target is without condition,
        # as this is always used anyway.
        if len(self._targets) >= 1 and not self._targets[0][1]:
            raise Exception("Cannot add conditional transition as there is a non conditional already")
        
        self._targets.append((target, condition))
       
    def _getTarget(self, statemachine):
        # we check which of the consitions are met
        for candidate in self._targets:
            if candidate[1]:
                if candidate[1](statemachine):
                    return candidate[0]
            else:
                return candidate[0]

        return None

  
class _State(QtCore.QObject):
    # State class representing a state in the state machine
    # Used internally for easy callback management, but is usable
    # by the user externally to connect to signals
    
    entered = QtCore.Signal()
    exited  = QtCore.Signal()
    
    def __init__(self, enum, parent):
        
        super().__init__()
               
        self.identifier = enum          # identifier from the state definition classes
        self._parent = parent           # _State group we are in
        self._children = set()          # Child _State
        self._initial = None            # _State that is used when transition to the group
        self._active = False            # True/False if active
        self._transitions  = {}         # transitions by event or signal
        self._asyncCallbacks = []       # Async functions to be called when entering the state (and aborted when exited)
        self.__tasks = []               # Collection of all running asyncio tasks
        self.__attributes = []          # All attributes we need to set when entering/leaving
        self.__event = asyncio.Event()  # Event to block till active
        
        if parent:
            parent._children.add(self)


    def _addTransition(self, to, *args, condition=None):
        
        result = None
        
        event = "__direct__"
        if args:
            event = args[0]
   
        if event not in self._transitions:
            result = _Transition(to, condition=condition)
            self._transitions[event] = result
            
        else:
            if not condition:
                raise Exception("Cannot add non-conditional transition, as event has already conditional one")
            
            result = self._transitions[event]
            result._addConditionalTarget(to, condition)
           
        return result
    
    
    def _getTransition(self, *arg) -> _Transition:
        # returns the state to transition to for given event, or None
        
        event = "__direct__"
        if arg:
            event = arg[0]
            
        if event in self._transitions:
            return self._transitions[event]
        
        return None


    def _activate(self, required):
        # process the state activation
        # - Sets itself as active
        # - Checks if the childs are correctly activated, and activates them if not by calling activate
        #   - Activates all child groups if self is type Parallel
        #   - Activates initial State if State is type Group and none of the childs is in required
        
        if not self._active:
            self._active = True
            self._onEntry()
        
        if StateTypes.Group in self.identifier.type:
            # we check if any child should be activated, if not, activate the initial one
            for child in self._children:
                if child in required:
                    child._activate(required)
                    return
                    
            # if we are here none of the childs was in required, we activate the default initial one
            assert self._initial, "Group has no initial state defined"
            self._initial._activate(required)
                
        if StateTypes.Parallel in self.identifier.type:
            # activate all children
            for child in self._children:
                child._activate(required)


    def _deactivate(self):
        # process the state deactivation
        # - Sets itself as deactive
        # - Deactivates all children
        
        if self._active:
            self._active = False
            self._onExit()

        for child in self._children:
            child._deactivate()


    @property
    def active(self) -> bool:
        return self._active
    
    def connectAsyncEntryCallback(self, asyncFcn):
        # Adds a async callback that gets called on state entry. When exiting the state before 
        # finishing the callback it will be abortet
        
        self._asyncCallbacks.append(asyncFcn)
        
    def setAttributeValue(self, obj: object, prop: str, value, reset=True):
        # Sets the property value when entering the state, and potentially sets it back to 
        # to the original value when leaving
        
        data = {"obj": obj, "attr": prop, "value": value, "reset": reset, "initial": None}
        self.__attributes.append(data)
    
    async def waitTillActive(self, timeout = 10):
        # async wait till the state gets active. Default timeout is 10s
        await asyncio.wait_for(self.__event.wait(), timeout=timeout)

    def _onEntry(self):
        
        # start all async callbacks
        self.__tasks = []
        for clb in self._asyncCallbacks:
            self.__tasks.append(asyncio.ensure_future(clb()))
        
        # procecss the enter callbacks
        self.entered.emit()
        
        # set the attributes (incl. QT properties)
        for data in self.__attributes:
            
            isqt = hasattr(data["obj"], "setProperty") and data["obj"].property(data["attr"]) != None
            
            if data["reset"]:
                if isqt:
                    data["initial"] = data["obj"].property(data["attr"])
                else:
                    data["initial"] = getattr(data["obj"], data["attr"])
            
            # check if qt proeprty           
            if isqt:
                data["obj"].setProperty(data["attr"], data["value"])
            else:        
                setattr(data["obj"], data["attr"], data["value"])

        self.__event.set()

    def _onExit(self):
        
        # check if there are unfinished tasks and cancel them
        if self.__tasks:
            for task in self.__tasks:
                if not task.done():
                    task.cancel()
        
        # processes all user callbacks on exit of state        
        self.exited.emit()
            
        # reset the attributes (incl. QT properties)
        for data in self.__attributes:
            if data["reset"]:
                
                isqt = hasattr(data["obj"], "setProperty") and data["obj"].property(data["attr"]) != None
                
                if isqt:
                    data["obj"].setProperty(data["attr"], data["initial"])
                else:        
                    setattr(data["obj"], data["attr"], data["initial"])
        
        self.__event.clear()
            

class StateMachine(QtCore.QObject):
    # class representing a state machine
    
    finished =          QtCore.Signal()    # Emitted if a FinalState is reached
    onProcessingEnter = QtCore.Signal()    # Any ProcessingState is entered
    onProcessingExit =  QtCore.Signal()    # Any ProcessingState is exited
    
    def __init__(self):
        
        subclassDir = dir(self) # get dir before we add our base class types to self to avoid doubling states and events
        super().__init__()
        
        self.__states = {}
        self.__events = None
        self.__finished = False
        self.__processing = False        # bool if we are currently processing an event
        self.__processingEvents = []     # Events that are emiited and need to be handled during an processing run
    
        # we search the states class to initialize!
        for entry in subclassDir:
            item = getattr(self, entry)
            if inspect.isclass(item) and issubclass(item, States):
                #lets build them all! 
                self._rootStates = self.__buildGroupStates(item, None)
                break
        
        # now events and callbacks. Not the same loop. as we need states initialized for event transitions
        for entry in subclassDir:
            item = getattr(self, entry)

            if inspect.isclass(item) and issubclass(item, Events):
                self.__events = item
                #lets build them all! 
                for event in item:
                    transitions = getattr(item, event.name)
                    for transition in transitions:
                        assert transition[0] in self.__states, "Transition start is not a valid state machine state"
                        assert transition[1] in self.__states, "Transition start is not a valid state machine state"
                        
                        self.__states[transition[0]]._addTransition(self.__states[transition[1]], event)

            
            elif hasattr(item, "statemachine_usecase"):
                if item.statemachine_usecase == "onEnter":
                    assert item.statemachine_data in self.__states, "onEnter callback state is invalid"
                    self.__states[item.statemachine_data].entered.connect(item)
                    
                elif item.statemachine_usecase == "onExit":
                    assert item.statemachine_data in self.__states, "onExit callback state is invalid"
                    self.__states[item.statemachine_data].exited.connect(item)
                elif item.statemachine_usecase == "onAsyncEnter":
                    assert item.statemachine_data in self.__states, "onAsyncEnter callback state is invalid"
                    self.__states[item.statemachine_data].connectAsyncEntryCallback(item)
                    
                elif item.statemachine_usecase == "transition":
                    assert len(item.statemachine_data) == 3, "wrong argument count for transition callback"
                    assert item.statemachine_data[0] in self.__states, "transition callback start state is invalid"
                    assert item.statemachine_data[1] in self.__states, "transition callback end state is invalid"

                    if item.statemachine_data[2]:
                        trans = self.addTransition(item.statemachine_data[0], item.statemachine_data[1], item.statemachine_data[2][0])
                    else:
                        trans = self.addTransition(item.statemachine_data[0], item.statemachine_data[1])
                    
                    trans.executed.connect(item)
                        
                elif item.statemachine_usecase == "onFinish":
                    self.finished.connect(item)
                    
                elif item.statemachine_usecase == "onProcessingEnter":
                    self.onProcessingEnter.connect(item)
                    
                elif item.statemachine_usecase == "onProcessingExit":
                    self.onProcessingExit.connect(item)
                    
    
        if not self.__states:
            raise Exception("No states defined")
        
        if not self.__events:
            raise Exception("No events defined")

        # check if the root is correctly setup (exactly one acticve state)
        active = [state for state in self._rootStates if state.active]
        if len(active) != 1:
            raise Exception(f"States require exactly 1 initial toplevel state, not {len(active)}")

    
    def __buildGroupStates(self, group, parent):
        # build all states from the group
        # returns the toplevel creates states (no substates)

        result = []        
        for state in group:
            
            stateObj = _State(state, parent)
            self.__states[state] = stateObj
            result.append(stateObj)
            
            #check if this is th einitial state and use it (or initial for the whole machine
            if StateTypes.Initial in state.type:
                if not parent:
                    stateObj._active = True
                else:
                    assert not parent._initial, "Only a single initial sate is allowed per group"
                    parent._initial = stateObj
            
            if StateTypes.Group in state.type or StateTypes.Parallel in state.type:
                self.__buildGroupStates(state, stateObj)
                
        return result
    
                      
    def processEvent(self, event):
        # Process an event and do the required transitions.   
        
        # difference to internal __processEvent is that it only allows normal events,
        # not signals.
        assert event in self.__events, "Not a valid event"
        self.__processEvent(event)
    
    
    def __processEvent(self, event):
        # Processes events and signals
    
        # This operation is complicated by the existence of parallel groups, and hence multiple 
        # parallel active states. A implementation Needs to correctly initialize or deactivate those
        # dependend on the transition state. To do this the following implementation is used:
        #
        # Consider that the state machine states form a tree. The tree nodes are either Groups or 
        # Paralells, which both handle activate or deactivate differently. The following algorithm 
        # is used to do the state transition
        # 1. Collect the start and end state for the transition
        # 2. Deactivate: 
        #   1. Compute common parent start and end state -> CP
        #   2. Compute highest parent group of start state below CP -> DS  (deactivate State)
        #   3. Call deactivate on DS, also recursivly deactivating all DS children
        # 3. Activate
        #   1. Set end state itself active
        #   2. Compute highest parent group of end state below CP -> AS (activate State)
        #   2. Set all states between end and AS active
        #   3. Call activate on AS, also recursivly activating all AS children
        #
        # For this to work it needs to be ensured that:
        #   1. Deactivate call on state does remove all active substates, recursively
        #   2. Activate call on state does check if childs are activated correctly, otherwise use
        #      initial states to correctly activate
        if self.__finished:
            return
        
        # prevent processing events ommited during the processing of annother event
        if self.__processing:
            self.__processingEvents.append(event)
            return
            
        self.__processing = True
        self.processEvents = []
        
        try:
            # from the current active states, see to which we are going to transition
            trans = self.__findTransition(self._rootStates, event)    
            while trans:
                
                start = trans[0]
                startPath = self.__getUpwardsPath(start)
                end = trans[1]._getTarget(self)
                endPath = self.__getUpwardsPath(end)
                
                # get the common parent, DS and AS states        
                cp = None
                for state in startPath:
                    if state in endPath:
                        cp = state
                        break
                    
                if cp:
                    ds_ = startPath[startPath.index(cp)-1]
                    as_ = endPath[endPath.index(cp)-1]
                else:
                    # no common parent means the relative toplevel group is the ds/as state
                    ds_ = startPath[-1]
                    as_ = endPath[-1]
                
                # finally deactivate  or activate the relevant states
                ds_._deactivate()   
                trans[1].executed.emit()
                as_._activate(endPath)
                
                # check if we left or entered a processing state
                if StateTypes.Process in start.identifier.type:
                    if not StateTypes.Process in end.identifier.type:
                        self.onProcessingExit.emit()
                
                elif StateTypes.Process in end.identifier.type:
                    self.onProcessingEnter.emit()
                
                # check if we reached a final state (a group or initial state cannot be final, hence it's
                # enough to check end state
                if StateTypes.Final in end.identifier.type:
                    self.__finished = True
                    self.finished.emit()
                
                # process all direct transitions
                trans = self.__findTransition(self._rootStates)
               
            # finalize all events that have been captured during the processing
            self.__processing = False
            # process all events emmited during this run. For that we need a local copie,
            # as the other runs may also emit new events that need collection
            events = self.processEvents.copy()
            for event in events:
                self.processEvent(event)

        except Exception as e:
            print("Statemachine event processing error: ", e)
        
        finally: 
            # just in case we errored out
            self.__processing = False
       
    
    def __findTransition(self, states, *args):
        # recursively searches the states for transitions with the given event
        # returns a tuple with (start, end) states
        
        for state in states:
            if state.active:
                trans = state._getTransition(*args)
                if trans and trans._getTarget(self):
                    return (state, trans)
                else:
                    states = self.__findTransition(state._children, *args)
                    if states:
                        return states
        
        return None
    
    def __getUpwardsPath(self, state):
        # Returns a list of all parent states for the given states, including itself
        
        result = []
        processed = state
        while processed:
            result.append(processed)
            processed = processed._parent
            
        return result


    @property
    def activeStates(self):
        
        result = []
        for state in self._rootStates:
            if state.active:
                result += self.__recursiveActiveStates(state)
        
        return [state.identifier for state in result]
    
    @property
    def hasFinished(self):
        return self.__finished
        
    def __recursiveActiveStates(self, state):
        
        result = [state]
        for sub in state._children:
            if sub.active:
                result += self.__recursiveActiveStates(sub)
        
        return result

    
    def addTransition(self, start, end, *args, condition=None) -> _Transition:
        # Adds a new transition between start and end states.
        # Additional arguments can be:
        # None:   Transition that is executed directly when state is entered
        # Event:  Transition that is executed when the event is processes
        # Signal: Transition that is executed when the signal is emitted
        # 
        # condition keyword: a function object returning a bool if the transition should be executed
        #                    (useful only if multiple conditional transitions are added, either for 
        #                     direct transitions or for a single event)
        #                    does not work for signal argument
        
        assert start in self.__states, "Transition start is not a valid state machine state"
        assert end in self.__states, "Transition end is not a valid state machine state"
          
        #check if args is an allowed transition
        if len(args) > 1:
            raise Exception("wrong amount of arguments")
        
        if len(args) == 1:
            if  not isinstance(args[0], QtCore.Signal) and \
                not args[0] in self.__events and \
                not args[0] is None:
                
                raise Exception("Argument must be None, Event or Signal")
            
            if isinstance(args[0], QtCore.Signal):
                sig = args[0]
                sig.connect(lambda: self.__processEvent(sig))
          
        # add transitions
        return self.__states[start]._addTransition(self.__states[end], *args, condition = condition)

    def setAttributeValue(self, state, obj, attr, value, reset = True):
        # Sets the attribute value when entering the state, and potentially sets it back
        # to the original value when leaving
        assert state in self.__states, "Not a valid state machine state"
    
        self.state(state).setAttributeValue(obj, attr, value, reset=reset)
    
    def state(self, state) -> _State:
        assert state in self.__states, "Invalid state identifier"

        return self.__states[state]
    
    def transition(self, start, end, *args) -> _Transition:
        assert start in self.__states, "Invalid state identifier"
        assert end in self.__states, "Invalid state identifier"
        assert start in self.__states, "State has no transition"            

        return self.__states[start]._getTransition(end, *args)



# ***********************************************************************************************************************
#                                                   Callback setups                                               
# ***********************************************************************************************************************


def onEnter(state):
    
    def wrapper(fnc):
        
        if asyncio.iscoroutinefunction(fnc):
            fnc.statemachine_usecase = "onAsyncEnter"
        else:
            fnc.statemachine_usecase = "onEnter"
            
        fnc.statemachine_data = state
        return fnc

    return wrapper

def onExit(state):
    
    def wrapper(fnc):
        
        result = fnc
        if asyncio.iscoroutinefunction(fnc):
            
            def asyncwrapper(self):
                asyncio.ensure_future(fnc(self))
                
            result = asyncwrapper
            
        result.statemachine_usecase = "onExit"
        result.statemachine_data = state
        return result

    return wrapper

def transition(start, end, *arg):
    
    def wrapper(fnc):
        
        result = fnc
        if asyncio.iscoroutinefunction(fnc):
            
            def asyncwrapper(self):
                asyncio.ensure_future(fnc(self))
                
            result = asyncwrapper
            
        result.statemachine_usecase = "transition"
        result.statemachine_data = (start, end, arg)
        return result

    return wrapper

def onFinish(fnc):
    
    result = fnc
    if asyncio.iscoroutinefunction(fnc):
        
        def asyncwrapper(self):
            asyncio.ensure_future(fnc(self))
            
        result = asyncwrapper
    
    result.statemachine_usecase = "onFinish"
    return result

def onProcessingEnter(fnc):
    
    result = fnc
    if asyncio.iscoroutinefunction(fnc):
        
        def asyncwrapper(self):
            asyncio.ensure_future(fnc(self))
            
        result = asyncwrapper
    
    result.statemachine_usecase = "onProcessingEnter"
    return result

def onProcessingExit(fnc):
    
    result = fnc
    if asyncio.iscoroutinefunction(fnc):
        
        def asyncwrapper(self):
            asyncio.ensure_future(fnc(self))
            
        result = asyncwrapper
    
    result.statemachine_usecase = "onProcessingExit"
    return result

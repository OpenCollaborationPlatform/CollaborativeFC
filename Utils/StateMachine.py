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
from PySide import QtCore

class StateTypes(Enum):
        Normal = auto()
        Initial = auto()
        Final = auto()
        Group = auto()
        Parallel = auto()
        

# ***********************************************************************************************************************
#                                                   Setup implementation                                               
# ***********************************************************************************************************************


class _StateDefBase():
    # Base class for all state defining classes
    
    type = StateTypes.Normal
    name = "unknown"
    
    def __repr__(self):
        return f"<State {self.name}: {self.type.name}>"
    
    def __str__(self):
        return f"<State {self.name}: {self.type.name}>"
    
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
        return f"<State {self.name}: {self.type.name}>"
    
    def __str__(self):
        return f"<State {self.name}: {self.type.name}>"

    def __iter__(self):
        result = []
        for entry in self.__dict__:
            
            item = self.__dict__[entry]
            if isinstance(item, _StateDefBase) or (inspect.isclass(item) and issubclass(item, _StateDefBase)):
                result.append(self.__dict__[entry])
        
        return iter(result)

class State(_StateDefBase):
    type = StateTypes.Normal

class InitialState(_StateDefBase):
    type = StateTypes.Initial

class FinalState(_StateDefBase):
    type = StateTypes.Final
    
class States(_StateDefBase, metaclass=_StateDefMeta):
    type = StateTypes.Group
    
class GroupedStates(_StateDefBase, metaclass=_StateDefMeta):
    type = StateTypes.Group

class ParallelStates(_StateDefBase, metaclass=_StateDefMeta):
    type = StateTypes.Parallel


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


class Events(_EventDefBase, metaclass = _EventDefMeta):
    pass


class Transitions(_EventDefBase):
    
    def __init__(self, *args):
        self._transition_touples = args
        
    def __iter__(self):
        return iter(self._transition_touples)


# ***********************************************************************************************************************
#                                                   Logic implementation                                       
# ***********************************************************************************************************************


class _Transition(QtCore.QObject):
    # Rrepresenting a transition between two states in the state machine
    # Used to connect to signals
    
    executed = QtCore.Signal()
    
    def __init__(self, target):
        super().__init__()
        self._target = target

  
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
        self._direct_transition  = None # direct transitions
        
        if parent:
            parent._children.add(self)

    def _addTransition(self, to, *args):
        
        result = None
        
        if args:
            if args[0] in self._transitions:
                raise Exception(f"{self.identifier} already has transition for {args[0]}")
            
            result = _Transition(to)
            self._transitions[args[0]] = result
            
        else:
            if self._direct_transition:
                raise Exception(f"{self.identifier} already has direct transition")
            
            if self.identifier.type == StateTypes.Group or self.identifier.type == StateTypes.Parallel:
                raise Exception(f"Direct transitions not supported for {self.identifier.type} states")
            
            result = _Transition(to)
            self._direct_transitions = result
            
        return result
            
    
    def _getDirectTransition(self) -> _Transition:
        return self._direct_transition
    
    
    def _getTransition(self, event) -> _Transition:
        # returns the state to transition to for given event, or None
        
        if event in self._transitions:
            return self._transitions[event]
        else:
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
        
        if self.identifier.type == StateTypes.Group:
            # we check if any child should be activated, if not, activate the initial one
            for child in self._children:
                if child in required:
                    child._activate(required)
                    return
                    
            # if we are here none of the childs was in required, we activate the default initial one
            assert self._initial, "Group has no initial state defined"
            self._initial._activate(required)
                
        if self.identifier.type == StateTypes.Parallel:
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
    def active(self):
        return self._active
        
    def _onEntry(self):
        # procecss the enter callbacks
        self.entered.emit()
        
    def _onExit(self):
        # processes all user callbacks on exit of state        
        self.exited.emit()
            


class StateMachine(QtCore.QObject):
    # class representing a state machine
    
    finished = QtCore.Signal()    # Emitted if a FinalState is reached
    
    def __init__(self):
        
        subclassDir = dir(self) # get dir before we add out base class types to self to avoid doubling states and events
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
                    
                elif item.statemachine_usecase == "onTransition":
                    assert len(item.statemachine_data) >= 1, "wrong argument count for onTransition callback"
                    assert item.statemachine_data[0] in self.__states, "onTransition callback start state is invalid"

                    if len(item.statemachine_data) == 1:
                        direct = self.__states[item.statemachine_data[0]]._getDirectTransition()
                        if not direct:
                            raise Exception("Direct transaction does not exist")
                        direct.executed.connect(item)
                    else:
                        trans = self.__states[item.statemachine_data[0]]._getTransition(item.statemachine_data[1])
                        if not trans:
                            raise Exception("Event transaction does not exist")
                        trans.executed.connect(item)
    
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
            if state.type == StateTypes.Initial:
                if not parent:
                    stateObj._active = True
                else:
                    assert not parent._initial, "Only a single initial sate is allowed per group"
                    parent._initial = stateObj
            
            if state.type == StateTypes.Group or state.type == StateTypes.Parallel:
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
       
        # from the current active states, see to which we are going to transition
        trans = self.__findTransition(self._rootStates, event)
        if not trans:
            return
        
        start = trans[0]
        startPath = self.__getUpwardsPath(start)
        end = trans[1]._target
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
        
        # check if we reached a final state (a group or initial state cannot be final, hence it's
        # enough to check end state
        self.__processing = False
        if end.identifier.type == StateTypes.Final:
            self.__finished = True
            self.finished.emit()
        else:    
            # process all events emmitd during this run. For that we need a local copie,
            # as the other runs may also emit new events that need collection
            events = self.processEvents.copy()
            for event in events:
                self.processEvent(event)
       
    
    def __findTransition(self, states, event):
        # recursively searches the states for transitions with the given event
        # returns a tuple with (start, end) states
        
        for state in states:
            if state.active:
                trans = state._getTransition(event)
                if trans:
                    return (state, trans)
                else:
                    states = self.__findTransition(state._children, event)
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

    
    def addTransition(self, start, end, *args) -> _Transition:
        # Adds a new transition between start and end states.
        # Additional arguments can be:
        # None:   Transition that is executed directly when state is entered
        # Event:  Transition that is executed when the event is processes
        # Signal: Transition that is executed when the signal is emitted
        
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
        return self.__states[start]._addTransition(self.__states[end], *args)

    
    def state(self, state) -> _State:
        assert state in self.__states, "Invalid state identifier"

        return self.__states[state]
    
    def transition(self, start, end, *args) -> _Transition:
        assert start in self.__states, "Invalid state identifier"
        assert end in self.__states, "Invalid state identifier"

        return self.__states[start]._getTransition(end, *args)



# ***********************************************************************************************************************
#                                                   Callback setups                                               
# ***********************************************************************************************************************


def onEnter(state):
    
    def wrapper(fnc):
        
        if asyncio.iscoroutine(fnc):
            
            def asyncwrapper():
                asyncio.ensure_future(fnc())
                
            fnc = asyncwrapper()
        
        fnc.statemachine_usecase = "onEnter"
        fnc.statemachine_data = state
        return fnc

    return wrapper

def onExit(state):
    
    def wrapper(fnc):
        
        if asyncio.iscoroutine(fnc):
            
            def asyncwrapper():
                asyncio.ensure_future(fnc())
                
            fnc = asyncwrapper()
            
        fnc.statemachine_usecase = "onExit"
        fnc.statemachine_data = state
        return fnc

    return wrapper

def onTransition(start, *arg):
    
    def wrapper(fnc):
        
        if asyncio.iscoroutine(fnc):
            
            def asyncwrapper():
                asyncio.ensure_future(fnc())
                
            fnc = asyncwrapper()
            
        fnc.statemachine_usecase = "onTransition"
        fnc.statemachine_data = (start, *arg)
        return fnc

    return wrapper

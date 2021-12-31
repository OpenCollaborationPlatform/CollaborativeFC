import unittest

   
from enum import Enum, auto
import StateMachine as SM
from PySide2 import QtCore, QtGui, QtWidgets

class States(SM.States):
        
    FirstState = SM.InitialState()
    SecondState = SM.State()
    ThirdState = SM.State()
    FourthState = SM.FinalState()
    ProcessState = SM.ProcessState()
    
    class FirstGroup(SM.GroupedStates):
        
        FirstState = SM.InitialState()
        SecondState = SM.State()
        
        class FirstGroup(SM.GroupedStates):
        
            FirstState = SM.InitialState()
            SecondState = SM.State()
                   
    class ParallelGroup(SM.ParallelStates):
    
        class FirstGroup(SM.GroupedStates):
    
            FirstState = SM.InitialState()
            SecondState = SM.State()
            
        class SecondGroup(SM.GroupedStates):
    
            FirstState = SM.InitialState()
            SecondState = SM.State()
            
            class FirstGroup(SM.GroupedStates):
    
                FirstState = SM.InitialState()
                SecondState = SM.State()
                
            class SecondGroup(SM.GroupedStates):
        
                FirstState = SM.InitialState()
                SecondState = SM.State()


class Events(SM.Events):
    first = SM.Transitions((States.FirstState, States.SecondState),
                          (States.SecondState, States.FirstGroup.FirstState),
                          (States.FirstGroup.FirstState, States.FirstGroup.SecondState),
                          (States.FirstGroup.SecondState, States.FirstGroup.FirstGroup.SecondState),
                          (States.FirstGroup.FirstGroup.SecondState, States.ThirdState),
                          (States.ThirdState, States.FirstGroup.FirstGroup))
    
    second = SM.Transitions((States.FirstState, States.ParallelGroup),
                          (States.ParallelGroup.FirstGroup.FirstState, States.ParallelGroup.FirstGroup.SecondState))
    
    third  = SM.Transitions((States.ParallelGroup.SecondGroup.FirstState, States.ParallelGroup.SecondGroup.SecondState),
                            (States.ParallelGroup.SecondGroup.SecondState, States.ParallelGroup.SecondGroup.FirstGroup.SecondState),
                            (States.ParallelGroup.SecondGroup.FirstGroup.SecondState, States.ParallelGroup.SecondGroup.SecondGroup.FirstState),
                            (States.ParallelGroup.SecondGroup.SecondGroup.FirstState, States.ParallelGroup.SecondGroup.FirstState))
    fourth = SM.Transitions((States.ParallelGroup.SecondGroup.FirstState, States.FirstGroup.FirstGroup))
    fith = SM.Transitions((States.FirstState, States.ProcessState),
                          (States.ProcessState, States.FourthState))
    sixth = SM.Transitions()


class MyTest(SM.StateMachine):  
        
    States = States
    Events = Events        

    def __init__(self):
        super().__init__()
        
        self.callbacks = []
        
        
    @SM.onEnter(States.SecondState)
    def c1(self):
        self.callbacks.append("c1")
        
    @SM.onEnter(States.FirstGroup)
    def c2(self):
        self.callbacks.append("c2")
        
    @SM.onExit(States.FirstGroup)
    def c3(self):
        self.callbacks.append("c3")
        
    @SM.onExit(States.FirstState)
    def c4(self):
        self.callbacks.append("c4")
        
    @SM.onTransition(States.FirstState, Events.first)
    def c5(self):
        self.callbacks.append("c5")
        
    @SM.onProcessingEnter
    def c6(self):
        self.callbacks.append("c6")
        
    @SM.onProcessingExit
    def c7(self):
        self.callbacks.append("c7")
        

class TestStateMachine(unittest.TestCase):


    def test_enum(self):
        
        self.assertNotEqual(States.FirstState, States.SecondState)
        self.assertEqual(States.FirstState, States.FirstState)
        self.assertNotEqual(States.FirstGroup, States.SecondState)
        self.assertEqual(States.FirstGroup, States.FirstGroup)
        self.assertNotEqual(States.FirstGroup, States.FirstGroup.FirstGroup)
        self.assertNotEqual(States.FirstGroup.FirstState, States.FirstGroup.FirstGroup.FirstState)

    def test_signal_event(self):
        
        class Obj(QtCore.QObject):
            sig = QtCore.Signal()
            
            def __init__(self):
                QtCore.QObject.__init__(self)
        
        t = MyTest()
        o = Obj()
        
        trans = t.addTransition(States.FirstState, States.SecondState, o.sig)
        trans.executed.connect(lambda: t.callbacks.append("transition"))
        
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.FirstState, t.activeStates)
        o.sig.emit()
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.SecondState, t.activeStates)
        o.sig.emit()
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.SecondState, t.activeStates)
        
        self.assertIn("transition", t.callbacks)
        

    def test_callbacks(self):
        
        t = MyTest()
        t.processEvent(Events.first)
        self.assertEqual(len(t.callbacks), 3)
        self.assertIn("c1", t.callbacks)
        self.assertIn("c4", t.callbacks)
        self.assertIn("c5", t.callbacks)
        
    
    def test_processing_states(self):
        
        t = MyTest()
        callbacks = []
        t.onProcessingEnter.connect(lambda: callbacks.append("enter"))
        t.onProcessingExit.connect(lambda: callbacks.append("exit"))
    
        t.processEvent(Events.fith)
        self.assertEqual(len(callbacks), 1)
        self.assertIn("enter", callbacks)
        self.assertIn("c6", t.callbacks)
        
        t.processEvent(Events.fith)
        self.assertEqual(len(callbacks), 2)
        self.assertIn("exit", callbacks)
        self.assertIn("c7", t.callbacks)
        
        
    def test_direct_transitions(self):
        
        t = MyTest()
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.FirstState, t.activeStates)
        
        t.addTransition(States.FirstState, States.SecondState, Events.sixth)
        t.addTransition(States.SecondState, States.ThirdState)
        
        t.processEvent(Events.sixth)
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.ThirdState, t.activeStates)
        

    def test_group_transitions(self):

        t = MyTest()
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.FirstState, t.activeStates)
        
        # toplevel state to state
        t.processEvent(Events.first)
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.SecondState, t.activeStates)
        
        # state to group state
        t.processEvent(Events.first)
        self.assertEqual(len(t.activeStates), 2)
        self.assertIn(States.FirstGroup, t.activeStates)
        self.assertIn(States.FirstGroup.FirstState, t.activeStates)
        
        # inner subgroup states
        t.processEvent(Events.first)
        self.assertEqual(len(t.activeStates), 2)
        self.assertIn(States.FirstGroup, t.activeStates)
        self.assertIn(States.FirstGroup.SecondState, t.activeStates)
        
        # subgroup to further subgroup state
        t.processEvent(Events.first)
        self.assertEqual(len(t.activeStates), 3)
        self.assertIn(States.FirstGroup, t.activeStates)
        self.assertIn(States.FirstGroup.FirstGroup, t.activeStates)
        self.assertIn(States.FirstGroup.FirstGroup.SecondState, t.activeStates)
        
        # subgroup to toplevel state
        t.processEvent(Events.first)
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.ThirdState, t.activeStates)

        # toplevel state to subgroup
        t.processEvent(Events.first)
        self.assertEqual(len(t.activeStates), 3)
        self.assertIn(States.FirstGroup, t.activeStates)
        self.assertIn(States.FirstGroup.FirstGroup, t.activeStates)
        self.assertIn(States.FirstGroup.FirstGroup.FirstState, t.activeStates)


    def test_parallel_states(self):
        
        t = MyTest()
        
        t.processEvent(Events.second)
        self.assertEqual(len(t.activeStates), 5)
        self.assertIn(States.ParallelGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.FirstGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.FirstGroup.FirstState, t.activeStates)
        self.assertIn(States.ParallelGroup.SecondGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.SecondGroup.FirstState, t.activeStates)
        
        t.processEvent(Events.second)
        self.assertEqual(len(t.activeStates), 5)
        self.assertIn(States.ParallelGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.FirstGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.FirstGroup.SecondState, t.activeStates)
        self.assertIn(States.ParallelGroup.SecondGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.SecondGroup.FirstState, t.activeStates)
        
        t.processEvent(Events.third)
        self.assertEqual(len(t.activeStates), 5)
        self.assertIn(States.ParallelGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.FirstGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.FirstGroup.SecondState, t.activeStates)
        self.assertIn(States.ParallelGroup.SecondGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.SecondGroup.SecondState, t.activeStates)
        
        t.processEvent(Events.third)
        self.assertEqual(len(t.activeStates), 6)
        self.assertIn(States.ParallelGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.FirstGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.FirstGroup.SecondState, t.activeStates)
        self.assertIn(States.ParallelGroup.SecondGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.SecondGroup.FirstGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.SecondGroup.FirstGroup.SecondState, t.activeStates)
        
        t.processEvent(Events.third)
        self.assertEqual(len(t.activeStates), 6)
        self.assertIn(States.ParallelGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.FirstGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.FirstGroup.SecondState, t.activeStates)
        self.assertIn(States.ParallelGroup.SecondGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.SecondGroup.SecondGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.SecondGroup.SecondGroup.FirstState, t.activeStates)
        
        t.processEvent(Events.third)
        self.assertEqual(len(t.activeStates), 5)
        self.assertIn(States.ParallelGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.FirstGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.FirstGroup.SecondState, t.activeStates)
        self.assertIn(States.ParallelGroup.SecondGroup, t.activeStates)
        self.assertIn(States.ParallelGroup.SecondGroup.FirstState, t.activeStates)
        
        t.processEvent(Events.fourth)
        self.assertEqual(len(t.activeStates), 3)
        self.assertIn(States.FirstGroup, t.activeStates)
        self.assertIn(States.FirstGroup.FirstGroup, t.activeStates)
        self.assertIn(States.FirstGroup.FirstGroup.FirstState, t.activeStates)
        
    def test_conditional_transitions(self):

        t = MyTest()
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.FirstState, t.activeStates)
        
        t.myvar = 0
        def condition1(sm):
            return sm.myvar == 1
         
        def condition2(sm):
            return sm.myvar == 2
         
        t.addTransition(States.FirstState, States.SecondState, Events.sixth, condition = condition1)
        t.addTransition(States.FirstState, States.ThirdState, Events.sixth, condition = condition2)
        t.addTransition(States.SecondState, States.FirstState, Events.sixth)
        t.addTransition(States.ThirdState, States.ProcessState, condition = condition1)
        t.addTransition(States.ThirdState, States.FourthState, condition = condition2)
         
        # with no condition meet, there should be no state change
        t.processEvent(Events.sixth)
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.FirstState, t.activeStates)
        
        #with one condition meet we should transition
        t.myvar = 1
        t.processEvent(Events.sixth)
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.SecondState, t.activeStates)
        
        #with the other one meet we should transition (incl. the direct transition)
        t.myvar = 2
        t.processEvent(Events.sixth) # back to first
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.FirstState, t.activeStates)
        t.processEvent(Events.sixth) # transition to third, direct transition to fourth
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.FourthState, t.activeStates)
        

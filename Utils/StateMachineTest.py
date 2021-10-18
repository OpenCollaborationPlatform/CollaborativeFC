import unittest

   
from enum import Enum, auto
import StateMachine as SM
from PySide2 import QtCore, QtGui, QtWidgets

class States(SM.States):
        
    FirstState = SM.InitialState()
    SecondState = SM.State()
    ThirdState = SM.State()
    FourthState = SM.FinalState()
    
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


class MyTest(SM.StateMachine):  
        
    States = States
    Events = Events        

    def __init__(self):
        super().__init__()
        
        
        
    @SM.onEnter(States.SecondState)
    def hmm(self):
        print("Enter second state")
        
    @SM.onEnter(States.FirstGroup)
    def enterGroup(self):
        print("enter mygroup")
        
    @SM.onExit(States.FirstGroup)
    def leaveGroup(self):
        print("exit mygroup")
        
    @SM.onExit(States.FirstState)
    def ohh(self):
        print("leave first state")
        
    @SM.onTransition(States.FirstState, Events.first)
    def ohh(self):
        print("Transition first to second")
        

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
        trans.executed.connect(lambda: print("transition"))
        
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.FirstState, t.activeStates)
        o.sig.emit()
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.SecondState, t.activeStates)
        o.sig.emit()
        self.assertEqual(len(t.activeStates), 1)
        self.assertIn(States.SecondState, t.activeStates)


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

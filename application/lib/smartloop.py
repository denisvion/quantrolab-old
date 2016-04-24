import yaml
import StringIO
import os
import os.path
import pickle
import sys
import copy
import time
import weakref
import re
import string
from ctypes import *
from numpy import *
from scipy import *

# Smartloops are debuggable and reloadable
from application.lib.base_classes1 import Debugger, Reloadable
# and can send and receive notifications
from application.lib.com_classes import Subject, Observer

##############################################
# To Do: lock modifications during next ?    #
##############################################

epsilon = 1e-10  # for numerical comparisons
# Rounding is made at each increment to avoid accumulation of numerical errors.
# used to calculate the incremented value
# round(val+step,digits-int(log10(abs(step))))
digits = 6


class SmartLoop(Debugger, Subject, Observer, Reloadable):
    """
    The SmartLoop class implements a loop with the following (smart) features:
      The SmartLoop can look for a LoopManager in memory and adds itself to it.
      The SmartLoop has
        - a name set at creation or with method 'setName', which can be read with method 'getName',
        - an optional parent loop set at creation or with method 'setParent', which can be read with method 'parent',
        - a list of children loops fed with method 'addChild', which can be read using method 'children'.
      The SmartLoop has also
            - one output value accessed with the method 'getValue',
            - an index that counts the number of iterations, which is read with method 'getIndex',
            - and a history of all its past values, which is accessed with method 'history'.
      The SmartLoop's base parameters are its start,stop and step values;
        They can be read or redefined at any time using methods 'getStart', 'getStop', 'getStep', 'setStart', 'setStop', 'setStep';
        Consequently, there is no fixed number of steps, although an initial number of steps can be specified at creation for conveniency.
      The SmartLoop is automatically terminated if its next value falls outside the start-stop range;
      Stop (and start after the loop has been started) can be set to None to make the loop infinite;
      The SmartLoop can jump to any value along the loop at the next increment using the method 'jumpToValue';
      The SmartLoop can be paused, played, reversed or terminated at the next increment using methods 'pause', 'play', 'reverse', 'stopAtNext'.
      Autoreverse or circular looping  when crossing start or stop can be set on and off, or read,
        using methods 'setAutoreverse', 'getAutoreverse', 'setAutoLoop', 'getAutoLoop'.
      Duration of an iteration averaged over all previous iterations with no pause can be obtained using 'iterationDuration()'.
      A dictionary including all loop parameters as well as an estimate of the remaining time before termination is obtained with method 'getParams'

    Iteration mechanism:
      As any other iterator in python, the smartloop increments itself by its next() method, which
      1) pauses or terminates the loop if requested by pause() or stopAtNext();
      2) calls an empty preIncrement function (to be overriden in subclasses if needed) ;
      3) updates the base parameters in case they were redefined with setStart, setStop, setStep;
      4) reverses or loops the loop if needed;
      5) updates time information;
      6) increments the index and output value, or terminates;
      7) updates history.

    In case of a terminate, the loop is
      - reinitialized if the loop was not stopped;
      - stopped by raising an error without reinitialization otherwise.
      - removed from its loop manager if it has one and if autoremove is true;

    The SmartLoop subclasses Subject and Observer classes and can send and receive notifications.
    It is designed to be subclassed by other types of loops with more specific (even smarter ;-) behaviors.

    """

    def __init__(self, start=0, step=1, stop=None, linnsteps=None, name='unamed', parent=None, toLoopManager=True, autoreverse=False, autoloop=False, autoremove=True):
        """
        Initializes the smartloop and adds it to the LoopManager if toLoopManager is true.
        """
        Debugger.__init__(self)
        Subject.__init__(self)
        Observer.__init__(self)
        Reloadable.__init__(self)

        self._children = []
        self._parent = None
        self.setParent(parent)

        self._name = name
        # memorize the initial start value in case it is erased by user
        self._start0 = start
        self._stop = stop
        self._step = step
        self._autoreverse = autoreverse  # has priority over autoLoop
        self._autoloop = autoloop
        self._autoremove = autoremove
        self.reinit()

        # specifies a number of equidistant steps up to stop or start +
        # linnsteps steps.
        if linnsteps is not None:
            if stop is not None:
                self._step = (stop - start) / linnsteps
            else:
                self._stop = start + linnsteps * self._step

        self._lm = None               # loop can have a loop manager
        if toLoopManager:             # and adds itself to it if toManager is true.
            self.toLoopManager()

        self.debugPrint('exiting loop', self.getName(
        ), '.init with start, stop, step = ', self._start, self._stop, self._step)

    def reinit(self):
        """
        Restores the loop in the states before first increment.
        """
        self._start = self._start0
        # index, value and previous value start at None.
        self._index = None
        self._value = None            # index, value will be valued at first  iteration
        self._imposedValue = None       # index at None means restart
        self._history = []
        self._previousValue = None    # previousValue will be valued at second iteration
        self._paused = False
        self._finished = False

        # time management
        self._time = None               # time of the last iteration
        # indicates whether pause was activated during last iteration
        self._pauseInLast = False
        # number of iteration free of pause (used to estimate durations)
        self._indexNoPause = 0
        self._duration = 0              # total duration of iterations with no pause
        self._averageDuration = None    # average duration of an iteration with no pause

        # Will be set to False if a stop is requested so that the loop can be
        # resumed
        self._reinitAtTerminate = True

    # Parent and children methods
    # A loop can have only one parent but many children.
    # A new parent-child link is established indifferently with either child.setParent or parent.addChild.
    # A previous incompatible link is automatically cleared and an impossible request is discarded.
    # An existing parent-link is destroyed indifferently with either child.clearParent() or parent.removeChild(child), or by establishing a new incompatible link
    #
    # To obtain this versatility, self.setParent(parent) calls parent.addChild(self) and self.addChild(child) calls child.setParent(self)
    # Programming has thus to avoid infinite recursion in particular when a child becomes the new parent of its old parent
    # The same remark applies to removeChild and clearParent.

    def addChild(self, child):
        """
        Adds a child to the loop.
        """
        if child is self:                             # Case 1: stupid request be your own child
            raise Exception("Cannot be my own child!")
        if self.parent() is child:                    # Case 2: the future child is currently the parent of self
            self.clearParent()
        if child in self.children():                  # Case 3: useless request cause child was already a child
            return  # this line breaks infinite recursion
        if child.parent() is not None:                # if the child has another parent
            child.parent().removeChild(self)  # remove the old parent-child link on both sides
        # append the new child to the children list
        self._children.append(child)
        # set self as the parent (avoid infinite recursion)
        child.setParent(self)
        self.notify("addChild", child)                 # notify the new link

    def setParent(self, parent):
        """
        Sets the loop's parent (or clears it if parent is None)
        """
        if parent is not None:
            # call the addChild (avoid infinite recursion)
            parent.addChild(self)
        self._parent = parent                           # set the parent
        self.notify("setParent", parent)               # notify the new link

    def removeChild(self, child):
        """
        Removes a child loop from the children list _children if it is present.
        Does not do anything otherwise (no error generated)
        Does not destroy the child loop, which has simply no parent any more.
        """
        if child in self._children:   # recursion stops if child is no longer in the children list
            self._children.remove(child)
            child.clearParent()
            self.notify("removeChild", child)

    def clearParent(self):
        """
        Clears the parent (sets it to None)
        """
        if self._parent is not None:  # recursion stops if parent is None
            self._parent.removeChild(self)
        self.setParent(None)
        self.notify("clearParent")

    def parent(self):
        """ returns the loop's parent """
        return self._parent

    def children(self):
        """ returns the list of children of the loop"""
        return self._children

    def tree(self):
        """
        Returns the loop's tree of loop objects (loop, [children, [grand-children,...])
        """
        tree = [self]
        if self.children():
            tree.append([child.tree() for child in self.children()])
        return tree

    def decendents(self):
        """
        Returns the loop's decendents [loop, children, grand-children,...] in a flatten list.
        """
        def flatten(nested, flat=[]):
            for i in nested:
                flatten(i, flat=flat) if isinstance(
                    i, list) else flat.append(i)
            return flat
        return flatten(self.tree()[1:])

    # Methods for incrementing the loop, determining if it is finished, and
    # terminating.

    def __iter__(self):
        """ possibility to overide the python iteration method"""
        return self

    def preIncrement(self):
        """
        This function is called just before updateParams in the iterator function next.
        It is left empty here but can be overidden in inherited classes.
        """
        pass

    def next(self):
        """
        Overriden function next() for python iterators.
        Increments the loop in the following way:
        1) pauses or terminates the loop if requested
        2) calls a preIncrement function (empty if not overriden)
        3) determines the next output value or if the loop is finished with the finishedOrNext method.
        4) updates time information
        5) increments the index and sets the new output value, or terminates
        """
        self.debugPrint('in ', self.getName(), '.next()')
        if self._paused:
            while self._paused:
                time.sleep(0.1)
        if self._finished:                 # terminates if _finished has been set to true by a manual stop of the loop
            self.terminate()
            raise StopIteration
        self.preIncrement()                # run empty or overriden preIncrement function
        # increment will call finishedOrNext() and will increment only if not
        # finished
        self.increment()
        self.timeUpdate()                  # update timing information
        if self._finished:
            # terminates if _finished has been set to true by increment()
            self.terminate()
            raise StopIteration
        # self.updateLoopManager()
        # tells the observers that the loop parameters have been updated
        self.notify('updateLoop')
        # append  (index,output value,time) to the history
        self._history.append((self._index, self._value, self._time))
        return self._value

    def increment(self):
        """
        private method. Core incrementing function.
        """
        self.debugPrint('in ', self.getName(), '.increment()',)
        if self._index is None:
            self._index = 0
            if self._start is not None:
                self._value = self._start
            else:
                self._value = self._start0
        else:
            # gets the next value to be applied or None if loop is finished
            nextVal = self.finishedOrNext()
            if nextVal is None:
                self._finished = True
            else:
                self.incrementIndexValue(nextVal)
        self._imposedValue = None
        self.debugPrint(' new value=', self._value,
                        ' and new index=', self._index)

    def addStep(self):
        """
        Private function
        Returns the current value + the step without introducing numerical errors,
        or _start0 if the current value is not a number.
        """
        val, step = self._value, self._step
        if all([isinstance(v, (int, long)) for v in [val, step]]):  # preserve the integer type
            return val + step
        elif all([isinstance(v, (int, long, float)) for v in [val, step]]):
            digits2 = digits - int(log10(abs(step)))
            # avoid accumulating numerical errors due to finite real precision
            return round(val + step, digits2)
        else:
            return self._start0

    def incrementIndexValue(self, nextValue):
        """
        private method. Core incrementing function. Overide this method in subclasses
        """
        self.debugPrint('in incrementIndexValue')
        self._previousValue = self._value
        self._value = nextValue                     # next output value is set
        self._index += 1                            # index is incremented

    def timeUpdate(self):
        """
        private method. update iteration duration.
        """
        time2 = time.time()
        if not self._pauseInLast:
            if self._time is not None:
                duration = time2 - self._time
                self._duration += duration
                self._indexNoPause += 1
                self._averageDuration = self._duration / self._indexNoPause
        self._time = time2
        if not self._paused:
            self._pauseInLast = False

    def iterationDuration(self):
        """ returns the iteration duration averaged over all passed iterations with no pause, or None if not available yet. """
        return self._averageDuration

    def finishedOrNext(self):
        """
        Private function.
        Determines whether the current scan is finished, and determines the next value.
        Implements autoreverse if autoreverse is true and autoloop if autoloop is true and autoreverse is false.
        Termination or looping occurs in either of these situations:
          - next value would cross either start or stop, or fall outside [start,stop];
          - autoreverse is ON and next value after reversion would be outside start-stop if start and stop exist.
        Loop is reversed if _autoreverse is true, and if next value would just cross either start or stop, but not both of them.
        If autoloop is true and autoreverse is false, next value is set to start if ramping from start to stop and to stop if ramping from stop to start.
        Returns the next output value or None if loop is finished.
        """
        start, stop, previous, val, step = self._start, self._stop, self._previousValue, self._value, self._step
        if self._imposedValue is not None:  # try the imposed value as the next one
            next = self._imposedValue
        else:
            # calculate the next value by adding step to current value
            next = self.addStep()
        self.debugPrint('in', self.getName(), '.finishedOrNext with start,stop,previous,val,step,next',
                        self._start, self._stop, self._previousValue, self._value, self._step, next)
        if next is not None:
            startIsNumber, stopIsNumber, previousIsNumber = [
                isinstance(v, (int, long, float)) for v in[start, stop, previous]]
            finished = False
            crossStart, crossStop, outside, end = [False] * 4
            if previousIsNumber:
                if startIsNumber:
                    crossStart = (next > start >= val >= previous) or (
                        next < start <= val <= previous)
                if stopIsNumber:
                    crossStop = (next > stop >= val >= previous) or (
                        next < stop <= val <= previous)
            elif stopIsNumber and startIsNumber:
                if val == start:
                    crossStop = (next > stop >= val) or (next < stop <= val)
                if val == stop:
                    crossStart = (next > start >= val) or (next < start <= val)
            if stopIsNumber and startIsNumber:
                outside = next > max(start, stop) or next < min(start, stop)
            self.debugPrint('crossStart=', crossStart,
                            ' crossStop=', crossStop, 'outside=', outside)
            if crossStart or crossStop or outside:
                finished = True
                if self._autoreverse:
                    self.reverse()
                    next = self.addStep()
                    if self._imposedValue is not None:
                        if crossStart:
                            next = start
                        elif crossStop:
                            next = stop
                    outside2 = False
                    if stopIsNumber and startIsNumber:
                        outside2 = next - \
                            max(start, stop) > epsilon or min(
                                start, stop) - next > epsilon
                    if not outside2:
                        finished = False  # not finished except if after reversing the step, next value would be outside the range
                    self.debugPrint('next=', next, ' start=', start,
                                    ' stop=', stop, ' outside2=', outside2)
                elif self._autoloop:
                    if crossStart:
                        next = self._stop
                    else:
                        next = self._start
                    finished = False
            if finished:
                next = None
        self.debugPrint('next value=', next)
        return next

    def terminate(self):
        """
        Reinitializes the loop if reinit is true and removes it from its manager if _autoremove is true.
        (this function is called if self._finished is true: end of ramp or manual stop)
        """
        self.debugPrint('in terminate')
        # the loop has finished naturally (not because of a manual stop)
        if self._reinitAtTerminate:
            self.reinit()
            # tells the listener that the loop parameters have been updated
            self.notify("updateLoop")
            if self._autoremove:
                self.removeFromManager()
        else:                         # the loop has been stopped manually
            # do not remove from manager and prepare for a possible resume
            self._finished = False
            self._reinitAtTerminate = True

    # Control of the loop and its parameters

    def stopAtNext(self):
        """
        Sets the loop as finished and deactivate reinit
        """
        self._finished = True
        self._reinitAtTerminate = False
        self._paused = False

    def pause(self):
        """ set the pause flag to true"""
        self._paused = True
        self._pauseInLast = True

    def play(self):
        """ set the pause flag to true"""
        self._paused = False

    def getMode(self):
        """
        Return the loop mode 'normal, 'autoRev', or 'autoLoop'
        """
        self.debugPrint('in getMode')
        mode = 'normal'
        if self._autoreverse:
            mode = 'autoRev'
        elif self._autoloop:
            mode = 'autoLoop'
        return mode

    def getParams(self):
        """
        Returns a dictionary with following parameters
        name,start,stop,step,index,value,mode,nextValue,autoRemove
        """
        self.debugPrint('in getParams')
        mode = self.getMode()
        dic1 = {'name': self._name, 'start': self._start, 'stop': self._stop, 'step': self._step,
                'index': self._index, 'value': self._value, 'mode': mode, 'autoRemove': self._autoremove}
        nextVal = self.finishedOrNext()
        dic1['nextValue'] = nextVal           # None if finished
        dic1['steps2Go'] = self.getSteps2Go(nextVal, mode)
        dic1['time2Go'] = self.getTime2Go(dic1['steps2Go'])
        self.debugPrint('in getParams with params= :', dic1)
        return dic1

    def getName(self):
        """ returns the loop's name"""
        return self._name

    def getStart(self):
        """ returns the loop's starting value"""
        return self._start

    def getStop(self):
        """ returns the loop's stopping value"""
        return self._stop

    def getStep(self):
        """ returns the loop's step value"""
        return self._step

    def getIndex(self):
        """ returns the loop's current index value"""
        return self._index

    def getValue(self):
        """ Returns the loop's current value"""
        return self._value

    def getSteps2Go(self, nextVal, mode='normal'):
        steps2Go = 'inf'
        # nextVal is None only when a loop is finished
        if nextVal is None:
            # It is self._start at start with self._start being always a number
            # at start
            steps2Go = 0
        elif all([isinstance(v, (int, long, float)) for v in [self._step, nextVal]]):
            steps2Go, steps2Start, steps2Stop = None, None, None
            if self._value is not None and isinstance(self._start, (int, long, float)):
                # number of intervals at next iteration
                steps2Start = int(
                    round((float(self._start) - nextVal) / self._step, 0))
                if steps2Start >= 0:
                    steps2Go = steps2Start
            if isinstance(self._stop, (int, long, float)):
                steps2Stop = int(
                    round((float(self._stop) - nextVal) / self._step, 0))
                if steps2Stop >= 0:
                    if steps2Go is None or steps2Stop < steps2Go:
                        steps2Go = steps2Stop
            if isinstance(steps2Go, (int, long)):
                # number of intervals at next iteration +1 + current steps
                steps2Go += 1
        return steps2Go

    def getTime2Go(self, steps2Go):
        if steps2Go == 'inf':
            time2Go = 'inf'
        elif isinstance(steps2Go, (int, long)) and isinstance(self._averageDuration, (int, long, float)):
            time2Go = self._averageDuration * steps2Go
        else:
            time2Go = '?'
        return time2Go

    def history(self):
        """ returns the list of tuples (index,output value,time) """
        return self._history

    def setName(self, newName):
        """
        Immediately redefines the name of the loop.
        """
        self._name = newName
        self.notify('updateLoop')
        return self._name

    def setStart(self, newStart):
        """
        Stores in _nextParams dictionary the new start and corresponding new nsteps and index, leaving other parameters unchanged.
        """
        # self._nextParams={'start':newStart}
        self._start = newStart
        if newStart is not None:
            # memorize the last start different from None to be able to restart
            # a loop
            self._start0 = newStart
        self.notify('updateLoop')

    def setStop(self, newStop):
        """
        Stores in _nextParams dictionary the new stop and corresponding new nsteps, leaving other parameters unchanged.
        """
        self._stop = newStop
        self.notify('updateLoop')

    def setStep(self, newStep):
        """
        Stores in _nextParams dictionary the new step and corresponding new nsteps and index , leaving other parameters unchanged.
        """
        self.debugPrint('in setStep with newStep = %s' % newStep)
        self._step = newStep
        self.notify('updateLoop')

    def reverse(self):
        """ Reverse the ramp direction by reversing the sign of step immediately"""
        self.debugPrint('reversing step')
        self._step *= -1
        self.notify('updateLoop')

    def jumpToValue(self, value):
        """ Stores in _nextParams dictionary the value to which the loop will jump at next iteration."""
        self.debugPrint('in jumpToValue with value = ', value)
        self._imposedValue = value
        self.notify('updateLoop')

    def jumpToFirst(self):
        """ Stores in _nextParams dictionary the start value (to which the loop will jump at next iteration)."""
        self.jumpToValue(self._start)

    def jumpToLast(self):
        """ Stores in _nextParams dictionary the stop value (to which the loop will jump at next iteration)."""
        self.jumpToValue(self._stop)

    def setNSteps2Go(self, nSteps=10, adaptStep=True):
        """
        Sets
          - either step if step is None or adaptStep is True and ramp is going towards an existing end (start or stop)
          - or the end (start or stop) the current ramp is going to otherwise,
        in order to have nSteps values from now before the next expected termination.
        """
        start, stop, prev, val, step = self._start, self._stop, self._previousValue, self._value, self._step
        if val is not None:
            v = val
        else:
            v = start
        if v is None:
            return              # we don't know where we are, we stop
        if stop is None and start is None:  # no start no stop => set stop if step > 0 or start if step < 0
            if step is None or step == 0:
                return   # no valid step => break
            elif step > 0:
                s = v + step * nSteps
            else:
                s = v - step * nSteps
            self.setStart(s)
        else:                               # there is either a start, a stop, or both
            if step is None or step == 0:
                if stop is not None:
                    s = (stop - v) / nSteps
                else:
                    s = (stop - v) / nSteps
                self.setStep(s)
            else:                             # step OK => determine whether ramping towards start or stop
                toStop = (stop is not None and (stop - v) * step >
                          0) or (start is not None and (start - v) * step < 0)
                toStart = (start is not None and (start - v) * step >
                           0) or (stop is not None and (stop - v) * step < 0)
                end = v + step * nSteps
                if toStop and (not adaptStep or stop is None):
                    self.setStop(end)
                elif toStart and (not adaptStep or start is None):
                    self.setStart(end)
                else:
                    if toStop:
                        s = (stop - v) / nSteps
                    else:
                        s = (start - v) / nStep
                    self.setStep(s)

    def getAutoreverse(self):
        """ Returns the autoreverse flag"""
        return self._autoreverse

    def setAutoreverse(self, ONorOFF):
        """ Set the autoreverse flag to True or False"""
        self._autoreverse = ONorOFF
        self.notify('updateLoop')
        return self._autoreverse

    def getAutoloop(self):
        """ Returns the autoloop flag"""
        return self._autoloop

    def setAutoloop(self, ONorOFF):
        """ Set the autoloop flag to True or False"""
        self._autoloop = ONorOFF
        self.notify('updateLoop')
        return self._autoloop

    def getAutoremove(self):
        """ Returns the autoremove flag"""
        return self._autoremove

    def setAutoremove(self, ONorOFF):
        """ Set the autoremove flag to True or False"""
        self._autoremove = ONorOFF
        self.notify('updateLoop')
        return self._autoremove

    # Stopping the loop and all its descendants

    def stopAllAtNext(self):
        """
        Stops the smartloop and all its descendants
        """
        self.stopAtNext()
        for child in self.children():
            child.stopAtNext()

    # Interaction with loopManager

    def _findALoopMgr(self):
        """
        Private function.
        Returns the first LoopMgr instance found in the global variables namespace (but does not load it).
        BUG: the manager will be in globals of a script only if it was loaded before the script is run for the first time.
        BUG: This is because the global variables are recopied in the script scope at the first run...
        """
        lm = None
        try:
            # read the class LoopMgr
            from application.helpers.loopmanager.loopmgr import LoopMgr
            # try to load the LoopMgr class in order to be able
            lm = LoopMgr._instance
            if lm:
                lm = weakref.ref(lm)
        except:
            pass
        return lm

    def loopMgr(self):
        """ returns the weak reference to the LoopMgr stored in _lm"""
        return self._lm

    def toLoopManager(self):
        """
        Adds the loop to the loop manager if it exists in memory
        """
        if self._lm is None:                    # BUG ? should also check if the manager still exists
            self._lm = self._findALoopMgr()
        if self._lm is not None:
            self._lm().addLoop(self)      # add to the manager
            return 1
        return 0

    def removeFromManager(self):
        """
        Removes the loop from its loop manager if it exists

        """
        if self._lm is not None:
            # loop directly removed to the manager
            self._lm.removeLoop(self)


class PredefinedLoop(SmartLoop):
    """
    Smartloop with a list of predefined values.
    The loop works as a smartloop operating on the indices rather than on the output values.
    """

    def __init__(self, start=0, values=range(10), **kwargs):
        self._values = values
        # initialize start and index
        SmartLoop.__init__(self, **kwargs)
        if not isinstance(self._stop, (int, long)) or self._stop < 0 or self._stop > len(values) - 1:
            # and stop as the last index if not already defined
            self._stop = len(values) - 1
        self._previousIndex = None

    def next(self):
        # the value has the index in a predefined loop
        return self._values[super(PredefinedLoop, self).next()]

    def getValue(self):
        # the value has the index in a predefined loop
        return self._values[self._value]


class AdaptiveLoop(SmartLoop):
    """
    Smartloop with a method for adapting its next update based on a feedback value.
    Typical feedback consists in calling newFeedbackValue(value) once per loop iteration.
    All feedback values are stored in _feedBackValues.
    The adaptive function is an external function adaptiveFunc(adaptiveLoop) with the loop as its single parameter.
    It has consequently access to all methods of a adaptiveLoop including getParams, feedBackValues, and all methods filling _nextParams
    It is passed to the adaptive loop at its creation or later using the setAdaptFunc(function) method

    Example:

      def adaptFunc1(adaptiveLoop):
        adaptiveLoop.setStep(1)
        if adaptiveLoop.feedBackValues[-1] > 2: adaptiveLoop.setStep(2)

      adaptiveLoop1=AdaptiveLoop(0,step=1,stop=10,adaptFunc=adaptFunc1)
      for x in adaptiveLoop1:
        # do something here and generate a feedback value yi
        adaptiveLoop1.newFeedbackValue(yi)

    WARNING: Competing with adaptFunc1() by changing in parallel the loop parameters from another piece of code or from a GUI interface
    will very likely lead to wrong results and errors.
    """

    def __init__(self, adaptFunc=None, **kwargs):
        SmartLoop.__init__(self, **kwargs)
        self._feedBackValues = []
        self._adaptFunc = adaptFunc

    def newFeedbackValue(self, value):
        self._feedBackValues.append(value)

    def feedBackValues(self):
        return self._feedBackValues

    def adaptFunc(self, adaptFunc):
        return self._adaptFunc

    def setAdaptFunc(self, adaptFunc):
        self._adaptFunc = adaptFunc
        return self._adaptFunc

    def preIncrement(self):  # overidden method of the SmartLoop parent class
        self.debugPrint(
            'in preincrement calling self._adaptFunc with feedBackValues=', self._feedBackValues)
        if self._adaptFunc is not None:
            self._adaptFunc(self)

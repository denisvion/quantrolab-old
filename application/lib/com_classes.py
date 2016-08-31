"""
This module defines several important abstract communication classes:
  Subject, Observer, Dispatcher(Subject) and ThreadedDispatcher(Dispatcher)
  are able to communicate with each other asynchroneously.
"""

DEBUG = False

"""
This module defines the abstract classes able to communicate asynchroneously between each other
Subject, Observer, and Dispatcher(Subject) and ThreadedDispatcher(KillableThread).
"""

import threading
import time
import ctypes
import timeit
import sys
import copy
import weakref
from base_classes1 import KillableThread


class Subject:
    """
    This class is part of a Subject-Observer communication system between objects.
    The subject manage a list of observers, and can notify to all of them some messages of the form: property, value.
    The notification is actually a direct call of the observer method observer.updated(self,property,value),
      where self indicates ot the observer the subject sending the message.
    """

    def __init__(self):
        self._observers = []
        self.isNotifying = False

    def __getstate__(self):
        variables = copy.copy(self.__dict__)
        if "_observers" in variables:
            del variables["_observers"]
        return variables

    def __setstate__(self, state):
        self.__dict__ = state
        self._observers = []

    def attach(self, observer):
        r = weakref.ref(observer)
        if r not in self._observers:
            self._observers.append(r)

    def setObservers(self, observers):
        if observers is not None:
            self._observers = observers
        else:
            self._observers = []

    def observers(self):
        return self._observers

    def detach(self, observer):
        r = weakref.ref(observer)
        try:
            if DEBUG:
                print "Removing observer."
            self._observers.remove(r)
        except ValueError:
            pass

    def notify(self, property=None, value=None, modifier=None):
        try:
            # This is to avoid infinite notification loop, e.g. when the
            # notified class calls a function of the subject that triggers
            # another notify and so on...
            if self.isNotifying:
                # print "WARNING: notify for property %s of %s was called
                # recursively by modifier %s, aborting." %
                # (property,str(self),str(modifier))
                print 'previous notification not finished'
                return False
            self.isNotifying = True
            deadObservers = []
            for observer in self._observers:  # observer is a weakref to the actual observer observer()
                if observer() is None:
                    deadObservers.append(observer)
                    continue
                if modifier != observer():
                    try:
                        if hasattr(observer(), 'updated'):
                            #  calls directly the updated method of the observer if it exists
                            observer().updated(self, property, value)
                    except:
                        print "An error occured when notifying observer %s." % str(observer())
                        print sys.exc_info()
                        raise
            for deadObserver in deadObservers:
                del self._observers[self._observers.index(deadObserver)]
            self.isNotifying = False
        except:
            print sys.exc_info()
            raise
        finally:
            self.isNotifying = False


class Observer:
    """
      This class is part of a Subject-Observer communication system between objects.
      The subject manage a list of observers, and can notify to all of them some messages of the form: property, value.
      The notification is actually a direct call of the observer method observer.updated(self,property,value),
        where self indicates ot the observer the subject sending the message.
      The updated method is to be overriden in each particular class deriving from Observer, in order to react properly to a notification.
    """

    def __init__(self):
        pass

    def updated(self, subject=None, property=None, value=None):
        pass


class Dispatcher(Subject):
    """
    The Dispatcher is a dedicated observer that receives only specific messages.
    Each of these specific messages always indicates a particular method to run and its arguments, and optionally a callback method.
    The Dispatcher does not derive from the observer class and has no updated method.
    It manages a queue of received messages that are FIFO processed.
    The processing consists in
      1) running the specified method,
      2) notifies the result
      3) calling the callback method with the result as parameter, if requested.
        (a typically callback method is a method from the notifying subject)
    Note that both the notifyer and the dispatcher are Subject instances, and that the notifyer has not to be an Observer if it uses callbacks,
    but can be an Observer if it uses Dispatcher's notifications.
    """

    def __init__(self):
        Subject.__init__(self)
        self._currentId = 0
        self.queue = []
        self._stopDispatcher = False

    def clearQueue(self):
        """ Dispatcher method clearing the notifications queue."""
        self.queue = []

    def stop(self):
        """ Dispatcher method that disables notifications and clears notifications queue."""
        self._stopDispatcher = True
        self.clearQueue()

    def unstop(self):
        """ Dispatcher method enabling notifications."""
        self._stopDispatcher = False

    def stopped(self):
        """
        Dispatcher method that returns True (False) if notifications are disabled (enabled).
        """
        return self._stopDispatcher

    def dispatch(self, command, *args, **kwargs):
        """
        Dispatcher method that dispatches a command to a subject that will notify when  the command is executed (no callback is requested).
        """
        self.queue.insert(0, [self._currentId, command, None, args, kwargs]
                          )     # insert message in queue with callback=None
        # increment message index
        self._currentId += 1
        # and enable processing
        self._stopDispatcher = False

    def dispatchCB(self, command, callback, *args, **kwargs):
        """
        Dispatcher method that dispatches a command with callback.
        """
        self.queue.insert(0, [self._currentId, command, callback,
                              args, kwargs])  # insert message in queue with a callback
        # increment message index
        self._currentId += 1
        # and enable processing
        self._stopDispatcher = False

    def processQueue(self):
        """
        Dispatcher method that processes all message queued by
          1) calling the specified local methods with passed parameter,
          2) notifying the method name and its result,
          3) calling back the sunjectif requested.
        """
        start = time.time()  # start a timer
        # queue is empty => return
        if len(self.queue) == 0:
            return
        while len(self.queue) > 0:
            # pop a message from the queue
            (dispatchId, command, callback, args, kwargs) = self.queue.pop()
            mname = command
            # if the method name specified in the message is an existing method
            if hasattr(self, mname):
                method = getattr(self, mname)
                if DEBUG:
                    print mname, method, args, kwargs
                # run it and get the result
                result = method(*args, **kwargs)
                # notify the name of the method run and its result (this is
                # different from callback)
                self.notify(command, result)
                if callback is not None:
                    # this is the callback call
                    callback(dispatchId, result)
            else:
                # the method name does not correspond to an existing method =>
                # error
                self.error()
        # calculate total duration of queue processing
        elapsed = (time.time() - start)

    def error(self):
        """
        Dispatcher method called in case a method name sent does not correspond to an existing method.
        """
        return None

    def queued(self, ID):
        """
        Test whether a message with specific ID is present somewhere in the queue.
        """
        for entry in self.queue:
            if entry[0] == ID:
                return True
        return False

    def pong(self):
        """
        Dispatcher method to be called to verify that the dispatcher answers.
        """
        return True


class ThreadedDispatcher(Dispatcher, KillableThread):
    """
    Dispatcher class that runs in a killable thread.
    """

    def __init__(self):
        Dispatcher.__init__(self)
        KillableThread.__init__(self)

    def restart(self):
        if self.isAlive():
            return
        KillableThread.__init__(self)
        self.start()

    def run(self):
        self.processQueue()

    def dispatchCB(self, command, callback, *args, **kwargs):
        Dispatcher.dispatchCB(self, command, callback, *args, **kwargs)
        if not self.isAlive():
            self.restart()

    def dispatch(self, command, *args, **kwargs):
        Dispatcher.dispatch(self, command, *args, **kwargs)
        if not self.isAlive():
            self.restart()

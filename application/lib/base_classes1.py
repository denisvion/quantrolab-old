"""
This module defines several important abstract classes.
  - Singleton(object): Only one instance of this class can exist in Python memory.
  - Reloadable(object): An instance of this class can reload and evaluate the module it is originating from, and update itself.
"""

DEBUG = False

import threading,time,ctypes,timeit,sys,copy,weakref

class Singleton(object):
  """
  A class deriving from this abstract class can have only one instance in Python memory.
  """
  _instance = None
  
  def delete(self):
    _instance = None
          
  def __new__(cls, *args, **kwargs):
      if not cls._instance:
          cls._instance = super(Singleton, cls).__new__(cls)
      return cls._instance

class Reloadable(object):
  """
  An instance deriving from this class can reload and evaluate the module it is originating from, and update itself.
  """
  #This function dynamically reloads the module that defines the class and updates the current instance to the new class.
  def reloadClass(self):
    self.beforeReload()
    print "Reloading %s" % self.__module__
    newModule = reload(sys.modules[self.__module__])
    self.__class__ = eval("newModule.%s" % self.__class__.__name__)
    self.onReload()
    
  def beforeReload(self,*args,**kwargs):
    pass
    
  def onReload(self,*args,**kwargs):
    pass
    
  def __init__(self):
    pass

class Debugger:
  """
  Class Debugger.
  Allows to set a derived class in debugging mode so that it prints messages using debugPrint()
  """
  def __init__(self):
    self._debugging = False

  def debugOn(self):
    self._debugging = True

  def debugOff(self):
    self._debugging = False
    
  def isDebugOn(self):
    return self._debugging

  def debugPrint(self,*args):
    if self._debugging:
      for arg in args: print arg,
      print

class StopThread(Exception):
    pass
 
def _async_raise(tid, excobj):
    """
    Function called to kill a KillableThread.
    """
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(excobj))
    if res == 0:
        raise ValueError("nonexistent thread id")
    elif res > 1:
        # """if it returns a number greater than one, you're in trouble, 
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)
        raise SystemError("PyThreadState_SetAsyncExc failed")

class KillableThread(threading.Thread):
    """
    Thread that can be killed by raising an exception.
    """
    def raise_exc(self, excobj):
      """
      Overriden method of the Thread class, called when an exception is raised
      """
      assert self.isAlive(), "thread must be started" # if thread is not alive, raise the error "thread must be started"
      for tid, tobj in threading._active.items():     # otherwise 
          if tobj is self:
              _async_raise(tid, excobj)               # propagate the exception
              return    
      # the thread was alive when we entered the loop, but was not found 
      # in the dict, hence it must have been already terminated. should we raise
      # an exception here? silently ignore?
    
    def terminate(self):
      self.raise_exc(SystemExit)



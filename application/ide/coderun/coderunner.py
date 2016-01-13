
"""
This module is the engine that runs and stops pieces of codes in different threads, and manage exceptions.
It is based on the 'multiprocessing' and 'threading' python libraries with
subclassed Process(es) and Thread(s).
More precisely, the top manager is MultiProcessCodeRunner, which runs a CodeProcess, which runs a CodeRunner,
starting several CodeThreads derived from KillableThread derived from threading.Thread.

Relevant documention is:
https://docs.python.org/2.7/library/threading.html
https://docs.python.org/2.7/library/multiprocessing.html
"""
######################################
#  IMPORTS                           #
######################################

import os,os.path
import sys
import time
import traceback

# import numpy # does not seem to be used
import threading
from multiprocessing import *        # Process and Queue will be used

from application.lib.base_classes1 import KillableThread,Reloadable,StopThread
from application.lib.com_classes import Subject
from threading import RLock

######################################
#  Specific module reloading         #
######################################

import __builtin__

_importFunction = __builtin__.__import__
_moduleDates = dict()

def _autoReloadImport(name,*a,**ka):
  global _importFunction
  global _moduleDates
  if name in sys.modules:
    m = sys.modules[name]
    if hasattr(m,'__file__'):
      filename = m.__file__
      if filename[-4:] == ".pyc":
        filename = filename[:-1]
      if filename[-3:] == ".py":
        mtime = os.path.getmtime(filename)
        if filename in _moduleDates:
          if mtime > _moduleDates[filename]:
            reload(m)
        _moduleDates[filename] = mtime
  return _importFunction(name,*a,**ka)

def enableModuleAutoReload():
  """
  Enables the automatic reloading of modules when issuing an "import" statement. This is done by replacing the builtin
  import function (__builtin__.__import__) with a function that checks if the module file has changed since
  the last import and if yes reloads it before passing the function call to the original import function.
  """
  __builtin__.__import__ = _autoReloadImport

def disableModuleAutoReload():
  """
  Disables the automatic reloading of modules when issuing an "import" statement.
  """
  __builtin__.__import__ = _importFunction

#def _ide():
#  return IDE # ??? does not seem to mean anything ???

#############################################################################
#  Classes CodeThread, CodeRunner, CodeProces, and MultiProcessCodeRunner   #
#############################################################################


class CodeThread (KillableThread):

  """
  A class representing a thread in which code is executed.
  Instances of this class are created by the CodeRunner class.
  """

  def __init__(self,code,gv = dict(),lv = dict(),callback = None,filename = "<my string>"):
    """
    Initializes the class with a given code string, a global and local variables dictionary,
    an optional callback function which is called when the code execution finishes and a filename
    of the code that is going to be executed and which will be displayed in a stack trace.
    """
    KillableThread.__init__(self)
    self._gv = gv
    #self._gv['from_CodeThread']=4 # test to be deleted
    self._lv = lv
    self._filename = filename
    self._failed = False
    self._callback = callback
    self._code = code
    self._stop = False
    self._restart = True
    self._isBusy = False

  def code(self):
    """
    Returns the code string that is executed by the class.
    """
    return self._code

  def filename(self):
    """
    Returns the filename of the code that is executed by the class.
    """
    return self._filename

  def isRunning(self):
    """
    Returns True if the class is executing code.
    """
    return self._isBusy and self.isAlive()

  def failed(self):
    """
    Returns True if the code execution terminated with an exception.
    """
    return self._failed

  def executeCode(self,code,filename = "<my string>"):
    """
    Executes a code string with a given filename.
    """
    if self.isRunning():
      raise Exception("Thread is already executing code!")
    self._code = code
    self._filename = filename
    self._restart = True

  def exceptionInfo(self):
    """
    Returns the exception type and value thrown by the code thread, or None if the thread exited normally.
    """
    if self.failed() == False:
      return None
    return (self._exception_type,self._exception_value)

  def tracebackInfo(self):
    """
    Returns the traceback thrown by the code thread, or None if the thread exited normally.
    """
    if self.failed() == False:
        return None
    return self._traceback

  def stop(self):
    """
    Stops the code thread.
    """
    self._stop = True

  def run(self):
    while not self._stop:
      if self._restart:
        try:
          self._isBusy = True
          self._failed = False
          code = compile(self._code,self._filename,'exec')
          exec(code,self._gv,self._lv)
        except StopThread:
          break
        except:
          self._failed = True
          exc_type, exc_value, exc_traceback = sys.exc_info()
          self._exception_type = exc_type
          self._exception_value = exc_value
          self._traceback = exc_traceback
          raise
        finally:
          self._restart = False
          self._isBusy = False
          if not self._callback is None:
            self._callback(self)
      else:
        time.sleep(0.5)

class CodeRunner(Reloadable,Subject):

  """
  A class that manages the execution of different pieces of code in different threads (of type CodeThread),
  in a single Process (of type CodeProcess)
  """
  _id = 0

  def getId(self):
    """
    Returns a new unique ID which can be used to identify a code thread.
    """
    print "in getId"
    CodeRunner._id+=1
    return CodeRunner._id

  def __init__(self,gv = dict(),lv = dict()):
    #print 'in  CodeRunner._init with self = ',self
    Reloadable.__init__(self)
    Subject.__init__(self)
    self._threadID = 0
    self.clear(gv,lv)

  def clear(self,gv = dict(),lv = dict()):
    """
    Reinitializes the class by
      - deleting all running threads,
      - setting the global variables to the passed parameter,
      - clearing the local variables.
    """
    self._gv = gv
    self._lv = dict()
    self._threads = {}
    self._exceptions = {}
    self._tracebacks = {}

  def gv(self):
    """
    Returns the global variables dictionary.
    """
    return self._gv

  def processVar(self,varname):
    """
    Returns a variable from the global variable dictionary, provided it can be pickled (otherwise return None).
    """
    if varname in self._gv:
      return self._gv[varname]
    else:
      return None

  def lv(self):
    """
    Returns the local variables dictionary.
    """
    return self._lv

  def currentWorkingDirectory(self):
    """
    Returns the current working directory.
    """
    return os.getcwd()

  def setCurrentWorkingDirectory(self,directory):
    """
    Changes the current working directoy.
    """
    os.chdir(directory)

  def clearExceptions(self):
    """
    Clears all exceptions that are stored in the exception dictionary.
    """
    self._exceptions = {}

  def getException(self,identifier):
    """
    Returns the exception thrown by the code thread with the given identifier, or None if no exception is present.
    """
    if identifier in self._exceptions:
      return self._exceptions[identifier]
    return None

  def getTraceback(self,identifier):
    """
    Returns the traceback thrown by the code thread with the given identifier, or None if no traceback is present.
    """
    if identifier in self._tracebacks:
      return traceback.extract_tb(self._tracebacks[identifier])
    return None

  def formatException(self,identifier):
    """
    Returns a formatted exception string for the given identifier, or an empty string if no exception is available.
    """
    exc = self.exception(identifier)
    tb = self.traceback(identifier)
    if exc is None:
      return ""
    return traceback.format_exception(exc[0],exc[1],tb)

  def _threadCallback(self,thread):
    """
    A callback function which gets called when a code thread finishes the execution of a piece of code.
    """
    lock = RLock()
    lock.acquire()
    if thread.failed():
      self._exceptions[thread._id] = thread.exceptionInfo()
      self._tracebacks[thread._id] = thread.tracebackInfo()
    lock.release()
    #identifier=next(i for i in self._threads if self._threads[i].name == thread.name)

  def hasFailed(self,identifier):
    """
    Returns True if the thread with the given identifier has terminated abnormally.
    """
    if identifier in self._threads:
      return self._threads[identifier].failed()
    return False

  def isExecutingCode(self,identifier = None):
    """
    Returns True if the thread with the given identifier exists and is currently executing code,
    or if any thread is running if identifier is None.
    """
    if identifier is None:
      for thread in self._threads.values():
        if thread.isRunning():
          return True
      return False
    if not identifier in self._threads:
      return False
    if self._threads[identifier] is None:
      return False
    return self._threads[identifier].isRunning()

  def stopExecution(self,identifier):
    """
    Stops the execution of code in the thread with the given identifier by asynchronously raising a special exception in the thread.
    """
    if not self.isExecutingCode(identifier):
      return
    if not identifier in self._threads:
      return
    self._threads[identifier].terminate()

  def status(self):
    """
    Returns a dictionary containing information on all threads that are managed by the code runner.
    """
    status = {}
    for identifier in self._threads:
      status[identifier] = dict()
      status[identifier]["isRunning"] = self.isExecutingCode(identifier)
      status[identifier]["filename"] = self._threads[identifier].filename()
      status[identifier]["failed"] = self._threads[identifier].failed()
    return status

  def executeCode(self,code,identifier,filename = None, lv = None,gv = None):
    """
    Executes a code string in an existing or new thread,
    with a given identifier, filename and local and global variable dictionaries.
    """
    #print 'in CodeRunner.executeCode with codeRunner = ',self
    if self.isExecutingCode(identifier):    # Raises exception if trying to run an existing thread that is executing code
      raise Exception("Code thread %s is busy!" % identifier)
    if lv is None:                          # creates the local variable dictionary for the thread if not passed
      if not identifier in self._lv:
        self._lv[identifier] = dict()
      lv = self._lv[identifier]
    if gv is None:                          # sets the global variable dictionary for the thread to the one known by the CodeRunner
      gv = self._gv
    if identifier in self._threads and self._threads[identifier].isAlive():
      ct = self._threads[identifier]        # if a thread with that identifier exists and is alive
      ct.executeCode(code,filename)         #   use it to execute the passed piece of code
    else:                                   # otherwise initiate a new thread
      ct = self.createThread(code,identifier,filename,gv,lv)
    return ct._id                           #  returns the thread ID.

  def createThread(self,code,identifier,filename,gv,lv): # separated from execute code by dv in Jan 2016
    """
    Creates and starts a codeThead with a given identifer and returns it.
    Use with care !!!
    """
    class GlobalVariables:
      """
      The GlobalVariable class encapsulates a global variable dictionnary and a reference to the __coderunner__.
      It allows users to get or set a variable a with syntax gv.a instead of gv['a'].
      """
      def __init__(self,gv,__coderunner__=None):
        self.__dict__ = gv
        self.__coderunner__=__coderunner__

      def __setitem__(self,key,value):
        setattr(self,key,value)

      def __getitem__(self,key):
        return getattr(self,key)

    gv1 = GlobalVariables(gv,self)        #   - creating a GlobalVariables instance encapsulating the global variable dictionary gv
    lv["gv"] = gv1                        #   - making this GlobalVariables accessible by gv in the local variable namespace
    lv["__file__"] = filename             #   - making the filename the code is originating from, available as a local variable _filename

    ct = CodeThread(code,filename = filename,lv = lv,gv = lv,callback = self._threadCallback)
    ct._id = self._threadID               #   - instantiating a CodeThread with the passed or prepared variables
    self._threadID+=1                     #   - setting the thread ID
    self._threads[identifier] = ct        #   - adding the thread to the thread dictionary self._threads
    ct.setDaemon(True)
    ct.start()                            #   - calling the start method of threading.Thread to run the piece of code in its thread.
    return ct

  def deleteThread(self,identifier):
    """
    Exit and deletes a codeThead with a given identifer and returns True if deletion could be done.
    Use with care !!!
    """
    if identifier in self._threads:
      ct = self._threads[identifier]
      del self._threads[identifier]
      del ct
      return True
    return False

class CodeProcess(Process):
  """
  A process which runs an instance of CodeRunner and communicates through queues with parent processes.
  This class is used by the MultiProcessCodeRunner class.
  It subclasses Process from the multiprocessing python library and adds several queues for commands, responses,
  inputs, outputs, and errors.
  This implementation of Process does not use the simple target strategy;
    instead, it uses a command queue managed by the overriden function run().
  """

  class StreamProxy(object):

    def __getattr__(self,attr):
      if hasattr(self._queue,attr):
        return getattr(self._queue,attr)
      else:
        raise KeyError("No such attribute: %s" %attr)

    def __init__(self,queue):
      self._queue = queue

    def flush(self):
      pass

    def write(self,output):
      #while(self._reading):
      #  time.sleep(0.05)
      self._writing=True
      self._queue.put(output)
      self._writing=False

    def read(self,blocking = True):
      return self._queue.get(blocking)

  def __init__(self,gv = dict(),lv = dict()): # gv and lv added by DV in May 2015
    Process.__init__(self)                    # instantiate the Process
    #print 'in CodeProcess.__init__ calling self._codeRunner = CodeRunner(gv)'
    self._gv,self._lv=gv,lv                   # (added by DV in May 2015)
    self._gv['from_CodeProcess']=3  # test to be deleted
    print self._gv
    self.daemon = True                        # Daemon threads can be abruptly stopped at shutdown
    self._commandQueue = Queue()              # Command queue (Queue is a class of the multiprocessing library)
    self._responseQueue = Queue()             # response queue
    self._stdoutQueue = Queue()               # output queue
    self._stderrQueue = Queue()               # error queue
    self._stdinQueue = Queue()                # input Queue
    self._codeRunner = CodeRunner(self._gv)           # (Note that only a copy of the CodeRunner created here (i.e. in main application thread)
                                              # will be available in the children threads of the Process )

  def stdoutProxy(self):
    return self.StreamProxy(self._stdoutQueue)

  def stderrProxy(self):
    return self.StreamProxy(self._stderrQueue)

  def commandQueue(self):
    #print 'in CodeProcess.commandQueue with self._codeRunner = ',self._codeRunner
    return self._commandQueue

  def responseQueue(self):
    return self._responseQueue

  def stdinQueue(self):
    return self._stdinQueue

  def stdoutQueue(self):
    return self._stdoutQueue

  def stderrQueue(self):
    return self._stderrQueue

  def run(self):
    """
    This run method starts the code process infinite loop. It subclasses the Process.run() method of 'multiprocessing'
    and is automatically called by the Process.start() method of 'multiprocessing'.
    """
    print "New code process is up and running ... "
    sys.stderr = self.StreamProxy(self._stderrQueue)
    sys.stdout = self.StreamProxy(self._stdoutQueue)
    sys.stdin = self.StreamProxy(self._stdinQueue)
    while True:                                         # infinite loop
      time.sleep(0.1)                                   #   every 0.1s
      try:                                              #   try to process the commandQueue while it is not empty
        while not self.commandQueue().empty():          #   until a command is stop or an keybord interupt occurs
          (command,args,kwargs) = self.commandQueue().get(False)
          if command == "stop":
            exit(0)
          if hasattr(self._codeRunner,command):         # simply ignore commands unknown from coderunner
            try:
              f = getattr(self._codeRunner,command)     #   build the command call
              r = f(*args,**kwargs)                     #   run it and get a result
              self.responseQueue().put(r,False)         #   and response got here
            except Exception as e:
              traceback.print_exc()
      except KeyboardInterrupt:
        print "Interrupt, exiting..."


class MultiProcessCodeRunner():
  """
  The MultiProcessCodeRunner encapsulates a CodeProcess (which runs a CodeRunner) and adds error and stdout queue managagement functions.
  (It is not clear why it does not simply subclass CodeProcess.)
  Any call to an unknown attribute is transformed into a message dispatched to the code process command queue;
  a possible response can be retrieved (if available before timeout) and returned.
  """

  def __init__(self,gv = dict(),lv = dict(),logProxy=lambda x:False,errorProxy=lambda x:False):
    self._gv,self._lv=gv,lv                  # added by DV in may 2015 to get a handle to global variables for a possible code process restart
    self._gv['from_MultiProcessCodeRunner']=2 # test to be deleted
    print self._gv
    self._codeProcess = CodeProcess(gv=gv)   # Process exists but is not started yet (gv added by DV in May 2015)
    self._codeProcess.start()                # Start the Process that will call the Process.run() method
    self._timeout = 2
    self._stdoutQueue=self._codeProcess.stdoutQueue()  # make the Process' queues attributes of MultiProcessCodeRunner
    self._stderrQueue=self._codeProcess.stderrQueue()
    self._stdoutProxy=self._codeProcess.stdoutProxy()
    self._stderrProxy=self._codeProcess.stderrProxy()

  def __del__(self):
    """ Destructor"""
    self.terminate()

  def terminate(self):
    """ Terminates the associated CodeProcess."""
    if self._codeProcess.is_alive():
      self._codeProcess.terminate()

  def stderrQueue(self):
    """
    Returns the error queue of the code process.
    """
    return self._stderrQueue

  def stdoutQueue(self):
    """
    Returns the output queue of the code process.
    """
    return self._stdoutQueue

  def setTimeout(self,timeout):
    """
    Sets the timeout duration.
    """
    self._timeout = timeout

  def timeout(self):
    """
    Gets the timeout duration.
    """
    return self._timeout

  def _clearQueue(self,queue):
    """
    Clears any queue passed to the method.
    """
    while True:
      try:
        queue.get(False)
      except:
        break

  def stdin(self,input):
    """
    Puts any input in the input queue of the associated CodeProcess.
    """
    self._codeProcess.stdinQueue().put(input,False)

  def hasStdout(self):
    return not self._codeProcess.stdoutQueue().empty()

  def _readFromQueueWithTimeout(self,queue,timeout):
    """
    Reads from any queue of the associated CodeProcess'.
    """
    string = ""
    start = time.clock()
    while not queue.empty():
      string+=queue.get(False)
      if time.clock()-start > timeout:
        break
    return string

  def stdout(self,timeout = 0.5):
    """
    Reads any output from the output queue of the associated CodeProcess' output queue.
    """
    return self._readFromQueueWithTimeout(self._codeProcess.stdoutQueue(),timeout)

  def hasStderr(self):
    """
    Reads True if the error queue of the associated CodeProcess contains at least one error.
    """
    return not self._codeProcess.stderrQueue().empty()

  def stderr(self,timeout = 0.5):
    return self._readFromQueueWithTimeout(self._codeProcess.stderrQueue(),timeout)

  def codeProcess(self):
    """
    Returns the associated CodeProcess.
    """
    return self._codeProcess

  def stop(self):
    """
    Stops the associated CodeProcess.
    """
    self._codeProcess.commandQueue().put(("stop",[],{}),False)

  def start(self):
    """
    Starts or restarts the associated CodeProcess.
    """
    #print 'in  MultiProcessCodeRunner.start with self=',self
    if self._codeProcess.is_alive():
      self.restart()
    else:
      self._codeProcess.start()

  def restart(self):
    """
    Terminate and restarts the associated CodeProcess with the same global variables.
    """
    print "Restarting code runner..."
    self._codeProcess.terminate()
    self._codeProcess = CodeProcess(gv=self._gv)
    self._codeProcess.start()

  def dispatch(self,command,*args,**kwargs):
    """
    This dispatch method is used to transform a command unknown by MultiProcessCodeRunner into a message
    put in the codeProcess' command queue.
    If a reponse from the responseQueue is returned before timeout, it is returned by dispatch.
    Like this a MultiProcessCodeRunner.command(*args,**kwargs) becomes self._codeProcess.commandQueue().put((command,args,kwargs),False).
    """
    message = (command,args,kwargs)
    if not self._codeProcess.is_alive():
      self.restart()
    self._clearQueue(self._codeProcess.commandQueue())
    self._clearQueue(self._codeProcess.responseQueue())
    self._codeProcess.commandQueue().put(message,False)
    try:
      response = self._codeProcess.responseQueue().get(True,timeout = self.timeout())
    except:
      response = None
    return response

  def __getattr__(self,attr):
    return lambda *args,**kwargs: self.dispatch(attr,*args,**kwargs)

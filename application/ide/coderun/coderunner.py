
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

import os
import os.path
import sys
import time
import traceback

import threading
from threading import RLock
from multiprocessing import Process, Queue        # Process and Queue will be used

from application.lib.base_classes1 import KillableThread, Reloadable, StopThread
from application.lib.com_classes import Subject

######################################
#  Specific module reloading         #
######################################

import __builtin__

_importFunction = __builtin__.__import__
_moduleDates = dict()


def _autoReloadImport(name, *a, **ka):
    global _importFunction
    global _moduleDates
    if name in sys.modules:
        m = sys.modules[name]
        if hasattr(m, '__file__'):
            filename = m.__file__
            if filename[-4:] == ".pyc":
                filename = filename[:-1]
            if filename[-3:] == ".py":
                mtime = os.path.getmtime(filename)
                if filename in _moduleDates:
                    if mtime > _moduleDates[filename]:
                        reload(m)
                _moduleDates[filename] = mtime
    return _importFunction(name, *a, **ka)


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


#############################################################################
#  Classes CodeThread, CodeRunner, CodeProces, and MultiProcessCodeRunner   #
#############################################################################


class CodeThread (KillableThread):

    """
    A class representing a thread in which code is executed (instances are created by the CodeRunner class.)
    A CodeThread has a given code string, a global and a local variables dictionary,
    an optional callback function called when the code execution finishes,
    and a filename of the code to be displayed in a stack trace.
    Because CodeThread subclasses KillableThread, it can be stopped by calling its terminate() method.
    """

    def __init__(self, code, gv=dict(), lv=dict(), callback=None, filename="<my string>"):
        """
        Initializes the class.
        """
        KillableThread.__init__(self)
        self._gv, self._lv = gv, lv
        self._code, self._callback, self._filename = code, callback, filename
        self._failed, self._stop, self._isBusy, self._restart = False, False, False, True
        # self._traceback, self._exception_type, self._exception_value = None, None, None # created on error only
        # self._gv['from_CodeThread']=4 # for debug

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

    def executeCode(self, code, filename="<my string>"):
        """
        Executes a code string with a given filename.
        """
        if self.isRunning():
            raise Exception("Thread is already executing code!")
        self._code, self._filename, self._restart = code, filename, True

    def exceptionInfo(self):
        """
        Returns the exception type and value thrown by the code thread, or None if the thread exited normally.
        """
        if not self.failed():
            return None
        return (self._exception_type, self._exception_value)

    def tracebackInfo(self):
        """
        Returns the traceback thrown by the code thread, or None if the thread exited normally.
        """
        if not self.failed():
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
                    self._isBusy, self._failed = True, False
                    code = compile(self._code, self._filename, 'exec')
                    exec(code, self._gv, self._lv)
                except StopThread:
                    break
                except:
                    self._failed = True
                    self._exception_type, self._exception_value, self._traceback = sys.exc_info()
                    raise
                finally:
                    self._restart, self._isBusy = False, False
                    if self._callback is not None:
                        self._callback(self)
            else:
                time.sleep(0.5)


class CodeRunner(Reloadable, Subject):

    """
    A class that manages the execution of different pieces of code in different threads (of type CodeThread),
    in a single Process (of type CodeProcess)
    """
    _id = 0  # Declared outside init so that identifiers continue to be incremented after reloading the coderunner ?

    def getId(self):
        """
        Returns a new unique ID which can be used to identify a code thread.
        """
        # print "in getId"
        CodeRunner._id += 1
        return CodeRunner._id

    def __init__(self, gv=dict(), lv=dict()):
        # print 'in  CodeRunner._init with self = ',self
        Reloadable.__init__(self)
        Subject.__init__(self)
        self._threadID = 0
        self.clear(gv, lv)
        print '\n process running CodeRunner is', os.getpid()
        print '\n id(CodeRunner._gv)=', id(self._gv)

    def clear(self, gv=dict(), lv=dict()):
        """
        Reinitializes the class by
          - deleting all running threads,
          - setting the global variables to the passed parameter,
          - clearing the local variables.
        """
        self._gv, self._lv = gv, dict()
        self._threads, self._exceptions, self._tracebacks = {}, {}, {}

    def gv(self):
        """
        Returns the global variables dictionary.
        """
        return self._gv

    def processVar(self, varname):
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

    def setCurrentWorkingDirectory(self, directory):
        """
        Changes the current working directoy.
        """
        os.chdir(directory)

    def clearExceptions(self):
        """
        Clears all exceptions that are stored in the exception dictionary.
        """
        self._exceptions = {}

    def getException(self, identifier):
        """
        Returns the exception thrown by the code thread with the given identifier, or None if no exception is present.
        """
        if identifier in self._exceptions:
            return self._exceptions[identifier]
        return None

    def getTraceback(self, identifier):
        """
        Returns the traceback thrown by the code thread with the given identifier, or None if no traceback is present.
        """
        if identifier in self._tracebacks:
            return traceback.extract_tb(self._tracebacks[identifier])
        return None

    def formatException(self, identifier):
        """
        Returns a formatted exception string for the given identifier, or an empty string if no exception is available.
        """
        exc = self.exception(identifier)
        if exc is None:
            return ''
        return traceback.format_exception(exc[0], exc[1], self.traceback(identifier))

    def _threadCallback(self, thread):
        """
        A callback function which gets called when a code thread finishes the execution of a piece of code.
        """
        lock = RLock()
        lock.acquire()
        if thread.failed():
            self._exceptions[thread._id] = thread.exceptionInfo()
            self._tracebacks[thread._id] = thread.tracebackInfo()
        lock.release()
        # identifier=next(i for i in self._threads if self._threads[i].name == thread.name)

    def hasFailed(self, identifier):
        """
        Returns True if the thread with the given identifier has terminated abnormally.
        """
        if identifier in self._threads:
            return self._threads[identifier].failed()
        return False

    def isExecutingCode(self, identifier=None):
        """
        Returns True if the thread with the given identifier exists and is currently executing code,
        or if any thread is running if identifier is None.
        """
        if identifier is None:
            for thread in self._threads.values():
                if thread.isRunning():
                    return True
            return False
        elif identifier not in self._threads or self._threads[identifier] is None:
            return False
        return self._threads[identifier].isRunning()

    def stopExecution(self, identifier):
        """
        Stops the code execution in the thread with the given identifier by asynchronously raising a special exception in the thread.
        """
        if not self.isExecutingCode(identifier):
            return
        if identifier not in self._threads:
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
            status[identifier]["filename"] = self._threads[
                identifier].filename()
            status[identifier]["failed"] = self._threads[identifier].failed()
        return status

    def executeCode(self, code, identifier, filename=None, lv=None, gv=None):
        """
        Executes a code string in an existing or new thread,
        with a given identifier, filename and local and global variable dictionaries.
        """
        # print 'in CodeRunner.executeCode with codeRunner = ',self
        # Raises exception if trying to run an existing thread that is executing
        # code
        if self.isExecutingCode(identifier):
            raise Exception("Code thread %s is busy!" % identifier)
        if lv is None:                          # creates the local variable dictionary for the thread if not passed
            if identifier not in self._lv:
                self._lv[identifier] = dict()
            lv = self._lv[identifier]
        if gv is None:                          # sets the global variable dictionary for the thread to the one known by the CodeRunner
            gv = self._gv
        if identifier in self._threads and self._threads[identifier].isAlive():
            # if a thread with that identifier exists and is alive
            ct = self._threads[identifier]
            # use it to execute the passed piece of code
            ct.executeCode(code, filename)
        else:                                   # otherwise initiate a new thread
            ct = self.createThread(code, identifier, filename, gv, lv)
        return ct._id  # returns the thread ID.

    # separated from execute code by dv in Jan 2016
    def createThread(self, code, identifier, filename, gv, lv):
        """
        Creates and executes a codeThread with a given identifer and returns the created codeThread instance.
        Use with care !!!
        """
        class GlobalVariables:
            """
            The GlobalVariable class is a handle to a global variable dictionary with a reference to the __coderunner__
            in the dictionnary itself. It is not a copy of the passed dictionary.
            It allows users to get or set a variable var using the syntax gv.var instead of gv['var'].
            """

            def __init__(self, gv, __coderunner__=None):
                # the dictionary of properties of the object becomes the passed
                # dictionary gv
                self.__dict__ = gv
                self.__coderunner__ = __coderunner__    # the coderunner property is added to (or overwritten in) gv

            def __setitem__(self, key, value):
                setattr(self, key, value)

            def __getitem__(self, key):
                return getattr(self, key)

        # - making the GlobalVariables handle to gv accessible by 'gv' in the local variable namespace
        lv['gv'] = GlobalVariables(gv, self)
        # - making the filename the code is originating from, available as a local variable _filename
        lv['__file__'] = filename
        ct = CodeThread(code, filename=filename, lv=lv, gv=lv, callback=self._threadCallback)
        # - instantiating a CodeThread with the passed or prepared variables
        ct._id = self._threadID
        self._threadID += 1  # - setting the thread ID
        # - adding the thread to the thread dictionary self._threads
        self._threads[identifier] = ct
        ct.setDaemon(True)
        # - calling the start method of threading.Thread to run the piece of code in its thread.
        ct.start()
        return ct

    def deleteThread(self, identifier):
        """
        Exit and deletes a codeThread with a given identifer and returns True if deletion could be done.
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
    A process which runs an instance of CodeRunner and communicates through queues with parent process(es).
    This class is used by the MultiProcessCodeRunner class.
    It subclasses Process from the multiprocessing python library and adds several queues for commands, responses,
    inputs, outputs, and errors.
    This implementation of Process does not use the simple target strategy;
      instead, it uses a command queue managed by the overriden function run().
    """

    class StreamProxy(object):
        """
        Proxy for a Queue instance passed to init, which allows to
        to read from or write to the queue, or even get an attribute of the queue
        """
        def __getattr__(self, attr):
            if hasattr(self._queue, attr):
                return getattr(self._queue, attr)
            else:
                raise KeyError("No such attribute: %s" % attr)

        def __init__(self, queue):
            self._queue = queue

        def flush(self):
            pass

        def write(self, output):
            # while(self._reading):
            #  time.sleep(0.05)
            self._writing = True
            self._queue.put(output)
            self._writing = False

        def read(self, blocking=True):
            return self._queue.get(blocking)

    def __init__(self, gv=dict(), lv=dict()):     # gv and lv added by DV in May 2015
        Process.__init__(self)                    # instantiate the Process
        self._gv, self._lv = gv, lv
        # Daemon threads can be abruptly stopped at shutdown
        self.daemon = True
        # Setting queues (Queue is a class of the multiprocessing library)
        self._commandQueue = Queue()              # commmand queue
        self._responseQueue = Queue()             # response queue
        self._stdoutQueue = Queue()               # output queue
        self._stderrQueue = Queue()               # error queue
        self._stdinQueue = Queue()                # input Queue
        self._codeRunner = CodeRunner(self._gv)
        # (Note that only a copy of the CodeRunner created here (i.e. from the parent application process)...
        # ...will be available in the children threads of the present child process)
        # Now for debugging purpose only, message to the console of main
        # self._gv['from CodeProcess'] = 3
        # print 'Sarting CodeProcess:  ', self._gv
        print '\n process running CodeProcess is', os.getpid(), ' with os.getpid'
        print '\n CodeProcess id is ', self.pid, ' with self.pid before start'
        print '\n id(CodeProcess._gv)=', id(self._gv)

    def stdoutProxy(self):
        return self.StreamProxy(self._stdoutQueue)

    def stderrProxy(self):
        return self.StreamProxy(self._stderrQueue)

    def commandQueue(self):
        # print 'in CodeProcess.commandQueue with self._codeRunner =
        # ',self._codeRunner
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
        This run method starts the code process infinite loop.
        It subclasses the Process.run() method of 'multiprocessing'.
        It is automatically called by the Process.start() method of 'multiprocessing'.
        """
        sys.stderr = self.StreamProxy(self._stderrQueue)
        sys.stdout = self.StreamProxy(self._stdoutQueue)
        sys.stdin = self.StreamProxy(self._stdinQueue)
        print 'New code process is up and running ... '
        while True:                                         # infinite loop
            time.sleep(0.1)  # every 0.1s
            try:  # try to process the commandQueue while it is not empty
                while not self._commandQueue.empty():
                    (command, args, kwargs) = self._commandQueue.get(False)
                    if command == 'stop':
                        exit(0)
                    # until a command is stop or a keybord interupt occurs.
                    # simply ignore commands unknown from coderunner
                    if hasattr(self._codeRunner, command):
                        try:
                            # build the command call
                            f = getattr(self._codeRunner, command)
                            r = f(*args, **kwargs)  # run it, get a result
                            self._responseQueue.put(r, False)  # and put it to the response queue
                        except Exception as e:
                            traceback.print_exc()
            except KeyboardInterrupt:
                print '\t Interrupting code process and exiting...'


class MultiProcessCodeRunner():
    """
    The MultiProcessCodeRunner is designed to run sub-processes of type CodeProcess (each one running a CodeRunner),
    and adds error and stdout queue managagement functions.
    The present implemention includes only a single CodeProcess.
    Any call to an unknown attribute of MultiProcessCodeRunner is transformed into
    a message dispatched to the command queue of this single code process;
    a possible response can be retrieved (if available before timeout) and returned.
    """

    def __init__(self, gv=dict(), lv=dict(), logProxy=lambda x: False, errorProxy=lambda x: False):
        # added by DV in may 2015 to get a handle to global variables for a
        # possible code process restart
        self._gv, self._lv = gv, lv
        self._timeout = 2
        # For debugging:
        self._gv['from_MultiProcessCodeRunner'] = 2  # test to be deleted
        # print self._gv
        print '\n process running MultiProcessCodeRunner is', os.getpid()
        print '\n id(MultiProcessCodeRunner._gv)=', id(self._gv)
        self.startCodeProcess()
        print '\n CodeProcess id is ', self._codeProcess.pid, ' with self.pid after start'

    def startCodeProcess(self):
        """
        Starts the associated CodeProcess.
        """
        # Creates a single CodeProcess with global variables gv
        self._codeProcess = CodeProcess(gv=self._gv)
        # Start the Process that automatically calls the Process.run() method
        self._codeProcess.start()
        # make the Process' queues attributes of MultiProcessCodeRunner
        self._stdoutQueue = self._codeProcess.stdoutQueue()
        self._stderrQueue = self._codeProcess.stderrQueue()
        self._stdoutProxy = self._codeProcess.stdoutProxy()
        self._stderrProxy = self._codeProcess.stderrProxy()

    def restart(self):
        """
        Terminate and restarts the associated CodeProcess with the same global variables.
        """
        print "Restarting code runner..."
        self.terminate()
        self.startCodeProcess()

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

    def setTimeout(self, timeout):
        """
        Sets the timeout duration.
        """
        self._timeout = timeout

    def timeout(self):
        """
        Gets the timeout duration.
        """
        return self._timeout

    def _clearQueue(self, queue):
        """
        Clears any queue passed to the method.
        """
        while True:
            try:
                queue.get(False)
            except:
                break

    def stdin(self, input):
        """
        Puts any input in the input queue of the associated CodeProcess.
        """
        self._codeProcess.stdinQueue().put(input, False)

    def hasStdout(self):
        return not self._codeProcess.stdoutQueue().empty()

    def _readFromQueueWithTimeout(self, queue, timeout):
        """
        Reads from any queue of the associated CodeProcess'.
        """
        string = ""
        start = time.clock()
        while not queue.empty():
            string += queue.get(False)
            if time.clock() - start > timeout:
                break
        return string

    def stdout(self, timeout=0.5):
        """
        Reads any output from the output queue of the associated CodeProcess' output queue.
        """
        return self._readFromQueueWithTimeout(self._codeProcess.stdoutQueue(), timeout)

    def hasStderr(self):
        """
        Reads True if the error queue of the associated CodeProcess contains at least one error.
        """
        return not self._codeProcess.stderrQueue().empty()

    def stderr(self, timeout=0.5):
        return self._readFromQueueWithTimeout(self._codeProcess.stderrQueue(), timeout)

    def codeProcess(self):
        """
        Returns the associated CodeProcess.
        """
        return self._codeProcess

    def stop(self):
        """
        Stops the associated CodeProcess.
        """
        self._codeProcess.commandQueue().put(("stop", [], {}), False)

    def dispatch(self, command, *args, **kwargs):
        """
        This dispatch method is used to transform a command unknown by MultiProcessCodeRunner into a message
        put in the codeProcess' command queue.
        If a reponse from the responseQueue is returned before timeout, it is returned by dispatch.
        Like this a MultiProcessCodeRunner.command(*args,**kwargs) becomes self._codeProcess.commandQueue().put((command,args,kwargs),False).
        """
        message = (command, args, kwargs)
        if not self._codeProcess.is_alive():
            self.restart()
        self._clearQueue(self._codeProcess.responseQueue())
        self._codeProcess.commandQueue().put(message, False)
        try:
            response = self._codeProcess.responseQueue().get(True, timeout=self.timeout())
        except:
            response = None
        return response

    def __getattr__(self, attr):
        return lambda *args, **kwargs: self.dispatch(attr, *args, **kwargs)

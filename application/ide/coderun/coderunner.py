
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
from threading import Thread, RLock
# Process and Queue will be used
from multiprocessing import Process, Queue

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
    A CodeThread has
    - a given code string,
    - a global and a local variable dictionary,
    - an optional resultExpression string to generate a result for callback,
    - a _result attribute to store the result of resultExpression, (WARNING: only pickable results can be passed between processes)
    - an optional callback function called when the code execution finishes,
    - a name of the code to be displayed in a stack trace.
    Because CodeThread subclasses KillableThread, it can be stopped by calling its terminate() method.
    """

    def __init__(self, code, threadId=None, name='', lv=dict(), gv=dict(), resultExpression=None, callback=None):
        """
        Initializes the class and triggers the execution of the code.
        The thread can receive
            - local and global directories or initialize them as empty ones.
            - a result expression to be evaluated once after code completion
            - a handle to a callback function to be called with the result of resultExpression as parameter.
        """
        # print 'initializing CodeThread', threadId, ' with gv =', gv, ' and lv = ', lv
        KillableThread.__init__(self)
        self._gv, self._lv = gv, lv
        self._code, self._id, self._name = code, threadId, name
        self._resultExpression, self._result = resultExpression, None
        self._callback = callback
        self._failed, self._stop, self._isBusy, self._restart = False, False, False, True

    def code(self):
        """
        Returns the code string that is executed by the class.
        """
        return self._code

    def name(self):
        """
        Returns the name of the code that is executed by the class.
        """
        return self._name

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

    def executeCode(self, code, name='', resultExpression=None):
        """
        Triggers the execution of a new code string and optional result expression string with a given name.
        """
        if self.isRunning():
            raise Exception("Thread is already executing code!")
        self._code, self._resultExpression, self._result, self._name, self._restart = code, resultExpression, None, name, True

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
        """
        Infinite loop waiting for self._restart = True, which then
        - compiles and runs self._code,
        - runs self._resultExpression if defined and puts the result in self._result
        - calls back self._callback(self, self._result) if self._callback is defined
        In case of errors, propagates the exception and traceback.
        """
        while not self._stop:
            if self._restart:
                try:
                    self._isBusy, self._failed = True, False
                    self._result, self._lv['_resultThread'] = None, None
                    code = compile(self._code, self._name, 'exec')
                    # print "entering executecode-run with gv = ", self._gv, " and lv = ", self._lv
                    exec(code, self._gv, self._lv)
                    if self._resultExpression is not None:
                        code = compile('_resultThread =' + self._resultExpression, self._name, 'exec')
                        exec(code, self._gv, self._lv)
                        self._result = self._lv['_resultThread']
                    # print "exiting executecode-run with gv = ", self._gv, " and lv = ", self._lv
                except StopThread:
                    break
                except:
                    self._failed = True
                    self._exception_type, self._exception_value, self._traceback = sys.exc_info()
                    raise
                finally:
                    self._restart, self._isBusy = False, False
                    if self._callback is not None:
                        self._callback(self, result=self._result)
            else:
                time.sleep(0.5)


class CodeRunner(Reloadable, Subject):

    """
    A class that manages the execution of different pieces of code in different threads of type CodeThread
    (in a single process).
    The coderunner has the following dicitonnaries:
        - a global and local variables dictionary,
        - a dictionary for the managed threads,
        - a dictionary for the exceptions,
        - a dictionary for the tracebacks.
    The coderunner passes its private _threadCallback function to each thread, the function being called each time the thread
    finishes executing a piece of code, with the optional result generated by the thread as an argument;
    if a callbackQueue has been passed to the coderunner, the _threadCallback function pushes to the queue the tupple
    (threadId, failed, result) with the optional result generated by the thread .
    WARNING: only pickable results can be passed between processes.
    The coderunner has the following public methods:
        - executeCode(code, threadId, name=None, lv=None, gv=None) to execute code in an existing or new thread;
        - stopExecution(threadId) to stop an existing thread;
        - isExecutingCode(threadId) to knwon whether a thread is currently running;
        - hasFailed(threadId) to knwon whether a thread has failed;
        - status to return Returns a dictionary with information on all managed threads;
        - gv(varname, keysOnly) to retrieve a global variable or the whole global dictionary of the codeRunner;
        - lv(varname, threadId, keysOnly) to retrieve a local variable or the whole local variable
        dictionary of a thread with id identifier;
        - getException, clearExceptions, getTraceback and formatException to manage thread errors;
    Remark about local variable dictionnaries:
        The coderunner creates the local variable dictionary for each thread as the variable threadId in its own local dictionary;
            it passes it to the thread if no other dictionary is specified.
        All threads have different GlobalVariables objects that all refer to the same global variable dictionary;
            the GlobalVariable object is stored as gv in the thread's local dictionary
    Note about geting global variables, or local variables of the threads.
        The gv and lv methods can return to a caller global variables or local variables of a CodeThread.
        However, variables have to be transferred between processes by queues or pipes => Don't call from a parent process codeProcess.codeRunner.gv()!!!
    """

    def __init__(self, gv=dict(), lv=dict(), callbackQueue=None):
        Reloadable.__init__(self)
        Subject.__init__(self)
        self._callbackQueue = callbackQueue
        self._gv, self._lv = gv, lv
        self._threads, self._exceptions, self._tracebacks = {}, {}, {}

    def _newId(self):
        """
        Returns an integer ID not already present in self._threads, which can be used to identify a code thread.
        """
        id1 = 0
        while id1 in self._threads:
            id1 += 1
        return id1

    def _varDic(self, threadId=None, varname=None, keysOnly=False, strRep=False):
        """
        Private function that returns
            a dictionary specified by threadID,
            or a variable with name varname in this dictionary,
            or an attribute of this variable in this dictionary,
            or the string representation of this variable or attribute if strRep = True.
        The dictionary is
            - coderunner's global dictionary if threadId is None,
            - the thread's local dictionary corresponding to threadId if threadId is not None.
        The returned quantity is
            - the whole dictionary if varname is None and keysOnly is False;
            - only the key(s) if varname is None and keysOnly is True;
            - the value of variable varname if varname is a simple name;
            - an attribute in the attribute tree of the variable if varname contains a dot (like 'var.attr.subattr' or 'var.attr(2,"toto")' )
            - the string representation of this variable or attribute if strRep is True (useful for non pickable result).
        Any error returns None.
        """
        if threadId is None:
            varDic = self._gv
        elif threadId in self._threads:
            varDic = self._threads[threadId]._lv
        else:
            return None
        if varname is None:
            if keysOnly:
                return varDic.keys()
            else:
                return varDic
        else:
            varnameSplit = varname.split('.', 1)
            varname0 = varnameSplit[0]
            if varname0 in varDic:
                var = varDic[varname0]
                if len(varnameSplit) == 2:
                    varname = 'var.' + varnameSplit[1]
                    exec('var = ' + varname)
                if strRep:
                    var = str(var)
                return var
            else:
                return None

    def gv(self, varname=None, keysOnly=False, strRep=False):
        """
        Public function that returns from the coderunner's global dictionary
            - the whole dictionary itself if varname is None and keysOnly is False;
            - only the key(s) if varname is None and keysOnly is True;
            - the value of variable varname if varname is a simple name;
            - an attribute of the variable if varname 'var.attr.subattr...'
            - the string representation of this variable or attribute if strRep is True (useful for non pickable result)
        Any error returns None.
        """
        return self._varDic(threadId=None, varname=varname, keysOnly=keysOnly, strRep=strRep)

    def lv(self, threadId, varname=None, keysOnly=False, strRep=False):
        """
        Public function that returns from the thread's local dictionary correponding to threadId
            - the whole dictionary itself if varname is None and keysOnly is False;
            - only the key(s) if varname is None and keysOnly is True;
            - the value of variable varname if varname is a simple name;
            - an attribute of the variable if varname 'var.attr.subattr...'
            - the string representation of this variable or attribute if strRep is True (useful for non pickable result)
        Any error returns None.
        (Note that threadId=None gives access to the global dictionary as with the method gv)
        """
        return self._varDic(threadId=threadId, varname=varname, keysOnly=keysOnly, strRep=strRep)

    def clearExceptions(self):
        """
        Clears all exceptions that are stored in the exception dictionary.
        """
        self._exceptions = {}

    def getException(self, threadId):
        """
        Returns the exception thrown by the code thread with the given identifier, or None if no exception is present.
        """
        if threadId in self._exceptions:
            return self._exceptions[threadId]
        return None

    def getTraceback(self, threadId):
        """
        Returns the traceback thrown by the code thread with the given identifier, or None if no traceback is present.
        """
        if threadId in self._tracebacks:
            return traceback.extract_tb(self._tracebacks[threadId])
        return None

    def formatException(self, threadId):
        """
        Returns a formatted exception string for the given identifier, or an empty string if no exception is available.
        """
        exc = self.exception(threadId)
        if exc is None:
            return ''
        return traceback.format_exception(exc[0], exc[1], self.traceback(threadId))

    def hasFailed(self, threadId):
        """
        Returns True if the thread with the given identifier has terminated abnormally.
        """
        if threadId in self._threads:
            return self._threads[threadId].failed()
        return False

    def isExecutingCode(self, threadId=None):
        """
        Returns True if the thread with the given identifier exists and is currently executing code,
        or if any thread is running if identifier is None.
        """
        if threadId is None:
            for thread in self._threads.values():
                if thread.isRunning():
                    return True
            return False
        elif threadId not in self._threads or self._threads[threadId] is None:
            return False
        return self._threads[threadId].isRunning()

    def stopExecution(self, threadId):
        """
        Stops the code execution in the thread with the given identifier by asynchronously raising a special exception in the thread.
        """
        if not self.isExecutingCode(threadId):
            print 'thread is already stopped.'
            return
        if threadId not in self._threads:
            print 'thread is not in memory any more. '
            return
        print 'calling terminate.'
        self._threads[threadId].terminate()

    def status(self):
        """
        Returns a dictionary containing information about all threads managed by the code runner.
        Format is {'threadId1':{'isRunning':trueOrFalse,'nanme':name,'failed': trueOrFalse },...}.
        """
        status = {}
        for threadId in self._threads:
            status[threadId] = dict()
            status[threadId]["isRunning"] = self.isExecutingCode(threadId)
            status[threadId]["name"] = self._threads[threadId].name()
            status[threadId]["failed"] = self._threads[threadId].failed()
        return status

    def executeCode(self, code, threadId, name=None, resultExpression=None, gv=None, lv=None):
        """
        Public mehtod to execute a code string and resultExpression string in an existing or new thread, with
        - a given identifier,
        - a given name,
        - and new global and local variable dictionaries if the thread does not exist yet.
        Returns the thread id.
        """
        # print "in  CodeRunner's executeCode with gv = ", gv
        if threadId is not None and self.isExecutingCode(threadId):
            raise Exception("Code thread %s is busy!" % threadId)
        if threadId in self._threads and self._threads[threadId].isAlive():
            # if a thread with that identifier exists and is alive
            ct = self._threads[threadId]
            # use it to execute the passed piece of code
            ct.executeCode(code, name, resultExpression=resultExpression)
        else:                                   # otherwise initiate a new thread
            ct = self._createThread(code, threadId, name, resultExpression, gv, lv)
        return ct._id

    def _createThread(self, code, threadId, name, resultExpression, gv, lv):
        """
        Private method that creates and executes a new codeThread with a given identifer, code, name,
        resultExpression, and global and local dictionnaries.
        Returns the created codeThread instance.
        Note that the
        """
        class GlobalVariables:
            """
            The GlobalVariable class is a handle to a global variable dictionary with a reference to the __coderunner__
            in the dictionary itself. It is not a copy of the passed dictionary.
            It allows users to get or set a variable var using the syntax gv.var instead of gv['var'].
            Printing the GlobalVariables prints its dictionary.
            But syntax <'key' in gv> does not work and has to be replaced by <'key' in gv.__dict__>.
            (is there a solution?)
            """

            def __init__(self, gv, __coderunner__=None):
                # the dictionary of properties of the object becomes the passed dictionary gv
                # print "creating GlobalVariable object with gv =", gv
                self.__dict__ = gv
                # the coderunner property is added to (or overwritten in) gv
                self.__coderunner__ = __coderunner__
                # print "new GlobalVariable = ", gv

            def __setitem__(self, key, value):  # transforms gv.key = b
                setattr(self, key, value)       # into of gv['keyname'] = b

            def __getitem__(self, key):         # allows to get gv.key
                return getattr(self, key)

            def __str__(self):                  # print of the object will print it dictionary __dict__
                return str(self.__dict__)

        if gv is None:                          # sets the thread's global variable dictionary to the CodeRunner's one if not passed
            gv = self._gv
        if lv is None:                          # reuse the local variable dictionary for the thread if not passed
            if threadId not in self._lv:
                self._lv[threadId] = dict()
            lv = self._lv[threadId]
        # - making the GlobalVariables handle to gv accessible by 'gv' in the local variable namespace
        lv['gv'] = GlobalVariables(gv, self)
        # - making the code name (filename the code is originating from for instance), available as a local variable __file__
        lv['__file__'] = name
        # - instantiating a CodeThread with the passed or prepared variables
        if threadId is None:  # just in case but should never happen
            threadId = self._newId()
            # Creates codethread with both gv and lv dictionnaries set to lv dictionary;
            # without gv=lv the gv variable (in lv dictionary) would not be available as a global variable
            # (in a function of a script for instance)
        ct = CodeThread(code, threadId=threadId, name=name, lv=lv, gv=lv,
                        resultExpression=resultExpression, callback=self._threadCallback)
        # - adding the thread to the thread dictionary self._threads
        self._threads[threadId] = ct
        ct.setDaemon(True)  # makes the thread daemonic, that is stoppable by terminating the coderunner "
        # - calling the start method of threading.Thread to run the piece of code in its thread.
        ct.start()
        return ct

    def deleteThread(self, threadId):
        """
        Exit and deletes a codeThread with a given thread identifier and returns True if deletion could be done.
        Use with care !!!
        """
        if threadId in self._threads:
            ct = self._threads[threadId]
            del self._threads[threadId]
            del ct
            return True
        return False

    def _threadCallback(self, thread, result=None):
        """
        A callback function which gets called when a code thread finishes the execution of a piece of code.
        (Not to be confused with the callback functions stored by the multiprocessCodeRunner).
        The present function propagates a result to the _callbackQueue passed to the codeRunner.
        """
        # print 'Thread %s is calling back with result =' % str(thread._id), result  # debugging
        lock = RLock()
        lock.acquire()
        if thread.failed():
            self._exceptions[thread._id] = thread.exceptionInfo()
            self._tracebacks[thread._id] = thread.tracebackInfo()
        if self._callbackQueue is not None:
            # TO BE DONE: PROTECTION AGAINST PICKLING ERROR
            try:  # QUEUE errors are not catched
                self._callbackQueue.put((thread._id, thread.failed(), result), False)
            except:
                pass
        lock.release()


class CodeProcess(Process):
    """
    A process which runs an instance of CodeRunner and communicates through queues with parent process.
    This class is used by the MultiProcessCodeRunner class.
    It subclasses Process from the multiprocessing python library and adds several queues for commands, responses,
    inputs, outputs, and errors.
    It also takes at intitialization an external callbackQueue as argument, for sending back results to the parent process.
    WARNING: only pickable results can be passed between processes.
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

    def __init__(self, commandQueue, responseQueue, callbackQueue=None):
        Process.__init__(self)
        # save the passed variables as self attributes ()
        self._commandQueue = commandQueue         # commmand queue
        self._responseQueue = responseQueue       # response queue for results once a thread has started
        self._callbackQueue = callbackQueue       # response queue for results returned by a thread result expression
        self._gv = dict()                         # Global variable dictionary for coderunner, helpers and all scripts
        # Sets the process as daemonic (abruptly stoppable at shutdown)
        self.daemon = True
        # Creates std in, out and error queues
        self._stdoutQueue = Queue()
        self._stderrQueue = Queue()
        self._stdinQueue = Queue()
        # Starts the codeRunner, propagating the global variable dictionary and the callbackQueue handle
        self._codeRunner = CodeRunner(gv=self._gv, callbackQueue=self._callbackQueue)

    def stdoutProxy(self):
        return self.StreamProxy(self._stdoutQueue)

    def stderrProxy(self):
        return self.StreamProxy(self._stderrQueue)

    def stdinQueue(self):
        return self._stdinQueue

    def stdoutQueue(self):
        return self._stdoutQueue

    def stderrQueue(self):
        return self._stderrQueue

    def run(self):
        """
        This run method subclasses the Process.run() method of 'multiprocessing'.
        It is automatically called by the Process.start() method of 'multiprocessing'.
        Starts the code process infinite loop, which consists in
        - reading the command queue
        - calling the command with its arguments
        - getting the response from the response queue
        """
        # Redirect the private std in out and error queues of the class to the system ones.
        sys.stderr = self.StreamProxy(self._stderrQueue)
        sys.stdout = self.StreamProxy(self._stdoutQueue)
        sys.stdin = self.StreamProxy(self._stdinQueue)
        print 'New code process is up and running ... '
        while True:                                         # infinite loop
            time.sleep(0.1)                                 # every 0.1s
            try:                                            # Tries to
                while not self._commandQueue.empty():       # process the commandQueue while it is not empty
                    (command, args, kwargs) = self._commandQueue.get(False)
                    if command == 'stop':
                        exit(0)                             # until a stop command or a keybord interrupt occurs.
                    if hasattr(self._codeRunner, command):  # Simply ignores commands unknown from coderunner
                        try:                                # Builds the command call,
                            f = getattr(self._codeRunner, command)
                            r = f(*args, **kwargs)          # runs it, gets a result,
                            self._responseQueue.put(r, False)  # and puts it in the response queue.
                        except Exception as e:
                            traceback.print_exc()
            except KeyboardInterrupt:
                print '\t Interrupting code process and exiting...'


class MultiProcessCodeRunner(Subject):
    """
    The MultiProcessCodeRunner is designed to run sub-processes of type CodeProcess (each one running a CodeRunner),
    and to add error and stdout queue managagement functions.
    The present implemention includes only one CodeProcess.
    Any call to an unknown attribute of MultiProcessCodeRunner is transformed into
    a message dispatched to the command queue communicating with this code process;
    a possible response from the dispatch function (read from the CodeProcess responseQueue) is returned if available before a timeout.
    As a Subject, the MultiProcessCodeRunner can send notifications to its observers.

    The main public method, executeCode(code, threadId, *args, name=filename, resultExpression=resultExpression, callbackFunc=callbackFunc, **kwagrs),
    calls the coderunner's executeCode method to run a piece of code in a particular thread.
    This executeCode method also allows its caller to be called back asynchroneously when the execution is finished,
    and possibly treat the result generated by resultExpression.
    Two callback mechanisms are provided: (1) a simple notification to observers, and (2) a direct callback function call.
    In that aim, the MultiProcessCodeRunner:
        - creates a callbackQueue that it passes to the CodeProcess for getting back messages of the form (threadId, failed, result) from each thread.
        - has a dictionary _callbackDict in which executeCode stores an item threadId:(callbackFunc, resultExpression) to memorize what to do with a future callback message from this thread.
        - has a _callbackQueueManager receiving the callback messages (threadId, failed, result) from the callback queue,
        and propagating them according to _callbackDict[threadId] = (callbackFunc, resultExpression):
            - if callbackFunc is 'notify', method (1) is used:
                A notification (subject='MultiProcessCodeRunner', property='callback', value=(threadId, failed, result)) is sent to all observers,
            - if callbackFunc is callable, method (2) is used:
                callbackFunc(result) is called if result is not None or callbackFunc() otherwise.
            The _callbackQueueManager removes _callbackDict[threadId] from _callbackDict when treating a message.
    WARNING 1: only pickable results can be passed between processes ==> Use callbackFunc only with resultExpression generating pickable results.
    WARNING 2: Several callbacks cannot be programmed asynchroneously for a single thread.
    """

    def __init__(self, logProxy=lambda x: False, errorProxy=lambda x: False):
        Subject.__init__(self)
        # handle to global variables for a possible code process restart
        self._timeout = 1
        self._codeProcess = None    # useful to test it in startCodeProcess
        # print '\n process running MultiProcessCodeRunner is', os.getpid()
        self._commandQueue = Queue()
        self._responseQueue = Queue()
        self._callbackQueue = Queue()
        self._callbackDict = {}
        self.startCodeProcess()

    def startCodeProcess(self):
        """
        Starts or restarts the associated CodeProcess.
        """
        # Creates a single CodeProcess with global variables gv
        if self._codeProcess is not None:
            self.terminateCodeProcess()
        # Creates a _callbackQueue manager
        cbqmThread = Thread(target=self._callbackQueueManager)
        cbqmThread.daemon = True
        cbqmThread.start()
        self._cbqmThread = cbqmThread
        # Creates and starts a single CodeProcess with global variables gv
        print "Starting (or restarting) code process..."
        self._codeProcess = CodeProcess(self._commandQueue, self._responseQueue, self._callbackQueue)
        self._codeProcess.daemon = True
        self._codeProcess.start()
        # make the Process' queues also attributes of MultiProcessCodeRunner
        self._stdoutQueue = self._codeProcess.stdoutQueue()
        self._stderrQueue = self._codeProcess.stderrQueue()
        self._stdoutProxy = self._codeProcess.stdoutProxy()
        self._stderrProxy = self._codeProcess.stderrProxy()

    def _callbackQueueManager(self):
        """
        This manager runs in a separate thread in the main process to avoid blocking the MultiProcessCodeRunner.
        It waits for each message arriving in the callback Queue and treats it:
            - If the message is 'stop', it terminates its infinite loop
            - If message has the form (threadId, failed, result) and threadID exists in callbackDict, and if failed is false,
            it treats the message according to _callbackDict[threadId] = (callbackFunc, resultExpression):
                - if callbackFunc is 'notify', method (1) is used:
                    A notification (property='callback', value=(threadId, failed, result)) is sent to all observers,
                - if callbackFunc is callable, method (2) is used:
                    callbackFunc(result) is called if result is not None or callbackFunc() otherwise.
                The _callbackQueueManager removes _callbackDict[threadId] from _callbackDict when treating a message.
            - otherwise it ignores the message.
        IMPORTANT: This _callbackQueueManager runs the callback functions one after the other in its own thread.
        It reports errors but does not raise them in order to never stop working.
        """
        _debug = True
        while True:                                     # infinite loop until a 'stop' message
            try:
                item = self._callbackQueue.get(True)    # blocks until an item is available from the callbackQueue
            except Exception, e:
                print 'ERROR in a MultiProcessCodeRunner getting message from _callbackQueue:' + str(e)
            if item == 'stop':                          # this is the sentinel indicating the end of the infinite loop.
                break                                   # exit
            elif isinstance(item, tuple) and len(item) >= 3:  # check message has the correct form
                # made of the thread id, the failed boolean, and the result.
                threadId, failed, result, = item
                if threadId in self._callbackDict:      # if theadId is in _callbackDict
                    callbackFunc, resultExpression = self._callbackDict[threadId]  # read what to do in callbackDict
                    self._callbackDict.pop(threadId)    # and erase this info because it is valid for a single call only
                    if not failed:                      # continue with callback only if code execution did not failed
                        if isinstance(callbackFunc, str) and callbackFunc.lower() == 'notify':  # use the notify method if specified
                            self.notify(property='callback', value=item)
                        # or calls a callback function if available
                        elif callable(callbackFunc):
                            try:
                                if resultExpression is not None:
                                    callbackFunc(result)                                      # with result if any
                                else:
                                    callbackFunc()                                            # or not.
                            except Exception, e:
                                print 'ERROR in a MultiProcessCodeRunner callback:' + str(e)
                elif _debug and result is not None:
                    print 'No callback defined for thread id = %s returning message' % threadId, item  # for debugging

    def terminateCodeProcess(self):
        """
        Terminates the associated CodeProcess if alive;
        Terminates the callback manager thread;
        Clears command, response, and callback queues.
        """
        if self._codeProcess.is_alive():
            self._codeProcess.terminate()
            self._codeProcess.join()                 # Waits for the CodeProcess to terminate
        self._clearQueue(self._commandQueue)         # Clears the command
        self._clearQueue(self._responseQueue)        # and response queues
        if self._cbqmThread.is_alive():              # Stops the callback manager thread
            self._callbackQueue.put('stop')          # by sending the sentinel
            self._cbqmThread.join()                  # and waiting for termination.
        self._clearQueue(self._callbackQueue)        # Clears the callback queue

    def __del__(self):
        """ Destructor"""
        self.terminate()

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

    def stderrProxy(self):
        """
        Returns the error proxy of the code process.
        """
        return self._stderrProxy

    def stdoutProxy(self):
        """
        Returns the output proxy of the code process.
        """
        return self._stdoutProxy

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

    def _readAllFromStringQueueWithTimeout(self, queue, timeout):
        """
        Returns the concatenated string made of all strings present in any string queue of the associated CodeProcess'.
        (used for stdout and stderr)
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
        return self._readAllFromStringQueueWithTimeout(self._codeProcess.stdoutQueue(), timeout)

    def hasStderr(self):
        """
        Reads True if the error queue of the associated CodeProcess contains at least one error.
        """
        return not self._codeProcess.stderrQueue().empty()

    def stderr(self, timeout=0.5):
        return self._readAllFromStringQueueWithTimeout(self._codeProcess.stderrQueue(), timeout)

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

    def executeCode(self, *args, **kwargs):
        """
        Asks the codeRunner to execute a piece of code by sending a message to the commandQueue, after optionally preparing for a callback.
        Syntax is executeCode(code, threadId, name=filename, resultExpression=resultExpression, callbackFunc=callbackFunc)
        Callback preparation consists in:
        - Stores the item threadId: (callbackFunc, resultExpression) in the _callbackDict dictionary if callbackFunc is given (and different from None).
        WARNING: This storage occurs only if threadId is not already present in the dictionary since several callbacks cannot be programmed asynchroneously for a single thread.
        the _callbackQueueManager will know:
            - whether to propagate a callback if callbackFunc is a function or 'notify'
            - whether the result from resultExpression is to be passed to the callback if resultExpression is not None.
        function as an argument or not;
        - Removes 'callbackFunc' from kwargs if necessary;
        - Dispatches (command, *args, **kwargs) to command queue;
        - Returns the response from the dispatch method.
        """
        # prepare for callback
        threadId = args[1]
        callbackFunc = kwargs.pop('callbackFunc')
        if threadId in self._callbackDict:
            print 'WARNING from MultiProcessCodeRunner: a second callback cannot be programmed for the same thread.'
        else:
            if callbackFunc is not None:
                if 'resultExpression' in kwargs:
                    expr = kwargs['resultExpression']
                else:
                    expr = None
                self._callbackDict[threadId] = (callbackFunc, expr)
        # dispatch message executecode to commandQueue
        return self.dispatch('executeCode', *args, **kwargs)

    def dispatch(self, command, *args, **kwargs):
        """
        This dispatch method is used with __getattr__ to transform a command unknown by MultiProcessCodeRunner
        into a message put in the codeProcess' command queue.
        If a reponse from the responseQueue is returned before timeout, it is returned by dispatch.
        A response left in the queue because arrived after timeout will be erased at the next dispatch.

        With this dispatch method MultiProcessCodeRunner.command(*args,**kwargs) is transformed into
        self._codeProcess.commandQueue().put((command,args,kwargs),False).
        """
        message = (command, args, kwargs)
        if not self._codeProcess.is_alive():
            self.startCodeProcess()
        self._clearQueue(self._responseQueue)
        self._commandQueue.put(message, False)
        try:
            response = self._responseQueue.get(True, timeout=self.timeout())
        except:
            response = None
        return response

    def __getattr__(self, attr):
        return lambda *args, **kwargs: self.dispatch(attr, *args, **kwargs)

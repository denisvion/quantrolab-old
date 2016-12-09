
"""
This module implements a model that executes a function f in a Qt GUI application.
It includes several private functions and a public function execInGui(f) that executes f() with no arguments
in the Qt application QApplication.instance() if it is found from the thread where execInGui(f) is called,
or in a new Qt application otherwise.

"""
import sys
import time
import threading
from threading import Thread

from PyQt4.QtGui import QApplication
from PyQt4.QtCore import Qt, SIGNAL, QThread

# Memorizes at the module level if the runGuiCode(PyQt_PyObject) signal has been connected to the _runGuiCode function
signalConnected = False


def _runGuiCode(funcArgsKwargsList):
    """
    _runGuiCode(f,*args,**kwargs) is a private method that executes a function f(*args,**kwargs) encoded in
    funcArgsKwargsList, in the current Qt application.
    Valid funcArgsKwargsList formats are f, [f], [f, args],  [f, kwargs] or [f, args, kwargs] (with list or tuples).
    """
    if isinstance(funcArgsKwargsList, (list, tuple)):
        f = funcArgsKwargsList[0]
        if len(funcArgsKwargsList) == 2:
            args = funcArgsKwargsList[1]
            if isinstance(args, list):
                f(*args)
            elif isinstance(args, dict):
                f(**args)
        elif len(funcArgsKwargsList) >= 3:
            args = funcArgsKwargsList[1]
            kwargs = funcArgsKwargsList[2]
            f(*args, **kwargs)
    else:
        f()


def execInGui(f, *args, **kwargs):
    """
    execInGui(f,*args,**kwargs) is a public method that requests the execution of a function f(*args,**kwargs)
    in the current Qt application (or in a new one created on the fly if it does not exist) by emitting a signal.
    """
    # This tests the existence of the Qt application and creates it if needed.
    global app
    _ensureGuiThreadIsRunning()
    if app is None:
        raise Exception('Invalid application handle!')
    # This tells the application to run f
    app.emit(SIGNAL('runGuiCode(PyQt_PyObject)'), [f, args, kwargs])


def _ensureGuiThreadIsRunning(silent=True):
    """
    This private function
      - tests whether a QApplication instance is available;
      - creates a new thread and a QApplication in this thread, if it is not available;
      - otherwise connects simply the handler _runGuiCode to the QtApplication signal "runGuiCode(PyQt_PyObject)".
    """
    global app, signalConnected  # declares global variables
    # Gets a handle to an existing QApplication in the process
    app = QApplication.instance()
    if app is None:                                                     # if no QApplication
        if not silent:
            print 'No existing Qt application in current process => creating one...',
        # creates a child thread with new application as target global app created here
        thread = Thread(target=_createApplication)
        thread.daemon = True
        thread.start()                                                  # starts it
        while thread.is_alive() and (app is None or app.startingUp()):  # and wait until it is started
            time.sleep(0.01)
    else:                                                               # there is already a QApplication
        if not silent:
            print 'Use existing Qt application of current process...',
    # if we have not memorized in signalConnected that a conection to _runGuiCodeSignal exists
    if not signalConnected:
        if not silent:
            print 'Adding signal handler to application...',
        # defines the connection and memorize it
        _connectSignal()
    if not silent:
        print 'done.'


def _createApplication():
    """
    This private function creates a QApplication thread and connects the signal "runGuiCode(PyQt_PyObject)"
    to the handler _runGuiCodeSignal in unique connection mode (multiple identical signals treated only once).
    The PyQt_PyObject argument means arbitrary type and works in particular for a function with no arguments like f.
    """
    global app
    app = QApplication(sys.argv)          # The Qt application is created here
    app.setQuitOnLastWindowClosed(True)
    _connectSignal()
    if app.thread() != QThread.currentThread():
        message = 'Cannot start QT application from side thread! You will have to restart your process.'
        raise Exception(message)
    app.exec_()


def _connectSignal():
    global app, signalConnected
    app.connect(app, SIGNAL('runGuiCode(PyQt_PyObject)'), _runGuiCode, Qt.QueuedConnection | Qt.UniqueConnection)
    signalConnected = True
    # The event loop of the new application starts here

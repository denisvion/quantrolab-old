
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

from PyQt4.QtGui import *
from PyQt4.QtCore import *

# Memorize at the module level if the runGuiCode(PyQt_PyObject) signal has
# been connected to the _runGuiCode function
signalConnected = False


def _runGuiCode(f):
    f()


def execInGui(f):
    """
    execInGui(f) is a public method that executes a function f() with no arguments in the current Qt application
    or in a new one created on the fly if it does not exist.
    """
    # This tests the existence of the Qt application and creates it if needed.
    _ensureGuiThreadIsRunning()
    global app
    if app is None:
        raise Exception("Invalid application handle!")
    # This tells the application to run f
    app.emit(SIGNAL("runGuiCode(PyQt_PyObject)"), f)


def _ensureGuiThreadIsRunning():
    """
    This private function
      - tests whether a QApplication instance is available;
      - if it is not available, creates a new thread and a QApplication in this thread;
      - otherwise connects simply the handler _runGuiCode to the QtApplication signal "runGuiCode(PyQt_PyObject)".
    """
    global app, signalConnected, _runGuiCode  # declares global variables
    # Gets a handle to an existing QApplication in the process
    app = QApplication.instance()
    if app is None:                                 # if no QApplication
        print 'Creating new application...',
        # creates a new thread with new application as target
        # global app created here
        thread = Thread(target=_createApplication)
        thread.daemon = True
        thread.start()                                  # starts it
        while thread.is_alive() and (app is None or app.startingUp()):
            # and wait until it is started
            time.sleep(0.01)
        print done
    else:                                           # there is already a QApplication
        # if we have not memorized in signalConnected that a conection to
        # _runGuiCodeSignal exists
        if not signalConnected:
            print 'Adding signal handler to application...',
            # defines the connection and memorize it
            print app.connect(app, SIGNAL("runGuiCode(PyQt_PyObject)"), _runGuiCode, Qt.QueuedConnection | Qt.UniqueConnection)
            signalConnected = True
            print 'done'


def _createApplication():
    """
    This private function creates a QApplication thread and connects the signal "runGuiCode(PyQt_PyObject)"
    to the handler _runGuiCodeSignal in unique connection mode (multiple identical signals treated only once).
    The PyQt_PyObject argument means arbitrary type and works in particular for a function with no arguments like f.
    """
    global app, signalConnected, _runGuiCode
    app = QApplication(sys.argv)          # The Qt application is created here
    app.setQuitOnLastWindowClosed(False)
    app.connect(app, SIGNAL('runGuiCode(PyQt_PyObject)'),
                _runGuiCode, Qt.QueuedConnection | Qt.UniqueConnection)
    signalConnected = True
    if app.thread() != QThread.currentThread():
        raise Exception(
            "Cannot start QT application from side thread! You will have to restart your process...")
    app.exec_()                           # The event loop of the new application starts here

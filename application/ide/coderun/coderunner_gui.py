
"""
This module implements a model that makes possible to execute a function in a Qt GUI application.
It includes several private functions and a public function execInGui(f) that executes f() with no arguments
in the Qt application QApplication.instance() if it is found from the thread where execInGui(f) is called,
 or in a new Qt application otherwise.
Note that in the Quantrolab multithread IDE, the threads in which each script is executed
are by default not Qt threads with a Qt application, and that calling execInGui from such a script will thus
lead to the creation of a new Qt application.

"""
import sys
import time
import threading
from threading import Thread

from PyQt4.QtGui import *
from PyQt4.QtCore import *

signalConnected = False


def _runGuiCodeSignal(f):
    f()


def execInGui(f):
    """
    execInGui(f) is a public method that executes a function f() with no arguments in the current Qt application
    or in a new one if it does not exist.
    """
    _ensureGuiThreadIsRunning(
    )    # This tests the existence of the Qt application and creates it if needed.
    global app
    if app is None:
        raise Exception("Invalid application handle!")
    # This tells the application to run f
    app.emit(SIGNAL("runGuiCode(PyQt_PyObject)"), f)


def _createApplication():
    """
    This private function creates a QApplication and connects the handler _runGuiCodeSignal
    to signal "runGuiCode(PyQt_PyObject)" in unique connection mode (multiple identical signals treated only once).
    The PyQt_PyObject argument type means arbitrary type and works for a function f (with no arguments)
    """
    global app
    global signalConnected
    global _runGuiCodeSignal
    app = QApplication(sys.argv)          # The Qt application is created here
    app.setQuitOnLastWindowClosed(False)
    app.connect(app, SIGNAL("runGuiCode(PyQt_PyObject)"),
                _runGuiCodeSignal, Qt.QueuedConnection | Qt.UniqueConnection)
    signalConnected = True
    if app.thread() != QThread.currentThread():
        raise Exception(
            "Cannot start QT application from side thread! You will have to restart your process...")
    app.exec_()                           # The event loop of the new application starts here


def _ensureGuiThreadIsRunning():
    """
    This private function
      - tests whether a QApplication instance is available from the thread in which execInGui was called;
      - connects simply the handler _runGuiCodeSignal to signal "runGuiCode(PyQt_PyObject)" if the instance exists;
      - creates a new thread and a QApplication in this thread if the instance does not exist.
    """
    global app
    global signalConnected
    global _runGuiCodeSignal
    app = QApplication.instance()
    if app is None:
        print "Creating new application..."
        thread = Thread(target=_createApplication)
        thread.daemon = True
        thread.start()
        while thread.is_alive() and (app is None or app.startingUp()):
            time.sleep(0.01)
    else:
        if not signalConnected:
            print "Adding signal handler to application.."
            print app.connect(app, SIGNAL("runGuiCode(PyQt_PyObject)"), _runGuiCodeSignal, Qt.QueuedConnection | Qt.UniqueConnection)
            signalConnected = True

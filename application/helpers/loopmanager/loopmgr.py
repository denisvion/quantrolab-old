import sys
import getopt
import os.path
import traceback
from threading import Thread

import PyQt4.uic as uic

# SUBJECT, OBSERVER, DISPATCHER, THREADEDDISPATCHER
from application.lib.base_classes1 import *
from application.lib.com_classes import *               # SINGLETON, RELOADABLE
from application.lib.helper_classes import Helper


# This is a class that manages loops
class LoopMgr(Singleton, ThreadedDispatcher, Helper):

    """
    The LoopMgr is a Singleton class loop manager, which can be used to manage loop objects of class SmartLoop (or derived from this class).
    Call addLoop() or removeLoop() to add or remove a loop to/from the loop manager.
    Control of loops is through loops' methods.
    """

    def __init__(self, parent=None, globals={}):
        if hasattr(self, "_initialized"):
            return
        Singleton.__init__(self)
        Helper.__init__(self, parent, globals)
        ThreadedDispatcher.__init__(self)
        self._loops = []
        self._initialized = True

    def updated(self, subject=None, property=None, value=None):
        self.notify("updated", subject)

    def removeLoop(self, loop):
        """
        Adds a loop to the loop manager.
        """
        if loop in self._loops:
            del self._loops[self._loops.index(loop)]
            self.notify("removeLoop", loop)
            return True

    def addLoop(self, loop):
        """
        Adds a loop to the loop manager.
        """
        if not loop in self._loops:
            self._loops.append(loop)
            self.notify("addLoop", loop)
            return True

    def updateLoop(self, loop):
        """
        Update loop manager
        """
        if loop in self._loops:
            self.notify("updateLoop", loop)
            return True

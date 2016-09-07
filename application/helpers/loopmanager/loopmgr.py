import sys
import gc
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
    The Loop manager LoopMgr is a Singleton class which can be used to keep track of and manage loops.
    It keeps a list of strong references to the managed loops.
    loopmgr_gui.py provides a graphical frontend for this manager.
    Just call addLoop() or removeLoop() to add or remove a loop to the loop manager.
    """

    def __init__(self, parent=None, globals={}):
        if hasattr(self, "_initialized"):
            return
        Singleton.__init__(self)
        Helper.__init__(self, parent, globals)
        ThreadedDispatcher.__init__(self)
        self._loops = []                    # the list of managed loops
        self._initialized = True

    def addLoop(self, loop):
        """
        Adds a loop to the loop manager.
        """
        if loop not in self._loops:
            self._loops.append(loop)
            self.notify("addLoop", loop)
            return True

    def removeLoop(self, loop, stop=True, removeChildren=True, notify=True):
        """
        Removes a loop from the loop manager (without necessarily deleting it),
        after stopping it and its children if stop=True.
        Removes also the children if removeChildren is true.
        Notifies if notify = true
          (which makes possible to notify only once for the parent loop in case of recursive calls for children)
        """
        if loop in self._loops:
            if stop:
                loop.stopAllAtNext()
            if removeChildren:
                for child in loop.children():
                    self.removeLoop(child, stop=False, notify=False)
            self._loops.remove(loop)
            if notify:
                self.notify("removeLoop", loop)

    def loops(self):
        """ Returns a copy of the list of loops"""
        return list(self._loops)

    def updated(self, subject=None, property=None, value=None):
        """
        Function called when receiving notification.
        Unused for the moment because the loop managers does not observe its managed loops.
        """
        pass

"""
This module defines the Helper and HelperGUI classes for the Quantrolab application.
A Helper is a NON-GUI plugin that adds functionalities to the Quantrolab integrated development environment (IDE).
A HelperGUI is a GUI plugin that adds functionalities to the Quantrolab IDE.
Helpers and HelperGUIs can be either independant applications from the IDE, or be run inside the IDE Coderunner to share the same global variables as the scripts.
They can be Singletons (that exist in only one exemplary) or not.
A HelperGUI can be stand-alone or be the GUI layer of a Helper associated to it.
  In case of Helper-HelperGUI association,
    - both classes can be in the same or in different files.
    - the HelperGUI is usually in charge of loading the Helper if it is not already loaded.
The possible strategies of interaction with Helpers and HelperGUIs are the following:
  1) Helper without HelperGUI => Users interact with the Helper through scripts in the IDE
  2) Stand alone HelperGUI
    2a) => User interacts with the HelperGUI only through the graphical user interface;
    2b) => User does not interact with the HelperGUI through the graphical user interface but through scripts, and the GUI is only a display;
    2c) => User can interact from both the graphical user interface and from scripts in the IDE (difficult to program in a reliable way).
  3) Associated Helper and HelperGUI
    3a) User interacts only with Helper through scripts, HelperGUI receive messages from the Helper and is only a display.
    3b) => Both scripts of the IDE and the HelperGUI are clients and send commands to the Helper;
        After both types of interaction, the HelperGUI receives messages from the Helper and update its GUI
        This strategy is powerful but difficult to program.

Example 1:  The DataMgr and DataManager form a couple of associated Helper-HelperGUI implementing strategy 3b to help
          users managing datacubes (the base data structure of Quantrolab)
Example 2:  The LoopMgr and LoopManager form a couple of associated Helper-HelperGUI implementing strategy 3b to help
          users managing Smartloops.

Remarks:
 - a HelperGUI and its associate Helper have strong references to each others.
"""
import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from application.lib.base_classes1 import Debugger, Reloadable
from application.lib.com_classes import Subject, Observer
from application.ide.widgets.observerwidget import ObserverWidget


class Helper(Debugger, Reloadable, Subject, Observer, object):
    """
    Class for a Quantrolab's non-gui helper.
    """

    def __init__(self, name=None, parent=None, globals={}):
        Reloadable.__init__(self)
        Subject.__init__(self)
        Observer.__init__(self)
        Debugger.__init__(self)
        self._name = name
        self._parent = parent
        self._globals = globals
        self._gui = None

    def __del__(self):
        self.notify('deleted')


class HelperGUI(Debugger, Reloadable, Subject, ObserverWidget, QMainWindow, object):
    """
    Class for a helper with a Qt graphical interface (QMainWindow).
    HelperGUI is deleted when closing its main window.
    What to do with associate ?
    """

    def __init__(self, name=None, parent=None, globals={}, helper=None):
        Reloadable.__init__(self)
        Subject.__init__(self)
        ObserverWidget.__init__(self)
        Debugger.__init__(self)
        QMainWindow.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self._parent = parent
        self._globals = globals
        self._name = name
        menubar = self.menuBar()
        helperMenu = menubar.addMenu('Helper')
        helperMenu.addAction(QAction('Reload this GUI helper...', self, triggered=self.reloadHelperGUI))
        self.setHelper(helper)
        if self._helper is not None:
            commandText = 'Reload associate ' + self._helper.__class__.__name__ + '...'
            helperMenu.addAction(QAction(commandText, self, triggered=self.reloadHelper))
        helperMenu.addAction(QAction('Close this GUI helper...', self, triggered=self.close))

    def setHelper(self, helper):
        self._helper = helper                                           # GUI helpers have a strong reference to their associate
        if self._helper is not None:
            # attach the gui to its associate to communicate with it
            self.debugPrint('attaching', self._helper, 'to', self)
            self._helper.attach(self)
            self._helper._gui = self                                    # create or update a _gui attribute to the associate

    def reloadHelperGUI(self):
        reply = QMessageBox.question(self,
                                     'Confirm reload ...',
                                     'This GUI helper will be reloaded. Are you sure?',
                                     QMessageBox.Ok | QMessageBox.Cancel)
        if reply == QMessageBox.Ok:
            self.reloadClass()

    def reloadHelper(self):
        reply = QMessageBox.question(self,
                                     'Confirm reload ...',
                                     'The associate helper ' + self._helper.__class__.__name__ +
                                     ' will be reloaded. Are you sure?',
                                     QMessageBox.Ok | QMessageBox.Cancel)
        if reply == QMessageBox.Ok:
            self._helper.reloadClass()

    def window2Front(self):
        self.showNormal()
        self.activateWindow()

    def showEvent(self, event):
        # determine the whole display geometry
        desktop = QDesktopWidget()
        rect = QRect()      # available geometry
        for i in range(desktop.screenCount()):
            rect = rect.united(desktop.availableGeometry(i))
        x1, y1, x2, y2 = rect.getCoords()
        # Read the settings
        settings = QSettings()
        key = ''
        if self._name is not None:
            key += self._name + '/'
        key2 = key + 'size'
        if settings.contains(key2):
            size = settings.value(key2, self.size()).toSize()
            self.resize(size)
        size = self.frameSize()
        w, h = size.width(), size.height()
        key1 = key + 'pos'                    # read the previous top-left corner
        if settings.contains(key1):
            pos = settings.value(key1, self.pos()).toPoint()
            x, y = pos.x(), pos.y()
            if x < x1:      # and move it back to inside the desktop if needed
                pos.setX(x1)
            elif x + w > x2:
                pos.setX(max(x1, x2 - w))
            if y < y1:
                pos.setY(y1)
            elif y + h > y2:
                pos.setY(max(0, y2 - h))
            if rect.contains(pos):
                self.move(pos)

    def closeEvent(self, event):
        """
        reply = QMessageBox.question(self,
                                     "Confirm Helper Panel Exit...",
                                     "Helper Panel will be closed and deleted. Are you sure?",
                                     QMessageBox.Ok | QMessageBox.Cancel)

        if reply == QMessageBox.Ok:
            if self._helper is not None:
                self.debugPrint('detaching', self._helper, 'from', self)
                self._helper.detach(self)   # remove the two references to this gui
                self._helper._gui = None
            event.accept()
            self.notify(property='closing',)
        else:
            event.ignore()
        """
        key = ''
        if self._name is not None:
            key += self._name + '/'
        QSettings().setValue(key + 'pos', self.pos())
        QSettings().setValue(key + 'size', self.size())

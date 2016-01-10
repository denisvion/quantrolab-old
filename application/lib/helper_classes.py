"""
This module defines the Helper and HelperGUI classes for the Quantrolab application.
A Helper is a NON-GUI plugin that adds functionalities to the Quantrolab integrated development environment (IDE).
A HelperGUI is a GUI plugin that adds functionalities to the Quantrolab IDE.
Helpers and HelperGUIs can be either independant applications from the IDE, or be run inside the IDE to share the same global variables as the scripts.
They can be Singletons (that exist in only one exemplary) or not
A HelperGUI can be stand-alone or be the GUI layer of a Helper associated to it.
  In case of Helper-HelperGUI association, 
    - both classes can be in the same or in different files.
    - the HelperGUI is usually in charge of loading the Helper if it is not already loaded.  
The possible strategies of interaction with Helpers and HelperGUIs are the following:
  1) Helper without HelperGUI => Users interact with the Helper through scripts in the IDE
  2) Stand alone HelperGUI
    2a) => User interacts with the HelperGUI only through the graphical user interface;
    2b) => User does not interact with the HelperGUI through the graphical user interface but through scripts and the GUI is only a display;
    2) => User can interact with both the graphical user interface and scripts in the IDE (difficult to program in a reliable way)
  3) Associated Helper and HelperGUI
    3a) User interacts only with Helper through scripts, HelperGUI receive messages from the Helper and is only a display.
    3b) => Both scripts of the IDE and the HelperGUI are clients and send commands to the Helper;
        After both type of interaction, the HelperGUI receives messages from the Helper and update its GUI 
        This strategy is powerful but difficult to program.

Example:  The DataMgr and DataManager form a couple of associated Helper-HelperGUI implementing strategy 3b to help
          users managing datacubes (the base data structure of Quantrolab)
"""
import sys
from PyQt4.QtCore import Qt
from PyQt4.QtGui import *
from application.lib.base_classes1 import Debugger,Reloadable
from application.lib.com_classes import Subject, Observer
from application.ide.widgets.observerwidget import ObserverWidget

class Helper(Debugger,Reloadable,Subject,Observer,object):
  """
  Class for a Quantrolab's non-gui helper.
  """      
  def __init__(self,parent=None,globals={}):
    Reloadable.__init__(self)
    Subject.__init__(self)
    Observer.__init__(self)
    Debugger.__init__(self)
    self._parent=parent
    self._globals=globals
    self._gui=None

  def __del__(self):
    self.notify('deleted')


class HelperGUI(Debugger,Reloadable,Subject,ObserverWidget,QMainWindow,object):
  """
  Class for a helper with a graphical interface.
  """
  def __init__(self,parent=None,globals={},helper=None):
    Reloadable.__init__(self)
    Subject.__init__(self)
    ObserverWidget.__init__(self)
    Debugger.__init__(self)
    QMainWindow.__init__(self,parent)
    self._parent=parent
    self._globals=globals
    self._helper=helper
    if self._helper:
      self.debugPrint('attaching',self._helper,'to',self)
      self._helper.attach(self)               # and attach the gui to the helper
    menubar = self.menuBar()
    helperMenu = menubar.addMenu('Helper')
    reloadHelperGUI = helperMenu.addAction(QAction('Reload this helper...',self,triggered=self.reloadHelperGUI))
    if self._helper:
      reloadHelper = helperMenu.addAction(QAction('Reload '+self._helper.__class__.__name__+'...',self,triggered=self.reloadHelper))
    close = helperMenu.addAction(QAction('Close GUI helper',self,triggered=self.close))

  def reloadHelperGUI(self):
    reply = QMessageBox.question(self,
      'Confirm reload ...',
      'This GUI helper will be reloaded. Are you sure?',
      QMessageBox.Ok| QMessageBox.Cancel)
    if reply == QMessageBox.Ok:
      self.reloadClass()

  def reloadHelper(self):
    reply = QMessageBox.question(self,
      'Confirm reload ...',
      'The associate helper '+self._helper.__class__.__name__+' will be reloaded. Are you sure?',
      QMessageBox.Ok| QMessageBox.Cancel)
    if reply == QMessageBox.Ok:
      self._helper.reloadClass()

  def window2Front(self):
    self.showNormal()
    self.activateWindow()

  def closeEvent(self,event):
      reply = QMessageBox.question(self,
            "Confirm Helper Panel Exit...",
            "Helper Panel will be closed and deleted. Are you sure?",
            QMessageBox.Ok| QMessageBox.Cancel)
      if reply == QMessageBox.Ok:
          event.accept()
          self.notify('deleted')
      else:
          event.ignore()
    
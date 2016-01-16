from PyQt4.QtGui import *
from PyQt4.QtCore import *
from types import ModuleType

from application.ide.widgets.observerwidget import ObserverWidget
import application.helpers.instrumentsmanager
from application.lib.base_classes1 import Debugger


class FrontPanel(Debugger, QMainWindow, QWidget, ObserverWidget, object):

    """
    A Qt instrument frontpanel class depending on classes QMainWindow,QWidget,and ObserverWidget.
    """

    def __init__(self, instrument, parent=None, **kwargs):
        Debugger.__init__(self)
        QMainWindow.__init__(self, parent)
        self.qw = QWidget(parent)
        self.setCentralWidget(self.qw)
        menubar = self.menuBar()
        myMenu = menubar.addMenu("&File")
        reloadCommand = myMenu.addAction("Reload instrument")
        saveStateCommand = myMenu.addAction("Save instrument state as...")
        restoreStateCommand = myMenu.addAction(
            "Load and restore instrument state...")
        self.connect(reloadCommand, SIGNAL(
            "triggered()"), self.reloadInstrument)
        self.connect(saveStateCommand, SIGNAL(
            "triggered()"), self.saveStateInFile)
        self.connect(restoreStateCommand, SIGNAL(
            "triggered()"), self.restoreStateFromFile)
        ObserverWidget.__init__(self)
        self.setInstrument(instrument)

    def setInstrument(self, instrument):
        """
        Set the instrument variable of the frontpanel.
        """
        self.instrument = instrument
        self.instrument.attach(self)

    def __del__(self):
        print "Detaching instrument..."
        self.instrument.detach(self)

    def hideEvent(self, e):
        print "Detaching instrument..."
        self.instrument.detach(self)
        QWidget.hideEvent(self, e)

    def closeEvent(self, e):
        print "Detaching instrument..."
        self.instrument.detach(self)
        QWidget.closeEvent(self, e)

    def showEvent(self, e):
        self.instrument.attach(self)
        QMainWindow.showEvent(self, e)

    def saveStateInFile(self):
        self.debugPrint(
            'in frontpanel.saveStateInFile() of instrument ', self.instrument.name())
        filename = QFileDialog.getSaveFileName(
            filter="instrumentState (*.inst)")
        if filename != '':
            self.instrument.saveStateInFile(filename)
            # self._manager.saveStateAs(filename=filename,instruments=[self.instrument.name()])
            # # Bad programming

    def restoreStateFromFile(self):
        self.debugPrint(
            'in frontpanel.restoreState() of instrument ', self.instrument.name())
        filename = QFileDialog.getOpenFileName(
            filter="instrumentState (*.inst)")
        if filename != '':
            # call the instrument method restoreStateFromFile
            self.instrument.restoreStateFromFile(filename)
            # configuration requested from a frontpanel should lead to its Gui
            # update => call updateGui
            self.updatedGui(self, property='restoreStateFromFile',
                            value=None, message=None)

    def reloadInstrument(self):
        """
        Reloads the instrument (not the frontpanel) if the module can be found (i.e. if it is local).
        No initialization is done.
        """
        name = self.instrument.name()
        self.debugPrint(
            'in frontpanel.reloadInstrument() of instrument ', name)
        module = None
        try:
            module = self.instrument.getModule()
        except:
            pass
        if not isinstance(module, ModuleType):
            print 'error in getting instrument module'
        else:
            try:
                reload(module)
                newClass = module.Instr
                self.instrument.__class__ = newClass
            except:
                raise

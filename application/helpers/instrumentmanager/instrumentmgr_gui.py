import sys
import os
import os.path
import imp
import time
import shelve
import inspect
import string
import yaml
import pickle
import traceback

from inspect import *
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from application.ide.widgets.observerwidget import ObserverWidget
from application.lib.instrum_classes import Instrument, VisaInstrument, CompositeInstrument
from application.lib.helper_classes import HelperGUI    # HelperGUI
from application.config.parameters import params
from application.ide.widgets.dockingtab import *
# (for displaying code of instruments)
from application.ide.editor.codeeditor import CodeEditor

from application.helpers.instrumentmanager.instrumentmgr import InstrumentMgr

# *******************************************
#  Helper initialization                   *
# *******************************************

# Global module dictionary defining the helper
helperDic = {'name': 'Instrument Manager', 'version': '1.0', 'authors': 'A. Dewes-V. Schmitt - D. Vion',
             'mail': 'denis.vion@cea.fr', 'start': 'startHelperGui', 'stop': None}

iconPath = os.path.dirname(__file__) + '/resources/icons'


# 3) Start the instrumentManager
def startHelperGui(exitWhenClosed=False, parent=None, globals={}):
    global instrumentManager
    instrumentManager = InstrumentManager(parent, globals)
    instrumentManager.show()                             # show its window
    QApplication.instance().setQuitOnLastWindowClosed(
        exitWhenClosed)  # close when exiting main application
    return instrumentManager


# 2) start the datamanager in IDE
def startHelperGuiInGui(exitWhenClosed=False, parent=None, globals={}):
    execInGui(lambda: startHelperGui(exitWhenClosed))

if __name__ == '__main__':                               # 1) starts here in the module
    startHelperGuiInGui(True)

# ********************************************
#  InstrumentManager GUI  class             *
# ********************************************


class InstrumentManager(HelperGUI):
    """
    Instrument manager GUI
    """

    def __init__(self, name=None, parent=None, globals={}):
        """
        Creator of the instrument manager panel.
        """
        instrumentMgr = InstrumentMgr(name, parent, globals)      # instantiates a InstrumentMgr
        instrumentMgr._gui = self                           # inform the helper it has an associated gui by adding the gui as an attribute

        # init superClasses and defines it as the associated helper of the present HelperGUI
        HelperGUI.__init__(self, name, parent, globals, helper=instrumentMgr)
        self.debugPrint("in InstrumentManagerPanel.creator")

        # Build GUI below
        self.setStyleSheet("""QTreeWidget:Item {padding:6;} QTreeView:Item {padding:6;}""")
        title = helperDic['name'] + " version " + helperDic["version"]
        if self._helper is not None:
            title += ' in tandem with ' + self._helper.__class__.__name__
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(iconPath + '/penguin.png'))
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        # preference dictionary for automatic build of preferences dialog box
        self.prefDict = {}

        menubar = self.menuBar()                            # menus
        filemenu = menubar.addMenu("File")
        self.connect(filemenu.addAction("Set root directory..."), SIGNAL("triggered()"), self.setRootDirectory)
        filemenu.addSeparator()
        openInst = filemenu.addAction("Open instrument from file...")
        closeInst = filemenu.addAction("Remove selected instrument(s)")
        filemenu.addSeparator()
        openList = filemenu.addAction("Open instrument config...")
        saveList = filemenu.addAction("Save instrument config as...")
        menubar.addMenu(filemenu)
        self.connect(openList, SIGNAL("triggered()"), self.openList)
        self.connect(openInst, SIGNAL("triggered()"), self.openInst)
        self.connect(closeInst, SIGNAL("triggered()"), self.closeInst)

        splitter = QSplitter(Qt.Horizontal)

        widgetLeft = QWidget()
        # left layout contains the instrument list (QTreeWidget) and a few buttons
        layoutLeft = QGridLayout()
        # The InstrumentList(QWidget) below has to be maintained up to date with backend instrument attribute _instrumentHandles.
        # In particular the items have to be kept in the same order
        self._instrList = InstrumentList()
        self._instrList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._instrList.setHeaderLabels(['Instrument name'])
        self._instrList.setSortingEnabled(False)
        self.connect(self._instrList, SIGNAL("reloadInstruments()"), self.reloadInstruments)
        self.connect(self._instrList, SIGNAL("loadShowFrontpanels()"), self.loadShowFrontpanels)
        self.setupList = QComboBox()
        self.setupList.setEditable(True)
        restoreSetup = QPushButton("Restore setup")
        saveSetup = QPushButton("Save setup")
        removeSetup = QPushButton("Remove setup")

        setupLayout = QBoxLayout(QBoxLayout.LeftToRight)

        reloadButton = QPushButton("Reload instrument(s)")
        frontPanelButton = QPushButton("Load/show frontpanel(s)")
        self.connect(reloadButton, SIGNAL("clicked()"), self.reloadInstruments)
        self.connect(frontPanelButton, SIGNAL("clicked()"), self.loadShowFrontpanels)

        self.connect(restoreSetup, SIGNAL("clicked()"), self.restoreSetup)
        self.connect(saveSetup, SIGNAL("clicked()"), self.saveSetup)
        self.connect(removeSetup, SIGNAL("clicked()"), self.removeSetup)

        buttonsLayout = QBoxLayout(QBoxLayout.LeftToRight)
        buttonsLayout.addWidget(reloadButton)
        buttonsLayout.addWidget(frontPanelButton)
        buttonsLayout.addStretch()
        setupLayout.addWidget(restoreSetup)
        setupLayout.addWidget(saveSetup)
        setupLayout.addStretch()
        setupLayout.addWidget(removeSetup)

        layoutLeft.addWidget(self._instrList)
        layoutLeft.addItem(buttonsLayout)
        layoutLeft.addWidget(QLabel("Store/restore setup:"))
        layoutLeft.addWidget(self.setupList)
        layoutLeft.addItem(setupLayout)

        widgetLeft.setLayout(layoutLeft)
        splitter.addWidget(widgetLeft)

        self._tabs = DockingTabWidget()
        self._instProp = InstrProperty(instrumentMgr=instrumentMgr)
        self._tabs.addTab(self._instProp, 'Parameters')
        self._instCode = InstrCodeWidget()
        self._instCode.setReadOnly(True)
        styleSheet = """CodeEditor{color:#000;background:#FFF;font-family:Consolas,Courier New,Courier;font-size:12px;font-weight:normal;}"""
        self._instCode.setStyleSheet(styleSheet)
        self._instCode.number_bar.setStyleSheet(styleSheet)
        self._tabs.addTab(self._instCode, 'Code')
        self._instHelp = InstrHelpWidget()
        self._tabs.addTab(self._instHelp, 'Methods')
        self._instVisa = InstrSCPIWidget()
        self._tabs.addTab(self._instVisa, 'Visa SCPI')
        for tabName in ['Parameters', 'Code', 'Methods', 'Visa SCPI']:
            self._tabs.setNotClosable(tabName)
            self._tabs.setNotFloatable(tabName)
        self._tabs.setMinimumWidth(550)
        splitter.addWidget(self._tabs)

        self.setCentralWidget(splitter)

        ##################
        # Initialization #
        ##################

        self._instrHandle = None   # current instrument handle

        # load persistent platform-independent application settings if any
        settings = QSettings()
        if settings.contains("instrumentManager.rootDirectory"):
            setupPath = str(settings.value("instrumentManager.rootDirectory").toString())
            instrumentMgr.setInstrumentsRootDir(setupPath)

        # load instrument states from a file
        """self._picklePath = setupPath + r"\config\setups.pickle"
        self.loadStates()"""

        # create a dictionary of frontpanels because the backend instrument manager does not manage them
        self._frontpanels = dict()

        self.connect(self._instrList, SIGNAL("currentItemChanged(QTreeWidgetItem *,QTreeWidgetItem *)"), self.selectInstr)
        self.updateInstrumentsList()
        # self.updateStateList()

    # root and  working directory management

    def setRootDirectory(self, directory=None):
        """
        Sets the root directory for instruments.
        """
        self.debugPrint("in InstrumentManagerPanel.setRootDirectory()")
        settings = QSettings()
        if directory is None:
            directory = self._helper.instrumentsRootDir()
            if directory is None:
                directory = ''
            path = QFileDialog.getExistingDirectory(self, "Select root diretory for instruments", directory=directory)
        if not os.path.exists(path):
            return
        self._helper.setInstrumentsRootDir(path)
        settings.setValue("instrumentManager.rootDirectory", path)
        settings.sync()  # commit immediately (in case of unexpected future error and freezing)

    def workingDirectory(self):
        """
        Returns the current working directory.
        """
        self.debugPrint("in InstrumentManagerPanel.workingDirectory()")
        return self._helper.currentWorkingDir()

    def setWorkingDirectory(self, directory):
        """
        Sets the current working directory.
        """
        self.debugPrint("in InstrumentManagerPanel.setWorkingDirectory(directory) with directory=", directory)
        if os.path.isdir(directory):
            self._helper.setCurrentWorkingDir(directory)

    # opening and saving list of instruments

    def openList(self):
        """
        Opens ...
        """
        self.debugPrint("in InstrumentManagerPanel.openList()")
        # choose the file
        filename = str(QFileDialog.getOpenFileName(caption='Open instrument list file',
                                                   filter="Instrument list file (*.inl)", directory=self.workingDirectory()))
        if filename != '':
            # import the file that should define an attribute instruments, and call
            # the instrument manager loadInstruments method
            self.setWorkingDirectory(os.path.dirname(filename))
            basename = os.path.basename(filename)
            fn = imp.load_source(basename, filename)
            if hasattr(fn, 'instruments') and isinstance(fn.instruments, list):
                self._helper.loadInstruments(fn.instruments, globalParameters={'forceReload': True})
            else:
                raise 'No list with name instruments defined in file ' + filename + '.'

    def saveList(self):
        """
        Saves ...
        """
        self.debugPrint("in InstrumentManagerPanel.saveList()")
        pass

    # opening or closing an instrument

    def openInst(self):
        """
        Prompt for an instrument file and opens it.
        """
        self.debugPrint("in InstrumentManagerPanel.openInst()")
        # choose the file
        filePath = str(QFileDialog.getOpenFileName(caption='Open instrument file',
                                                   filter="Instrument list file (*.py)", directory=self.workingDirectory()))
        if filePath != '':
            self.setWorkingDirectory(os.path.dirname(filePath))
            self._helper.loadInstrumentFromFilePath(None, filePath, args=[], kwargs={})

    def closeInst(self):
        """
        Closes the instruments selected in self._instrList
        """
        self.debugPrint("in InstrumentManagerPanel.closeInst()")
        indices = [index.row() for index in self._instrList.selectedIndexes()]
        msg = QMessageBox('Instrument manager')
        msg.setIcon(QMessageBox.Warning)
        msg.setText('Remove selected instruments?')
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        ret = msg.exec_()
        if ret == QMessageBox.Ok:
            self._helper.removeInstruments(indices, True)

    # Saving and restoring setups

    def restoreSetup(self):
        """
        Restores the configuration...
        """
        self.debugPrint("in InstrumentManagerPanel.restoreSetup()")
        name = str(self.setupList.currentText())
        if name in self._states:
            self._helper.restoreState(self._states[name])

    def removeSetup(self):
        """
        ???
        """
        self.debugPrint("in InstrumentManagerPanel.removeSetup()")
        message = QMessageBox()
        message.setWindowTitle("Confirm Setup Deletion")
        message.setIcon(QMessageBox.Question)
        name = str(self.setupList.currentText())
        if name in self._states:
            message.setText(
                "Do you really want to remove setup \"%s\"?" % name)
            message.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)
            message.setDefaultButton(QMessageBox.Cancel)
            result = message.exec_()
            if result == QMessageBox.Cancel:
                return
            del self._states[name]
        self.updateStateList()

    def saveSetup(self):
        """
        Saves...
        """
        self.debugPrint("in InstrumentManagerPanel.saveSetup()")
        name = str(self.setupList.currentText())
        # Sanitize the name of the setup...
        valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        name = ''.join(c for c in name if c in valid_chars)
        if name == "":
            return
        state = self._helper.saveState(name, withInitialization=False)
        self._states[name] = state
        self.saveStates()
        self.updateStateList()
        self.setupList.setCurrentIndex(self.setupList.findText(name))

    # updating gui

    def updatedGui(self, subject=None, property=None, value=None):
        """
        Updates the GUI when the panel receives notifications.
        """
        self.debugPrint("in InstrumentManagerPanel.updatedGui() with subject=",
                        subject, " property=", property, " and value=", value)
        if subject == self._helper:
            if property in ['new_instrument', 'removed_instruments']:        # value is the instrument handle
                self.updateInstrumentsList()
                if self._instrHandle is value:
                    self.propagateInstrHandle(value)
            elif property == "initialized":          # value is the instrument handle
                if self._instrHandle is value:
                    self._instProp.setInstrHandle(value)

    def updateInstrumentsList(self):
        """
        Rebuilds the QTreeWidget instrument list form the list of instruments self._helper.instruments().
        """
        self.debugPrint("in InstrumentManagerPanel.updateInstrumentsList()")
        li = self._instrList
        li.clear()
        for index, instrument in enumerate(self._helper.instruments()):
            item = QTreeWidgetItem()
            item.setText(0, instrument.name())
            li.addTopLevelItem(item)
            if isinstance(instrument, CompositeInstrument):         # if CompositeInstrument
                for childName in instrument.childrenNames():    # add children at level of the tree
                    childItem = QTreeWidgetItem(item)
                    childItem.setText(0, childName)

    def reloadInstruments(self):
        """
        Reload the intruments selected in the QTreeWidget instrument list (not the frontpanel).
        """
        self.debugPrint("in InstrumentManagerPanel.reloadInstruments()")
        indices = [index.row() for index in self._instrList.selectedIndexes()]
        self._helper.reloadInstruments(indices)

    # frontpanels management

    def loadFrontpanel(self, instrument, show=True):
        """
        Ask the instrument manager to load the frontpanel of instrument instrument (if not already loaded) and adds it to the frontpanel dictionary self._frontpanels.
        """
        self.debugPrint("in InstrumentManagerPanel.loadFrontpanel(name) with name=", name)
        frontpanel = self._helper.frontpanel(name)
        if frontpanel is not None:
            self._frontpanels[name] = frontpanel
            if show:
                frontpanel.show()

    def dockFrontpanel(self, name, show=True):
        """
        Docks a frontpanel in self._tabs.
        The frontpanel can be initially in an independant QMainWindow, in a flotting DockToTabWidget, or already be docked.
        Makes the tab active
        """
        self.debugPrint("in InstrumentManagerPanel.dockFrontpanel(name) with name=", name)
        if name not in self._frontpanels:
            return
        frontpanel = self._frontpanels[name]
        loadInstrumentsabs.indexOf(frontpanel)
        if index != -1:                                           # instrument panel is already in a tab
            if show:
                # => make active this tab if show is True
                self._tabs.setCurrentIndex(index)
        # panel is in a floating DockToTabWidget
        elif isinstance(frontpanel.parent(), DockToTabWidget):
            frontpanel.parent().show()
            frontpanel.parent().setFloating(True)
            # => dock the widget of DockToTabWidget back to DockingTabWidget.
            frontpanel.parent().dockToTab()
        else:                                                   # panel is NOT in a floating DockToTabWidget
            # => add it in a new tab of to self._tab
            panelName = name + ' panel'
            self._tabs.addTab(frontpanel, QString(panelName))
            if show:
                self._tabs.setCurrentWidget(frontpanel)

    def showFrontpanel(self, name):
        """
        Show the frontpanel with name name.
        """
        self.debugPrint("in InstrumentManagerPanel.showFrontpanel(name) with name=", name)
        frontpanel = self._frontpanels[name]
        frontpanel.show()
        frontpanel.activateWindow()

    def closeFrontpanel(self, name):
        """
        Closes the frontpanel with name name.
        """
        self.debugPrint("in InstrumentManagerPanel.closeFrontpanel()")
        self._frontpanels[name].close()
        del self._frontpanels[name]

    def loadShowFrontpanels(self, forceReload=False):
        """
        Show the frontpanels of selected instruments.
        """
        self.debugPrint("in InstrumentManagerPanel.loadShowFrontpanels()")
        indices = [index.row() for index in self._instrList.selectedIndexes()]
        for index in indices:
            self.loadShowFrontpanel(index, forceReload=forceReload)

    def loadShowFrontpanel(self, index, forceReload=False):
        """
        Show the frontpanel of instrument name.
        """
        if name not in self._frontpanels or forceReload:
            self.loadFrontpanel(name, show=False)
        self.dockFrontpanel(name)

    def saveStates(self, path=None):
        """
        ???
        """
        self.debugPrint("in InstrumentManagerPanel.saveStates(path) with path=", path)
        if path is None:
            path = self._picklePath
        string = yaml.dump(self._states)
        stateDir = os.path.dirname(path)
        if not os.path.exists(stateDir):
            os.mkdir(stateDir)
        file = open(path, "w")
        file.write(string)
        file.close()

    def loadStates(self, path=None):
        """
        Loads instrument states from a file
        """
        self.debugPrint(
            "in InstrumentManagerPanel.loadStates(path) with path=", path)
        if path is None:
            path = self._picklePath
        if os.path.exists(path):
            try:
                file = open(path, "r")
                string = file.read()
                self._states = yaml.load(string)
            except:
                print "Failed to load instrument setups!"
                traceback.print_exc()
                self._states = dict()
        else:
            self._states = dict()

    def updateStateList(self):
        """
        ???
        """
        self.debugPrint("in InstrumentManagerPanel.updateStateList()")
        self.setupList.clear()
        for name in self._states.keys():
            self.setupList.addItem(name, name)

    def selectInstr(self, new, previous):
        """
        Set current instrument handle self._instrHandle to the handle of the selected instrument.
        Called when a new item is selected in the QTreeWidget of instruments.
        """
        self.debugPrint('in InstrumentManagerPanel.selectInstr() with current instr =',
                        new, ' and last instr=', previous)
        handle = None
        if new is not None:
            try:
                handle = self._helper.instrumentHandles().withName(str(new.text(0)))[0]
            except:
                pass
        self._instrHandle = handle
        self.propagateInstrHandle(handle)

    def propagateInstrHandle(self, handle):
        for obj in [self._instProp, self._instHelp, self._instCode, self._instVisa]:
            obj.setInstrHandle(handle)


class InstrumentList(QTreeWidget):
    """
    This is the QWidget to display instruments in the Instrument Manager GUI.
    """

    def mouseDoubleClickEvent(self, e):
        QTreeWidget.mouseDoubleClickEvent(self, e)  # propagate
        # emit signal showFrontPanel
        self.emit(SIGNAL("loadShowFrontpanels()"))

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        renameAction = menu.addAction('Rename instrument...')
        reloadAction = menu.addAction('Reload selected instruments')
        loadPanelAction = menu.addAction("Load panels of selected instruments ")
        menu.addSeparator()
        setStateAction = menu.addAction('Set instrument state...')
        saveStateAction = menu.addAction('Save instrument state as...')
        menu.addSeparator()
        removeAction = menu.addAction('Remove selected instrument')
        action = menu.exec_(self.viewport().mapToGlobal(event.pos()))
        if action == renameAction:
            pass
        elif action == reloadAction:
            self.emit(SIGNAL('reloadInstruments()'))
        elif action == loadPanelAction:
            self.emit(SIGNAL('loadShowFrontpanels()'))
        elif action == setStateAction:
            pass
        elif action == saveStateAction:
            pass
        elif action == removeAction:
            self.emit(SIGNAL('closeInst()'))


class InstrProperty(QWidget):
    """
    This is the QWidget for displaying/managing the parameters of an instrument in the Instrument Manager GUI
    """

    def __init__(self, instrumentMgr=None):
        """
        Creator. Sets up the GUI.
        """
        QWidget.__init__(self)

        self._instrumentMgr = instrumentMgr
        self._instrHandle = None

        lineEditList = ['_instrName', '_moduleName', '_fullPath', '_serverAdress']
        for lineEdit in lineEditList:
            setattr(self, lineEdit, QLineEdit())
            getattr(self, lineEdit).setReadOnly(True)
        self._remote = QCheckBox('Remote')
        self._remote.setEnabled(False)
        tables = self._args, self._kwargs, self._params = (
            QTableWidget(0, 2), QTableWidget(0, 2), QTableWidget(50, 2))
        for table in tables:
            table.setHorizontalHeaderLabels(['Param. name', 'Value'])
            table.setColumnWidth(0, 100)
            table.horizontalHeader().setStretchLastSection(True)
            table.setMaximumHeight(250)
        subLayout1 = QGridLayout()
        subLayout1.setSpacing(4)
        subLayout1.addWidget(QLabel('Instrument name:'), 0, 0)
        subLayout1.addWidget(self._instrName, 0, 1)
        subLayout1.addWidget(QLabel('Module name:'), 0, 2)
        subLayout1.addWidget(self._moduleName, 0, 3)
        subLayout1.addWidget(QLabel('Path:'), 1, 0)
        subLayout1.addWidget(self._fullPath, 1, 1, 1, 3)
        subLayout1.addWidget(self._remote, 2, 0)
        subLayout1.addWidget(QLabel('server address:'), 2, 1)
        subLayout1.addWidget(self._serverAdress, 2, 2)

        subLayout2 = QGridLayout()
        subLayout2.setSpacing(4)
        subLayout2.addWidget(QLabel('Initialization arguments:'), 0, 0)
        subLayout2.addWidget(self._args, 1, 0)
        subLayout2.addWidget(QLabel('Initialization keyword arguments:'), 2, 0)
        subLayout2.addWidget(self._kwargs, 3, 0)

        subLayout3 = QHBoxLayout()
        initializeButton = QPushButton('(Re-)Initialize')
        self.connect(initializeButton, SIGNAL('clicked()'), self.initialize)
        subLayout3.addWidget(initializeButton)
        self._initialized = QCheckBox('initialized')
        self._initialized.setEnabled(False)
        subLayout3.addWidget(self._initialized)

        layout1 = QVBoxLayout()
        layout1.addLayout(subLayout1)
        layout1.addLayout(subLayout2)
        layout1.addLayout(subLayout3)
        self.initParamGBox = QGroupBox('Initialization parameters')
        self.initParamGBox.setLayout(layout1)

        layout2 = QVBoxLayout()
        layout2.addWidget(self._params)
        self.instrParamGBox = QGroupBox('Instrument parameters')
        self.instrParamGBox.setLayout(layout2)

        layout = QVBoxLayout()
        layout.addWidget(self.initParamGBox)
        layout.addWidget(self.instrParamGBox)
        self.setLayout(layout)

    def setInstrHandle(self, instrHandle):
        """
        Sets the _instrHandle attribute
        """
        self._instrHandle = instrHandle  # this is an InstrumentHandle
        self.update()

    def update(self):
        """
        update all gui elements using the instrument handle and the intrument's code.
        """
        handle = self._instrHandle
        for table in [self._args, self._kwargs, self._params]:
            table.clearContents()
        for table in [self._args, self._kwargs]:
            table.setRowCount(0)
        if handle is None:
            return

        instrument = handle['instrument']
        self._instrName.setText(handle.name())
        self._moduleName.setText(QString(handle['moduleName']))
        remote = handle['remoteServer'] is not None
        self._remote.setChecked(remote)
        if remote:
            self._serverAdress.setVisible(True)
            server = handle['remoteServer']
            self._serverAdress.setText(QString(server.ip() + ':' + str(server.port())))
        else:
            self._serverAdress.clear()
            self._serverAdress.setVisible(False)
            self._fullPath.setText(QString(handle['fullPath']))

        args, kwargs = [], {}
        if instrument.initialized:
            args = handle['args']
            kwargs = handle['kwargs']
        argNames, kwargsCode = instrument.getInitializationArgs()

        self._args.setRowCount(len(argNames))
        for index, argName in enumerate(argNames):
            value = '?'
            if instrument.initialized:
                value = args[index]
            item = QTableWidgetItem(argName)
            item.setFlags(Qt.ItemIsEnabled)
            self._args.setItem(index, 0, item)
            self._args.setItem(index, 1, QTableWidgetItem(str(value)))

        self._kwargs.clearContents()
        self._kwargs.setRowCount(len(kwargsCode))
        index = 0
        for key, value in kwargsCode.iteritems():
            if instrument.initialized:
                value = kwargs[key]
            valueString = str(value)
            if isinstance(value, str):
                valueString = "'" + valueString + "'"
            item = QTableWidgetItem(key)
            item.setFlags(Qt.ItemIsEnabled)
            self._kwargs.setItem(index, 0, item)
            self._kwargs.setItem(index, 1, QTableWidgetItem(valueString))
            index += 1

        self._initialized.setChecked(instrument.initialized)

    def initialize(self):
        """
        Calls the initializeInstrument() method of the instrument manager with the current instrument.
        (self.update() will be called back through a notification)
        """
        if self._instrHandle is not None and self._instrumentMgr is not None:
            args, kwargs = self.buildArgsKwargs()
            self._instrumentMgr.initializeInstrument(self._instrHandle, args=args, kwargs=kwargs)

    def buildArgsKwargs(self):
        """
        Builds the args and kwargs functional arguments from the QTableWidget
        """
        args = [eval(str(self._args.item(i, 1).text())) for i in range(self._args.rowCount())]
        kwargs = {}
        for i in range(self._kwargs.rowCount()):
            kwargs[str(self._kwargs.item(i, 0).text())] = eval(str(self._kwargs.item(i, 1).text()))
        # print args, [type(arg) for arg in args]
        # print kwargs, [type(arg) for key, arg in kwargs.iteritems()]
        return args, kwargs


class InstrHelpWidget(QWidget):
    """
    This is the QWidget for displaying/calling the methods and help of an instrument in the Instrument Manager GUI
    """
    # Initializes the widget.

    def __init__(self, parent=None):
        QWidget.__init__(self)

        self.myClass = QLineEdit()
        self.sourceFile = QLineEdit()
        self.generalHelp = QTextEdit()
        self.generalHelp.setAcceptRichText(True)
        self.generalHelp.setReadOnly(True)
        self.methods = QTreeWidget()
        self.methods.setHeaderLabels(['Public methods'])
        self.methods.setSortingEnabled(True)
        self.search = QLineEdit()
        self.methodHelp = QTextEdit()
        self.hideParentMethods = QCheckBox('Hide parent methods')
        self.hideParentMethods.setChecked(True)
        self.methodCall = QLineEdit()
        self.execute = QPushButton('Call')
        self.clearLog = QPushButton('Clear log')
        for button in [self.execute, self.clearLog]:
            button.setMaximumWidth(80)
        self.log = QTextEdit()
        self.methodHelp.setAcceptRichText(True)
        for item in [self.myClass, self.sourceFile, self.methodHelp]:
            item.setReadOnly(True)

        self.connect(self.hideParentMethods, SIGNAL('stateChanged(int)'), self.fillMethods)
        self.connect(self.methods, SIGNAL(
            "currentItemChanged(QTreeWidgetItem *,QTreeWidgetItem *)"), self.help)
        self.connect(self.search, SIGNAL("textEdited(QString)"), self.searchF)
        self.connect(self.methodCall, SIGNAL(
            "editingFinished()"), self.executeCommand)
        self.connect(self.execute, SIGNAL('clicked()'), self.executeCommand)
        self.connect(self.clearLog, SIGNAL('clicked()'), lambda: self.log.clear())

        classGroupBox = QGroupBox('Class information')
        layout1 = QGridLayout()
        layout1.addWidget(QLabel('Class:'), layout1.rowCount(), 0, 1, 1, Qt.AlignLeft)
        layout1.setColumnStretch(layout1.columnCount() - 1, 0)
        layout1.addWidget(self.myClass, layout1.rowCount() - 1, layout1.columnCount())
        layout1.addWidget(QLabel('Source:'), layout1.rowCount(), 0, 1, 1, Qt.AlignLeft)
        layout1.addWidget(self.sourceFile, layout1.rowCount() - 1, 1)
        layout1.setColumnStretch(layout1.columnCount() - 1, 4)
        layout1.addWidget(QLabel('Doc string:'), layout1.rowCount(), 0)
        self.generalHelp.setMaximumHeight(150)
        layout1.addWidget(self.generalHelp, layout1.rowCount(),
                          0, 1, layout1.columnCount())
        classGroupBox.setLayout(layout1)

        methodsGroupBox = QGroupBox('Methods')
        layout2 = QGridLayout()
        layout2.setSpacing(2)
        layout2.setColumnStretch(0, 0)
        layout2.setColumnStretch(1, 10)
        subLayout = QGridLayout()
        subLayout.setSpacing(2)
        self.methods.setMaximumWidth(200)
        subLayout.addWidget(self.methods, 0, 0, 1, 2)
        subLayout.addWidget(QLabel('search:'), 1, 0)
        self.search.setMaximumWidth(200)
        subLayout.addWidget(self.search, 1, 1)
        layout2.addItem(subLayout, 0, 0, 7, 1)
        layout2.addWidget(self.hideParentMethods, 0, 1)
        layout2.addWidget(QLabel('Doc string:'), 1, 1)
        self.methodHelp.setMaximumHeight(150)
        layout2.addWidget(self.methodHelp, 2, 1)
        layout2.addWidget(QLabel('Instrument method call:'), 3, 1)
        layout2.addWidget(self.methodCall, 4, 1)
        hBoxLayout = QHBoxLayout()
        hBoxLayout.setSpacing(10)
        hBoxLayout.addWidget(self.execute)
        hBoxLayout.addWidget(self.clearLog)
        hBoxLayout.addWidget(QLabel('Log:'))
        layout2.addItem(hBoxLayout, 5, 1)
        self.log.setMaximumHeight(300)
        layout2.addWidget(self.log, 6, 1)
        methodsGroupBox.setLayout(layout2)

        layout = QVBoxLayout()
        layout.addWidget(classGroupBox)
        layout.addWidget(methodsGroupBox)
        self.setLayout(layout)

        self._instrHandle = None

    def setInstrHandle(self, instrHandle):
        self._instrHandle = instrHandle
        self.update()

    def update(self):
        for item in [self.myClass, self.sourceFile, self.generalHelp, self.methods, self.methodCall, self.methodHelp]:
            item.clear()
        if self._instrHandle is None:
            return
        if self._instrHandle['remoteServer'] is not None:
            # self.myClass.setTextColor(QColor('Red'))
            self.myClass.setText(QString('Remote Instrument'))
            # self.myClass.setTextColor(QColor('Black'))
            return()
        self.fillClassSourceDoc()
        self.fillMethods()

    def fillClassSourceDoc(self):
        ins = self._instrHandle['instrument']
        clas = ins.getClass()
        if clas is None:
            clas = 'None'
        self.myClass.setText(QString(str(clas)))
        sourceFile = ins.getSourceFile()
        self.sourceFile.setText(QString(str(sourceFile)))
        doc = inspect.getdoc(ins)
        if doc is None:
            doc = 'No documentation string.'
        self.generalHelp.setText(QString(doc))

    def fillMethods(self):
        if self._instrHandle is None or self._instrHandle['remoteServer'] is not None:
            return
        self.methods.clear()
        ins = self._instrHandle['instrument']
        clas = ins.getClass()
        publicMethods = [method[0] for method in inspect.getmembers(
            clas, predicate=inspect.ismethod) if method[0][0] != '_']
        directMethods = [meth for meth in publicMethods if meth in clas.__dict__]
        for method in publicMethods:
            if method in directMethods or not self.hideParentMethods.isChecked():
                item = QTreeWidgetItem()
                if method not in directMethods:
                    item.setTextColor(0, QColor('blue'))
                item.setText(0, method)
                self.methods.insertTopLevelItem(self.methods.topLevelItemCount(), item)
        if self.methods.isSortingEnabled():
            self.methods.sortItems(0, self.methods.header().sortIndicatorOrder())

    def help(self, new, previous):
        self.methodHelp.clear()
        self.methodCall.clear()
        if new is None:
            return
        methodName = str(new.text(0))
        method = getattr(self._instrHandle['instrument'], methodName)
        if inspect.ismethod(method):
            # helpString=method.__doc__
            helpString = inspect.getdoc(method)
            if helpString is None:
                self.methodHelp.setTextColor(QColor('Red'))
                helpString = 'No doc string found.'
            argspec = inspect.getargspec(method)
        if argspec is None:
            definition = 'No definition found.'
        else:
            args, varargs, keywords, defaults = argspec
            # start to built the method call
            methodCall = methodName + '('
            # determine the number of arguments and keyword arguments
            nArgs = 0
            if args is not None:
                nArgs = len(args)
                nKwargs = 0
                if defaults is not None:
                    nKwargs = len(defaults)
                    nArgs -= nKwargs
                if nArgs != 0:                                # add arguments but self
                    if args[0] != 'self':
                        methodCall += ','.join(args[0: nArgs])
                        if nKwargs != 0:
                            methodCall += ','
                    elif nArgs > 1:
                        methodCall += ','.join(args[1: nArgs])
                        if nKwargs != 0 or varargs is not None or keywords is not None:
                            methodCall += ','
                if nKwargs != 0:                              # add keyword arguments
                    methodCall += ','.join([kwarg + '=' + str(default)
                                            for kwarg, default in zip(args[nArgs:], defaults)])
                    if varargs is not None or keywords is not None:
                        methodCall += ','
                if varargs is not None:
                    methodCall += '*' + varargs
                    if keywords is not None:
                        methodCall += ','
                if keywords is not None:
                    methodCall += '**' + keywords
                methodCall += ')'
            self.methodCall.setText(QString(methodCall))
            self.methodHelp.setText(QString(helpString))
            self.methodHelp.setTextColor(QColor('Black'))

    def searchF(self, qstr):
        if qstr.trimmed().isEmpty():
            self.methods.setSortingEnabled(True)
            # self.methods.sortItems(0,Qt.AscendingOrder)
        else:
            found = self.methods.findItems(qstr, Qt.MatchContains)
            if len(found) != 0:
                self.methods.setSortingEnabled(False)
                for item in found:
                    self.methods.takeTopLevelItem(
                        self.methods.indexOfTopLevelItem(item))
                self.methods.insertTopLevelItems(0, found)
                self.methods.setCurrentItem(found[0])

    def executeCommand(self):
        ins = self._instrHandle['instrument']
        commandQString = self.methodCall.text()
        error = None
        self.log.setTextColor(QColor('Black'))
        self.log.append(commandQString)
        try:
            returned = ins(str(commandQString))  # syntax compatible with remote instrument !
        except Exception as exception:
            error = exception
            returned = 'Error:\n' + str(error)
        color = 'Blue'
        if error:
            color = 'Red'
        self.log.setTextColor(QColor(color))
        self.log.append(QString(str(returned)))
        # if error is not None: raise error


class InstrCodeWidget(CodeEditor):
    """
    This is the QWidget for displaying the code of an instrument in the Instrument Manager GUI
    """
    # Initializes the widget.

    def __init__(self, parent=None):
        CodeEditor.__init__(self)
        self._instrHandle = None

    def setInstrHandle(self, instrHandle):
        self._instrHandle = instrHandle
        self.update()

    def update(self):
        if self._instrHandle is not None and not self._instrHandle['remoteServer'] is not None:
            name = self._instrHandle['module'].__file__
            path, basename = os.path.dirname(name), os.path.splitext(os.path.basename(name))[0]
            filename = path + '\\' + basename + '.py'
            self.openFile(filename)
        else:
            self.setPlainText('')


class InstrSCPIWidget(QWidget):
    """
    This is the QWidget for making SCPI calls in the Instrument Manager GUI
    """
    # Initializes the widget.

    def __init__(self, parent=None):
        QWidget.__init__(self)

        self._instrHandle = None

        self.visaAddress = QLineEdit()
        self.timeout = QDoubleSpinBox()
        self.connect(self.timeout, SIGNAL('valueChanged(double)'), self.setTimeout)
        clearDeviceButton = QPushButton('Clear device')
        self.connect(clearDeviceButton, SIGNAL('clicked()'), self.clearDevice)
        readButton = QPushButton('Read')
        self.connect(readButton, SIGNAL('clicked()'), self.myRead)
        writeButton = QPushButton('Write')
        self.connect(writeButton, SIGNAL('clicked()'), self.myWrite)
        askButton = QPushButton('Ask')
        self.connect(askButton, SIGNAL('clicked()'), self.myAsk)
        clearButton = QPushButton('Clear')
        self.connect(clearButton, SIGNAL('clicked()'), lambda: self.log.clear())
        self.messageOut = QLineEdit()
        self.messageOut.setText(QString('*IDN?'))
        self.log = QTextEdit()
        self.log.setAcceptRichText(True)
        self.log.setReadOnly(True)

        layout = QGridLayout()
        layout.addWidget(QLabel('Visa address:'), 0, 0)
        layout.addWidget(self.visaAddress, 0, 1)
        layout.addWidget(QLabel('Timeout (s):'), 0, 2)
        layout.addWidget(self.timeout, 0, 3)
        layout.addWidget(clearDeviceButton, 0, 4)

        subLayout1 = QVBoxLayout()
        subLayout1.addWidget(writeButton)
        subLayout1.addWidget(readButton)
        subLayout1.addWidget(askButton)
        subLayout1.addWidget(clearButton)
        subLayout1.addStretch()

        subLayout2 = QVBoxLayout()
        subLayout2.addWidget(self.messageOut)
        subLayout2.addWidget(self.log)

        layout.addLayout(subLayout1, 1, 0)
        layout.addLayout(subLayout2, 1, 1, 1, 4)
        self.setLayout(layout)

    def setInstrHandle(self, instrumentHandle):
        self._instrHandle = instrumentHandle
        self.update()

    def update(self):
        for item in [self.visaAddress, self.messageOut, self.log]:
            item.clear()
        if self._instrHandle is None:
            return
        if self._instrHandle['remoteServer'] is not None:
            self.visaAddress.setText('Remote instrument: dialog will work only if it is a VisaInstrument')
            self.messageOut.setText('*IDN?')
        elif isinstance(self._instrHandle['instrument'], VisaInstrument):
            visaAddress = self._instrHandle['instrument']._visaAddress
            self.timeout.setValue(10.)
            if visaAddress is not None:
                self.visaAddress.setText(str(visaAddress))
                self.messageOut.setText('*IDN?')
        self.setTimeout()

    def myWrite(self):
        self._instrHandle['instrument'].write(str(self.messageOut.text()))
        self.log.setTextColor(QColor('black'))
        self.log.append(commandQString)
        # self.messageOut.clear() # user might want send twice the same
        # commmand

    def myRead(self):
        str1 = self._instrHandle['instrument'].read()
        self.log.setTextColor(QColor('Blue'))
        self.log.append(QString(str1))

    def myAsk(self):
        self.myWrite()
        self.myRead()

    def setTimeout(self):
        self._instrHandle['timeout'] = 1000. * self.timeout.value()

    def clearDevice(self):
        self._instrHandle['instrument'].clear()


class InstrumentsArea(QMainWindow, ObserverWidget):
    """
    This is the QWindow to display a frontpanel intrument in the instrument Manager (in a tab or a separate window).
    """

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        ObserverWidget.__init__(self)

        self.setWindowTitle("Instruments")

        self._windows = dict()

        self.setAutoFillBackground(False)

        self._instrumentsArea = QMdiArea(self)

        self._instrumentsArea.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded)
        self._instrumentsArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.setCentralWidget(self._instrumentsArea)

    def area(self):
        return self._instrumentsArea

    def removeFrontPanel(self, frontPanel):
        if frontPanel in self._windows and self._windows[frontPanel] in self._instrumentsArea.subWindowList():
            self._instrumentsArea.removeSubWindow(self._windows[frontPanel])

    def addFrontPanel(self, frontPanel):
        widget = self._instrumentsArea.addSubWindow(frontPanel)
        self._windows[frontPanel] = widget
        widget.setWindowFlags(Qt.WindowSystemMenuHint | Qt.WindowTitleHint |
                              Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)

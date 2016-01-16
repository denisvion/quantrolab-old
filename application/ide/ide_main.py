"""
Main module of the quantrolab application defining the IDE and the Log classes.
It also starts the IDE when called as main.
"""
# imports

import sys,imp
import os, os.path
import inspect
import pyclbr
import yaml
import re
import random
import time

from PyQt4.QtGui import *
from PyQt4.QtCore import *

import application.lib.objectmodel as objectmodel                     # file directory object model
from application.lib.helper_classes import *                          # helper classes

from application.ide.editor.codeeditor import *
from application.ide.threadpanel import *
from application.ide.project import Project,ProjectModel,ProjectView  # project management and display
from application.ide.coderun.coderunner import MultiProcessCodeRunner # Code runner of the IDE
#from application.ide.coderun.coderunner_gui import execInGui           # Utility function to run a Qt helper in the coderunner process
from application.ide.widgets.observerwidget import ObserverWidget     # QtWidget being notified in its Qt event queue
from application.ide.helpermanager import HelperManager               # helper management

# important directories
from application.config.parameters import params                      # module containing directory parameters
_applicationDir=params['basePath']
_configDefaultDir=params['configPath']
_helpersDefaultDir=os.path.join(_applicationDir,'helpers')

# version
__version__=''
try:
  from application._version import __version__
except:
  print 'Could not find the application version.'

# splash screen
splashFile=QString(_applicationDir+'\quantrolab.png')

class Log(LineTextWidget):
  """
  Log text window.
  To do:
    -Add a context menu with a "clear all" menu entry
    -Add a search function
  """

  def __init__(self,queue,ide=None,tabID=0,parent = None):
      self._ide=ide
      self._queue=queue
      self._tabID=tabID
      LineTextWidget.__init__(self,parent)
      MyFont = QFont("Courier",10)
      MyDocument = self.document()
      MyDocument.setDefaultFont(MyFont)
      self.setDocument(MyDocument)
      self.setMinimumHeight(200)
      self.setReadOnly(True)
      self.timer = QTimer(self)     # instantiate a timer in this LineTextWidget
      self._writing = False
      self.timer.setInterval(20)   # set its timeout to 0.3s
      self.queuedStdoutText = ""    #initialize a Stdout queue to an empty string
      self.queuedStderrText = ""    #initialize a Stderr queue to an empty string
      self.connect(self.timer,SIGNAL("timeout()"),self.addQueuedText)
                                    # call addQueuedText() every timeout
      self.timer.start()            # start the timer
      self.cnt=0
      self._timeOfLastMessage=0
      self._hasUnreadMessage=False

  def clearLog(self):
    self.clear()

  def contextMenuEvent(self,event):
    MyMenu = self.createStandardContextMenu()
    MyMenu.addSeparator()
    clearLog = MyMenu.addAction("clear log")
    self.connect(clearLog,SIGNAL("triggered()"),self.clearLog)
    MyMenu.exec_(self.cursor().pos())

  def addQueuedText(self):
        self._ide.logTabs.setTabIcon(self._ide.logTabs.currentIndex(),QIcon())
        if self._tabID == self._ide.logTabs.currentIndex():
          self._hasUnreadMessage=False
        #else:
        #  if time.time()-2>self._timeOfLastMessage and self._hasUnreadMessage:
        #    self._ide.logTabs.setTabIcon(self._tabID,self._ide._icons['logo'])
        #print self._tabID
        #print str(self._hasUnreadMessage)

        try:
          message=''
          try:
            while(True):
              message+=self._queue.get(True,0.01)
          except:
            pass
          if message != '':
            self.moveCursor(QTextCursor.End)
            if len(message)>0:
              self._hasUnreadMessage=True
            if self._ide.logTabs.currentIndex() != self._tabID:
              self._ide.logTabs.setTabIcon(self._tabID,self._ide._icons['killThread'])
              self._timeOfLastMessage=time.time()
            self.textCursor().insertText(message)
            self.moveCursor(QTextCursor.End)
        except:
          pass

class IDE(QMainWindow,ObserverWidget):

  """
  The main Quantrolab IDE class.
  """

  def __init__(self,parent=None):
      """
      IDE's GUI definition and call of initialize
      """
      print "defining IDE's GUI..."
      QMainWindow.__init__(self,parent)
      ObserverWidget.__init__(self)
     # beginning of GUI definition  +  MultiProcessCodeRunner,CodeEditorWindow, Log, and errorConsole instantiation
      self._windowTitle = "QuantroLab python IDE\t"
      self.setWindowTitle(self._windowTitle)
      self.setDockOptions(QMainWindow.AllowTabbedDocks)
      self.LeftBottomDock = QDockWidget()
      self.LeftBottomDock.setWindowTitle("Log")
      self.RightBottomDock = QDockWidget()
      self.RightBottomDock.setWindowTitle("File Browser")

      self._timer = QTimer(self)
      self._runningCodeSessions = []
      self._timer.setInterval(500)
      self.connect(self._timer,SIGNAL("timeout()"),self.onTimer)
      self._timer.start()

      self.initializeIcons()

      self._gv = dict() # this is the global variable dictionary of the Quantrolab application, to be shared with its helpers and scripts.
      self._gv['from_main']=1   # test to be deleted
      print 'starting code runner...',
      self._codeRunner = MultiProcessCodeRunner(gv = self._gv,lv = self._gv) # The Process will have only a copy of self._gv
      print 'OK'
      print 'starting editor...',
      self.editorWindow = CodeEditorWindow(parent=self,newEditorCallback = self.newEditorCallback)   # tab editor window
      print 'OK'
      print 'starting error console...',
      self.errorConsole = ErrorConsole(codeEditorWindow = self.editorWindow,codeRunner = self._codeRunner)
      print 'OK'
      self.logTabs = QTabWidget()
      stdoutLog = Log(self._codeRunner.stdoutQueue(),ide=self,tabID=0)
      self.logTabs.addTab(stdoutLog,"&Log")
      stderrLog = Log(self._codeRunner.stderrQueue(),ide=self,tabID=1)
      self.logTabs.addTab(stderrLog,"&Error")

      verticalSplitter = QSplitter(Qt.Vertical)       # outer verticalsplitter
      horizontalSplitter = QSplitter(Qt.Horizontal)   # upper horizontal splitter in outer splitter
      self.tabs = QTabWidget()                        # empty tabs for future project /thread
      self.tabs.setMaximumWidth(350)
      horizontalSplitter.addWidget(self.tabs)         # add the project/thread tabs
      horizontalSplitter.addWidget(self.editorWindow) # add the tabs editor window
      verticalSplitter.addWidget(horizontalSplitter)
      verticalSplitter.addWidget(self.logTabs)        # add the log/error window
      verticalSplitter.setStretchFactor(0,2)

      self.projectWindow = QWidget()                  # create the project tab with its toolbar menu
      self.projectTree = ProjectView()
      self.projectModel = ProjectModel(objectmodel.Folder("[project]"))
      self.projectTree.setModel(self.projectModel)
      self.projectToolbar = QToolBar()

      newFolder = self.projectToolbar.addAction("New Folder")
      edit = self.projectToolbar.addAction("Edit")
      delete = self.projectToolbar.addAction("Delete")

      self.connect(newFolder,SIGNAL("triggered()"),self.projectTree.createNewFolder)
      self.connect(edit,SIGNAL("triggered()"),self.projectTree.editCurrentItem)
      self.connect(delete,SIGNAL("triggered()"),self.projectTree.deleteCurrentItem)

      layout = QGridLayout()
      layout.addWidget(self.projectToolbar)
      layout.addWidget(self.projectTree)

      self.projectWindow.setLayout(layout)
                                                      # create the thread panel tab
      self.threadPanel = ThreadPanel(codeRunner = self._codeRunner,editorWindow = self.editorWindow)

      self.tabs.addTab(self.projectWindow,"Project")  # create the project and thread tabs to the empty tabs
      self.tabs.addTab(self.threadPanel,"Threads")
      self.connect(self.projectTree,SIGNAL("openFile(PyQt_PyObject)"),lambda filename: self.editorWindow.openFile(filename))

      StatusBar = self.statusBar()
      self.workingPathLabel = QLabel("Working path: ?")
      StatusBar.addWidget(self.workingPathLabel)

      self.setCentralWidget(verticalSplitter)

      self.setWindowIcon(self._icons["logo"])

      self.initializeIcons()
      self.initializeMenus()
      self.initializeToolbars()

      # end of GUI definition
      self._workingDirectory = None

      print 'Future messages will be routed to GUI'

      sys.stdout = self._codeRunner._stdoutProxy
      sys.stderr = self._codeRunner._stderrProxy
      try:
        sys.sdtout = self._codeRunner.stdoutQueue()
        sys.sdterr = self._codeRunner.stderrQueue()
      except:
        raise
      finally:
        pass

      self.showMaximized()
      self.initialize()

  def initializeIcons(self):
    self._icons = dict()

    iconFilenames = {
      "newFile"             :'filenew.png',
      "openFile"            :'fileopen.png',
      "saveFile"            :'filesave.png',
      "saveFileAs"          :'filesaveas.png',
      "closeFile"           :'fileclose.png',
      "exit"                :'exit.png',
      "workingPath"         :'gohome.png',
      "killThread"          :'stop.png',
      "executeAllCode"      :'runfile.png',
      "executeCodeBlock"    :'runblock.png',
      "executeCodeSelection":'runselection.png',
      "logo"                :'penguin.png',
    }

    iconPath = params['basePath'] + params['directories.icons']

    for key in iconFilenames:
      self._icons[key] = QIcon(iconPath + '/' + iconFilenames[key])

  def initializeMenus(self):

    settings=QSettings()
    menuBar = self.menuBar()

    fileMenu = menuBar.addMenu("&File")
    projectNew = fileMenu.addAction(self._icons["newFile"],"New project")
    projectNew.setShortcut(QKeySequence("Ctrl+Shift+N"))
    projectOpen = fileMenu.addAction(self._icons["openFile"],"Open project...")
    projectOpen.setShortcut(QKeySequence("Ctrl+Shift+O"))
    projectSave = fileMenu.addAction(self._icons["saveFile"],"Save &project")
    projectSave.setShortcut(QKeySequence("Ctrl+Shift+S"))
    projectSaveAs = fileMenu.addAction(self._icons["saveFileAs"],"Save project as...")
    projectSaveAs.setShortcut(QKeySequence("CTRL+Shift+F12"))

    fileMenu.addSeparator()

    fileNew = fileMenu.addAction(self._icons["newFile"],"&New file")
    fileNew.setShortcut(QKeySequence("Ctrl+n"))
    fileOpen = fileMenu.addAction(self._icons["openFile"],"&Open file...")
    fileOpen.setShortcut(QKeySequence("Ctrl+o"))
    fileClose = fileMenu.addAction(self._icons["closeFile"],"&Close file")
    fileClose.setShortcut(QKeySequence("Ctrl+F4"))
    fileSave = fileMenu.addAction(self._icons["saveFile"],"&Save file")
    fileSave.setShortcut(QKeySequence("Ctrl+s"))
    fileSaveAs = fileMenu.addAction(self._icons["saveFileAs"],"Save file &as...")
    fileSaveAs.setShortcut(QKeySequence("Ctrl+F12"))

    fileMenu.addSeparator()
    filePrefs = fileMenu.addAction("&Preferences...")

    fileMenu.addSeparator()

    fileExit = fileMenu.addAction(self._icons["exit"],"Quitter")
    fileExit.setShortcut(QKeySequence("ALT+F4"))

    self.connect(fileNew, SIGNAL('triggered()'), self.editorWindow.newEditor)
    self.connect(fileOpen, SIGNAL('triggered()'), self.editorWindow.openFile)
    self.connect(fileClose, SIGNAL('triggered()'), self.editorWindow.closeCurrentFile)
    self.connect(fileSave, SIGNAL('triggered()'), self.editorWindow.saveCurrentFile)
    self.connect(fileSaveAs, SIGNAL('triggered()'), self.editorWindow.saveCurrentFileAs)
    self.connect(fileExit, SIGNAL('triggered()'), self.close)

    self.connect(projectNew, SIGNAL('triggered()'), self.newProject)
    self.connect(projectOpen, SIGNAL('triggered()'), self.openProject)
    self.connect(projectSave, SIGNAL('triggered()'), self.saveProject)
    self.connect(projectSaveAs, SIGNAL('triggered()'), self.saveProjectAs)

    fileMenu.addSeparator()

    #self.editMenu = menuBar.addMenu("Edit")
    # self.viewMenu = menuBar.addMenu("View")

    self.helpersMenu = menuBar.addMenu("&Helpers")
    self.buildHelperMenu()

    self.codeMenu = menuBar.addMenu("&Code")

    #self.settingsMenu = menuBar.addMenu("Settings")
    #self.runStartupGroup = self.settingsMenu.addAction("Run startup group at startup")
    #self.runStartupGroup.setCheckable(True)
    #self.connect(self.runStartupGroup, SIGNAL('triggered()'), self.toggleRunStartupGroup)
    #if settings.contains('ide.runStartupGroup'):
    #self.runStartupGroup.setChecked(settings.value('ide.runStartupGroup').toBool())

    self.windowMenu = menuBar.addMenu("&Window")
    self.connect(self.windowMenu,SIGNAL('aboutToShow()'),self.buildWindowMenu)
    self.connect(self.windowMenu,SIGNAL('triggered(QAction*)'),self.selectTab)      # Only menu is connected and will pass the action to selectTab.
    self.helpMenu = menuBar.addMenu("Help")
    about = self.helpMenu.addAction('&About')
    self.connect(about, SIGNAL('triggered()'), self.showAbout)
    debug = self.helpMenu.addAction('&Debug')
    self.connect(debug, SIGNAL('triggered()'), self.debug)

    restartCodeRunner = self.codeMenu.addAction("&Restart Code Process")
    self.connect(restartCodeRunner,SIGNAL("triggered()"),self.restartCodeProcess)
    self.codeMenu.addSeparator()
    runFiles=self.codeMenu.addAction(self._icons["executeAllCode"],"Run &File(s)")
    runFiles.setShortcut(QKeySequence("CTRL+Enter"))
    runBlock=self.codeMenu.addAction(self._icons["executeCodeBlock"],"Run &Block")
    runSelection=self.codeMenu.addAction(self._icons["executeCodeSelection"],"Run &Selection")
    self.connect(runFiles, SIGNAL('triggered()'), self.runFiles)
    self.connect(runBlock, SIGNAL('triggered()'), self.runBlock)
    self.connect(runSelection, SIGNAL('triggered()'), self.runSelection)

  def initialize (self):
    """
    IDE initialization (after having defined the GUI).
    """
    self.queuedText = ""

    print "Loading settings...",
    settings = QSettings()
    if settings.contains('ide.workingpath'):
      self.changeWorkingPath(settings.value('ide.workingpath').toString())
    print 'done.'
    #self.logTabs.show()

    print "Loading project...",
    self.setProject(Project())
    lastProjectOpened=False
    if settings.contains("ide.lastproject"):
      try:
        self.openProject(str(settings.value("ide.lastproject").toString()))
        lastProjectOpened=True
        print 'done.'
      except:
        print('Cannot open last project: %s.' % str(settings.value("ide.lastproject").toString()))

    self._helpersRootDir =_helpersDefaultDir
    if settings.contains('ide.helpersRootDir'):
      self._helpersRootDir = settings.value('ide.helpersRootDir').toString()

    self._helperManager = HelperManager(self,self._helpersRootDir,self.executeCode)
    self.buildHelperMenu() # rebuild menu because 'load helper' is added to the menu only if a _helperManager exists.
    self._helpers={}

  def fileBrowser(self):
    """

    """
    return self.FileBrowser

  def directory(self):
    """
    """
    return self.FileBrowser.directory()

  def saveProjectAs(self):
    filename = QFileDialog.getSaveFileName(caption='Save project as',filter = "project (*.prj)",directory = self.workingDirectory())
    if filename != '':
      self._project.saveToFile(filename)
      self.setWorkingDirectory(filename)
      self.updateWindowTitle()
      return True
    else:
      return False

  def saveProject(self):
    if self._project.filename() != None:
      self._project.saveToFile(self._project.filename())
      self.updateWindowTitle()
      return True
    else:
      return self.saveProjectAs()

  def workingDirectory(self):
    if self._workingDirectory is None:
      return os.getcwd()
    return self._workingDirectory

  def setWorkingDirectory(self,filename):
    if filename != None:
      directory = os.path.dirname(str(filename))
      self._workingDirectory = directory
    else:
      self._workingDirectory = None

  def newProject(self):
    if self._project.hasUnsavedChanges():
      MyMessageBox = QMessageBox()
      MyMessageBox.setWindowTitle("Warning!")
      MyMessageBox.setText("The current project has unsaved changed? Do you want to continue?")
      yes = MyMessageBox.addButton("Yes",QMessageBox.YesRole)
      no = MyMessageBox.addButton("No",QMessageBox.NoRole)
      MyMessageBox.exec_()
      choice = MyMessageBox.clickedButton()
      if choice == no:
        return False
    self.setProject(Project())
    return True

  def openProject(self,filename = None):
    if filename is None:
      filename = QFileDialog.getOpenFileName(caption='Open project as',filter = "Project (*.prj)",directory = self.workingDirectory())
    if os.path.isfile(filename):
        if self.newProject() == False:
          return False
        project = Project()
        project.loadFromFile(filename)
        self.setWorkingDirectory(filename)
        self.setProject(project)
        return True
    return False

  def closeEvent(self,e):
    self.editorWindow.closeEvent(e)

    if not e.isAccepted():
      return

    if self._project.hasUnsavedChanges():
      MyMessageBox = QMessageBox()
      MyMessageBox.setWindowTitle("Warning!")
      MyMessageBox.setText("Save changes made to your project?")
      yes = MyMessageBox.addButton("Yes",QMessageBox.YesRole)
      no = MyMessageBox.addButton("No",QMessageBox.NoRole)
      cancel = MyMessageBox.addButton("Cancel",QMessageBox.NoRole)
      MyMessageBox.exec_()
      choice = MyMessageBox.clickedButton()
      if choice == cancel:
        e.ignore()
        return
      elif choice == yes:
        if self.saveProject() == False:
          e.ignore()
          return
    settings = QSettings()
    if self._project.filename() != None:
      settings.setValue("ide.lastproject",self._project.filename())
    else:
      settings.remove("ide.lastproject")
    settings.setValue("ide.runStartupGroup",self.runStartupGroup.isChecked())
    settings.sync()
    self._codeRunner.terminate()

  def closing0k(self,editor):
    """
    This method is called by the codeEditorWindow to check that closing is allowed
    """
    iden=id(editor)
    if iden in self._codeRunner.status():
      question='Closing editor %s terminates the access to thread %i. Close anyway?' % (editor._shortname,iden)
      if QMessageBox.question (self,'Warning', question, QMessageBox.Ok, QMessageBox.Cancel) == QMessageBox.Cancel:
        return False
    return True

  def processVar(self,varname):
    """
    Retrieve a global variable of the CodeProcess
    """
    return self._codeRunner.processVar(varname)

  def executeCode(self,code,filename = "none",editor = None,identifier = "main"):
    if self._codeRunner.executeCode(code,identifier,filename) != -1:        # this function returns when the code has started running in the coderunner
      self._runningCodeSessions.append((code,identifier,filename,editor))   # why does main memorize codesessions rather than relying on coderunner?
      #if editor is not None:
        #editor.hasBeenRun = True # leave a trace in the editor that its code has been run at least once. Why not relying on the coderunner?

  def runCode(self,delimiter=""):
    """
    This method runs a piece of textual python code.
    It is called by runBlock, runSelection, or runFile, and calls executeCode.
    """
    editor=self.editorWindow.currentEditor()        # retrieve the current editor (i.e. script)
    code=editor.getCurrentCodeBlock(delimiter)      # retrieve the relevant piece of code
    try:
      justName=editor.filename().split('\\')[-1]
    except:
      justName=False
    filename = justName or "[unnamed buffer]"       # builds  and prints feedback message to the user
    shortFileName=filename[filename.rfind("\\")+1:]
    identifier = id(editor)
    if delimiter == "":
      poc="entire file"
    elif delimiter == "\n":
      poc="current selection"
    elif delimiter == "\n##":
      poc="current block"
    else:
      poc="???"
    print("Running "+poc+" in "+shortFileName+" (id="+str(identifier)+")")
    self.executeCode(code,filename = filename,editor = editor,identifier = identifier) # execute the code
    return True

  def runBlock(self):
    """
    Runs a block of code delimited by \n## (or start/end of file).
    """
    return self.runCode(delimiter="\n##")

  def runSelection(self):
    """
    Runs all lines having at least one char in the selection of the current script in the code editor.
    """
    return self.runCode(delimiter="\n")

  def runFile (self):
    """
    Runs the entire file.
    """
    return self.runCode(delimiter="")

  def runFileOrFolder(self,node):
    """
    Run files or folders selected in the project view.
    """
    if type(node) == objectmodel.File:
      self.projectTree.openFile(node)
      return self.runFile()
    elif type(node) == objectmodel.Folder:
      for child in node.children():
        self.runFileOrFolder(child)
      return True

  def runFiles(self):
    """
    Runs the current script file in the code editor if the later has the focus,
    or all the files selected in the project view if the project view has the focus.
    """
    widgetWithFocus=self.focusWidget()
    if type(widgetWithFocus) == CodeEditor:
      return self.runFile()
    elif type(widgetWithFocus) == ProjectView:
      selectedIndexes = widgetWithFocus.selectedIndexes()
      getNode=widgetWithFocus.model().getNode
      selectedNodes=map(getNode,selectedIndexes)
      for node in selectedNodes:
        self.runFileOrFolder(node)
    elif type(widgetWithFocus) == QTreeWidget:
      print("Run from QTreeWidget not implemented yet")
    return False

  def eventFilter(self,object,event):
    """
    Event filter of user typing enter, ctrl+enter or shif+enter for running a piece of code.
    """
    if event.type() == QEvent.KeyPress:
      if event.key() == Qt.Key_Enter and type(object) == CodeEditor:
        if event.modifiers() & Qt.ShiftModifier:     # shift+enter runs only the lines in the selection
          self.runSelection()
          return True
        elif event.modifiers() & Qt.ControlModifier: # ctrl+enter runs the entire file
          self.runFile()
          return True
        else:                                        # enter runs the current block between ##
          self.runBlock()
          return True
    return False

  def restartCodeProcess(self):
    print 'Restarting CodeProcess'
    self._codeRunner.restart()
    settings = QSettings()
    if settings.contains('ide.workingpath'):
      self.changeWorkingPath(str(settings.value('ide.workingpath').toString()))

  def changeWorkingPath(self,path = None):
    """
    Changes the working directory of the application
    """
    settings = QSettings()

    if path is None:
      path = QFileDialog.getExistingDirectory(self,"Change Working Diretory",directory = self.codeRunner().currentWorkingDirectory())

    if not os.path.exists(path):
      return

    os.chdir(str(path))
    self.codeRunner().setCurrentWorkingDirectory(str(path))

    settings.setValue("ide.workingpath",path)
    self.workingPathLabel.setText("Working path:"+path)

  def setupCodeEnvironmentCallback(self,thread):
    """
    """
    print("Done setting up code environment...")

  def setupCodeEnvironment(self):
    """
    """
    pass

  def codeRunner(self):
    """
    utility method returning the codeRunner object
    """
    return self._codeRunner

  def terminateCodeExecution(self):
    """
    Tries to stop the execution of the script selected in the editor if it is running
    """
    currentEditor = self.editorWindow.currentEditor()
    for session in self._runningCodeSessions:
      (code,identifier,filename,editor) = session
      if editor == currentEditor:
        print("Stopping execution...")
        self._codeRunner.stopExecution(identifier)

  def onTimer(self):
    return
    #sys.stdout.write(self._codeRunner.stdout())
    #sys.stderr.write(self._codeRunner.stderr())

  def newEditorCallback(self,editor):
    """
    """
    editor.installEventFilter(self)

  def setProject(self,project):
    self._project = project
    self.projectModel.setProject(project.tree())
    self.updateWindowTitle()

  def updateWindowTitle(self):
    if self._project.filename() != None:
      #self.setWindowTitle(self._windowTitle+ " - " + self._project.filename())
      self.setWindowTitle(self._windowTitle+ " - Project '" + self._project.filename()+"'")
    else:
      self.setWindowTitle(self._windowTitle)

  def toggleRunStartupGroup(self):
    """
    obsolete
    """
    self.runStartupGroup.setChecked(self.runStartupGroup.isChecked())

  def debug(self):
    print self.processVar('lastHelper')

  def buildHelperMenu(self):
    """
    The buildHelperMenu method builds the helper menu with
    - a 'Load helper...' command
    - a separator
    - A list of the loaded HelperGUIs and their associated Helper just below
    - a separator
    - alist of helpers with no associate
    Only HelperGUIs are enabled so that user can bring HelperGUI window to the front. Helpers are dimmed.
    """
    self.helpersMenu.clear()
    if hasattr(self,'_helperManager'):
      loadHelpers = self.helpersMenu.addAction('Load helper...')
      loadHelpers.setShortcut(QKeySequence("Ctrl+h"))
      self.connect(loadHelpers, SIGNAL('triggered()'), self._helperManager.loadHelpers)
      self.helpersMenu.addSeparator()
      helpers = self._helperManager.helpers()
      ag1,ag2 = QActionGroup(self,exclusive=False,triggered=self.showHelper),QActionGroup(self,exclusive=False)
      for key,dic in  helpers.items():
        helperType,associate,associateType=dic['helperType'],dic['associate'],dic['associateType']
        if helperType=='HelperGUI':
          ag1.addAction(QAction(key, self, checkable=False))
          if associate is not None:
            ag1.addAction(QAction(QString('  -  '+associate), self, checkable=False,enabled=False))
        elif helperType=='Helper':
            ag2.addAction(QAction(key, self, checkable=False,enabled=False))
      self.helpersMenu.addActions(ag1.actions())
      self.helpersMenu.addSeparator()
      self.helpersMenu.addActions(ag2.actions())

  def showHelper(self,action):
    actionName=str(action.text())
    if actionName in self._helpers:
      code='gv.%s.window2Front()' % actionName
      self.executeCode(code,identifier = actionName,filename = "IDE",editor = None)

  def buildWindowMenu(self):
    self.windowMenu.clear()
    tab=self.editorWindow.tab
    li=[str(tab.tabText(i)) for i in range(tab.count())]
    current=tab.tabText(tab.currentIndex())
    ag=QActionGroup(self)
    for name in li:
      a=ag.addAction(QAction(name, self, checkable=True))
      self.windowMenu.addAction(a)
      # individual actions are not connected. Only the menu is connected to triggered() event.
      if name==current:
        a.setChecked(True)

  def selectTab (self,action):
    tab=self.editorWindow.tab
    li=[str(tab.tabText(i)) for i in range(tab.count())]
    index=li.index(str(action.text()))
    tab.setCurrentIndex(index)

  def initializeToolbars(self):
      self.mainToolbar = self.addToolBar("Tools")

      icons = self._icons

      changeWorkingPath = self.mainToolbar.addAction(self._icons["workingPath"],"Change working directory...")

      self.mainToolbar.addSeparator()

      newFile = self.mainToolbar.addAction(icons["newFile"],"New file")
      openFile = self.mainToolbar.addAction(icons["openFile"],"Open file...")
      saveFile = self.mainToolbar.addAction(icons["saveFile"],"Save file")
      saveFileAs = self.mainToolbar.addAction(icons["saveFileAs"],"Save file as...")

      self.mainToolbar.addSeparator()

      runFiles = self.mainToolbar.addAction(icons["executeAllCode"],"Run file(s) (ctrl + enter)")
      runBlock = self.mainToolbar.addAction(icons["executeCodeBlock"],"Run block (enter)")
      runSelection = self.mainToolbar.addAction(icons["executeCodeSelection"],"Run selection (shift + enter)")
      self.connect(runFiles, SIGNAL('triggered()'), self.runFiles)
      self.connect(runBlock, SIGNAL('triggered()'), self.runBlock)
      self.connect(runSelection, SIGNAL('triggered()'), self.runSelection)

      self.mainToolbar.addSeparator()

      killThread = self.mainToolbar.addAction(self._icons["killThread"],"Kill thread")

      # obsolete
      #self.connect(executeBlock,SIGNAL('triggered()'),lambda: self.executeCode(self.editorWindow.currentEditor().getCurrentCodeBlock(),filename = self.editorWindow.currentEditor().filename() or "[unnamed buffer]",editor = self.editorWindow.currentEditor(),identifier = id(self.editorWindow.currentEditor())))

      self.connect(newFile, SIGNAL('triggered()'), self.editorWindow.newEditor)
      self.connect(openFile, SIGNAL('triggered()'), self.editorWindow.openFile)
      self.connect(saveFile, SIGNAL('triggered()'), self.editorWindow.saveCurrentFile)
      self.connect(saveFileAs, SIGNAL('triggered()'), self.editorWindow.saveCurrentFileAs)
      self.connect(killThread,SIGNAL("triggered()"),self.terminateCodeExecution)
      self.connect(changeWorkingPath, SIGNAL('triggered()'), self.changeWorkingPath)

  def runStartup(self):
    print "Looking for a startup file or folder at tree level 1 in current project"
    if self.runStartupGroup.isChecked():
        childrenLevel1= self.projectModel.project().children()
        found=False
        for child in childrenLevel1:
          if child.name().lower() == 'startup' :
            self.runFileOrFolder(child)
            found=True
        if not found:
          print("Startup file or folder not found" )

  def showAbout(self):

    text= "<p align='center'> <FONT COLOR='blue' >QuantroLab Version "+__version__+"<br>\
    <FONT COLOR='black'> QuantroLab is a simple python<br>\
    integrated development environment<br>\
    for controlling a physics laboratory.<br><br>\
    CEA-Saclay 2012-2015<br>\
    <br><FONT COLOR='blue'>\
    Andreas Dewes<br>\
    Vivien Schmitt<br>\
    Denis Vion</p>"
    QMessageBox.about (self, 'About QuantroLab python IDE', QString(text))

  def updatedGui(self, subject = None, property = None, value = None):
    if property =='deleted':
      key=subject.__class__.__name__
      if key in self._helpers and isinstance(self._helpers[key]['helper'],(Helper,HelperGUI)):
        associateName=self._helpers[key]['associateName']
        if associateName is not None:
          associate,associatePath=self._helpers[key]['associate'],self._helpers[key]['associatePath']
          self._helpers[associateName]={'helper':associate,'filepath':associatePath,'associateName':None,'associate':None,'associatePath':None}
        self._helpers.pop(key)
        self.buildHelperMenu()
      else:
        for k2,dic in self._helpers.items():
          if key == dic['associateName']:
            for k3 in ['associateName','associate','associatePath']:
              dic[k3]=None
            self.buildHelperMenu()
# end of IDE class definition

# Starting application function
def startIDE(qApp = None):
  print 'Starting IDE...'
  if qApp is None:
    qApp = QApplication(sys.argv)
  splash_pix = QPixmap(splashFile)
  splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
  #splash.setMask(splash_pix.mask())
  splash.show()
  t0=time.time()
  splash.showMessage("loading...",68) # 68 means bottom-center
  qApp.processEvents()

  QCoreApplication.setOrganizationName("CEA-Quantronics")
  QCoreApplication.setOrganizationDomain("cea.fr")
  QCoreApplication.setApplicationName("QuantroLab Python IDE")
  QCoreApplication.setApplicationVersion(QString(__version__))

  qApp.setStyle(QStyleFactory.create("QMacStyle"))
  qApp.setStyleSheet("""QTreeWidget:Item {padding:6;}QTreeView:Item {padding:6;}""")
  qApp.connect(qApp, SIGNAL('lastWindowClosed()'), qApp,SLOT('quit()'))
  myIDE = IDE()
  myIDE.showMaximized()

  t1=time.time()-t0
  if t1<3: time.sleep(3-t1)           # Ensure that the splash screen is displayed during at least 3 seconds
  splash.finish(myIDE)                # and terminates the display when the IDE is fully displayed.
  qApp.exec_()                        # Start the application main event loop


if __name__ == '__main__':
  startIDE()

#*******************************************************************************
# Variable manager frontpanel                                                       *
#*******************************************************************************

#Imports

import sys,getopt,os,os.path,weakref,gc,time,inspect
from functools import partial

from application.ide.coderun.coderunner_gui import execInGui

from application.lib.helper_classes import HelperGUI    # HelperGUI
from application.ide.mpl.canvas import *
from application.lib.instrum_classes import *
from application.lib.base_classes1 import *             # SUBJECT, OBSERVER, DISPATCHER, THREADEDDISPATCHER
from application.lib.com_classes import *               # SINGLETON, RELOADABLE
from application.ide.widgets.observerwidget import ObserverWidget
from application.helpers.userPromptDialogs import *

import numpy

#*******************************************
#  Helper initialization                   *
#*******************************************

# Global module dictionary defining the helper
helperDic = {'name':'Variable Manager','version':'beta 0.1','authors':'V. Schmitt','mail':'denis.vion@cea.fr','start':'startHelperGui','stop':None}

def startHelperGui(exitWhenClosed = False,parent=None,globals={}):    # 3) Start the dataManager
    global VarManager                                                # define dataManager as a global variable
    VarManager = VarManager(parent,globals)                         # Instantiate the datamanager gui here
    VarManager.show()                                                # show its window
    QApplication.instance().setQuitOnLastWindowClosed(exitWhenClosed) #close when exiting main application
    return VarManager

def startHelperGuiInGui(exitWhenClosed = False,parent=None,globals={}):# 2) Start the datamanager in the gui
    execInGui(lambda :startHelperGui(exitWhenClosed,parent,globals))

if __name__ == '__main__':                                             # 1) starts here in the module if file is main
    startHelperGuiInGui(True)

#********************************************
#  VaraibleManager GUI  class                *
#********************************************
iconPath = os.path.dirname(__file__)+'/resources/icons'

class VarManager(HelperGUI):

  def __init__(self,parent = None,globals = {}):

    # init superClasses
    HelperGUI.__init__(self,parent,globals,helper=None)
    self.debugPrint("in variable Manager creator")

    self._workingDirectory = None

    self.setStyleSheet("""QTreeWidget:Item {padding:6;} QTreeView:Item {padding:6;}""")

    title = helperDic['name'] + ' version '  + helperDic['version']
    if self._helper is not None: title+=' in tandem with '+self._helper.__class__.__name__
    self.setWindowTitle(title)
    self.setWindowIcon(QIcon(iconPath+'/penguin.png'))
    self.setAttribute(Qt.WA_DeleteOnClose,True)

    # define GUI below

    splitter = QSplitter(Qt.Horizontal)
    self._thread = None
    self._threadList = ThreadList(parent =self,globals = globals)

    self._updateButton=QPushButton("Update")

    self.connect(self._updateButton,SIGNAL("clicked()"),self.updatePressed)

    self._variablesList = VariablesList(parent =self,globals = globals)
    self._props = ThreadProperties(parent =self,globals = globals)
    self.connect(self._threadList,SIGNAL("currentItemChanged(QTreeWidgetItem *,QTreeWidgetItem *)"),self.selectThread)

    self.tabs = QTabWidget()

    splitter.addWidget(self._threadList)
    splitter.addWidget(self._updateButton)
    splitter.addWidget(self.tabs)

# this is a comment
    self.tabs.addTab(self._props,"Properties")
    self.tabs.addTab(self._variablesList,"Variables")

    self.setCentralWidget(splitter)
    print 'reached end of gui definition'

  def updatedGui(self,subject,property = None,value = None):
    return

  def selectThread(self,current,last):
    if not current is None:
      self._thread = current
      self._props.setThread(self._thread.id)
      self._variablesList.setThread(self._thread.id)

  def updatePressed(self):
    self._threadList.updateThreadList()
    self._variablesList.updateVariableList()


class ThreadList(QTreeWidget,ObserverWidget):

  def __init__(self,parent = None,globals={}):
    QTreeWidget.__init__(self,parent)
    ObserverWidget.__init__(self)

    self._parent=parent
    self.setSelectionMode(QAbstractItemView.SingleSelection)
    self.setSortingEnabled(True)

    self._globals=globals

    self._coderunner=self._globals["__coderunner__"]
    self.updateThreadList()



  def updateThreadList(self):
    threadsId=self._coderunner.status().keys()

    self.clear()
    self.setHeaderLabels(["Name","ID"])

    for threadId in threadsId:
      thread=self._coderunner.status()[threadId]
      item=QTreeWidgetItem()
      item.setText(0,str(thread["filename"]))
      item.setText(1,str(threadId))
      item.id=threadId
      self.insertTopLevelItem(0,item)


def clearLayout(layout):
  for i in range(layout.count()): layout.takeAt(0).widget().close()#layout.removeWidget(layout.itemAt(i).widget())

class VariablesList(QWidget,ObserverWidget):
  def __init__(self,parent = None,globals = {}):
    QScrollArea.__init__(self,parent)
    ObserverWidget.__init__(self)
    self._globals = globals
    self._coderunner=self._globals["__coderunner__"]
    self._thread = None


    layout = QFormLayout()
    self.setAttribute(Qt.WA_DeleteOnClose,True)
    self.variables = QLineEdit()
    self.variables.setReadOnly(True)


    self.setLayout(layout)

  def valueChanged(self,item):
    old=self._coderunner._lv[self._threadId][item]
    try:
      self._coderunner._lv[self._threadId][item]=old.__new__(type(old),str(self.variables[item].text()))
    except ValueError:
      messageBox = QMessageBox(QMessageBox.Information,"Type Error","Value does not match previous data type")
      messageBox.exec_()
      self.variables[item].setText(str(old))

  def setThread(self,threadId):
    self._threadId=threadId
    self.updateVariableList()

  def updateVariableList(self):
    layout=self.layout()
    clearLayout(layout)
    self.variables = dict()
    index=0
    lv=self._coderunner._lv[self._threadId]
    for item in sorted(lv.keys()):
      listSkipped=["ismodule","isclass","ismethod","isfunction","isgeneratorfunction","isgenerator","istraceback","isframe","iscode","isbuiltin","isroutine","isabstract","ismethoddescriptor","isdatadescriptor","isgetsetdescriptor","ismemberdescriptor"]
      otherSkipped=["gv","__builtins__","__file__"]
      a=False
      for test in listSkipped:
        a=a or getattr(inspect,test)(lv[item])
      for test in otherSkipped:
        a=a or item == test
      if a == False:
        self.variables[item]=QLineEdit()
        self.variables[item].name=item
        self.variables[item].setText(str(lv[item]))
        self.variables[item].setReadOnly(False)
        self.variables[item].returnPressed.connect(partial(self.valueChanged,item=item))
#        self.connect(self.variables[item],SIGNAL("textEdited(QString)"),self.valueChanged,item=item)
        layout.addRow(item,self.variables[item])
        #layout.addWidget(QLabel(item))
        #layout.addWidget(self.variables[item])


class ThreadProperties(QWidget,ObserverWidget):
  def __init__(self,parent = None,globals = {}):
    QWidget.__init__(self,parent)
    ObserverWidget.__init__(self)
    layout = QGridLayout()

    self._globals = globals
    self._thread = None
    self._coderunner=self._globals["__coderunner__"]
    self.name = QLineEdit()
    self.filename = QLineEdit()
    self.filename.setReadOnly(True)
    self.failed = QLineEdit()
    self.isRunning = QLineEdit()
    self.failed.setReadOnly(True)
    self.isRunning.setReadOnly(True)

    layout.addWidget(QLabel("Name"))
    layout.addWidget(self.name)
    layout.addWidget(QLabel("Filename"))
    layout.addWidget(self.filename)
    layout.addWidget(QLabel("failed"))
    layout.addWidget(self.failed)
    layout.addWidget(QLabel("isRunning"))
    layout.addWidget(self.isRunning)

    self.setLayout(layout)

  def setThread(self,threadId):
    thread=self._coderunner.status()[threadId]
    self.filename.setText(str(thread['filename']))
    self.failed.setText(str(thread['failed']))
    self.isRunning.setText(str(thread['isRunning']))

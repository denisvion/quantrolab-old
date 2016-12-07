# *************************************************************************
# DataManager Frontpanel                                                       *
# *************************************************************************

# Imports

import sys
import getopt
import os
import os.path
import weakref
import gc
import time
import warnings

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QApplication, QCursor

from application.ide.coderun.coderunner_gui import execInGui

from application.lib.helper_classes import HelperGUI    # HelperGUI
from application.lib.datacube import *                  # Datacube
# Instrument, VisaInstrument, RemoteInstrument, ServerConnection, Debugger
from application.lib.instrum_classes import *
# Subject, Observer, Dispatcher, ThreadedDispatcher
from application.lib.com_classes import *
from application.helpers.datamanager.datamgr import *   # DataMgr
# DatacubeView
from application.helpers.datamanager.datamanager_gui.datacubeview import *
# CubeProperties
from application.helpers.datamanager.datamanager_gui.cubeproperties import *
from application.ide.widgets.observerwidget import ObserverWidget
from application.ide.widgets.prefDialog import *        # PrefgAutoDialog
from application.helpers.userPromptDialogs import *
from application.helpers.datamanager.datamanager_gui.plotter import Plot2DWidget, Plot3DWidget  # Plotter

import numpy

# *******************************************
#  Helper initialization                   *
# *******************************************

# Global module dictionary defining the helper
helperDic = {'name': 'Data Manager', 'version': '1.0', 'authors': 'A. Dewes-V. Schmitt - D. Vion',
             'mail': 'denis.vion@cea.fr', 'start': 'startHelperGui', 'stop': None}
# splash screen
splashFile = QString(os.path.dirname(__file__) + '/resources/quantrolab.png')


# 3) Start the dataManager
def startHelperGui(exitWhenClosed=False, parent=None, globals={}):

    # define dataManager as a global variable
    global dataManager
    # Instantiate the datamanager gui here
    dataManager = DataManager(parent, globals)
    # show its window
    dataManager.show()
    QApplication.instance().setQuitOnLastWindowClosed(
        exitWhenClosed)  # close when exiting main application
    return dataManager


# 2) Start the datamanager in the gui
def startHelperGuiInGui(exitWhenClosed=False, parent=None, globals={}):
    execInGui(lambda: startHelperGui(exitWhenClosed, parent, globals))

# 1) starts here in the module if file is main
if __name__ == '__main__':
    startHelperGuiInGui(True)

# ********************************************
#  DataManager GUI  class                   *
# ********************************************
# general rules :
#   - the client interacts with the dataManager only, and not with the dataManager frontpanel
#   - the dataManager or the datacubes then send notifications to the frontpanel or to its elements.
# The general algorithm is the following :
# 1) possibly add a datacube to the dataManager
# 2) It is set as the current one, but the user can set another one from the front panel
# 3) x and y variables selectors are automatically filled. An x,y pair is pre-selected but can be changed from the front panel
# 4) The graphics and the list of plots is cleared upon request.
# 5) A plot is added to the list of plots if requested, or if autoplot is true, provided it is not already present
# 6) Graphics is updated

iconPath = os.path.dirname(__file__) + '/resources/icons'


class DataManager(HelperGUI):

    def __init__(self, name=None, parent=None, globals={}):

        dataMgr = DataMgr(parent, globals)         # instantiates a DataMgr

        # init superClasses
        HelperGUI.__init__(self, name, parent, globals, helper=dataMgr)
        self.debugPrint("in dataManagerGUI frontpanel creator")
        # inform the helper it has an associated gui by adding the gui as an attribute
        dataMgr._gui = self

        self._workingDirectory = None

        self.setStyleSheet("""QTreeWidget:Item {padding:6;} QTreeView:Item {padding:6;}""")

        title = helperDic['name'] + " version " + helperDic["version"]
        if self._helper is not None:
            title += ' in tandem with ' + self._helper.__class__.__name__
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(iconPath + '/penguin.png'))
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self.prefDict =\
            {'folders': {'label': 'Save children in folders', 'type': bool, 'value': False},
             'header': {'label': 'Include parameters in data text files', 'type': bool, 'value': False}}

        self._cube = None   # current cube of the datamanager GUI

        # define GUI below

        splitter = QSplitter(Qt.Horizontal)

        self.cubeList = CubeTreeView(parent=self, manager=self._helper)
        self.cubeViewer = DatacubeTableView()
        self.connect(self.cubeList, SIGNAL(
            "currentItemChanged(QTreeWidgetItem *,QTreeWidgetItem *)"), self.selectCube)
        self.plotters2D = []
        self.plotters3D = []
        self.tabs = QTabWidget()

        leftLayout = QGridLayout()

        leftLayout.addWidget(self.cubeList)

        leftWidget = QWidget()
        leftWidget.setLayout(leftLayout)

        splitter.addWidget(leftWidget)
        splitter.addWidget(self.tabs)
        menubar = self.menuBar()
        filemenu = menubar.addMenu("File")

        newCube = filemenu.addAction("New")
        loadCube = filemenu.addAction("Open...")
        renameCube = filemenu.addAction("Rename...")
        filemenu.addSeparator()
        removeCube = filemenu.addAction("Remove")
        removeAll = filemenu.addAction("Remove all")
        filemenu.addSeparator()
        saveCube = filemenu.addAction("Save")
        saveCubeAs = filemenu.addAction("Save as...")
        filemenu.addSeparator()
        markAsGood = filemenu.addAction("Mark as Good")
        markAsBad = filemenu.addAction("Mark as Bad")
        filemenu.addSeparator()
        sendToIgor = filemenu.addAction("Send to IgorPro")
        filemenu.addSeparator()
        preferences = filemenu.addAction("Preferences...")

        menubar.addMenu(filemenu)

        self.connect(loadCube, SIGNAL("triggered()"), self.loadCube)
        self.connect(newCube, SIGNAL("triggered()"), self.newCube)
        self.connect(renameCube, SIGNAL("triggered()"), self.renameCube)
        self.connect(saveCube, SIGNAL("triggered()"), self.saveCube)
        self.connect(saveCubeAs, SIGNAL("triggered()"), self.saveCubeAs)
        self.connect(removeCube, SIGNAL("triggered()"), self.removeCube)
        self.connect(removeAll, SIGNAL("triggered()"), self.removeAll)
        self.connect(markAsGood, SIGNAL("triggered()"), self.markAsGood)
        self.connect(markAsBad, SIGNAL("triggered()"), self.markAsBad)
        self.connect(sendToIgor, SIGNAL("triggered()"), self.sendToIgor)
        self.connect(preferences, SIGNAL("triggered()"), self.preferences)

        plotmenu = menubar.addMenu("Plots")
        new2DPlot = plotmenu.addAction("New 2D plot")
        new3DPlot = plotmenu.addAction("New 3D plot")
        removePlot = plotmenu.addAction("Remove current plot")
        self.connect(new2DPlot, SIGNAL("triggered()"), self.add2DPlotter)
        self.connect(new3DPlot, SIGNAL("triggered()"), self.add3DPlotter)
        self.connect(removePlot, SIGNAL("triggered()"), self.removePlotter)

        def preparePlotMenu():
            removePlot.setEnabled(isinstance(self.tabs.currentWidget(
            ), Plot2DWidget) or isinstance(self.tabs.currentWidget(), Plot3DWidget))
        self.connect(plotmenu, SIGNAL("aboutToShow()"), preparePlotMenu)

        menubar.addMenu(plotmenu)

        self.setCentralWidget(splitter)
        self.controlWidget = CubeProperties(globals=globals)
        self.tabs.addTab(self.controlWidget, "Properties")
        self.tabs.addTab(self.cubeViewer, "Table View")
        self.add2DPlotter()
        self.add3DPlotter()
        self.selectCube(self._cube, None)

    def pref(self, key):
        return self.prefDict[key]['value']

    def selectCube(self, current, last):
        self.debugPrint('in DataManagerGUI.selectCube with current cube =',
                        current, ' and last cube=', last)
        if current is None:
            self._cube = None
        else:
            self._cube = current._cube()
            if self._cube is None:
                self.cubeList.removeItem(current)
        cube = self._cube
        self.controlWidget.setCube(cube)
        self.cubeViewer.setDatacube(cube)
        for plotter2D in self.plotters2D:
            plotter2D.setCube(cube)
        for plotter3D in self.plotters3D:
            plotter3D.setCube(cube)

    def updatedGui(self, subject=None, property=None, value=None):
        self.debugPrint('in DataManagerGUI.updatedGui with subject=',
                        subject, ', property =', property, ', and value=', value)
        if subject == self._helper and property == "plot":
            cube = value[0][0]
            kwargs = value[1]
            threeD = False
            if 'threeD' in kwargs:
                threeD = kwargs['threeD']
            for i in range(self.tabs.count()):
                if not threeD and isinstance(self.tabs.widget(i), Plot2DWidget):
                    self.tabs.widget(i).addPlot2(cube=cube, **kwargs)
                    break
                elif threeD and isinstance(self.tabs.widget(i), Plot3DWidget):
                    self.tabs.currentWidget.addPlot(cube=cube, **kwargs)
                    break
        else:
            self.debugPrint("not managed")

    def workingDirectory(self):
        if self._workingDirectory is None:
            return os.getcwd()
        return self._workingDirectory

    def setWorkingDirectory(self, filename):
        if filename is not None:
            directory = os.path.dirname(str(filename))
            self._workingDirectory = directory
        else:
            self._workingDirectory = None

    def loadCube(self):
        self.debugPrint("in DataManagerGUI.loadCube()")
        filename = QFileDialog.getOpenFileName(
            filter="Datacubes (*.par);;Datacubes (*.txt)", directory=self.workingDirectory())
        if not filename == '':
            self.setWorkingDirectory(filename)
            cube = Datacube()
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            cube.loadtxt(str(filename))
            self._helper.addDatacube(cube)
            QApplication.restoreOverrideCursor()
            # Make the manually loaded datacube the current cube. It will be
            # automatically selected also in the CubeTreeView
            self._cube = cube

    def newCube(self):
        self.debugPrint("in DataManagerGUI.newCube()")
        cube = Datacube()
        cube.set(a=0, b=0, commit=False)
        self._helper.addDatacube(cube)
        # Make the manually created datacube the current cube. It will be
        # automatically selected also in the CubeTreeView
        self._cube = cube

    def renameCube(self):
        self.debugPrint("in DataManagerGUI.renameCube()")
        if self._cube is None:
            return
        oldName = self._cube.name()
        dialog = QInputDialog()
        dialog.setWindowTitle("Rename datacube")
        dialog.setLabelText(
            "Warning: Existing plots will loose any reference to this datacube.\nNew name:")

        dialog.setTextValue(oldName)
        newName = None
        dialog.exec_()
        str1 = str(dialog.textValue())
        if dialog.result() == QDialog.Accepted and str1 != oldName:
            if str1 != "":
                newName = str1
                self._cube.setName(newName)

    def removeCube(self, deleteCube=True):
        self.debugPrint("in DataManagerGUI.removeCube()")
        if self._cube is not None:
            self._helper.removeDatacube(self._cube, deleteCube=deleteCube)

    def removeAll(self, deleteCube=True):
        self.debugPrint("in DataManagerGUI.removeAll()")
        reply = QMessageBox.question(
            self, 'Please confirm', 'Delete all datacubes from dataManager ?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            for cube in list(self._helper.datacubes()):
                self._helper.removeDatacube(cube, deleteCube=deleteCube)

    def saveCubeAs(self):
        self.saveCube(saveAs=True)

    def addChild(self, new=False):
        self.debugPrint("in DataManagerGUI.addChild()")
        if self._cube is not None:
            cube = None
            if new:
                name0 = 'child_'
                names = [child.name() for child in self._cube.children()]
                i = 0
                while True:
                    name = name0 + str(i)
                    i += 1
                    if name not in names or i > 1000:
                        break
                if i <= 1000:
                    cube = Datacube(name=name)
                    cube.set(aa=0, bb=0, commit=True)
            else:
                filename = QFileDialog.getOpenFileName(
                    filter="Datacubes (*.par);;Datacubes (*.txt)", directory=self.workingDirectory())
                if not filename == '':
                    cube = Datacube()
                    self.setWorkingDirectory(filename)
                    cube.loadtxt(str(filename))
            if cube:
                self._cube.addChild(cube)
                self._cube.commit()

    def markAsBad(self):
        if userAsk("Are you sure ?", timeOut=5, defaultValue=False):
            if self._cube is None:
                return
            try:
                self._cube.erase()
            except:
                pass
            workingDir = os.getcwd()
            subDir = os.path.normpath(workingDir + "/bad_data")
            if not os.path.exists(subDir):
                os.mkdir(subDir)
            if "badData" in self._cube.parameters() and self._cube.parameters()["badData"]:
                messageBox = QMessageBox(
                    QMessageBox.Information, "Already marked, returning...")
                messageBox.exec_()
                return
            self.removeCube()
            self._cube.savetxt(os.path.normpath(subDir + "/" + self._cube.name()),
                               folders=self.pref('folders'), header=self.pref('header'))
            self._cube.parameters()["badData"] = True
            messageBox = QMessageBox(QMessageBox.Information, "Data marked as bad",
                                     "The data has been marked and moved into the subfolder \"bad_data\"")
            messageBox.exec_()

    def markAsGood(self):
        if self._cube is None:
            return
        workingDir = os.getcwd()
        subDir = os.path.normpath(workingDir + "/good_data")
        if not os.path.exists(subDir):
            os.mkdir(subDir)
        if "goodData" in self._cube.parameters() and self._cube.parameters()["goodData"]:
            messageBox = QMessageBox(
                QMessageBox.Information, "Already marked, returning...")
            messageBox.exec_()
            return
        self._cube.savetxt(os.path.normpath(subDir + "/" + self._cube.name()),
                           folders=self.pref('folders'), header=self.pref('header'))
        self._cube.parameters()["goodData"] = True
        messageBox = QMessageBox(QMessageBox.Information, "Data marked as good",
                                 "The data has been marked and copied into the subfolder \"good_data\"")
        messageBox.exec_()

    def saveCube(self, saveAs=False):
        self.debugPrint("in DataManagerGUI.saveAs()")
        if self._cube is None:
            return
        if self._cube.filename() is None or self._cube.filename() == '' or saveAs:
            directory = self.workingDirectory()
            if self._cube.name() is not None:
                directory += '/' + self._cube.name() + '.par'
            if self.pref('header'):
                filter1 = "Datacubes (*.txt)"
            else:
                filter1 = "Datacubes (*.par)"
            filename = QFileDialog.getSaveFileName(
                filter=filter1, directory=directory)
            if filename != "":
                self.setWorkingDirectory(filename)
                self._cube.savetxt(str(filename), overwrite=True, folders=self.pref(
                    'folders'), header=self.pref('header'))
        else:
            # save as txt if name ends with .txt and as par otherwise.
            header = self._cube.filename().split('.')[-1] == 'txt'
            self._cube.savetxt(overwrite=True, folders=self.pref(
                'folders'), header=header)

    def sendToIgor(self):
        """
        Send the selected datacube to igor
        """
        self._cube.sendToIgor()

    def preferences(self):
        self._prefDialog = PrefAutoDialog(parent=self, prefDict=self.prefDict)
        self._prefDialog.setModal(True)
        self._prefDialog.show()

    def add2DPlotter(self):
        plotter2D = Plot2DWidget(parent=self, dataManager=self._helper,
                                 name="2D Data plot " + str(len(self.plotters2D) + 1))
        self.plotters2D.append(plotter2D)
        self.tabs.addTab(plotter2D, plotter2D.name)
        plotter2D.setCube(self._cube)

    def add3DPlotter(self):
        plotter3D = Plot3DWidget(parent=self, dataManager=self._helper,
                                 name="3D Data plot " + str(len(self.plotters3D) + 1))
        self.plotters3D.append(plotter3D)
        self.tabs.addTab(plotter3D, plotter3D.name)
        plotter3D.setCube(self._cube)

    def removePlotter(self):
        plotter = self.tabs.currentWidget()
        if plotter in self.plotters2D:
            self.plotters2D.remove(plotter)
        elif plotter in self.plotters3D:
            self.plotters3D.remove(plotter)
        plotter.__del__()
        self.tabs.removeTab(self.tabs.currentIndex())

    # Trick from Denis to propagate the notification that a child has been
    # added to a datacube to all plotter2Ds.
    def propagateAddChild(self, subject, value):
        for plotter in self.plotters2D:
            # Subject is the parent, value is the child.
            plotter.updatedGui(
                subject=subject, property="addChild", value=value)

# ********************************************
#  CubeTreeView class                       *
# ********************************************


class CubeTreeView(QTreeWidget, ObserverWidget, Debugger):

    def __init__(self, parent=None, manager=None):
        Debugger.__init__(self)
        QTreeWidget.__init__(self, parent)
        ObserverWidget.__init__(self)
        self._parent = parent
        self._items = dict()
        # attach  dataManager to this CubeTreeView, i.e. CubeTreeView receives
        # message from datamanager
        self._manager = manager
        self.debugPrint('attaching ', self._manager, ' to ', self)
        self._manager.attach(self)
        self.setHeaderLabels(["Name"])
        self.initTreeView()
        self.itemDoubleClicked.connect(self.renameCube)

    def renameCube(self):
        if self._parent is not None:
            self._parent.renameCube()

    def ref(self, cube):
        return weakref.ref(cube)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        addRenameAction = menu.addAction("Rename datacube...")
        menu.addSeparator()
        addChildAction = menu.addAction("Add child from file...")
        addNewChildAction = menu.addAction("Add new child")
        menu.addSeparator()
        removeAction = menu.addAction("Remove")
        menu.addSeparator()
        saveAsAction = menu.addAction("Save as...")
        menu.addSeparator()
        markAsGoodAction = menu.addAction("Mark as Good")
        markAsBadAction = menu.addAction("Mark as Bad")
        action = menu.exec_(self.viewport().mapToGlobal(event.pos()))
        if action == addRenameAction:
            if self._parent is not None:
                self._parent.renameCube()
        elif action == addChildAction:
            if self._parent is not None:
                self._parent.addChild(new=False)
        if action == addNewChildAction:
            if self._parent is not None:
                self._parent.addChild(new=True)
        elif action == removeAction:
            if self._parent is not None:
                self._parent.removeCube()
        elif action == saveAsAction:
            if self._parent is not None:
                self._parent.saveCubeAs()
        elif action == markAsGoodAction:
            if self._parent is not None:
                self._parent.markAsGood()
        elif action == markAsBadAction:
            if self._parent is not None:
                self._parent.markAsBad()

    def selectCube(self, cube):
        self.debugPrint("in CubeTreeView.selectCube(datacube) with datacube =", cube)
        if self.ref(cube) in self._items:
            item = self._items[self.ref(cube)]
            self.setCurrentItem(item)

    def addCube(self, cube, parent):
        """
        1) Adds a cube in the _items dictionary if not already resent,
        2) adds its name to the view,
        3) attaches this widget to the cube so that it will get future notifications from the cube
        4) call recursively addCube for each child.
        Dictionary _items  has the form {weakRef(cube1):QTreeWidgetItem1,weakRef(cube2):QTreeWidgetItem2,... },
        in which cube1, cube2, ... are cubes at any level in the tree structure.
        A cube whatever its level cannot be added a second time.
        """
        self.debugPrint("in CubeTreeView.addCube(cube) with cube =",
                        cube, "and cube's parent =", parent)
        # Returns without adding if cube reference already present
        if self.ref(cube) in self._items:
            return
        item = QTreeWidgetItem()
        item.setText(0, str(cube.name()))
        item._cube = self.ref(cube)
        self.debugPrint('attaching ', cube, ' to ', self)
        cube.attach(self)
        self._items[self.ref(cube)] = item
        if parent is None:
            self.insertTopLevelItem(0, item)
        else:
            # this is the addChild method of QTreeWidget
            self._items[self.ref(parent)].addChild(item)
        for child in cube.children():
            self.addCube(child, cube)             # recursive call for children

    def removeItem(self, item):
        self.debugPrint("in CubeTreeView.removeItem(item) with item =", item)
        if item.parent() is None:
            self.takeTopLevelItem(self.indexOfTopLevelItem(item))
        else:
            item.parent().removeChild(item)

    def removeCube(self, cube, parent):
        """
        1) Removes a cube and all its children from the _items dictionary,
        2) from the view,
        3) detaches this widget from the cube,
        4) call recursively addCube for each child.
        Note: it is important that this code removes all references to any menmber of the removed familly.
        FEV 2015 : REFERENCES TO CHILDREN WERE NOT REMOVED => CODE MODIFIED BY DV
        """
        self.debugPrint(
            'in CubeTreeView.removecube(datacube) with datacube = ', cube, ' and parent = ', parent)
        for child in cube.children():
            self.removeCube(child, cube)
        if parent is not None:
            parentItem = self._items[self.ref(parent)]
            cubeItem = self._items[self.ref(cube)]
            parentItem.takeChild(parentItem.indexOfChild(cubeItem))
        else:
            cubeItem = self._items[self.ref(cube)]
            self.takeTopLevelItem(self.indexOfTopLevelItem(cubeItem))
        del self._items[self.ref(cube)]
        cube.detach(self)

    def updateCube(self, cube):
        self.debugPrint("in CubeTreeView.updatecube(cube) with cube =", cube)
        item = self._items[self.ref(cube)]
        item.setText(0, cube.name())

    def initTreeView(self):
        self.debugPrint("in CubeTreeView.initTreeView()")
        self.clear()
        for cube in self._manager.datacubes():
            self.addCube(cube, None)

    def updatedGui(self, subject, property=None, value=None):
        self.debugPrint("in CubeTreeView.updatedGui with subject=",
                        subject, " property=", property, ' and value =', value)
        if property == "addDatacube":
            cube = value
            self.addCube(cube, None)
            if self._parent._cube == cube:   # select the cube in the CubeTreeView if it is the current cube in the datamanager GUI
                self.selectCube(cube)
        elif property == "addChild":
            child = value
            self.addCube(child, subject)
            # Trick from Denis to propagate the notification that a Child has
            # been added. Subject is the parent, value is the child.
            self._parent.propagateAddChild(subject, value)
        elif property == "name":
            self.updateCube(subject)
        elif property == "removeDatacube":
            self.removeCube(value, None)
        elif property == "removeChild":
            self.removeCube(value, subject)
        else:
            self.debugPrint("not managed")

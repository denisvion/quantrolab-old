import sys
import getopt
import os
import os.path
import weakref
import gc
import time
import numpy

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QApplication, QCursor

from application.lib.helper_classes import HelperGUI    # HelperGUI
from application.ide.widgets.observerwidget import ObserverWidget
from application.ide.widgets.prefDialog import *        # PrefgAutoDialog
from application.helpers.userPromptDialogs import *

from application.helpers.loopmanager.loopmgr import LoopMgr

iconPath = os.path.dirname(__file__) + '/resources/icons'

#*******************************************
#  Helper initialization                   *
#*******************************************

# Global module dictionary defining the helper
helperDic = {'name': 'Loop Manager', 'version': '1.1', 'authors': 'A. Dewes-V. Schmitt - D. Vion',
             'mail': 'denis.vion@cea.fr', 'start': 'startHelperGui', 'stop': None}


# 3) Start the dataManager
def startHelperGui(exitWhenClosed=False, parent=None, globals={}):
    # define dataManager as a global variable
    global loopManager
    # Instantiate the datamanager gui here
    loopManager = LoopManager(parent, globals)
    # show its window
    loopManager.show()
    QApplication.instance().setQuitOnLastWindowClosed(
        exitWhenClosed)  # close when exiting main application
    return loopManager


# 2) Start the datamanager in the gui
def startHelperGuiInGui(exitWhenClosed=False, parent=None, globals={}):
    execInGui(lambda: startHelperGui(exitWhenClosed, parent, globals))

# 1) starts here in the module if file is main
if __name__ == '__main__':
    startHelperGuiInGui(True)

#********************************************
#  LoopsManager GUI  class                  *
#********************************************


class LoopManager(HelperGUI):
    """
    Loop manager GUI
    """

    def __init__(self, parent=None, globals={}):
        """
        Creator of the loop manager panel.
        """
        loopMgr = LoopMgr(
            parent, globals)       # instantiates the backend manager
        # inform the helper it has an associated gui by adding the gui as an
        # attribute
        loopMgr._gui = self
        # init superClasses
        HelperGUI.__init__(self, parent, globals, helper=loopMgr)
        self.debugPrint("in loopManagerGUI frontpanel creator")

        # Build GUI below
        #self.setStyleSheet("""QTreeWidget:Item {padding:6;} QTreeView:Item {padding:6;}""")
        self.initializeIcons()
        title = helperDic['name'] + " version " + helperDic['version']
        if self._helper is not None:
            title += ' in tandem with ' + self._helper.__class__.__name__
        self.setWindowTitle(title)
        self.setWindowIcon(self._icons['loop'])
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setMinimumHeight(200)

        layout = QGridLayout()

        #iconsBarW = QWidget()
        #self._iconsBar = QGridLayout(iconsBarW)
        # layout.addWidget(iconsBarW)
        self.setWindowIcon(self._icons['loop'])
        self._iconsBar = QGridLayout()

        self.playPauseButton = QPushButton('Play/Pause')
        # self.playPauseButton.setIcon(self._icons['play'])
        self.connect(self.playPauseButton, SIGNAL("clicked()"), self.playPause)
        self._iconsBar.addWidget(self.playPauseButton, 0, 0)

        self.stopButton = QPushButton('Stop')
        # self.stopButton.setIcon(self._icons['stop'])
        self.connect(self.stopButton, SIGNAL("clicked()"), self.stop)
        self._iconsBar.addWidget(self.stopButton, 0, 1)

        self.reverseButton = QPushButton('Reverse')
        # self.reverseButton.setIcon(self._icons['reverse'])
        self.connect(self.reverseButton, SIGNAL("clicked()"),
                     lambda: self.modifyStepCoeff(-1))
        self._iconsBar.addWidget(self.reverseButton, 0, 2)

        self.divideStepCoeffButton = QPushButton('1/2')
        # self.divideStepCoeffButton.setIcon(self._icons['slow'])
        self.connect(self.divideStepCoeffButton, SIGNAL(
            "clicked()"), lambda: self.modifyStepCoeff(0.5))
        self._iconsBar.addWidget(self.divideStepCoeffButton, 0, 3)

        # self.changeStepButton=QPushButton()
        # self.changeStepButton.setIcon(self._icons['ask'])
        #self.connect(self.changeStepButton,SIGNAL("clicked()"), self.changeStep)
        # self._iconsBar.addWidget(self.changeStepButton,0,3)

        self.doubleStepCoeffButton = QPushButton('x2')
        # self.doubleStepCoeffButton.setIcon(self._icons['fwd'])
        self.connect(self.doubleStepCoeffButton, SIGNAL(
            "clicked()"), lambda: self.modifyStepCoeff(2))
        self._iconsBar.addWidget(self.doubleStepCoeffButton, 0, 4)

        self.firstButton = QPushButton('First')
        # self.doubleStepCoeffButton.setIcon(self._icons['fwd'])
        self.connect(self.firstButton, SIGNAL("clicked()"), self.first)
        self._iconsBar.addWidget(self.firstButton, 0, 5)

        self.lastButton = QPushButton('Last')
        # self.doubleStepCoeffButton.setIcon(self._icons['fwd'])
        self.connect(self.lastButton, SIGNAL("clicked()"), self.jumpToLast)
        self._iconsBar.addWidget(self.lastButton, 0, 6)

        self.autoReverseBox = QCheckBox('Auto-rev')
        # self.autoReverseButton.setIcon(self._icons['autoReverseButton'])
        self.connect(self.autoReverseBox, SIGNAL(
            "stateChanged(int)"), self.autoReverse)
        self._iconsBar.addWidget(self.autoReverseBox, 0, 7)

        self.autoLoopBox = QCheckBox('Auto-loop')
        # self.autoReverseButton.setIcon(self._icons['autoReverseButton'])
        self.connect(self.autoLoopBox, SIGNAL(
            "stateChanged(int)"), self.autoLoop)
        self._iconsBar.addWidget(self.autoLoopBox, 0, 8)

        self.autoDeleteBox = QCheckBox('Auto-delete')
        # self.autoReverseButton.setIcon(self._icons['autoReverseButton'])
        self.connect(self.autoDeleteBox, SIGNAL(
            "stateChanged(int)"), self.autoDelete)
        self._iconsBar.addWidget(self.autoDeleteBox, 0, 9)

        self.deleteButton = QPushButton('Delete')
        # self.deleteButton.setIcon(self._icons['trash'])
        self.connect(self.deleteButton, SIGNAL("clicked()"), self.delete)
        self._iconsBar.addWidget(self.deleteButton, 0, 10)

        layout.addLayout(self._iconsBar, 0, 0)

        self._looplist = LoopList()
        self.connect(self._looplist, SIGNAL(
            "currentItemChanged(QTreeWidgetItem *,QTreeWidgetItem *)"), self.selectLoop)
        self.connect(self._looplist, SIGNAL(
            "itemDoubleClicked(QTreeWidgetItem *,int)"), self.editVariable)

        layout.addWidget(self._looplist, 1, 0)
        centralWidget = QWidget()
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)

        ##################
        # Initialization #
        ##################

        self._items = dict()
        self._selectedLoop = None
        settings = QSettings()
        self._updated = False

        for loop in self._helper._loops:
            self.addLoop(loop)

    def initializeIcons(self):
        self._icons = dict()
        iconFilenames = {
            "pause": 'player_pause.png',
            "play": 'player_play.png',
            "reverse": 'player_reverse.png',
            "stop": 'player_stop.png',
            "slow": 'player_end.png',
            "fwd": 'player_fwd.png',
            "ask": 'player_ask.png',
            "trash": 'trashcan_full.png',
            "loop": 'recur.png',
        }
        for key in iconFilenames:
            self._icons[key] = QIcon(iconPath + '/' + iconFilenames[key])

    def updatedGui(self, subject, property=None, value=None):
        """
        Private method called when a notification is received.
        """
        # print 'in updatedGui with subject = ',subject,', property =
        # ',property,', value = ',value
        if property == 'addLoop':
            # loop will be added at the correct level if not already present
            self.addLoop(value)
        elif property == 'addChild':
            self.addChild(value)
        elif property == "removeLoop":
            # loop will be removed with all its children if present
            self.removeLoop(value)
        elif property == "removeChild":
            # child will be moved at top level if present
            self.childAtTop(value)
        elif property == "updateLoop":
            self.updateLoop(value)

    def ref(self, loop):
        """
        returns a weak refeence to the loop object to allow garbage collection when the loop won't be referenced any longer.
        """
        return weakref.ref(loop)

    def selectLoop(self, current, last):
        """
        Private method called when the a new QTreeWidgetItem is selected in the QTreeWidget list of loops.
        current and last are the new and old QTreeWidgetItems.
        """
        if current is not None:
            self._selectedLoop = current._loop()
            self.updateLoop(self._selectedLoop)

    def updateLoop(self, loop=None):
        """
        Updates the buttonbar and information displayed in the loop's QTreeWidgetItem:
        button bar should always correspond to the selected loop.
        """
        # get all parameters of the loop
        if loop is not None:
            fp = loop.getParams()
            autoRev, autoLoop, autoDel = fp['mode'] == 'autoRev', fp[
                'mode'] == 'autoLoop', fp['autoDel']
        # update button bar
        if self._selectedLoop is None:
            self.onOffBar(False)
        elif self._selectedLoop == loop:
            self.onOffBar(True)
            for box in [self.autoReverseBox, self.autoLoopBox, self.autoDeleteBox]:
                box.blockSignals(True)
            self.autoReverseBox.setEnabled(True)
            self.autoReverseBox.setChecked(autoRev)
            self.autoLoopBox.setEnabled(not autoRev)
            self.autoLoopBox.setChecked(autoLoop)
            self.autoDeleteBox.setEnabled(True)
            self.autoDeleteBox.setChecked(autoDel)
            for box in [self.autoReverseBox, self.autoLoopBox, self.autoDeleteBox]:
                box.blockSignals(False)
        # update loop item
        if loop is not None:
            # look in the loop dictionary for the passed loop to retrieve the
            # proper QTreeWidgetItem
            item = self._items[self.ref(loop)]
            # item is the QTreeWidgetItem corresponding to the loop
            item.setText(0, fp['name'])
            item.setText(1, loop.__class__.__name__)
            li1 = start, stop, step, index, value, mode, nextValue, steps2Go = fp['start'], fp[
                'stop'], fp['step'], fp['index'], fp['value'], fp['mode'], fp['nextValue'], fp['steps2Go']
            for i, v in zip([2, 3, 4, 5, 6, 7, 8, 9], li1):
                if v is None:
                    v = ''
                item.setText(i, str(v))
            timeEstim = fp['time2Go']
            if isinstance(timeEstim, (float)):
                timeEstim = time.strftime(
                    "%H:%M:%S", time.gmtime(fp['time2Go']))
            else:
                timeEstim = ''
            item.setText(10, timeEstim)
            if loop._paused:
                # self.playPauseButton.setIcon(self._icons['play'])
                self.playPauseButton.setText('Play')
            else:
                # self.playPauseButton.setIcon(self._icons['pause'])
                self.playPauseButton.setText('Pause')
        for i in range(0, self._looplist.columnCount()):
            self._looplist.resizeColumnToContents(i)
        return

    def onOffBar(self, setToOn):
        for button in [self.playPauseButton, self.stopButton, self.reverseButton, self.divideStepCoeffButton, self.doubleStepCoeffButton, self.firstButton, self.lastButton, self.deleteButton]:
            button.setEnabled(setToOn)
        for box in [self.autoReverseBox, self.autoLoopBox, self.autoDeleteBox]:
            box.setEnabled(setToOn)
        if not setToOn:
            self.playPauseButton.setText('Play/Pause')
            for box in [self.autoReverseBox, self.autoLoopBox, self.autoDeleteBox]:
                box.setChecked(False)
                box.setEnabled(False)

    def addLoop(self, loop):
        """
        Adds a loop to the panel if not already present.
        Called at initialization, in response to notifications 'addLoop', or from addChild()
        """
        # print 'in addLoop with loop =', loop.getName()
        # do nothing if the loop is already present at any level
        if self.ref(loop) in self._items:
            return
        item = QTreeWidgetItem()          # prepare the item
        item.setFlags(Qt.ItemIsSelectable |
                      Qt.ItemIsEnabled | Qt.ItemIsEditable)
        item._loop = self.ref(loop)
        loop.attach(self)
        # add to dictionary whatever future level
        self._items[self.ref(loop)] = item
        parent = loop.parent()
        # if the loop has no parent already present
        if parent is None or self.ref(parent) not in self._items:
            # print 'inserting top level item for ',loop.getName()
            self._looplist.insertTopLevelItem(
                self._looplist.topLevelItemCount(), item)  # insert it at the top level
        else:                                                     # else add it as a child item
            # print 'adding child item ', loop.getName(), ' to parent item ',
            # parent.getName()
            # (this is the Qt addChild method of QTreeWidget)
            self._items[self.ref(parent)].addChild(item)
            for child in loop.children():
                self.addLoop(child)           # recursive call for children
        self.updateLoop(loop)

    def addChild(self, child):
        """
        Adds a child loop to the panel if not already present or moves it at the correct place if present and its parent present.
        Called in response to notifications 'addChild'
        """
        # print 'in addChild with loop =', child.getName()
        # if child already present (could be improved by testing also if it is
        # not at the right place)
        if self.ref(child) in self._items:
            self.removeLoop(child, update=False)  # remove it first
        self.addLoop(child)                       # simply call addLoop

    def removeLoop(self, loop, update=True):
        """
        Removes a loop and all its children from the panel, whatever its level.
        Called in response to a notification 'removeLoop'
        """
        # print 'in removeLoop with loop =', loop.getName()
        # call recursively removeLoop to remove the children first.
        for child in loop.children():
            # (easy way to remove them from the dictionary)
            self.removeLoop(child, update=False)
        item = self._items[self.ref(loop)]  # retrieve the QTreeWidgetItem
        parent = item.parent()               # retrieve its possible parent item
        if parent:                         # if parent exist
            # print 'removing child item ', loop.getName()
            parent.removeChild(item)  # remove child
        else:                              # otherwise
            # print 'removing top level item ', loop.getName()
            # remove it from the QTreeWidget
            self._looplist.takeTopLevelItem(
                self._looplist.indexOfTopLevelItem(item))
        del self._items[self.ref(loop)]    # and from the dictionary
        # detach the loop so that it stops sending notifications directly to
        # this loopspanel
        loop.detach(self)
        try:
            if self._selectedLoop == loop:
                self._selectedLoop = None
        except:
            print 'an error occured in removeLoop'
        if update:
            self.updateLoop()      # update only once at the end cause update is false for children

    def childAtTop(self, loop):
        """
        Moves a child loop to top level.
        Called in response to notification 'removeChild' => the loop still exists although it is no longer a child.
        """
        # print 'in childAtTop with loop =', loop.getName()
        item = self._items[self.ref(loop)]
        parentItem = item.parent()               # retrieve its possible parent item
        if parentItem:                         # if parent exist
            # print 'removing child item ', loop.getName()
            parentItem.removeChild(item)  # remove child
        if self._looplist.indexOfTopLevelItem(item) == -1:
            # print 'adding top level item ', loop.getName()
            self._looplist.insertTopLevelItem(
                self._looplist.topLevelItemCount(), item)

    def playPause(self):
        if self._selectedLoop is not None:
            if self._selectedLoop._paused:
                self._selectedLoop.play()
            else:
                self._selectedLoop.pause()
            self.updateLoop(self._selectedLoop)

    def stop(self):
        self._selectedLoop.setFinished()

    def modifyStepCoeff(self, coeff):
        loop = self._selectedLoop
        if loop is not None:
            item = self._items[self.ref(loop)]
            oldStep = float(item.text(4))
            newStep = coeff * oldStep
            loop.setStep(newStep)
            self.updateLoop(loop)

    def first(self):
        self.jumpToValue(self._selectedLoop, 'start')
        self.updateLoop(self._selectedLoop)

    def jumpToLast(self):
        self.jumpToValue(self._selectedLoop, 'stop')
        self.updateLoop(self._selectedLoop)

    def jumpToValue(self, loop, value='start'):
        if loop is not None:
            l, item = self._items[self.ref(loop)]
            if value == 'start':
                value = float(item.text(2))
            elif value == 'stop':
                value = float(item.text(3))
            item.setText(8, str(value))
            loop.jumpToValue(value)
            self.updateLoop(loop)

    def autoReverse(self, state):
        loop = self._selectedLoop
        if loop is not None:
            loop.setAutoreverse(state == 2)
            self.updateLoop(loop)

    def autoLoop(self, state):
        loop = self._selectedLoop
        if loop is not None:
            loop.setAutoloop(state == 2)
            self.updateLoop(loop)

    def autoDelete(self):
        loop = self._selectedLoop
        if loop is not None:
            loop.setAutodelete(state == 2)
            self.updateLoop(loop)

    def delete(self):
        """
        Removes the loop from the loopmanager
        """
        self._loopsmanager.removeLoop(self._selectedLoop)

    def editVariable(self, item, colIndex):
        """
        Prompts for a new value at the specified column index colIndex of QTreeWidgetItem item.
        """
        loop = item._loop()
        if colIndex in [0, 2, 3, 4, 8, 9] or (colIndex == 9 and item.text(colIndex) not in ['inf', '?']):
            val, newVal, ok = [None] * 3
            textValue = str(item.text(colIndex))
            columnName = self._looplist.headerItem().text(colIndex)
            try:
                val = int(textValue)
                newVal, ok = QInputDialog().getInt(self, 'Get new integer value',
                                                   'New % s =' % columnName, value=val)
            except:
                try:
                    val = float(textValue)
                    if 1e-10 < val < 1e10:
                        newVal, ok = QInputDialog().getDouble(self, 'Get new real value', 'New % s =' %
                                                              columnName, value=val, decimals=10)
                    else:
                        while True:
                            newVal, ok = QInputDialog().getText(self, 'Get real value', 'New % s =' %
                                                                columnName, text=textValue)
                            try:
                                newVal = float(newVal)
                                break
                            except:
                                print 'Please enter a valid number'
                except:
                    val = QString(textValue)
                    newVal, ok = QInputDialog().getText(self, 'Get text', 'New % s =' %
                                                        columnName, text=val)
                    newVal = str(newVal)
            if ok and newVal != val:
                functions = ['setName', None, 'setStart', 'setStop', 'setStep',
                             None, None, None, 'jumpToValue', 'setNSteps2Go', None]
                item.setText(colIndex, QString(str(newVal)))
                getattr(loop, functions[colIndex])(newVal)
                self.updateLoop(loop)


class LoopList(QTreeWidget):

    def __init__(self):
        QTreeWidget.__init__(self)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setHeaderLabels(["Name", "Class", "Start", "Stop", "Step", "Index",
                              "Value", "Mode", "Next", "Steps to go", "Time estim.", "Specific"])
        self.setSortingEnabled(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

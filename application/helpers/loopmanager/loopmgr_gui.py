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

# *******************************************
#  Helper initialization                    *
# *******************************************

# Global module dictionary defining the helper
helperDic = {'name': 'Loop Manager', 'version': '1.0', 'authors': 'A. Dewes-V. Schmitt - D. Vion',
             'mail': 'denis.vion@cea.fr', 'start': 'startHelperGui', 'stop': None}


# 3) Start the dataManager
def startHelperGui(exitWhenClosed=False, parent=None, globals={}):
    # define dataManager as a global variable
    global loopManager
    # Instantiate the datamanager gui here
    loopManager = LoopManager("", parent, globals)
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

# ********************************************
#  LoopsManager GUI  class                  *
# ********************************************


class LoopManager(HelperGUI):
    """
    Loop manager GUI
    """

    def __init__(self, name=None, parent=None, globals={}):
        """
        Creator of the loop manager panel.
        """
        # instantiates the backend manager and init superClass HelperGUI
        HelperGUI.__init__(self, name, parent, globals, helper=LoopMgr(name, parent, globals))
        self.debugPrint("in loopManagerGUI frontpanel creator")

        # Build GUI below
        # self.setStyleSheet("""QTreeWidget:Item {padding:6;} QTreeView:Item {padding:6;}""")
        self.initializeIcons()
        title = helperDic['name'] + " version " + helperDic['version']
        if self._helper is not None:
            title += ' in tandem with ' + self._helper.__class__.__name__
        self.setWindowTitle(title)
        self.setWindowIcon(self._icons['loop'])
        # self.setAttribute(Qt.WA_DeleteOnClose, True) # now done at the HelperGUIlevel
        self.setMinimumHeight(200)

        layout = QGridLayout()

        # iconsBarW = QWidget()
        # self._iconsBar = QGridLayout(iconsBarW)
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
        # self.connect(self.changeStepButton,SIGNAL("clicked()"), self.changeStep)
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

        self.autoRemoveBox = QCheckBox('Auto-delete')
        # self.autoReverseButton.setIcon(self._icons['autoReverseButton'])
        self.connect(self.autoRemoveBox, SIGNAL(
            "stateChanged(int)"), self.autoRemove)
        self._iconsBar.addWidget(self.autoRemoveBox, 0, 9)

        self.deleteButton = QPushButton('Remove')
        # self.deleteButton.setIcon(self._icons['trash'])
        self.connect(self.deleteButton, SIGNAL("clicked()"), self.delete)
        self._iconsBar.addWidget(self.deleteButton, 0, 10)

        layout.addLayout(self._iconsBar, 0, 0)

        self._loopsTree = LoopsTreeWidget()
        self.connect(self._loopsTree, SIGNAL(
            "currentItemChanged(QTreeWidgetItem *,QTreeWidgetItem *)"), self.selectLoop)
        self.connect(self._loopsTree, SIGNAL(
            "itemDoubleClicked(QTreeWidgetItem *,int)"), self.editVariable)

        layout.addWidget(self._loopsTree, 1, 0)
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
        # print 'in loopsPanel updatedGui with subject = ',subject,', property
        # = ',property,', value = ',value
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
            self.updateLoop(subject)

    def ref(self, loop):
        """
        returns a weak reference to the loop object to allow garbage collection when the loop won't be referenced any longer.
        """
        return weakref.ref(loop)

    def selectLoop(self, currentItem, lastItem):
        """
        Private method called when the a new QTreeWidgetItem is selected in the QTreeWidget list of loops.
        current and last are the new and old QTreeWidgetItems.
        """
        if currentItem is not None:
            self._selectedLoop = currentItem._loopRef()  # ._loopRef is the true loop
            self.updateLoop(self._selectedLoop)

    def updateLoop(self, loop=None):
        """
        Updates the buttonbar and information displayed in the loop's QTreeWidgetItem:
        button bar should always correspond to the selected loop.
        """
        # get all parameters of the loop
        if loop is not None:
            fp = loop.getParams()
            autoRev, autoLoop, autoRemove = fp['mode'] == 'autoRev', fp[
                'mode'] == 'autoLoop', fp['autoRemove']
        # update button bar
        if self._selectedLoop is None:
            self.onOffBar(False)
        elif self._selectedLoop == loop:
            self.onOffBar(True)
            for box in [self.autoReverseBox, self.autoLoopBox, self.autoRemoveBox]:
                box.blockSignals(True)
            self.autoReverseBox.setEnabled(True)
            self.autoReverseBox.setChecked(autoRev)
            self.autoLoopBox.setEnabled(not autoRev)
            self.autoLoopBox.setChecked(autoLoop)
            self.autoRemoveBox.setEnabled(True)
            self.autoRemoveBox.setChecked(autoRemove)
            for box in [self.autoReverseBox, self.autoLoopBox, self.autoRemoveBox]:
                box.blockSignals(False)
        # update loop item
        if loop is not None:
            # look in the loop dictionary for the passed loop to retrieve the
            # proper QTreeWidgetItem
            item = self._loopsTree.loopRefItemDict()[self.ref(loop)]
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
        for i in range(0, self._loopsTree.columnCount()):
            self._loopsTree.resizeColumnToContents(i)
        return

    def onOffBar(self, setToOn):
        for button in [self.playPauseButton, self.stopButton, self.reverseButton, self.divideStepCoeffButton, self.doubleStepCoeffButton, self.firstButton, self.lastButton, self.deleteButton]:
            button.setEnabled(setToOn)
        for box in [self.autoReverseBox, self.autoLoopBox, self.autoRemoveBox]:
            box.setEnabled(setToOn)
        if not setToOn:
            self.playPauseButton.setText('Play/Pause')
            for box in [self.autoReverseBox, self.autoLoopBox, self.autoRemoveBox]:
                box.setChecked(False)
                box.setEnabled(False)

    def addLoop(self, loop):
        """
        Adds a loop to the panel if not already present.
        Called at initialization, in response to notifications 'addLoop', or from addChild()
        """
        # print 'in addLoop with loop =', loop.getName()
        loopRefItemDict = self._loopsTree.loopRefItemDict()
        # do nothing if the loop is already present at any level
        if self.ref(loop) in loopRefItemDict:
            return
        item = QTreeWidgetItem()          # prepare the item
        item.setFlags(Qt.ItemIsSelectable |
                      Qt.ItemIsEnabled | Qt.ItemIsEditable)
        item._loopRef = self.ref(loop)      # save a weak reference to it
        # define this gui as an observer of the loop
        loop.attach(self)
        parent = loop.parent()
        # if the loop has no parent already present
        if parent is None or self.ref(parent) not in loopRefItemDict:
            # print 'inserting top level item for ',loop.getName()
            self._loopsTree.insertTopLevelItem(
                self._loopsTree.topLevelItemCount(), item)  # insert it at the top level
        else:                                                     # else add it as a child item
            # print 'adding child item ', loop.getName(), ' to parent item ',
            # parent.getName()
            # (this is the Qt addChild method of QTreeWidget)
            loopRefItemDict[self.ref(parent)].addChild(item)
            for child in loop.children():
                self.addLoop(child)           # recursive call for children
        self.updateLoop(loop)             # update once at the end

    def addChild(self, child):
        """
        Adds a child loop to the panel if not already present or moves it at the correct place if present and its parent present.
        Called in response to notifications 'addChild'
        """
        # print 'in addChild with loop =', child.getName()
        # if child already present (could be improved by testing also if it is
        # not at the right place)
        if self.ref(child) in self._loopsTree.loopRefItemDict():
            self.removeLoop(child, update=False)  # remove it first
        self.addLoop(child)                       # simply call addLoop

    def removeLoop(self, loop, update=True):
        """
        Removes a loop and all its children from the panel, whatever its level.
        Called in response to a notification 'removeLoop'
        """
        # print 'in removeLoop with loop =', loop.getName()
        loopRefItemDict = self._loopsTree.loopRefItemDict()

        if self.ref(loop) in loopRefItemDict:
            def detachAll(loop):
                """
                Detaches the current GUI from the loop and all its children
                """
                for child in loop.children():
                    child.detachAll(self)  # recursive call
                loop.detach(self)

            # retrieve the QTreeWidgetItem
            item = loopRefItemDict[self.ref(loop)]
            parent = item.parent()               # retrieve its possible parent item
            if parent:                         # if parent exists
                parent.removeChild(item)  # remove child
            else:                              # otherwise remove it from the QTreeWidget
                self._loopsTree.takeTopLevelItem(
                    self._loopsTree.indexOfTopLevelItem(item))
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
        item = self._loopsTree.loopRefItemDict()[self.ref(loop)]
        parentItem = item.parent()               # retrieve its possible parent item
        if parentItem:                         # if parent exist
            # print 'removing child item ', loop.getName()
            parentItem.removeChild(item)  # remove child
        if self._loopsTree.indexOfTopLevelItem(item) == -1:
            # print 'adding top level item ', loop.getName()
            self._loopsTree.insertTopLevelItem(
                self._loopsTree.topLevelItemCount(), item)

    def playPause(self):
        if self._selectedLoop is not None:
            if self._selectedLoop._paused:
                self._selectedLoop.play()
            else:
                self._selectedLoop.pause()
            self.updateLoop(self._selectedLoop)

    def stop(self):
        if self._selectedLoop is not None:
            self._selectedLoop.stopAtNext()

    def modifyStepCoeff(self, coeff):
        loop = self._selectedLoop
        if loop is not None:
            item = self._loopsTree.loopRefItemDict()[self.ref(loop)]
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
            item = self._loopsTree.loopRefItemDict()[self.ref(loop)]
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

    def autoRemove(self, state):
        loop = self._selectedLoop
        if loop is not None:
            loop.setAutoremove(state == 2)
            self.updateLoop(loop)

    def delete(self):
        """
        Stops and removes the selected loop and its children from the loopmanager backend.
        - The loop will be deleted from memory by garbage collection only if no other reference to it exists
        - The loopmanager backend will then notify the removal, which will trigger the self.removeLoop method above
        """
        if self._selectedLoop is not None:
            self._helper.removeLoop(self._selectedLoop)

    def editVariable(self, item, colIndex):
        """
        Prompts for a new value at the specified column index colIndex of QTreeWidgetItem item.
        The data type is imposed to be the same as the current value.
        """
        loop = item._loopRef()
        val, newVal, ok = [None] * 3
        textValue = str(item.text(colIndex))
        textValue2 = textValue
        colName = self._loopsTree.headerItem().text(colIndex)
        if colName not in ['Name', 'Start', 'Stop', 'Step', 'Next', 'Steps to go']:
            return
        if colName in ['Start', 'Stop'] and textValue == '':
            textValue2 = str(item.text(8))  # use Next to determine the type
        try:
            int(textValue2)
            typ = int
            message = 'Get new integer value'
        except:
            try:
                float(textValue2)
                typ = float
                message = 'Get new real value'
            except:
                typ = str
                message = 'Get new value'
        if colName in ['Start', 'Stop']:
            message += ' (or leave empty)'
        while True:
            newVal, ok = QInputDialog().getText(self, message, 'New % s =' %
                                                colName, text=textValue)
            if not ok:
                break
            if colName in ['Start', 'Stop'] and newVal == '':
                break
            elif typ == int:
                try:
                    newVal = int(newVal)
                    break
                except:
                    print 'Please enter a valid integer number or cancel'
            elif typ == float:
                try:
                    newVal = float(newVal)
                    break
                except:
                    print 'Please enter a valid float number or cancel'
            elif typ == str:
                break
        if ok and (textValue == '' or newVal != typ(textValue)):
            functions = ['setName', None, 'setStart', 'setStop', 'setStep',
                         None, None, None, 'jumpToValue', 'setNSteps2Go', None]
            item.setText(colIndex, QString(str(newVal)))
            if newVal == '':
                newVal = None
            getattr(loop, functions[colIndex])(newVal)
            self.updateLoop(loop)


class LoopsTreeWidget(QTreeWidget):

    def __init__(self):
        QTreeWidget.__init__(self)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setHeaderLabels(["Name", "Class", "Start", "Stop", "Step", "Index",
                              "Value", "Mode", "Next", "Steps to go", "Time estim.", "Specific"])
        self.setSortingEnabled(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setExpandsOnDoubleClick(False)

    def get_subtree_nodes(self, tree_widget_item):
        """Returns all QTreeWidgetItems in the subtree rooted at the given node."""
        nodes = []
        nodes.append(tree_widget_item)
        for i in range(tree_widget_item.childCount()):
            nodes.extend(self.get_subtree_nodes(tree_widget_item.child(i)))
        return nodes

    def get_all_items(self):
        """Returns all QTreeWidgetItems in the given QTreeWidget."""
        all_items = []
        for i in range(self.topLevelItemCount()):
            top_item = self.topLevelItem(i)
            all_items.extend(self.get_subtree_nodes(top_item))
        return all_items

    def loopRefItemDict(self):
        """
        Builds the dictionary {loopRef1: QTreeWidgetItem1, loopRef2: QTreeWidgetItem2}
        """
        return {item._loopRef: item for item in self.get_all_items()}

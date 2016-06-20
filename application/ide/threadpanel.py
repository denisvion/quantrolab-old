import sys
import os
import os.path
import string
import threading
import time

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from application.config.parameters import *
from application.ide.widgets.observerwidget import ObserverWidget


class ThreadPanel(QWidget, ObserverWidget):
    """
    QWidget that refreshes every half second information about the different threads of a codeRunner, corresponding to
     different editors of the editorWindow.
    The widget displays the thread identifier, the thread status (running, finished, or failed), and the source name.
    It is able to stop a killable trhead and to remove a thread from the code runner when the corresponding editor has been closed.
    """

    def __init__(self, codeRunner=None, editorWindow=None, parent=None):
        QWidget.__init__(self, parent)
        ObserverWidget.__init__(self)
        self.setMinimumHeight(200)
        self.setWindowTitle('Active threads')
        layout = QGridLayout()
        self._codeRunner = codeRunner
        self._editorWindow = editorWindow
        self._threads = {}
        self._threadItems = {}
        self._threadView = QTreeWidget()
        self._threadView.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._threadView.setHeaderLabels(['Identifier', 'Status', 'Filename'])

        setupLayout = QBoxLayout(QBoxLayout.LeftToRight)

        killButton = QPushButton('Kill')
        self.connect(killButton, SIGNAL('clicked()'), self.killThread)

        buttonsLayout = QBoxLayout(QBoxLayout.LeftToRight)
        buttonsLayout.addWidget(killButton)
        buttonsLayout.addStretch()

        layout.addWidget(self._threadView)
        layout.addItem(buttonsLayout)

        self.updateThreadList()
        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.start()
        self.connect(self.timer, SIGNAL('timeout()'), self.updateThreadList)

    def updatedGui(self, subject=None, property=None, value=None):
        pass

    def _updateItemInfo(self, item, identifier, thread):
        if identifier in self._threads and self._threads[identifier] == thread:
            return
        self._threads[identifier] = thread
        item.setText(0, str(identifier))
        status = 'running' if thread['isRunning'] else 'failed' if thread['failed'] else 'finished'
        item.setText(1, status)
        filename = str(thread['filename'])
        (di, shortname) = os.path.split(filename)
        item.setText(2, shortname)
        item.setToolTip(2, filename)
        if self._editorWindow is not None:
            editor = self._editorWindow.getEditorForFile(thread['filename'])
            if editor is not None:
                editor.setTabText(' [-]' if thread['isRunning'] else ' [!]' if thread['failed'] else ' [.]')
                self._editorWindow.updateTabText(editor)

    def updateThreadList(self):
        """
        Updates the list of threads by
            - adding threads from the coderunner status that are not already listed
            - removing non running threads created from editors that have been closed.
                (these threads have integer identifiers that are no longer identifier of an editor)
            - updating the status of other threads
        and deletes from the coderunner non-running threads created from editors that have been closed.
        """
        # list of the current threads in the coderunner
        threadDict = self._codeRunner.status()
        if threadDict is None or type(threadDict) != dict:
            return
        # list of identifiers of open editors
        editorIDs = map(id, self._editorWindow.editors)
        # print threadDict.keys() # for debugging
        for idr in threadDict:                                          # add to list of threads
            tobeadded = idr not in self._threadItems and (not isinstance(idr, int) or idr in editorIDs)
            if tobeadded:
                item = QTreeWidgetItem()
                self._updateItemInfo(item, idr, threadDict[idr])
                self._threadView.insertTopLevelItem(self._threadView.topLevelItemCount(), item)
                self._threadItems[idr] = item
        tbr = []
        for idr in self._threadItems:                                   # update in or remove from list of threads
            orphean = idr in threadDict and isinstance(idr, int) and idr not in editorIDs
            orphean = orphean and not threadDict[idr]['isRunning']
            toberemoved = orphean or idr not in threadDict
            if toberemoved:
                tbr.append(idr)
                if orphean:
                    self._codeRunner.deleteThread(idr)
            else:
                item = self._threadItems[idr]
                self._updateItemInfo(item, idr, threadDict[idr])
        for idr in tbr:
            item = self._threadItems[idr]
            self._threadView.takeTopLevelItem(self._threadView.indexOfTopLevelItem(item))
            del self._threadItems[idr]
            del self._threads[idr]

    def killThread(self):
        selectedItems = self._threadView.selectedItems()
        for item in selectedItems:
            keys, values = self._threadItems.keys(), self._threadItems.values()
            if item in self._threadItems.values():
                identifier = filter(lambda x: x[0] == item, zip(values, keys))[0][1]
                self._codeRunner.stopExecution(identifier)

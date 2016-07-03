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
        self._codeRunner = codeRunner           # handle to coderunner
        self._editorWindow = editorWindow       # handle to coderunner
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

    def threadIds(self):
        """
        Returns the dictionary {identifier: item} of the threadview QTreeWidget.
        """
        count = self._threadView.topLevelItemCount()
        header = self._threadView.headerItem()
        index = [str(header.text(i)) for i in range(header.columnCount())].index('Identifier')
        items = [item for item in [self._threadView.topLevelItem(j) for j in range(count)]]
        keys = [str(item.text(index)) for item in items]
        keys = [int(key) if key.isdigit() else key for key in keys]
        return {key: item for key, item in zip(keys, items)}

    def updateThreadList(self):
        """
        Updates the list of threads by
            - adding threads from the coderunner status that are not already listed
            - removing non running threads created from editors that have been closed.
                (these threads have integer identifiers that are no longer identifier of an editor)
            - removing non running threads created from IDE.
                (these threads have a text identifier)
            - updating the status of other threads
        and deletes from the coderunner non-running threads created from editors that have been closed.
        """
        # list of the current threads in the coderunner
        threadDict = self._codeRunner.status()
        if threadDict is None or type(threadDict) != dict:
            return
        # list of identifiers of open editors
        editorIDs = map(id, self._editorWindow.editors)
        # list of displayed identifiers
        threadIds = self.threadIds()
        for idr in threadDict:                                          # add to list of threads
            tobeadded = idr not in threadIds  # and (not isinstance(idr, int) or idr in editorIDs)
            if tobeadded:
                item = QTreeWidgetItem()
                self._updateItemInfo(item, idr, threadDict[idr])
                self._threadView.insertTopLevelItem(self._threadView.topLevelItemCount(), item)

        tbr = []
        for idr in threadIds:                                           # update in or remove from list of threads
            orphean = idr in threadDict and idr not in editorIDs and isinstance(idr, int)
            orphean = orphean and not threadDict[idr]['isRunning']
            toberemoved = orphean or idr not in threadDict
            if toberemoved:
                tbr.append(idr)
                if orphean:
                    self._codeRunner.deleteThread(idr)
            else:
                item = threadIds[idr]
                self._updateItemInfo(item, idr, threadDict[idr])
        for idr in tbr:
            item = threadIds[idr]
            self._threadView.takeTopLevelItem(self._threadView.indexOfTopLevelItem(item))

    def _updateItemInfo(self, item, identifier, thread):
        headers = self._threadView.headerItem()
        headers = [str(headers.text(i)) for i in range(headers.columnCount())]
        item.setText(headers.index('Identifier'), str(identifier))
        status = 'running' if thread['isRunning'] else 'failed' if thread['failed'] else 'finished'
        item.setText(headers.index('Status'), status)
        filename = str(thread['filename'])
        (di, shortname) = os.path.split(filename)
        index = headers.index('Filename')
        item.setText(index, shortname)
        item.setToolTip(index, filename)
        if self._editorWindow is not None:
            editor = self._editorWindow.getEditorForFile(thread['filename'])
            if editor is not None:
                editor.setTabText(' [-]' if thread['isRunning'] else ' [!]' if thread['failed'] else ' [.]')
                self._editorWindow.updateTabText(editor)

    def killThread(self):
        header = self._threadView.headerItem()
        index = [str(header.text(i)) for i in range(header.columnCount())].index('Identifier')
        ids = [str(item.text(index)) for item in self._threadView.selectedItems()]
        ids = [int(id1) if id1.isdigit() else id1 for id1 in ids]
        for id1 in ids:
            print 'Stopping code thread', id1, '... ',
            self._codeRunner.stopExecution(id1)

    def updatedGui(self, subject=None, property=None, value=None):
        pass

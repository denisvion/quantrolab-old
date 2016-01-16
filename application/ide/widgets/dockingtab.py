import sys
from application.ide.coderun.coderunner import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *


class DockToTabWidget(QDockWidget):
    """
    QDockWidget dockable in a DockingTabWidget (subclassed QTabWidget) rather than in a QMainWindow
    """

    def __init__(self, title, parent=0):
        QDockWidget.__init__(self, title, parent)
        self._title = title
        self.topLevelChanged.connect(self.dockToTab)

    def dockToTab(self):
        if not self.isFloating():
            self.parent().addTab(self.widget(), self._title)
            self.close()
            del self


class DockingTabWidget(QTabWidget):
    """
    QTabWidget whose tabs can be made floating in a QDockWindow.
    A tab with name name can be made floatable or not with setFloatable(name) or setNotFloatable(name)
    A tab with name name can be made closable or not with setClosable(name) or setNotClosable(name)
    """

    def __init__(self):
        super(DockingTabWidget, self).__init__()
        self.setMovable(True)
        self.setTabsClosable(True)
        self.notFloatable = []		# name of the tabs that can't be undocked
        self.tabBar().installEventFilter(self)
        self.motion = 'rest'
        self.tabCloseRequested.connect(self.tabClose)

    def setNotFloatable(self, name):
        if name not in self.notFloatable:
            self.notFloatable.append(name)

    def setFloatable(self, name):
        if name in self.notFloatable:
            self.notFloatable.remove(name)

    def setNotClosable(self, name):
        index = [self.tabText(i) for i in range(self.count())].index(name)
        self.tabBar().setTabButton(index, 1, None)

    def setClosable(self, name):
        index = [self.tabText(i) for i in range(self.count())].index(name)
        self.tabBar().setTabButton(index, 1, 1)

    def eventFilter(self, object, event):
        """
        Event filter detecting double click for undocking a tab
        """
        if object == self.tabBar():
            if event.type() == QEvent.MouseButtonDblClick:
                pos = event.pos()
                tabIndex = object.tabAt(pos)
                title = self.tabText(tabIndex)
                if title not in self.notFloatable:
                    widget = self.widget(tabIndex)
                    self.removeTab(tabIndex)
                    dockWidget = DockToTabWidget(title, parent=self)
                    dockWidget.setFeatures(QDockWidget.AllDockWidgetFeatures)
                    dockWidget.setWidget(widget)
                    dockWidget.setFloating(True)
                    dockWidget.move(self.mapToGlobal(pos))
                    dockWidget.show()
                    return True
            return False

    def tabClose(self, index):
        self.removeTab(index)

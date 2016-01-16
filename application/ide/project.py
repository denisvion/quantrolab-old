"""
Class module defining the Project class and its Qt interface class ProjectView (derived from QTreeview). 
"""

import yaml
import application.lib.objectmodel as objectmodel


class Project(object):
    """
    Class implementing the concept of user project in a similar waya as in other integrated development environment.
    The project is a set of code files, organised hyerachicaly in a tree, having parameters, and being saved in a project file with extension '.prj'.
    """

    def __init__(self):
        self._tree = objectmodel.Folder("[project]")
        self._parameters = dict()
        self._filename = None
        self._lastState = self.saveToString()

    def parameters(self):
        return self._parameters

    def setParameters(self, parameters):
        self._parameters = parameters

    def tree(self):
        return self._tree

    def setTree(self, tree):
        self._tree = tree

    def setFilename(self, filename):
        self._filename = filename

    def filename(self):
        return self._filename

    def saveToFile(self, filename):
        string = self.saveToString()
        file = open(filename, "w")
        file.write(string)
        file.close()
        self.setFilename(filename)
        self._lastState = string

    def loadFromFile(self, filename):
        file = open(filename, "r")
        content = file.read()
        file.close()
        self.loadFromString(content)
        self.setFilename(filename)
        self._lastState = content

    def hasUnsavedChanges(self):
        if self._lastState != self.saveToString():
            return True
        return False

    def saveToString(self):
        converter = objectmodel.Converter()
        treedump = converter.dump(self._tree)
        return yaml.dump({'tree': treedump, 'parameters': self._parameters})

    def loadFromString(self, string):
        params = yaml.load(string)
        converter = objectmodel.Converter()
        self._tree = converter.load(params["tree"])
        self._parameters = params["parameters"]

#############
#   Qt gui  #
#############

from PyQt4.QtGui import *
from PyQt4.QtCore import *


class ProjectModel(QAbstractItemModel):

    def __init__(self, root, parent=None):
        QAbstractItemModel.__init__(self, parent)
        self._root = root
        self._nodeList = []
        self._dropAction = Qt.MoveAction
        self._mimeData = None

    def setProject(self, project):
        self.beginResetModel()
        self._root = project
        self.endResetModel()

    def project(self):
        return self._root

    def headerData(self, section, orientation, role):
        if section == 1:
            return QVariant(QString(u""))

    def deleteNode(self, index):
        parent = self.parent(index)
        node = self.getNode(index)
        parentNode = self.getNode(parent)
        if parentNode is None:
            parentNode = self._root
        self.beginRemoveRows(parent, index.row(), index.row())
        parentNode.removeChild(node)
        self.endRemoveRows()

    def getIndex(self, node):
        if node in self._nodeList:
            return self._nodeList.index(node)
        self._nodeList.append(node)
        index = self._nodeList.index(node)
        return index

    def getNode(self, index):
        if not index.isValid():
            return self._root
        return self._nodeList[index.internalId()]

    def parent(self, index):
        if index == QModelIndex():
            return QModelIndex()
        node = self.getNode(index)
        if node is None:
            return QModelIndex()
        if node.parent() is None:
            return QModelIndex()
        if node.parent().parent() is None:
            return QModelIndex()
        else:
            grandparent = node.parent().parent()
            row = grandparent.children().index(node.parent())
            return self.createIndex(row, 0, self.getIndex(node.parent()))

    def hasChildren(self, index):
        node = self.getNode(index)
        if node is None:
            return True
        if node.hasChildren():
            return True
        return False

    def data(self, index, role=Qt.DisplayRole):
        node = self.getNode(index)
        if role == Qt.DisplayRole:
            return QVariant(node.name())
        return QVariant()

    def index(self, row, column, parent):
        parentNode = self.getNode(parent)
        if parentNode is None:
            if row < len(self._root.children()):
                return self.createIndex(row, column, self.getIndex(self._root.children()[row]))
        elif row < len(parentNode.children()):
            return self.createIndex(row, column, self.getIndex(parentNode.children()[row]))
        return QModelIndex()

    def columnCount(self, parent):
        return 1

    def supportedDropActions(self):
        return Qt.MoveAction | Qt.CopyAction

    def setDropAction(self, action):
        self._dropAction = action

    def rowCount(self, parent):
        if not parent.isValid():
            return len(self._root.children())
        node = self.getNode(parent)
        return len(node.children())

    def flags(self, index):
        defaultFlags = QAbstractItemModel.flags(self, index)
        if index.isValid():
            return Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | defaultFlags
        else:
            return Qt.ItemIsDropEnabled | defaultFlags

    def mimeData(self, indexes):
        mimeData = QMimeData()
        mimeData.setData("projecttree/internalMove", "")
        self._moveIndexes = indexes
        return mimeData

    def addNode(self, node, parent=QModelIndex()):
        self.beginInsertRows(parent, 0, 0)
        parentNode = self.getNode(parent)
        parentNode.insertChild(0, node)
        self.endInsertRows()

    def dropMimeData(self, data, action, row, column, parent):
        """
        This is the function that manages the drop on the the projectView QTreeView
        """
        # To do: clean this fucntion to get the right drop behavior in any case
        # print data,action,row,column,parent,self.getNode(parent),data.formats
        if row == -1:
            row = 0
        if data != None:
            parentNode = self.getNode(parent)
            if parentNode is None:
                return False
            if data.hasFormat("projecttree/internalMove"):
                if self._dropAction == Qt.MoveAction:
                    parentNode = self.getNode(parent)
                    while type(parentNode) is not objectmodel.Folder:
                        if parentNode.parent() is None:
                            return False
                        parentNode = parentNode.parent()
                        parent = self.parent(parent)
                    for index in self._moveIndexes:
                        oldParent = index.parent()
                        oldParentNode = self.getNode(oldParent)
                        node = self.getNode(index)
                        rowOfChild = oldParentNode.children().index(node)
                        if oldParentNode == parentNode and rowOfChild == row:
                            return False
                        if node.isAncestorOf(parentNode):
                            return False
                        self.beginMoveRows(
                            oldParent, rowOfChild, rowOfChild, parent, 0)
                        oldParentNode.removeChild(node)
                        parentNode.insertChild(0, node)
                        self.endMoveRows()
            elif data.hasUrls():
                index = parent
                # print index,data.url()
                while type(parentNode) != objectmodel.Folder:
                    if parentNode.parent() is None:
                        return False
                    index = self.parent(index)
                    parentNode = parentNode.parent()
                for url in data.urls():
                    if url.toLocalFile() != "":
                        fileNode = objectmodel.File(url=str(url.toLocalFile()))
                        self.beginInsertRows(index, len(
                            parentNode), len(parentNode))
                        parentNode.addChild(fileNode)
                        self.endInsertRows()
        return True


class ProjectView(QTreeView):

    def __init__(self, parent=None):
        QTreeView.__init__(self, parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.connect(self, SIGNAL(
            "customContextMenuRequested(const QPoint &)"), self.getContextMenu)

    def dragMoveEvent(self, e):
        e.accept()

    def dragEnterEvent(self, e):
        e.acceptProposedAction()

    def getContextMenu(self, p):
        menu = QMenu()
        selectedItems = self.selectedIndexes()
        if len(selectedItems) == 1:
            renameAction = menu.addAction("Edit")
            self.connect(renameAction, SIGNAL(
                "triggered()"), self.editCurrentItem)
            deleteAction = menu.addAction("Delete")
            self.connect(deleteAction, SIGNAL(
                "triggered()"), self.deleteCurrentItem)
        menu.exec_(self.viewport().mapToGlobal(p))

    def createNewFolder(self):
        selectedIndices = self.selectedIndexes()
        if len(selectedIndices) == 0:
            index = QModelIndex()
        else:
            index = selectedIndices[0]

        node = self.model().getNode(index)

        while type(node) != objectmodel.Folder:
            if node.parent() is None:
                return
            node = node.parent()
            index = self.model().parent(index)

        dialog = QInputDialog()
        dialog.setWindowTitle("New Folder")
        dialog.setLabelText("Name")
        dialog.setTextValue("")
        dialog.exec_()
        if dialog.result() == QDialog.Accepted:
            node = objectmodel.Folder(str(dialog.textValue()))
            self.model().addNode(node, index)

    def editCurrentItem(self):

        selectedItems = self.selectedIndexes()
        if len(selectedItems) == 1:
            index = selectedItems[0]
            node = self.model().getNode(index)
            if node is None or type(node) != objectmodel.Folder:
                return
            dialog = QInputDialog()
            dialog.setWindowTitle("Edit Folder")
            dialog.setLabelText("Name")
            dialog.setTextValue(node.name())
            dialog.exec_()
            if dialog.result() == QDialog.Accepted:
                node.setName(str(dialog.textValue()))

    def deleteCurrentItem(self):
        selectedItems = self.selectedIndexes()
        if len(selectedItems) == 1:
            message = QMessageBox(QMessageBox.Question, "Confirm deletion",
                                  "Are you sure that you want to delete this node?", QMessageBox.Yes | QMessageBox.No)
            message.exec_()
            if message.standardButton(message.clickedButton()) != QMessageBox.Yes:
                return
            self.model().deleteNode(selectedItems[0])

    def openFile(self, node):
        if type(node) == objectmodel.File:
            self.emit(SIGNAL("openFile(PyQt_PyObject)"), node.url())

    def mouseDoubleClickEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            node = self.model().getNode(index)
            if type(node) == objectmodel.File:
                self.emit(SIGNAL("openFile(PyQt_PyObject)"), node.url())
                event.accept()
                return
        QTreeView.mouseDoubleClickEvent(self, event)

    def selectionChanged(self, selected, deselected):
        if len(selected.indexes()) == 1:
            node = self.model().getNode(selected.indexes()[0])
        else:
            pass
        QTreeView.selectionChanged(self, selected, deselected)

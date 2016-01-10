#*******************************************************************************
# datacubeview2 class that provides a table view of a datacube.                *
#*******************************************************************************

___debugDCV2___ = False
def debugDCV2(*args):
  if ___debugDCV2___:
    for arg in args: print arg,
    print

#Imports

import sys,mimetypes,getopt,re,weakref

from PyQt4.QtGui import * 
from PyQt4.QtCore import *
from numpy import complex128

from application.ide.widgets.observerwidget import ObserverWidget

#This is our directory model...
class DatacubeViewModel(QAbstractItemModel,ObserverWidget):

  def __init__(self,cube):
    QAbstractItemModel.__init__(self)
    ObserverWidget.__init__(self)
    self.setDatacube(cube)

  def setDatacube(self,cube):
    if hasattr(self,'_cube') and self._cube != None:
      self._cube.detach(self)
    self._cube = cube
    self.emit(SIGNAL("modelReset()"))
    if cube != None:
      self._cube.attach(self)

  def updated(self,cube,property = None,value = None):
    if cube != self._cube:
      cube.detach(self)
    else:
      self.emit(SIGNAL("layoutChanged()"))
  
  def flags(self,index):
    return QAbstractItemModel.flags(self,index) | Qt.ItemIsEditable
    
  def datacube(self):
    return self._cube
    
  def setElement(self,index,value):
    cube=self._cube
    iy = index.column()
    ix = index.row()
    if value == "":
      return
    elif cube.dataType() == complex128:
      val=complex(value)
    else: 
      val= float(value)
    kwargs={cube.columnName(iy):val}
    if ix < len(cube):
      notify=True
    else:
      notify=False
    cube.set(rowIndex=ix,notify=notify,commit=False,**kwargs)
    self.emit(SIGNAL("cellChanged()"))
    if ix>len(cube):
      cube.addRow(notify=False)
      self.emit(SIGNAL("layoutChanged()"))
     
  def getElement(self,index):
    ix = index.row()
    iy = index.column()
    cube=self._cube
    table=cube._table
    if table is None or (ix >=len(table)) or (ix > len(cube)) : return "" # get elements up to first row out of datacube, i.e. up to index = length
    else:
      value = self._cube._table[ix,iy]                   # _table is the whole table including the first element outside cube whereas table() is       
      if self._cube.table().dtype == complex128:         # on ly the valid part from 0 to length -1
        if value == 0:  return "0"
        return str(value)[1:-1]
      return str(value)
          
  def index(self,row,column,parent):
    return self.createIndex(row,column,None)
    
  def parent(self,index):
    return QModelIndex()

  def headerData(self,section,orientation,role = Qt.DisplayRole):
    if role == Qt.DisplayRole and orientation == Qt.Vertical:
      return QString(str(section))
    if role == Qt.DisplayRole and orientation == Qt.Horizontal and self._cube != None:
      name = self._cube.columnName(section)
      if name != None:
        return QString(name)
    return QAbstractItemModel.headerData(self,section,orientation,role)

  #Returns the data for the given node...
  def data(self,index,role):
    if role == Qt.DisplayRole:
      element = self.getElement(index)
      return QVariant(element)
    elif role == Qt.TextColorRole:
      if index.row()>=len(self._cube):
        return QVariant(QColor('red'))
    return QVariant()
    
  def hasChildren(self,index):
    return False
  
  def rowCount(self,index):
    if self._cube is None:
      return 0
    return len(self._cube)+2
    
  #Returns the rowCount of a given node. If the corresponding directory has never been parsed, we call buildDirectory to do so.
  def columnCount(self,index):
    if self._cube is None:
      return 0
    return len(self._cube.names())

class ElementDelegate(QItemDelegate):
  
  def setModel(self,model):
    self._model = model
  
  def setModelData(self,editor,model,index):    
    self._model.setElement(index,str(editor.text()))
  
  def setEditorData(self,editor,index):
    value = self._model.getElement(index)
    editor.setText(str(value))
  
  def createEditor(self,parent,option,index):
    return QLineEdit(parent)
    

class DatacubeTableView(QTableView):
  
  def __init__(self,cube = None,parent = None):
    QTableView.__init__(self,parent)
    self.delegate = ElementDelegate(self)
    self.dirModel = DatacubeViewModel(cube)
    self.delegate.setModel(self.dirModel)
    self.setModel(self.dirModel)
    self.setItemDelegate(self.delegate)
    self.setAutoScroll(True)
    self.setEditTriggers(QAbstractItemView.AnyKeyPressed | QAbstractItemView.SelectedClicked | QAbstractItemView.DoubleClicked)
    self.setSelectionMode(QAbstractItemView.ContiguousSelection)
    self.connect(self.horizontalHeader(),SIGNAL("sectionDoubleClicked(int)"),self.renameColumn)
    self.connect(self.selectionModel(),SIGNAL("currentChanged(QModelIndex,QModelIndex)"),self.newSelectedItem)

  def newSelectedItem(self,newSelected,previous):
    cube=cube=self.dirModel.datacube()
    newRow=newSelected.row()
    prevRow=previous.row()
    if newRow>len(cube) and prevRow != newRow:
      self.addRow()

  def setDatacube(self,cube):
    self.dirModel.setDatacube(cube)
    self.dirModel.reset()
    self.setContextMenuPolicy(Qt.CustomContextMenu)
    self.connect(self, SIGNAL("customContextMenuRequested(const QPoint &)"), self.getContextMenu)
  
  def removeRows(self,rows):
    self.dirModel.datacube().removeRows(rows,notify=True)

  def removeColumns(self,cols):
    self.dirModel.datacube().removeColumns(cols,notify=True)

  def addColumn(self):
    self.dirModel.datacube().createCol(notify=True)

  def addRow(self):
    self.dirModel.datacube().addRow(notify=True)

  def insertRows(self,rows):
    self.dirModel.datacube().insertRows(rowIndex=min(rows),numberOfRows=len(rows),notify=True)
  
  def insertColumns(self,cols):
    index=min(cols)
    for i in range(len(cols)):
      self.dirModel.datacube().createCol(columnIndex=index+i,notify=True)

  def renameColumn(self,index):
    cube=self.dirModel.datacube()
    oldName = cube.columnName(index)
    dialog = QInputDialog()
    dialog.setWindowTitle("Rename column")
    dialog.setLabelText("New name:")
    dialog.setTextValue(oldName)
    newName = None
    dialog.exec_()
    str1=str(dialog.textValue())
    if dialog.result() == QDialog.Accepted and str1 != oldName :
      if str1 != "":
        newName = str1
      cube.renameColumn(oldName,newName)

  def copyAsPlainText(self,rows,cols):
    st=""
    model=self.dirModel
    for row in rows:
      for col in cols:
        index=model.index(row,col,None) # DV not shure when setting parent to None
        st+=model.data(index,0).toString()
        if col<cols[-1]:st+='\t'
      if row<rows[-1]: st+='\n'
    QApplication.clipboard().setText(st)

  def getContextMenu(self,p):
    menu = QMenu()
    selectedItems = self.selectedIndexes()
    cols = []
    rows=[]
    for index in selectedItems:
      cols.append(index.column())
      rows.append(index.row())
    cols=sorted(list(set(cols)))
    rows=sorted(list(set(rows)))
    if len(selectedItems) >= 1:
      copy=menu.addAction("Copy")
      menu.addSeparator()
      addRow = menu.addAction("Add a last row")
      insertRows = menu.addAction("Insert rows before selection")
      removeRows = menu.addAction("Remove selected rows")
      menu.addSeparator()
      addColumn = menu.addAction("Add a last column")
      insertColumns = menu.addAction("Insert columns before selection")
      removeColumns = menu.addAction("Remove selected columns")
      self.connect(copy,SIGNAL("triggered()"),lambda: self.copyAsPlainText(rows,cols))
      self.connect(addRow,SIGNAL("triggered()"),self.addRow)
      self.connect(addColumn,SIGNAL("triggered()"),self.addColumn)
      self.connect(removeRows,SIGNAL("triggered()"),lambda: self.removeRows(rows))
      self.connect(removeColumns,SIGNAL("triggered()"),lambda: self.removeColumns(cols))
      self.connect(insertRows,SIGNAL("triggered()"),lambda : self.insertRows(rows))
      self.connect(insertColumns,SIGNAL("triggered()"),lambda : self.insertColumns(cols))
    menu.exec_(self.viewport().mapToGlobal(p))
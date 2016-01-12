import os,traceback,math,sys,time,re

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from syntaxhighlighter import *
from application.config.parameters import *
from application.ide.widgets.observerwidget import ObserverWidget

DEVELOPMENT = False

class ErrorConsole(QTreeWidget,ObserverWidget):

  def __init__(self,codeEditorWindow,codeRunner,parent = None):
    self._codeEditorWindow = codeEditorWindow
    self._codeRunner = codeRunner
    QTreeWidget.__init__(self,parent)
    ObserverWidget.__init__(self)
    self.connect(self,SIGNAL("itemDoubleClicked(QTreeWidgetItem *,int)"),self.itemDoubleClicked)
    self.setColumnCount(2)
    self.setColumnWidth(0,400)
    self.setHeaderLabels(["filename","line"])

  def updatedGui(self,subject,property,value = None):
    if subject == self._codeRunner and property == "exceptions":
      for info in value:
        self.processErrorTraceback(info)
      self._codeRunner.clearExceptions()

  def itemDoubleClicked(self,item,colum):
    if item.parent() != None:
      filename = unicode(item.text(0))
      line = int(item.text(1))
      editor = self._codeEditorWindow.openFile(filename)
      if editor is None:
        return
      editor.highlightLine(line)

  def processErrorTraceback(self,exceptionInfo):

    while self.topLevelItemCount() > 20:
      self.takeTopLevelItem(self.topLevelItemCount()-1)

    (exception_type,exception_value,tb) = exceptionInfo

    text = traceback.format_exception_only(exception_type,exception_value)[0]

    text = text.replace("\n"," ")

    tracebackEntries = traceback.extract_tb(tb)
    exceptionItem = QTreeWidgetItem()


    font = QFont()
    font.setPixelSize(14)

    exceptionItem.setFont(0,font)

    self.insertTopLevelItem(0,exceptionItem)

    exceptionItem.setText(0,text)
    exceptionItem.setFirstColumnSpanned(True)
    exceptionItem.setFlags(Qt.ItemIsEnabled)

    for entry in tracebackEntries[1:]:
      (filename, line_number, function_name, text) = entry

      if os.path.exists(filename) and os.path.isfile(filename):
        item = QTreeWidgetItem()
        exceptionItem.addChild(item)
        item.setText(0,filename)
        item.setText(1,str(line_number))

class EditorTabBar(QTabBar):

  def __init__(self,parent = None):
    QTabBar.__init__(self,parent)
    self._startDragPosition = None

  def mousePressEvent(self,e):
    if (e.buttons() & Qt.LeftButton):
      self._startDragPosition = e.pos()
      self._tab = self.tabAt( e.pos())
      self.move=False
    QTabBar.mousePressEvent(self,e) # why not using ignore() ?

  def mouseMoveEvent(self,e):
    # We try here to make compatible the movable tabs along x with a drag and drop triggered by a vertical drag.
    if (e.buttons() & Qt.LeftButton):
      #if (e.pos()-self._startDragPosition).manhattanLength() > QApplication.startDragDistance():
      x,y,w,h,s=e.pos().x(),e.pos().y(),self.width(),self.height(),10
      self.move = self.move or abs(x-self._startDragPosition.x()) > s
      if not self.move and (y<-s or y>h+s):                        # start a Drag if vertical drag by more than s pixels outside tabBar
        drag = QDrag(self)
        url = QUrl.fromLocalFile(str(self.tabToolTip(self._tab)))
        mimeData = QMimeData()
        mimeData.setUrls([url])
        drag.setMimeData(mimeData)
        drag.exec_()
        # insert something here to repaint the tabBar so that tab that has started to move go back to its initial position
        # to do: correct the drop of file with no url.
      else:
        QTabBar.mouseMoveEvent(self,e)
    else:
      QTabBar.mouseMoveEvent(self,e)

class CodeEditorWindow(QWidget):

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

    def checkForOpenFile(self,filename):
      if filename is None:
        return None
      path = os.path.normpath(str(filename))
      for i in range(0,self.tab.count()):
        if self.tab.widget(i).filename() == path:
          self.tab.setCurrentWidget(self.tab.widget(i))
          return self.tab.widget(i)
      return None

    def saveCurrentFile(self):
      currentEditor = self.currentEditor()
      if currentEditor.filename() is None:
        return self.saveCurrentFileAs()
      else:
        return currentEditor.save()

    def saveCurrentFileAs(self):
      currentEditor = self.currentEditor()
      filename = str(QFileDialog.getSaveFileName(caption='Save file as',filter = "Python(*.py *.pyw)",directory = self.workingDirectory()))
      if filename != "":
        print "Saving document as %s" % filename
        self.setWorkingDirectory(filename)
        currentEditor.setFilename(filename)
        return self.saveCurrentFile()
      return False

    def getEditorForFile(self,filename):
      for i in range(0,self.tab.count()):
        editor = self.tab.widget(i)
        if editor.filename() == filename:
          return editor
      return None

    def updateTabText(self,editor):
      index = self.tab.indexOf(editor)
      extraText = editor.tabText()
      if editor.hasUnsavedModifications():
        changedText = "*"
      else:
        changedText = ""
      if editor.filename() != None:
        (dir,file) = os.path.split(editor.filename())
        self.tab.setTabText(index,file+extraText+changedText)
        self.tab.setTabToolTip(index,str(editor.filename()))
      else:
        currentTabText=self.tab.tabText(index)
        if currentTabText in [None,'']: currentTabText='untitled'
        self.tab.setTabText(index,currentTabText+extraText+changedText)
        self.tab.setTabToolTip(index,currentTabText)

    def openFile(self,filename = None):

      if filename is None:
        filename = str(QFileDialog.getOpenFileName(caption='Open file',filter = "Python(*.py *.pyw)",directory = self.workingDirectory()))

      if filename == "":
        return None

      if self.checkForOpenFile(filename) != None:
        return self.checkForOpenFile(filename)

      if os.path.isfile(str(filename)):
        self.setWorkingDirectory(filename)
        editor = self.newEditor()
        editor.openFile(filename)
        self.saveTabState()
        return editor
      return None

    def editorHasUnsavedModifications(self,editor,changed):
      self.updateTabText(editor)

    def newEditor(self,editor = None):
      if editor is None:
        editor = CodeEditor()
        editor.append("")
        editor.activateHighlighter()
      self.editors.append(editor)
      self.tab.addTab(editor,"untitled %i" % self.count)
      self.tab.setTabToolTip(self.tab.indexOf(editor),"untitled %i" % self.count)
      self.connect(editor,SIGNAL("hasUnsavedModifications(bool)"),lambda changed,editor = editor: self.editorHasUnsavedModifications(editor,changed))
      self.count = self.count + 1
      self.tab.setCurrentWidget(editor)
      if self._newEditorCallback != None:
        self._newEditorCallback(editor)
      return editor

    def saveTabState(self):
      openFiles = list()
      for i in range(0,self.tab.count()):
        widget = self.tab.widget(i)
        if widget.filename() != None:
          openFiles.append(QString(widget.filename()))
      settings = QSettings()
      settings.setValue('Editor/OpenFiles',openFiles)

    def restoreTabState(self):
      settings = QSettings()
      if settings.contains("Editor/OpenFiles"):
        openFiles = settings.value("Editor/OpenFiles").toList()
        if openFiles != None:
          for file in openFiles:
            self.openFile(file.toString())
      else:
        self.newEditor()

    def closeEditor(self,editor,askOnly = False, runCheck=True):
      if runCheck and hasattr(editor,'hasBeenRun') and editor.hasBeenRun:
          identifier=id(editor)
          question='Closing this editor terminates the access to thread %i. Close anyway?' % identifier
          if QMessageBox.question (self,'Warning', question, QMessageBox.Ok, QMessageBox.Cancel) == QMessageBox.Cancel:
              return
      if editor.hasUnsavedModifications():
        self.tab.setCurrentWidget(editor)
        messageBox = QMessageBox()
        messageBox.setWindowTitle("Warning!")
        if editor.filename() != None:
          messageBox.setText("Save changes made to file \"%s\"?" % editor.filename())
        else:
          messageBox.setText("Save changes made to this unsaved buffer?")
        yes = messageBox.addButton("Yes",QMessageBox.YesRole)
        no = messageBox.addButton("No",QMessageBox.NoRole)
        cancel = messageBox.addButton("Cancel",QMessageBox.RejectRole)
        messageBox.exec_()
        choice = messageBox.clickedButton()
        if choice == yes:
          if self.saveCurrentFile() == False:
            return False
        elif choice == cancel:
          return False
      if askOnly:
        return True
      if editor.close():
        self.editors.remove(editor)
        editor.destroy()
        self.tab.removeTab(self.tab.indexOf(editor))
        if self.tab.count() == 0:
          self.count = 1
          self.newEditor()
        self.saveTabState()
        return True
      return False

    def closeEvent(self,e):
      for i in range(0,self.tab.count()):
        if self.closeTab(i,askOnly = True, runCheck=False) == False:
          e.ignore()
          return
      self.saveTabState()

    def closeCurrentFile(self):
      index = self.tab.indexOf(self.currentEditor())
      return self.closeTab(index)

    def closeTab(self,index,askOnly = False, runCheck=True):
      editor = self.tab.widget(index)
      return self.closeEditor(editor,askOnly,runCheck)

    def currentEditor(self):
      return self.tab.currentWidget()

    def askToReloadChangedFile(self,editor):
        if editor.fileReloadPolicy() == CodeEditor.FileReloadPolicy.Always:
          editor.reloadFile()
          return
        elif editor.fileReloadPolicy() == CodeEditor.FileReloadPolicy.Never:
          return
        MyMessageBox = QMessageBox()
        MyMessageBox.setWindowTitle("Warning!")
        MyMessageBox.setText("File contents of \"%s\" have changed. Reload?" % editor.filename())
        yes = MyMessageBox.addButton("Yes",QMessageBox.YesRole)
        no = MyMessageBox.addButton("No",QMessageBox.NoRole)
        never = MyMessageBox.addButton("Never",QMessageBox.RejectRole)
        always = MyMessageBox.addButton("Always",QMessageBox.AcceptRole)
        MyMessageBox.exec_()
        choice = MyMessageBox.clickedButton()
        if choice == yes:
          editor.reloadFile()
        elif choice == no:
          editor.updateFileModificationDate()
        elif choice == never:
          editor.setFileReloadPolicy(CodeEditor.FileReloadPolicy.Never)
          editor.updateFileModificationDate()
        elif choice == always:
          editor.setFileReloadPolicy(CodeEditor.FileReloadPolicy.Always)
          editor.reloadFile()

    def onTimer(self):
      for i in range(0,self.tab.count()):
        editor = self.tab.widget(i)
        if editor.fileHasChangedOnDisk():
          currentEditor = self.tab.currentWidget()
          try:
            self.tab.setCurrentWidget(editor)
            self.askToReloadChangedFile(editor)
          finally:
            self.tab.setCurrentWidget(currentEditor)

    def sendCloseEventToParent():
        #under development
        app = QtGui.QApplication.instance()
        event = QEvent(1000)
        target = self.parent()
        print 'parent of code editor window is ', target
        app.sendEvent(target, event)

    def __init__(self,parent=None,gv = dict(),lv = dict(),newEditorCallback = None):
        self.editors = []
        self.count = 1
        self._workingDirectory = None
        self._newEditorCallback = newEditorCallback
        QWidget.__init__(self,parent)

        timer = QTimer(self)
        timer.setInterval(1000)
        self.connect(timer,SIGNAL("timeout()"),self.onTimer)
        timer.start()

        myLayout = QGridLayout()

        self.tabBar = EditorTabBar()
        self.tab = QTabWidget()
        self.tab.setTabBar(self.tabBar)
        self.tab.setMovable(True) # does not work as is because of drag and drop on tabBar

        self.tab.setTabsClosable(True)
        self.connect(self.tab,SIGNAL("tabCloseRequested(int)"),self.closeTab)
        myLayout.addWidget(self.tab,0,0)
        self.setLayout(myLayout)

        self.restoreTabState()

class LineNumbers(QPlainTextEdit):

  def __init__(self,parent,width = 50):
    QPlainTextEdit.__init__(self,parent)
    self.setFixedWidth(width)
    self.setReadOnly(True)
    MyDocument = self.document()
    MyDocument.setDefaultFont(parent.document().defaultFont())
    self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    self.setDisabled(True)

class LineTextWidget(QPlainTextEdit):

    #For QTextEdit
    #   def contentOffset(self):
    #     return QPointF(0,0)

    #For QTextEdit:
    #  def firstVisibleBlock(self):
    #   return self.document().begin()

    def appendPlainText(self,string):
      QPlainTextEdit.appendPlainText(self,string)

    #For QTextEdit:
    # def blockBoundingGeometry(self,block):
    #return self.document().documentLayout().blockBoundingRect(block)

    def append(self,string):
        self.appendPlainText(string)

    class NumberBar(QWidget):

        def __init__(self, *args):
            QWidget.__init__(self, *args)
            self.edit = None
            # This is used to update the width of the control.
            # It is the highest line that is currently visibile.
            self.highest_line = 0

        def setTextEdit(self, edit):
            self.edit = edit

        def update(self, *args):
            maxline = self.edit.document().lastBlock().blockNumber()+self.edit.document().lastBlock().lineCount()
            width = QFontMetrics(self.edit.document().defaultFont()).width(str(maxline)) + 10+10
            if self.width() != width:
                self.setFixedWidth(width)
                margins = QMargins(width,0,0,0)
                self.edit.setViewportMargins(margins)
                self.edit.viewport().setContentsMargins(margins)
            QWidget.update(self, *args)

        def mousePressEvent(self,e):
          block = self.edit.firstVisibleBlock()
          contents_y = self.edit.verticalScrollBar().value()*0
          viewport_offset = self.edit.contentOffset()-QPointF(0,contents_y)
          changed = False
          while block.isValid():
            topLeft = self.edit.blockBoundingGeometry(block).topLeft()+viewport_offset
            bottomLeft = self.edit.blockBoundingGeometry(block).bottomLeft()+viewport_offset
            if e.pos().y()>topLeft.y() and e.pos().y()<bottomLeft.y():
              if not block.next().isVisible():
                while not block.next().isVisible() and block.next().isValid():
                  block.next().setVisible(True)
                  block.setLineCount(block.layout().lineCount())
                  self.edit.document().markContentsDirty(block.next().position(),block.next().length())
                  block = block.next()
                changed = True
              elif self.isBeginningOfBlock(block):
                (startBlock,endBlock) = self.getEnclosingBlocks(block)
                self.edit.hideBlocks(startBlock,endBlock)

            block = block.next()

            if changed:
              self.edit.viewport().update()

            if bottomLeft.y() > self.edit.viewport().geometry().bottomLeft().y():
              break

        def isBeginningOfBlock(self,block):
          if block.text()[:2] == "##":
            return True
          else:
            if re.match("^\s*$",block.text()):
              return False
            matchBlock = re.search("^(\s+)",block.text())
            if matchBlock is None:
              indentation = ""
            else:
              indentation = matchBlock.group(1)
            nextBlock = block.next()
            while nextBlock.isValid() and re.match("(^\s*$)|(^\s*\#.*$)",nextBlock.text()):
              nextBlock = nextBlock.next()
            matchNextBlock = re.search("^(\s+)",nextBlock.text())
            if matchNextBlock is None:
              nextIndentation = ""
            else:
              nextIndentation = matchNextBlock.group(1)
            if len(nextIndentation) > len(indentation):
              return True

        def getEnclosingBlocks(self,block):
          if block.text()[:2] == "##":
            startBlock = block
            while block.next().isValid() and block.next().text()[:2] != "##":
              block = block.next()
              endBlock = block
            return (startBlock,endBlock)
          else:
            matchBlock = re.search("^(\s+)",block.text())
            if matchBlock is None:
              indentation = ""
            else:
              indentation = matchBlock.group(1)
            nextBlock = block.next()
            while nextBlock.next().isValid() and re.match("(^\s*$)|(^\s*\#.*$)",nextBlock.text()):
              nextBlock = nextBlock.next()
            matchNextBlock = re.search("^(\s+)",nextBlock.text())
            if matchNextBlock is None:
              nextIndentation = ""
            else:
              nextIndentation = matchNextBlock.group(1)
            startBlock = block
            endBlock = startBlock
            while block.next().isValid() and (block.next().text()[:len(nextIndentation)] == nextIndentation or re.match("(^\s*$)|(^\s*\#.*$)",block.next().text())):
              block = block.next()
              endBlock = block
            while endBlock.isValid() and re.match("(^\s*$)|(^\s*\#.*$)",endBlock.text()):
              endBlock = endBlock.previous()
            return (startBlock,endBlock)

        def paintEvent(self, event):

            contents_y = self.edit.verticalScrollBar().value()*0
            page_bottom = self.edit.viewport().height()
            font_metrics = QFontMetrics(self.edit.document().defaultFont())
            current_block = self.edit.document().findBlock(self.edit.textCursor().position())

            painter = QPainter(self)

            # Iterate over all text blocks in the document.
            block = self.edit.firstVisibleBlock()
            viewport_offset = self.edit.contentOffset()-QPointF(0,contents_y)
            line_count = block.blockNumber()+1
            painter.setFont(self.edit.document().defaultFont())

            while block.isValid():

                invisibleBlock = False

                while not block.isVisible() and block.isValid():
                  invisibleBlock = True
                  block = block.next()
                  if block == self.edit.document().lastBlock():
                    break


                # The top left position of the block in the document
                position = self.edit.blockBoundingGeometry(block).topLeft()+viewport_offset
                position2 = self.edit.blockBoundingGeometry(block).bottomLeft()+viewport_offset
                # Check if the position of the block is out side of the visible
                # area.

                line_count = block.blockNumber()+1

                additionalText = ""


                if not block.next().isVisible():
                  additionalText = "+"
                elif self.isBeginningOfBlock(block):
                  additionalText = "-"

                if position.y() > page_bottom:
                    break
                # We want the line number for the selected line to be bold.
                bold = False
                if block == current_block:
                    bold = True
                    font = painter.font()
                    font.setBold(True)
                    painter.setFont(font)

                # Draw the line number right justified at the y position of the
                # line. 3 is a magic padding number. drawText(x, y, text).
                painter.drawText(self.width() - 10 - font_metrics.width(str(line_count)) - 3, round(position.y()) + font_metrics.ascent()+font_metrics.descent()-1, str(line_count)+additionalText)

                # Remove the bold style if it was set previously.
                if bold:
                    font = painter.font()
                    font.setBold(False)
                    painter.setFont(font)


                block = block.next()

                if block.isValid():

                  topLeft = self.edit.blockBoundingGeometry(block).topLeft()+viewport_offset
                  bottomLeft = self.edit.blockBoundingGeometry(block).bottomLeft()+viewport_offset
                  if bottomLeft.y() > self.edit.viewport().geometry().bottomLeft().y():
                    break

            self.highest_line = line_count
            painter.end()

            QWidget.paintEvent(self, event)


    def __init__(self, *args):
        QPlainTextEdit.__init__(self, *args)

        self.number_bar = self.NumberBar(self)
        self.number_bar.setTextEdit(self)

        self.viewport().installEventFilter(self)

    def resizeEvent(self,e):
        self.number_bar.setFixedHeight(self.height())
        super(LineTextWidget,self).resizeEvent(e)

    def setDefaultFont(self,font):
      self.document().setDefaultFont(font)

    def eventFilter(self, object, event):
        # Update the line numbers for all events on the text edit and the viewport.
        # This is easier than connecting all necessary singals.
        if object is self.viewport():
            self.number_bar.update()
        return QPlainTextEdit.eventFilter(self,object, event)

    def paintEvent(self, event):

      QPlainTextEdit.paintEvent(self, event)

      """
      This functions paints a dash-dotted line before hidden blocks.
      """
      contents_y = self.verticalScrollBar().value()*0+1

      page_bottom = self.viewport().height()

      painter = QPainter(self.viewport())

      # Iterate over all text blocks in the document.
      block = self.firstVisibleBlock()
      viewport_offset = self.contentOffset()-QPointF(0,contents_y)
      line_count = block.blockNumber()+1
      painter.setFont(self.document().defaultFont())

      pen = QPen()
      pen.setWidth(1)
      pen.setStyle(Qt.DotLine)
      pen.setColor(QColor(0,100,0))
      painter.setBrush(QBrush(QColor(255,0,0,122)))

      painter.setPen(pen)

      while block.isValid():

          invisibleBlock = False

          while not block.isVisible() and block.isValid():
            invisibleBlock = True
            block = block.next()
            if block == self.document().lastBlock():
              break

          # The top left position of the block in the document
          topLeft = self.blockBoundingGeometry(block).topLeft()+viewport_offset
          bottomLeft = self.blockBoundingGeometry(block).bottomLeft()+viewport_offset
          # Check if the position of the block is out side of the visible
          # area.

          if not block.next().isVisible():
            rect = QRectF(bottomLeft.x(),bottomLeft.y(),self.viewport().width(),topLeft.y()-bottomLeft.y())
            # painter.drawRect(rect)
            painter.drawLine(bottomLeft.x(),bottomLeft.y(),self.viewport().width(),bottomLeft.y())
            # if bottomLeft.y() > page_bottom:
            # break

          block = block.next()

class SearchableEditor(QPlainTextEdit):

  def __init__(self,parent = None):
    self._panel = QWidget(self)
    self._layout = QBoxLayout(QBoxLayout.LeftToRight)
    self._panel.setLayout(self._layout)
    self._searchText = QLineEdit("")
    self._replaceText = QLineEdit("")
    self._replaceButton = QCheckBox("and replace by")# dv
    self._forwardButton = QPushButton("Forward")
    self._backwardButton = QPushButton("Backward")
    self._caseSensitive = QCheckBox("Case Sensitive")
    self._useRegex = QCheckBox("Regex")

    self._panel.setFocusPolicy(Qt.TabFocus)
    self._replaceText.setFocusPolicy(Qt.TabFocus)
    self._searchText.setFocusPolicy(Qt.TabFocus)

    self._layout.addWidget(QLabel("Search")) # dv
    self._layout.addWidget(self._searchText)
    self._layout.addWidget(self._replaceButton)
    self._layout.addWidget(self._replaceText)
    self._layout.addWidget(self._forwardButton)
    self._layout.addWidget(self._backwardButton)
    self._layout.addWidget(self._caseSensitive)
    self._layout.addWidget(self._useRegex) # dv
    self._layout.addWidget(QLabel("(Esc to exit search)")) # dv
    self._layout.addStretch()
    self._panel.hide()

    self.connect(self._searchText,SIGNAL("enterPressed()"),self.searchText)
    self.connect(self._forwardButton,SIGNAL("clicked()"),self.searchText)
    self.connect(self._backwardButton,SIGNAL("clicked()"),lambda: self.searchText(backward = True))

  def resizeEvent(self,e):
    self._panel.setGeometry(0,self.viewport().height(),self.viewport().width(),40)
    self.adjustMargins()

  def searchText(self,backward = False,clip = True):
    text = self._searchText.text()
    if self._useRegex.isChecked():
      if backward:
        result = self.document().find(QRegExp(text),self.textCursor().selectionStart(),QTextDocument.FindBackward)
      else:
        result = self.document().find(QRegExp(text),self.textCursor().position())
    else:
      if self._caseSensitive.isChecked():
        if backward:
          result = self.document().find(text,self.textCursor().selectionStart(),QTextDocument.FindCaseSensitively | QTextDocument.FindBackward)
        else:
          result = self.document().find(text,self.textCursor().position(),QTextDocument.FindCaseSensitively)
      else:
        if backward:
          result = self.document().find(text,self.textCursor().selectionStart(),QTextDocument.FindBackward)
        else:
          result = self.document().find(text,self.textCursor().position())
    if not result.isNull():
      self.setTextCursor(result)
      self.ensureCursorVisible()
      selection = QTextEdit.ExtraSelection
      selection.cursor = result
      selection.format = QTextCharFormat()
      selection.format.setBackground(QBrush(QColor(255,0,0,140)))
      self.selections = []
      self.selections.append(selection)
    #      self.setExtraSelections(self.selections)
      self.setFocus()
      self._searchText.setStyleSheet("background:#5F5;")
    else:
      cursor = QTextCursor(self.document())
      if backward:
        cursor.setPosition(self.document().lastBlock().position()+self.document().lastBlock().length()-1)
      else:
        cursor.setPosition(0)
      self.setTextCursor(cursor)
      self._searchText.setStyleSheet("background:#F55;")
      if clip:
        self.searchText(backward,clip = False)


  def replaceText(self):
    pass

  def showSearchBar(self):
    self._panel.show()
    self._searchText.setFocus()
    self._searchText.selectAll()
    self._searchText.setStyleSheet("")
    self.adjustMargins()

  def hideSearchBar(self):
    self._panel.hide()
    self.setFocus()
    self.adjustMargins()

  def adjustMargins(self):
    if self._panel.isVisible():
      margins = self.viewport().contentsMargins()
      margins.setBottom(40)
      self.setViewportMargins(margins)
    else:
      margins = self.viewport().contentsMargins()
      margins.setBottom(0)
      self.setViewportMargins(margins)

  def keyPressEvent(self,e):
    if (e.key() == Qt.Key_F) and (e.modifiers() & Qt.ControlModifier):
      self.showSearchBar()
    elif (e.key() == Qt.Key_Escape):
      self.hideSearchBar()
    if not self._panel.isVisible():
      e.ignore()
      return
    elif (e.key() == Qt.Key_Enter or e.key() == Qt.Key_Return):
      e.accept()
      self.searchText()
    elif e.key() == Qt.Key_Up or e.key() == Qt.Key_Down:
      e.accept()
      if e.key() == Qt.Key_Up:
        self.searchText(backward = True)
      else:
        self.searchText()
    elif e.key() == Qt.Key_Tab:
      self._panel.keyPressEvent(e)
      e.accept()
    else:
      if self._panel.isVisible():
        e.accept()
      else:
        e.ignore()

class CodeEditor(SearchableEditor,LineTextWidget):

    class FileReloadPolicy:
      Always = 0
      Never = 1
      Ask = 2

    def tabText(self):
      return self._tabText

    def setTabText(self,text):
      self._tabText = text

    def reloadFile(self):
      if self.filename() is None or not (os.path.exists(self.filename()) and os.path.isfile(self.filename())):
        raise Exception("CodeEditor.reloadFile: Unable to perform reload since no filename has been defined!")
      self.openFile(self.filename())

    def fileReloadPolicy(self):
      return self._fileReloadPolicy

    def setFileReloadPolicy(self,policy):
      self._fileReloadPolicy = policy

    def __init__(self,parent = None,lineWrap = True):
        LineTextWidget.__init__(self,parent)
        SearchableEditor.__init__(self,parent)
        self._filename = None
        self.setTabStopWidth(30)
        self._modifiedAt = None
        self._tabText = ""
        self._fileReloadPolicy = CodeEditor.FileReloadPolicy.Ask
        self._errorSelections = []
        self._blockHighlighting = True
        self._tabToolTip = '[untitled]'
        self.setAttribute(Qt.WA_DeleteOnClose,True)

        self.setStyleSheet("""
        CodeEditor
        {
          color:#000;
          background:#FFF;
          font-family:Consolas, Courier New,Courier;
          font-size:14px;
          font-weight:normal;
        }
        """)
        self.connect(self.document(), SIGNAL('modificationChanged(bool)'), self.updateUndoStatus)
        self.connect(self, SIGNAL("cursorPositionChanged()"),self.cursorPositionChanged)
        self.setLineWrap(lineWrap)
        self.setHasUnsavedModifications(False)

    def resizeEvent(self,e):
      LineTextWidget.resizeEvent(self,e)
      SearchableEditor.resizeEvent(self,e)

    def checkForText(self):
     if self.fileOpenThread.textReady == False:
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(1000)
        self.connect(self.timer,SIGNAL("timeout()"),self.checkForText)
        self.timer.start()
        return
     #self.setPlainText(self.fileOpenThread.text)

    def highlightLine(self,line):

      print "Highlighting line no %d" % line

      block = self.document().findBlockByLineNumber(line-1)

      selection = QTextEdit.ExtraSelection()

      cursor = self.textCursor()
      cursor.setPosition(block.position()+1)
      cursor.movePosition(QTextCursor.StartOfLine,QTextCursor.KeepAnchor)
      cursor.movePosition(QTextCursor.EndOfLine,QTextCursor.KeepAnchor)
      selection.cursor = cursor
      format = QTextCharFormat()
      format.setBackground(QBrush(QColor(255,255,0)))
      format.setProperty(QTextFormat.FullWidthSelection, True)

      selection.format = format

      cursor = self.textCursor()
      cursor.setPosition(block.position())

      self.setTextCursor(cursor)
      self.setErrorSelections([selection])
      self.cursorPositionChanged()
      self.ensureCursorVisible()

    def filename(self):
      return self._filename

    def setFilename(self,filename):
      self._filename = os.path.normpath(str(filename))
      if re.search(".py$",self._filename) or re.search(".pyw$",self._filename):
        self.activateHighlighter(True)
      else:
        self.activateHighlighter(False)
      if os.path.exists(self.filename()):
        self._modifiedAt = os.path.getmtime(self._filename)
      else:
        self._modifiedAt = 0

    def activateHighlighter(self,activate = True):
      if activate:
        self.highlighter = Python( self.document() )
      else:
        if hasattr(self,"highlighter"):
          del self.highlighter

    def hasUnsavedModifications(self):
      return self._hasUnsavedModifications

    def setHasUnsavedModifications(self,hasUnsavedModifications = True):
      self._hasUnsavedModifications = hasUnsavedModifications
      self.emit(SIGNAL("hasUnsavedModifications(bool)"),hasUnsavedModifications)
      self.document().setModified(hasUnsavedModifications)

    def autoIndentCurrentLine(self):
      cursor = self.textCursor()

      start = cursor.position()

      cursor.movePosition(QTextCursor.StartOfLine,QTextCursor.MoveAnchor)
      cursor.movePosition(QTextCursor.EndOfLine,QTextCursor.KeepAnchor)

      text = cursor.selection().toPlainText()

      lastLine = QTextCursor(cursor)

      lastLine.movePosition(QTextCursor.PreviousBlock,QTextCursor.MoveAnchor)
      lastLine.movePosition(QTextCursor.StartOfLine,QTextCursor.MoveAnchor)
      lastLine.movePosition(QTextCursor.EndOfLine,QTextCursor.KeepAnchor)

      lastLineText = lastLine.selection().toPlainText()

      blankLine = QRegExp("^[\t ]*$")

      indents = QRegExp(r"^[ \t]*")
      index = indents.indexIn(lastLineText)
      cursor.insertText(lastLineText[:indents.matchedLength()]+text)

      cursor.setPosition(start+indents.matchedLength())

      self.setTextCursor(cursor)

    def indentCurrentSelection(self):
      cursor = self.textCursor()

      start = cursor.selectionStart()
      end = cursor.selectionEnd()

      cursor.setPosition(start,QTextCursor.MoveAnchor)
      cursor.movePosition(QTextCursor.StartOfLine,QTextCursor.MoveAnchor)

      start = cursor.selectionStart()

      cursor.setPosition(end,QTextCursor.KeepAnchor)
      cursor.movePosition(QTextCursor.EndOfLine,QTextCursor.KeepAnchor)

      text = cursor.selection().toPlainText()

      text.replace(QRegExp(r"(\n|^)"),"\\1\t")

      cursor.insertText(text)

      cursor.setPosition(start)
      cursor.setPosition(start+len(text),QTextCursor.KeepAnchor)

      self.setTextCursor(cursor)

    def unindentCurrentSelection(self):
      cursor = self.textCursor()

      start = cursor.selectionStart()
      end = cursor.selectionEnd()

      cursor.setPosition(start,QTextCursor.MoveAnchor)

      start = cursor.selectionStart()

      cursor.movePosition(QTextCursor.StartOfLine,QTextCursor.MoveAnchor)
      cursor.setPosition(end,QTextCursor.KeepAnchor)
      cursor.movePosition(QTextCursor.EndOfLine,QTextCursor.KeepAnchor)

      text = cursor.selection().toPlainText()

      text.replace(QRegExp(r"(\n)[ \t]([^\n]+)"),"\\1\\2")
      text.replace(QRegExp(r"^[ \t]([^\n]+)"),"\\1")

      cursor.insertText(text)

      cursor.setPosition(start)
      cursor.setPosition(start+len(text),QTextCursor.KeepAnchor)

      self.setTextCursor(cursor)

    def gotoNextBlock(self):
      block = self.getCurrentBlock()
      cursor = self.textCursor()
      cursor.setPosition(block.cursor.selectionEnd())
      if not cursor.atEnd():
        cursor.setPosition(block.cursor.selectionEnd()+1)
      self.setTextCursor(cursor)

    def gotoPreviousBlock(self):
      block = self.getCurrentBlock()
      cursor = self.textCursor()
      if cursor.position() == block.cursor.selectionStart() and block.cursor.selectionStart() != 0:
        cursor.setPosition(block.cursor.selectionStart()-1)

        block = self.getCurrentBlock()
        cursor.setPosition(block.cursor.selectionStart())
      else:
        cursor.setPosition(block.cursor.selectionStart())
      self.setTextCursor(cursor)

    def getCurrentBlock(self,delimiter="\n##"):

      text = unicode(self.document().toPlainText())
      blockStart=0
      blockEnd=len(text)
      if delimiter != "":
        cursorStart = self.textCursor().anchor() #dv
        cursorStop = self.textCursor().position()
        blockStart = text.rfind(delimiter,0,max(0,cursorStart-1))+1 #dv
        blockEnd = text.find(delimiter,cursorStop)-1

        if blockStart == -1:
          blockStart = 0

        if blockStart == blockEnd:
          return None

        if blockEnd != -1:
          blockEnd+=1

      selection = QTextEdit.ExtraSelection()

      cursor = self.textCursor()

      cursor.setPosition(blockStart,QTextCursor.MoveAnchor)

      if blockEnd != -1:
        cursor.setPosition(blockEnd,QTextCursor.KeepAnchor)
      else:
        cursor.movePosition(QTextCursor.End,QTextCursor.KeepAnchor)

      selection.cursor = cursor
      return selection

    def cursorPositionChanged(self):
      if self._blockHighlighting == False:
        return

      selection = self.getCurrentBlock()

      if selection is None:
        return

      selections = []

      selections.extend(self._errorSelections)

      self._errorSelections = []

      selection = self.getCurrentBlock()

      selection.format = QTextCharFormat()
      pen = QPen()
      #      selection.format.setProperty(QTextFormat.OutlinePen,pen)
      #      selection.format.setBackground(QBrush(QColor(240,240,240)))
      #      selection.format.setProperty(QTextFormat.FullWidthSelection, True)

      selections.append(selection)

      self.setExtraSelections(selections)

    def setErrorSelections(self,selections):
      self._errorSelections = selections

    def errorSelections(self):
      return self._errorSelections

    def getCurrentCodeBlock(self,delimiter="\n##"):
        selection = self.getCurrentBlock(delimiter)
        block = self.document().findBlock(selection.cursor.selectionStart())
        n = block.blockNumber()
        return "\n"*n+unicode(selection.cursor.selection().toPlainText())+u"\n"

    def hideBlocks(self,startBlock,endBlock):
      block = startBlock.next()
      while block.isValid():
        self.document().markContentsDirty(block.position(),block.length())
        block.setVisible(False)
        block.setLineCount(0)
        if block == endBlock:
          break
        block = block.next()
      #bugfix: scrollbar value is not updated if unless calling "resize" explicitly...
      self.resize(self.size()+QSize(1,1))
      self.resize(self.size()+QSize(-1,-1))
      self.viewport().update()

    def hideCurrentBlock(self):
      block = QTextBlock()
      selection = self.getCurrentBlock()
      startBlock = self.document().findBlock(selection.cursor.selectionStart())
      endBlock = self.document().findBlock(selection.cursor.selectionEnd())
      self.hideBlocks(startBlock,endBlock)

    def contextMenuEvent(self,event):
        MyMenu = self.createStandardContextMenu()
        hideBlock = MyMenu.addAction("Hide block")
        MyMenu.addSeparator()
        if self._lineWrap:
          lineWrap = MyMenu.addAction("Disable line wrap")
        else:
          lineWrap = MyMenu.addAction("Enable line wrap")
        self.connect(lineWrap,SIGNAL("triggered()"),self.toggleLineWrap)
        self.connect(hideBlock,SIGNAL('triggered()'),self.hideCurrentBlock)
        MyMenu.exec_(self.cursor().pos())

    def toggleLineWrap(self):
      self.setLineWrap(not self._lineWrap)

    def save(self):
      if self.filename() != None:
        return self.saveAs(self.filename())
      else:
        return False

    def updateFileModificationDate(self):
      self._modifiedAt = os.path.getmtime(self.filename())+1

    def fileHasChangedOnDisk(self):
      if self.filename() != None:
        if os.path.exists(self.filename()) == False:
          return True
        elif os.path.getmtime(self.filename()) > self._modifiedAt:
            return True
      return False

    def saveAs(self,filename):
      if self.filename() is None:
        return False
      self._modifiedAt = time.time()+1
      try:
        file = open(self.filename(),'w')
        file.write(unicode(self.document().toPlainText()))
        file.close()
        self.setHasUnsavedModifications(False)
        self._modifiedAt = os.path.getmtime(self.filename())+1
        return True
      finally:
        file.close()

    def openFile(self,filename):
      if os.path.isfile(filename):
        try:
          file = open(filename,'r')
          text = file.read()
        except IOError:
          raise
        self.setPlainText(text)
        self.setFilename(filename)
        self.setHasUnsavedModifications(False)
      else:
        raise IOError("Invalid path: %s" % filename)

    def activateBlockHighlighting(self,activate = False):
      self._blockHighlighting = activate

    def updateUndoStatus(self,status):
      self.setHasUnsavedModifications(status)

    def keyPressEvent(self,e):
      SearchableEditor.keyPressEvent(self,e)
      if e.isAccepted():
        return
      if (e.key() == Qt.Key_Up or e.key() == Qt.Key_Down) and e.modifiers() & Qt.ControlModifier:
        if e.key() == Qt.Key_Up:
          self.gotoPreviousBlock()
        else:
          self.gotoNextBlock()
        e.accept()
        return
      if (e.key() == Qt.Key_Left or e.key() == Qt.Key_Right) and e.modifiers() & Qt.ControlModifier:
        if e.key() == Qt.Key_Left:
          self.unindentCurrentSelection()
        else:
          self.indentCurrentSelection()
        e.accept()
        return
      LineTextWidget.keyPressEvent(self,e)
      if e.key() == Qt.Key_Return or e.key() == Qt.Key_Enter:
        self.autoIndentCurrentLine()

    def setLineWrap(self,state):
      self._lineWrap = state
      if state:
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
      else:
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

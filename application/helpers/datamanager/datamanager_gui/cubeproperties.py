#imports

from PyQt4.QtGui import * 
from PyQt4.QtCore import *
from PyQt4.uic import *

from application.lib.instrum_classes import *             # INSTRUMENT, VISAINSTRUMENT, REMOTEINSTRUMENT, SERVERCONNECTION, DEBUGGER
from application.lib.com_classes import *                # SUBJECT, OBSERVER, DISPATCHER, THREADEDDISPATCHER
from application.ide.widgets.observerwidget import ObserverWidget     # OBSERVERWIDGET
   
#********************************************
#  CubeProperties class  
#********************************************
class CubeProperties(QWidget,ObserverWidget,Debugger):
  
    def __init__(self,parent = None,globals = {}):
        Debugger.__init__(self)
        QWidget.__init__(self,parent)
        ObserverWidget.__init__(self)
        
        self._globals = globals
        self._cube = None
        
        # GUI below
        layout = QGridLayout()
        self._name = QLineEdit()
        self._filename = QLineEdit()
        self._filename.setReadOnly(True)
        self._tags = QLineEdit()
        self._description = QTextEdit()
        self._description.setMaximumHeight (40)
        self._parameters=QTableWidget(100,2)
        self._attributes= QTableWidget(100,2)
        for widg in [self._parameters,self._attributes]:
            widg.setHorizontalHeaderLabels(["Key","Value"])
            widg.setColumnWidth (0, 100)
            widg.horizontalHeader().setStretchLastSection(True)
            for row in range(100): widg.setRowHeight (row, 20)
        self._attributes.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._parameters.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.connect(self._parameters,SIGNAL("cellChanged(int,int)"),self.parameterToDict) # use an event corresponding to manual editing editing 

        self.bindName = QLineEdit()
        self.updateBindButton = QPushButton("Update / Set")
        self.updateBindButton.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Maximum)
        self.connect(self.updateBindButton,SIGNAL("clicked()"),self.updateBind)
        
        subLayout1=QBoxLayout(QBoxLayout.LeftToRight)
        subLayout1.setSpacing(4)
        subLayout1.addWidget(QLabel("Name"))
        subLayout1.addWidget(self._name)
        subLayout1.addWidget(QLabel(" Bind to local variable:"))
        subLayout1.addWidget(self.bindName)
        subLayout1.addWidget(self.updateBindButton)
        layout.addItem(subLayout1)

        subLayout2= QGridLayout()
        subLayout2.setSpacing(4) 
        subLayout2.addWidget(QLabel("Filename"),0,0)
        subLayout2.addWidget(self._filename,0,1)
        subLayout2.addWidget(QLabel("Tags"),1,0)
        subLayout2.addWidget(self._tags,1,1)
        subLayout2.addWidget(QLabel("Description"),2,0)
        subLayout2.addWidget(self._description,2,1)
        layout.addItem(subLayout2)

        subLayout3= QGridLayout()
        subLayout3.setSpacing(4) 
        subLayout3.addWidget(QLabel("Parameters"),0,0)
        subLayout3.addWidget(QLabel("Child attributes"),0,1)
        subLayout3.addWidget(self._parameters,1,0)
        subLayout3.addWidget(self._attributes,1,1)
        layout.addItem(subLayout3)

        self.connect(self._name,SIGNAL("textEdited(QString)"),self.nameChanged)
        self.connect(self._tags,SIGNAL("textEdited(QString)"),self.tagsChanged)
        self.connect(self._description,SIGNAL("textChanged()"),self.descriptionChanged)
        self.setLayout(layout)

    def setCube(self,cube):
        self.debugPrint("in DatacubeProperties.setCube(cube) with cube = ",cube)
        if self._cube != None:
          self.debugPrint('detaching ',self._cube,' from ',self )
          self._cube.detach(self)
        self._cube = cube
        if not self._cube is None:
          self.debugPrint('attaching',self._cube,'to',self)
          self._cube.attach(self)
        self.updateProperties()

    def updateBind(self):
        name = str(self.bindName.text())
        self._globals[name] = self._cube
        
    def descriptionChanged(self):
        if self._cube is None:
          return
        if self._cube.description() != self._description.toPlainText():
          self._cube.setDescription(self._description.toPlainText())
    
    def nameChanged(self,text):
        if self._cube is None:
          return
        self._cube.setName(self._name.text())

    def tagsChanged(self,text):
        if self._cube is None:
          return
        self._cube.setTags(self._tags.text())

    def parameterToDict(self,i,j):                  
        key=self._parameters.item(i,0)                          # Types of existing parameters different from numbers are preserved and cannot change
        if key: key=str(key.text())                             # New parameters are made int if they can be interpreted as int, and float if they can be interpreted as float;
        newValue=str(self._parameters.item(i,1).text())         #   but other types are not recognized and are stored as strings
        try:
            newValue=eval(newValue)                             # first try to interpret the attribute as python code
        except:      
            pass                                                # otherwise keep the string
        self._cube.setParameter(key,newValue)
    
    def updateProperties(self):
        self.debugPrint("in DatacubeProperties.updateProperties()")
        filename=name=tags=description=''                             # clear everything
        self._parameters.clearContents ()
        self._attributes.clearContents ()
        if self._cube != None:
            filename=str(self._cube.filename());  
            name=str(self._cube.name())
            tags=str(self._cube.tags())
            description=str(self._cube.description())
            self.setEnabled(True)
            self._name.setText(name)                                  # fill name
            self._filename.setText(filename)                          # fill filename
            self._tags.setText(tags)                                  # fill tags
            self._description.setPlainText(description)               # fill description
            params=self._cube.parameters()
            i=0
            self._parameters.blockSignals(True)
            for key in params:                                        # fill parameters
                self._parameters.setItem(i,0,QTableWidgetItem(str(key)))
                self._parameters.setItem(i,1,QTableWidgetItem(str(params[key])))
                i+=1
            self._parameters.blockSignals(False)
            parent=self._cube.parent()
            if parent is not None:                                          # fill child attributes if cube has a parent
                attribs=parent.attributesOfChild(self._cube)
                print 'attributes=',attribs
                self._attributes.setEnabled(True)
                i=0
                if 'row' in attribs:
                    self._attributes.setItem(i,0,QTableWidgetItem('row'))
                    self._attributes.setItem(i,1,QTableWidgetItem(str(attribs['row'])))
                    del attribs['row']
                    i+=1
                for key in attribs:
                    self._attributes.setItem(i,0,QTableWidgetItem(str(key)))
                    self._attributes.setItem(i,1,QTableWidgetItem(str(attribs[key])))
                    i+=1
            else:
                self._attributes.setEnabled(False)
        else: self.setEnabled(False)  
        
    def updatedGui(self,subject = None,property = None,value = None):
        self.debugPrint("in DatacubeProperties.updatedGui with property ",property,' and value=',value)
        if subject == self._cube and property == "metaUpdated":
            self.updateProperties()
      

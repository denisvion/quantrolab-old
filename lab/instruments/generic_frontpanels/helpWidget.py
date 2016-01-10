import sys

sys.path.append('.')
sys.path.append('../')

from PyQt4.QtGui import * 
from PyQt4.QtCore import *
from inspect import *

#This is a generic widget for SCPI dialog with an instrument.
class HelpWidget(QWidget):

  #Initializes the widget.
  def __init__(self,parentFrontPanel=None):
    QWidget.__init__(self)

    self.instrument=parentFrontPanel.instrument
    
    generalButton=QPushButton('Instrument class')
    self.connect(generalButton,SIGNAL('clicked()'),self.myReadGeneral)
    helpButton=QPushButton('Help method')
    self.connect(helpButton,SIGNAL('clicked()'),self.myMethodHelp)
    clearButton=QPushButton('Clear')
    self.connect(clearButton,SIGNAL('clicked()'),self.myClear)
    self.generalHelp=QTextEdit()
    self.generalHelp.setAcceptRichText(True)
    self.generalHelp.setReadOnly(True)
    self.methodHelp=QTextEdit()
    self.methodHelp.setAcceptRichText(True)
    self.methodHelp.setReadOnly(True)

    layout = QGridLayout()
    layout.addWidget(generalButton,0,0)
    layout.addWidget(self.generalHelp,0,1)
    layout.addWidget(helpButton,1,0)
    layout.addWidget(clearButton,2,0)
    layout.addWidget(self.methodHelp,1,1,2,1)
    self.setLayout(layout)

    self.myReadGeneral()

  def myReadGeneral(self):
    ins=self.instrument
    clas=str(ins.__class__)
    if clas is None:  clas='None'
    mod=str(getmodule(ins))
    doc=ins.__doc__
    if doc is None : doc='has no documentation string.'
    attributes=dir(ins)
    methods=[attribute for attribute in attributes if ismethod(getattr(ins,attribute))]
    properties=list(set(attributes)-set(methods))
    publicMethods=[method for method in methods if method[0] != '_']
    publicProperties=[propert for propert in properties if propert[0] != '_']
    self.generalHelp.clear()
    helpString = clas + ' defined in \n'+ mod + ':\n' + doc +'\n'
    helpString+='***********************\nPublic properties\n***********************\n'
    for propert in publicProperties: helpString+= propert+'\n'
    helpString+='***********************\nPublic methods\n***********************\n'
    for method in publicMethods: helpString+= method+'\n'
    self.generalHelp.append(QString(helpString))

  def myMethodHelp(self):
    ins=self.instrument
    selection=str(self.generalHelp.textCursor().selectedText())
    if hasattr(ins,selection):
      attr=getattr(ins,selection)
      if ismethod(attr):
        helpString=attr.__doc__
        if helpString:  self.methodHelp.append(QString(helpString))
        else: self.methodHelp.append(QString('Selected method has no documentation string.'))
      else: self.methodHelp.append(QString('Selection is not a method name.'))

  def myClear(self):
    self.methodHelp.clear()


 
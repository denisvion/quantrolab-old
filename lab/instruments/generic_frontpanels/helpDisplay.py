import sys

sys.path.append('.')
sys.path.append('../')

from PyQt4.QtGui import * 
from PyQt4.QtCore import *

#This is a generic widget for SCPI dialog with an instrument.
class Scpichat(QWidget):

  #Initializes the widget.
  def __init__(self,parentFrontPanel=None):
    QWidget.__init__(self)

    self.instrument=parentFrontPanel.instrument
    
    readButton=QPushButton('Read')
    self.connect(readButton,SIGNAL('clicked()'),self.myRead)
    writeButton=QPushButton('Write')
    self.connect(writeButton,SIGNAL('clicked()'),self.myWrite)
    askButton=QPushButton('Ask')
    self.connect(askButton,SIGNAL('clicked()'),self.myAsk)
    clearButton=QPushButton('Clear')
    self.connect(clearButton,SIGNAL('clicked()'),lambda :self.log.clear())
    self.messageOut=QLineEdit()
    self.messageOut.setText(QString('*IDN?'))
    self.log=QTextEdit()
    self.log.setAcceptRichText(True)
    self.log.setReadOnly(True)

    layout = QGridLayout()
    layout.addWidget(askButton,0,0,2,1,Qt.AlignTop)
    layout.addWidget(writeButton,0,1)
    layout.addWidget(self.messageOut,0,2)
    layout.addWidget(readButton,1,1,1,1,Qt.AlignTop)
    layout.addWidget(self.log,1,2,2,1)
    layout.addWidget(clearButton,2,1,1,1,Qt.AlignTop)
    self.setLayout(layout)

  def myWrite(self):
  	commandQString=self.messageOut.text()
  	self.instrument.write(str(commandQString))
  	self.log.setTextColor(QColor('black'))
  	self.log.append(commandQString)
  	self.messageOut.clear()

  def myRead(self):
  	str1=self.instrument.read()
  	self.log.setTextColor(QColor('Red'))
  	self.log.append(QString(str1))

  def myAsk(self):
  	self.myWrite()
  	self.myRead()
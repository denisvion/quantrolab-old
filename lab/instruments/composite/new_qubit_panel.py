import sys

from application.lib.instrum_classes import *
import string

import re
import struct

import os
import os.path

from numpy import *
from numpy.random import *

from application.ide.mpl.canvas import MatplotlibCanvas as Canvas
from application.lib.instrum_panel import FrontPanel

class GenericObject(object):
  pass
class Panel(FrontPanel):
  
  """
  The Qubit frontpanel.
  """
  
  def __init__(self,instrument,parent = None):
    FrontPanel.__init__(self,instrument,parent)

    self.layout = QGridLayout()
   
    self.spectro=GenericObject()
    self.spectro.Layout=QBoxLayout(QBoxLayout.LeftToRight)
    self.spectro.Layout.addWidget(QLabel("<b>Spectro: </b>"))
    self.spectro.Layout.addWidget(QLabel("Frequency Start:"))
    self.spectro.startEdit=QLineEdit("5.")
    self.spectro.Layout.addWidget(self.spectro.startEdit)
    self.spectro.Layout.addWidget(QLabel(" Stop:"))
    self.spectro.stopEdit=QLineEdit("10.")
    self.spectro.Layout.addWidget(self.spectro.stopEdit)
    self.spectro.Layout.addWidget(QLabel("Step:"))
    self.spectro.stepEdit=QLineEdit("0.005")
    self.spectro.Layout.addWidget(self.spectro.stepEdit)
    self.spectro.Layout.addWidget(QLabel("Power:"))
    self.spectro.powerEdit=QLineEdit("-5.")
    self.spectro.Layout.addWidget(self.spectro.powerEdit)
    self.spectro.start=QPushButton("Measure")
    self.spectro.Layout.addWidget(self.spectro.start)
    
    self.layout.addLayout(self.spectro.Layout,1,1)   
    
    self.rabi=GenericObject()
    self.rabi.Layout=QBoxLayout(QBoxLayout.LeftToRight)
    self.rabi.Layout.addWidget(QLabel("<b>Rabi: </b>"))
    self.rabi.Layout.addWidget(QLabel("Duration Start:"))
    self.rabi.startEdit=QLineEdit("0.")
    self.rabi.Layout.addWidget(self.rabi.startEdit)
    self.rabi.Layout.addWidget(QLabel(" Stop:"))
    self.rabi.stopEdit=QLineEdit("100.")
    self.rabi.Layout.addWidget(self.rabi.stopEdit)
    self.rabi.Layout.addWidget(QLabel("Step:"))
    self.rabi.stepEdit=QLineEdit("1.")
    self.rabi.Layout.addWidget(self.rabi.stepEdit)
    self.rabi.Layout.addWidget(QLabel("Power:"))
    self.rabi.powerEdit=QLineEdit("-5.")
    self.rabi.Layout.addWidget(self.rabi.powerEdit)
    self.rabi.start=QPushButton("Measure")
    self.rabi.Layout.addWidget(self.rabi.start)
    self.layout.addLayout(self.rabi.Layout,2,1)   
     
    self.t1=GenericObject()
    self.t1.Layout=QBoxLayout(QBoxLayout.LeftToRight)
    self.t1.Layout.addWidget(QLabel("<b>T1: </b>"))
    self.t1.Layout.addWidget(QLabel("Delay Start:"))
    self.t1.startEdit=QLineEdit("0.")
    self.t1.Layout.addWidget(self.t1.startEdit)
    self.t1.Layout.addWidget(QLabel(" Stop:"))
    self.t1.stopEdit=QLineEdit("1000.")
    self.t1.Layout.addWidget(self.t1.stopEdit)
    self.t1.Layout.addWidget(QLabel("Step:"))
    self.t1.stepEdit=QLineEdit("2.")
    self.t1.Layout.addWidget(self.t1.stepEdit)
    self.t1.accurateEdit = QCheckBox("Accurate ?")
    self.t1.Layout.addWidget(self.t1.accurateEdit)
    self.t1.start=QPushButton("Measure")
    self.t1.Layout.addWidget(self.t1.start)
    self.layout.addLayout(self.t1.Layout,3,1)
    
    
    


    self.sCurves=GenericObject()
    self.sCurves.Layout=QBoxLayout(QBoxLayout.LeftToRight)
    self.sCurves.Layout.addWidget(QLabel("<b>sCurves: </b>"))
    self.sCurves.start=QPushButton("Measure")
    self.sCurves.Layout.addWidget(self.sCurves.start)
    self.layout.addLayout(self.sCurves.Layout,4,1)

    self.stopLayout=QBoxLayout(QBoxLayout.LeftToRight)
    self.stopButton=QPushButton("Stop")
    self.stopLayout.addWidget(self.stopButton)
    self.layout.addLayout(self.stopLayout,4,1)
      
    self.qw.setLayout(self.layout)
    
    self.connect(self.spectro.start,SIGNAL("clicked()"),self.measureSpectro)
    self.connect(self.rabi.start,SIGNAL("clicked()"),self.measureRabi)
    self.connect(self.t1.start,SIGNAL("clicked()"),self.measuret1)
    self.connect(self.sCurves.start,SIGNAL("clicked()"),self.measureSCurves)
    self.connect(self.stopButton,SIGNAL("clicked()"),self.stop)
    
    
    
    
    
    
    
    
  def measureSpectro(self):
    self.instrument.dispatch("measureSpectroscopy",float(self.spectro.startEdit.text()),float(self.spectro.stopEdit.text()),float(self.spectro.stepEdit.text()),float(self.spectro.powerEdit.text()))

  def measureRabi(self):
    self.instrument.dispatch("measureRabi",float(self.rabi.startEdit.text()),float(self.rabi.stopEdit.text()),float(self.rabi.stepEdit.text()),float(self.rabi.powerEdit.text()))

  def measuret1(self):
    self.instrument.dispatch("measureT1",float(self.t1.startEdit.text()),float(self.t1.stopEdit.text()),float(self.t1.stepEdit.text()),self.t1.accurateEdit.isChecked())

  def measureSCurves(self):
    self.instrument.dispatch("measureSCurves")
    
  def stop(self):
    self.instrument.terminate()

    
    
    
    
    
    
    
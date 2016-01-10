import sys,string,time
from datetime import *

sys.path.append('.')
sys.path.append('../')

from application.lib.instrum_classes import *
from application.ide.mpl.canvas import *
from application.lib.instrum_panel import FrontPanel
from frontpanels.scpichat import *
from frontpanels.helpWidget import *

# This is the FSP FrontPanel.
# As a frontpanel, it is also an ObserverWidget (so an Observer)
class Panel(FrontPanel):

  #Initializes the front panel.
  def __init__(self,instrument,parent=None):
    super(Panel,self).__init__(instrument,parent)

    self._reference = None
    self._traces = []
    self._workingDirectory = ''
    self.fileDialog = QFileDialog()
    
    # Stimulus and measurement control
    readButton = QPushButton("Read")
    self.connect(readButton,SIGNAL("clicked()"),self.requestSetup)
    
    labels=['Center freq.(GHz)','Span (GHz)','Start freq. (GHz)','Stop freq. (GHz)','Res. BW (Hz)','Points','Sweep counts']
    spinBoxNames=['centerInGHz','spanInGHz','startInGHz','stopInGHz','resBWInHz','NumOfPoints','sweepCount']
    types=['double','double','double','double','double','int','int']
    setNames= ['setCenterInGHz','setSpanInGHz','setStartInGHz','setStopInGHz','setResBWInHz','setNumOfPoints','setSweepCounts']
    getNames= ['getCenterInGHz','getSpanInGHz','getStartInGHz','getStopInGHz','getResBWInHz','getNumOfPoints','getSweepCounts']
    maxima=[30,30,30,30,10000000,32000,32768]
    decimals=[9,9,9,9,0,0,0]
    for spinBoxName, type0, setName,getName,maximum,decimal in zip(spinBoxNames,types,setNames,getNames,maxima,decimals):
      if type0 == 'double' :
        setattr(self,spinBoxName,QDoubleSpinBox())
      else:
        setattr(self,spinBoxName,QSpinBox())  
      spinBox=getattr(self,spinBoxName)
      if type0 == 'double' :
        spinBox.setDecimals(decimal)
      spinBox.setMaximum(maximum)
      def connectInNewScope(spinBox0,setName0,getName0):
        self.connect(spinBox0,SIGNAL('valueChanged('+type0+')'),lambda: self.requestSetParam(setName0,getName0,spinBox0))
      connectInNewScope(spinBox,setName,getName)

    # Graphs
    self.cvsFreq = MatplotlibCanvas(self, width=5, height=4, dpi=100)
    self.cvsFreq.axes.set_visible(True)
    self.cvsTime = MatplotlibCanvas(self, width=5, height=4, dpi=100)
    self.cvsTime.axes.set_visible(True)
    
    # Get, show and save data
    updateButton = QPushButton("Get trace")
    self.connect(updateButton,SIGNAL("clicked()"),self.requestAcquire)
    self.traceNum=QSpinBox()
    self.traceNum.setMinimum(1)
    self.traceNum.setMaximum(10)
    self.traceNum.setValue(1)
    self.traceNum.setWrapping(True)
    self.traceNum.setMinimumWidth(50)

    self.traces = QTableWidget()
    self.traces.horizontalHeader().setStretchLastSection(True)
    self.traces.setColumnCount(3)
    self.traces.setColumnWidth(1,300)
    self.traces.setHorizontalHeaderItem(0,QTableWidgetItem("filename"))
    dw = QTableWidgetItem("description")
    dw.setSizeHint(QSize(400,30))
    self.traces.setHorizontalHeaderItem(1,dw)
    self.traces.setHorizontalHeaderItem(2,QTableWidgetItem("options"))

    self.connect(self.traces,SIGNAL("cellChanged(int,int)"),self.updateTraceProperties)

    clearButton = QPushButton("Clear traces")
    self.connect(clearButton,SIGNAL("clicked()"),self.clearTraces)

    saveButton = QPushButton("Save all")
    self.connect(saveButton,SIGNAL("clicked()"),self.saveTraces)

    saveFigButton = QPushButton("Save fig.")
    self.connect(saveFigButton,SIGNAL("clicked()"),self.savePlot)

    clearRefButton = QPushButton("Clear ref")
    self.connect(clearRefButton,SIGNAL("clicked()"),lambda : self.makeReference(None))

    hideAllButton = QPushButton("Hide all")
    self.connect(hideAllButton,SIGNAL("clicked()"),self.hideAll)
    
    self.waitFullSweepButton = QCheckBox("New sweep",checked=False)
    
    self.showLegend = QCheckBox("Legend",checked=False)
    self.connect(self.showLegend,SIGNAL("stateChanged(int)"),self.plotTraces)
    
    self.tabs = QTabWidget()
    self.tabs.addTab(self.cvsFreq,' mag ( freq ) ')
    self.tabs.addTab(self.cvsTime,' mag ( time ) ')
    
    # Place interface elements
    subGrid1 = QGridLayout()
    subGrid1.setSpacing(10)
    subGrid1.addWidget(readButton,0,0)
    for label,spinBoxName in zip(labels,spinBoxNames ):
      col=subGrid1.columnCount()
      subGrid1.addWidget(QLabel(label),0,col)
      subGrid1.addWidget(getattr(self,spinBoxName),1,col)

    subGrid2 = QGridLayout()
    subGrid2.setSpacing(10)
    subGrid2.addWidget(updateButton,0,subGrid2.columnCount())
    subGrid2.addWidget(self.traceNum,0,subGrid2.columnCount())
    subGrid2.addWidget(self.waitFullSweepButton,0,subGrid2.columnCount())
    subGrid2.addWidget(self.showLegend,0,subGrid2.columnCount())
    subGrid2.addWidget(clearButton,0,subGrid2.columnCount())
    subGrid2.addWidget(saveButton,0,subGrid2.columnCount())
    subGrid2.addWidget(saveFigButton,0,subGrid2.columnCount())
    subGrid2.addWidget(clearRefButton,0,subGrid2.columnCount())
    subGrid2.addWidget(hideAllButton,0,subGrid2.columnCount())

    # Window setup
    self.setWindowTitle("FSP or FSV Spectrum Analyzer Frontpanel")
    self.grid = QGridLayout()
    self.grid.setSpacing(10)
    self.grid.addItem(subGrid1,self.grid.rowCount(),0)
    self.grid.addWidget(self.tabs,self.grid.rowCount(),0)
    self.grid.addItem(subGrid2,self.grid.rowCount(),0)
    self.grid.addWidget(self.traces,self.grid.rowCount(),0)

    self.qw.setLayout(self.grid)
    self.setMinimumWidth(640)
    self.setMinimumHeight(500)
    
    self.plotTraces()

    try:
      self.requestSetup()
    except:
      print 'Error occured when trying to read fsp parameters.'

  def updateTraceList(self):
    """
    Private method for updating the list of traces 
    """
    self.traces.setRowCount(len(self._traces))
    for i in range(0,len(self._traces)):
      self.traces.setItem(i,0,QTableWidgetItem(self._traces[i].name()))
      self.traces.setItem(i,1,QTableWidgetItem(self._traces[i].description()))

      myLayout = QGridLayout()
      myLabel = QLabel("")
      myCheckBox = QCheckBox("show")
      myCheckBox.setCheckState(Qt.Checked if self.visibility(i) == True else Qt.Unchecked)
      myLayout.addWidget(myCheckBox,0,0)
      myLabel.setFixedHeight(50)
      myLabel.setLayout(myLayout)
      deleteButton = QPushButton("Delete")
      saveButton = QPushButton("Save")
      refButton = QPushButton("Make ref")
      dataMangerButton = QPushButton("->DataMan.")
      myLayout.addWidget(deleteButton,0,1)
      myLayout.addWidget(saveButton,0,2)
      myLayout.addWidget(refButton,0,3)
      myLayout.addWidget(dataMangerButton,0,4)
      
      #Programming with "lambda" rocks :)
      self.connect(myCheckBox,SIGNAL("stateChanged(int)"),lambda state, x = i: self.setVisibility(x,state))
      self.connect(deleteButton,SIGNAL("clicked()"),lambda x = i: self.deleteTrace(x))
      self.connect(saveButton,SIGNAL("clicked()"),lambda x = i: self.saveTrace(x))
      self.connect(refButton,SIGNAL("clicked()"),lambda x = i: self.makeReference(x))
      self.connect(dataMangerButton,SIGNAL("clicked()"),lambda x = i: self.sendToDataManager(x))
      
      self.traces.setCellWidget(i,2,myLabel)
      self.traces.setRowHeight(i,50)        
  
  # Plots the given traces.
  def graph(self,cvs,xLabel,legends,plots):
    """
    Plots all the traces and the legend
    """
    cvs.axes.clear()
    cvs.axes.plot(*list(plots))
    cvs.axes.grid(True)
    cvs.axes.set_ylabel('amplitude [dB]')
    cvs.axes.set_xlabel(xLabel)
    if self.showLegend.isChecked(): cvs.axes.legend(legends,'lower left')
    cvs.axes.set_visible(True)

  def plotTraces(self):
    if len(self._traces) == 0:
      self.cvsFreq.axes.set_visible(False)
      self.cvsTime.axes.set_visible(False)
      self.cvsFreq.draw()
      self.cvsTime.draw()
      return
    plotsFreq = []
    plotsTime = []
    legendsFreq = []
    legendsTime = []
    for x in range(0,len(self._traces)):
      if self.visibility(x):
        mag=self._traces[x]['mag']
        if self._reference != None and self._reference != self._traces[x]:
          mag-=self._reference['mag']
        if 'freq' in self._traces[x].names():
          freq=map(lambda x : x / 1e9 ,self._traces[x]['freq'])
          plotsFreq.extend([freq,mag])
          legendsFreq.append(self._traces[x].name())
        elif 'time' in self._traces[x].names():
          tim=self._traces[x]['time']
          plotsTime.extend([tim,mag])
          legendsTime.append(self._traces[x].name())
    if len(plotsFreq) == 0:
      self.cvsFreq.axes.set_visible(False)
    else:
      self.graph(self.cvsFreq,'freq',legendsFreq,plotsFreq)
    if len(plotsTime) == 0:
      self.cvsTime.axes.set_visible(False)
    else:
      self.graph(self.cvsTime,'time',legendsTime,plotsTime)
    self.cvsFreq.draw()
    self.cvsTime.draw()

  # Below are the two calls to the instrument for getting parameters and traces.
  # The instrument.dispatch(methodName) method is used and send a notification with property=methodname and value=data
  # The updatedGui function takes then the necessary actions.

  def requestSetup(self):
    self.instrument.dispatch('getSetup') # change DV

  def requestSetParam(self,setName,getName,widget):
    self.debugPrint('in requestSetParam')
    self.setTextColor(widget,'red')
    newVal=widget.value()
    oldVal=getattr(self.instrument,getName)()
    if oldVal != newVal: #Here is a dirty trick to avoid seting again the same value because of the valueChanged event. This is the price to pay for using a QSpinBox as an output and an automatic input when the value changes
      self.instrument.dispatch(setName,newVal)
      self.requestSetup()
    self.setTextColor(widget,'black')

  def updatedGui(self,subject,property = None,value = None,message = None):
    """
    Update handler. Gets invoked whenever the instrument sends notifications.
    """
    self.debugPrint('in updatedGui with subject=',subject,', property=',property,', value=',value)
    if subject == self.instrument:
      if property == 'getTrace':
        #print 'Trace data arrived!'
        if not value in self._traces:
          self._traces.append(value)
          self.plotTraces()
          self.updateTraceList()
      elif property == 'getSetup':
        for key in value:
          if hasattr(self,key): getattr(self,key).setValue(value[key]) # use the fact that spin boxes have the same names as the keys in the returned dictionary

  #Request a trace from the instrument.
  def requestAcquire(self,trace=1):
    waitFullSweep=bool(self.waitFullSweepButton.isChecked())
    trace=self.traceNum.value()
    self.instrument.dispatch("getTrace",trace=trace,waitFullSweep=waitFullSweep,cubeOut=True)

  def makeReference(self,i):
    if i is None:
      self._reference = None
    else:
      self._reference = self._traces[i]
    self.plotTraces()   

  def sendToDataManager(self,i):
    self._traces[i].toDataManager()
    
  #Deletes a given trace.
  def deleteTrace(self,i):
    self._traces.pop(i)
    self.plotTraces()
    self.updateTraceList()
    
  #Save the plot with all the traces to a file (PDF, PNG, EPS, ...)    
  def savePlot(self):
    plot = self.tabs.currentWidget()
    if plot.axes.get_visible() == False:
        return
    if self._workingDirectory != '':
        self.fileDialog.setDirectory(self._workingDirectory)
    self.fileDialog.setAcceptMode(1)
    self.fileDialog.setNameFilter("Image files (*.png *.eps *.jpg)");
    self.fileDialog.setDefaultSuffix('eps')
    filename = str(self.fileDialog.getSaveFileName())
    if len(filename) > 0:
        self._workingDirectory = str(self.fileDialog.directory().dirName())
        plot.figure.savefig(filename)

  def setVisibility(self,i,state):
    self._traces[i].parameters()["visible"] = state
    self.plotTraces()
    
  def visibility(self,i):
    if not "visible" in self._traces[i].parameters():
      self._traces[i].parameters()["visible"] = True
    return bool(self._traces[i].parameters()["visible"])
    
  def toggleVisibility(self,i):
    self.setVisibility(i,not self.visibility(i))
        
  #Updates the properties of a trace according to the values the user entered in the table.
  def updateTraceProperties(self,i,j):
      return
      if j == 0:
        #We change the name of the trace...
        self._traces[i].setName(str(self.traces.item(i,j).text().toAscii()))
        self.plotTraces()
      if j == 1:
        #We change the name of the trace...
        self._traces[i].setDescription(str(self.traces.item(i,j).text().toAscii()))
        self.plotTraces()

  #Deletes all traces that have been taken so far.
  def clearTraces(self):
      self._traces = []
      self.plotTraces()
      self.updateTraceList()

  #Write a given trace to a file.
  def writeTrace(self,filename,trace):
    trace.savetxt(filename)

  #Saves all the traces to a directory chosen by the user. The individual traces will be named according to the filenames in the first column of the table.
  #The first column of each data file will contain the description entered by the user in the second column of the table.
  def saveTraces(self):
      self.fileDialog.setAcceptMode(1)
      if self._workingDirectory != '':
          self.fileDialog.setDirectory(self._workingDirectory)
      valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
      dirname = str(self.fileDialog.getExistingDirectory())
      if len(dirname) > 0:
         self._workingDirectory = dirname
         for x in range(0,len(self._traces)):
            trace = self._traces[x]
            sanitized_filename = ''.join(c for c in trace.name() if c in valid_chars)
            print "Storing trace 1 in file %s" % sanitized_filename
            self.writeTrace(dirname + '/'+ sanitized_filename+ '.dat',trace)

  #Saves one single trace to a file.
  def saveTrace(self,x):
      if self._workingDirectory != '':
          self.fileDialog.setDirectory(self._workingDirectory)
      self.fileDialog.setAcceptMode(1)
      filename = str(self.fileDialog.getSaveFileName())
      if len(filename) > 0:
          self._workingDirectory = self.fileDialog.directory().dirName()
          self.writeTrace(filename,self._traces[x])

  def hideAll(self):
    for i in range(0,len(self._traces)):
      self.setVisibility(i,False)

  def setTextColor(self,mySpinBox,color):
    palette = QPalette()
    palette.setColor(palette.Text,QColor(color)) 
    mySpinBox.setPalette(palette)

# Imports
import sys,time,datetime,re,instruments,copy
import numpy as np
from PyQt4 import QtGui

sys.path.append('.')
sys.path.append('../')

from application.lib.instrum_classes import *
from application.lib.instrum_panel import FrontPanel
from application.ide.mpl.canvas import *
from application.lib.datacube import Datacube

# HOW TO MAKE A BACKEND INSTRUMENT AND ITS FRONTPANEL COMMUNICATE
# Several strategies are possible.
#    I) Synchronous programming:
#       - Use the syntax result=instrument.method(*args,**kwargs)  with instrument.method a method of the backend instrument.
#       You get the result in the frontpanel, which stays pending until it gets the result.
#    II) Asynchronous programming without callback for local instrument only:
#       - Use the syntax instrument.method(*args,**kwargs) without getting a result;
#       - Have explicitely a self.notify('methodName',value,message) in instrument.method if you want to be aware that an operation is completed;
#       - Have an updatedGui(subject,property,value,message) in the front panel to react to the notification with subject='intrument', property='method'. 
#    III) Asynchronous programming without callback for both local or remote instrument:
#       - Use the syntax instrument.dispatch('method',*args,**kwargs)
#       - You will receive notifications from the dispatcher (or ThreadedDispatcher for remote instrument)
#       - Have an updatedGui(subject,property, value, message) in this front panel to react to the notification with subject='intrument', property=methodName 
#    IV) Asynchronous programming with callback for both local or remote instrument:
#       - Use the syntax instrument.dispatchCB('method','callback',*args,**kwargs)
#       doc to be continued...
#       

class Panel(FrontPanel):
    """
    The frontpanel class for the Acqiris instrument controlling a Acqiris digitizer board
    
    Authors (add your name here if not present):
      - Andreas Dewes, andreas.dewes@gmail.com (creator)
      - Denis Vion, denis.vion@cea.fr (updates)
      - Vivien Schmitt, vovios@gmail.com (updates)
    Description:
      This frontpanel is a GUI allowing the user to see and set the acqiris parameters, to control the board via the acqiris instrument, and display the aquired data.
    """
    # instantiation

    def __init__(self,instrument,parent=None):
      """
      Initializes the frontpanel
      """    
      super(Panel,self).__init__(instrument,parent)
      self.setWindowTitle('Acqiris Control Panel:')
      self._workingDirectory = ''
      self.fileDialog = QFileDialog()
      self.lastWave=dict()     # create the lastWave dictionary to avoid errors before very first transfer
      self.lastWave['identifier']=-1
      self.colors=['b','g','r','c','m','k']
      
      # access directly to instruments constants to adapt the gui definition to the number of channels
      self.constants=self.instrument.constants() 
      self.nbrOfChannels=self.constants['nbrOfChannels']
      
      #Lists containing the parameters controls of the different channels.
      self.couplings = list()
      self.fullScales = list()
      self.offsets = list()
      self.bandwidths = list()
      self.activated = list()
           
      #The grid layout channelGrid that contains the parameters for the different channels.
      self.channelGrid = QGridLayout()
      self.channelGrid.setVerticalSpacing(2)
      self.channelGrid.setHorizontalSpacing(10)
      
      self.chCombineGUI()
      self.channelGrid.addWidget(QLabel('Channel config:'),0,0)
      self.channelGrid.addWidget(self.chCombine,0,1,1,max(1,self.nbrOfChannels-1))
      self.colors=['blue','green','red','cyan','blue','green','red','cyan']
      for i in range(0,self.nbrOfChannels):
        self.channelParamGUI(i)
      
      #The grid layout paramsGrid that contains all the global parameters of the card.
      self.paramsGrid = QGridLayout()
      self.paramsGrid.setVerticalSpacing(2)
      self.paramsGrid.setHorizontalSpacing(10)
      myWidth=90
    
      #trigger parameters
      self.triggerGUI(myWidth)
      self.paramsGrid.addWidget(QLabel('Trigger source'),0,0)
      self.paramsGrid.addWidget(self.trigSource,1,0)    
      self.paramsGrid.addWidget(QLabel('Trigger Coupling'),2,0)
      self.paramsGrid.addWidget(self.trigCoupling,3,0)
      self.paramsGrid.addWidget(QLabel('Trigger event'),4,0)
      self.paramsGrid.addWidget(self.trigSlope,5,0)
      self.paramsGrid.addWidget(QLabel('Trigger levels (mV)'),6,0)
      self.paramsGrid.addItem(self.triggerLevelGrid,7,0)
      self.paramsGrid.addWidget(QLabel('Trigger delay (s)'),8,0)
      self.paramsGrid.addWidget(self.trigDelay,9,0)
      
      # horizontal parameters
      self.horizParamsGUI(myWidth)
      self.paramsGrid.addWidget(QLabel('Sampling time (s)'),0,1)
      self.paramsGrid.addWidget(self.sampleInterval,1,1)
      self.paramsGrid.addWidget(QLabel('Samples/segment'),2,1)
      self.paramsGrid.addWidget(self.numberOfPoints,3,1)
      self.paramsGrid.addWidget(QLabel('Segments/bank'),4,1)
      self.paramsGrid.addWidget(self.numberOfSegments,5,1)
      self.paramsGrid.addWidget(QLabel('Memory bank(s)'),6,1)
      self.paramsGrid.addWidget(self.numberOfBanks,7,1)  
      self.paramsGrid.addWidget(QLabel('Acqs or banks/acq'),8,1)
      self.paramsGrid.addWidget(self.nLoops,9,1)
      
      # clocking and memory parameters
      self.clockMemGUI(myWidth)
      self.paramsGrid.addWidget(QLabel('Clocking'),0,2)
      self.paramsGrid.addWidget(self.clock,1,2)
      self.paramsGrid.addWidget(QLabel('Memory used'),2,2)
      self.paramsGrid.addWidget(self.memType,3,2)
      self.paramsGrid.addWidget(QLabel('Config mode'),4,2)
      self.paramsGrid.addWidget(self.configMode,5,2)    

      #Several plots in a QTabWidget.
      self.plotTabGUI()
      self.plotTabs = QTabWidget()
      self.plotTabs.setMinimumHeight(350)
      self.plotTabs.addTab(self.timestampTab,'TimeStamps')
      self.plotTabs.addTab(self.sequenceTab,'Sequences')
      self.plotTabs.addTab(self.segmentTab,'Segments')
      self.plotTabs.addTab(self.averageTab,'Average')
      #if self.mathModule:
      self.plotTabs.addTab(self.trendTab,'Segment property trend')
      self.plotTabs.setCurrentIndex(2)
      for i in range(0,5):
        self.plotTabs.setTabEnabled (i,False)
      
      self.connect(self.plotTabs,SIGNAL('currentChanged(int)'),self.updatePlotTabs)
      
      #Some buttons and checkboxes, their grid, and corresponding functions
      self.buttonGrid1 = QBoxLayout(QBoxLayout.LeftToRight)
      self.buttonGrid2 = QBoxLayout(QBoxLayout.LeftToRight)
      self.ButtonGUI()

      #The grid layout for delivering messages: messageGrid.
      self.MessageGUI()
      self._displayMessages=True            # allow message display (which can slow down the scope)

      #The grid layout of the whole frontpanel:
      self.grid = QGridLayout()
      self.grid.setHorizontalSpacing(20)
      
      self.grid.addItem(self.buttonGrid1,0,0,1,2)
      self.grid.addItem(self.channelGrid,1,0)
      self.grid.addWidget(self.plotTabs,2,0,1,2)
      self.grid.addItem(self.paramsGrid,1,1)        
      self.grid.addItem(self.buttonGrid2,3,0,1,2)
      self.grid.addItem(self.messageGrid,4,0,1,2)

      self.qw.setLayout(self.grid)          # now the interface does exist
      
      self.requestParameters()              # Requests the board acquisition parameters
      self.requestTemperature()             # and temperature
      self._waitingForData = False          # instrument is ready

      self._timerRun = QTimer(self)         # timer for continuous run mode
      self.connect(self._timerRun,SIGNAL('timeout()'),self.onTimerRun)

    def closeEvent(self,e):
      self._timerRun.stop()
      e.accept()

    def restoreState(self):
      self.debugPrint('in acqiris.restoreState()')
      filename = QFileDialog.getOpenFileName(filter = "instrumentState (*.inst)")
      if filename != "":
        self._manager.loadAndRestoreState(filename=filename,instruments=[self.instrument.name()])
        self.requestGetBoardConfig()
        self.displayMessages('Configuration '+str(filename)+' loaded.')    

    # Interaction with a backend instrument either local (in the same memory as this frontpanel) or remote (in another PC's memory)
    # we use here the dispatch strategy

    def requestInitialize(self):
      """
      Requests a (re)initialization of the Acqiris board.
      """
      self.debugPrint('calling instrument.reinit()')
      self.instrument.dispatch('reinit')
      
    def requestParameters(self):
      """
      Requests paramaters of the backend instrument
      """
      self.instrument.dispatch('parameters')

    def requestTemperature(self):
      """
      Requests a temperature reading vof the Acqiris board.
      """
      self.debugPrint('calling instrument.dispatch("Temperature")')
      self.instrument.dispatch('Temperature')
      #self.instrument.Temperature()
    
    def requestCalibrate(self):
      """
      Requests a calibration of the Acqiris board.
      """
      result =  QMessageBox.question(self,'Calibrate?','Do you want to start the calibration of the Acqiris card?',buttons = QMessageBox.Cancel | QMessageBox.Ok)
      if result != QMessageBox.Ok:
        return
      params = self.getParamsFromFrontPanel()
      self.debugPrint('calling instrument.Calibrate()')
      self.instrument.dispatch('Calibrate',option=1,channels=params['wantedChannels'])      #channel
      
    def requestSetBoardConfig(self):
      """
      Requests a configuration of the Acqiris board with the parameters displayed in the frontend.
      """
      params = self.getParamsFromFrontPanel()               # collects all parameters from frontpanel in a dictionary
      self.debugPrint('calling instrument.dispatch("setConfigAll",**params) with param',params)
      self.instrument.dispatch('setConfigAll',**params)     # requests setConfigAll of the Acqiris board
      self.instrument.dispatch('parameters')                # requests parameters stored in the backup instrument 
    
    def requestGetBoardConfig(self):
      """
      Requests reading of the current configuration of the Acqiris board.
      """
      self.instrument.dispatch('getConfigAll')
      self.instrument.dispatch('parameters')
    
    def request1Acquire(self):
      """
      Disable the acquire button and request an acquisition by and a transfer from the Acqiris board to the backend instrument.
      """
      if not self._waitingForData:
        self.acquireButton.setEnabled(False)
        if self.autoConfig.isChecked():
          self.displayMessages('Sending configuration')
          self.requestSetBoardConfig()
        self.clearPlotTabs()
        # update the dictionary of parameters and call AcquireTransfer
        self.requestAcquire()
        self.displayMessages('AcquireTransfer request sent...')
      else:
        self.displayMessages('Already waiting for data. AcquireTransfer request not sent.')    
    
    def requestAcquire(self):
      """
      Request an acquisition by and a transfer from the Acqiris board to the backend instrument.
      """
      if not self._waitingForData :
        params = self.getParamsFromFrontPanel()
        self.instrument.dispatch('AcquireTransfer',wantedChannels=params['wantedChannels'],transferAverage=params['transferAverage'],nLoops=params['nLoops'])
        self._waitingForData=True
      # A notification will be sent by the instrument at the end of the AcquireTransfer function

    def requestStop(self):
      """
      Tries to stop the current acquisition in the Acqiris board (in case of problem).
      """
      self.runCheckbox.setChecked(False)
      self.instrument.StopAcquisition()    # 
      self._waitingForData = False
      self.acquireButton.setEnabled(True)

    # Update frontpanel from backend instrument

    def updatedGui(self,subject,property = None, value =None, message = None):
      """
      Processes notifications from the Acqiris backend instrument and updates this frontpanel accordingly.
      """
      self.debugPrint('updatdGui()called with property ', property, 'and value',value)
      if subject == self.instrument:
        if self.listen.isChecked():
          if property == 'Temperature':
            self.displayTemperature(value)
          elif property in ['parameters','restoreStateFromFile']:
            self.setFrontPanelFromParams(**value)
          elif property == 'Acquire':
            pass # DV 11/03/2012
          elif property in ['DMATransfer','AcquireTransfer']:
            self.newDataAvailableInInstrument()
          elif property == 'reinit':
            self.requestGetBoardConfig()
      elif subject == self:
        if property == 'restoreStateFromFile':
          if value is None:
            value=self.instrument.parameters()
          self.setFrontPanelFromParams(**value) 

    def displayTemperature(self,temp):
      """
      Displays the temperature in this frontpanel.
      Called by the updatedGui function when property is 'temperature'.
      """
      palette = QPalette()
      if temp<=55:
        palette.setColor(0,QColor('blue'))
      else:
        palette.setColor(0,QColor('red'))
      self.labelTemp.setPalette(palette)
      message='  '+str(temp)+ u'\N{DEGREE SIGN}'+'C'+' at ' + time.strftime('%H:%M:%S')
      self.labelTemp.setText(message)
      self.labelTemp.show()

    def setFrontPanelFromParams(self,**params):
      """
      Updates this frontpanel according to the given dictionary params.
      """
      self.debugPrint('in setFrontPanelFromParams')
      if 'couplings' in params and len(params['couplings'])>=self.nbrOfChannels:
        for i in range(0,self.nbrOfChannels):
          self.couplings[i].setCurrentIndex(int(params['couplings'][i]))
      if 'bandwidths' in params and len(params['bandwidths'])>=self.nbrOfChannels:
        for i in range(0,self.nbrOfChannels):
          self.bandwidths[i].setCurrentIndex(int(params['bandwidths'][i]))
      if 'fullScales' in params and len(params['fullScales'])>=self.nbrOfChannels:
        for i in range(0,self.nbrOfChannels):
          self.fullScales[i].setText(str(params['fullScales'][i]))
      if 'offsets' in params and len(params['offsets'])>=self.nbrOfChannels:
        for i in range(0,self.nbrOfChannels):
          self.offsets[i].setText(str(params['offsets'][i]))
      if 'usedChannels' in params:
        for i in range(0,self.nbrOfChannels):
           used=bool(params['usedChannels'] & (1 << i))
           if (not used): self.activated[i].setChecked(False)
           self.activated[i].setDisabled(not used)     
      if 'trigSource' in params:
        if int(params['trigSource']) != -1:
          self.trigSource.setCurrentIndex(int(params['trigSource']))
        else:
          self.trigSource.setCurrentIndex(0)
      for key in ['trigCoupling','trigSlope','clock','memType']:
        if key in params and hasattr(self,key):
          getattr(self,key).setCurrentIndex(int(params[key]))
      if 'configMode' in params:
        index=int(params['configMode'])
        if index == 10: index=3
        self.configMode.setCurrentIndex(index) 
      for key in ['sampleInterval','numberOfPoints','trigDelay','numberOfSegments','trigLevel1','trigLevel2']:
        if key in params and hasattr(self,key):
          getattr(self,key).setText(str(params[key]))
      if (('numberOfBanks' in params) and ('configMode' in params) and (params['configMode'] == 10))  :
          self.numberOfBanks.setText(str(params['numberOfBanks']))    
      if ('nLoops' in params):
          self.nLoops.setText(str(params['nLoops']))    
      if 'convertersPerChannel' in params:
        if params['convertersPerChannel'] == 1:
          self.chCombine.setCurrentIndex(0)
        elif params['convertersPerChannel'] == 2:
          self.chCombine.setCurrentIndex(1)
        elif params['convertersPerChannel'] == 4:
          self.chCombine.setCurrentIndex(2)
      for key in ['transferAverage']:
        if key in params and hasattr(self,key):
          getattr(self,key).setChecked(bool(params[key]))

    def newDataAvailableInInstrument(self,dispatchID=None,result=None):
      """
      Updates the data displayed in this frontpanel after a notification of new data in the backend instrument.
      Called by the updatedGui function when property is 'DMATransfer' or 'AcquireTransfer'.
      """
      self.debugPrint('in newDataAvailableInInstrument()')
      # get a copy of LastWave
      #self.displayMessages('Transferring new data from instrument to frontpanel...')
      lw=self.instrument.getLastWave()
      if lw != 'memory locked' :
        self.lastWave=lw  # WARNING: we have pointers to the data arrays. If the instrument and/or the board is on the same machine and manipulatie the data at the same time, a memory error will occur.
        #self.displayMessages('Transferring new data from instrument to frontpanel...done.')
        self.resetTrend()# reset the data analysis
        # enable or disable the proper tabs depending on the data received
        for i in [0,3]:
          self.plotTabs.setTabEnabled ( i, True) # timestamp tab and average always available
        for i in [1,2,4]:                        # and disable the other tabs (except times) if average
          self.plotTabs.setTabEnabled ( i, not self.lastWave['transferAverage']) 
        if self.lastWave['transferAverage']: self.plotTabs.setCurrentIndex(3)
        #elif self.plotTabs.currentIndex() == 3 and not self.forceCalc.isChecked(): self.plotTabs.setCurrentIndex(2) # bad idea => makes impossible to force the average calculation
        # update the plot tabs if auto plot
        if bool(self.updatePlots.isChecked()):
          self.updatePlotTabs()
      self._waitingForData = False
      if not self.runCheckbox.isChecked() :self.acquireButton.setEnabled(True)              

    #  generic methods for displaying info

    def displayMessages(self,message):
      if self._displayMessages:
        self.messageString.setText(message)
        self.messageString.repaint()

    def getParamsFromFrontPanel(self):
      """
      Reads all the parameter values from the frontpanel and returns them in a dictionary.
      This dictionary can be used as a parameter to a configure function as "ConfigureV2"
      """
      params = dict()
      params['offsets'] = list()          #list of vertical offsets
      params['fullScales'] = list()       #list of vertical fullscales
      params['couplings'] = list()        #list of coupling codes (see front panel)
      params['bandwidths'] = list()       #list of vertical bandwidth codes (see front panel)
      for i in range(0,self.nbrOfChannels):                # read from front panel
        params['offsets'].append(float(self.offsets[i].text()))
        params['fullScales'].append(float(self.fullScales[i].text()))
        params['couplings'].append(self.couplings[i].itemData(self.couplings[i].currentIndex()).toInt()[0])
        params['bandwidths'].append(self.bandwidths[i].itemData(self.bandwidths[i].currentIndex()).toInt()[0])  
      if self.chCombine.currentIndex() == 3:
        params['convertersPerChannel'] = 4
      elif self.chCombine.currentIndex() == 2:
        params['convertersPerChannel'] = 2
      else :
        params['convertersPerChannel'] = 1
      params['wantedChannels'] = 0          # used channels = sum 2^channel
      params['usedChannels'] = 0
      for i in range(0,self.nbrOfChannels):
        if self.activated[i].isChecked(): params['wantedChannels']+=1<<i
        if self.activated[i].isEnabled(): params['usedChannels']+=1<<i
      params['clock'] = self.clock.itemData(self.clock.currentIndex()).toInt()[0]   # clock mode code
      params['sampleInterval'] = float(self.sampleInterval.text())  # sampling interval in s
      params['trigSource'] = self.trigSource.itemData(self.trigSource.currentIndex()).toInt()[0]        # trigger source code
      if params['trigSource'] == 0:      
        params['trigSource'] = -1
      params['trigCoupling'] = self.trigCoupling.itemData(self.trigCoupling.currentIndex()).toInt()[0]  # trigger coupling code
      params['trigSlope'] = self.trigSlope.itemData(self.trigSlope.currentIndex()).toInt()[0]           # trigger slope code
      params['trigLevel1'] = float(self.trigLevel1.text())                                              # trigger level 1
      params['trigLevel2'] = float(self.trigLevel2.text())                                              # trigger level 2 for clever trigger
      params['trigDelay'] = float(self.trigDelay.text())                                                # trigger delay in s
      params['numberOfPoints'] = int(self.numberOfPoints.text())                                        # sampling interval 
      params['numberOfSegments'] = int(self.numberOfSegments.text())# sampling interval
      params['memType'] = self.memType.itemData(self.memType.currentIndex()).toInt()[0]   # memory to be used (defautl or force internal))
      params['configMode'] = self.configMode.currentIndex()                               # acquisition mode (see front panel)
      if  params['configMode'] == 3:
        params['configMode'] = 10                                                         
      params['numberOfBanks']= int(self.numberOfBanks.text())                                    # number of banks in memory (1 in all modes except SAR)
      params['nLoops']= int(self.nLoops.text())                                           # number of acquisition loops (or banks in SAR mode)
      params['transferAverage']= bool(self.transferAverage.isChecked())                  # transfer averaged trace only
      return params     
    
    def clearPlotTabs(self):
      for plot in [self.sequencePlot,self.segmentPlot,self.averagePlot,self.trendPlot]:
        plot.axes.lines=[]
        plot.axes.patches=[]
        plot.redraw()

    def updatePlotTabs(self):
      self.debugPrint('in updatePlotTabs()')
      self.displayMessages('Plotting data #%i...'%(self.lastWave['identifier']))
      if self.plotTabs.currentIndex() == 0: self.updateTimeStampsTab() 
      elif self.plotTabs.currentIndex() == 1: self.updateSequenceTab()
      elif self.plotTabs.currentIndex() == 2: self.updateSegmentTab()
      elif self.plotTabs.currentIndex() == 3: self.updateAverageTab()
      elif self.plotTabs.currentIndex() == 4: self.updateTrendTab()
      self.displayMessages('Data #%i plotted'%(self.lastWave['identifier']))
      
    def updateTimeStampsTab(self):
      self.debugPrint('in updateTimeStampsTab()')
      self.plotTimeStamps()
    
    def updateSequenceTab(self):
      """ """
      self.plotSequence()
      
    def updateSegmentTab(self):
      nbrSegmentMax=max(self.lastWave['nbrSegmentArray'])
      self.segmentNumber.setMaximum(max(nbrSegmentMax,1))
      self.NumOfSegDislay.setText('out of '+ str(nbrSegmentMax))
      self.plotSegment()
      
    def updateAverageTab(self):
      """ """
      self.plotAverage()
      
    def updateTrendTab(self):
      key = str(self.trendList.currentText())
      boxcar=(key == 'Boxcar')
      for element in [self.index1,self.index2]:
        element.setEnabled(boxcar)
      maxi=self.lastWave['nbrSamplesPerSeg']-1
      self.index1.setMaximum(maxi)
      self.index2.setMaximum(maxi)
      if self.index2.value == 0 : self.index2.setValue(maxi)
      if boxcar:
        self.trend[key]['exist']=False
      self.plotTrend()
      
    def plotTimeStamps(self):
      """
      Plot the time array
      """
      self.debugPrint('in plotTimeStamps()')
      ax=self.timeStampsPlot.axes
      if ax.get_xlabel() == '': ax.set_xlabel('segment index')
      if ax.get_ylabel() == '': ax.set_ylabel('t or Delta t (s)')
      ax.lines=[]
      if self.lastWave['timeStampsSize']:
        if self.deltaTimestamps.isChecked():
          y=self.lastWave['timeStamps'][1:]-self.lastWave['timeStamps'][:-1]
        else:
          y=self.lastWave['timeStamps'][:]
        ax.plot(y,self.colors[0],marker='o',markersize=3)
      self.timeStampsPlot.redraw()
      
    def plotSequence(self):
      """
      Plot the whole sequence in the Sequence tab.
      """
      self.debugPrint('in plotSequence()')
      ax=self.sequencePlot.axes
      if ax.get_xlabel() == '': ax.set_xlabel('sample index')
      if ax.get_ylabel() == '': ax.set_ylabel('voltage (V)')
      ax.lines=[] 
      if not(self.lastWave['transferAverage']):
        channels2Plot=0
        for i in range(self.nbrOfChannels):
          if self.lastWave['transferedChannels'] & (1 << i) and self.ch1[i].isChecked():
            channels2Plot+=1
        for i in range(self.nbrOfChannels):
          if self.lastWave['transferedChannels'] & (1 << i) and self.ch1[i].isChecked():
            if self.overlay.isChecked():
              for j in range(self.lastWave['nbrSegmentArray'][i]):
                start= j*self.lastWave['nbrSamplesPerSeg']
                stop=start+self.lastWave['nbrSamplesPerSeg']-1
                if channels2Plot>=2: 
                  ax.plot(self.lastWave['wave'][i][start:stop+1],self.colors[i])
                else:
                  ax.plot(self.lastWave['wave'][i][start:stop+1])  
            else:
              ax.plot(self.lastWave['wave'][i],self.colors[i]) 
        self.sequencePlot.redraw()

    def plotSegment(self):
      self.debugPrint('in plotSegment()')
      self.sm.setVisible(self.smooth.isChecked())
      ax=self.segmentPlot.axes
      if self.segmentTab.mode.currentIndex() == 1:  # xy mode
        if ax.get_xlabel() != 'voltage (V)': ax.set_xlabel('voltage (V)')
      else:
        ax.set_xlabel('sample index (samp. time = '+str.format('{0:.3e}',self.lastWave['samplingTime'])+' s)')
      if ax.get_ylabel() == '': ax.set_ylabel('voltage (V)')
      ax.lines=[]
      requestedSegment=self.segmentNumber.value()
      if requestedSegment<=self.lastWave['timeStampsSize']:
        self.currentTimeStamp.setText(str.format('{0:.3e}',self.lastWave['timeStamps'][requestedSegment-1]))
      if requestedSegment<=self.lastWave['horPosSize']:
        self.currentHorPos.setText(str.format('{0:.3e}',self.lastWave['horPos'][requestedSegment-1]))
      start= (requestedSegment-1)*self.lastWave['nbrSamplesPerSeg']
      stop=start+self.lastWave['nbrSamplesPerSeg']-1
      chIndices,channels=[],[]
      for i in range(0,self.nbrOfChannels):
        if self.lastWave['transferedChannels'] & (1 << i)and self.ch2[i].isChecked():
          y=self.lastWave['wave'][i][start:stop+1]
          if self.smooth.isChecked() :  y= np.array(self.smoothing(y))
          chIndices.append(i)
          channels.append(y)
      if self.segmentTab.mode.currentIndex() == 0:
        for i,channel in zip(chIndices, channels):
          ax.plot(channel,self.colors[i])
      elif self.segmentTab.mode.currentIndex() == 1:
        for i in range(len(chIndices)/2):
          j=2*i
          ax.plot(channels[j],channels[j+1],self.colors[j])
      elif self.segmentTab.mode.currentIndex() == 2:
        for i in range(len(chIndices)/2):
          j=2*i
          ax.plot((channels[j]**2+channels[j+1]**2)**0.5,self.colors[j])
      self.segmentPlot.redraw()
  
    def smoothing(self,y):
      l=len(y)
      n=min(self.sm.value(),l)
      z=np.zeros(l-(n-1))
      z[:l-(n-1)]=y[:l-(n-1)]
      for i in range(1,n):
        z+=y[i:l-(n-1)+i]
      return z/n

    def plotAverage(self):
      """
      Plot or replot averages in the average tab.
      """
      self.debugPrint('in plotAverage()')
      ax=self.averagePlot.axes
      # modify axes labels
      if self.averageTab.mode.currentIndex() == 1:  # xy mode
        if ax.get_xlabel() != 'voltage (V)': ax.set_xlabel('voltage (V)')
      else:
        ax.set_xlabel('sample index (samp. time = '+str.format('{0:.3e}',self.lastWave['samplingTime'])+' s)')
      if ax.get_ylabel() == '': ax.set_ylabel('voltage (V)')
      ax.lines=[]
      # Asl for average calculation if needed
      if not(self.lastWave['transferAverage']) and not(self.lastWave['averageCalculated']) and self.forceCalc.isChecked():
        self.debugPrint('calling getLastAverage with identifier=',self.lastWave['identifier'])
        lastAve=self.instrument.getLastAverage(identifier=self.lastWave['identifier'])
        if lastAve is None: return
        self.lastWave['averageCalculated']=lastAve['averageCalculated']
        self.lastWave['lastAverageArray']=lastAve['lastAverageArray']
      chIndices,channels=[],[]
      for i in range(self.nbrOfChannels):
        if self.lastWave['transferedChannels'] & (1 << i)and self.ch3[i].isChecked():
          if self.lastWave['transferAverage']:
            y=self.lastWave['wave'][i]
          elif self.lastWave['averageCalculated']:
            y=self.lastWave['lastAverageArray'][i]
          else:
            return
          chIndices.append(i)
          channels.append(y)    
      if self.averageTab.mode.currentIndex() == 0:
        for i,channel in zip(chIndices, channels):
          ax.plot(channel,self.colors[i])
      elif self.averageTab.mode.currentIndex() == 1:
        for i in range(len(chIndices)/2):
          j=2*i
          ax.plot(channels[j],channels[j+1],self.colors[j])
      elif self.averageTab.mode.currentIndex() == 2:
        for i in range(len(chIndices)/2):
          j=2*i
          ax.plot((channels[j]**2+channels[j+1]**2)**0.5,self.colors[j])
      self.averagePlot.redraw()
      
    def forceCalcNow(self):
      """
      Call the function that calculates and plots averages
      """
      if self.forceCalc.isChecked(): self.plotAverage()   

    def resetTrend(self):
      # Place here the definitions of the functions that calculate a property of a data segment x
      functs={'Min':lambda x: min(x),'Max':lambda x: max(x),'Mean':lambda x: np.mean(x),\
      'Std':lambda x: np.std(x),'Var':lambda x: np.var(x),\
      'Boxcar':lambda x: np.mean(x[int(self.index1.value()):int(self.index2.value())])}
      self.trend=dict()
      for i in range(self.trendList.count()):
        key=str(self.trendList.itemText(i))
        self.trend[key] ={'exist':False,'arr':[[],[],[],[]],'funct':functs[key]}
    
    def plotTrend(self):
      self.debugPrint('in plotTrend()')
      ax=self.trendPlot.axes
      ax.lines=[]
      ax.patches=[]
      key = str(self.trendList.currentText())
      if not(self.lastWave['transferAverage']) and key in self.trend: 
        funct=self.trend[key]['funct'] 
        if not self.trend[key]['exist']:
          self.trend[key]['arr']=[[],[],[],[]]
          for i in range(4):
            if self.lastWave['transferedChannels']  & (1<<i):
              arr=[]
              for j in range (self.lastWave['nbrSegmentArray'][i]):
                start= j*self.lastWave['nbrSamplesPerSeg']
                stop=start+self.lastWave['nbrSamplesPerSeg']-1
                vect=self.lastWave['wave'][i][start:stop]
                arr.append(self.trend[key]['funct'](vect))
              self.trend[key]['arr'][i]=arr
          self.trend[key]['exist']=True 
        if not self.histo.isChecked():              # not histo
          ax.set_xlabel('segment index')
          ax.set_ylabel('property')  
        else:                                       # histo
          ax.set_xlabel('property')
          ax.set_ylabel('population')
        for i in range(self.nbrOfChannels): 
          if (self.lastWave['transferedChannels']  & (1<<i)) and self.ch4[i].isChecked():
              if not self.histo.isChecked():        # not histo
                ax.plot(self.trend[key]['arr'][i],self.colors[i],marker='o',markersize=3)               
              else:
                bins=int(self.bin.value())           # histo
                hist, bin_edges =np.histogram(self.trend[key]['arr'][i], bins=bins)
                width=(bin_edges[-1]-bin_edges[0])/bins
                ax.bar(bin_edges[:-1], hist,width=width,color=self.colors[i])
        self.trendPlot.redraw()
      else: self.displayMessages('No definition for function '+ key) 
          
    # Runs 'AcquireTransfer' in a asynchronous loop based on a timer and a flag indicating whether the previous update is completed.

    def runOscillo(self,newState):
      minRepPeriod=100
      if newState != 0:
        self.debugPrint('Entering continous run.')
        self.acquireButton.setEnabled(False)
        self._displayMessages=True
        self.displayMessages('Entering continous run (no further messages).')
        self._displayMessages=False
        self._timerRun.setInterval(minRepPeriod)
        self._timerRun.start()
      else:
        self._timerRun.stop()
        self._displayMessages=True
        self.displayMessages('Exit from continous run.')
        if not self._waitingForData:
          self.acquireButton.setEnabled(True)
        
    def onTimerRun(self):
        self.requestAcquire()

    # Interaction with outside: datacube build, transfer to file, data manager or Igor.

    def makeDatacube(self):
      if   self.plotTabs.currentIndex() == 0:
        cube= self.timestampDatacube
        cube.clear()
        cube.setName('timestamps')
        cube.createCol('timestamps_(s)',values=self.lastWave['timeStamps'])
      elif self.plotTabs.currentIndex() == 1:
        cube= self.sequenceDatacube
        cube.clear()
        cube.setName('sequence')
        cube.createCol('ApproxTime',values=self.lastWave['samplingTime']*np.arange(self.lastWave['nbrSamplesPerSeg']))
        channels=[]
        lengthes=[]
        for i in range(self.nbrOfChannels):
          if self.lastWave['transferedChannels'] & (1 << i)and self.ch2[i].isChecked():
            channels.append(i)
            lengthes.append(self.lastWave['nbrSegmentArray'][i])
          leng=min(lengthes)
        for i in range(1,leng+1):
          start= (i-1)*self.lastWave['nbrSamplesPerSeg']
          stop=start+self.lastWave['nbrSamplesPerSeg']-1
          for j in channels:
            cube.createCol('ch'+str(j)+'seg'+str(i),values=self.lastWave['wave'][j][start:stop+1])
      elif self.plotTabs.currentIndex() == 2:
        cube= self.segmentDatacube
        cube.clear()
        requestedSegment=self.segmentNumber.value()
        start= (requestedSegment-1)*self.lastWave['nbrSamplesPerSeg']
        stop=start+self.lastWave['nbrSamplesPerSeg']-1
        cube.setName('segment_'+str(requestedSegment))
        cube.createCol('time',values=self.lastWave['horPos'][requestedSegment-1]+ self.lastWave['samplingTime']*np.arange(self.lastWave['nbrSamplesPerSeg']))
        for i in range(self.nbrOfChannels):
          if self.lastWave['transferedChannels'] & (1 << i)and self.ch2[i].isChecked():
            cube.createCol('channel'+str(i),values=self.lastWave['wave'][i][start:stop+1])  
      elif self.plotTabs.currentIndex() == 3:
        cube=self.averageDatacube
        cube.clear()
        cube.setName('average')
        cube.createCol('time',values=self.lastWave['samplingTime']*np.arange(self.lastWave['nbrSamplesPerSeg']))
        for i in range(self.nbrOfChannels):
          if self.lastWave['transferedChannels'] & (1 << i) and self.ch3[i].isChecked():
            if self.lastWave['transferAverage']:
              wave=self.lastWave['wave'][i]
            elif self.lastWave['averageCalculated']:
              wave=self.lastWave['lastAverageArray'][i]
            cube.createCol('ch'+str(i)+'av'+str(self.lastWave['nbrSegmentArray'][i]),values=wave)  
      elif self.plotTabs.currentIndex() == 4:
        cube= self.trendDatacube
        cube.clear()
        key = str(self.trendList.currentText())
        if not self.histo.isChecked():
          cube.setName('trend_'+key)
          cube.createCol('timeStamps_(s)',values=self.lastWave['timeStamps'])
        else:
          cube.setName('histo_'+key)
        for i in range(self.nbrOfChannels): 
          if (self.lastWave['transferedChannels']  & (1<<i)) and self.ch4[i].isChecked():
              if not self.histo.isChecked():        # not histo
                cube.createCol('ch'+str(i)+'_'+key,values=self.trend[key]['arr'][i])              
              else:
                bins=int(self.bin.value())           # histo
                hist, bin_edges =np.histogram(self.trend[key]['arr'][i], bins=bins)
                cube.createCol('ch'+str(i)+'_'+key,values=((np.roll(bin_edges,-1)+bin_edges)/2.)[:-1])
                cube.createCol('ch'+str(i)+'_events',values=hist)
      return cube

    def saveData(self):
      cube=self.makeDatacube() # analyze why several minute per Mega Samples ....
      if cube is not None:
        defaultName='wave'+str(self.lastWave['identifier'])+'_'+cube.name()
        if self._workingDirectory != '':
          defaultName=self._workingDirectory+defaultName
        filename=str(QtGui.QFileDialog.getSaveFileName(parent=self,directory=defaultName,filter='Text files (*.txt *.par )'))
        if len(filename) > 0:
          path=os.path.dirname(filename)+'/'
          self._workingDirectory=path
          basename=os.path.basename(filename)
          cube.setFilename(filename)
          # def savetxt(self,path = None, absPath=None, saveChildren = True,overwrite = False,forceSave = False,allInOneFile = False, forceFolders=False)
          cube.savetxt(path=filename,overwrite=True)
          self.displayMessages('datacube saved in '+filename)

    def toDatamanager(self):
      cube=self.makeDatacube()
      if cube:
        copy.deepcopy(cube).toDataManager()

    def sendToIgor(self):
      cube=self.makeDatacube()
      if cube:
        cube.sendToIgor()   
        
    def saveFig(self):
      """
      Save the displayed plot to an image file (PDF, PNG, EPS, ...)
      """
      plot=self.plotTabs.currentWidget().findChildren(MatplotlibCanvas)[0]
      if not plot: return
      if self._workingDirectory != '':
          self.fileDialog.setDirectory(self._workingDirectory)
      self.fileDialog.setAcceptMode(1)
      self.fileDialog.setNameFilter('Image files (*.png *.eps *.jpg *.pdf)');
      self.fileDialog.selectFile('acqisitionN%i' %self.lastWave['identifier'])
      self.fileDialog.setDefaultSuffix('jpg') 
      filename = str(self.fileDialog.getSaveFileName())
      if len(filename) > 0:
          self._workingDirectory = str(self.fileDialog.directory().dirName())
          plot.figure.savefig(filename)
          self.displayMessages('Figure saved in '+filename)

    # GUI building functions
      
    def channelParamGUI(self,i):
      myWidth=90
      activated = QCheckBox('Active')
      activated.setChecked(True)
          
      fullScale=QLineEdit('5.0')
      fullScale.setMaximumWidth(myWidth)
      offset=QLineEdit('0.0');
      offset.setMaximumWidth(myWidth)
        
      coupling = QComboBox()
      coupling.addItem('Ground',0)
      coupling.addItem('DC 1 MO',1)
      coupling.addItem('AC 1 MO',2)
      coupling.addItem('DC 50 O',3)
      coupling.addItem('AC 50 O',4)
      coupling.setCurrentIndex(3)
      coupling.setMaximumWidth(myWidth)
        
      bandwidth = QComboBox()
      bandwidth.addItem('Max 1GHz (0)',0)
      bandwidth.addItem('25  MHz (1)',1)
      bandwidth.addItem('700 MHz (2)',2)
      bandwidth.addItem('200 MHz (3)',3)
      bandwidth.addItem('20  MHz (4)',4)
      bandwidth.addItem('35  MHz (5)',5)
      bandwidth.setCurrentIndex(3)
      bandwidth.setMaximumWidth(myWidth)
            
      self.activated.append(activated)
      self.couplings.append(coupling)
      self.fullScales.append(fullScale)
      self.bandwidths.append(bandwidth)
      self.offsets.append(offset)
      label=QLabel('Channel %d' % (i+1))
      palette = QPalette()
      palette.setColor(0,QColor(self.colors[i]))
      label.setPalette(palette)
      self.channelGrid.addWidget(label,1,i)
      self.channelGrid.addWidget(activated,2,i)
      self.channelGrid.addWidget(QLabel('Coupling %d' % (i+1)),3,i)
      self.channelGrid.addWidget(self.couplings[i],4,i)
      self.channelGrid.addWidget(QLabel('Fullscale %d (V)' % (i+1)),5,i)
      self.channelGrid.addWidget(self.fullScales[i],6,i)
      self.channelGrid.addWidget(QLabel('Offset %d (V)' % (i+1)),7,i)
      self.channelGrid.addWidget(self.offsets[i],8,i)
      self.channelGrid.addWidget(QLabel('Bandwidth '+str(i+1)),9,i)
      self.channelGrid.addWidget(self.bandwidths[i],10,i)
    
    def chCombineGUI(self):
      commands=['1 ADC per channel (0)','2 ADC per channel (1)','4 ADC per channel (2)']
      indexMax=[0,1,1,2]
      self.chCombine = QComboBox()
      for i in range(0,indexMax[self.nbrOfChannels-1]+1):
        self.chCombine.addItem(commands[i],i)
      self.chCombine.setCurrentIndex(0)
      # response to a currentIndexChanged() event of self.chCombine
      def chCombineChanged():
        if self.chCombine.currentIndex() == 0:      # 1 ADC per channel
          for i in range(0,self.nbrOfChannels):
            self.activated[i].setDisabled(False)
            #self.activated[i].setChecked(True)
        elif self.chCombine.currentIndex() == 1:    # 2 ADCs per channel
            self.activated[0].setDisabled(False)
            self.activated[1].setChecked(False)
            self.activated[1].setDisabled(True)
            if self.nbrOfChannels>=4:
              self.activated[2].setDisabled(False)
              self.activated[3].setChecked(False)
              self.activated[3].setDisabled(True)
        elif self.chCombine.currentIndex() == 2:    # 4 ADCs per channel
            self.activated[0].setDisabled(False)
            self.activated[1].setChecked(False)
            self.activated[2].setChecked(False)
            self.activated[3].setChecked(False)
            self.activated[1].setDisabled(False)
            self.activated[2].setDisabled(False)
            self.activated[3].setDisabled(False)
        self.sampleInterval.setFocus()
        self.sampleInterval.clearFocus()  
      self.connect(self.chCombine,SIGNAL('currentIndexChanged(int)'),chCombineChanged)
    
    def triggerGUI(self,myWidth):
              
      self.trigSource = QComboBox()        
      self.trigSource.addItem('Ext 1',0)
      for i in  range(1,self.nbrOfChannels+1):
        self.trigSource.addItem('Ch '+str(i),i)
      self.trigSource.setMaximumWidth(myWidth)

      self.trigCoupling = QComboBox()    
      self.trigCoupling.addItem('DC (0)',0)
      self.trigCoupling.addItem('AC (1)',1)
      self.trigCoupling.addItem('HF Reject (2)',2)
      self.trigCoupling.addItem('DC 50 O (3)',3)
      self.trigCoupling.addItem('AC 50 O (4)',4)
      self.trigCoupling.setCurrentIndex(3)
      self.trigCoupling.setMaximumWidth(myWidth)

      self.trigSlope = QComboBox()      
      self.trigSlope.addItem('Pos. slope',0)
      self.trigSlope.addItem('Neg. slope',1)
      self.trigSlope.addItem('out of window',2)
      self.trigSlope.addItem('into window',3)
      self.trigSlope.addItem('HF divide',4)
      self.trigSlope.addItem('Spike stretcher',5)
      self.trigSlope.setCurrentIndex(1)
      self.trigSlope.setMaximumWidth(myWidth)   
      
      # response to a currentIndexChanged() event of self.trigSlope
      def trigSlopeChanged():
        if self.trigSlope.currentIndex()in (2,3):
          self.trigLevel2.setDisabled(False)
        else:
          self.trigLevel2.setDisabled(True)
      self.connect(self.trigSlope,SIGNAL('currentIndexChanged(int)'),trigSlopeChanged)

      self.triggerLevelGrid= QGridLayout()
      self.triggerLevelGrid.setVerticalSpacing(2)
      self.triggerLevelGrid.setHorizontalSpacing(5)
      myWidth2=40
      self.trigLevel1 = QLineEdit('500.0')        
      self.trigLevel1.setMaximumWidth(myWidth2)   
      self.triggerLevelGrid.addWidget(self.trigLevel1,0,0)
      self.trigLevel2 = QLineEdit('600.0')        
      self.trigLevel2.setMaximumWidth(myWidth2)
      self.triggerLevelGrid.addWidget(self.trigLevel2,0,1)   
        
      self.trigDelay = QLineEdit('400e-9')        
      self.trigDelay.setMaximumWidth(myWidth) 
    
    def horizParamsGUI(self,myWidth):
      self.sampleInterval = QLineEdit('1e-9')
      self.sampleInterval.setMaximumWidth(myWidth)         
      
      # response to a editingFinished() event of sampleInterval
      def sampleIntervalChanged():
        minStep=0.5e-9
        if self.chCombine.currentIndex() == 1:
          minStep/=2
        elif self.chCombine.currentIndex() == 2 :
          minStep/=4
        step=minStep*round(float(self.sampleInterval.text())/minStep)
        if step< minStep :
          mb=QMessageBox.warning(self, 'Warning', "sampleInterval can't be shorter than "+str(minStep)+' s\n with the actual channel configuration.')
          step=minStep
        self.sampleInterval.setText(str(step))
          
      self.connect(self.sampleInterval ,SIGNAL('editingFinished ()'),sampleIntervalChanged)

      self.numberOfPoints = QLineEdit('1000')
      self.numberOfPoints.setMaximumWidth(myWidth)         
      
      # response to a editingFinished() event of numberOfPoints
      def numberOfPointsChanged():
        self.numberOfPoints.setText(str(int(np.floor(float(self.numberOfPoints.text())))))
        if int(self.numberOfPoints.text())<1:
          self.numberOfSegments.setText('1')
          mb=QMessageBox.warning(self, 'Warning', 'Number of points >=1')
          
      self.connect(self.numberOfPoints ,SIGNAL('editingFinished()'),numberOfPointsChanged)
      
      self.numberOfSegments = QLineEdit('100')
      self.numberOfSegments.setMaximumWidth(myWidth)              
      
      # response to a editingFinished() event of numberOfSegments
      def numberOfSegmentsChanged():
        self.numberOfSegments.setText(str(int(np.floor(float(self.numberOfSegments.text())))))
        if int(self.numberOfSegments.text())<1:
          self.numberOfSegments.setText('1')
          mb=QMessageBox.warning(self, 'Warning', 'Number of segments>=1')
        elif self.memType.currentIndex() == 1 and int(self.numberOfSegments.text())>1000:
          self.nLoops.setText(str(int(self.numberOfSegments.text())/1000))
          self.numberOfSegments.setText('1000')
          mb=QMessageBox.warning(self, 'Warning', 'Number of segments<=1000 with internal memory.\nAdjust number of banks in acquisition,\nor swith to default memory.')
        elif self.memType.currentIndex() == 0 and int(self.numberOfSegments.text())>16000:
          self.numberOfSegments.setText('16000')
          mb=QMessageBox.warning(self, 'Warning', 'Number of segments<=16000 with M32M extended memory.')
          
      self.connect(self.numberOfSegments ,SIGNAL('editingFinished()'),numberOfSegmentsChanged)
       
      self.numberOfBanks = QLineEdit('1')
      self.numberOfBanks.setMaximumWidth(myWidth)       
      self.numberOfBanks.setDisabled(True)        
      
      self.nLoops = QLineEdit('1')
      self.nLoops.setMaximumWidth(myWidth)
      
    def clockMemGUI(self,myWidth):
      self.clock = QComboBox()     
      self.clock.addItem('Int clk',0)
      self.clock.addItem('Ext clk',1)
      self.clock.addItem('Ext Ref 10MHz',2)
      self.clock.addItem('Ext clk Start/Stop',3)
      self.clock.setCurrentIndex(2)
      self.clock.setMaximumWidth(myWidth+10)     
      
      self.memType = QComboBox()     
      self.memType.addItem('default',0)
      self.memType.addItem('force internal',1)
      self.memType.setCurrentIndex(1)
      self.memType.setMaximumWidth(myWidth+10)     
      
      # response to a currentIndexChanged() event of self.memType
      def memTypeChanged():
          self.numberOfSegments.setFocus()
          self.numberOfSegments.clearFocus()
 
      self.connect(self.memType,SIGNAL('currentIndexChanged(int)'),memTypeChanged)
      
      self.configMode = QComboBox()     
      self.configMode.addItem('normal',0)
      self.configMode.addItem('start on trigger',1)
      self.configMode.addItem('sequence wrap',1)
      self.configMode.addItem('SAR mode',1)
      self.configMode.setCurrentIndex(0)
      self.configMode.setMaximumWidth(myWidth+10)     
      
      # response to a currentIndexChanged() event of self.configMode
      def configModeChanged():
        if self.configMode.currentIndex() == 3: # SAR mode: simultaneous acquisition and transfer
          self.numberOfBanks.setText('2')
          self.numberOfBanks.setDisabled(False)
          self.memType.setCurrentIndex(1)
          self.memType.setDisabled(True)
        else :
          self.numberOfBanks.setText('1')
          self.numberOfBanks.setDisabled(True)
          self.memType.setDisabled(False)
          if self.configMode.currentIndex() == 1: # start on trigger
            a=1
          elif self.configMode.currentIndex() == 2: # wrap mode
            a=1
          elif self.configMode.currentIndex() == 0:   #normal
            a=1  
      self.connect(self.configMode,SIGNAL('currentIndexChanged(int)'),configModeChanged)
    
    def plotTabGUI(self):
      myWidth=4
      myHeight=3.5
      mydpi=80
      
      # Timestamps tab
      self.timestampTab = QWidget()
      self.timestampDatacube=Datacube('timeStamps')
      self.timestampTabLayout = QGridLayout(self.timestampTab)
      self.deltaTimestamps=QCheckBox('Delta Timestamps')
      self.timestampTabLayout.addWidget(self.deltaTimestamps)
      self.timeStampsPlot = MatplotlibCanvas(width=myWidth, height=myHeight, dpi=mydpi)
      self.timestampTabLayout.addWidget(self.timeStampsPlot)
      self.connect(self.deltaTimestamps,SIGNAL('stateChanged(int)'),self.plotTimeStamps)
         
      # Full sequence tab
      self.sequenceTab = QWidget()
      self.sequenceDatacube=Datacube('sequence')
      self.sequenceTabLayout = QGridLayout(self.sequenceTab)
      seqt=self.sequenceTabLayout
      self.ch1=[]
      for i in range(self.nbrOfChannels):
        self.ch1.append(QCheckBox('Ch'+str(i+1)))
        self.ch1[i].setChecked(True)
        self.connect(self.ch1[i],SIGNAL('stateChanged(int)'),self.plotSequence)
        seqt.addWidget(self.ch1[i],0,seqt.columnCount ())        
      self.overlay=QCheckBox('Overlay segments')        
      seqt.addWidget(self.overlay,0,seqt.columnCount ())
      self.connect(self.overlay,SIGNAL('stateChanged(int)'),self.plotSequence)
      self.sequencePlot = MatplotlibCanvas(width=myWidth, height=myHeight, dpi=mydpi)
      seqt.addWidget(self.sequencePlot,1,0,1,-1)
      
      # single segment tab
      self.segmentTab = QWidget()
      self.segmentDatacube=Datacube('segment')
      self.segTabLayout = QGridLayout(self.segmentTab)
      segt=self.segTabLayout
      segt.addWidget(QLabel('Segment number:'))
      self.segmentNumber=QSpinBox()
      self.segmentNumber.setMinimum(1)
      self.segmentNumber.setValue(1)
      self.segmentNumber.setWrapping(True)
      self.segmentNumber.setMinimumWidth(60)
      segt.addWidget(self.segmentNumber,0,segt.columnCount ())
      self.connect(self.segmentNumber,SIGNAL('valueChanged(int)'),self.plotSegment)
      self.NumOfSegDislay=QLabel('(out of ??)')
      self.NumOfSegDislay.setMinimumWidth(58)
      segt.addWidget(self.NumOfSegDislay,0,segt.columnCount ())
      segt.addWidget(QLabel('Stamp(s)='),0,segt.columnCount ())
      self.currentTimeStamp=QLabel('??')
      self.currentTimeStamp.setMinimumWidth(58)
      segt.addWidget(self.currentTimeStamp,0,segt.columnCount ())
      self.segTabLayout.addWidget(QLabel('Horiz. pos.(s)='),0,segt.columnCount ())
      self.currentHorPos=QLabel('??')
      self.currentHorPos.setMinimumWidth(58)
      segt.addWidget(self.currentHorPos,0,segt.columnCount ())
      self.ch2=[]
      j=0
      for i in range(self.nbrOfChannels):
        self.ch2.append(QCheckBox('Ch'+str(i+1)))
        self.ch2[i].setChecked(True)
        self.connect(self.ch2[i],SIGNAL('stateChanged(int)'),self.plotSegment)
        segt.addWidget(self.ch2[i],1,i)
        j=i
      j+=1
      mode=QComboBox()
      mode.addItem('Normal',0)
      mode.addItem('XY',0)
      mode.addItem('Amplitude',0)
      segt.addWidget(mode,1,j)
      j+=1
      self.segmentTab.mode=mode
      self.connect(self.segmentTab.mode,SIGNAL('activated(int)'),self.plotSegment)
      self.smooth=QCheckBox('Smooth:')
      segt.addWidget(self.smooth,1,j)
      j+=1
      self.sm=QSpinBox()
      self.sm.setMinimum(2)
      self.sm.setValue(2)
      self.sm.setVisible(False)    
      segt.addWidget(self.sm,1,j)
      self.connect(self.smooth,SIGNAL('stateChanged(int)'),self.plotSegment)
      self.connect(self.sm,SIGNAL('valueChanged(int)'),self.plotSegment)
      self.segmentPlot = MatplotlibCanvas(width=myWidth, height=myHeight, dpi=mydpi)
      segt.addWidget(self.segmentPlot,2,0,1,-1)
      
      # averaged of segments tab
      self.averageTab = QWidget()
      self.averageDatacube=Datacube('average')
      self.averageTabLayout = QGridLayout(self.averageTab)
      at=self.averageTabLayout
      self.ch3=[]
      for i in range(self.nbrOfChannels):
        self.ch3.append(QCheckBox('Ch'+str(i+1)))
        self.ch3[i].setChecked(True)
        self.connect(self.ch3[i],SIGNAL('stateChanged(int)'),self.plotAverage)
        at.addWidget(self.ch3[i],0,at.columnCount())
      mode=QComboBox()
      mode.addItem('Normal',0)
      mode.addItem('XY',0)
      mode.addItem('Amplitude',0)
      at.addWidget(mode,0,at.columnCount ())
      self.averageTab.mode=mode
      self.connect(self.averageTab.mode,SIGNAL('activated(int)'),self.plotAverage)    
      self.forceCalc=QCheckBox('Force calculation')
      at.addWidget(self.forceCalc,0,at.columnCount ())
      self.connect(self.forceCalc,SIGNAL('stateChanged(int)'),self.forceCalcNow)
      self.averagePlot = MatplotlibCanvas(width=myWidth, height=myHeight, dpi=mydpi)
      at.addWidget(self.averagePlot,1,0,1,-1)
      
      # segment trend tab
      #try:
      segmentProperties=['Min','Max','Mean','Var','Std','Boxcar']
        #segmentProperties=self.instrument('DLLMath1Module.segmentProperties')
        #self.mathModule=True
      #except:
        #self.mathModule=False
      if True: #self.mathModule:
        self.trendTab = QWidget()
        self.trendDatacube=Datacube('trend')
        self.trendTabLayout = QGridLayout(self.trendTab)
        tt=self.trendTabLayout
        self.ch4=[]
        for i in range(self.nbrOfChannels):
          self.ch4.append(QCheckBox('Ch'+str(i+1)))
          self.ch4[i].setChecked(True)
          self.connect(self.ch4[i],SIGNAL('stateChanged(int)'),self.plotTrend)
          tt.addWidget(self.ch4[i],0,tt.columnCount ())
        self.trendList = QComboBox()
        for functionName in segmentProperties: 
          self.trendList.addItem(functionName)
        self.connect(self.trendList,SIGNAL('currentIndexChanged(int)'),self.updateTrendTab)
        tt.addWidget(self.trendList,0,tt.columnCount ())
        tt.addWidget(QLabel('from'),0,tt.columnCount ())
        self.index1=QSpinBox()
        self.index1.setMinimumWidth(80)
        self.index1.setValue(0)
        self.index1.setWrapping(True)
        tt.addWidget(self.index1,0,tt.columnCount ())
        tt.addWidget(QLabel('to'),0,tt.columnCount ())
        self.index2=QSpinBox()
        self.index2.setMinimumWidth(80)
        self.index2.setValue(0)
        self.index2.setWrapping(True)
        tt.addWidget(self.index2,0,tt.columnCount ())
        self.histo=QCheckBox('histogram')
        tt.addWidget(self.histo,0,tt.columnCount ())
        tt.addWidget(QLabel('# bins'),0,tt.columnCount ())
        self.bin=QSpinBox()
        self.bin.setMinimumWidth(80)
        self.bin.setValue(10)
        self.bin.setMaximum(100)
        tt.addWidget(self.bin,0,tt.columnCount ())
        for element in [self.index1,self.index2,self.bin]:
          self.connect(element ,SIGNAL('valueChanged(int)'),self.updateTrendTab)
        self.trendPlot = MatplotlibCanvas(width=myWidth, height=myHeight, dpi=mydpi)
        tt.addWidget(self.trendPlot,1,0,1,-1)
        self.connect(self.histo,SIGNAL('stateChanged(int)'),self.plotTrend)             
    
    def ButtonGUI(self):
      initializeButton = QPushButton('(Re)Init')
      calibrateButton = QPushButton('Calibrate')
      getConfigButton = QPushButton('Get Config')
      setConfigButton = QPushButton('Set Config')
      self.autoConfig = QCheckBox('auto',checked=False)
      temperatureButton = QPushButton('Temperature')
      self.acquireButton = QPushButton('Acquire && transfer')
      stopAcqButton=QPushButton('Stop acq.')
      self.transferAverage = QCheckBox('average only')
      self.runCheckbox = QCheckBox('Run',checked=False)
      plotButton = QPushButton('Plot')
      self.updatePlots = QCheckBox('auto',checked=True)
      saveDataButton = QPushButton('Save data...')
      saveFigButton = QPushButton('Save fig...')
      toDatamgrButton = QPushButton('->DataMgr')
      toIgorButton = QPushButton('->Igor')
      self.labelTemp=QLabel('    ')
      self.space=QLabel('    ')
      self.listen=QRadioButton('Listen to instrument');self.listen.setChecked(True);self.listen.setEnabled(True)
      # connections between buttons' clicked() signals and corresponding functions
      self.connect(initializeButton,SIGNAL('clicked()'),self.requestInitialize)
      self.connect(temperatureButton,SIGNAL('clicked()'),self.requestTemperature)
      self.connect(calibrateButton,SIGNAL('clicked()'),self.requestCalibrate)
      self.connect(setConfigButton,SIGNAL('clicked()'),self.requestSetBoardConfig)
      self.connect(getConfigButton,SIGNAL('clicked()'),self.requestGetBoardConfig)
      self.connect(self.acquireButton,SIGNAL('clicked()'),self.request1Acquire)
      self.connect(stopAcqButton,SIGNAL('clicked()'),self.requestStop)
      self.connect(self.runCheckbox,SIGNAL('stateChanged(int)'),self.runOscillo)
      self.connect(plotButton,SIGNAL('clicked()'),self.updatePlotTabs)
      self.connect(saveDataButton,SIGNAL('clicked()'),self.saveData)
      self.connect(saveFigButton,SIGNAL('clicked()'),self.saveFig)
      self.connect(toDatamgrButton,SIGNAL('clicked()'),self.toDatamanager)
      self.connect(toIgorButton,SIGNAL('clicked()'),self.sendToIgor)
      #layout
      self.buttonGrid1.addWidget(initializeButton)
      self.buttonGrid1.addWidget(calibrateButton)
      self.buttonGrid1.addWidget(getConfigButton)
      self.buttonGrid1.addWidget(setConfigButton)
      self.buttonGrid1.addWidget(self.autoConfig)
      self.buttonGrid1.addWidget(temperatureButton)
      self.buttonGrid1.addWidget(self.labelTemp)
      self.buttonGrid1.addWidget(self.space)
      self.buttonGrid1.addWidget(self.listen)
      self.buttonGrid1.addStretch()
      
      self.buttonGrid2.addWidget(stopAcqButton)
      self.buttonGrid2.addWidget(self.acquireButton)
      self.buttonGrid2.addWidget(self.transferAverage)
      self.buttonGrid2.addWidget(self.runCheckbox)      
      self.buttonGrid2.addWidget(plotButton)
      self.buttonGrid2.addWidget(self.updatePlots)
      self.buttonGrid2.addWidget(saveDataButton)
      self.buttonGrid2.addWidget(saveFigButton)
      self.buttonGrid2.addWidget(toDatamgrButton)
      self.buttonGrid2.addWidget(toIgorButton)
      self.buttonGrid2.addStretch()
    
    def MessageGUI(self):
      #The grid layout for delivering messages: messageGrid.
      self.messageGrid = QGridLayout()
      self.messageGrid.setVerticalSpacing(2)
      self.messageGrid.setHorizontalSpacing(10)
      self.errorString=QLabel('')
      self.messageString = QLineEdit('Hello :-)')
      self.messageString.setStyleSheet('color : red;');
      self.messageString.setReadOnly(True)
      self.mess=QLabel('Last message:')
      self.mess.setMaximumWidth(70)
      self.messageGrid.addWidget(self.mess,0,0)
      self.messageGrid.addWidget(self.messageString,0,1)

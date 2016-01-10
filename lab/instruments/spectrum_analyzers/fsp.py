import sys
import getopt
import time

from application.lib.instrum_classes import *
from application.lib.datacube import *

""" MODIFIED BY DV IN DEC 2014"""

class Trace:
  """
  A class storing trace data for the FSP.
  """
  def __init__(self):
    self.frequencies = []
    self.times = []
    self.magnitude = []
    self.timestamp = ''
    self.instrument = None 

# This is the Rhode & Schwarz FSP instrument.
# As a visa instrument, it is also an Instrument and a ThreadedDispatcher.
class Instr(VisaInstrument):

  """
  The Rhode & Schwarz FSP instrument class.
  """

  def initialize(self,visaAddress="TCPIP0::192.168.0.17::inst0",**kwargs):
    try:
      self.debugPrint('Initializing FSP')
      self._visaAddress = visaAddress
      self.lastTrace=Trace()
      self.transferIndex=0
    except:
      self.statusStr("An error has occured. Cannot initialize FSP.")
    
  def saveState(self,name):
    self.storeConfig(name)
    return name
    
  def restoreState(self,name):
    """ """
    self.loadConfig(name)
   
  def storeConfig(self,name = "default"):
    """
    Stores the instrument configuration in a file on the harddisk of the instrument.
    """
    self.write("MMEM:STOR:STAT 1,'%s'" % name)    
  
  def loadConfig(self,name = "default"):
    """
    Loads a given configuration file.
    """
    print "Restoring:",name
    self.write("MMEM:LOAD:STAT 1,'%s'" % name)
    
  def getConfig(self,name = "default"):
    """
    Transfers a given configuration file from the instrument.
    """
    currentDirectory = self.ask("MMEM:CDIR?")[1:-1]
    data = self.ask("MMEM:DATA? '%s%s.fsp'" % (currentDirectory,name))
    #Remove the GPIB header from the data. This header is of the form "#xyyyyy", where "x" indicates the number of digits "y" that follow it. 
    length = int(data[1])
    data = data[2+length:]
    return data

  #########################
  #  BASIC SETS AND GETS  #
  #########################

  def setReferenceLevel(self,level):
    """ """
    self.write("DISP:TRACE1:Y:RLEVEL %f" % level)
    
  def referenceLevel(self):
    """ """
    return float(self.ask("DISP:TRACE1:Y:RLEVEL?"))
  
  def getFrequency(self):
    """ """
    return float(self.ask('SENSE1:FREQUENCY:CENTER?'))/1e9
  
  def setFrequency(self,f):
    self.write('SENSE1:FREQUENCY:CENTER %f GHZ'%f)
    return self.getFrequency()

  def getCenterInGHz(self):
    """ """
    return self.getFrequency()

  def setCenterInGHz(self,*args):
    """ """
    return self.setFrequency(*args)
    
  def getSpanInGHz(self):
    """ """
    return float(self.ask('SENSE1:FREQUENCY:SPAN?'))/1e9

  def setSpanInGHz(self,span):
    self.write('SENSE1:FREQUENCY:SPAN %f GHZ'%span)
    return self.getSpanInGHz()

  def getStartInGHz(self):
    """Gets the start frequency in GHz."""
    return float(self.ask('SENSE1:FREQUENCY:START?'))/1e9

  def setStartInGHz(self,f):
    """Sets the start frequency in GHz."""
    self.write('SENSE1:FREQUENCY:START %f GHZ'%f)
    return self.getStartInGHz()

  def getStopInGHz(self):
    """Gets the stop frequency in GHz."""
    return float(self.ask('SENSE1:FREQUENCY:STOP?'))/1e9

  def setStopInGHz(self,f):
    self.write('SENSE1:FREQUENCY:STOP %f GHZ'%f)
    return self.getStopInGHz()
  
  def getResBWInHz(self):
      """ """
      return float(self.ask('BAND:RES?'))

  def setResBWInHz(self,resBandwidth='auto'):
      if type(resBandwidth) != type(str):
        resBandwidth=str(resBandwidth)+'HZ'
      self.write('BAND:RES '+resBandwidth)
      return self.getResBWInHz()

  def getVidBWInHz(self):
      """ """
      return float(self.ask('BAND:VID?'))

  def setVidBWInHz(self,videoBandwidth='auto'):
      if type(videoBandwidth) != type(str):
        videoBandwidth=str(videoBandwidth)+'HZ'
      self.write('BAND:VID '+resBandwidth)
      return self.getVidBWInHz()

  def getBandWidthInHz(self):
    """ """
    return (self.getResBWInHz,self.getVidBWInHz())

  def setBandWidthInHz(self,resBandwidth='auto',videoBandwidth='auto'):
    self.setResBWInHz(resBandwidth=resBandwidth)
    self.setVidBWInHz(videoBandwidth=videoBandwidth)
    return self.getBandWidthInHz()

  def getSweepTimeInSec(self):
    """ """
    return float(self.ask('SENSE1:SWEEP:TIME?'))

  def setSweepTimeInSec(self,st='AUTO'):
    """ """
    if not(isinstance(st,str)):
      st2=' '+str(st)+'s'
    else:
      st2=':'+st
    if st == 'AUTO' or st == 'auto':
      st2=str(st2)+' ON'
    msg="SENSE1:SWEEP:TIME"+st2
    self.write(msg)
    return self.getSweepTimeInSec()
  
  def getSweepCounts(self):
    """ """
    return int(self.ask('SWE:COUN?'))

  def setSweepCounts(self,sweepCounts=1):
    """ """
    self.write('SWE:COUN %i' %sweepCounts)
    return self.getSweepCounts()

  def getValueAtMarker(self):
    """ """
    return float(self.ask('CALC:MARK:Y?'))

  def getNumOfPoints(self):
    """ """
    return int(self.ask('SWE:POIN?'))

  def setNumOfPoints(self,n):
    """ """
    self.write('SENSE1:SWEEP:POINT '+str(n))
    return self.getNumOfPoints()

  def getSetup(self):
    """ """
    return {'centerInGHz':self.getFrequency(),'spanInGHz':self.getSpanInGHz(),'startInGHz':self.getStartInGHz(),'stopInGHz':self.getStopInGHz(),'resBWInHz':self.getResBWInHz(),'vidBWInHz':self.getVidBWInHz(),'NumOfPoints':self.getNumOfPoints(),'sweepTimeInSec':self.getSweepTimeInSec(),'sweepCount':self.getSweepCounts()}

  ######################
  #  GET TRACES BELOW  #
  ######################

  def getTrac(self,trace = 1):
    """
    Transfers immeditaly a trace from the FSP.
    Returns the trace as a list of two lists.
    For internal use only. USE getTrace() OR getTraceCube  INSTEAD.
    """
    if DEBUG: print "Getting trace..."
    freq_mode = self.ask("FREQ:MODE?")
    timedomain = False
    sweeptime = 0
    freqStart = 0
    freqStop = 0
    if freq_mode == 'FIX':
      #This is a time domain measurement.
      if DEBUG:
        print "Time domain measurement..."
      timedomain = True
      sweeptime = float(self.ask("SWE:TIME?"))
      if DEBUG: print "Sweeptime: %f " % sweeptime
    else:
      #This is a frequency domain measurement.
      freqStart = float(self.ask("FREQ:START?"))
      freqStop = float(self.ask("FREQ:STOP?"))
      if DEBUG: print "Frequency domain measurement from %f to %f" % (freqStart,freqStop)
    self.write("FORM ASC;TRAC? TRACE%d" % trace)
    trace = self.read()
    # self.write("INIT:CONT ON")# 20/03/2012 VS recoved Denis 30/01/2013
    values = trace.split(',')
    values = map(lambda x:float(x),values)
    if timedomain:
      self.lastTrace.frequencies=[]
      times=[i * sweeptime / len(values) for i in range(0,len(values))]
      self.lastTrace.times=times
      result = [times,values]
    else:
      self.lastTrace.times=[]
      frequencies=[ freqStart+ i * (freqStop-freqStart) / len(values) for i in range(0,len(values))]
      self.lastTrace.frequencies=frequencies
      result = [frequencies,values]
    self.transferIndex+=1
    return result

  def getTrace(self,trace = 1,waitFullSweep = False,timeout = 20,cubeOut=False):
    """
    If waitFullSweep=true, sets the instrument to single sweep mode, resets the sweep count, waits until the data acqusition finishes and transfers the data from the instrument.
    Otherwise gets the current trace immediately.
    By default, returns the trace as a list of two lists for historical reasons.
    USE KEYWORD ARGUMENT cubeOut=True TO RETURN A DATACUBE.   
    """
    if waitFullSweep:
      self.write('INIT:CONT OFF')
      self.write('INIT;*WAI')
      result = 0 
      cnt = 0
      #Check the status of the data acquisition operation.
      while True:
        try:
          result = int(self.ask('*OPC?'))
        except VisaIOError:
          pass
        if result == 1 or cnt > timeout*10:
          break
        cnt+=1
        time.sleep(0.1)
    result=self.getTrac(trace=trace)
    if not cubeOut:
      return result
    else:
      cube = Datacube('fspTrace-'+str(self.transferIndex))
      name="freq"
      if len(self.lastTrace.times) != 0: name='time'
      cube.createCol(name=name,values=result[0])
      cube.createCol(name="mag",values=result[1])
      return cube

  def getSingleTrace(self,**kwargs):
    """
    Equivalent to getTrace with keyword argument waitFullSweep = True.
    """
    return self.getTrace(waitFullSweep = True,**kwargs)
    

import sys,getopt,math
from numpy import *
from pyvisa import vpp43

from application.lib.instrum_classes import *
if 'lib.datacube' in sys.modules:
  reload(sys.modules['lib.datacube'])
from application.lib.datacube import Datacube


class VNATrace:

  def __init__(self):
    self.frequencies = []
    self.phase = []
    self.magnitude = []
    self.timestamp = ''
    self.instrument = None  

#This is the VNA instrument.
class Instr(VisaInstrument):

  #Initializes the instrument.
  def initialize(self,visaAddress = "GPIB::29",powerParams={}):
    print 'Initializing '+self.name()+' with adress ', visaAddress, ':'
    self._visaAddress = visaAddress
    try:
      #self.clearDevice()
      self.getID()
    except:
      print "ERROR: Cannot initialize instrument!"
    self._powerParams={'attenMin':0,'attenMax':60,'sourceMin':-20,'sourceMax':0,'offset':0} # everything in dBm
    self.setPowerParams(powerParams)

  def getID(self):
    return self.ask('*IDN?')

  def clearDevice(self):
    handle = self.getHandle()
    handle.timeout = 1
    cnt = 0
    handle.write("*CLS")
    while True:
      try:
        if cnt>100:
          return False
        if int(vpp43.read_stb(handle.vi)) & 128:
          return True
        time.sleep(0.1)
      except visa.VisaIOError:
        cnt+=1
    return False
    
  def powerParams(self):
    return self._powerParams

  def setPowerParams(self,newDict):
    for key in newDict:
      if key in self._powerParams: self._powerParams[key]=newDict[key]
    return self._powerParams

  def triggerReset(self):
    self.write("*CLS;TRS;")
    
  def setAttenuation(self,a):
    self.write("SA1 %f DB" % a)
    return self.attenuation()
    
  def attenuation(self):
    return float(self.ask("SA1?"))
  
  def setTotalPower(self,powerIndBm):           
    power=powerIndBm-self._powerParams['offset']
    attenMax=self._powerParams['attenMax']
    if self._powerParams['sourceMin']-attenMax<=power<=self._powerParams['sourceMax']-self._powerParams['attenMin']:
      atten,powe=divmod(power,-10)
      atten*=10
      if atten>attenMax:
        atten=attenMax
        powe=power+attenMax
      self.setAttenuation(atten)
      self.setPower(powe)
    else:
      raise NameError('Total power out of available range.')
    return self.totalPower()

  def totalPower(self):
    return self.power()-self.attenuation()+self._powerParams['offset']

  def setPower(self,power):
    self.write("PWR %f DB" % power)
    return self.power()
  
  def power(self):
    return float(self.ask("PWR?"))
  
  def startFrequency(self):
    return float(self.ask("SRT?"))

  def getStartInGHz(self):
      return self.startFrequency()/1e9
  
  def setStartFrequency(self,f):
    self.write("SRT %f GHZ" % f)
    return self.startFrequency()

  def setStartInGHz(self,f):
    return self.setStartFrequency(f)/1e9
    
  def stopFrequency(self):
    return float(self.ask("STP?"))

  def getStopInGHz(self):
      return self.stopFrequency()/1e9
  
  def setStopFrequency(self,f):
    self.write("STP %f GHZ" % f)
    return self.stopFrequency()

  def setStopInGHz(self,f):
    return self.setStopFrequency(f)
  
  def centerFrequency(self):
    return float(self.ask("CNTR?"))

  def getCenterInGHz(self):
      return self.centerFrequency()/1e9
  
  def setCenterFrequency(self,f):
    self.write("CNTR %f GHZ" % f)
    return self.centerFrequency()

  def setCenterInGHz(self,f):
    return self.setCenterFrequency(f)
  
  def spanFrequency(self):
    return float(self.ask("SPAN?"))

  def getSpanInGHz(self):
    return self.spanFrequency()/1e9
  
  def setSpanFrequency(self,f):
    self.write("SPAN %f GHZ" % f)
    return self.spanFrequency()

  def setSpanInGHz(self,f):
    return self.setSpanFrequency(f)

  def numberOfPoints(self):
    return int(self.ask("ONP"))

  def setNumberOfPoints(self,n):
    li=[51,101,201,401,801,1601]
    li2=list(abs(n-array(li)))
    n=li[li2.index(min(li2))]
    self.write("NP%i" % n)
    return self.numberOfPoints()
  
  def average(self):
    return bool(int(self.ask("AOF?")))
  
  def turnOnaver(self):
    self.write("AON")
    return self.average()
    
  def turnOffaver(self):
    self.write("AOF")
    return self.average()

  def setAverage(self,b):
      if b:
        return self.turnOnaver()
      else :
        return self.turnOffaver() 

  def numberOfAveraging(self):
    return int(float(self.ask("AVG?")))
  
  def setNumberOfAveraging(self,n):
    self.write("AVG %i" % n)
    return self.numberOfAveraging()

  def videoBW(self):
    return int(10**(float(self.ask("IFX?"))))

  def setVideoBW(self, bw):
    i=math.log10(bw)
    self.write("IF%i" % i)
    return self.videoBW()

  def electricalLength(self):
    self.write("RDA")
    return float(self.ask("RDD?"))

  def setCWFrequency(self,f):
    self.write("CWF %f GHZ" % f)
    return self.CWFrequency()

  def CW(self):
    return bool(int(self.ask('CWON?'))),float(self.ask('CWF?'))

  def setCWOn(self):
    self.write("CWON")

  def setCWOff(self):
    self.write("SWP")

  def setCW(self,on=True,freq=None):
    if on:
      if freq is not None:
        self.setCWFrequency(freq)
      else:
        self.setCWOn()
    else:
      self.setCWOff()
    return self.CW()
    
  def turnOnHold(self):
    self.write("HLD")
    
  def turnOnSweep(self):
    self.write("CTN")
    
  def turnOffRFOnHold(self):
    self.write("RH0")
    
  def keepOnRFOnHold(self):
    self.write("RH1")

  def getSetup(self):
      return {
      'power':self.totalPower(),\
      'centerInGHz':self.getCenterInGHz(),'spanInGHz':self.getSpanInGHz(),\
      'startInGHz':self.getStartInGHz(),'stopInGHz':self.getStopInGHz(),\
      'videoBW':self.videoBW(),'numOfPoints':self.numberOfPoints(),\
      'avgCount':self.numberOfAveraging(),'avgONOFF':self.average()}

  # marker functions

  def checkMarkerIndex(self,index):
    if index>=6:
      raise NameError('Marker index should be lower than 6.')

  def markerState(self,marker=1):
    self.checkMarkerIndex(marker)
    return int(self.ask('MR'+str(marker)+'?'))
    
  def markerOn(self,marker=1):
    self.checkMarkerIndex(marker)
    self.write('MR'+str(marker))
    return self.markerState(marker=marker)
    
  def markerOff(self,marker=1):
    self.checkMarkerIndex(marker)
    self.write('MO'+str(marker))
    return self.markerState(marker=marker)
  
  def markerX(self,marker=1):                  # position X in the unit of the X axis (frequency, power or time )
    self.checkMarkerIndex(marker)
    return float(self.ask('MK'+str(marker)+'?'))/1e9
    
  def markerSetX(self,x,unit='GHZ',marker=1) :    # position in number of points
    self.checkMarkerIndex(marker)
    self.write('MK'+str(marker)+' '+str(x)+' '+unit)
    return self.markerX(marker=marker)

  def getValuesAtMarker(self,marker=1,waitNewSweep=False):
    if waitNewSweep: self.write("TRS;WFS;")
    return [float(stri) for stri in self.ask("OM"+str(marker)).split(',')]

  def getMarkerXY(self,marker=1,waitNewSweep=False):
    return [self.markerX(marker=marker),self.getValuesAtMarker(marker=marker,waitNewSweep=waitNewSweep)]
          
  # getting traces

  def waitFullSweep(self):
    self.write("*CLS;HLD;TRS;WFS;")
    handle = self.getHandle()
    handle.timeout = 1
    cnt = 0
    while True:
      try:
        if cnt>100:
          return False
        time.sleep(1)
        status =  vpp43.read_stb(handle.vi)
        if int(status) & 128:
          return True
      except visa.VisaIOError:
        cnt+=1
        print sys.exc_info()
    return False              
               
  #Get a trace from the instrument and store it to a local array.
  def getTrace(self,waitFullSweep = False,timeOut = 1600,fromMemory=False):
    """ 
    Get a raw trace in the VNA, without correcting the data, except for internal attenuators.
    Get the memory instead of main trace if fromMemory=True.
    Restart a sweep and wait for its completion if fromMemory=False and waitFullSweep=True.
    FOR INTERNAL USE ONLY.
    USE INSTEAD getFreqMagPhase(waitFullSweep = False,fromMemory=False,timeOut=60,addedAttenuators=0,unwindPhase=False,subtractedSlope=None,deltaPhase=None,offset=None).
    """
    trace = Datacube('Spectrum')
    handle = self.getHandle()
    handle.timeout = timeOut
    if waitFullSweep:
      print "Getting trace...",
      # freqs = self.ask_for_values("HLD;TRS;WFS;fma;msb;OFV;") 2011/12 VS 
      self.write('TRS;WFS;')
    freqs = self.ask_for_values('fma;msb;OFV;')
    data = self.write('fma;msb;')
    if(fromMemory):
      data = self.ask_for_values('MEM;OFD;')
      self.write('DTM;')
    else: 
      data = self.ask_for_values('OFD;')
    if waitFullSweep:
      print "done."
    freqs.pop(0)
    data.pop(0)
    mag = []
    phase = []
    #If y length is twice the x length, we got phase and magnitude.
    if len(data) == 2*len(freqs):
      for i in range(0,len(data)):
        if i%2 == 0:	
          mag.append(data[i])
        else:
				 phase.append(data[i])
    else:
      mag = data
    att=self.attenuation()
    trace.setParameters( {'attenuation':att,'power':self.totalPower()})
    trace.createCol(name='freq',values=freqs)
    trace.createCol(name='mag',values=array(mag)+att)
    if len(phase) != 0: trace.createCol(name='phase',values=phase)
    return trace

  def getFullTrace(self,**kwargs):
    self.getTrace(waitFullSweep = True,**kwargs)
  
  def getFreqMagPhase(self,waitFullSweep=False,fromMemory=False,timeOut=60,addedAttenuators=0.,unwindPhase=False,subtractedSlope=None,deltaPhase=None,phaseOffset=None,phaseStart=None,phaseStop=None):
    """ 
    - Get a trace in the VNA
    - Correct amplitude for added attenuation.
    - Unwind phase, and/or remove slope, and/or impose a phase difference between last and first point, and/or add an offset to the phase, if requested.
    Get the memory instead of main trace if fromMemory=True.
    Restart a sweep and wait for its completion if fromMemory=False and waitFullSweep=True.
    """
    trace=self.getTrace(waitFullSweep = waitFullSweep,fromMemory=fromMemory,timeOut=timeOut)
    if addedAttenuators != 0:
      self.correctMag(trace,addedAttenuators=addedAttenuators)
    if unwindPhase or subtractedSlope is not None or deltaPhase is not None or phaseOffset is not None :
      self.correctPhase(trace,unwindPhase=unwindPhase,subtractedSlope=subtractedSlope,deltaPhase=deltaPhase,phaseOffset=phaseOffset,phaseStart=phaseStart,phaseStop=phaseStop)
    return trace

  def correctMag(self,traceCube,addedAttenuators=0.):
    if 'mag' in traceCube.names():
      traceCube.createCol(name='magCor',values=traceCube['mag']+addedAttenuators)
      params=traceCube.parameters()
      params['addedAtten']=addedAttenuators
      
  def correctPhase(self,traceCube,unwindPhase=False,subtractedSlope=None,deltaPhase=None,phaseOffset=None,phaseStart=None,phaseStop=None):
    traceCube.names()
    if 'phase' in traceCube.names():
      params=traceCube.parameters()
      params['unwind']=False
      for key in ['subtractedSlope','deltaPhase','phaseOffset']: params[key]=None
      phase=traceCube['phase']
      if unwindPhase:
        phase=self.unwind(phase,period=360)                                         # unwind phase if requested
        params['unwind']=True
      if subtractedSlope is not None:                                                     # flatten phase if requested
        freq=traceCube['freq']
        phase=phase-subtractedSlope*(freq-freq[0])                                  # flatten by slope subtraction has priority over imposing a the total delta jump
        params['subtractedSlope']=subtractedSlope
      elif deltaPhase is not None:                                                        # impose a the total delta jump
        phase=phase-(+phase[-1]-phase[0]-deltaPhase)/len(phase)*arange(len(phase))
        params['deltaPhase']=deltaPhase
      if phaseStart is not None:
        phaseOffset=phaseStart-phase[0]
      elif phaseStop is not None:
        phaseOffset=phaseStop-phase[-1]
      if phaseOffset is not None:
        phase=phase+phaseOffset
        params['phaseOffset']=phaseOffset    
      traceCube.createCol(name='phaseCor',values=phase)

  def unwind(self,li,period=360):
    """Unwind a list, tuple or 1D array initially defined on a circle with period period. Format is preserved."""
      
    def substract(li1,li2):
      """Subtraction li1-li2 between two lists, tuples or 1D arrays. Format is preserved."""
      result=array(li1)-array(li2)
      if isinstance(li1, list):   result=list(result)
      elif isinstance(li1, tuple):  result=tuple(result) 
      return result

    def rotateLeft(li,shift=1):
      """Rotate a list, tuple or 1st dimension of an array by shift positions to the left. Format is preserved."""
      shift=shift%len(li)
      result=concatenate((array(li)[shift:],array(li)[:shift]))
      if isinstance(li, list):    result=list(result)
      elif isinstance(li, tuple): result=tuple(result) 
      return result

    def derivList(li):
      """Discrete derivative of a list, tuple or 1D array.
      Format is preserved, but with an output length 1 unit below the input length."""
      return substract(rotateLeft(li),li)[:-1]

    def listIntegrate(li):
      """Discrete integration of a list, tuple or 1D array. Format is preserved."""
      for i in range(len(li))[1:]:
        li[i]+=li[i-1]
      return li

    def jump(x):
      dif=[abs(x-period),abs(x),abs(x+period)]
      return dif.index(min(dif))-1
  
    jumps=listIntegrate(map(jump,derivList(li)))
    jumps.insert(0,0.)
    result=array(jumps)*period+array(li)
    if isinstance(li, list):    result=list(result)
    elif isinstance(li, tuple): result=tuple(result)
    return result

  def saveState(self):
    print 'saving state'
    return self.getSetup()

  #-----------------------------------------------------------------------
  # Set center frequency or marker to Max or Min
  #-----------------------------------------------------------------------

  def extremum(self,target='max',waitFullSweep = False,**kwargs):
    traceCube=self.getTrace(waitFullSweep = waitFullSweep)
    x,y=traceCube['freq'],traceCube['mag']
    if target == 'max': target=max(y)
    else: target=min(y)
    pos=where(y == target)[0][0]
    return ((x[pos],y[pos]),pos+1)

  def centerAtExtremum(self,**kwargs):
    ((x0,y0),pos)=self.extremum(**kwargs)
    self.setCenterFrequency(x0*1e-9)
    return ((x0,y0),pos)
    
  def centerAtMax(self,**kwargs):
    return self.centerAtExtremum(target='max',**kwargs)

  def centerAtMin(self,**kwargs):
    return self.centerAtExtremum(target='min',**kwargs)

  def markerAtExtremum(self,target='max',marker=1,**kwargs):
    self.checkMarkerIndex(marker)
    self.write('MR1')
    if target == 'max':
      self.write('MMX')
    elif target == 'min':
      self.write('MMN')
    return self.getMarkerXY(marker=marker)

  def markerAtMax(self,**kwargs):
    return self.markerAtExtremum(target='max',**kwargs)

  def markerAtMin(self,**kwargs):
    return self.markerAtExtremum(target='min',**kwargs)




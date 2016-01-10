import sys
import getopt
import re
import struct
import math
import numpy
import scipy

from application.lib.instrum_classes import *
from application.helpers.instrumentsmanager import Manager
from application.lib.smartloop import *


from application.lib.datacube import Datacube

from macros.fit_functions import *
reload(sys.modules["macros.fit_functions"])
from macros.fit_functions import *

#This is a virtual instrument representing a Quantum Bit.
#This class provides convenience functions for setting the Qubit parameters and for
#making measurements of the Qubit state.
class Instr(Instrument):

  def parameters(self):
    return self._params

  def saveState(self,name):
    params = copy.deepcopy(self._params)
    return params

  def restoreState(self,state):
    self._params = state

  def initialize(self,jba, pulseGenerator):


    manager=Manager()
    if not hasattr(self,'_params'):
      print("reseting self._params dictionnary")
      self._params = dict()
      self._params['jba']=jba
      self._jba=manager.getInstrument(jba)
      self._params['pulseGenerator']=pulseGenerator
      self._pulseGenerator=manager.getInstrument(pulseGenerator)
      self.gaussianParameters={'sigma':10,'maxHeight':1,'cutOff':2}

  def measureT1(self,delays,data=None,t1Parameters=None, dataParameters=None):
    """
    Measure a T1, will use what is in dictionnary if power/frequency/useCalibration/nLoops are not set
    Fit and save the period in the Qubit dictionnary under T1
    Return data and T1
    """
    if dataParameters is None:
      dataParameters=dict()
      dataParameters['addToDataManager']=True
      dataParameters['save']=True
    print t1Parameters
    if t1Parameters is None:
      if self._params.has_key('t1Parameters'):
        t1Parameters=self._params['t1Parameters']
      else: raise Exception("Unable to find rabi parameters... Exiting... ")

    useCalibration=t1Parameters['useCalibration']
    frequency=t1Parameters['frequency']
    if frequency == "f01":frequency=self.frequency01()
    print frequency 

    power=t1Parameters['power']
    nLoops=t1Parameters['nLoops']
    duration=t1Parameters['duration']
    if duration == "rabi":duration=self._params['piRabiTime']


    if t1Parameters.has_key('remember'):
      if t1Parameters['remember']: self._params['t1Parameters']=t1Parameters

    if self._params.has_key('offsetDelay'):
      offsetDelay=self._params['offsetDelay']
    else: offsetDelay=20

    if data is None:
      data=Datacube("T1 Measurement")
      if dataParameters['addToDataManager']:data.toDataManager()

    if power != "stay":self._pulseGenerator._MWSource.setPower(power)
   
    if power != "stay":self._pulseGenerator._MWSource.setPower(power)
  
    for delay in delays:

      self._pulseGenerator.clearPulse()
      self._pulseGenerator.generatePulse(duration=duration, frequency=frequency, DelayFromZero=10000-delay-duration-offsetDelay,useCalibration=False)
      self._pulseGenerator.sendPulse()

      result=self._jba.measure(nLoops=nLoops,fast=True)[0]
      data.set(**result)
      data.set(delay=delay)
      data.commit()
    
    columnName="b%i"%self._jba.bit
    [y0,dy,T1],yfit=fitT1(data['delay'],data[columnName])
    data.createColumn("fit",yfit)
    
    self._params['T1']=T1


    return data,T1

  def measureRabi(self,durations,data=None,rabiParameters=None, dataParameters=None):
    """
    Measure a rabi, will use what is in dictionnary if power/frequency/useCalibration/nLoops are not set
    Fit and save the period in the Qubit dictionnary under piRabiTime
    Return the datacube and rabiPeriod
    """

    if dataParameters is None:
      dataParameters=dict()
      dataParameters['addToDataManager']=True
      dataParameters['save']=True

    if rabiParameters is None:
      if self._params.has_key('rabiParameters'):
        rabiParameters=self._params['rabiParameters']
      else: raise Exception("Unable to find rabi parameters... Exiting... ")

    useCalibration=rabiParameters['useCalibration']
    frequency=rabiParameters['frequency']
    if frequency == "f01":frequency=self.frequency01()

    power=rabiParameters['power']
    nLoops=rabiParameters['nLoops']

    if rabiParameters.has_key('remember'):
      if rabiParameters['remember']: self._params['rabiParameters']=rabiParameters

    if self._params.has_key('offsetDelay'):
      offsetDelay=self._params['offsetDelay']
    else: offsetDelay=20

    if data is None:
      data=Datacube("Rabi %s dBm"%power)
      if dataParameters['addToDataManager']:data.toDataManager()


    if power != "stay":self._pulseGenerator._MWSource.setPower(power)
    self._pulseGenerator._MWSource.turnOn()
    for duration in durations:
      self.clearPulses()
      self.generateRabiPulse(duration=duration, frequency=frequency, offsetDelay=offsetDelay,useCalibration=rabiParameters['useCalibration'])
      result=self._jba.measure(nLoops=nLoops,fast=True)[0]
      data.set(**result)
      data.set(duration=duration)
      data.commit() 

    #Fit
    try:
      columnName="b%i"%self._jba.bit
      period= estimatePeriod(data['duration'],data[columnName])
      [y0,dy,piRabi,t10],yfit=fitRabi(data['duration'],data[columnName],period=period)
      data.createColumn("%sfit"%columnName,yfit)
    except:
      print 'fit error'
      piRabi=0
    if dataParameters['save']:data.savetxt()
    self._params['piRabiTime']=piRabi

    return data,piRabi

  def measureRabiArea(self,areas,data=None,rabiParameters=None, dataParameters=None):
    """
    Measure a rabi, will use what is in dictionnary if power/frequency/useCalibration/nLoops are not set
    Fit and save the period in the Qubit dictionnary under piRabiTime
    Return the datacube and rabiPeriod
    """

    if dataParameters is None:
      dataParameters=dict()
      dataParameters['addToDataManager']=True
      dataParameters['save']=True

    if rabiParameters is None:
      if self._params.has_key('rabiParameters'):
        rabiParameters=self._params['rabiParameters']
      else: raise Exception("Unable to find rabi parameters... Exiting... ")

    useCalibration=rabiParameters['useCalibration']
    frequency=rabiParameters['frequency']
    if frequency == "f01":frequency=self.frequency01()

    nLoops=rabiParameters['nLoops']

    if rabiParameters.has_key('remember'):
      if rabiParameters['remember']: self._params['rabiParameters']=rabiParameters

    if rabiParameters.has_key('maxHeight'):
      maxHeight=rabiParameters['maxHeight']

    if rabiParameters.has_key('shape'):
      shape=rabiParameters['shape']

    if self._params.has_key('offsetDelay'):
      offsetDelay=self._params['offsetDelay']
    else: offsetDelay=0

    if data is None:
      data=Datacube("Rabi")
      if dataParameters['addToDataManager']:data.toDataManager()


    self._pulseGenerator._MWSource.turnOn()
    for area in areas:


      self.clearPulses()
      self.generateRabiPulseArea(area=area, frequency=frequency,maxHeight=maxHeight, offsetDelay=offsetDelay,useCalibration=rabiParameters['useCalibration'],shape=shape)
      result=self._jba.measure(nLoops=nLoops,fast=True)[0]
      data.set(**result)
      data.set(area=area)
      data.commit() 

    #Fit
    try:
      columnName="b%i"%self._jba.bit
      period= estimatePeriod(data['duration'],data[columnName])
      [y0,dy,piRabi,t10],yfit=fitRabi(data['duration'],data[columnName],period=period)
      data.createColumn("%sfit"%columnName,yfit)
    except:
      print 'fit error'
      piRabi=0
    if dataParameters['save']:data.savetxt()
    self._params['piRabiTime']=piRabi

    return data,piRabi

  def measureSpectroscopy(self,frequencies, data=None, spectroscopyParameters=None,dataParameters=None):
    """
    Measure a spectroscopy
    Fit
    Return the datacube and centerFrequency
    """

    if spectroscopyParameters is None:
      if self._params.has_key(spectroscopyParameters):
        spectroscopyParameters=self._params['spectroscopyParameters']
      else:
        raise Exception("No spectroscopy parameters found... Exiting...")

    if dataParameters is None:
      dataParameters=dict()
      dataParameters['addToDataManager']=True
      dataParameters['save']=True

    if spectroscopyParameters.has_key('remember'):self._params['spectroscopyParameters']=spectroscopyParameters

    useCalibration=spectroscopyParameters['useCalibration']
    nLoops=spectroscopyParameters['nLoops']
    duration=spectroscopyParameters['duration']
    if spectroscopyParameters.has_key('power'): self._pulseGenerator._MWSource.setPower(spectroscopyParameters['power'])
    amplitude = spectroscopyParameters['amplitude'] if spectroscopyParameters.has_key('amplitude') else 0
    offsetDelay = spectroscopyParameters['offsetDelay'] if spectroscopyParameters.has_key('offsetDelay') else (self._params['offsetDelay'] if self._params.has_key('offsetDelay') else 20)


    if data is None:
      data=Datacube("Spectroscopy measurement")
      if dataParameters['addToDataManager']:data.toDataManager()





    first=True
    for frequency in frequencies:
      self._pulseGenerator._MWSource.setFrequency(frequency)
      if first: # i.e. generate a rabi pulse on the AWG only the first time (no need to re-generate an AWG pulse every time)
        self._pulseGenerator.pulseList=[]
        self.generateRabiPulse(duration=duration,amplitude=amplitude,offsetDelay=offsetDelay,useCalibration=useCalibration,frequency=frequency)
        first=False


      time.sleep(0.1)
      data.set(frequency=frequency)
      data.set(**self._jba.measure(nLoops=nLoops,fast=True)[0])
      data.commit()

    try:
      columnName="b%i"%self._jba.bit
      [dy,f0,df,y0],yfit=fitLorentzian(data['frequency'],data[columnName],1)
      data.createColumn(columnName+"fit",yfit)
    except:
      print "fitting error"
      [dy,f0,df,y0]=[0]*4

    if dataParameters['save']:data.savetxt()
    data.setParameters(Manager().saveState('currentState'))

    return data, f0

  def setFrequency01(self,f01,accuracy=7):
    """
    Set the input frequency under self._params['f01'] with given accuracy (round)
    """
    self._params['frequency01']=round(f01,6)

  def frequency01(self):
    return self._params['frequency01']

  def rabiPeriod(self):
    try:
      return self._params["rabiPeriod"]
    except:
      return 0


  def setRabiPeriod(self,period):
    self._params["rabiPeriod"]=period

  def clearPulses(self):
    self._pulseGenerator.clearPulse()

  def rabiArea(self):
      return self._params["rabiArea"]

  def setRabiArea(self, area):
    self._params["rabiArea"]=float(area)

  def rabiAmplitude(self, amp=None):
    if amp is not None:
      self._params["amplitude"]=amp
      return amp
    return self._params['amplitude'] if self._params.has_key('amplitude') else 1
    
  def rabiOffset(self, offsetDelay=None):
    if offsetDelay is not None:
      self._params["offsetDelay"]=offsetDelay
      return offsetDelay
    return self._params['offsetDelay'] if self._params.has_key('offsetDelay') else 0
    


  def generateRabiPulse(self,duration=None,amplitude=None,offsetDelay=None,useCalibration=False,clear=True,frequency=None):
    if frequency is None:frequency=self.frequency01()
    if duration is None:duration=self.rabiPeriod()
    if clear:self._pulseGenerator.pulseList=[]
    if amplitude is None: amplitude=self.rabiAmplitude()
    if offsetDelay is None: offsetDelay=self.rabiOffset()

    self._pulseGenerator._MWSource.turnOn()
    self._pulseGenerator.generatePulse(duration=duration,amplitude=amplitude, frequency=frequency, DelayFromZero=10000-duration-offsetDelay,useCalibration=useCalibration)
    self._pulseGenerator.sendPulse()

  def generateRabiPulseArea(self,area=None,maxHeight=None,offsetDelay=None,useCalibration=True,frequency=None,shape=None,clear=True,phase=0):
    if frequency is None:frequency=self.frequency01()
    if area is None:duration=self.rabiArea()
    if shape is None:shape='square'
    if maxHeight is None: maxHeight=self.rabiAmplitude()
    if offsetDelay is None: offsetDelay=self.rabiOffset()
    sigma=self.gaussianParameter('sigma')
    cutOff=self.gaussianParameter('cutOff')


    if clear:self._pulseGenerator.pulseList=[]
    if shape == 'gaussian':
      self._pulseGenerator.addPulse(generatorFunction="gaussianSlopePulse",frequency=frequency,end=10000-offsetDelay,sigma=sigma,maxHeight=maxHeight,cutOff=cutOff,area=area,applyCorrections=useCalibration,phase=phase)
    elif shape == 'square':
      self._pulseGenerator.addPulse(generatorFunction="square",frequency=frequency,amplitude=maxHeight,start=10000-area/maxHeight-offsetDelay, stop=10000-offsetDelay, applyCorrections=useCalibration,phase=phase)
    else: print "ERROR"
    print self._pulseGenerator.pulseList
    self._pulseGenerator.preparePulseSequence()
    self._pulseGenerator.sendPulseSequence()

  def measure(self, data,nLoops=None):
    if nLoops is None:
      nLoops = self._nLoops if hasattr(self,'_nLoops') else 10
    data.set(**self._jba.measure(nLoops=nLoops,fast=True)[0])
    data.commit()


  def generateRabiPulseAreaDerivative(self,area=None,maxHeight=None,offsetDelay=None,useCalibration=False,frequency=None,shape=None,clear=True,phase=0,coefficient=1.):
    if frequency is None:frequency=self.frequency01()
    if area is None:duration=self.rabiArea()
    if shape is None:shape='square'
    if offsetDelay is None: offsetDelay=self.rabiOffset()

    sigma=self.gaussianParameter('sigma')
    print sigma
    if maxHeight is None:maxHeight=self.gaussianParameter('maxHeight')
    cutOff=self.gaussianParameter('cutOff')


    if clear:self._pulseGenerator.pulseList=[]
    if shape == 'gaussian':
      self._pulseGenerator.addPulse(generatorFunction="gaussianSlopePulseDerivative",frequency=frequency,end=10000-offsetDelay,sigma=sigma,maxHeight=maxHeight,cutOff=cutOff,area=area,applyCorrections=useCalibration,phase=phase,coefficient=coefficient)
    elif shape == 'square':
      self._pulseGenerator.addPulse(generatorFunction="square",frequency=frequency,amplitude=maxHeight,start=10000-area/maxHeight-offsetDelay, stop=10000-offsetDelay, applyCorrections=useCalibration,phase=phase)
    else: print "ERROR"
    print self._pulseGenerator.pulseList
    self._pulseGenerator.preparePulseSequence()
    self._pulseGenerator.sendPulseSequence()

  def measure(self, data,nLoops=20):
    data.set(**self._jba.measure(nLoops=nLoops,fast=True)[0])
    data.commit()

  def gaussianParameter(self,obj):
    return self.gaussianParameters[obj]

  def setGaussianParameter(self,obj, value):
    self.gaussianParameters[obj]=value

  def generateRotation(self, mag, angle, offsetDelay,clear=False, frequency=None):
    area=self.rabiArea()*mag/math.pi
    print "area =" , area
    self.generateRabiPulseArea(area=area,offsetDelay=offsetDelay,useCalibration=True,shape='gaussian',clear=clear,phase=angle,frequency=frequency)
    self.generateRabiPulseAreaDerivative(area=area,offsetDelay=offsetDelay,useCalibration=True,shape='gaussian',clear=False,phase=angle-math.pi/2,frequency=frequency,coefficient=self.dragCoef())
#    self.generateRabiPulseArea(area=area,offsetDelay=offsetDelay, phase=angle,shape='gaussian',clear=clear)

  def setDragCoef(self,coef):
    self._params['dragCoef']=coef
  def dragCoef(self):
    return self._params['dragCoef']

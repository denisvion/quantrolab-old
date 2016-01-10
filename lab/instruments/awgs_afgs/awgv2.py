import sys,ctypes,getopt,re,struct,time,numpy

"""
.. module:: useful_1
   :platform: Unix, Windows
   :synopsis: A useful module indeed.

.. moduleauthor:: Andrew Carter <andrew@invalid.com>

Modified DV Feb 2015.
"""

from application.lib.instrum_classes import VisaInstrument
#from application.lib.swig.tools import numerical

class Waveform:

    def __init__(self):
      """
      this is the doc string for the init method...
      """
      self._name = None
      self._data = None
      self._markers = None
      self._length = None
      self._format = None
      self._rawdata = None
      
class Sequence:

    def __init__(self):
      """
      this is the doc string for the init method...
      """
      self._length = None
      
class AwgException(Exception):
  pass

class Instr(VisaInstrument):

  """
  The Tektronix AWG5xxx instrument.
  """
  # initialization, storing and loading states

  def initialize(self,visaAddress = "TCPIP0::192.168.0.3::inst0",waitTime = 0):
    """
    Initializes the AWG.
    """
    try:
      self.waveforms = []
      self._waitTime = waitTime
      self._markersPerChannel=2
      self._visaAddress = visaAddress
      print "Initializing AWG with address %s" % visaAddress
    except:
      self.statusStr("An error has occured. Cannot initialize %s." % self._name)     
  
  def parameters(self):
    """
    Returns all relevant AWG parameters.
    """
    params = dict()
    params["runMode"] = self.runMode()
    params["repetitionRate"] = self.repetitionRate()
    params["channels"] = []
    params["clockSource"] = self.clockSource()
    params["triggerInterval"] = self.triggerInterval()
    for i in [1,2,3,4]:
      channelParams = dict()
      channelParams["high"] = self.high(i)
      channelParams["low"] = self.low(i)
      channelParams["amplitude"] = self.amplitude(i)
      channelParams["offset"] = self.offset(i)
      channelParams["skew"] = self.skew(i)
      channelParams["function"] = self.function(i)
      channelParams["waveform"] = self.waveform(i)
      channelParams["phase"] = self.phase(i)
      channelParams["dac_resolution"] = self.DACResolution(i)
      params["channels"].append(channelParams)
    return params

  
  def loadSetup(self,name):
    """
    Loads a given setup file (.awg).
    """
    self.debugPrint('in '+self.name()+'.loadSetup(name) with name='+name)
    self.write("AWGControl:SRestore \"%s\"" % name) # be careful with "" chars
    for i in range(1,self.channels()+1):
      self.setState(i,True)
    
  def saveSetup(self,name):
    """
    Saves the current instrument configuration to a setup file.
    """
    self.debugPrint('in '+self.name()+'.saveSetup(name) with name='+name)
    self.write("AWGControl:SSave \"%s\"" % name)

  def setups(self):
    """
    Returns a list of all available setups.
    """
    self.debugPrint('in '+self.name()+'.setups()')
    setups = []
    string = self.ask("MMemory:CATALOG?")
    result = re.match(r'^\d+\,\d+\,(.*)$',string)
    filestr = result.groups(0)[0]
    files = re.findall(r'\,?\"(.*?)\,(.*?)\,(.*?)\"',filestr)
    for filestr in files:
      if re.search(r'\.awg$',filestr[0],re.I):
        setups.append(filestr[0])
    return setups
    
  def state(self,channels): # Dangerous programming. State is already a mehtod of the Instrument class that does something else
    """
    Returns the output state of channels of the instrument.
      - channels is a single channel index or a list of channel index
    """
    isIterable=hasattr(channels, '__iter__')
    if not isIterable:  channels=[channels]
    states=[]
    for channel in channels:
      states.append(self.ask("OUTPUT%d:STATE?" % channel))
    if not isIterable:
      states=states[0]
    return states
       
  def setState(self,channels,states): # Dangerous programming. State is already a mehtod of the Instrument class that does something else
    """
    Sets the output state of channels in the instrument.
      - channels can be a single channel or a list of channel indices lower than the number of channels.
      - states can be a single boolean or a list of booleans corresponding to the channels in channels
    """
    hasattr(channels, '__iter__')
    if not hasattr(channels, '__iter__'):  channels=[channels]
    if not hasattr(states, '__iter__'): states=[states]*len(channels)
    max= self.channels()
    for channel,state in zip(channels,states):
      if channel <= max:
        buf = "OFF"
        if state == True:
          buf = "ON"
        self.write("OUTPUT%d:STATE %s" % (channel,buf))
    return self.state(range(1,1+self.channels()))

  # start stop functions

  def runAWG(self):
    """
    Starts the AWG.
    """
    self.write("AWGControl:RUN:IMM")
    
  def stopAWG(self):
    """
    Stops the AWG.
    """
    self.write("AWGControl:STOP:IMM")

  def startAllChannels(self):
    """
    Start all the channels
    """
    return self.state(range(1,1+self.channels()))

  # information functions about fixed AWG parameters

  def channels(self):
    """
    Returns the number of channels of the instrument.
    """
    return int(self.ask("AWGControl:CONFIGURE:CNUMBER?"))

  def maxPoints(self):
    """
    Returns the maximum number of points per waveform.
    """
    return 20000

  def DACResolution(self,channel):
    """
    Returns the DAC resolution of the AWG.
    """
    return int(self.ask("SOURCE%d:DAC:RES?" % channel))
    
  def setDACResolution(self,channel,resolution):
    """
    Sets the DAC resolution of the AWG.
    """
    self.write("SOURCE%d:DAC:RES %d" % (channel,int(resolution)))

  # Overall timing 

  def clockSource(self):
    """
    Returns the value of the clock:source parameter.
    """
    return self.ask("AWGControl:CLOCK:SOURCE?")
  
  def triggerInterval(self):
    """
    Returns the trigger interval
    """
    return float(self.ask("TRIG:TIM?"))
    
  def setTriggerInterval(self,interval):
    """
    Returns the trigger interval
    """
    self.write("TRIG:TIM %f" % interval)

  def setRepetitionRate(self,rate):
    """
    Sets the repetition rate of the AWG.
    """
    self.write("AWGControl:RRate %f" % rate)
    
  def repetitionRate(self):
    """
    Returns the repetition rate of the AWG.
    """
    return float(self.ask("AWGControl:RRate?"))
  
  def setRunMode(self,mode):
    """
    Sets the run mode of the AWG. 
    options: CONT, TRIG, GAT, SEQ
    """
    self.write("AWGControl:RMODE %s" % mode) 
    
  def runMode(self):
    """
    Returns the run mode of the AWG.
    """
    return self.ask("AWGControl:RMODE?")

  # Global waveform timing and phase control

  def setSamplingTime_ns(self,time):
    """
    Set and return the sampling time in ns
    """
    return self.setSamplingTime(time*1e-9)*1e9

  def setSamplingTime(self,time):
    """
    Set and return the sampling time in s
    """
    freq=1/time
    self.write("SOUR1:FREQ "+str(freq))
    return self.samplingTime()

  def samplingTime_ns(self):
    """
    return the sampling time in ns
    """
    return self.samplingTime()*1e9
  
  def samplingTime(self):
    """
    return the sampling time in s
    """
    return 1./float(self.ask("SOUR1:FREQ?"))

  def phase(self,channel):
    """
    Returns the phase of a given channel.
    """
    return float(self.ask("SOURCE%d:PHASE?" % channel))
    
  def setPhase(self,channel,phase):
    """
    Sets the phase of a given channel.
    """
    self.write("SOURCE%d:PHASE:ADJUST %f" % phase)

  # Vertical control: amplitude and offset

  def amplitude(self,channel):
    """
    Returns the amplitude of a given channel.
    """
    return float(self.ask("SOURCE%d:VOLTAGE:LEVEL:IMMEDIATE:AMPLITUDE?" % channel))

  def offset(self,channel):
    """
    Returns the offset of a given channel.
    """
    return float(self.ask("SOURCE%d:VOLTAGE:LEVEL:IMMEDIATE:OFFSET?" % channel))

  # Waveform and marker generation
    
  def writeIntData(self,values,markers,useC = False):
    """
    Writes integer data to a string.
    """    
    if useC:
      valuesInt = numpy.zeros(len(values),dtype = numpy.ushort)
      markersInt = numpy.zeros(len(markers),dtype = numpy.uint8)
  
      valuesInt[:] = values[:]
      markersInt[:] = markers[:]

      buf = ctypes.create_string_buffer(len(valuesInt)*2)
      numerical.awg_pack_int_data(len(valuesInt),valuesInt.ctypes.data,markersInt.ctypes.data,ctypes.addressof(buf))
      return buf.raw
    else:
      output = ""
      for i in range(0,len(values)):
        marker = int(markers[i])
        value = int(values[i])
        output+=struct.pack("<H",((marker & 3) << 14) + (value & (0xFFFF >> 2)))
      return output
    
  def loadRealWaveform(self,realWaveform, channel=1, markers = None,waveformName='ch1'):
    """
    Loads a waveform and 2 marker waveforms into the AWG file.
    Input waveform 'realWaveform' should be encoded between -1 and 1 (and will be converted in the range 0, 2^14-1 = 16383)
    """
    waveform = numpy.zeros(len(realWaveform))
    waveform[:] = numpy.real(realWaveform)
    if max(abs(waveform))>1:
      print self.name(), " warning: requested pulse not in range [-1,1] => waveform will be truncated."
      def truncate(x):
        if x>1: return 1
        elif x<-1: return -1
        else: return x
      waveform[:]=map(truncate,waveform)
    if markers is None:
      markers=numpy.zeros(len(waveform),dtype=numpy.int8)
      markers[:10000]=3
    data = self.writeIntData((waveform+1.0)/2.0*((1<<14)-1),markers)
    self.createWaveform(waveformName,data,"INT")
    self.setWaveform(channel,waveformName)
    return len(data)
    
  def listRealWaveform(self,realWaveform, markers = None,waveformName='ch1'):
    """
    Loads a waveform and 2 marker waveforms into the AWG file.
    """
        
    waveform = numpy.zeros(len(realWaveform))
    waveform[:] = numpy.real(realWaveform)
           
    if markers is None:
      markers=numpy.zeros(len(waveform),dtype=numpy.int8)
      markers[:10000]=3
    data = self.writeIntData((waveform+1.0)/2.0*((1<<14)-1),markers)
    self.createWaveform(waveformName,data,"INT")
    return len(data)
        
  def writeRealData(self,values,markers,useC=False):
    """
    Writes real-valued data to a string.
    """
    output = ""
    #Fast code that calls a C++ function to encode the data...

    valuesFloat = numpy.zeros(len(values),dtype = numpy.float32)
    markersInt = numpy.zeros(len(markers),dtype = numpy.uint8)

    valuesFloat[:] = values[:]
    markersInt[:] = markers[:] << 6

    buf = ctypes.create_string_buffer(len(valuesFloat)*5)
    if useC:
      numerical.awg_pack_real_data(len(valuesFloat),valuesFloat.ctypes.data,markersInt.ctypes.data,ctypes.addressof(buf))
      return buf.raw
    else:
      for i in range(0,len(values)):
        marker = float(markers[i])
        value = float(values[i])
        output+=struct.pack("<f",((marker & 3) << 14) + (value & (0xFFFF >> 2)))
      return output 
    
  def setWaveform(self,channel,name):
    """
    Sets the waveform for a given channel.
    """
    self.write("SOURCE%d:WAVEFORM \"%s\"" % (channel,name))
    
  def waveform(self,channel):
    """
    Returns the waveform of a given channel.
    """
    return self.ask("SOURCE%d:WAVEFORM?" % channel)[1:-1]
      
  def function(self,channel):
    """
    Returns the function of a given channel.
    """
    return self.ask("SOURCE%d:FUNCTION:USER?" % channel)[1:-1]
    
  def setFunction(self,channel,name):
    """
    Sets the function of a given channel.
    """
    self.write("SOURCE%d:FUNCTION:USER \"%s\"" % name)
      
  def setSkew(self,channel,time):
    """
    Sets the skew time of a given channel.
    """
    self.write("SOURCE%d:SKEW %d ps" % (channel,int(time)))
    
  def skew(self,channel):
    """
    Returns the skew time of a given channel.
    """
    return float(self.ask("SOURCE%d:SKEW?" % channel))
      
  def setLow(self,channel,voltage):
    """
    Sets the low voltage of a given channel.
    """
    self.write("SOURCE%d:VOLTAGE:LEVEL:IMMEDIATE:LOW %f" % (channel,voltage))

  def setHigh(self,channel,voltage):
    """
    Sets the high voltage of a given channel.
    """
    self.write("SOURCE%d:VOLTAGE:LEVEL:IMMEDIATE:HIGH %f" % (channel,voltage))

  def setAmplitude(self,channel,voltage):
    """
    Sets the amplitude of a given channel.
    """
    self.write("SOURCE%d:VOLTAGE:LEVEL:IMMEDIATE:AMPLITUDE %f" % (channel,voltage))
    
  def setOffset(self,channel,voltage):
    """
    Sets the offset of a given channel.
    """
    self.write("SOURCE%d:VOLTAGE:LEVEL:IMMEDIATE:OFFSET %f" % (channel,voltage))

  def low(self,channel):
    """
    Returns the low voltage of a given channel.
    """
    return float(self.ask("SOURCE%d:VOLTAGE:LEVEL:IMMEDIATE:LOW?" % channel))

  def high(self,channel):
    """
    Returns the high voltage of a given channel.
    """
    return float(self.ask("SOURCE%d:VOLTAGE:LEVEL:IMMEDIATE:HIGH?" % channel))

  def markerLow(self,channel,marker):
    """"""
    return float(self.ask("SOURCE%d:MARKER%d:VOLTAGE:LEVEL:IMMEDIATE:LOW?" % (channel,marker)))

  def markerHigh(self,channel,marker):
    """"""
    return float(self.ask("SOURCE%d:MARKER%d:VOLTAGE:LEVEL:IMMEDIATE:HIGH?" % (channel,marker)))

  def setMarkerHigh(self,channel,marker,voltage):
    """"""
    self.write("SOURCE%d:MARKER%d:VOLTAGE:LEVEL:IMMEDIATE:HIGH %f" % (channel,marker,voltage))

  def setMarkerLow(self,channel,marker,voltage):
    """"""
    self.write("SOURCE%d:MARKER%d:VOLTAGE:LEVEL:IMMEDIATE:LOW %f" % (channel,marker,voltage))

  # Convenient functions for querying the marker values:

  def marker1High(self,channel):
    """"""
    return self.markerHigh(channel,1)

  def marker1Low(self,channel):
    """"""
    return self.markerLow(channel,1)

  def marker2High(self,channel):
    """"""
    return self.markerHigh(channel,2)

  def marker2Low(self,channel):
    """"""
    return self.markerLow(channel,2)

  def setMarker1High(self,channel,voltage):
    """"""
    return self.setMarkerHigh(channel,1,voltage)

  def setMarker1Low(self,channel,voltage):
    """"""
    return self.setMarkerLow(channel,1,voltage)

  def setMarker2High(self,channel,voltage):
    """"""
    return self.setMarkerHigh(channel,2,voltage)

  def setMarker2Low(self,channel,voltage):
    """"""
    return self.setMarkerLow(channel,2,voltage)
    
  def writeMarkers(self,markers):
    """
    Writes marker data to a string.
    """
    output = ""
    for i in range(0,len(markers)):
      marker = int(markers[i])
      output+=struct.pack("B",marker << 6) 
    return output
    
  def readMarkers(self,data):
    """
    Reads marker data from a string.
    """
    markers = []
    for j in range(0,len(data)):
      marker = int(struct.unpack('B',data[j])[0]) >> 6
      markers.append(marker)
    return (numpy.array(markers))
    
  def readRealData(self,data):
    """
    Reads real-valued data from a string.
    """
    values = []
    markers = []
    for j in range(0,len(data)/5):
      value = struct.unpack('f',data[j*5:j*5+4])[0]
      values.append(float(value))
      marker = int(struct.unpack('B',data[j*5+4:j*5+5])[0])
      markers.append(marker)
    return (numpy.array(values),numpy.array(markers))
  
  def readIntData(self,data):
    """
    Reads integer data from a string.
    """
    values = []
    markers = []
    for j in range(0,len(data)/2):
      bytes = struct.unpack('H',data[j*2:j*2+2])[0]
      value = (bytes >> 6) & 0xFF 
      values.append(value)
      markers.append(bytes >> 14)
    return (numpy.array(values),numpy.array(markers))

  def deleteWaveform(self,name):
    """
    Deletes a given waveform.
    """
    self.write("WLIST:WAVEFORM:DELETE \"%s\"" % (name))
    
  def createRawWaveform(self,name,values,markers,wavetype):
    """
    Creates a waveform using a set of values and markers.
    """
    if wavetype == 'INT':
      data = self.writeIntData(values,markers)
    else:
      data = self.writeRealData(values,markers)
    return self.createWaveform(name,data,wavetype)

  def deleteWaveform(self,name):
    if name == 'ALL':
      self.write("WLIST:WAVEFORM:DELETE ALL")
    else:
      self.write("WLIST:WAVEFORM:DELETE \"%s\"" % name)
    
  def createWaveform(self,name,data,wavetype):
    """
    Creates a waveform using a data string as generated by WriteIntData or WriteRealData.
    """
    size = len(data) / 5
    if wavetype == 'INT':
      size = len(data) / 2
    #print "Creating waveform of length %d" % size
    self.write("WLIST:WAVEFORM:NEW \"%s\",%d,%s" %(name,size,wavetype))     
    header = "#%d%d" % (len("%d" % len(data)),len(data))
    self.write("WLIST:WAVEFORM:DATA \"%s\",0,%d," %(name,size)+header+data)
    time.sleep(self._waitTime)
    
  def appendWaveformToSequence(self,index,channel,waveform,wait=True,repeat=1):
    """
    Adds a waveform from to the sequence at position 'index' to 'channel'.
    """
    if self.sequenceLength()<index:
      self.createSequence(index)
    self.write("SEQuence:ELEMent%d:WAVeform%d \"%s\""%(index,channel,waveform))
    if repeat != 'inf':
      self.write("SEQuence:ELEMent%d:LOOP:COUNT %d"%(index,repeat))
    else:
      self.write("SEQuence:ELEMent%d:LOOP:INFINITE 1"%(index))
    if wait:
      self.write("SEQuence:ELEMent%d:TWAIT 1"%(index))
    else:
      self.write("SEQuence:ELEMent%d:TWAIT 0"%(index))

  def updateMarkers(self,name,markers):
    """
    Updates the markers on a given channel.
    """
    data = self.writeMarkers(markers)
    size = len(markers)
    header = "#%d%d" % (len("%d" % len(data)),len(data))
    self.write("WLIST:WAVEFORM:MARKER:DATA \"%s\",0,%d," %(name,size) +header+data)
    time.sleep(self._waitTime)
 
  def getMarkers(self,name):
    """
    Returns the markers of a given channel.
    """
    data = self.ask("WLIST:WAVEFORM:MARKER:DATA? \"%s\"" % name)
    length = int(data[1])
    data = data[2+length:]
    return self.readMarkers(data)
    
  def getWaveform(self,name,prntSize=True):
    """
    Returns the waveform with a given name.
    """
    self.write("*CLS")
    data = self.ask("WLIST:WAVEFORM:DATA? \"%s\"" % name)
    wavetype = self.ask("WLIST:WAVEFORM:TYPe? \"%s\"" % name)
    m = re.match("\\s*\#\\d+\\s*",data)
    if prntSize: print "Size: %s" % m.string[m.start(0):m.end(0)]
    data = m.string[m.end(0):]
    MyWaveform = Waveform()
    if wavetype == 'REAL':
      MyWaveform._length = len(data)/5
      (values,markers) = self.readRealData(data)
    elif wavetype == 'INT':
      MyWaveform._length = len(data)/2
      (values,markers) = self.readIntData(data)
    MyWaveform._rawdata = data
    MyWaveform._data = values
    MyWaveform._markers = markers
    MyWaveform._name = name
    MyWaveform._type = wavetype
    return MyWaveform
     
  def getWaveformNames(self):
    """
    Returns the names of all waveforms stored in the AWG memory.
    """
    nWaveforms = int(self.ask("WLIST:SIZE?"))
    print "Found %d waveforms." % nWaveforms
    self.waveformNames = []
    for i in range(0,nWaveforms):
      name = self.ask("WLIST:NAME? %d" % i)[1:-1]
      self.waveformNames.append(name)
    self.notify("waveformnames",self.waveformNames)
    return self.waveformNames
  
  def updateWaveforms(self):
    """
    Retrieves all waveforms from the AWG.
    """
    nWaveforms = int(self.ask("WLIST:SIZE?"))
    print "Found %d waveforms." % nWaveforms
    self.waveforms = []
    for i in range(0,nWaveforms):
      name = self.ask("WLIST:NAME? %d" % i)[1:-1]
      try:
        waveform = self.getWaveform(name)
        self.waveforms.append(waveform)
      except:
        print "An error occured.."
    return self.waveforms
    
  def getWaveforms(self):
    """"""
    return self.waveforms
    
  def setWaitTime(self,time):
    """"""
    self._waitTime = time
    
  def waitTime(self):
    """"""
    return self._waitTime

  def  markersPerChannel(self):  
    """"""   
    return self._markersPerChannel

  # sequence programming

  def createSequence(self,length):
    """
    Creates a Sequence of length "length". All waveforms are the default waveforms (see programmer manual pg.22)
    """
    self.write("SEQuence:LENGth %d" %length)     
    time.sleep(self._waitTime)

  def sequenceLength(self):
    """
    returns the length of the sequence
    """
    self.write("SEQuence:LENGth?")
    length=self.read()     
    return float(length)   

  # Combination of two waveforms in a single complex waveform (used for instance by IQ mixers)

  def loadiqWaveform(self,iqWaveform, channels=(1,2), markers = None,waveformNames=('i','q')):
    """
    Loads an IQ waveform and 2 marker waveforms into 2 channels.
    """
    iChannel = numpy.zeros(len(iqWaveform))
    qChannel = numpy.zeros(len(iqWaveform))
    iChannel[:] = numpy.real(iqWaveform)
    qChannel[:] = numpy.imag(iqWaveform)
          
    self.loadRealWaveform(iChannel,channels[0],waveformName=waveformNames[0])
    self.loadRealWaveform(qChannel,channels[1],waveformName=waveformNames[1])
    return
    if markers is None:
      iMarkers=(numpy.zeros(len(iqWaveform),dtype=numpy.int8),numpy.zeros(len(iqWaveform),dtype=numpy.int8))
      qMarkers=(numpy.zeros(len(iqWaveform),dtype=numpy.int8),numpy.zeros(len(iqWaveform),dtype=numpy.int8))
    else:
      (iMarkers,qMarkers)=markers
    iData = self.writeIntData((iChannel+1.0)/2.0*((1<<14)-1),iMarkers)
    self.createWaveform(waveformNames[0],iData,"INT")
    self.setWaveform(channels[0],waveformNames[0])
  
    qData = self.writeIntData((qChannel+1.0)/2.0*((1<<14)-1),qMarkers)
    self.createWaveform(waveformNames[1],qData,"INT")
    self.setWaveform(channels[1],waveformNames[1])
  
    return len(qData)

  def loadComplexWaveforms(self,complexWaveform, channels=(1,2), markers = None,waveformNames=('i','q')):
    iChannel = numpy.zeros(len(complexWaveform),dtype = numpy.float32)
    qChannel = numpy.zeros(len(complexWaveform),dtype = numpy.float32)
    iChannel[:] = numpy.real(complexWaveform)
    qChannel[:] = numpy.imag(complexWaveform)
    self.load2RealWaveforms(waveforms=[iChannel,qChannel],channels=channels, markers = markers,waveformNames=waveformNames)

  def load2RealWaveforms(self,waveforms, channels=[1,2], markers = None,waveformNames=('i','q')):
    self.loadRealWaveform(realWaveform=waveforms[0],channel=channels[0],markers=markers[0], waveformName=waveformNames[0])
    self.loadRealWaveform(realWaveform=waveforms[1],channel=channels[1],markers=markers[1], waveformName=waveformNames[1])

  #    Is the function below useful?
  def loadRealWaveform2(self, waveform, channel=1, markers=None, waveformName='i'):
    def reverse( n, p):
      return sum(1<<(n-1-i) for i in range(n) if p>>i&1)
    #data=self.writeRealData(waveform,markers)
    dataD = ""
    dataM = ""

    if __DEBUG__:t0=time.time()

    print "loading channel ",channel, ",  mean=", numpy.mean(waveform)

    valuesFloat = numpy.zeros(len(waveform),dtype = numpy.float32)
    markersInt = numpy.zeros(len(markers),dtype = numpy.uint8)

    valuesFloat[:] = waveform[:]
    markersInt[:]=markers[:]

    print "loading channel ",channel, ",  mean=", numpy.mean(valuesFloat)

    for i in range(0,len(waveform)):
      #output+=struct.pack("<f",((marker & 3) << 14) + (value & (0xFFFF >> 2)))
      dataD+=struct.pack("<f",valuesFloat[i])
      dataD+=struct.pack("<b",0)
      dataM+=struct.pack("<B",reverse(8,markersInt[i]))

    size=len(dataD)/5
    wavetype='REAL'
    self.write("WLIST:WAVEFORM:NEW \"%s\",%d,%s" %(waveformName,size,wavetype))     
    headerD = "#%d%d" % (len("%d" % len(dataD)),len(dataD))
    self.write("WLIST:WAVEFORM:DATA \"%s\",0,%d," %(waveformName,size)+headerD+dataD)
    headerM = "#%d%d" % (len("%d" % len(dataM)),len(dataM))
    self.write("WLIST:WAVEFORM:MARKER:DATA \"%s\",0,%d," %(waveformName,size)+headerM+dataM)
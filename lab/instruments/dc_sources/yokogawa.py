
# imports
import sys,getopt,re,struct,time,math
from application.lib.instrum_classes import VisaInstrument

class Trace:
      pass

class Instr(VisaInstrument):

    """
    The Yokogawa DC source instrument class
    """

    def initialize(self,visaAddress = "GPIB0::9",slewrate = None):
      """
      Initializes the device.
      """
      try:
        self._slewrate = slewrate
        self._visaAddress = visaAddress
      except:
        self.statusStr("An error has occured. Cannot initialize Yoko(%s)." % visaAddress)        

    def setSlewrate(self,slewrate):
      self._slewrate = slewrate
      return self._slewrate

    def slewrate(self):
      return self._slewrate

    def toVoltage(self,range=None,turnOn=False):
      """
      Switch to voltage mode, and optionally select range.
      """
      self.write('F1;E')
      c=None
      if range == 1 or range == '10mV':
        c='R2'
      elif range == 2 or range == '100mV':
        c='R3'
      elif range == 3 or range == '1V':
        c='R4'
      elif range == 4 or range == '10V':
        c='R5'
      elif range == 5 or range == '30V':
        c='R6'
      if c is not None:
        self.write(c+';E')
      if turnOn:
        self.turnOn()

    def toCurrent(self,range=None,turnOn=False):
      """
      Switch to current mode, and optionally select range.
      """
      self.write('F5;E')
      c=None
      if range == 1 or range == '1mA':
        c='R4'
      elif range == 2 or range == '10mA':
        c='R5'
      elif range == 3 or range == '100mA':
        c='R6'
      if c is not None:
        self.write(c+';E')
      if turnOn:
        self.turnOn()
         
    def voltage(self):
      """
      OBSOLETE. Maintained for compatibility reasons.
      """
      return self.outputValue()

    def outputValue(self):
      """
      Returns the current output in V or mA depending on the source mode
      """
      string = self.ask('od;E;')
      string = re.sub(r'^(NDCV|NDCA|EDCV)',r'',string)
      self.notify('voltage',float(string))
      return float(string)
    
    def _setVoltageOrCurrent(self,mode,value,slewrate,turnOn):
      """
      Private function for setVoltage or setCurrent
      """
      string = self.ask("od;")
      if mode == 'voltage' and string.find('CA') != -1:
        self.toVoltage()
      elif mode == 'current' and string.find('CV') != -1:
        self.toCurrent()
      self.setOutputValue(value,slewrate=slewrate)
      if turnOn:  self.turnOn()
      return self.outputValue()

    def setVoltage(self,value,slewrate=None,turnOn=False):
      """
      Switches to voltage mode if necessary, outputs voltage, and optionnaly switches output on.
      """
      return self._setVoltageOrCurrent('voltage',value,slewrate,turnOn)

    def setCurrent(self,value,slewrate=None,turnOn=False):
      """
      Switches to current mode if necessary, outputs voltage, and optionnaly switches output on.
      """
      return self._setVoltageOrCurrent('current',value,slewrate,turnOn)

    def setOutputValue(self,value,slewrate=None,raiseError=False):
      """
      Sets the voltage to a given value with a given slew rate.
      The "slew rate" is actually in V/s or A/s during the waiting time between increments.
      Since the time to set and read the output value is not negligible with respect to the waiting time, the "slew rate" is very approximative.
      """
      prec=self.precision()               # determline the precision
      if slewrate is None:  slewrate = self._slewrate        
      if slewrate is None:
        self.write('S%f;E;' % value)
      else:
        inc=max(abs(slewrate)*0.1,prec)   # and an increment larger than or equal to the precision
        v = self.outputValue()
        while abs(value-v) > prec:   # while you have the precision to get closer
          time.sleep(0.1)
          if value > v+inc:
                v+=inc
          elif value < v-inc:
                v-=inc
          else:
            v = value
          self.write('S%f;E;' % v)
      v=self.outputValue()
      if abs(v-value)>prec:
        msg='Error: could not set the requested value!'
        if raiseError:
          raise msg
        else:
          print msg
      return v
      
    def output(self):
      """
      Returns the output status of the device (ON/OFF)
      """
      match = re.search('STS1=(\d+)',self.ask('OC;'))
      status = int(match.groups(0)[0])
      isOn = status & 16
      if isOn:
        isOn = True
      else:
        isOn = False
      self.notify('output',isOn)
      return isOn
      
    def turnOn(self):
      """
      Turns the device on.
      """
      self.write('E;O1;E;')
      return self.output()
      
    def turnOff(self):
      """
      Turns the device off.
      """
      self.write("E;O0;E;")
      return self.output()
      
    def saveState(self,name):
      """
      Saves the state of the device to a dictionary.
      """
      return self.parameters()
      
    def restoreState(self,state):
      """
      Restores the state of the device from a dictionary.
      """
      self.setVoltage(state['voltage'])
      if state['output'] == True:
        self.turnOn()
      else:
        self.turnOff()
      
    def parameters(self):
      """
      Returns the parameters of the device.
      """
      params = dict()
      try:
        params['voltage'] = self.voltage()
        params['output'] = self.output()
        return params
      except:
        return "Disconnected"

    def precision(self):
      """
      Determines the actual precision of the output
      """
      string = self.ask('od;E;')                  # get the actual output
      i1 = string.find('.')
      i2 = string.find('E',i1)                    # find the indices of the dot before the decimal part and the E before the exponent
      decimals=i2-i1-1                            # calculate the number of digit in the decimal part
      exponent=int(string[i2+1:])
      prec=10**(-decimals+ exponent)           # calculate te precision
      return prec
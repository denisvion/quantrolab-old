import sys
import getopt
import re
import struct
import time
import math

from application.lib.instrum_classes import VisaInstrument

class Trace:
      pass

class Instr(VisaInstrument):

      """
      The Yokogawa instrument class
      """

      def voltage(self):
        """
        Returns the voltage
        """
        self.write("I %u" % (self._unit))
        string = self.ask("volt?")
        self.notify("voltage",float(string))
        return float(string)
      
      def setVoltage(self,value,slewRate = None):
        """
        Sets the voltage to a given value with a given slew rate
        """
        self.write("I %u" % (self._unit))
        if slewRate is None:
          slewRate = self.slewRate        
        if math.fabs(value) > 50.0: 
          raise "Error! Voltage is too high!"
        if slewRate is None:
          self.write("volt %f" % value)
        else:
          slewRate=abs(slewRate)
          v = self.voltage()
          while math.fabs(v - value)>0.0000001:
            time.sleep(0.1)
            if v > value:
              if v-value > slewRate*0.1:
                v-=slewRate*0.1
              else:
                v=value
              self.write("volt %f" % v)
              v = self.voltage()
            elif v < value:
              if value-v > slewRate*0.1:
                v+=slewRate*0.1
              else:
                v = value
              self.write("volt %f" % v)
              v = self.voltage()
                
        return self.voltage()
        
      def output(self):
        """
        Returns the output status of the device (ON/OFF)
        """
        self.write("I %u" % self._unit)
        isOn = self.ask("outp?")
        if isOn:
          isOn = True
        else:
          isOn = False
        self.notify("output",isOn)
        return isOn
        
      def turnOn(self):
        """
        Turns the device on.
        """
        self.write("I %u" % (self._unit))
        print "ordre sent=","I %u" % (self._unit)
        self.write("outp 1")
      #  return self.output()
        
      def turnOff(self):
        """
        Turns the device off.
        """
        self.write("I %u" % (self._unit))
        self.write("outp 0")
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
		
      def initialize(self,visaAddress = "GPIB0::5", unit = 1, slewRate = None):
        """
        Initializes the device.
        """
        try:
          self.slewRate = slewRate
          self._unit = unit
          self._visaAddress = visaAddress
        except:
          self.statusStr("An error has occured. Cannot initialize Yoko(%s)." % visaAddress)        
import sys
import getopt

from application.lib.instrum_classes import *

class Instr(Instrument):


      def initialize(self, visaAddressIn = "192.168.0.61::12061",visaAddressOut = "192.168.0.61::12000"):
        try:
          if DEBUG or True:
            print "Initializing temperature sensor with addresses IN/OUT "+ visaAddressIn +' / '+visaAddressOut
          self._visaAddressIn = visaAddressIn
          self._visaAddressOut = visaAddressOut
        except:
          self.statusStr("An error has occured. Cannot initialize sensor.")    
          print "An error has occured. Cannot initialize sensor."

      def parameters(self):
        params = dict()
        params['temperature'] = self.temperature()
        return params
      
      def saveState(self,name):
        return self.parameters()

      def temperature(self):
        """
        Returns the temperature
        """
        self.write('*IDN?')
        string='Test OK'
        #string = self.ask('MMR3GetMes()')
        # treat string here
        return string 

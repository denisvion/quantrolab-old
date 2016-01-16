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
    The lakeshore 455 instrument class
    """

    def initialize(self, visaAddress="GPIB0::9", slewRate=None):
        """
        Initializes the device.
        """
        try:
            self._visaAddress = visaAddress
        except:
            self.statusStr(
                "An error has occured. Cannot initialize Yoko(%s)." % visaAddress)

    def saveState(self, name):
        """
        Saves the state of the device to a dictionary.
        """
        return self.parameters()

    def restoreState(self, state):
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

    def readField(self):
        """
        Read the displyed value.
        """
        return self.ask('RDGFIELD?')

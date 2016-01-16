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
    The Keithley2400 instrument class
    """

    def current(self):
        """
        Returns the current
        """
        self.write(":OUTP ON")
        time.sleep(1)
        self.write(":SENS:FUNC 'CURR'")
        self.write(":READ?")
        string = self.read()
        self.write(":OUTP OFF")
        return float(string[14:27])

    def voltage(self):
        """
        Returns the voltage
        """
        self.write(":SENS:FUNC 'VOLT'")
        self.write(":READ?")
        string = self.read()
        return float(string[0:13])

    def resistance(self):
        """
        Returns the current
        """
        self.write(":READ?")
        string = self.read()
        return float(string[28:41])

    def setVoltage(self, value):
        """
        Sets the voltage to a given value
        """
        if math.fabs(value) > 10.0:
            raise "Error! Voltage is too high!"
        else:
            self.write(":SOUR:FUNC VOLT")
            self.write(":SOUR:VOLT:LEV %s" % str(value))
            self.write(":SENS:CURR:PROT 2E-2")
            self.write(":SENS:VOLT:PROT 2E-1")
        return self.voltage()

    def setCurrent(self, value):
        """
        Sets the current to a given value
        """
        if math.fabs(value) > 1.0:
            raise "Error! Current is too high!"
        else:

            self.write(":SOUR:FUNC CURR")
            self.write(":SOUR:CURR:LEV %s" % str(value))
            self.write(":SENS:CURR:PROT 2E-2")
            self.write(":SENS:VOLT:PROT 2E-1")

    def output(self):
        """
        Returns the output status of the device (ON/OFF)
        """
        self.write("OUTP:STAT?")
        isOn = self.read()
        if isOn:
            isOn = True
        else:
            isOn = False
        self.notify("output", isOn)
        return isOn

    def turnOn(self):
        """
        Turns the device on.
        """
        self.write(":OUTP ON")
        return self.output()

    def turnOff(self):
        """
        Turns the device off.
        """
        self.write(":OUTP OFF")
        return self.output()

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

    def initialize(self, name="Keithley2400", visaAddress="GPIB0::9", slewRate=None):
        """
        Initializes the device.
        """
        try:
            self.slewRate = slewRate
            self._name = name
            self._visaAddress = visaAddress
        except:
            self.statusStr(
                "An error has occured. Cannot initialize Yoko(%s)." % visaAddress)

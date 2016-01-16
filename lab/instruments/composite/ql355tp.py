import sys
import getopt
import re
import struct
import numpy

from application.lib.instrum_classes import VisaInstrument  # VISAINSTRUMENT


__DEBUG__ = True


class AwgException(Exception):
    pass


class Instr(VisaInstrument):

    """
    The QL355TP instrument (voltage source to bias amplifiers)
    """

    def initialize(self, visaAddress="GPIB::11"):
        print 'Initializing ' + self.name() + ' with adress ', visaAddress, ':'
        self._visaAddress = visaAddress
        try:
            # self.clearDevice()
            self.getID()
        except:
            print "ERROR: Cannot initialize instrument!"

    def getID(self):
        return self.ask('*IDN?')

    def state(self):
        """
        Returns the output state of the instrument.
        """
        return self.ask("OUTPUT?")

    def setState(self, state):
        """
        Sets the output state of the instrument.
        """
        buf = "OFF"
        if state == True:
            buf = "ON"
        self.write("OUTPUT %s" % (buf))

    def saveState(self, name):
        """
        Saves the state of the instrument.
        """
        # self.saveSetup(name)
        # return name
        return None

    def restoreState(self, name):
        """
        Restores the state of the instrument.
        """
        return None  # self.loadSetup(name)

    # Type all your methods below

    def triggerInterval(self):
        return float(self.ask("TRIG:DEL?"))

    def turnOnOff(self, flag):
        self.write("OPALL %f" % flag)

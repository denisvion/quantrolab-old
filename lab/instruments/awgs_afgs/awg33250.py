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
    The AWG instrument.
    """

    def initialize(self, visaAddress="GPIB::2"):
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

    def period(self):
        pass

    def setPeriod(self, freq):
        pass

    def freq(self):
        pass

    def setFreq(self, freq):
        pass

    def low(self):
        """
        Returns the low voltage of a given channel.
        """
        return float(self.ask("VOLTAGE:LOW?"))

    def setLow(self, voltage):
        """
        Sets the low voltage of a given channel.
        """
        self.write("VOLTAGE:LOW %f" % (voltage))
        return self.low()

    def high(self):
        """
        Returns the high voltage of a given channel.
        """
        return float(self.ask("VOLTAGE:HIGH?"))

    def setHigh(self, voltage):
        """
        Sets the high voltage of a given channel.
        """
        self.write("VOLTAGE:HIGH %f" % (voltage))
        return self.high()

    def amplitude(self):
        """
        Returns the amplitude .
        """
        return float(self.ask("VOLTAGE?"))

    def setAmplitude(self, voltage):
        """
        Sets the amplitude of a given channel.
        """
        self.write("VOLTAGE %f" % (voltage))
        return self.amplitude()

    def offset(self):
        """
        Returns the offset of a given channel.
        """
        return float(self.ask("VOLTAGE:OFFSET?"))

    def setOffset(self, voltage):
        """
        Sets the offset of a given channel.
        """
        self.write("VOLTAGE:OFFSET %f" % (voltage))
        return self.offset()

    def triggerInterval(self):
        return float(self.ask("TRIG:DEL?"))

    def setTriggerInterval(self, interval):
        self.write("TRIG:DEL %f e-6" % interval)

    def pulsewidth(self):
        return float(self.ask("PULSE:WIDTH?"))

    def setPulsewidth(self, pulsewidth):
        self.write("PULSE:WIDTH %f e-6" % pulsewidth)
        return self.pulsewidth()

    def loadRealWaveform(self, realWaveform, channel=1, markers=None, waveformName='ch1'):
        """
        Loads a waveform and 2 marker waveforms into the AWG file.
        """

        waveform = numpy.zeros(len(realWaveform))
        waveform[:] = numpy.real(realWaveform)

        if markers is None:
            markers = numpy.zeros(len(waveform), dtype=numpy.int8)
            markers[:10000] = 3
        data = self.writeIntData(
            (waveform + 1.0) / 2.0 * ((1 << 14) - 1), markers)
        self.createWaveform(waveformName, data, "INT")
#    data = self.writeRealData((waveform+1.0)/2.0*((1<<14)-1),markers)
#    self.createWaveform(waveformName,data,"REAL")
        self.setWaveform(channel, waveformName)

        return len(data)

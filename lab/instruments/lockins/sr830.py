
# imports
import numpy as np
from application.lib.instrum_classes import *


class Instr(VisaInstrument):

    """
    The SR830 lock in instrument class.
    """
    # ranges
    sensitivities = [2, 5, 10, 20, 50, 100, 200, 500, 1, 2, 5, 10,
                     20, 50, 100, 200, 500, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1]
    voltageUnits = ['nV', 'nV', 'nV', 'nV', 'nV', 'nV', 'nV', 'nV', 'muV', 'muV', 'muV', 'muV',
                    'muV', 'muV', 'muV', 'muV', 'muV', 'mV', 'mV', 'mV', 'mV', 'mV', 'mV', 'mV', 'mV', 'mV', 'V']
    currentUnits = ['fA', 'fA', 'fA', 'fA', 'fA', 'fA', 'fA', 'fA', 'pA', 'pA', 'pA', 'pA', 'pA',
                    'pA', 'pA', 'pA', 'pA', 'nA', 'nA', 'nA', 'nA', 'nA', 'nA', 'nA', 'nA', 'nA', 'muA']
    prefix = {'f': 1e-15, 'p': 1e-12, 'n': 1e-9, 'mu': 1e-6, 'm': 1e-3, 'k': 1e3}
    times = [10e-6, 30e-6, 100e-6, 300e-6, 1e-3, 3e-3, 10e-3, 30e-3, 100e-3,
             300e-3, 1., 3., 10., 30., 100., 300., 1000., 3000., 10000., 30000.]
    filterSlopes = [6, 12, 18, 24]
    parameters = {'x': 1, 'y': 2, 'r': 3, 't': 4, 'auxIn1': 5, 'auxIn2': 6,
                  'auxIn3': 7, 'auxIn4': 8, 'f': 9, 'ch1': 10, 'ch2': 11}

    # Reference and phase commands

    def phase(self):
        """
        Returns the reference phase in degrees.
        """
        return self.ask('PHAS?')

    def setPhase(self, phaseInDegrees):
        """
        Sets and returns the reference phase in degrees.
        """
        return self.ask('PHAS%f;PHAS?' % phaseInDegrees)

    def source(self):
        """
        Returns 1 if the reference source is internal or 0 if it is external.
        """
        return self.ask('FMOD?')

    def setSource(self, source):
        """
        Sets and returns 1 if the reference source.
        source: '0' or 'external' or 'ext' for external source or '1' or 'internal' or 'int' for internal source
        """
        if source in ['external', 'ext']:
            source = 0
        elif source in ['internal', 'int']:
            source = 1
        if source in [0, 1, '0', '1']:
            self.write('FMOD' + str(source))
        return self.ask('FMOD?')

    def frequency(self):
        """
        Returns the reference frequency in Hertz.
        """
        return self.ask('FREQ?')

    def setFrequency(self, freqInHertz):
        """
        Sets and returns the reference frequency in Hertz in internal mode.
        """
        return self.ask('FREQ%f;FREQ?' % freqInHertz)

    def voltage(self):
        """
        Returns the output voltage in Volts.
        """
        return self.ask('SLVL?')

    def setVoltage(self, voltageInVolt):
        """
        Sets and returns the output voltage in Volts (0.004 to 5.000 rounded to 0.002V).
        """
        return self.ask('SLVL %f; SLVL?' % voltageInVolt)

    def harmonic(self):
        """
        Returns the detection harmonic.
        """
        return self.ask('HARM?')

    def setHarmonic(self, harmonic):
        """
        Sets and returns the detection harmonic.
        """
        return self.ask('HARM %i; HARM?' % harmonic)

    def triggerMode(self):
        """
        Returns the trigger mode for the detection: sine zero crossing (0), TTL rise (1) , or TTL fall (2).
        """
        return self.ask('RSLP?')

    def setTriggerMode(self, triggerMode):
        """
        Sets and returns the trigger mode for the detection: sine zero crossing (0), TTL rise (1) , or TTL fall (2).
        """
        return self.ask('RSLP %i; RSLP?' % triggerMode)

    # Input and filter commands

    def input(self):
        """
        Returns the input configuration: A (0), A-B (1) , or current I with input impedence 1 MOhm (2) or 100 MOhm (3).
        """
        return int(self.ask('ISRC?'))

    def setInput(self, inputConf):
        """
        Sets and returns the input configuration: A (0), A-B (1) , or current I with input impedence 1 MOhm (2) or 100 MOhm (3).
        """
        return int(self.ask('ISRC %i; ISRC?' % inputConf))

    def setInputA(self):
        """
        Sets input to voltage A (0) and returns the input configuration.
        """
        return self.setInput(0)

    def setInputAMinusB(self):
        """
        Sets input to voltage A-B (1) and returns the input configuration.
        """
        return self.setInput(1)

    def setInputCurrent(self, impedanceInMOhm=1):
        """
        Sets input to current with input impedance impedanceInMOhm = 1 or 100.
        """
        code = 2
        if impedanceInMOhm > 10:
            code = 3
        return self.setInput(code)

    def coupling(self):
        """
        Returns the input coupling 'ac' (0) or 'dc' (1).
        """
        return ['ac', 'dc'][int(self.ask('ICPL?'))]

    def setCoupling(self, coupling):
        """
        Sets and returns the input coupling 'ac' (0) or 'dc' (1).
        """
        if coupling in ['AC', 'ac']:
            coupling = 0
        elif coupling in ['DC', 'dc']:
            coupling = 1
        return ['ac', 'dc'][int(self.ask('ICPL %i; ICPL?' % coupling))]

    def lineFilter(self):
        """
        Returns the input line filter: No filter (0), line (1) , line x2 (2), or both filters (3).
        """
        return int(self.ask('ILIN?'))

    def setLineFilter(self, filterCode):
        """
        Sets and returns the input line filter: No filter (0), line (1) , line x2 (2), or both filters (3).
        """
        return int(self.ask('ILIN %i; ILIN?' % filterCode))

    def noLineFilter(self):
        """
        Sets no input line filter (0) and returns the input line filter configuration: No filter (0), line (1) , line x2 (2), or both filters (3).
        """
        return self.setFilter(0)

    def lineFilter50Hz(self):
        """
        Sets the input line filter (1) and returns the input line filter configuration: No filter (0), line (1) , line x2 (2), or both filters (3).
        """
        return self.setFilter(1)

    def lineFilter100Hz(self):
        """
        Sets the input line x2 filters (2) and returns the input line filter configuration: No filter (0), line (1) , line x2 (2), or both filters (3).
        """
        return self.setFilter(2)

    def lineFilter50HzAnd100Hz(self):
        """
        Sets the input line and line x2 filters (3) and returns the input line filter configuration: No filter (0), line (1) , line x2 (2), or both filters (3).
        """
        return self.setFilter(3)

    # Sensitivity and time constant

    def sensitivity(self):
        """
        Returns the input sensitivity as a tuple (sensitivity, unit), which depends whether input is in voltage or current.
        """
        sensCode = int(self.ask('SENS?'))
        if self.input() >= 2:
            unitList = self.currentUnits
        else:
            unitList = self.voltageUnits
        return (self.sensitivities[sensCode], unitList[sensCode])

    def setSensitivity(self, sensitivityInAmpereOrVolt):
        """
        Sets the input sensitivity to the allowed value equal or just above the passed value sensitivityInAmpereOrVolt.
        SensitivityInAmpereOrVolt is interpreted as a voltage if input is A or A-B and as a current if input is I.
        Returns the selected sensitivity as a tuple (sensitivity, unit)
        """
        if self.input() >= 2:
            unitList = self.currentUnits
        else:
            unitList = self.voltageUnits
        ranges = np.array(self.sensitivities) * \
            np.array([self.prefix[unit[:-1]] if len(unit) > 1 else 1 for unit in unitList])
        index = min(np.searchsorted(ranges, sensitivityInAmpereOrVolt), len(ranges))
        return self.ask('SENS%i;SENS?' % index)

    def timeConstant(self):
        """
        Returns the time constant in second.
        """
        return self.times[int(self.ask('OFLT?'))]

    def timeConstantList(self):
        """
        Returns the list of allowed time constants in second.
        """
        return self.times

    def setTimeConstant(self, timeConstantInSecond):
        """
        Sets the the time constant to the allowed value equal or just above the passed value timeConstantInSecond.
        Returns the selected time constant in second.
        """
        index = min(np.searchsorted(self.times, timeConstantInSecond), len(self.times))
        return self.times[int(self.ask('OFLT %i; OFLT?' % index))]

    def filterSlope(self):
        """
        Returns the filter slope in dB/octave.
        """
        return self.filterSlopes[int(self.ask('OFSL?'))]

    def filterSlopeList(self):
        """
        Returns the list of allowed filter slope in dB/octave.
        """
        return self.filterSlopes

    def setFilterSlope(self, slopeIndBPerOctave):
        """
        Set and returns the filter slope in dB/octave.
        """
        index = min(np.searchsorted(self.filterSlopes, slopeIndBPerOctave), len(self.filterSlopes))
        return self.filterSlopes[int(self.ask('OFSL %i; OFSL?' % index))]

    # measures

    def readOutput(self, output):
        """
        Returns a particular output.
        output : 'X' (or 'x' or 1), or 'Y' (or 'y' or 2), or 'R' (or 'r' or 3), or 'T' (or 't' or 'theta' or 'Theta' or 4)
        """
        if output in ['X', 'x']:
            output = 1
        elif output in ['Y', 'y']:
            output = 2
        elif output in ['R', 'r']:
            output = 3
        elif output in ['T', 't', 'theta', 'Theta']:
            output = 4
        if output in [1, 2, 3, 4]:
            return self.ask('OUTP ? %i' % output)
        else:
            return 'incorrect output specification'

    def readChannel(self, channel):
        """
        Returns the value in one of the two channels.
        channel : 1 or 2
        """
        if channel in [1, 2]:
            return self.ask('OUTR ? %i' % channel)
        else:
            return 'incorrect channel specification'

    def measure(self, params, returnDict=False):
        """
        Returns a list of 2 to 6 parameters (or measured values) specified by the parameter list params.
        params: a list or tuple of elements belonging to  {'x', 'y', 'r', 't','auxIn1', 'auxIn2', 'auxIn3', 'auxIn4','f', 'ch1', 'ch2'}
        If returnDict is true, return a dictionary rather than a list.
        """
        codeString = ','.join(str(self.parameters[param]) for param in params)
        results = [float(stri) for stri in self.ask('SNAP?' + codeString).split(',')]
        if returnDict:
            results = dict(zip(params, results))
        return results

    def measureXY(self):
        """
        Returns the list of X and Y.
        """
        return self.measure(['x', 'y'])

    def measureRTheta(self):
        """
        Returns the list of R and Theta.
        """
        return self.measure(['r', 't'])

    def measureChannels(self):
        """
        Returns the list of R and Theta.
        """
        return self.measure(['ch1', 'ch2'])

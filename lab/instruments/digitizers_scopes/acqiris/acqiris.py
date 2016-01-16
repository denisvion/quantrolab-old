# This Acqiris instrument is based on the C++ library "Acqiris_QuantroDLL1.dll",
# which contains basic oscilloscope functions.
# In addition, it can optionally use other DLLs like a mathematical one based on the GSL library.
# These DLL are loaded when initializing the acqiris instrument.

___TEST___ = False
___DLL1Name___ = 'Acqiris_QuantroDLL1b.dll'   #
# OBSOLETE should be passed as a parameter. ___includeDLLMath1Module___=True   # load the GSL based mathematical module as an attribute of the acqiris instrument
# OBSOLETE should be passed as a parameter. ___includeModuleDLL2___=False
# # load the heterodyne demodulation module

import sys
import getopt
import math
import os.path
import time

from ctypes import *
from numpy import *

from application.helpers.instrumentsmanager import *
from application.lib.instrum_classes import *
from application.lib.datacube import Datacube

#import acqiris_ModuleDLL2

# utility class for helping in C to python interface


class myType:

    def __init__(self, i, dtype=float64):
        self._value = zeros(1, dtype=dtype)
        self._value[0] = i

    def address(self):
        return self._value.ctypes.data

    def value(self):
        return self._value[0]

# intrument class for the acquisition board


class Instr(Instrument):
    """
    The instrument class for the Acqiris fast acquisition card.
    """
    # creator function

    def initialize(self, *args, **kwargs):
        """
        Initializes the Acqiris virtual instruments and the Acqiris board.
        """
        self.__instrumentID = c_uint32(0)
        self.__numInstruments = c_uint32()
        self.__nbrOfChannels = c_uint32()
        self.__nbrADCBits = c_uint32()
        self.__temperature = c_int32()
        self.__time_us = c_double()

        # Load the different DLLs or DLL based modules
        self.loadDLLs(**kwargs)
        self.reinit()                 # init or reinit the board DEACTIVATED BY DV
        self.createDictAndGlobals()   # create dictionaries and global variables
        # duplicate self.nbrOfChannels in a Python type variable
        self.nbrOfChannels = int(self.__nbrOfChannels.value)
        self.getInitialConfig()

        # Flag to forbid the access to the live waveform when it has been
        # passed to the DLL
        self._memoryLocked = False

    def loadDLLs(self, **kwargs):
        """
        Load the different DLLs or DLL based modules for the acqiris instrument.
        """
        self.debugPrint('in acqiris.loadDLLs()')
        self.DLL1Loaded = False
        self.DLLMath1Loaded = False
        if '___includeModuleDLL1___' in kwargs:
            ___includeModuleDLL1___ = kwargs['___includeModuleDLL1___']
        else:
            ___includeModuleDLL1___ = False
        if '___includeModuleDLL2___' in kwargs:
            ___includeModuleDLL2___ = kwargs['___includeModuleDLL2___']
        else:
            ___includeModuleDLL2___ = False
        if '___includeDLLMath1Module___' in kwargs:
            ___includeDLLMath1Module___ = kwargs['___includeDLLMath1Module___']
        else:
            ___includeDLLMath1Module___ = False

        if ___TEST___:
            None
        else:
            if hasattr(self, "__acqiris") is False:
                try:
                    print "\nLoading basic oscilloscope DLL " + ___DLL1Name___ + "..."
                    print "path = ", os.path.dirname(os.path.abspath(__file__)) + '/' + ___DLL1Name___
                    self.__acqiris_QuantroDLL1 = windll.LoadLibrary(
                        os.path.dirname(os.path.abspath(__file__)) + '/' + ___DLL1Name___)
                    dllVersionString = p = create_string_buffer(48)
                    dllHelpString = create_string_buffer(1024)
                    self.__acqiris_QuantroDLL1.DLL1Version(
                        byref(dllVersionString), c_bool(True))
                    self.__acqiris_QuantroDLL1.DLL1Help(
                        "", byref(dllHelpString), c_bool(True))
                    self.__acqiris_QuantroDLL1.DLL1Help(
                        "DLL1Help", byref(dllHelpString), c_bool(True))
                    print "OK"
                    self.DLL1Loaded = True
                except ImportError:
                    print "Cannot load DLL " + ___DLL1Name___ + "!"
                    print sys.exc_info()
                    return False
        if ___includeDLLMath1Module___:
            try:
                if "acqiris_DLLMath1Module" in sys.modules.values():
                    reload("acqiris_DLLMath1Module")
                else:
                    import acqiris_DLLMath1Module
                self.DLLMath1Module = acqiris_DLLMath1Module.DLLMath1Module(
                    self)
                print "OK"
                self.DLLMath1Loaded = True
            except:
                print "Cannot load acqiris_DLLMath1Module!"
                print sys.exc_info()
                return False

        if ___includeModuleDLL2___:
            try:
                if "acqiris_ModuleDLL2" in sys.modules.values():
                    reload("acqiris_ModuleDLL2")
                else:
                    import acqiris_ModuleDLL2
                # print "\nLoading SWIG DLL 'acqiris_QuantroDLL2.dll'"
                # acqiris_ModuleDLL2.ModuleDLL2.__init__(self)
                self.moduleDLL2 = acqiris_ModuleDLL2.ModuleDLL2(self)
                self.setChannels = self.moduleDLL2.setChannels
                self.frequenciesAnalyse = self.moduleDLL2.frequenciesAnalyse
                self.setFrequencyAnalysisCorrections = self.moduleDLL2.setFrequencyAnalysisCorrections
                self.setDemodulatorCorrections = self.moduleDLL2.setDemodulatorCorrections
            except:
                print "Cannot load module or DLL acqiris_ModuleDLL2!"
                print sys.exc_info()
                return False

    def reinit(self, *args):
        """
        Initialize or reinitialize the access to Acqiris board.
        """
        print "Finding and testing board..."
        try:
            if self.__instrumentID.value != 0:  # if a handle to the board is known, reinitialize, i.e. close the access first
                self.__acqiris_QuantroDLL1.FinishApplication(
                    self.__instrumentID, c_bool(True))
            self.__acqiris_QuantroDLL1.FindDevices(
                byref(self.__instrumentID), byref(self.__numInstruments), c_bool(True))
            self.__acqiris_QuantroDLL1.NbrChannels(
                self.__instrumentID, byref(self.__nbrOfChannels), c_bool(True))
            self.__acqiris_QuantroDLL1.NbrADCBits(
                self.__instrumentID, byref(self.__nbrADCBits), c_bool(True))
            self.Temperature()
            print "OK"
        except:
            print "Error when trying to access Acqiris board."

    def createDictAndGlobals(self):
        self.debugPrint('in acqiris.createDictAndGlobals()')
        self.nbrOfChannels = int(self.__nbrOfChannels.value)

        self._constants = dict()
        self._constants["nbrOfChannels"] = self.nbrOfChannels
        self._constants["nbrADCBits"] = int(self.__nbrADCBits.value)

        # Acqiris board parameters defined in a second  dictionary params, initialized here with standard parameters
        # the idea is to have this dictionary always up to date and
        # corresponding to the actual state of the instrument
        self._params = dict()
        # replaces old synchro boolean
        self._params["clock"] = 2
        self._params["trigSource"] = -1
        self._params["trigCoupling"] = 3
        self._params["trigLevel1"] = 500  # in mV
        self._params["trigLevel2"] = 0  # in mV
        self._params["trigSlope"] = 0
        self._params["trigDelay"] = 0e-9
        self._params["memType"] = 1
        # flag modifier: 0=normal, 1=Start on trigger, 2=Wrap mode, 10=SAR mode
        self._params["configMode"] = 0
        self._params["convertersPerChannel"] = 1
        self._params["fullScales"] = [5.0] * self.nbrOfChannels
        self._params["offsets"] = [0.0] * self.nbrOfChannels
        self._params["couplings"] = [3] * self.nbrOfChannels
        self._params["bandwidths"] = [3] * self.nbrOfChannels
        self._params["usedChannels"] = 3
        self._params["sampleInterval"] = 5e-10  # in seconds
        self._params["numberOfPoints"] = 400
        self._params["numberOfSegments"] = 10   # per bank
        self._params["numberOfBanks"] = 1         # in acqiris board memory

        # Last acquired sequence is defined below as global variables
        # unique wave identifier initialized to 0
        self.lastWaveIdentifier = 0
        self.lastTransferredChannel = 0					  # code of transferred channels
        # last transfer was the sequence average
        self.lastTransferAverage = False
        self.lastWaveformArray = [zeros(1, dtype=float64)] * 4
        # number of samples in each waveform channels
        self.lastWaveformArraySizes = zeros(4, dtype=int32)
        self.lastSamplingTime = 0						      # last sampling period
        # number of samples per segment in the  last waveforms returned
        self.lastNbrSamplesPerSeg = 0
        # number of segments actually returned for each channel
        self.lastNbrSegmentsArray = zeros(4, dtype=int32)
        self.lastHorPositionsArray = zeros(1, dtype=float64)
        self.lastHorPositionsArraySize = 1
        # total size time stamp array in the last transfer
        self.lastTimeStampsArray = zeros(1, dtype=float64)
        # total size time stamp array in the last transfer
        self.lastTimeStampsArraySize = 1
        self.lastAverageArray = [zeros(1)] * 4
        self.lastAverageCalculated = False

        # Data analysis in other global variables
        # not implemented with the DLLMath here

    def getInitialConfig(self):
        print "\nReading the digitizer configuration..."
        try:
            # read the initial configuration of the acquisition board and
            # update params dictionary
            self.getConfigAll()
            # self._params["wantedChannels"]=self._params["usedChannels"]    #
            # not initialized
            self.notify("parameters", self._params)
            print "OK"
        except:
            print "Error when trying to get the current configuration of the Acqiris board."

    def transformErr2Str(self, *args):
        """
        Transform acqiris error codes into string describing the error.
        """
        error_code = c_int32(args[0])
        error_str = create_string_buffer("\000" * 1024)
        status = self.__acqiris_QuantroDLL1.transformErr2Str(
            self.__instrumentID, error_code, error_str)
        return str(error_str)

    def restoreState(self, state):
        self.debugPrint('in acqiris.restoreState(state) with state = ', state)
        self._params = state
        self.setConfigAll()

    def constants(self):
        """
        Returns the constants of the Acqiris card.
        """
        return self._constants

    def parameters(self):
        """
        Returns the params dictionary.
        """
        # always up to date => nothing to do
        return self._params

    def updateParameters(self, *args, **kwargs):
        self.debugPrint('in acqiris.updateParameters()')
        """
    Updates the parameter dictionary of the instrument.
    """
        for key in kwargs.keys():
            self._params[key] = kwargs[key]

    def setParameter(self, arg, value):
        """
        set a single parameter dictionary of the instrument.
        """
        self.debugPrint('in acqiris.setParameter(', arg, ',', value, ')')
        self._params[arg] = value
        return self._params

    # calibrate function
    CAL_FULL = 0               # full calibration code
    CAL_CURRENT_CONFIG = 1     # calibrate current configuration code
    CAL_FAST = 4               # calibrate specified channels

    def Calibrate(self, option=CAL_FAST, channels=15):
        """
        Calibrates the Acqiris board by calling the calibrate C DLL function.
        """
        self.debugPrint('in acqiris.Calibrate(option=',
                        option, ',channels=', channels, ')')
        time_us = myType(0, float64)
        status = self.__acqiris_QuantroDLL1.Calibrate(
            self.__instrumentID, option, channels, time_us.address(), c_bool(True))
        if status != 0:
            raise Exception(self.transformErr2Str(status))

    # Get config function
    def getConfigAll(self):
        """
        Get the current configuration of the board by calling configAll with parameter set=False.
        """
        self.debugPrint('in acqiris.getConfigAll()')
        return self.configAll(False)

    # Set config function
    def setConfigAll(self, *args, **kwargs):
        """
        Set the current configuration of the board by calling configAll with parameter set=True.
        """
        self.debugPrint('in acqiris.setConfigAll()')
        return self.configAll(True, *args, **kwargs)

    # configure function
    def configAll(self, set, *args, **kwargs):
        """
        Get or Set the configuration of the board by calling the C DLL function configAll with parameter set=False or True.
        Systematic notification de-activated. Callers have to use a dispatch call to get notification.
        """
        # update first the params dictionary with any parameters passed to the
        # function
        self.updateParameters(*args, **kwargs)
        # create ctypes objects for all the python typed parameters in the the
        # dictionary params, to be passed to the C DLL.
        clock = c_int32(self._params["clock"])
        trig = c_int32(self._params["trigSource"])
        trig_coupling = c_int32(self._params["trigCoupling"])
        trig_slope = c_int32(self._params["trigSlope"])
        trig_level1 = c_double(self._params["trigLevel1"])
        trig_level2 = c_double(self._params["trigLevel2"])
        trig_delay = c_double(self._params["trigDelay"])
        mem = c_int32(int(self._params["memType"]))
        configMode = c_int32(int(self._params["configMode"]))
        converters_per_channel = c_int32(self._params["convertersPerChannel"])
        used_channels = c_int32(self._params["usedChannels"])
        sample_interval = c_double(self._params["sampleInterval"])
        number_of_points = c_int32(self._params["numberOfPoints"])
        number_of_segments = c_int32(self._params["numberOfSegments"])
        numberOfBanks = c_int32(self._params["numberOfBanks"])
        fs = zeros(self.nbrOfChannels, dtype=float64)
        of = zeros(self.nbrOfChannels, dtype=float64)
        cs = zeros(self.nbrOfChannels, dtype=int32)
        bs = zeros(self.nbrOfChannels, dtype=int32)
        for i in range(0, self.nbrOfChannels):
            fs[i] = self._params["fullScales"][i]
            of[i] = self._params["offsets"][i]
            cs[i] = self._params["couplings"][i]
            bs[i] = self._params["bandwidths"][i]
        time_us = myType(0, float64)
        dataArraySize = c_int32(0)
        timeArraySize = c_int32(0)
        # call the ConfigAll DLL function that configures all the acquisition
        # parameters
        status = self.__acqiris_QuantroDLL1.ConfigAll(
            c_bool(set), self.__instrumentID, byref(clock), byref(used_channels), byref(converters_per_channel), byref(mem), byref(sample_interval), byref(number_of_points), byref(number_of_segments), byref(numberOfBanks), byref(trig), byref(trig_coupling), byref(
                trig_slope), byref(trig_level1), byref(trig_level2), byref(trig_delay), byref(configMode), byref(dataArraySize), byref(timeArraySize), fs.ctypes.data, of.ctypes.data, cs.ctypes.data, bs.ctypes.data, time_us.address(), c_bool(True)
        )
        self.transformErr2Str(status)
        # update dictionary params by converting back ctyped data in python
        # because params dictionary has to be kept always up to date
        self._params["clock"] = clock.value
        self._params["trigSource"] = trig.value
        self._params["trigCoupling"] = trig_coupling.value
        self._params["trigSlope"] = trig_slope.value
        self._params["trigLevel1"] = trig_level1.value
        self._params["trigLevel2"] = trig_level2.value
        self._params["trigDelay"] = trig_delay.value
        self._params["memType"] = mem.value
        self._params["configMode"] = configMode.value
        self._params["convertersPerChannel"] = converters_per_channel.value
        self._params["usedChannels"] = used_channels.value
        self._params["sampleInterval"] = sample_interval.value
        self._params["numberOfPoints"] = number_of_points.value
        self._params["numberOfSegments"] = number_of_segments.value
        self._params["numberOfBanks"] = numberOfBanks.value
        for i in range(0, self.nbrOfChannels):
            self._params["fullScales"][i] = float(fs[i])
            self._params["offsets"][i] = float(of[i])
            self._params["couplings"][i] = int(cs[i])
            self._params["bandwidths"][i] = int(bs[i])
        # This is the data array size required for a raw data transfer
        self.dataArraySize = dataArraySize.value
        # This is the time array size required for timestamps and horPositions
        self.timeArraySize = timeArraySize.value
        # self.notify("parameters",self._params)  # possible notification to a Frontpanel
        # Notify only if you accept that your front panel looses its settings
        # at each new configuration
        return status

    # acquisition and transfer function
    def AcquireTransfer(self, voltages=True, wantedChannels=15, transferAverage=False, getHorPos=True, getTimeStamps=True, nLoops=1., timeOut=10):
        """
        Start a sequence acquisition and transfer the acquired sequence by calling the C DLL function AcquireTransfer.
        A number of nLoops sequences can be piled up to circumvent the sequence limitation of the acqiris system.
        A timeout larger than the normal acqiris limit can also be used.
        All acquisition parameters and the sequence data are first stored in global variables and copied in a dictionary 
        to be used by a possible frontpanel.
        Systematic notification de-activated. Callers have to use a dispatch call to get notification.
        """
        self.debugPrint('in acqiris.AcquireTransfer(voltages=', voltages, ',wantedChannels=', wantedChannels, ',transferAverage=',
                        transferAverage, ',getHorPos=', getHorPos, ',getTimeStamps=', getTimeStamps, ',nLoops=', nLoops, ',timeOut=', timeOut, ')')
        # self.nLoops=nLoops
        # prepare all the parameters for calling DLL function AcquireTransferV4
        self._memoryLocked = True                 # lock memory
        requestedLoopsOrBanks = myType(nLoops, dtype=int32)
        wantedChannels2 = myType(wantedChannels, dtype=int32)
        totalArraySizes = zeros(4, dtype=int32)
        transferAverages = zeros(4, dtype=bool)
        transferAverages[:] = [transferAverage] * 4
        # We reserve the required size and reset the arrays
        if transferAverage == False:  # that will contain the transferred vertical data if no averaging
            size = int(self._params["numberOfPoints"] *
                       self._params["numberOfSegments"] * nLoops)
        else:                         # that will contain the transferred vertical data if averaging
            size = int(self._params["numberOfPoints"])
        for i in range(0, self.nbrOfChannels):
            size2 = 1
            if wantedChannels & (1 << i):
                size2 = size
            self.lastWaveformArraySizes[i] = size2
            self.lastWaveformArray[i] = zeros(size2, dtype=float64)
        self.lastAverageCalculated = False
        samplingTime = myType(0, float64)
        nbrSamplesPerSeg = myType(0, dtype=int32)
        nbrSegments = myType(0, dtype=int32)
        nbrSegmentsArray = zeros(4, dtype=int32)

        if getHorPos:  # reserve the required size for horizontal positions of the successive triggers
            horPosArraySize = myType(
                self._params["numberOfSegments"] * nLoops, dtype=int32)
            self.lastHorPositionsArray = zeros(
                self._params["numberOfSegments"] * nLoops, dtype=float64)
        else:
            horPosArraySize = myType(0, dtype=int32)
            self.horPosArray = zeros(1, dtype=float64)

        if getTimeStamps:  # reserve the required size for timestamps of the successive triggers
            timeStampsArraySize = myType(
                self._params["numberOfSegments"] * nLoops, dtype=int32)
            self.lastTimeStampsArray = zeros(
                self._params["numberOfSegments"] * nLoops, dtype=float64)
        else:
            timeStampsArraySize = myType(0, dtype=int32)
            self.lastTimeStampsArray = zeros(1, dtype=float64)
        maxDelayBetweenTrigs_s = myType(100, dtype=float64)
        time_s = myType(0, float64)

        # call the C AcquireTransfer DLL function that acquire AND transfer
        self.debugPrint(
            'calling __acqiris_QuantroDLL1.AcquireTransfer() from acqiris.AcquireTransfer() with timeout=', timeOut)
        status = self.__acqiris_QuantroDLL1.AcquireTransfer(
            self.__instrumentID,
            c_int(timeOut),
            requestedLoopsOrBanks.address(),
            c_bool(voltages),
            wantedChannels2.address(),
            transferAverages.ctypes.data,
            self.lastWaveformArraySizes.ctypes.data,
            self.lastWaveformArray[0].ctypes.data,
            self.lastWaveformArray[1].ctypes.data,
            self.lastWaveformArray[2].ctypes.data,
            self.lastWaveformArray[3].ctypes.data,
            samplingTime.address(),
            nbrSamplesPerSeg.address(),
            nbrSegments.address(),
            self.lastNbrSegmentsArray.ctypes.data,
            c_bool(getHorPos),
            horPosArraySize.address(),
            self.lastHorPositionsArray.ctypes.data,
            c_bool(getTimeStamps),
            timeStampsArraySize.address(),
            self.lastTimeStampsArray.ctypes.data,
            maxDelayBetweenTrigs_s.address(),
            time_s.address(),
            c_bool(True)
        )
        self.debugPrint('back to acqiris.AcquireTransfer()')
        # update the non-array global variables by translating the variables
        # passed to the C DLL function back to Python types
        self.lastTransferredChannel = wantedChannels2.value()
        self.lastTransferAverage = transferAverage
        self.lastSamplingTime = samplingTime.value()
        self.lastNbrSamplesPerSeg = nbrSamplesPerSeg.value()
        self.lastTimeStampsArraySize = timeStampsArraySize.value()
        self.lastHorPositionsArraySize = horPosArraySize.value()
        self.lastWaveIdentifier += 1
        # unlock memory
        self._memoryLocked = False
        # return the status returned by the DLL function
        return status

    def getLastWave(self):
        """
        Return a dictionary with all the information about the last sequence aquired.
        """
        self.debugPrint('in acqiris.getLastWave()')
        if self._memoryLocked:
            return'memory locked'
        lastWave = dict()
        lastWave['identifier'] = self.lastWaveIdentifier
        lastWave['samplingTime'] = self.lastSamplingTime
        lastWave['transferedChannels'] = self.lastTransferredChannel
        lastWave['transferAverage'] = self.lastTransferAverage
        lastWave['nbrSegmentArray'] = self.lastNbrSegmentsArray
        lastWave['nbrSamplesPerSeg'] = self.lastNbrSamplesPerSeg
        lastWave['waveSizes'] = self.lastWaveformArraySizes
        # Note that the array is not copied, but is passed by reference
        lastWave['wave'] = self.lastWaveformArray
        lastWave['timeStampsSize'] = self.lastTimeStampsArraySize
        # Note that the array is not copied, but is passed by reference
        lastWave['timeStamps'] = self.lastTimeStampsArray
        lastWave['horPosSize'] = self.lastHorPositionsArraySize
        # Note that the array is not copied, but is passed by reference
        lastWave['horPos'] = self.lastHorPositionsArray
        lastWave['averageCalculated'] = self.lastAverageCalculated
        # Note that the array is not copied, but is passed by reference
        lastWave['lastAverageArray'] = self.lastAverageArray
        return lastWave

    def StopAcquisition(self):
        """
        Stop the current acquisition (useful in case a problem occurs).
        """
        self.debugPrint('in acqiris.StopAcquisition()')
        status = self.__acqiris_QuantroDLL1.StopAcquisition(
            self.__instrumentID, c_bool(True))

    def calculateAverage(self):
        """
        Calculate the average over the sequence.
        """
        self.debugPrint('in acqiris.calculateAverage()')
        if not self.lastTransferAverage and not self.lastAverageCalculated:
            size = [0, 0, 0, 0]
            for i in range(0, 4):
                if self.lastTransferredChannel & (1 << i):
                    size[i] = self.lastNbrSamplesPerSeg
            self.lastAverageArray = [zeros(size[0]), zeros(
                size[1]), zeros(size[2]), zeros(size[3])]
            nbrSamp = self.lastNbrSamplesPerSeg
            for i in range(0, 4):
                if self.lastTransferredChannel & (1 << i):
                    nbrSeg = self.lastNbrSegmentsArray[i]
                    for j in range(0, nbrSamp):
                        for k in range(0, nbrSeg):
                            self.lastAverageArray[i][
                                j] += self.lastWaveformArray[i][k * nbrSamp + j]
                        self.lastAverageArray[i][j] /= nbrSeg
            self.lastAverageCalculated = True

    def getLastAverage(self, identifier=None, calculate=True):
        """
        Return a dictionary with the averaged sequence if it has been calculated.
        """
        self.debugPrint('in acqiris.getLastAverage()')
        if identifier is not None and identifier != self.lastWaveIdentifier:
            return None
        if not self.lastAverageCalculated and calculate:
            self.calculateAverage()
        if not self.lastAverageCalculated:
            return None
        lastAve = dict()
        lastAve['identifier'] = self.lastWaveIdentifier
        lastAve['averageCalculated'] = self.lastAverageCalculated
        lastAve['lastAverageArray'] = self.lastAverageArray
        return lastAve

    def getLastWaveIdentifier(self):
        """
        Returns the unique identifier of the last sequence aquired.
        """
        self.debugPrint('in acqiris.getLastWaveIdentifier()')
        return self.lastWaveIdentifier

    def FinishApplicationV1(self, *args):
        """
        Terminates the control session of the acqiris digitizer.
        """
        self.debugPrint('in acqiris.FinishApplicationV1()')
        self.__acqiris_QuantroDLL1.FinishApplication(
            self.__instrumentID, c_bool(True))

    def Temperature(self):
        """
        Returns the temperature of the Acqiris card.
        """
        self.debugPrint('in acqiris.Temperature()')
        try:
            self.__acqiris_QuantroDLL1.Temperature(
                self.__instrumentID, byref(self.__temperature), c_bool(True))
        except:
            print "Could not read temperature"
            self.__temperature = c_int32(-1)
        # self.notify("temperature",self.__temperature.value)   # possible
        # automatic notification to a Frontpanel
        return self.__temperature.value

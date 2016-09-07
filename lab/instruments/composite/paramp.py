# imports

import os
import sys
import getopt
import re
import struct
import pickle
import math
import numpy
import scipy
import scipy.optimize
import scipy.interpolate

from qubit_setup.macros.utility_fitting import *

from application.lib.instrum_classes import *
from application.helpers.instrumentmanager.instrumentsmgr import InstrumentManager
from application.lib.datacube import Datacube
from application.lib.smartloop import SmartLoop


# Check if register exists
register = None
try:
    register = InstrumentManager().getInstrument('register')
except:
    print 'Could not find an instrument with name "register"'

# Class definition
initialInstruments = {'biasGen': None, 'pumpGen': None,
                      'testVNA': None, 'testGen': None, 'testFSA': None}

defaultBiasMethodNames = {'setBias': 'setVoltage', 'bias': 'voltage'}
defaultPumpMethodNames = {'setPumpFreq': 'setFrequency', 'pumpFreq': 'frequency', 'setPumpPow': 'setPower',
                          'pumpPow': 'power', 'setPumpPhase': 'setPhase', 'pumpPhase': 'phase', 'setPumpOutput': 'setOutput', 'pumpOutput': 'output'}
defaultVNAMethodNames = {'setVNAFreq': 'setCenterInGHz', 'VNAFreq': 'getCenterInGHz', 'setVNASpan': 'setSpanInGHz', 'VNASpan': 'getSpanInGHz', 'setVNAPow': 'setTotalPower', 'VNAPow': 'totalPower',
                         'setVNABandwidth': 'setVideoBW', 'VNABandwidth': 'videoBW', 'setVNACW': 'setCW', 'VNACW': 'CW', 'VNATrace': 'getFreqMagPhase'}
defaultTestGenMethodNames = {'setTestGenFreq': 'setFrequency', 'testGenFreq': 'frequency',
                             'setTestGenPow': 'setPower', 'testGenPow': 'power', 'setTestGenOutput': 'setOutput', 'testGenOutput': 'output'}
defaultFSAMehtodNames = {'setFSAFreq': 'setCenterInGHz', 'FSAFreq': 'getCenterInGHz', 'setFSASpan': 'setSpanInGHz',
                         'FSASpan': 'getSpanInGHz', 'setFSABandwidth': 'setResBWInHz', 'FSABandwidth': 'getResBWInHz', 'FSATrace': 'getSingleTrace'}
defaultMethodNames = {}
for d in [defaultBiasMethodNames, defaultVNAMethodNames, defaultFSAMehtodNames]:
    defaultMethodNames.update(d)

initialMethods = dict()
for key in defaultMethodNames.keys():
    initialMethods[key] = None

suffixNames = ["-freqOfBias"]


class Instr(Instrument):
    """
    Class for a flux controlled parametric amplifier operated in reflection.
    - This instrument has sub-instruments:
      - a voltage source 'biasGen' for flux DC biasing the paramp;
      - a microwave generator 'pumpGen' for parametric pumping the paramp;
      - a microwave generator generating a test signal;
      - an optional vectorial network analyzer 'testVNA' for calibrating the paramp frequency;
      - an optional spectrum analyzer 'testFSA' for calibrating the paramp gain and bandwidth.

    Each sub-instrument is defined at class initilization, or later using methods setBiasGen, setPumpGen, setTestVNA, or setTestFSA (see doc strings).
    Its specification is given as a tuple (instr,dict) where:
      - instr is the instrument object or its name in the instrument manager;
      - dict is a dictionary with keys 
        * 'setBias' and 'bias' for the flux dc bias generator,
        * 'setPumpFreq', 'pumpFreq','setPumpPow','pumpPow' for the pump microwave generator,
        * 'setVNAFreq','VNAFreq','setVNASpan','VNASpan','setVNAPow','VNAPow','getVNASpectrum' for the test vectorial network analyzer,
        * 'setFSAFreq','FSAFreq','setFSASpan','FSASpan','setFSAPow','FSAPow','getFSASpectrum' for the test frequency spectrum analyzer;
        The dictionary values are the the corresponding method names of the sub-instruments.
    """

    ###################################
    # Initialization
    ###################################

    def initialize(self, biasGen=None, pumpGen=None, testVNA=None, testFSA=None):
        """
        Initializes the paramp instrument
        """
        print 'initializing' + self._name
        self._manager = None
        try:
            # has now a handle to the singleton instrument manager.
            self._manager = InstrumentManager()
        except:
            print "Could not load instrument manager."
        self._subInstruments = initialInstruments
        self._methods = initialMethods
        for name, instrum, defaultMethods in zip(initialInstruments.keys(), [biasGen, pumpGen, testVNA, testFSA], [defaultBiasMethodNames, defaultPumpMethodNames, defaultVNAMethodNames, defaultFSAMehtodNames]):
            self.setSubInstrum(name, instrum, defaultMethods)
        self._params = dict()
        self._freqOfBias = None
        self._biasOfFreq = None
        self._params["slewrateBias"] = 1
        self._freqOfBiasCube = None
        self.restoreState()

    def parameters(self):
        """
        Returns IQ mixer parameters
        """
        return dict(self._params)  # this is a copy

    def saveState(self, directory=None):
        """
        Saves the _param dictionary of the instrument in a file 
        """
        self.debugPrint('saveState with directory = ', directory)
        if directory is None or not os.path.isdir(directory):
            try:
                directory = register[self._name + '_Cal']
                if not os.path.isdir(directory):
                    raise
            except:
                directory = os.getcwd()
        for cube, suffixName in zip([self._freqOfBiasCube], suffixNames):
            if isinstance(cube, Datacube):
                fileName = self._name + suffixName
                path = directory + '/' + fileName
                self.debugPrint('saving ', path)
                cube.savetxt(path, overwrite=True, forceSave=True)
                self._params['dirName'] = directory
                if register is not None:
                    key = self._name + '_Cal'
                    self.debugPrint('storing register key ',
                                    key, ' = ', directory)
                    register[key] = directory

    def restoreState(self, directory=None, create=False):
        """
        Restores the state of the instrument by loading _param dictionary.
        """
        if directory is None or not os.path.isdir(directory):
            try:
                directory = register[self._name + '_Cal']
                if not os.path.isdir(directory):
                    raise
            except:
                directory = os.getcwd()
        self._params['dirName'] = directory
        for cubeName, suffixName in zip(['_freqOfBiasCube'], suffixNames):
            filename = self._name + suffixName
            path = directory + '/' + filename
            try:                                       # 1) try to load from files,
                setattr(self, cubeName, Datacube())
                getattr(self, cubeName).loadtxt(path, loadChildren=True)
                print self._name, ' has loaded calibration datacube ', path
                try:
                    self.makeInterpBiasFreq()
                except:
                    'error in makeInterpBiasFreq'
            except:
                setattr(self, cubeName, None)
                # 2) or create an empty datacube if allowed.
                if create:
                    setattr(self, cubeName, Datacube(filename))

    def setSlewrateBias(self, slewrate):
        '''
        Memorizes the bias source slew rate to be used in setBias commands.
        '''
        self._params["slewrateBias"] = slewrate

    def setSubInstrum(self, name, instrum, defaultMethods):
        """
        Gets handles to a sub-instrument and its requested methods 
        """
        if instrum is None:
            return
        # separate reference to sub-instrument from dictionary of
        # sub-instrument methods
        inst, instDict = instrum
        print inst, insDict
        # do not do anything if sub-instrument is None
        if inst is not None:
            # instr is a string => it's the name of the sub-instrument =>
            # retrieve it from the instrument manager
            if isinstance(inst, str):
                try:
                    inst = self._manager.getInstrument(inst)
                except:
                    print 'instrument ' + inst + ' not found.'
                    raise
            # otherwise assume that inst is the sub-instrument object
            else:
                inst = instr
            # save the sub-instrument object in the sub-instrument dictionary
            self._subInstruments[name] = inst

            # for all expected methods of sub-instrument
            for methodKey in defaultMethods.keys():
                methodName = None
                if instDict is not None and instDict.has_key(methodKey) and hasattr(inst, instDict[methodKey]):
                    methodNam2 = instDict[methodKey]
                elif hasattr(inst, defaultMethods[methodKey]):
                    methodName = defaultMethods[methodKey]
                if methodName is not None:
                    # memorize the methods in the field 'biasGen' of
                    # self._subInstruments dictionary
                    self._methods[methodKey] = getattr(inst, methodName)
                    # self.methodkey aliases now the method inst.methodName
                    setattr(self, methodKey, getattr(inst, methodName))

    def subInstruments(self):
        """
        Return the dictionary of sub-instruments.
        """
        return self._subInstruments

    def methods(self):
        """
        Return the dictionary of methods.
        """
        return self._methods

    def _missing(self, instrumentList, methodList):
        """
        Private utility method for determining if any sub-instrument or method is missing in the lists.
        Display a message and return True (missing) or False (nothing missing).
        """
        missing = any([self._subInstruments[instrumentName] is None for instrumentName in instrumentList]) or not all(
            [hasattr(self, methodName) for methodName in methodList])
        if missing:
            print 'Missing instrument or method.'
        return missing

    ###################################
    # Amplifier center frequency
    ###################################

    def setupVNA(self, center=None, span=None, bandwidth=None, power=None):
        if center is not None and hasattr(self, 'setVNAFreq'):
            self.setVNAFreq(center)
        if span is not None and hasattr(self, 'setVNASpan'):
            self.setVNASpan(span)
        if bandwidth is not None and hasattr(self, 'setVNABandwidth'):
            self.setVNABandwidth(bandwidth)
        if power is not None and hasattr(self, 'setVNAPow'):
            self.setVNAPow(power)

    def calibrateFreq(self, biasStart, biasStop, biasStep=1, VNACenter=None, VNASpan=None, VNABandwidth=None):
        missing = self._missing([], ['setBias', 'VNATrace'])
        if missing:
            return
        self.setupVNA(VNACenter=VNACenter, VNASpan=VNASpan,
                      VNABandwidth=VNABandwidth)
        loop = SmartLoop(biasStart, biasStep, biasStop)
        cube = Datacube(self._name + '-FreqCal')
        cube.toDataManager()
        for bias in loop:
            self.setBias(bias, self._params["slewrateBias"])
            child = self.VNATrace(waitFullSweep=True,
                                  unwindPhase=True, phaseStart=180)
            cube.addChild(child)
            cube.set(bias=bias, freq=self.findFreq(child),
                     columnOrder=['bias', 'freq'], commit=True)
        self._freqOfBiasCube = cube
        self.makeInterpBiasFreq()

    def calToDataManager(self):
        """
        Send the calibration cubes to the data manager.
        """
        if isinstance(self._freqOfBiasCube, Datacube):
            self._freqOfBiasCube.toDataManager()

    def makeInterpBiasFreq(self, save=True):
        """
        Updates the two interpolation function self._params["biasOfFreq"] and .
        """
        cube = self._freqOfBiasCube
        if cube is None:
            return
        self._freqOfBias = scipy.interpolate.interp1d(
            cube['bias'], cube['freq'])
        i1, i2 = numpy.argmin(cube['freq']), numpy.argmax(cube['freq'])
        if i1 > i2:
            i1, i2 = i2, i1
        try:
            self._biasOfFreq = scipy.interpolate.interp1d(
                cube['freq'][i1:i2], cube['bias'][i1:i2])
        except:
            print 'Error in inverse interpolation probably due to non-bijective behavior.'
        if save:
            self.saveState()

    def findFreq(self, child):
        i = indexLastPos = numpy.where(child['phaseCor'] < 0)[0][0] - 1
        x0, x1, y0, y1 = child['freq'][i], child['freq'][
            i + 1], child['phaseCor'][i], child['phaseCor'][i + 1]
        f0 = x0 + (x1 - x0) * y0 / (y0 - y1)
        return f0 / 1e9

    def gotoFreq(self, freqInGHz, setPumpFreq=True):
        """
        Sets the bias to reach a targetted parametric resonator frequency fr, and optionally sets the pumping frequency to twice fr.
        """
        interp = self._biasOfFreq
        noWay = not hasattr(self, 'setBias') or interp is None
        if noWay:
            print 'Missing method "setBias" or interpolation function "biasOfFreq"'
            return
        try:
            bias = interp(freqInGHz)
        except Exception as e:
            print e
            return
        self.setBias(bias, self._params["slewrateBias"])
        if setPumpFreq:
            self.setPumpFreq(2 * freqInGHz)

    ###################################
    # Optimization of the measured output power
    ###################################

    def _optimizeXFromFSA(self, setX, getX):
        """
        Private method for maximizing the power measured on the fsp, as a function of a paratmeter specified by the setX and setY mehtods.
        """
        self.debugPrint('in optimizeBiasFromFSA')
        missing = self._missing([], [setX, getX, 'FSATrace'])
        if missing:
            return

        def myFunction(x):
            getattr(self, setX)(bias)
            time.sleep(0.5)
            return self.powerFSA()
        x0 = getattr(self, getX)()
        result = scipy.optimize.fmin(myFunction, x0)
        return (result[0], result)

    def optimizeBiasFromFSA(self):
        """
        Maximimizes the power measured on the fsp, as a function of the bias.
        """
        return optimizeXFromFSA(self, 'setBias', 'bias')

    def optimizePumpPhaseFromFSA(self):
        """
        Maximimizes the power measured on the fsp, as a function of the bias.
        """
        return optimizeXFromFSA(self, 'setPumpPhase', 'pumpPhase')

    def setupFSA(self, averaging=10, reference=-30):
        """
        Setup fsa
        """
        noWay = not all([hasattr(self, method) for method in [
                        'testGenFreq', 'setFSAFreq', 'setFSASpan', 'setFSABandWidth']])
        if noway:
            return
        bw = 2000
        self.debugPrint('in setupFSA')
        # store previous configurations of fsp,awg for IF, and mwg for LO
        self._fsp.storeConfig("BeforeParampCharac")
        self.setFSAFreq(self.testGenFreq())
        # self.setFSASpan(abs(self.testGenFreq()-self.pumpGenFreq()/2))
        self.setFSASpan(0)
        self.setFSABandWidth(bw)

    def restoreFSA(self):
        """ """
        missing = self._missing(['testFSA'], [])
        if not missing:
            self._fsp.loadConfig("BeforeParampCharac")

    def powerFSA(self):
        """ """
        missing = self._missing([], ['FSATrace'])
        if not missing:
            return numpy.average(self.FSATrace()[1])

    ###################################
    # measure the paramp gain
    ###################################

    def measureGainFromFSA(self):
        self.debugPrint('in measureGainFromFSA')
        missing = not all([hasattr(self, method) for method in [
                          'testGenFreq', 'setFSAFreq', 'setFSASpan', 'setFSABandWidth']])
        if missing:
            return

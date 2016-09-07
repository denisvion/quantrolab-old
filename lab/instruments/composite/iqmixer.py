# imports
import os
import sys
import getopt
import time
import traceback
import scipy
import scipy.optimize
import scipy.interpolate
from numpy import *
from application.lib.instrum_classes import *
from application.lib.datacube import Datacube
from application.helpers.instrumentmanager.instrumentsmgr import InstrumentManager
from macros.optimization import Minimizer
reload(sys.modules['macros.optimization'])
from macros.optimization import Minimizer

register = None
try:
    register = InstrumentManager().getInstrument('register')
except:
    print 'Could not find an instrument with name "register"'

suffixNames = ["_offsetCal", "_SBCal"]
awgCalibWaveformLength = 20000  # samples


class Instr(Instrument):
    """
    IQ Mixer instrumant class that knows its microwave generator, its AWG and its two channel indices, as well as a spectrum analyzer for calibration.
    The class has several methods to correct the dc offsets on I and Q, as well as the amplitude and phase imbalance (complex correction c), by maximizing the sideband image rejection.
    Calibration are stored in datacubes than can be saved, reloaded, and re-initialized with fixed names, but in any directory.
    If a register instrument exists at instrument loading, the last directory used for saving is stored in the register variable. self_name+'_Cal'.
    """

    #####################################################
    #  General methods and interaction with client      #
    #####################################################

    def initialize(self, MWSource, AWG, AWGChannels, fsp, offsetCube=None, sidebandCube=None):
        """
        Initialize instrument.
        """
        instrumentManager = InstrumentManager(
        )  # Bad programming: an instrument should not be able to start an instrument manager
        # => make a composite instrument class able toload its children, and to which an instrument manager can be optionally be passed
        # If the composite instrument has a handle to the manager, it would try to ask the manager to load its children
        # I f not or failure, it would try to load them diirectly.
        # self._name=name
        self._mwg = instrumentManager.getInstrument(MWSource)
        self._fsp = instrumentManager.getInstrument(fsp)
        self._awg = instrumentManager.getInstrument(AWG)
        self._params = dict()
        self._params["MWSource"] = MWSource
        self._params["AWG"] = AWG
        self._params["AWGChannels"] = AWGChannels
        maxPoint = awgCalibWaveformLength
        try:
            maxPoint = self._awg.maxPoints()
        except:
            print "Cannot read the maximum number of points per channel => will use ", maxPoint, "."
        self._params["AWGMaxPoints"] = maxPoint
        self._params["AWGAmpCal"] = 2         # volt(s)
        self._params["fsp"] = fsp
        # directory name for offset and sideband calibration files
        self._params["dirName"] = None
        self._offsetCalCube = None            # datacube for offset calibration data
        self._sidebandCalCube = None          # datacube for sideband calibration data
        # datacube for storing a set of minimization process
        self._topOptiCube = None
        # datacube for storing a single minimization process
        self._optiCube = None

        self._iOffsetInterpolation = lambda x: 0
        self._qOffsetInterpolation = lambda x: 0

        self.loadCal()                      # try to load existing calibration if available

    def saveState(self, directory=None):
        """
        Saves the state of the instrument.
        Here simply aliases saveCal().
        """
        self.saveCal(directory)

    def restoreState(self, directory=None):
        """
        Restores the state of the instrument.
        Here simply aliases loadCal().
        """
        self.loadCal(directory)

    def reInitCal(self, save=True, directory=None):
        """
        Set the two calibration cubes to None.
        """
        self._offsetCalCube = None
        self._sidebandCalCube = None

    def setCal(self, offsetCalCube=None, sidebandCalCube=None):
        """
        Set the two calibration cubes to passed ones.
        """
        for calCube, newCalCube in zip(['_offsetCalCube', '_sidebandCalCube'], [offsetCalCube, sidebandCalCube]):
            if isinstance(newCalCube, Datacube):
                self.set_attr(calCube, newCalCube)

    def saveCal(self, directory=None):
        """
        Save offset and sideband calibration datacubes to files in a specified directory, or in a directory found in the register's variable, or in the current directorty.
        Filenames are fixed and made of the mixer's name and suffix "-offsetCal" or "-sidebandCal".
        Update register variable _name+'_Cal' with new directory name.
        """
        self.debugPrint('saveCal with directory = ', directory)
        if directory is None or not os.path.isdir(directory):
            try:
                directory = register[self._name + '_Cal']
                if not os.path.isdir(directory):
                    raise
            except:
                directory = os.getcwd()
        for cube, suffixName in zip([self._offsetCalCube, self._sidebandCalCube], suffixNames):
            if isinstance(cube, Datacube):
                path = directory + '/' + self._name + suffixName
                self.debugPrint('saving ', path)
                cube.savetxt(path, overwrite=True, forceSave=True)
                self._params['dirName'] = directory
                if register is not None:
                    key = self._name + '_Cal'
                    self.debugPrint('storing register key ',
                                    key, ' = ', directory)
                    register[self._name + '_Cal'] = directory

    def loadCal(self, directory=None, create=False):
        """
        Loads offset and sideband calibration cubes from files located either in a specified directory, or in directory found in the register, or in the current directory. 
        Filenames are fixed and made of the mixer name and suffix "-offsetCal" and "-sidebandCal".
        If create is true, creates empty calibration cube if could not load existing one.
        """
        print 'in loadCal'
        if directory is None or not os.path.isdir(directory):
            try:
                directory = register[self._name + '_Cal']
                if not os.path.isdir(directory):
                    raise
            except:
                directory = os.getcwd()
        self._params['dirName'] = directory
        for calCube, suffixName in zip(['_offsetCalCube', '_sidebandCalCube'], suffixNames):
            filename = self._name + suffixName
            path = directory + '/' + filename
            try:                                        # 1) try to load from files,
                setattr(self, calCube, Datacube())
                getattr(self, calCube).loadtxt(path, loadChildren=True)
                register[self._name + '_Cal'] = directory
                print self._name, ' has loaded calibration datacube ', path
            except:
                print 'could not open' + path
                setattr(self, calCube, None)
                # 2) or create an empty datacube if allowed.
                if create:
                    setattr(self, calCube, Datacube(filename))

    def setOffsetCalibration(self, datacube):
        """set the offset calibration datacube"""
        self._offsetCalCube = datacube
        self.updateOffsetCalInterpolation()

    def setSidebandCalibration(self, datacube):
        """set the sideband calibration datacube"""
        self._sidebandCalCube = datacube

    def parameters(self):
        """
        Returns IQ mixer parameters
        """
        return self._params

    def offsetCalibrationData(self):
        """
        Return offset calibration datacube
        """
        return self._offsetCalCube

    def sidebandCalibrationData(self):
        """
        Return sideband calibration datacube
        """
        return self._sidebandCalCube

    def calibrationData(self):
        """
        Return calibration data as a dictionary {'offsetCal':offsetCalCube,'sidebandCal':sidebandCalCube}
        """
        return({'offsetCal': self._offsetCalCube, 'sidebandCal': self._sidebandCalCube})

    def calToDataManager(self):
        """
        Send the two calibration cubes to the data manager.
        """
        if isinstance(self._offsetCalCube, Datacube):
            self._offsetCalCube.toDataManager()
        if isinstance(self._sidebandCalCube, Datacube):
            self._sidebandCalCube.toDataManager()

    def optToDataManager(self):
        """
        Send the last optimization cube to the data manager.
        """
        if isinstance(self._topOptiCube, Datacube):
            self._topOptiCube.toDataManager()

    def setAWGAmpCal(self, amplitude):
        """
        Sets the amplitude to be used on the AWG for calibrations.
        """
        self._params["AWGAmpCal"] = amplitude

    def getAWGAmpCal(self):
        """
        Sets the amplitude to be used on the AWG for calibrations.
        """
        return self._params["AWGAmpCal"]

    #########################################
    #  Sideband generation and loading      #
    #########################################

    def generateSidebandWaveform(self, IF=0, c=None, phi=None, length=None, delay=0, normalize=True, useCalibIfNone=True, LO=None):
        """
        Generates a complex sideband waveform using a sideband frequency "IF", and a complex correction |c|exp(j phi), i.e. |c|cos(phi) on I and |c|sin(phi) on Q. 
        I + j Q = exp(-2 pi IF (t+delay)) + |c|exp(j phi) exp(+2 pi IF (t+delay))
          - If c or phi is None and useCalibIfNone is true, try to use calibration values.
          - If c or phi is None and useCalibIfNone is False, take zero correction.
          - otherwise use the passed values.
        The complex waveform encodes two AWG channels for I and Q
        """
        if length is None:
            length = self._params["AWGMaxPoints"]
        self.debugPrint('in generateSidebandWaveform')
        if length == 0:
            return array([])
        waveformIQ = zeros((max(1, length)), dtype=complex128)
        times = arange(0, length, 1)
        if any([c, phi]) is None:
            c1, phi1 = 0, 0
            if useCalibIfNone:                            # get corrections from calibration
                try:
                    if LO is None:
                        LO = self._mwg.frequency()    # as corrections depend on LO, get it if not provided
                    self.debugPrint(
                        'calling sidebandCorrection with LO = ', LO, ' and IF = ', IF)
                    c1, phi1 = self.sidebandCorrection(LO, IF)
                except Exception as e:
                    print e
            if c is None:
                c = c1
            if phi is None:
                phi = phi1
        self.debugPrint('using corrections c,phi = ', c, ', ', phi)
        # see A. Dewes' thesis page 87
        # C,PHI divided by 20 so that first increment of 1 represents 1/20=5%
        # of amplitude and 3deg
        cr = c * exp(1j * phi)
        waveformIQ = exp(-2.0j * pi * IF * (times + float(delay)))
        waveformIQ = 0.5 * (waveformIQ + cr * conj(waveformIQ))
        return waveformIQ

    def loadSidebandWaveform(self, IF=0, c=None, phi=None, length=None, useCalibIfNone=True):
        """
        Generates and loads the proper iq waveform for sideband calibration into the awg.
        Waveforms for I and Q are stored in awg files "SB_cal_I" and "SB_cal_Q" for fast reloading.
        """
        if length is None:
            length = self._params["AWGMaxPoints"]
        self.debugPrint('in loadSidebandWaveform with IF = ', IF)
        channels = self._params["AWGChannels"]
        waveform = self.generateSidebandWaveform(
            IF=IF, c=c, phi=phi, useCalibIfNone=useCalibIfNone, length=length)
        self._awg.loadiqWaveform(waveform, channels=self._params["AWGChannels"], waveformNames=[
                                 "SBCalI-" + str(channels[0]), "SBCalQ-" + str(channels[1])])
        return waveform

    def setSidebandWaveform(self):
        """
        Reloads existing awg I and Q sideband waveforms dedicated to sideband calibration.
        Waveforms are awg files "SB_cal_I" and "SB_cal_Q"
        """
        channels = self._params["AWGChannels"]
        self._awg.setWaveform(channels[0], "SBCalI-" + str(channels[0]))
        self._awg.setWaveform(
            channels[1], "SBCalQ-" + str(channels[1]))  # PROBABLY USELESS

    #########################################
    #  Calibrations                         #
    #########################################

    def calibrate(self, IForIFRange, offsetOnly=False, optToDataMan=False, calToDataMan=False):
        """
        Calibrate an IQ mixer using fsp at 1 carrier frequency.
        """
        IFRange = IForIFRange
        if not hasattr(IForIFRange, "__iter__"):
            IFRange = [IForIFRange]
        print 'calibration in progress'
        self.calibrateIQOffset(optToDataMan=optToDataMan,
                               calToDataMan=calToDataMan)
        if not offsetOnly:
            self.calibrateSideband(
                IFRange=IFRange, optToDataMan=optToDataMan, calToDataMan=calToDataMan)
        print 'calibration ended'

    def calibrateIQOffset(self, LORange=None, reference=-5, method="scipy.optimize.fmin", save=True, optToDataMan=False, calToDataMan=False):
        """
        Calibrate the IQ mixer DC offsets at a series of LO frequencies
        """
        self.debugPrint('in calibrateIQOffset with LORange, save, optToDataMan,calToDataMan = ',
                        (LORange, save, optToDataMan, calToDataMan))
        if LORange is None:
            # use current carrier frequency if not specified
            LORange = [self._mwg.frequency()]
        elif isinstance(LORange, [float, int]):
            LORange = [LORange]  # make a list if single frequency
        channels = self._params["AWGChannels"]
        try:
            # setup the different generators
            self.setup(reference=reference)
            if not self._offsetCalCube:
                self._offsetCalCube = Datacube(
                    name=self._name + suffixNames[0])
            cube = self._offsetCalCube
            self.dictCube(cube)
            if calToDataMan:
                cube.toDataManager()
            self.debugPrint('setting awg')
            for channel in channels:
                self._awg.setWaveform(channel, 'zeroes')
            self._awg.setState(channels, [True] * len(channels))
            self._awg.runAWG()
            self._mwg.turnOn()
            self.debugPrint('creating cu datacube')
            cu = self._topOptiCube = Datacube(name=self._name + '_offsetOptim')
            if optToDataMan:
                cu.toDataManager()
            LOpower = self._mwg.power()
            for LO in LORange:                                      # loop over LO frequencies
                cu.set(LO_dBm=LOpower, LO_GHz=LO, columnOrder=[
                       'LO_dBm', 'LO_GHz'], commit=True)
                self._optiCube = Datacube(name='LO_GHz=' + str(LO))
                cu.addChild(self._optiCube)
                self._mwg.setFrequency(LO)
                # self._mwg.turnOn()
                self._fsp.write("SENSE1:FREQUENCY:CENTER %f GHZ" % LO)
                time.sleep(1)
                if method == "scipy.optimize.fmin":                    # find minimum power
                    (voltages, minimum) = self.optimizeIQMixerPowell(
                        replaceOptiCube=False)
                elif method == "vs.fmin":
                    (voltages, minimum) = self.optimizeIQMixerVS(
                        replaceOptiCube=False)
                else:
                    raise Error("bad method selected !!")
                minimum = self.measurePower(voltages)
                print "Optimum value of %g dBm at offset %g V, %g V" % (minimum, voltages[0], voltages[1])
                cube = self._offsetCalCube
                print "trying to search"
                try:                                                  # remove outdated offset at the same frequency
                    cube.removeRows(cube.search(LO_GHz=LO))
                except:
                    # and store in the offset cube
                    print "search or remove error"
                cube.set(LO_dBm=LOpower, LO_GHz=LO, lowI=voltages[0], lowQ=voltages[
                         1], RF_dBm=minimum, columnOrder=['LO_dBm', 'LO_GHz', 'lowI', 'lowQ', 'RF_dBm'], commit=True)
                # sort in frequency
                cube.sortBy("LO_GHz")
                if save:
                    # and save in file if requested
                    cube.savetxt(overwrite=True)
        except:
            raise
        finally:
            self.teardown()                                         # restore all generator
            # update interpolation function
            self.updateOffsetCalInterpolation()
            LO = self._mwg.frequency()
            # set the I and Q offsets on the AWG
            self._awg.setOffset(channels[0], self.iOffset(LO))
            self._awg.setOffset(channels[1], self.qOffset(LO))

    def calibrateSideband(self, LORange=None, IFRange=arange(-0.5, 0.51, 0.1), reference=0, method="scipy.optimize.fmin", save=True, optToDataMan=False, calToDataMan=False):
        """
        Calibrate the IQ mixer in sideband generation for a set of LO frequencies and a set of IF frequencies.
        """
        self.debugPrint('in calibrateSideband with LORange, IFRange, save, optToDataMan,calToDataMan = ',
                        (LORange, IFRange, save, optToDataMan, calToDataMan))
        if LORange is None:
            LORange = [self._mwg.frequency()]
        elif isinstance(LORange, [float, int]):
            LORange = [LORange]
        try:
            # setup the different generators
            self.setup(reference=reference)
            if not isinstance(self._sidebandCalCube, Datacube):
                self._sidebandCalCube = Datacube(name=self._name + '_SBCal')
            # this is the final calibration cube
            cube = self._sidebandCalCube
            if calToDataMan:
                cube.toDataManager()
            self.dictCube(cube)
            self._mwg.turnOn()
            channels = self._params["AWGChannels"]
            # probably useless call since successive waveforms will be loaded
            # later by loadSidebandWaveform
            self.setSidebandWaveform()
            self._awg.runAWG()
            # start requested channels
            self._awg.setState(channels, [True] * len(channels))
            # this is the optimization cube for control
            cu = self._topOptiCube = Datacube(name=self._name + '_SBOptim')
            if optToDataMan:
                cu.toDataManager()
            for LO in LORange:                                      # loop over LO frequencies
                # center frequency rounded to 1 MHz
                LO = round(LO, 3)
                self._mwg.setFrequency(LO)
                # self._awg.setAmplitude(channels[0],1)  # Displaced in setup awg
                # self._awg.setAmplitude(channels[1],1)
                self._awg.setOffset(channels[0], self.iOffset(LO))
                self._awg.setOffset(channels[1], self.qOffset(LO))
                cu.set(LO_dBm=self._mwg.power(), LO_GHz=LO,
                       columnOrder=['LO_dBm', 'LO_GHz'], commit=True)
                if cube.column('LO_GHz') is None or LO not in cube.column('LO_GHz'):
                    cube.set(LO_dBm=self._mwg.power(), LO_GHz=LO,
                             columnOrder=['LO_dBm', 'LO_GHz'], commit=True)
                    child = Datacube("LO_GHz=%g" % LO)
                    cube.addChild(child, LO_GHz=LO)
                else:
                    child = cube.children(LO_GHz=LO)[-1]
                # child cube at a particular LO carrier LO to gather grand
                # children cubes
                cuChild = Datacube("LO_GHz=%g" % LO)
                cu.addChild(cuChild)
                for IF in IFRange:                                     # loop over IF frequencies
                    cuChild.set(IF_GHz=IF, commit=True)
                    # optimization grandchild cube at a particular couple
                    # (LO,IF)
                    self._optiCube = Datacube("IF_GHz=%g" % IF)
                    cuChild.addChild(self._optiCube)
                    print "LO_GHz=%g, IF_GHz=%g" % (LO, IF)
                    self._fsp.write(
                        "SENSE1:FREQUENCY:CENTER %f GHZ" % (LO - IF))
                    time.sleep(1)
                    print "minimizing"
                    if method == "scipy.optimize.fmin":
                        # defines the directions, as well as the initial steps
                        # (1 means 100% correction and 1 radian)
                        direc = eye(2, dtype=float) * 0.1
                        result = scipy.optimize.fmin_powell(lambda x, *args: self.measureSidebandPower(x, *args), [0, 0], args=[
                                                            IF], direc=direc, full_output=1, xtol=0.001, ftol=1e-2, maxiter=50, maxfun=50, disp=True, retall=True)
                    elif method == "vs.fmin":
                        minimizer = Minimizer(lambda x: self.measureSidebandPower(x, IF_GHz=IF), [
                                              0., 0.], [[-0.2, 0.2], [-2, 2]], xtol=[0.01, 0.01], maxfun=20, maxiter=3)
                        minimizer.minimize()
                        result = minimizer.result()
                    else:
                        raise Error("bad method selected !!")
                    params = result[0]
                    value = result[1]
                    print "LO_GHz=%g, IF_GHz=%g, c = %g, phi = %g rad : value = %g" % (LO, IF, params[0], params[1], self.measureAveragePower())
                    self.loadSidebandWaveform(IF=IF, c=params[0], phi=params[
                                              1], length=self._params["AWGMaxPoints"])
                    child.set(LO_GHz=LO, IF_GHz=IF, absC=params[0], argC_rad=params[
                              1], columnOrder=['LO_GHz', 'IF_GHz', 'absC', 'argC_rad'])
                    # measure the different sidebands
                    for i in [-3, -2, -1, 0, 1, 2, 3]:
                        self._fsp.write(
                            "SENSE1:FREQUENCY:CENTER %f GHZ" % (LO + IF * i))
                        time.sleep(1)
                        if i < 0:
                            suppl = "m"
                        else:
                            suppl = ""
                        power = self.measureAveragePower()
                        child.set(**{"p_sb%s%d" % (suppl, abs(i)): power})
                        print "Power at ", (LO + IF * i), " GHz: ", power
                    child.commit()
                if save:
                    cube.savetxt(overwrite=True)
        except:
            raise
        finally:
            self.teardown()

    #########################################
    #  optimization                         #
    #########################################

    def setup(self, averaging=10, reference=-30):
        """
        Memorize MWG, AWG, and FSP setting and setup for the IQ mixer calibration.
        """
        self.debugPrint('in setup with averaging,reference = ',
                        (averaging, reference))
        # store previous configurations of fsp,awg for IF, and mwg for LO
        self._fsp.storeConfig("BeforeIQCal")
        self._awg.saveSetup("BeforeIQCal.awg")
        self.memorizeAWGOffsets()                           # correct a bug of the AWG
        self._mwgState = self._mwg.saveState("BeforeIQCal")
        self.setupFSP(averaging, reference)
        self.setupAWG()                               # call awg setup function

    def setupFSP(self, averaging=10, reference=-30):
        """
        Setup fsp for calibration
        """
        self._fsp.write("SENSE1:FREQUENCY:SPAN 0 MHz")
        self._fsp.write("SWE:TIME 2 ms")
        rbw = 10000
        self._fsp.write("SENSE1:BAND:RES %f Hz" % rbw)
        self._fsp.write("SENSE1:BAND:VIDEO AUTO")
        self._fsp.write("TRIG:SOURCE EXT")
        self._fsp.write("TRIG:HOLDOFF 0.000 s")
        self._fsp.write("TRIG:LEVEL 0.5 V")
        self._fsp.write("TRIG:SLOP POS")
        self._fsp.write("SENSE1:AVERAGE:COUNT %d" % averaging)
        self._fsp.write("SENSE1:AVERAGE:STAT1 ON")
        self._fsp.write("DISP:TRACE1:Y:RLEVEL %f" % reference)

    def memorizeAWGOffsets(self):
        """
        Corrects a bug of AWG5014B that does not save the offsets when saving the setup
        """
        self._awgOffsets = [self._awg.offset(
            i + 1) for i in range(self._awg.channels())]

    def restoreAWGOffsets(self):
        """
        Corrects a bug of AWG5014B that does not save the offsets when saving the setup
        """
        for i in range(1, self._awg.channels()):
            self._awg.setOffset(i + 1, self._awgOffsets[i])

    def setupAWG(self):
        """
        Setup AWG waveforms for the IQ mixer calibration.
        """
        self.debugPrint('in setupAWG')
        self._awg.write("AWGC:RMOD CONT")
        #period = int(1.0/self._awg.repetitionRate()*1e9)
        amplitude = self._params["AWGAmpCal"]
        channels = self._params["AWGChannels"]
        self._awg.setAmplitude(channels[0], amplitude)
        self._awg.setAmplitude(channels[1], amplitude)
        le = self._params["AWGMaxPoints"]
        waveformOffset = zeros((le))
        #waveformActive = zeros((le))
        #waveformPassive = zeros((le))-1.0
        self._markers = zeros((le), dtype=uint8)
        self._markers[1:len(self._markers) / 2] = 255
        self._awg.createRawWaveform(
            "zeroes", (waveformOffset + 1.0) / 2.0 * ((1 << 14) - 1), self._markers, "INT")
        #self.loadSidebandWaveform(IF=0, c=0, phi=0)

    def teardown(self):
        """
        Restore the original configuration of fsp,awg, and mwg.
        """
        self._fsp.loadConfig("BeforeIQCal")
        self._awg.loadSetup("BeforeIQCal.awg")
        self.restoreAWGOffsets()
        self._mwg.restoreState(self._mwgState)

    def dictCube(self, cube):
        "set the parameters of one of the two calibration datacubes."
        if cube:
            params = dict()
            params["LO_dBm"] = self._mwg.power()
            params["channels"] = self._params["AWGChannels"]
            params["mwg"] = self._mwg.name()
            params["awg"] = self._awg.name()
            params["fsp"] = self._fsp.name()
            cube.setParameters(params)

    def optimizeIQMixerVS(self, replaceOptiCube=True):
        if replaceOptiCube or not isinstance(self._optiCube, Datacube):
            self._optiCube = Datacube(name='IQMixerVS')
        print "optimizing with IQMixerVS"
        time.sleep(1)
        minimizer = Minimizer(lambda x: self.measurePower(x), [0., 0.], [
                              [-0.2, 0.2], [-0.2, 0.2]], xtol=[0.0005, 0.0005], maxfun=100, maxiter=50)
        minimizer.minimize()
        return minimizer.result()

    def optimizeIQMixerPowell(self, x0Limit=.1, replaceOptiCube=True):
        """
        Use Powell's biconjugate gradient method to minimize the power leak in the IQ mixer.
        """
        if replaceOptiCube or not isinstance(self._optiCube, Datacube):
            self._optiCube = Datacube(name='IQMixerPowell')
        self.debugPrint('in optimizeIQMixerPowell with x0Limit = ', x0Limit)
        x0 = [0, 0]
        for i in [0, 1]:
            x0[i] = self._awg.offset(self._params["AWGChannels"][i])
            if x0Limit is not None and abs(x0[i]) > abs(x0Limit):
                x0[i] = x0Limit
        result = scipy.optimize.fmin_powell(lambda x: self.measurePower(
            x), x0, full_output=1, xtol=0.00005, ftol=1e-3, maxiter=100, maxfun=50, disp=True, retall=True)
        #result = scipy.optimize.fmin(lambda x: self.measurePower(x),[0.,0.],full_output = 1,xtol = 0.001,ftol = 1e-2,maxiter =50,maxfun =50, disp=True, retall=True)
        return (result[0], result)

    def measurePower(self, lows):
        """
        Measure the leaking power of the IQ mixer at a given point.
        """
        self.debugPrint('in measurePower with lows = ', lows)
        for i in [0, 1]:
            if math.fabs(lows[i]) > 0.6:
                return 100.0
            self._awg.setOffset(self._params["AWGChannels"][i], lows[i])
        power = self.measureAveragePower()
        self.debugPrint('Measuring power at ', lows[0], lows[1], ': ', power)
        self._optiCube.set(I_V=lows[0], Q_V=lows[1], RF_dBm=power, columnOrder=[
                           'I_V', 'Q_V', 'RF_dBm'], commit=True)
        linpower = math.pow(10.0, power / 10.0) / 10.0
        return power

    def measureAveragePower(self):
        self.debugPrint('in measureAveragePower')
        trace = self._fsp.getSingleTrace()
        if trace is None:
            print "returning trace error"
            return 0
        minimum = mean(trace[1])
        return minimum

    def measureSidebandPower(self, x, IF):
        """measure a sideband power at sideband frequency IF."""
        c = x[0]
        phi = x[1]
        if abs(c) > 1.:
            return 100
        # if abs(phi)>3:
            # return 100
        self.loadSidebandWaveform(
            IF=IF, c=c, phi=phi, length=self._params["AWGMaxPoints"])
        time.sleep(0.5)
        power = self.measureAveragePower()
        self._optiCube.set(absC=c, argC_rad=phi, RF_dBm=power, columnOrder=[
                           'absC', 'argC_rad', 'RF_dBm'], commit=True)
        print "Sideband power at IF = %g GHz,absC = %g, argC_rad = %g : %g dBm" % (IF, c, phi, power)
        return power

    def measureSidebandPower2(self, x, IF):
        i = x[0]
        q = x[1]
        c = sqrt(i**2 + q**2)
        if c > 1:
            print "bound"
            return 0
        phi = math.atan2(q, i)
        self.loadSidebandWaveform(
            IF=IF, c=c, phi=phi, length=self._params["AWGMaxPoints"])
        power = self.measureAveragePower()
        print "Sideband power at IF = %g GHz,i = %g, q = %g, absC=%g, argC_rad=%g : %g dBm" % (IF, i, q, c, phi, power)
        return power

    #########################################
    #  interpolation function               #
    #########################################

    def updateOffsetCalInterpolation(self):
        """
        Builts or rebuilts the two  I offset and Q offset interpolation functions of the LO frequency, using the offset calibration cube if it exists.
        """
        cube = self._offsetCalCube
        if cube and 'LO_GHz' in cube.names():
            if len(cube.column('LO_GHz')) > 1:
                freqs, iOffsets, qOffsets = cube.column(
                    'LO_GHz'), cube.column('lowI'), cube.column('lowQ')
                self._iOffsetInterpolation = scipy.interpolate.interp1d(
                    freqs, iOffsets)
                self._qOffsetInterpolation = scipy.interpolate.interp1d(
                    freqs, qOffsets)
            elif len(cube.column('LO_GHz')) == 1:
                self._iOffsetInterpolation = lambda x: cube.column('lowI')[0]
                self._qOffsetInterpolation = lambda x: cube.column('lowQ')[0]

    def iOffset(self, LO):
        """
        Returns the I offset at a carrier frequency LO, using the interpolation function _iOffsetInterpolation.
        """
        return self._iOffsetInterpolation(LO)

    def qOffset(self, LO):
        """
        Returns the Q offset at a carrier frequency LO, using the interpolation function _iOffsetInterpolation.
        """
        return self._qOffsetInterpolation(LO)

    def offsetCorrection(self, LO):
        """
        Returns a tuple of the I and Q offsets at a carrier frequency f=LO, using the interpolation functions _iOffsetInterpolation and _qOffsetInterpolation.
        """
        return (self._qOffsetInterpolation(f), self._qOffsetInterpolation(f))

    def sidebandCorrection(self, LO, IF):
        """
        Returns a tuple of interpolated c and phi correction parameters at carrier frequency LO and IF frequency IF.
        """
        self.debugPrint('in sidebandCorrection with LO=', LO, ' and IF =', IF)
        cube = self._sidebandCalCube
        if cube and cube.children(LO_GHz=LO) == []:
            print 'No value in sidebandCalibrationData'
            self.debugPrint('corrections c = 0, phi =0')
            return (0, 0)
        try:
            calibrationData = self._sidebandCalCube.children(LO_GHz=LO)[-1]
            rows = calibrationData.search(IF_GHz=IF)
            self.debugPrint(rows)
            if rows == []:
                try:
                    if len(calibrationData['IF_GHz']) > 1:
                        calibrationData.sortBy('IF_GHz')
                        cList = calibrationData.column("absC")
                        phiList = calibrationData.column("argC_rad")
                        IFList = calibrationData.column("IF_GHz")
                        self.debugPrint('absC', cList, 'argC_rad',
                                        phiList, 'IF_GHz', IFList)
                        try:
                            self.debugPrint("trying to interpolate")
                            phiInterpolation = scipy.interpolate.interp1d(
                                IFList, phiList)
                            cInterpolation = scipy.interpolate.interp1d(
                                IFList, cList)
                            c = cInterpolation(IF)
                            phi = phiInterpolation(IF)
                            self.debugPrint('c', c, 'phi', phi)
                            print c, phi
                            return c, phi
                        except Exception as e:
                            print e
                            print "interpolation failed"
                except:
                    print "unknown error in sidebandCorrection"
                    return (0, 0)
            elif rows != []:
                c, phi = calibrationData.column(
                    "absC")[rows[-1]], calibrationData.column("argC_rad")[rows[-1]]
            else:
                c, phi = calibrationData.column(
                    "absC")[-1], calibrationData.column("argC_rad")[-1]
            debugPrint('found corrections c = ', c, ' phi = ', phi)
            return (c, phi)
        except Exception as e:
            raise
            print e, "(error 4)"
            return (0, 0)

    def calCorrection(self, LO, IF):
        try:
            (iO, qO) = (self.iOffset(LO), self.qOffset(LO))
            (c, phi) = self.sidebandCorrection(LO, IF)
            return {'i0': iO, 'q0': qO, 'c': c, 'phi': phi}
        except:
            raise
            print "unable to find correct parameters -> return (0,0,0,0)"
            return {'i0': 0, 'q0': 0, 'c': 0, 'phi': 0}

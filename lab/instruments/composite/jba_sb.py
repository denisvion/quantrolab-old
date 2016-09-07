import sys
import getopt
import numpy
from matplotlib.pyplot import *
from application.lib.instrum_classes import *
from application.helpers.instrumentsmanager import Manager
from numpy import *
register = Manager().getInstrument('register')
import time
import numpy.linalg
import scipy
import scipy.interpolate
import scipy.optimize
import copy
from application.lib.instrum_classes import *
from application.lib.datacube import Datacube
from application.helpers.datamanager.datamgr import DataManager
from application.helpers.instrumentsmanager import Manager
from application.lib.datacube import Datacube
from macros.advancedFitFunctions import *
import scipy
import time
from numpy import *
import numpy as np
from scipy import linalg
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import random
from sklearn import mixture, preprocessing, pipeline
from application.helpers.datamanager.datamgr import DataManager

from macros.fit_functions2 import *
reload(sys.modules['macros.fit_functions2'])
from macros.fit_functions2 import *


from numpy import *
import numpy as np
import random
from sklearn import mixture, preprocessing, pipeline

dataManager = DataManager()


__DEBUG__ = False


class Instr(Instrument):

    """
    Single frequency JBA - VS 2012/01
    Virtual Instrument able to generate and analyse JBA signals.
    """

    def saveState(self, name):
        d = self._params
        try:
            d["frequency"] = self._frequency
            d["amplitude"] = self._amplitude
            d["shape"] = self._shapeParams
            d["bit"] = self.bit
            d["maxVoltage"] = self.maxVoltage
        except Exception as ex:
            print ex
            pass
        return d

    def restoreState(self, state):

        self.bit = state["bit"]
        try:
            self.maxVoltage = state["maxVoltage"]
        except:
            raise
        self._shapeParams = state["shape"]
        self.shape[10000 + self._shapeParams["offsetDelay"]:10000 + self._shapeParams["offsetDelay"] +
                   self._shapeParams["risingTime"]] = linspace(0, 1, self._shapeParams["risingTime"])
        self.shape[10000 + self._shapeParams["offsetDelay"] + self._shapeParams["risingTime"]:10000 +
                   self._shapeParams["offsetDelay"] + self._shapeParams["risingTime"] + self._shapeParams["plateauLength"]] = 1
        self.shape[10000 + self._shapeParams["offsetDelay"] + self._shapeParams["risingTime"] + self._shapeParams["plateauLength"]:10000 + self._shapeParams["offsetDelay"] +
                   self._shapeParams["risingTime"] + self._shapeParams["plateauLength"] + self._shapeParams["risingTime"]] = linspace(1, self._shapeParams["plateau"], self._shapeParams["risingTime"])
        self.shape[10000 + self._shapeParams["offsetDelay"] + self._shapeParams["risingTime"] + self._shapeParams["plateauLength"] + self._shapeParams["risingTime"]:10000 + self._shapeParams[
            "offsetDelay"] + self._shapeParams["risingTime"] + self._shapeParams["plateauLength"] + self._shapeParams["risingTime"] + self._shapeParams["latchLength"]] = self._shapeParams["plateau"]

        self.setFrequency(state["frequency"])
        self.setAmplitude(state["amplitude"])

        # self.sendWaveform()

        return None

    def startJBA(self):
        self._started = True
        self._pulseGenerator.startPulse(name=self.name())
        self._pulseAnalyser.startAnalyseFrequency(name=self.name())

    def stopJBA(self):
        self._started = False
        self._pulseGenerator.stopPulse(name=self.name())
        self._pulseAnalyser.stopAnalyseFrequency(name=self.name())

    def initialize(self, name, generator, analyser, magnitudeButton='formAmplitude'):
        """
        Initialize instrument, and define default shape in self.shape
        """
        print "loading JBA"
        instrumentManager = Manager()
        self._pulseGenerator = instrumentManager.getInstrument(generator)
        self._pulseAnalyser = instrumentManager.getInstrument(analyser)
        self._params = dict()
        self._params["pulseGenerator"] = generator
        self._params["pulseAnalyser"] = analyser
        self._change = True
        self._started = True
        self._magnitudeButton = magnitudeButton
        self.data = Datacube()
        try:
            self._variableAttenuator = instrumentManager.getInstrument(
                'jba_att')
        except:
            raise
        self._shapeParams = dict()
        print "shape params reinisitlised"
        self._shapeParams["startingTime"] = 10000
        self._shapeParams["risingTime"] = 10
        self._shapeParams["plateauLength"] = 200
        self._shapeParams["latchLength"] = 1000
        self._shapeParams["plateau"] = 0.85
        self._shapeParams["offsetDelay"] = 0

        self.generateShape()

        self.bit = int(self.name()[-1]) - 1
        self._phase = 0
        self._nLoopsMax = 70

    def generateShape(self):
        """
        Use the folowing dictionary to generate the shape:
        self._shapeParams["startingTime"] 
        self._shapeParams["risingTime"]    
        self._shapeParams["plateauLength"] 
        self._shapeParams["latchLength"]   
        self._shapeParams["plateau"]       
        self._shapeParams["offsetDelay"] 
        """
        self.shape = zeros((20000))

        self.shape[self._shapeParams["startingTime"] + self._shapeParams["offsetDelay"]:self._shapeParams["startingTime"] +
                   self._shapeParams["offsetDelay"] + self._shapeParams["risingTime"]] = linspace(0, 1, self._shapeParams["risingTime"])
        self.shape[self._shapeParams["startingTime"] + self._shapeParams["offsetDelay"] + self._shapeParams["risingTime"]:self._shapeParams[
            "startingTime"] + self._shapeParams["offsetDelay"] + self._shapeParams["risingTime"] + self._shapeParams["plateauLength"]] = 1
        self.shape[self._shapeParams["startingTime"] + self._shapeParams["offsetDelay"] + self._shapeParams["risingTime"] + self._shapeParams["plateauLength"]:self._shapeParams["startingTime"] + self._shapeParams[
            "offsetDelay"] + self._shapeParams["risingTime"] + self._shapeParams["plateauLength"] + self._shapeParams["risingTime"]] = linspace(1, self._shapeParams["plateau"], self._shapeParams["risingTime"])
        self.shape[self._shapeParams["startingTime"] + self._shapeParams["offsetDelay"] + self._shapeParams["risingTime"] + self._shapeParams["plateauLength"] + self._shapeParams["risingTime"]:self._shapeParams["startingTime"] +
                   self._shapeParams["offsetDelay"] + self._shapeParams["risingTime"] + self._shapeParams["plateauLength"] + self._shapeParams["risingTime"] + self._shapeParams["latchLength"]] = self._shapeParams["plateau"]

    def parameters(self):
        """
        Return parameters
        """
        return self._params

    def init(self):
        """
        Clear the JBA (no frequency to analyse)
        """
        self._pulseGenerator.clearPulse()
        self._pulseAnalyser.clear()
        self._change = True

    def setCarrierFrequency(self, f):
        self._pulseGenerator.setCarrierFrequency(f)

    def setFrequency(self, frequency, amplitude=1., duration=0., gaussian=False, delayFromZero=0, phase=None, shape=None, generatorToo=False):
        """
        Add a new frequency to analyse
        """
        print frequency, amplitude, duration, gaussian, delayFromZero, phase, shape, generatorToo

        if generatorToo:
            self.setCarrierFrequency(frequency)
        if shape is None:
            shape = self.shape
        if phase is None:
            phase = self._phase
        self.phase = phase
        self._frequency = frequency
        self._amplitude = amplitude
        # self._pulseGenerator.clearPulse()
#    self._pulseGenerator.generatePulse(duration=duration, frequency=self._frequency, amplitude=self._amplitude, DelayFromZero=delayFromZero,useCalibration=True, phase=phase,shape=amplitude*shape, name=self.name())

        self._pulseGenerator.addPulse(generatorFunction="arb", overwrite=True, frequency=self._frequency,
                                      applyCorrections=True, shape=self.shape * amplitude, name=self.name())
        self._pulseGenerator.preparePulseSequence()
        self._pulseGenerator.sendPulseSequence()

        self._fsb = -(self._pulseGenerator._MWSource.frequency() - frequency)
        self._pulseAnalyser.addFrequency(
            f=self._fsb, name=self.name(), bit=self.bit)
        self._change = True

    def sendAllWaveforms(self, forceSend=False):
        """
        Send all waveforms in pulseGenerator buffer
        """
        # self._pulseGenerator.sendPulse(forceSend)
        return

    def sendWaveform(self, forceSend=False):
        """
        Send waveform pf this JBA
        """
        # self._pulseGenerator.sendPulse(forceSend)
        return

    def setAmplitude(self, amplitude, magnitudeButton=None, phase=None, **args):
        """
        Set amplitude of the JBA pulse with button=magnitudeButton (if define, else self._magnitudeButton)
        """
        if magnitudeButton is None:
            magnitudeButton = self._magnitudeButton
        if magnitudeButton == 'formAmplitude':
            if phase is None:
                phase = self._phase
            self.phase = phase
            if abs(amplitude) > 1.2:
                amplitude = amplitude / abs(amplitude) * 1.2
            self.setFrequency(frequency=self._frequency,
                              amplitude=amplitude, phase=phase)
            # self.sendWaveform()
            time.sleep(1.)
        elif magnitudeButton == 'variableAttenuator':
            if amplitude > 5:
                amplitude = 5
            if amplitude < 0:
                amplitude = 0
            self._variableAttenuator.setVoltage(amplitude)
            time.sleep(0.2)
        elif magnitudeButton == 'microwaveSource':
            if amplitude > 19:
                amplitude = 19
            if amplitude < -19:
                amplitude = -19
            self._pulseGenerator._MWSource.setPower(amplitude)
            time.sleep(0.1)
        else:
            print "Error in magnitudeButton value"
        self.amplitude = amplitude
        return amplitude

    def getMeasurement(self):
        """
        Measure IQ signal at all frequencies previously added
        """
        self.co = self._pulseAnalyser.analyse()
        self._change = False
        return self.co

    def calculateBifurcation(self):
        """
        Acquire and calculate if JBA bifurcates or not
        """
        if self._change:
            self._pulseGenerator.sendPulse()
            time.sleep(0.5)
        (av, co, fr) = self._pulseAnalyser.analyse()
        self._change = False
        r = self._pulseAnalyser._acqiris.multiplexedBifurcationMapAdd(co, fr)
        proba = self._pulseAnalyser._acqiris.convertToProbabilities(r)
        return (av, co, fr, proba)

    def calibrate(self, bounds=None, level=0.5, accuracy=0.025, magnitudeButton=None, onlyOne=False, dataS=None, voltages=None, **kwargs):
        """
        Calibrate Offset and rotation for a single frequency f, and store it
        """
        if magnitudeButton is None:
            magnitudeButton = self._magnitudeButton
        self.notify("status", "Starting calibration...")
        self.notify("variance", 0)
        maxVoltage, bounds = self._findAmplitude(
            magnitudeButton=magnitudeButton, frequency=self._frequency, shape=self.shape, bounds=bounds, fitModel=False, **kwargs)
        if not(onlyOne):
            maxVoltage, b = self._findAmplitude(
                magnitudeButton=magnitudeButton, frequency=self._frequency, shape=self.shape, color=1, bounds=bounds, fitModel=True)
        self.notify("status", "Voltage calibration complete...")
        self.voltage = self.center
        self.setAmplitude(self.center)
        self.adjustSwitchingLevel(level)

    def _findAmplitude(self, frequency=None, shape=None, magnitudeButton=None, center=None, color=0, bounds=None, dataValues=None, fitModel=True, nLoops=10):
        """
        Only used by function calibrate.
        Measure and find the amplitude where the JBA is bi-evaluated, go to this point, and store this amplitude
        """

        def fitLorentzian(fs, p1, f0=None):

            fitfunc = lambda p, x: p[2] + p[0] / \
                (1.0 + pow((x - fs[argmax(p1)]) / p[1], 2.0))
            errfunc = lambda p, x, y, ff: pow(
                numpy.linalg.norm(ff(p, x) - y), 2.0)

            ps = [(max(p1) - min(p1)), 0.005, min(p1)]
            if f0 is not None:
                if max(fs) > f0 and min(fs) < f0:
                    ps[1] = f0

            print "Initial guess:", ps

            import numpy.linalg
            import scipy
            import scipy.optimize
            p1s = scipy.optimize.fmin(errfunc, ps, args=(fs, p1, fitfunc))
            rsquare = 1.0 - numpy.cov(p1 - fitfunc(p1s, fs)) / numpy.cov(p1)
            print p1s
            return p1s.tolist()

        if frequency is None:
            frequency = self._frequency
        if shape is None:
            shape = self.shape
        if magnitudeButton is None:
            magnitudeButton = self._magnitudeButton

        self.setFrequency(frequency=frequency, shape=shape)
        # self.sendWaveform()
        if magnitudeButton == 'formAmplitude':
            """
            values = voltage amplitude
            """
            if center is None:
                values = arange(0, 0.8, 0.01)
            else:
                if bounds is not None:
                    values = linspace(
                        center - 0.025, center + 0.025, bounds[2] / 2)
                else:
                    values = arange(center - 0.025, center + 0.025, 0.001)
        elif magnitudeButton == 'variableAttenuator':
            """
            values = attenuator voltage 
            """
            if center is None:
                values = arange(0, 5, 0.1)
            else:
                values = arange(center - 0.2, center + 0.2, 0.01)
        elif magnitudeButton == 'microwaveSource':
            """
            values = microwave Output power in dB
            """
            self.setFrequency(frequency=frequency, shape=shape)
            # self.sendWaveform()
            if center is None:
                values = arange(0, 20, 0.20)
            else:
                values = arange(center - 1, center + 1, 0.05)
        else:
            print "Error in the value of magnitudeButton"

        if bounds is not None:
            if center is None:
                values = linspace(bounds[0], bounds[1], bounds[2])
            else:
                print ''

        if fitModel:
            separatrixList = []
        self.notify('iqP', 0)
        ps = []
        maxcov = 0
        maxVoltage = 0
        self.variances = zeros((len(values), 2))
        self.variances[:, 0] = values
        self.data.clear()
        try:
            self.setAmplitude(magnitudeButton=magnitudeButton,
                              amplitude=values[0])
            time.sleep(0.5)
            for i in range(0, len(values)):
                if self.stopped():
                    self._stopped = False
                    raise Exception("Got stopped!")
                v = values[i]
                v = self.setAmplitude(
                    magnitudeButton=magnitudeButton, amplitude=v)
                trends = self.getComponents(nLoops=nLoops)
                varsum = cov(trends[0]) + cov(trends[1])

                x = 1. * i / len(values)
                self.notify("iqP", (trends[0], trends[1], ((x, 0, 1 - x))))

                if fitModel:
                    try:
                        fitResults = self.multiGaussianClusters(
                            trends.transpose())
                    except:
                        raise
                    sep = self.separatrixBimodal(fitResults)
                    separatrixList.append(sep)

                    self.separatrixList = separatrixList
                    s = [sep[0]]
                    sepCenters = array([[p[0], p[1]] for p in s]).transpose()
                    c = sep[3]
                    centers = [[c[0][0], c[1][0]], [c[0][1], c[1][1]]]
                    self.notify("centersIQ", [sepCenters, centers])

                if not dataValues is None:
                    ch = Datacube()
                    dataValues.addChild(ch)
                    ch.createColumn('I', trends[0])
                    ch.createColumn('Q', trends[1])
                    dataValues.set(v=v, varsum=varsum)
                    dataValues.commit()
                self.data.set(v=v)
                self.data.set(varsum=varsum)
                self.data.commit()
                self.notify("variance", (self.data.column("v"),
                                         self.data.column("varsum"), ((color, 0, 0))))
                self.notify("status", "Variance at %g V: %g" % (v, varsum))
                if DEBUG:
                    print "Variance at v = %f : %f" % (v, varsum)
                self.variances[i, 1] = varsum
                ps.append(varsum)
                if varsum > maxcov:
                    maxcov = varsum
                    maxVoltage = values[i]
            self.setAmplitude(magnitudeButton=magnitudeButton,
                              amplitude=maxVoltage)
            self._vMaxAmplitude = maxVoltage
        except:
            raise
        finally:

            # calculate separatrix
            print "fitModel: ", fitModel
            if fitModel:
                self.separatrixList = separatrixList

                sepCenters = [s[0] for s in self.separatrixList]
                centers = [s[3] for s in self.separatrixList]

                self.notify("centersIQ", [sepCenters, centers])

                print "separatrixList: ", separatrixList
                coefs, st = self.separatrixMulti(separatrixList, 0.1, 0.9)
                I0 = separatrixList[len(separatrixList) / 2][0][0]
                Q0 = coefs[0] * I0 + coefs[1]
                angle = arctan(coefs[0])
                self._setRotationAndOffset(I0, Q0, angle)
                self.setAmplitude(amplitude=self.center - abs(self.width) / 2)
                p0 = self.takePoint(nLoops=10)
                self.setAmplitude(amplitude=self.center + abs(self.width) / 2)
                p1 = self.takePoint(nLoops=010)
                print "p0 = ", p0, " p1= ", p1
                if p0 > p1:
                    self._setRotationAndOffset(I0, Q0, angle + math.pi)
                bounds = []
            else:
                # calculate bounds
                variances = self.data['varsum'].tolist()
                voltages = self.data['v'].tolist()
                yTarget = max(variances) * 0.4 + min(variances) * 0.6
                print yTarget
                vmax = firstXCrossTargetYFromAnEnd(
                    variances, voltages, yTarget=yTarget, direction='rightToLeft')[4]
                vmin = firstXCrossTargetYFromAnEnd(
                    variances, voltages, yTarget=yTarget, direction='leftToRight')[4]

                vmin = vmin  # -(vmax-vmin)*0.5
                vmax = vmax  # +(vmax-vmin)*0.5

                if vmax is None or vmin is None:
                    center = extremum(x=voltages, y=variances, minOrMax="max")
                    vmin, vmax = [center * 0.8, center * 1.2]

                self.center = (vmin + vmax) / 2
                self.width = abs(vmax - vmin)

                bounds = [vmin, vmax, 15.]
                print "bounds = " + str(bounds)

            return maxVoltage, bounds

    def _adjustRotationAndOffset(self, accurate=False):
        frequency = self._fsb
        """
    Only used by function calibrate, use only where the JBA is bi-valued
    To find the rotation angle and offsets to discriminate properly the bi-valued values, at a single frequency, and store thoses values
    """

        oldAmplitude = self.amplitude
        trends = self.getComponents()

        # if accurate:
        #  density,Chi,XY,domain=convertToDensity(trends.transpose())
        #  e,f,p= fit2D2Gaussian(Chi,XY)
        #  centers=[[p[2],p[3]],[p[7],p[8]]]
        #  sepCenter=(mean([centers[0][0],centers[1][0]]),mean([centers[0][1],centers[1][1]]))
        #  sepAngle=-math.atan2(centers[0][0]-centers[1][0],centers[0][1]-centers[1][1])
        # else:
        #  covar = cov(trends[0],trends[1])
        #  print covar
        #  la,v = linalg.eig(covar)
        #  if la[1] > la[0]:
        #    angle = math.atan2(v[0,0],v[0,1])
        #  else:
        #    angle = math.atan2(v[1,0],v[0,0])
        #  sepCenter=(mean(trends[0]),mean(trends[1]))
        #  print sepCenter
        #  print angle
        #  sepAngle=angle

        print "means = " + str(mean(trends[0])) + " " + str(mean(trends[1]))

        fitResults = self.multiGaussianClusters(trends.transpose())
        sep = self.separatrixBimodal(fitResults)
        sepCenter = sep[0]
        sepAngle = sep[1]

        self._setRotationAndOffset(sepCenter[0], sepCenter[1], sepAngle)
        self.setAmplitude(amplitude=self.center - abs(self.width) / 2)
        p0 = self.takePoint(nLoops=10)
        self.setAmplitude(amplitude=self.center + abs(self.width) / 2)
        p1 = self.takePoint(nLoops=010)

        if __DEBUG__:
            print "center, width="
        if __DEBUG__:
            print self.center, self.width

        if __DEBUG__:
            print "P0, p1="
        if __DEBUG__:
            print p0, p1
        if p0 > p1:
            print "reversing separatrix"
            self._setRotationAndOffset(sepCenter[0], sepCenter[
                                       1], sepAngle - math.pi)
        self.setAmplitude(oldAmplitude)

    def _setRotationAndOffset(self, I0, Q0, angle):
        self._demodulatorCorrections = {"I0": I0, "Q0": Q0, "angle": angle}
        if __DEBUG__:
            print I0, Q0, angle
        self._pulseAnalyser._acqiris.setFrequencyAnalysisCorrections(
            -self._fsb, I0, Q0, angle)
        self.notify("iqPaxes", (I0, Q0, angle))

    def measureSCurve(self, voltages=None, nLoops=5, microwaveOff=True, data=None, fspPower=False, corelations=False, **extraInDatacube):
        self.notify("status", "Measuring S curve...")

        def getVoltageBounds(v0, jba, variable, ntimes):
            return (0.5, 5)
            v = v0
            jba.setVoltage(v)
            jba._acqiris.bifurcationMap(ntimes=nLoops)
            p = jba._acqiris.Psw()[variable]

            while p > 0.03 and v < v0 * 2.0:
                v *= 1.05
                jba.setVoltage(v)
                jba._acqiris.bifurcationMap(ntimes=nLoops)
                p = jba._acqiris.Psw()[variable]
            vmax = v

            v = v0
            jba.setVoltage(v)
            jba._acqiris.bifurcationMap(ntimes=nLoops)
            p = jba._acqiris.Psw()[variable]

            while p < 0.98 and v > v0 / 2.0:
                v /= 1.05
                jba.setVoltage(v)
                jba._acqiris.bifurcationMap(ntimes=nLoops)
                p = jba._acqiris.Psw()[variable]
            vmin = v
            return (vmin * 0.95, vmax * 1.2)
        if fspPower:
            self._pulseGenerator._mixer._fsp.setFrequency(self._frequency)
        if data is None:
            data = Datacube("%s S Curve - f=%f" %
                            (self.name(), self._frequency))
            dataManager = DataManager()
            dataManager.addDatacube(data)
        else:
            data.setName("%s S Curve - f=%f" % (self.name(), self._frequency))

        if voltages is None:
            bounds = [self.center - self.width *
                      1, self.center + self.width * 1]
#      voltages=linspace(bounds[0],bounds[1],200)
            voltages = SmartLoop(
                bounds[0], (bounds[1] - bounds[0]) / 50, bounds[1], name="Scurve voltages")
        print "entering in loop"
        try:
            for v in voltages:
                print "voltage :", v
                self.setAmplitude(v)
                data.set(v=v)
                print "measuring"
                d = self.measure(nLoops=nLoops)
                print "got point"
                # d=self.getThisMeasure()
                # data.set(**d[1])
                data.set(**d[-1])
                print "in datacube"
                # data.set(**extraInDatacube)
                print "extra in datacube"
                if fspPower:
                    time.sleep(1)
                    data.set(
                        fspPower=self._pulseGenerator._mixer._fsp.getValueAtMarker())
                # self.notify("histograms",d[2][self.bit][0])
                # self.notify("iqdata",(d[2][self.bit][0],d[2][self.bit][1]))
                # self.notify("iqP",(d[0][:,0],d[0][:,1],((0,0,0))))
                print "commiting"
                data.commit()
                print "commited"
                # self.notify("sCurve",(data.column("v"),data.column("b%i"%self.bit)))
                print "first loop over"
            # data.sortBy('v')
            # data.sortBy("b%i"%self.bit)
            # p=data["b%i"%self.bit]
            # v=data['v']
            # p=p[p>0]
            # v=v[p>0]
            # p=p[p<1]
            # v=v[p<1]
            # self.sInterpolateVP=scipy.interpolate.interp1d(p,v)
            # data.sortBy('v')
            print "first loop over"
        except:
            raise
        finally:
            data.savetxt()
            self.notify("status", "S curve complete.")
            self.setAmplitude(self._vMaxAmplitude)
            return data

    def measureAll(self):
        return self._pulseAnalyser.measureAll()

    # ,verbose = False,minSensitivity = 15.0,microwaveOff = True,nmax = 100):
    def adjustSwitchingLevel(self, level=0.2, accuracy=0.05, nLoops=40, function='dichotmie'):
        print 'adjusting %f, with %f precision' % (level, accuracy)

        def levelAt(amplitude, nLoops=10, **args):
            v = self.setAmplitude(amplitude, **args)
            p = self.takePoint(nLoops=nLoops)
            self.notify("goto", ["singlePoint", [v, p]])
            return (v, p)

        if function == 'fit':
            fitfuncS = lambda p, x: exp(1 - exp((x - p[0]) / p[1])) / exp(1)

            def fitS(x, y, x0, dx):
                errfunc = lambda p, x, y, ff: pow(
                    numpy.linalg.norm(ff(p, x) - y), 2.0)
                ps = [x0, dx]
                p1s = scipy.optimize.fmin(errfunc, ps, args=(
                    x, y, fitfuncS), retall=False, disp=False)
                rsquare = 1.0 - numpy.cov(y - fitfuncS(p1s, x)) / numpy.cov(y)
                print "fit parameters"
                print p1s
                return p1s.tolist()

            def addToArray(x):
                (nx, ny) = levelAt(x)
                print nx, ny
                self.x.append(nx)
                self.y.append(ny)

            def defineFunction():
                self.notify('goto', ['clear', ''])
                self.x = []
                self.y = []

                # [self._vMaxAmplitude-2*max(self._vMaxAmplitude/5,abs(self._sCurveParams[0])),self._vMaxAmplitude+2*max(self._vMaxAmplitude/5,abs(self._sCurveParams[0]))]
                [vmin, vmax] = [self.center - self.width /
                                4, self.center + self.width / 4]

                addToArray(vmin)
                addToArray(vmax)
                print self.x, self.y
                for i in [1, 2, 3, 4, 5]:
                    self.params = fitS(
                        self.x, self.y, self._vMaxAmplitude, 0.2)
                    print self.params
                    addToArray(self.params[0])
                addToArray(self.params[0] - self.params[1] / 4)
                addToArray(self.params[0] - self.params[1] / 4)
                self.params = fitS(self.x, self.y, self._vMaxAmplitude, 0.2)

                # Define the invert function from center-2linewidth to center+2linewidth
                #x = linspace(params[0]-5*params[1],params[0]+5*params[1],100)
                #f = lambda x: fitfuncS(params,x)
                #y = map(f,x)
                self.sfunction = lambda x: self.params[
                    1] * log(1 - log((x) * exp(1))) + self.params[0]
                self.notify('goto', ['fit', self.sfunction])

            if not(hasattr(self, 'sfunction')):
                defineFunction()
            (v, l) = levelAt(self.sfunction(level), nLoops=nLoops)
            if abs(l - level) > accuracy:
                defineFunction()
            (v, l) = levelAt(self.sfunction(level), nLoops=nLoops)
            print "level at %f : %f" % (v, l)
        if function == "dichotmie":
            self.notify('goto', ['clear', ''])
            bounds = [self.center - self.width /
                      3, self.center + self.width / 3]
            p1 = levelAt(bounds[0])[1]
            p2 = levelAt(bounds[1])[1]
            if p1 > p2:
                slope = -1
            elif p1 < p2:
                slope = 1
            else:
                raise Exception("BAD RANGE")
            values = [p1, p2]
            l = -1
            n = 0
            error = False
            while abs(l - level) > accuracy and not error:
                newPoint = (level - values[0]) * (bounds[1] -
                                                  bounds[0]) / (values[1] - values[0]) + bounds[0]

                # newPoint=mean(bounds)
                o, l = levelAt(newPoint)
                if l < level:
                    bounds[(1 - slope) / 2] = newPoint
                    values[(1 - slope) / 2] = l
                else:
                    bounds[(1 + slope) / 2] = newPoint
                    values[(1 + slope) / 2] = l
                n += 1
                if n > 10:
                    error = True
            self.notify(
                'status', "level at %f : %f (found in %i tries)" % (newPoint, l, n))
            if error:
                return False
            else:
                return True

        # self.setAmplitude(self.sInterpolateVP(level))
        # self.setAmplitude(self._vMaxAmplitude)
        # return True
        # def levelAt(amplitude,nLoops=1,**args):
        #  self.setAmplitude(amplitude,**args)
        #  return self.takePoint(nLoops=nLoops)
        #
        #[vmin,vmax]=[self._vMaxAmplitude-2*max(self._vMaxAmplitude/5,abs(self._sCurveParams[0])),self._vMaxAmplitude+2*max(self._vMaxAmplitude/5,abs(self._sCurveParams[0]))]
        # options=dict()
        # options['maxiter']=15
        # result=scipy.optimize.minimize_scalar(levelAt,bracket=(vmin,self._vMaxAmplitude,vmax),bounds=(vmin,vmax),method='bounded',tol=accuracy,options=options)
        # return result

        #errfunc = lambda p, x, f:abs(f(x)-p)
        #v = scipy.optimize.fmin(errfunc, self._vMaxAmplitude,args=(p, self.sInterpolate),xtol=1e-5,ftol=1e-3)
        # print v
        # self.setAmplitude(v)

    def getIQp(self):
        co = self.getMeasurement()
        (clicks, IQData) = self._pulseAnalyser._acqiris.multiplexedBifurcationMapAdd(
            co, self._fsb)
        r = self._pulseAnalyser._acqiris.convertToProbabilities(clicks)
        return (r, IQData)

    def measure(self, nLoops=None, fast=False):
        """
        acquire, measure and calculate probabilities
        """
        try:
            if nLoops is None:
                nLoops = self.nLoops()
            if nLoops > self._nLoopsMax:
                firstNLoops = nLoops - \
                    int(nLoops / self._nLoopsMax) * self._nLoopsMax
                try:
                    r = self._pulseAnalyser.analyse(
                        firstNLoops, fast=fast)  # [-1]
                except:
                    print "error in pre-loop -> catched"
                if __DEBUG__:
                    print r[0], r[-1]
                toReturn = dict()
                for key in r[-1].keys():
                    toReturn[key] = firstNLoops * r[-1][key]
#        for key in r[0].keys():
           #         toReturn[key]=firstNLoops*r[0][key]
    #        r[key]*=firstNLoops
                    extraLoop = int(nLoops / self._nLoopsMax)
                if __DEBUG__:
                    print toReturn
                for i in range(0, extraLoop):

                    for j in [0, 1, 2]:
                        try:
                            print "index:", i, " over ", extraLoop
                            r = self._pulseAnalyser.analyse(
                                self._nLoopsMax, fast=fast)
                            if __DEBUG__:
                                print r[0], r[-1]
                            for key in r[-1].keys():
                                toReturn[key] += self._nLoopsMax * r[-1][key]
                            # for key in r[0].keys():
                            #  toReturn[key]+=self._nLoopsMax*r[0][key]
                            if __DEBUG__:
                                print toReturn
                            print "OK !"
                        except Exception as a:
                            print "error in extraLoop-> catched"
                            print a
                            pass
                        else:
                            break
                if __DEBUG__:
                    print "dividing by ", nLoops
                for key in toReturn.keys():
                    toReturn[key] /= nLoops
                toReturn = [toReturn]
            else:
                toReturn = self._pulseAnalyser.analyse(nLoops, fast=fast)

            return toReturn
        except Exception as a:
            print "error in extraLoop->not catched"
            print a

    def nLoops(self):
        try:
            return self._nLoops
        except:
            return 20

    def getThisMeasure(self, nLoops=10):
        """
        Return proba, non-corrected IQ, corrected IQ
        """
        r = self.measure(nLoops=nLoops)
        return (r[1]['b%i' % self.bit], r[0][self.bit], r[2][self.bit])

    def takePoint(self, nLoops=1):
        return self.measure(nLoops=nLoops)[1]['b%i' % self.bit]

    def getComponents(self, nLoops=10):
        return self.measure(nLoops=nLoops)[0][self.bit]

    def caracteriseJBA(self, shape, frequencies, test=False):
        for f in frequencies:
            self._pulseGenerator._MWSource.setFrequency(f)
            self._pulseGenerator._IQMixer.calibrate(offsetOnly=True)
            self.frequency(frequency=f, shape=shape)
            self._pulseGenerator.sendPulse()

    def caracteriseIQvsFvsP(self, frequencies, voltages, data=None):

        if data is None:
            data = Datacube("JBA mapping")
            dataManager.addDatacube(data)
        try:
            previousShape = self.shape
            self.shape = zeros((20000))
            self.shape[10000:10010] = linspace(0, 1, 10)
            self.shape[10010:12100] = 1
            self.shape[12100:12110] = linspace(1, 0, 10)
#      return self.shape
            import scipy

            pvsv = Datacube("power")
            data.addChild(pvsv)
            for v in voltages:
                self.setAmplitude(amplitude=v)
                p = self.measureJBAPower(f='autodetect')
                pvsv.set(v=v, bluePower=p)
                pvsv.commit()
            pv = scipy.interpolate.interp1d(
                pvsv.column("v"), pvsv.column("bluePower"))
            data.savetxt()

            for f in frequencies:
                child = Datacube("f=%f" % f)
                data.addChild(child)
                self.setFrequency(f)
                for v in voltages:
                    self.setAmplitude(amplitude=v)
                    time.sleep(0.5)
                    co = self.getThisMeasure()[1]
                    var = cov(co[0]) + cov(co[1])
                    if var > 0.01:
                        cod = Datacube("components at p=%f" % pv(v))
                        cod.createColumn('I', co[0])
                        cod.createColumn('Q', co[1])
                        cod.createColumn('bluePower', [pv(v)] * len(co[0]))
                        child.addChild(cod)
                    else:
                       # ECRIRE QUELQUE CHOSE ICI
                        [I, Q] = [mean(co[0]), mean(co[1])]
                        child.set(f=f, v=v, I=I, Q=Q,
                                  sigma=var, bluePower=pv(v))
                        child.set(M=sqrt(I**2 + Q**2))
                        child.set(phi=math.atan2(I, Q))
                        child.commit()
                        data.set(f=f, v=v, I=I, Q=Q,
                                 sigma=var, bluePower=pv(v))
                        data.set(M=sqrt(I**2 + Q**2))
                        data.set(phi=math.atan2(I, Q))
                        data.commit()
                data.savetxt()
        except:
            raise
        finally:
            data.savetxt()
            self.shape = previousShape

    def measureJBAPower(self, f=None):
        if f is None:
            f = frequency = self._f01
        else:
            f = self._pulseGenerator._MWSource.frequency()

        self._pulseGenerator.clearPulse()

        self._pulseGenerator.pulses[self.name()][1] = False
        self._pulseGenerator.generatePulse(duration=register[
                                           'repetitionPeriod'], frequency=f, DelayFromZero=0., useCalibration=False, name='calibration')
        self._pulseGenerator.pulses['calibration'][1] = True

        self._pulseGenerator.sendPulse()

        fsp = self._pulseGenerator._mixer._fsp
        fsp.write("SENSE1:FREQUENCY:CENTER %f GHZ" % f)
        fsp.write("SENSE1:FREQUENCY:SPAN 0 MHz")
        fsp.write("SWE:TIME 1 ms")
        rbw = 10000
        fsp.write("SENSE1:BAND:RES %f Hz" % rbw)
        fsp.write("SENSE1:BAND:VIDEO AUTO")
        fsp.write("TRIG:SOURCE EXT")
        fsp.write("TRIG:HOLDOFF 0.0 s")
        fsp.write("TRIG:LEVEL 0.5 V")
        fsp.write("TRIG:SLOP POS")
        averaging = 0
        fsp.write("SENSE1:AVERAGE:COUNT %d" % averaging)
        fsp.write("SENSE1:AVERAGE:STAT1 ON")
        time.sleep(0.5)
        m = mean(fsp.getSingleTrace()[1])
        print self._pulseGenerator.pulses
        self._pulseGenerator.pulses['calibration'][1] = False
        self._pulseGenerator.pulses[self.name()][1] = True
        self._pulseGenerator.sendPulse()
        print self._pulseGenerator.pulses
        return m

# Utility functions for separating clusters

    def multiGaussianClusters(self, distribution, n_components=2, scale=True, returnGMM=False, predict=False):
        scaler = preprocessing.StandardScaler()
        distribution2 = distribution
        if scale:
            distribution2 = scaler.fit_transform(distribution)
        gmm = mixture.GMM(n_components=n_components, covariance_type='full')
        gmm.fit(distribution2)
        weights, centers, covars = [gmm.weights_, gmm.means_, gmm.covars_]
        if scale:
            centers = scaler.inverse_transform(centers)
            for i in range(len(covars)):
                covars[i] = np.diag(scaler.std_).dot(
                    covars[i]).dot(np.diag(scaler.std_))
        ind = argsort(weights)[::-1]
        weights = weights[ind]  # sort by decreasing weights
        [weights, centers, covars] = [elmt[ind]
                                      for elmt in [weights, centers, covars]]
        # diagonalize all covariance matrices to find the principal axes and
        # variances
        eigen = map(linalg.eigh, covars)
        model = ()  # sort principal axes with largest variance first
        for index in range(len(weights)):
            eigvals, eigvecs = eigen[index]
            # principal axis with largest sigma first
            ind = argsort(eigvals)[::-1]
            [eigvals, eigvecs] = [elmt[ind] for elmt in [eigvals, eigvecs]]
            angle = rad2deg(arctan(eigvecs[0, 1] / eigvecs[0, 0]))
            model = model + \
                ([weights[index], centers[index], angle, sqrt(eigvals)],)
        if returnGMM:
            model = model + (gmm,)
        if predict:
            model = model + (gmm.predict(distribution2),)
        return(model)

    def separatrixBimodal(self, bimodalGaussian):
        '''
        Find the best separatrix orthogonal to the line joining the two centers of a 2D bimodal Gaussian distribution.
        Return the list [sepPoint,beta,array([w1,w2]),array([c1,c2]),array([s1,s2])] with
            - sepPoint the point of the separatrix on the segment joining the centers C1 and C2,
            - beta the angle between x and the separatrix,
            - w1,w2 the weights of the two components,
            - c1,c2 the two centers of the Gaussian
            - s1,s2 the two sigmas along the C1C2
        Note that the first component is on the left of the oriented axe defined by the point and the oriented angle. 
        '''
        cluster1, cluster2 = bimodalGaussian[0:2]
        w1, w2 = cluster1[0], cluster2[0]
        c1, c2 = cluster1[1], cluster2[1]
        x, y = c1c2 = c2 - c1
        dist = linalg.norm([x, y])
        # angle between the segment joining the centers and X
        alpha = arctan2(y, x)
        sigmasAlongC1C2 = []
        for cluster in [cluster1, cluster2]:
            c, a, s = cluster[1:4]
            tangent = tan(a - alpha)
            sAlongC1C2 = sqrt((1 + tangent**2) /
                              (1 / s[0]**2 + (tangent / s[1])**2))
            sigmasAlongC1C2.append(sAlongC1C2)
        s1, s2 = sigmasAlongC1C2
        sigmaSum = sum(sigmasAlongC1C2)
        if sigmaSum > dist:
            print 'Alert: separation between clouds 1 and 2 smaller than sigma1 + sigma2'
        sepPoint = s1 / (s1 + s2) * c1c2 + c1
        beta = alpha + math.pi / 2
        return [sepPoint, beta, array([w1, w2]), array([c1, c2]), array([s1, s2])]

    def separatrixMulti(self, ListOfSeparatrices, wMin=0, wMax=1):
        '''
        Find the best separatrix line given a list of separatrices of the form [separatrix1,separatrix2,...] with
        separatrixi = [sepPoint,beta,weightsW1W2,centersC1C2,sigmasAlongC1C2]
        Return the a and b parameters of the separatrix equation y=a x + b
        Separatrices correponding to weight > wMax or weight < wMin are ignored  
        Alert with a message if the separatrix 
            - approaches one of the Gaussian peak at less than a sigma
            - or is on the wrong side of the gaussian peak
        '''
        __DEBUG__ = False
        # selection=[elmt for elmt in ListOfSeparatrices if (elmt[2][0] > wMin
        # and elmt[2][1] < wMax)] # bug here with the order of the two
        # complementary weights
        selection = [elmt for elmt in ListOfSeparatrices if abs(
            elmt[2][1] - elmt[2][0]) <= abs(wMax - wMin)]
        abs(elmt[2][1] - elmt[2][0])
        weights = [elmt[2] for elmt in selection]
        points = [elmt[0] for elmt in selection]
        status = 'ok'
        # no separatrices selected => error
        if len(points) == 0:
            status = 'Error:Cannot proceed with an empty ListOfSeparatrices.'
            print status
            return [None, status]
        # only one separatrice selected => return it
        elif len(points) == 1:
            sepPoint, angle = ListOfSeparatrices[1][:2]
            a = tan(angle)
            b = sepPoint[1] - a * sepPoint[0]
            return [array([a, b]), status]
        # several separatrices => fit the best new separatrix ## COMPLETELY
        # WRONG !!! minimize y distance betweend separatrix and points
        x, y = array(points).T

        A = vstack([x, ones(len(x))]).T
        a, b = abarray = linalg.lstsq(A, y)[0]
        for separatrix in selection:                           # Check if the new separatrix a x + b is valid
            sepPoint, beta, weights, [c1, c2], [s1, s2] = separatrix
            if __DEBUG__:
                print "sepPoint: ", sepPoint
            c1c2 = c2 - c1
            # intersection of a x +b separatrix with C1C2
            xi = dot(array([b - c1[1], c1[0]]), c1c2) / \
                dot(array([-a, 1]), c1c2)
            yi = a * xi + b
            ci = array([xi, yi])
            cic1 = c1 - ci
            cic2 = c2 - ci
            inside = dot(cic1, cic2) < 0
            if inside:
                tooClose = linalg.norm(cic1) < s1 or linalg.norm(cic2) < s2
                if tooClose:
                    status = 'invalid'
                    print 'Alert: Separatrix for weights=', weights, ' approaches one of the peak by less than a sigma.'
            else:
                status = 'invalid'
                print 'Alert: Separatrix for weights=', weights, ' does not pass between the gaussian peaks'

        if __DEBUG__:
            print "a,b: ", a, b

        # return the list of a,b array and status string
        return [abarray, status]

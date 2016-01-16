import sys
import getopt
import re
import struct
import math
import numpy
import scipy
import scipy.interpolate

from application.lib.instrum_classes import *
from application.helpers.instrumentmanager.instrumentsmgr import InstrumentManager
if 'macros.iq_level_optimization' in sys.modules:
    reload(sys.modules["macros.iq_level_optimization"])
from macros.qubit_functions import *
if 'macros.qubit_functions' in sys.modules:
    reload(sys.modules["macros.qubit_functions"])
instrumentManager = InstrumentManager()
from macros.iq_level_optimization import IqOptimization
from application.lib.datacube import Datacube
from application.helpers.datamanager.datamgr import DataManager
dataManager = DataManager()
register = instrumentManager.getInstrument("register")


class WaveformException(Exception):
    pass


class QubitException(Exception):
    pass


def gaussianFilter(x, cutoff=0.5):
    return numpy.exp(-numpy.power(numpy.fabs(numpy.real(x)) / cutoff, 2.0))


def gaussianPulse(length=500, delay=0, flank=4, normalize=True, resolution=1, filterFrequency=0.2):
    waveform = numpy.zeros((math.ceil(flank * 2) + 1 + int(math.ceil(length)) +
                            math.ceil(delay)) * int(1.0 / resolution), dtype=numpy.complex128)
    if length == 0:
        return waveform
    for i in range(0, len(waveform)):
        t = float(i) * resolution
        if t <= flank + delay:
            waveform[
                i] = numpy.exp(-0.5 * math.pow(float(t - delay - flank) / float(flank) * 3.0, 2.0))
        elif t >= flank + delay + length:
            waveform[i] = numpy.exp(-0.5 * math.pow(float(t -
                                                          delay - flank - length) / float(flank) * 3.0, 2.0))
        else:
            waveform[i] = 1.0
    pulseFFT = numpy.fft.rfft(waveform)
    freqs = numpy.linspace(0, 1.0, len(pulseFFT))
    filteredPulseFFT = pulseFFT
    filteredPulse = numpy.array(numpy.fft.irfft(
        filteredPulseFFT, len(waveform)), dtype=numpy.complex128)
    filteredPulse = waveform
    integral = numpy.sum(filteredPulse)
    if normalize:
        filteredPulse /= integral / float(length) * resolution
    return filteredPulse


def gaussianPulse2(length=500, delay=0, flank=4, normalize=True, resolution=1, filterFrequency=0.2, withDerivative=False):
    from math import ceil, floor
    gaussianLength = math.ceil(math.ceil(flank * 2) + 1)
    smallPulse = numpy.zeros(gaussianLength + delay, dtype=numpy.complex128)
    smallPulseDerivative = numpy.zeros(
        gaussianLength + delay, dtype=numpy.complex128)
    for i in range(0, len(smallPulse) - int(delay)):
        smallPulse[
            delay + i] = numpy.exp(-0.5 * math.pow(float(i - flank) / float(flank) * 3.0, 2.0))
        smallPulseDerivative[delay + i] = -1 * float(i - flank) * math.pow(1 / float(
            flank) * 3.0, 2.0) * numpy.exp(-0.5 * math.pow(float(i - flank) / float(flank) * 3.0, 2.0))
    area = sum(smallPulse)
    if area > length:
        if withDerivative:
            return (smallPulse * float(length) / area, smallPulseDerivative * float(length) / area)
        else:
            return smallPulse * float(length) / area
    else:
        plateauLength = math.ceil(length - area)
        longPulse = numpy.zeros(
            delay + plateauLength + gaussianLength, dtype=numpy.complex128)
        longPulseDerivative = numpy.zeros(
            delay + plateauLength + gaussianLength, dtype=numpy.complex128)
        longPulse[delay:] = 1.0
        longPulseDerivative[delay:] = 0
        longPulse[delay:delay + ceil(gaussianLength / 2)
                  ] = smallPulse[delay:delay + ceil(gaussianLength / 2)]
        longPulseDerivative[delay:delay + ceil(gaussianLength / 2)] = smallPulseDerivative[
            delay:delay + ceil(gaussianLength / 2)]
        longPulse[-ceil(gaussianLength / 2)
                        :] = smallPulse[delay + floor(gaussianLength / 2):]
        longPulseDerivative[-ceil(gaussianLength / 2):] = smallPulseDerivative[
            delay + floor(gaussianLength / 2):]
        if withDerivative:
            return (longPulse * float(length) / sum(longPulse), longPulseDerivative * float(length) / sum(longPulse))
        else:
            return longPulse * float(length) / sum(longPulse)


class Pulse:

    def __init__(self, shape, delay):
        self._shape = shape
        self._delay = delay

    def shape(self):
        return self._shape

    def delay(self):
        return self._delay

    def __len__(self):
        return len(self._shape) + self._delay


class PulseSequence:

    def __init__(self):
        self._base = dict()
        self._pulses = []
        self._offset = 0
        self._pos = 0

    def setOffset(self, offset):
        self._offset = offset

    def offset(self):
        return self._offset

    def setPosition(self, pos):
        self._pos = pos

    def position(self):
        return self._pos

    def addPulse(self, shape, delay=0, position=None):
        if position is None:
            pos = delay + self._pos
        else:
            pos = position + delay
        pulse = Pulse(shape, pos)
        self._pulses.append(pulse)
        self._pos = pos + len(shape)

    def addWait(self, length):
        self._pos += length

    def __len__(self):
        maxlen = 0
        for pulse in self._pulses:
            if len(pulse.shape()) + pulse.delay() > maxlen:
                maxlen = len(pulse.shape()) + pulse.delay()
        return int(max(maxlen, self._pos))

    def clearPulses(self):
        self._pulses = []

    def getWaveform(self, dataType=numpy.complex128, endAt=None):
        waveform = numpy.zeros(len(self), dtype=dataType) + self._offset
        for pulse in self._pulses:
            totalLength = len(pulse.shape()) + pulse.delay()
            if totalLength > len(waveform):
                oldLength = len(waveform)
                waveform.resize(totalLength)
                waveform[oldLength:] = self._offset
            waveform[math.ceil(pulse.delay()):math.ceil(
                pulse.delay()) + len(pulse.shape())] += pulse.shape()
        if endAt is None:
            return waveform
        if endAt < len(waveform):
            raise Exception("Waveform is too long!")
        shiftedWaveform = numpy.zeros(endAt, dtype=dataType)
        shiftedWaveform[endAt - len(self):] = waveform
        return shiftedWaveform

# This is a virtual instrument representing a Quantum Bit.
# This class provides convenience functions for setting the Qubit parameters and for
# making measurements of the Qubit state.


class Instr(Instrument):

    def measureSpectroscopy(self, fstart, fstop, fstep, power=0., name=None, data=None):
        duration = 2000
        newData = False
        if data is None:
            newData = True
            if name is None:
                name = 'Spectro %s' % self.name()
            data = Datacube(name)
            dataManager.addDatacube(data)
        print fstart, fstop, fstep
        frequencies = numpy.arange(fstart, fstop, fstep)
        self._pulseGenerator._MWSource.turnOn()
        self._pulseGenerator._MWSource.setPower(power)
        self._pulseGenerator.generatePulse(duration=duration, frequency=fstart, DelayFromZero=register[
                                           'repetitionPeriod'] / 2 - duration - 15, useCalibration=False)
        self._pulseGenerator.sendPulse()
        try:
            for f in frequencies:
                print f
                self._pulseGenerator._MWSource.setFrequency(f)
                data.set(f=f)
                data.set(**self._jba.measure()[1])
                data.commit()
        except:
            raise
        finally:
            data.setParameters(instrumentManager.parameters())
            if newData:
                data.savetxt()
            try:
                p, o2 = fitQubitFrequency(
                    data, variable="b1")  # ,f0=self._f01)
                self._f01 = p[1]
            finally:
                return data

    def measureRabi(self, tstart, tstop, tstep, power=None, name=None, data=None):
        newData = False
        if data is None:
            newData = True
            if name is None:
                name = 'rabi %s' % self.name()
            data = Datacube(name)
            dataManager.addDatacube(data)
        durations = numpy.arange(tstart, tstop, tstep)
        if power is None:
            power = self._rabiPower

        self._pulseGenerator._MWSource.turnOn()
        self._pulseGenerator._MWSource.setPower(power)
        self._pulseGenerator._MWSource.setFrequency(self._f01)

        try:
            for duration in durations:
                self._pulseGenerator.generatePulse(duration=duration, frequency=self._f01, DelayFromZero=register[
                                                   'repetitionPeriod'] / 2 - duration - 10, useCalibration=False)
                self._pulseGenerator.sendPulse()
                data.set(duration=duration)
                data.set(p=self._jba.takePoint())
                data.commit()
        except:
            raise
        finally:
            data.setParameters(instrumentManager.parameters())
            self._rabiPower = power
            if newData:
                data.savetxt()
            p, o2 = fitRabiFrequency(data, yVariable="p", xVariable="duration")
            self._rabiDuration = p[1] / 2
            return data

    def measureT1(self, tstart, tstop, tstep, accurate=False, name=None, data=None):

        newData = False
        if data is None:
            newData = True
            if name is None:
                name = 'T1 %s' % self.name()
            data = Datacube(name)
            dataManager.addDatacube(data)
        data.setParameters(instrumentManager.parameters())
        self._pulseGenerator._MWSource.turnOn()
        self._pulseGenerator._MWSource.setPower(self._rabiPower)
        self._pulseGenerator._MWSource.setFrequency(self._f01)
        print tstart, tstop, tstep
        if accurate:
            delays = numpy.concatenate([numpy.arange(tstart, tstart + (tstop - tstart) * 0.3, tstep), numpy.arange(
                tstart + (tstop - tstart) * 0.9, tstop, max(1, int(tstep / 2)))], axis=0)
        else:
            delays = numpy.arange(tstart, tstop, tstep)

        try:
            for delay in delays:
                self._pulseGenerator.generatePulse(duration=self._rabiDuration, frequency=self._f01, DelayFromZero=register[
                                                   'repetitionPeriod'] / 2 - self._rabiDuration - delay, useCalibration=False)
                self._pulseGenerator.sendPulse()
                data.set(delay=delay)
                data.set(p=self._jba.takePoint())
                data.commit()
        except:
            raise
        finally:
            data.setParameters(instrumentManager.parameters())
            p = fitT1Parameters(data, variable="p")
            if newData:
                data.savetxt()
            self._t1 = p[2]
            return data

    def measureSCurves(self, ntimes=None, data=None):
        if data is None:
            if name is None:
                name = 'sCurves %s' % self.name()
            data = Datacube(name)
            dataManager.addDatacube(data)
        self._pulseGenerator._MWSource.setPower(self._rabiPower)
        self._pulseGenerator._MWSource.setFrequency(self._f01)
        self._pulseGenerator.generatePulse(duration=self._rabiDuration, frequency=self._f01, DelayFromZero=register[
                                           'repetitionPeriod'] / 2 - self._rabiDuration - 10, useCalibration=False)
        self._pulseGenerator.sendPulse()
        off = Datacube('sOff')
        data.addChild(off)
        self._pulseGenerator._MWSource.turnOff()
        self._jba.measureSCurve(data=off, ntimes=10)
        on = Datacube('sOn')
        data.addChild(on)
        self._pulseGenerator._MWSource.turnOn()
        self._jba.measureSCurve(data=on, ntimes=10)

    def caractiseQubit(self, data=None, frequencies=[8.5, 9.5]):
        if data is None:
            data = Datacube('caracterisation %s' % self.name())
            dataManager.addDatacube(data)
        acqiris.setNLoops(1)
        self._jba.calibrate(bounds=[2, 3, 25])
        acqiris.setNLoops(10)
        spectro = Datacube('spectro')
        data.addChild(spectro)
        self.measureSpectroscopy(fstart=frequencies[0], fstop=frequencies[
                                 1], fstep=0.002, power=-27., data=spectro)
        data.set(f01=self._f01)
        rabi = Datacube('rabi')
        data.addChild(rabi)
        self.measureRabi(tstart=0, tstop=60, tstep=2., data=rabi)
        data.set(rabiPi=self._rabiDuration)
        scurves = Datacube('sCurves')
        data.addChild(scurves)
        self.measureSCurves(data=scurves, ntimes=10)
        t1 = Datacube('t1')
        data.addChild(t1)
        self.measureT1(tstart=0, tstop=500, tstep=4, data=t1)
        data.set(t1=self._t1)
        frequencies = [self._f01 - 0.25, self._f01 + 0.05]
        data.commit()
        data.savetxt()

    def measureDrivePower(self, f=None):

        if f is None:
            f = frequency = self._f01
        else:
            f = self._pulseGenerator._MWSource.frequency()

        self._pulseGenerator.clearPulse()
        self._pulseGenerator.generatePulse(duration=register[
                                           'repetitionPeriod'], frequency=f, DelayFromZero=0., useCalibration=False)
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
        return mean(fsp.getSingleTrace()[1])

    def initialize(self, jba, pulseGenerator):
        instrumentManager = InstrumentManager()
        if not hasattr(self, '_params'):
            self._params = dict()
        self._params['jba'] = jba
        self._jba = instrumentManager.getInstrument(jba)
        self._params['pulseGenerator'] = pulseGenerator
        self._pulseGenerator = instrumentManager.getInstrument(pulseGenerator)

        self._rabiPower = -5.

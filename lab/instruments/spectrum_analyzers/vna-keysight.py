import sys
import getopt
import time

from application.lib.instrum_classes import *
if 'lib.datacube' in sys.modules:
    reload(sys.modules['lib.datacube'])
from application.lib.datacube import Datacube
from numpy import *
from pyvisa import vpp43


class VNATrace:

    def __init__(self):
        self.frequencies = []
        self.phase = []
        self.magnitude = []
        self.timestamp = ''
        self.instrument = None

# This is the VNA instrument.


class Instr(VisaInstrument):

    # Initializes the instrument.
    def initialize(self, visaAddress="TCPIP0::192.168.0.71::inst0::INSTR", powerParams={}):
        print 'Initializing ' + self.name() + ' with adress ', visaAddress, ':',
        self._visaAddress = visaAddress
        try:
            self.clearDevice()
        except:
            print "ERROR: Cannot initialize instrument!"
        self._powerParams = {'attenMin': 0, 'attenMax': 80, 'sourceMin': -
                             20, 'sourceMax': 0, 'offset': 0}  # everything in dBm
        self.setPowerParams(powerParams)

    def clearDevice(self):
        handle = self.getHandle()
        handle.timeout = 1
        vpp43.clear(handle.vi)
        # handle.write('*CLS')
        try:
            print 'STB=', self.ask('*STB?')
            return True
        except visa.VisaIOError:
            return False

    def powerParams(self):
        return self._powerParams

    def setPowerParams(self, newDict):
        for key in newDict:
            if key in self._powerParams:
                self._powerParams[key] = newDict[key]
        return self._powerParams

    def sweepMode(self, channel=1):
        return self.ask('SENS' + str(channel) + ':SWEEP:MODE?')

    def sweepContinuous(self, channel=1):
        self.write('SENS' + str(channel) + ':SWEEP:MODE CONT')
        return self.sweepMode(channel=channel)

    def sweepSingle(self, channel=1):
        self.write('SENS' + str(channel) + ':SWEEP:MODE SINGLE')
        return self.sweepMode(channel=channel)

    def sweepHold(self, channel=1):
        self.write('SENS' + str(channel) + ':SWEEP:MODE HOLD')
        return self.sweepMode(channel=channel)

    def outputState(self):
        return self.ask('OUTP:STAT?')

    def turnOn(self):
        self.write('OUTP:STAT ON')
        return self.outputState()

    def turnOff(self):
        self.write('OUTP:STAT OFF')
        return self.outputState()

    def totalPower(self, port=1):
        return float(self.ask('SOUR' + str(int(port)) + ':POW?'))

    def setTotalPower(self, powerIndBm, port=1):
        self.write('SOUR' + str(int(port)) + ':POW ' + str(powerIndBm))
        return self.totalPower(port=port)

    def attenuation(self):
        return float(self.ask("SOUR:POW:ATT?"))

    def setAttenuation(self, attenIndB='AUTO', channel=1, port=1):
        str1 = 'SOUR' + str(channel) + ':POW' + str(int(port))
        if isinstance(attenIndB, (int, long, float)):
            str1 += ':ATT ' + str(attenIndB)
        else:
            str1 += ':ATT:AUTO ON'
        self.write(str1)
        return self.attenuation()

    def getMode(self):
        return self.ask('SENS:SWE:TYPE?')

    def setMode(self, mode):
        self.write('SENS:SWE:TYPE ' + mode)
        return self.getMode()

    def setCW(self, on=True):
        if on:
            return self.setMode('CW')
        else:
            return self.setMode('LIN')

    def getCW(self):
        return self.getMode() == 'CW'

    def startFrequency(self, channel=1):
        return float(self.ask('SENS' + str(channel) + ':FREQ:START?'))

    def getStartInGHz(self, channel=1):
        return self.startFrequency(channel=channel) / 1e9

    def setStartFrequency(self, freq, channel=1):
        self.write('SENS' + str(channel) + ':FREQ:START ' + str(freq))
        return self.startFrequency(channel=channel)

    def setStartInGHz(self, freq, channel=1):
        return self.setStartFrequency(freq * 1e9, channel=channel)

    def stopFrequency(self, channel=1):
        return float(self.ask('SENS' + str(channel) + ':FREQ:STOP?'))

    def getStopInGHz(self, channel=1):
        return self.stopFrequency(channel=channel) / 1e9

    def setStopFrequency(self, freq, channel=1):
        self.write('SENS' + str(channel) + ':FREQ:STOP ' + str(freq))
        return self.stopFrequency(channel=channel)

    def setStopInGHz(self, freq, channel=1):
        return self.setSopFrequency(freq * 1e9, channel=channel)

    def centerFrequency(self, channel=1):
        return float(self.ask('SENS' + str(channel) + ':FREQ:CENT?'))

    def getCenterInGHz(self, channel=1):
        return self.centerFrequency(channel=channel) / 1e9

    def setCenterFrequency(self, freq, channel=1):
        self.write('SENS' + str(channel) + ':FREQ:CENT ' + str(freq))
        return self.centerFrequency(channel=channel)

    def setCenterInGHz(self, freq, channel=1):
        return self.setCenterFrequency(freq * 1e9, channel=channel)

    def spanFrequency(self, channel=1):
        return float(self.ask('SENS' + str(channel) + ':FREQ:SPAN?'))

    def getSpanInGHz(self, channel=1):
        return self.spanFrequency(channel=channel) / 1e9

    def setSpanFrequency(self, span, channel=1):
        self.write('SENS' + str(channel) + ':FREQ:SPAN ' + str(span))
        return self.spanFrequency(channel=channel)

    def setSpanInGHz(self, span, channel=1):
        return self.setSpanFrequency(span * 1e9, channel=channel)

    def numberOfPoints(self, channel=1):
        return int(self.ask('SENS' + str(channel) + ':SWEEP:POINTS?'))

    def setNumberOfPoints(self, nOfPoints, channel=1):
        self.write('SENS' + str(channel) + ':SWEEP:POINTS ' + str(nOfPoints))
        return self.numberOfPoints(channel=channel)

    def bandwidth(self, channel=1):
        return float(self.ask('SENS' + str(channel) + ':BAND?'))

    def setBandwidth(self, bandwidth, channel=1):
        self.write('SENS' + str(channel) + ':BAND ' + str(bandwidth))
        return self.bandwidth(channel=channel)

    def average(self):
        return bool(int(self.ask('SENS:AVER?')))

    def averageOn(self):
        self.write('SENS:AVER ON')
        return self.average()

    def averageOff(self):
        self.write('SENS:AVER OFF')
        return self.average()

    def setAverage(self, b):
        if b:
            return self.averageOn()
        else:
            return self.averageOff()

    def averageClear(self):
        self.write('SENS:AVER:CLE')

    def averageMode(self):
        return self.ask('SENS:AVER:MODE?')

    def setAverageMode(self, mode='SWEEP'):  # use 'SWEEP' or 'POINT'
        self.write('SENS:AVER:MODE ' + mode)
        return self.averageMode()

    def averageCount(self):
        return int(self.ask('SENS:AVER:COUN?'))

    def setAverageCount(self, count):
        self.write('SENS:AVER:COUN ' + str(int(count)))
        return self.averageCount()

    def getSetup(self):
        return {'power': self.totalPower(), 'cwONOFF': self.getCW(), 'centerInGHz': self.getCenterInGHz(), 'spanInGHz': self.getSpanInGHz(), 'startInGHz': self.getStartInGHz(),
                'stopInGHz': self.getStopInGHz(), 'BWInHz': self.bandwidth(), 'numOfPoints': self.numberOfPoints(), 'avgCount': self.averageCount(),
                'avgONOFF': self.average()}

    # measurement number = tr# (and mont the trace) on the PNA
    def measurements(self, channel=1):
        return [int(u) for u in self.ask('SYST:MEAS:CAT? ' + str(channel))[1:-1].split(',')]

    # trace also called measurement in the documentation
    def selectTrace(self, channel=1, trace=1):
        if trace in self.measurements(channel=channel):
            self.write('CALC' + str(channel) + ':PAR:MNUM ' + str(trace))
        trace2 = int(self.ask('CALC' + str(channel) + ':PAR:MNUM?'))
        if trace2 != trace:
            raise NameError("Can't select trace " + str() +
                            " of channel " + str(channel))
        return trace2

    def getFormat(self, channel, trace):
        success, trace = self.selectTrace(channel=channel, trace=trace)
        if success:
            self.ask('CALC' + str(channel) + ':FORM?')
        else:
            print 'channel ' + channel + ':measurement ' + trace + ' does not exist.'

    # format is MLINear,MLOGarithmic,PHASe,UPHase,IMAGinary,REAL,POLar
    def setFormat(self, channel, trace, format):
        success, trace = self.selectTrace(channel=channel, trace=trace)
        if success:
            self.write('CALC' + str(channel) + ':FORM ' + format)
            return self.getFormat(channel, trace)

    def electricalLength(self, channel=1, trace=1):
        self.selectTrace(channel=channel, trace=trace)
        return float(self.ask('CALC' + str(channel) + ':CORR:EDEL:DIST?'))

    def setElectricalLength(self, dist, channel=1, trace=1):
        success, trace = self.selectTrace(channel=channel, trace=trace)
        self.write('CALC' + str(channel) + ':CORR:EDEL:DIST ' + str(dist))
        return self.electricalLength()

    def checkMarkerIndex(self, index):
        if index >= 10:
            raise NameError('Marker index should be lower than 10.')

    def markerState(self, channel=1, trace=1, marker=1):
        self.checkMarkerIndex(marker)
        self.selectTrace(channel=channel, trace=trace)
        return int(self.ask('CALC' + str(channel) + ':MARK' + str(marker) + '?'))

    def markerOn(self, channel=1, trace=1, marker=1):
        self.checkMarkerIndex(marker)
        self.selectTrace(channel=channel, trace=trace)
        self.write('CALC' + str(channel) + ':MARK' + str(marker) + ' ON')
        return self.markerState(channel=channel, marker=marker)

    def markerOff(self, channel=1, trace=1, marker=1):
        self.checkMarkerIndex(marker)
        self.selectTrace(channel=channel, trace=trace)
        self.write('CALC' + str(channel) + ':MARK' + str(marker) + ' OFF')
        return self.markerState(channel=channel, marker=marker)

    def markerState2(self, channel=1, trace=1, marker=1, forceOn=False):
        state = self.markerState(channel=channel, trace=trace, marker=marker)
        if not state:
            if forceOn:
                return self.markerOn(channel=channel, trace=trace, marker=marker)
            else:
                raise NameError(
                    'Marker is off. Switch it on or use kwarg forceOn=True in your calls.')
        else:
            return state

    # position in number of points
    def markerPosition(self, channel=1, trace=1, marker=1, forceOn=False):
        self.markerState2(channel=channel, trace=trace,
                          marker=marker, forceOn=forceOn)
        return int(self.ask('CALC' + str(channel) + ':MARK' + str(marker) + ':BUCK?'))

    # position in number of points
    def markerSetPosition(self, position, channel=1, trace=1, marker=1, forceOn=True):
        self.markerState2(channel=channel, trace=trace,
                          marker=marker, forceOn=forceOn)
        self.write('CALC' + str(channel) + ':MARK' +
                   str(marker) + ':BUCK ' + str(position))
        return self.markerPosition(channel=channel, marker=marker)

    # position X the unit of the X axis (frequency, power or time )
    def markerX(self, channel=1, trace=1, marker=1, forceOn=True):
        self.markerState2(channel=channel, trace=trace,
                          marker=marker, forceOn=forceOn)
        return float(self.ask('CALC' + str(channel) + ':MARK' + str(marker) + ':X?'))

    # position in number of points
    def markerSetX(self, x, channel=1, trace=1, marker=1, forceOn=True):
        self.markerState2(channel=channel, trace=trace,
                          marker=marker, forceOn=forceOn)
        self.write('CALC' + str(channel) + ':MARK' +
                   str(marker) + ':X ' + str(x))
        return self.markerX(channel=channel, marker=marker)

    def markerY(self, channel=1, marker=1, trace=1, forceOn=True):
        self.markerState2(channel=channel, trace=trace,
                          marker=marker, forceOn=forceOn)
        return [float(y) for y in self.ask('CALC' + str(channel) + ':MARK' + str(marker) + ':Y?').split(',')]

    # see doc "Getting Data from the Analyzer"
    def decodeBlock(self, str1, byteEncoding=4):
        if str1[0] != '#' or (byteEncoding != 4 and byteEncoding != 8):
            return
        dtype = float64
        if byteEncoding == 4:
            dtype = float32
        numDigit = int(str1[1])
        byteCount = int(str1[2:2 + numDigit])
        str1 = str1[2 + numDigit:]
        if len(str1) != byteCount or len(str1) % byteEncoding != 0:
            return
        return fromstring(str1, dtype=dtype)

    def trigger(self, channel=1):
        self.write('TRIG:SOUR MAN')
        self.write('INIT' + str(channel) + ':IMM')

    def waitFullSweep(self, channel=1, restore=False):
        mode = self.ask('TRIG:SOUR?')
        self.trigger(channel=channel)
        self.write('*OPC')
        while True:
            time.sleep(0.5)
            esr = int(self.ask('*ESR?'))
            if (esr & 1) == 1:
                break
        if restore:
            self.write('TRIG:SOUR ' + mode)

    def getTrace(self, channel=1, trace=1, waitFullSweep=False, fromMemory=False, timeOut=60):
        handle = self.getHandle()
        handle.timeout = timeOut
        if waitFullSweep:
            print "Getting trace...",
            self.waitFullSweep(channel=channel, restore=True)
        self.write('FORM:BORDER SWAP')  # swap for ibm pc
        # 64 bits = 8 bytes for frequencies according to Keysight doc
        self.write('FORM REAL,64')
        self.selectTrace(channel=channel, trace=trace)
        x = self.decodeBlock(
            self.ask('CALC' + str(channel) + ':X?'), byteEncoding=8)
        # 32 bits = 4 bytes for data according to Keysight doc
        self.write('FORM REAL,32')
        term = 'FDATA'
        if fromMemory:
            term = 'FMEM'
        y = self.decodeBlock(
            self.ask('CALC' + str(channel) + ':DATA? ' + term), byteEncoding=4)
        if waitFullSweep:
            print "done."
        return x, y

    def getFreqMagPhase(self, channel=1, tracesMagPhase=[1, 2], waitFullSweep=False, fromMemory=False, timeOut=60, addedAttenuators=0, unwindPhase=False, substractedSlope=None, deltaPhase=None, phaseOffset=None):
        if tracesMagPhase[0] is not None:
            f1, mag = self.getTrace(channel=channel, trace=tracesMagPhase[
                                    0], waitFullSweep=waitFullSweep, fromMemory=fromMemory, timeOut=timeOut)
        if tracesMagPhase[1] is not None:
            f2, phase = self.getTrace(channel=channel, trace=tracesMagPhase[
                                      1], waitFullSweep=False, fromMemory=fromMemory, timeOut=timeOut)
        cube = Datacube('spectrum')
        cube.createCol(name="freq", values=f1)
        cube.createCol(name="mag", values=mag + addedAttenuators)
        if (f2 != f1).any():
            cube.createCol(name="freq2", values=f2)
        cube.createCol(name="phase", values=phase)
        if addedAttenuators != 0:
            self.correctMag(trace, addedAttenuators=addedAttenuators)
        if unwindPhase or substractedSlope is not None or deltaPhase is not None or phaseOffset is not None:
            self.correctPhase(trace, unwindPhase=unwindPhase, substractedSlope=substractedSlope,
                              deltaPhase=deltaPhase, phaseOffset=phaseOffset)
        return cube

    def correctMag(self, traceCube, addedAttenuators=0):
        if 'mag' in trace.names():
            trace.createCol(name='magCor', values=trace[
                            'mag'] + addedAttenuators)
            params = trace.parameters()
            params['addedAttenuation'] = addedAttenuators

    def correctPhase(self, traceCube, unwindPhase=False, substractedSlope=None, deltaPhase=None, phaseOffset=None):
        if 'phase' in trace.names():
            params['unwound'] = False
            for key in ['substractedSlope', 'deltaPhase', 'phaseOffset']:
                params[ket] = None
            phase = trace['phase']
            if unwindPhase:
                # unwind phase if requested
                phase = self.unwind(phase, period=360)
                params['unwound'] = True
            # flatten phase if requested
            if substractedSlope is not None:
                # flatten by slope subtraction has priority over imposing a the
                # total delta jump
                phase = phase - substractedSlope * (f2 - f2[0])
                params['substractedSlope'] = substractedSlope
            # impose a the total delta jump
            elif deltaPhase is not None:
                phase = phase - \
                    (+phase[-1] - phase[0] - deltaPhase) / \
                    len(phase) * arange(len(phase))
                params['deltaPhase'] = deltaPhase
            if phaseOffset is not None:
                phase = phase + phaseOffset
                params['phaseOffset'] = phaseOffset
            trace.createCol(name='phaseCor', values=phase)

    def unwind(self, li, period=360):
        """Unwind a list, tuple or 1D array initially defined on a circle with period period. Format is preserved."""

        def substract(li1, li2):
            """Subtraction li1-li2 between two lists, tuples or 1D arrays. Format is preserved."""
            result = array(li1) - array(li2)
            if isinstance(li1, list):
                result = list(result)
            elif isinstance(li1, tuple):
                result = tuple(result)
            return result

        def rotateLeft(li, shift=1):
            """Rotate a list, tuple or 1st dimension of an array by shift positions to the left. Format is preserved."""
            shift = shift % len(li)
            result = concatenate((array(li)[shift:], array(li)[:shift]))
            if isinstance(li, list):
                result = list(result)
            elif isinstance(li, tuple):
                result = tuple(result)
            return result

        def derivList(li):
            """Discrete derivative of a list, tuple or 1D array.
            Format is preserved, but with an output length 1 unit below the input length."""
            return substract(rotateLeft(li), li)[:-1]

        def listIntegrate(li):
            """Discrete integration of a list, tuple or 1D array. Format is preserved."""
            for i in range(len(li))[1:]:
                li[i] += li[i - 1]
            return li

        def jump(x):
            dif = [abs(x - period), abs(x), abs(x + period)]
            return dif.index(min(dif)) - 1

        jumps = listIntegrate(map(jump, derivList(li)))
        jumps.insert(0, 0.)
        result = array(jumps) * period + array(li)
        if isinstance(li, list):
            result = list(result)
        elif isinstance(li, tuple):
            result = tuple(result)
        return result

        #----------------------------------------------------------------------
        # Set center frequency or marker to Max or Min
        #----------------------------------------------------------------------

    def extremum(self, target='max', channel=1, trace=1, waitFullSweep=False, **kwargs):
        x, y = self.getTrace(channel=channel, trace=trace,
                             waitFullSweep=waitFullSweep)
        if target == 'max':
            target = max(y)
        else:
            target = min(y)
        pos = where(y == target)[0][0]
        return (trace, (x[pos], y[pos]), pos)

    def centerAtExtremum(self, channel=1, **kwargs):
        (trace, (x0, y0), pos) = self.extremum(channel=channel, **kwargs)
        self.setCenterFrequency(x0, channel=channel)
        return (trace, (x0, y0), pos)

    def centerAtMax(self, **kwargs):
        return self.centerAtExtremum(target='max', **kwargs)

    def centerAtMin(self, **kwargs):
        return self.centerAtExtremum(target='min', **kwargs)

    def markerAtExtremum(self, channel=1, trace=1, marker=1, forceOn=False, allTraces=True, complexOut=False, **kwargs):
        self.markerState2(channel=channel, trace=trace,
                          marker=marker, forceOn=forceOn)
        (trace, (x0, y0), pos) = self.extremum(
            channel=channel, trace=trace, marker=marker, **kwargs)
        if allTraces:
            result = []
            traces = self.measurements(channel=channel)
            for tracei in traces:
                self.markerSetPosition(
                    pos, channel=channel, trace=tracei, marker=marker)
                xi = self.markerX(channel=channel, trace=trace,
                                  marker=marker, forceOn=forceOn)
                yi = self.markerY(channel=channel, trace=trace,
                                  marker=marker, forceOn=forceOn)
                if complexOut == False:
                    yi = yi[0]
                # list of tuples
                # [(trace1,(x1,y1),pos1),(trace2,(x2,y2),pos2),...]
                result.append((tracei, (xi, yi), pos))
        else:
            self.markerSetPosition(pos, channel=channel,
                                   trace=trace, marker=marker)
            result = (trace, (x0, y0), pos)  # tuple
        return result

    def markerAtMax(self, **kwargs):
        return self.markerAtExtremum(target='max', **kwargs)

    def markerAtMin(self, **kwargs):
        return self.markerAtExtremum(target='min', **kwargs)

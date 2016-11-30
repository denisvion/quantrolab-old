import time
import numpy
from pyvisa.vpp43 import set_attribute
from application.lib.instrum_classes import *

"""
This module implements the basic controls of a Tabor AWG.
09/2016
"""


class Waveform:

    def __init__(self):
        """
        this is the doc string for the init method...
        """
        self._name = None
        self._data = None
        self._markers = None
        self._length = None
        self._format = None
        self._rawdata = None


class Sequence:

    def __init__(self):
        """
        this is the doc string for the init method...
        """
        self._length = None


class AwgException(Exception):
    pass


class Instr(VisaInstrument):
    # class Instr(Instrument):

    """
    This is the Tabor's AWG WXxx84 instrument.
    WARNING: Due to management of termination characters by the Tabor's parser, behavior can vary between GPIB, usb, TCPIP-VXI and TCPIP RAW SOCKET connexions.
    This code is tested here for TCPIP RAW SOCKET with termination char \n. Note that termination char is not allowed after any scpi command transfering a binary block.
    Arbitrary waveforms are defined as real numpy arrays with a number of points multiple of 16 and larger than 192,
        with values between -1.0 and 1.0 corresponding to low and high voltages;
    Arbitrary markers are defined as integer numpy arrays with values between 0 and 1 corresponding to low TTL and high TTL.
        IMPORTANT: although marker timestep is 2 waveform points inside Tabor device (see doc),
        markers passed to the instrument methods below should have the waveform sampling.
    Different methods of the instrument translate these real waveforms and markers into 14+2 bit integers (2 chars).
    """

    def initialize(self, visaAddress="TCPIP0::192.168.0.73::5025::SOCKET", term_chars='\n', waitTime=0, force=False, **kwargs):
        """
        Initializes the AWG.
        """
        h = self._handle
        vi = h.vi
        h.read_termination = term_chars
        h.write_termination = term_chars
        set_attribute(vi, VI_ATTR_WR_BUF_OPER_MODE, VI_FLUSH_ON_ACCESS)
        set_attribute(vi, VI_ATTR_RD_BUF_OPER_MODE, VI_FLUSH_ON_ACCESS)
        set_attribute(vi, VI_ATTR_TERMCHAR_EN, VI_TRUE)

    def setWaitTime(self, time):
        """
        Sets the waiting time attribute
        """
        self._waitTime = time
        return self._waitTime

    def waitTime(self):
        """
        Returns the waiting time attribute
        """
        return self._waitTime

    def runAWG(self):
        """
        DOES NOT APPLY TO THIS AWG
        """
        pass

    def stopAWG(self):
        """
        DOES NOT APPLY TO THIS AWG
        """
        pass

    def parameters(self):
        """
        Returns all relevant AWG parameters.
        """
        params = dict()
        params["runMode"] = self.runMode()
        params["repetitionRate"] = self.repetitionRate()
        params["channels"] = []
        params["clockSource"] = self.clockSource()
        # params["triggerInterval"] = self.triggerInterval()
        for i in [1, 2, 3, 4]:  # TODO please adjust the way the channels are addressed - it doesn't work right now Do this for all commented requests
            channelParams = dict()
            channelParams["high"] = self.high(i)
            channelParams["low"] = self.low(i)
            channelParams["amplitude"] = self.amplitude(i)
            channelParams["offset"] = self.offset(i)
            channelParams["skew"] = self.skew(i)
            # channelParams["function"] = self.function(i)
            # channelParams["waveform"] = self.waveform(i)
            # channelParams["phase"] = self.phase(i)
            # channelParams["dac_resolution"] = self.DACResolution(i)
            params["channels"].append(channelParams)
        return params

    def startAllChannels(self):
        # As in awgv2, setState was considered as dangerous programming, it has been replaced here by setOutput which turns the output on/off.
        # This is also closer to the way the Tabor works
        """
        Start all the channels
        """
        for i in [1, 2, 3, 4]:
            self.setOutput(i, 1)

    def output(self, channel):
        """
        Returns the state of the output of a given channels.
        """
        self.write("INSTrument:SELect " + str(int(channel)))
        return self.ask("OUTP:STAT?")  # command executed but program crashes afterwards - please fix

    def setOutput(self, channel, state):
        """
        Set the state of the output of a given channels
        """
        self.write("INSTrument:SELect " + str(int(channel)))
        self.write("OUTP:STAT %d" % state)
        return self.ask("OUTP:STAT?")

    def channels(self):
        """
        Returns the number of channels of the instrument.
        """
        var = self.ask("SYSTem:INFormation:MODel?")
        # The model is WXx284 if 4 channels and WXx282 if 2 channels
        return var[5]

    # Overall timing

    def runMode(self):
        """
        Returns the run mode of the AWG, i.e. either 'cont', 'trig' or 'gated'.
        """
        runMode = 'trig'
        if self.ask('INIT:CONT?') == 'ON':
            runMode = 'cont'
        elif self.ask('INIT:GATE?') == 'ON':
            runMode = 'gated'
        return runMode

    def setRunMode(self, mode):
        """
        Sets and returns the run mode of the AWG, i.e. either 'cont', 'trig' or 'gated'.
        """
        if mode == 'cont':
            self.write('INIT:CONT 1')
        elif mode == 'trig':
            self.write('INIT:CONT 0')
            self.write('INIT:GATE 0')
        elif mode == 'gated':
            self.write('INIT:GATE 1')
        else:
            print 'unknown mode'
        return self.runMode()

    def triggerSource(self):
        """
        Returns the trigger source of the AWG, relevant when its run mode is 'Trig'.
        Source is either 'ext', 'bus', or 'tim'.
        """
        return self.ask('TRIG:SOUR:ADV?')

    def setTriggerSource(self, mode):
        """
        Sets and returns the trigger source of the AWG, relevant when its run mode is 'Trig'.
        Source is either 'ext', 'bus', 'tim' or 'even'.
        """
        if mode in ['ext', 'bus', 'tim', 'even', 'EXT', 'BUS', 'TIM', 'EVENT']:
            self.ask(':TRIG:SOUR:ADV%s;:TRIG:SOUR:ADV?' % mode)
        else:
            print 'unknown mode %s. Allowed modes are "ext, "bus", "tim", or "even". '

    def triggerPeriod(self):
        """
        Returns the trigger period in seconds in run mode 'trig' and trig source 'tim'
        """
        return self.ask(':TRIG:TIM:TIME?')

    def setTriggerPeriod(self, period):
        """
        Sets and returns the trigger period in seconds in run mode 'trig' and trig source 'tim'
        """
        return self.ask(':TRIG:TIM:TIME %f;:TRIG:TIM:TIME?' % period)

    def functionMode(self, channel=1):
        """
        Returns the function mode of the AWG.
        """
        return self.ask('INST %s;:FUNC:MODE?' % channel)

    def setFunctionMode(self, channel=1, mode='FIX'):
        """
        Sets one of the following function modes of the awg:
        FIXed: Pre - defined waveforms
        USER: User defined waveforms = arbitrary
        SEQuence: Sequence mode
        ASEQuence: Advanced sequence mode
        MODulation: Modulation mode
        PULSe: Pulse mode
        PATTern: Pattern mode
        """
        return self.ask(':INST %s;:FUNC:MODE %s;:FUNC:MODE?' % (channel, mode))

    def clockSource(self):
        """
         Returns the value of the clock: source parameter.
        """
        return self.ask(':ROSC:SOUR?')

    def repetitionPeriod(self):
        """
        Returns the repetition period in seconds of the AWG.
        """
        return float(self.ask("PULS:PER?"))

    def setRepetitionPeriod(self, period):
        """
        Sets the repetition period of the AWG in seconds.
        """
        return float(self.ask(":PULS:PER %f;:PULS:PER?" % period))

    def repetitionRate(self):
        """
        Returns the repetition rate in Hz of the AWG.
        """
        return 1 / self.repetitionPeriod()

    def setRepetitionRate(self, rate):
        """
        Sets the repetition rate of the AWG in Hz.
        """
        return 1 / self.setRepetitionPeriod(1 / rate)

    def function(self, channel=1):
        """
        Returns the waveform function of a given channel when the AWG operates as an AFG(FIX mode). Choices are:
        SINusoid | TRIangle | SQUare | RAMP | SINC | GAUSsian | EXPonential | NOISe | DC
        """
        if (self.functionMode() == "FIX"):
            return self.ask(":INST %s;:SOURce:FUNCtion:SHAPe?" % channel)
        else:
            print("ERROR: AWG not in FIXed mode")

    def setFunction(self, channel=1, name='SIN'):
        """
        Sets the waveform function of a given channel if the AWG operates as an AFG(FIX mode). Choices are:
        SINusoid | TRIangle | SQUare | RAMP | SINC | GAUSsian | EXPonential | NOISe | DC
        """
        if (self.functionMode() == "FIX"):
            return self.ask(":INST %s;:SOUR:FUNC:SHAP %s;:SOUR:FUNC:SHAP?" % (channel, name))
        else:
            print("ERROR: AWG not in FIXed mode")

    def skew(self, channel):
        """
        Returns the skew time in seconds of a given channel.
        WARNING: The skew is defined within a pair. If CH1 or CH2 is selected, the skew is the one applied on CH2.
        """
        return float(self.ask(":INST %s;:INST:SKEW?" % channel))

    def Xskew(self, channel):
        """
        Returns the skew time in seconds of a given channel.
        WARNING: The skew is defined within a pair. If CH1 or CH2 is selected, the skew is the one applied on CH2.
        """
        return float(self.ask(":INST %s;:XINST:SKEW?"))

    def setSkew(self, channel, skew):
        """
        Sets the skew time in seconds between the two channels of a pair.
        If CH1 or CH2 is selected, the skew will be applied to CH2.
        Skew is between - 100 ps and +100 ps
        """
        if abs(skew) > 1e-10:
            print 'WRONG PARAMETER: Skew is limited to +/- 100 ps'
        else:
            self.write(":INST %s:SKEW %f" % (channel, time))
        return self.skew(channel)

    def delay(self, channel):
        """
        Returns the number of samples(delay) between the trigger and the waveform start of a given channel.
        """
        return int(self.ask("INST %s;:TRIG:DEL?" % channel))

    def setDelay(self, channel, delay):
        """
        Sets and returns the number of samples(delay) between the trigger and the waveform start of a given channel.
        """
        return self.ask("INST %s;:TRIG:DEL %i;:TRIG:DEL?" % (channel, delay))

    # Vertical scale : voltages

    def DACResolution(self, channel=1):
        """
        Returns the DAC resolution of the AWG in bits.
        """
        return 14

    def setDACResolution(self, channel=1, resolution=14):
        """
        Not applicable to this AWG with fixed depth of 14 bits.
        """
        if resolution != 14:
            print 'WARNING: AWG with fixed depth'
        return 14

    def amplitude(self, channel=1):
        """
        Returns the amplitude of a given channel.
        """
        return float(self.ask("INST %i;:VOLT:AMPL?" % channel))

    def setAmplitude(self, channel, voltage):
        """
        Sets the amplitude of a given channel in volts.
        Allowed range: 50mV - 2 Volts.
        """
        if not (50e-3 <= abs(voltage) <= 2):
            print 'WRONG PARAMETER: voltage is limited to 50mV-2V'
        else:
            self.write(":INST %s;:VOLT:AMPL %f" % (channel, voltage))
        return self.amplitude(channel)

    def offset(self, channel=1):
        """
        Returns the offset of a given channel.
        """
        return float(self.ask("INST %s;:VOLT:OFFS?" % channel))

    def setOffset(self, channel, voltage):
        """
        Sets the offset of a given channel in allowed range - 1V to + 1V.
        """
        if abs(voltage) > 1:
            print 'WRONG PARAMETER: offset is limited to +/-1V'
        else:
            self.write(":INST %s;:VOLT:OFFS %f" % (channel, voltage))
        return self.offset(channel)

    def low(self, channel):
        """
        Returns the low voltage of a given channel.
        """
        return self.offset(channel) - self.amplitude(channel) / 2

    def setLow(self, channel, voltage):
        """
        Sets the low voltage of a given channel. If Vlow is > Vhigh, set high voltage instead
        """
        voltage = float(voltage)
        if (voltage >= self.high(channel)):
            return self.setHigh(channel, voltage)
            print('bite')
        else:
            high = self.high(channel)
            amp = high - voltage
            off = (high + voltage) / 2
            self.setAmplitude(channel, amp)
            self.setOffset(channel, off)
            return self.low(channel)

    def high(self, channel):
        """
        Returns the high voltage of a given channel.
        """
        return self.offset(channel) + self.amplitude(channel) / 2

    def setHigh(self, channel, voltage):
        """
        Sets the high voltage of a given channel without changing the low value.
        If Vlow > Vhigh, set low voltage instead.
        """
        voltage = float(voltage)
        if (voltage < self.low(channel)):
            return self.setLow(channel, voltage)
        else:
            low = self.low(channel)
            amp = voltage - low
            off = (voltage + low) / 2
            self.setAmplitude(channel, amp)
            self.setOffset(channel, off)
            return self.high(channel)

    # FUNCTIONS FOR MARKERS (except marker waveforms)

    def setMarkerState(self, channel, markerchannel, state):
        '''
        Switches marker 'ON' (1) or 'OFF' (0) and returns the final state
        '''
        return self.ask("INST %s;:MARK:SEL %s;:MARK:STAT %s;:MARK:STAT?" % (channel, channel, state)) == 'ON'

    def markerState(self, channel, markerchannel):
        '''
        Returns marker state 'ON' (1) or 'OFF' (0)
        '''
        return self.ask("INST %s;:MARK:SEL %s;:MARK:STAT?" % (channel, channel)) == 'ON'

    def setMarkerSource(self, channel, source):
        '''
        source='WAVE' : enables only a single marker transition
        source='USER' : enables arbitrary marker pattern by loading MarkerState together with the waves using the TRACe command
        '''
        return self.ask("INST:SEL %s;:MARK:SOUR %s;:MARK:SOUR?" % (channel, source))

    def markerSource(self, channel):
        '''
        source='WAVE' : enables only a single marker transition
        source='USER' : enables arbitrary marker pattern by loading MarkerState together with the waves using the TRACe command
        '''
        return self.ask("INST:SEL %s;:MARK:SOUR?" % channel)

    def marker(self, channel, markerchannel):
        '''
        Returns the marker properties in a dictionnary {position, width and delay
        '''
        position = self.ask("INST %s;:MARK:SEL %s;:MARK:POS?" % (channel, channel))
        width = int(self.ask("MARK:WIDT?"))
        delay = float(self.ask("MARK:DEL?"))
        return {'position': position, 'width': width, 'delay': delay}

    def setMarker(self, channel, markerchannel, position=0, width=4, delay=0):
        '''
        Defines a marker made of a single pulse with position, width and delay properties.
        note that the position can be only even numbers
        IMPORTANT: Marker download source has to be INT: do this using setMarkerSource(channel,'WAVE')
        '''
        self.write("INST %s;:MARK:SEL %s;:MARK:POS %i;:MARK:WIDT %i;:MARK:DEL %f" %
                   (channel, channel, position, width, delay))
        return self.marker(channel, markerchannel)

    # FUNCTIONS FOR ARBITRARY WAVEFORMS
    """
    Arbitrary waveforms are defined as real numpy arrays with values between - 1.0 and 1.0 corresponding to low and high voltages;
    the different methods of the instrument translate these real waveforms into 14bit integer ones.
    """

    def deleteWaveform(self, name, channel=1):
        """
        Deletes a given segment(on both channels of a couple), name is the segment number. Be sure you are selecting the correct channel couple.
        """
        self.write(":INST%s;:TRACe:DELete %s" % (channel, name))

    def deleteAllWaveform(self):
        """
        WARNING: This deletes ALL waveform of any channel
        """
        self.write(":TRACe:DELete:ALL")

    def load1RealWaveform(self, realWaveform, channel=1, markers=None, markerShift=12, mode='SINGle', doPrint=False):
        """
        Prepares a waveform with markers in a string, and send it to the Tabor memory.
        - realWaveform: a single waveform encoded between - 1.0 (low) and 1.0 (high);
            Its length should be a multiple of 16 points larger than 192 points;
        - channel: the channel identifier integer;
        - markers: None or [marker1, marker2] with markeri = None or numpy.array of integers 0 or 1;
            The length of each marker different from None should be the same as that of the waveform;
        - mode: 'SINGle', 'DUPLicate', 'ZERoed';
        - doPrint: a boolean indicating whether printing information or not during data preparation and transfer.
        Note: this method simply calls _loadRealWaveforms with a single waveform and markers.
        """
        if markers is not None and channel in [2, 4]:
            print 'WARNING: markers are not overwritten in single waveform transfer on channels 2 or 4.'
        return self._loadRealWaveforms(realWaveform, channel=channel, markers=markers, markerShift=markerShift, mode=mode, doPrint=doPrint)

    def load2RealWaveforms(self, realWaveform1, realWaveform2, channel=1, markers=None, markerShift=12, doPrint=False):
        '''
        Prepares an interleaved pair of waveforms with markers in a string, and send this string to the Tabor memory.
        - realWaveforms: a single or a pair of waveforms, each one being a numpy arrays encoded between -1.0 (low) and 1.0 (high);
            The length of each waveform should be a multiple of 16 points larger than 192;
        - channel: one of the two channel identifier of the chanel pair (integer);
        - markers: None or  [marker1,marker2] with markeri = None or numpy.array of integers 0 or 1;
            The length of each marker different from None should be the same as that of the waveforms;
        - doPrint: a boolean indicating whether printing information or not during data preparation and transfer.
        Note: this method simply calls _loadRealWaveforms with a pair of waveforms and markers.
        '''
        return self._loadRealWaveforms([realWaveform1, realWaveform2], channel=channel, markers=markers, markerShift=markerShift, mode='COMBined', doPrint=doPrint)

    def _loadRealWaveforms(self, realWaveforms, channel=1, markers=None, markerShift=12, mode='SINGle', doPrint=False):
        '''
        Prepares a waveform or an interleaved pair of waveforms with markers in a string, and send this string to the Tabor memory.
        See Tabor WXxx84C user manual (publication N 010614 Rev1.2 July 2015) pages 4.11 and 4.61-4.66
        - realWaveforms: a single or a pair of waveforms, each one being a numpy arrays encoded between -1.0 (low) and 1.0 (high)
            The length of each waveform should be a multiple of 16 points larger than 192;
        - channel: the channel identifier integer;
        - markers: None or  [marker1,marker2] with markeri = None or numpy.array of integers 0 or 1;
            The length of each marker different from None should be the same as that of the waveform(s);
        - markerShift: number of point to shift the markers with respect to waveform (12 is the default. see doc);
        - mode: 'SINGle', 'DUPLicate', 'ZERoed' for one waveform, and 'COMBined' for two waveforms;
            (mode is forced to 'COMB' if two waveforms are detected)
        - doPrint: a boolean indicating whether printing information or not during data preparation and transfer.
        '''
        waveform1, waveform2 = self._checkWaveforms(realWaveforms, markers)
        buflen = len(waveform1)                                     # size of numpy array for data
        if waveform2 is not None:                                   # if there are two waveforms
            buflen *= 2  # double the size
            mode = 'COMB'  # force mode to COMB
            channel = channel if channel % 2 == 0 else channel + 1  # marker data is written to an even channel
        elif mode == 'COMB':                                        # if COMB with a single waveform (this is an error)
            mode = 'SINGle'  # force mode SINGle
        if doPrint:
            print 'Preparing data...',
        t0 = time.time()
        try:
            data = numpy.empty(buflen).astype('uint16')             # try to allocate space in memory
        except MemoryError:
            if doPrint:
                print "Not enough RAM => Using hard drive to store temporary files...",
            from tempfile import mkdtemp                            # or create a memory map on a file
            import os.path as path
            filename = path.join(mkdtemp(), 'taborDataString.dat')
            data = numpy.memmap(filename, dtype='uint16', mode='w+', shape=buflen)
        conv_factor = 0.5 * ((1 << 14) - 1)
        # built the data array
        if waveform2 is not None:                                   # convert and interleave if two waveforms
            for i in xrange(16):
                data[i::32] = ((waveform2[i::16] + 1) * conv_factor).astype('uint16')
                data[i + 16::32] = ((waveform1[i::16] + 1) * conv_factor).astype('uint16')
        else:
            data[:] = ((waveform1[:] + 1) * conv_factor).astype('uint16')  # otherwise just convert
        if markers is not None:                                     # marker construction
            # skip and step parameters for a single waveform. See doc page 4.65 for the 12 point shift
            skip, step = 8, 16
            if waveform2 is not None:                               # and for two waveforms
                skip += 16
                step += 16
            div, mod = divmod(markerShift, 16)
            for marker, bitShift in zip(markers, [14, 15]):
                if marker is not None:        # fill markers in even channels
                    for i in xrange(8):
                        # shift the marker # marker resolution is 2 points => mod/2
                        shift = div * step + ((i + mod / 2) > 7) * skip + mod / 2
                        slice1 = (numpy.arange(skip + i, buflen, step) + shift) % buflen
                        # shift the index if located in the don't care region (see fig 4.4 page 4.65 of the doc)
                        data[slice1] += (marker[2 * i::16] * (1 << bitShift)).astype('uint16')
        if doPrint:
            print "Finished preparing data at time %f s..." % (time.time() - t0)
        # call the download function.
        self._downloadWaveform(data.tostring(), channel=channel, mode=mode, doPrint=doPrint)

    def _checkWaveforms(self, realWaveforms, markers=None):
        """
        Private method that recognizes one or two waveforms in realWaveforms, and returns them, after performing several
        checks on these waveforms and their markers.
        """
        waveform1 = waveform2 = None
        try:
            if isinstance(realWaveforms, numpy.ndarray):
                shape = realWaveforms.shape
                if len(shape) == 1:
                    waveform1 = realWaveforms
                elif len(shape) == 2 and shape[0] == 2:
                    waveform1, waveform2 = realWaveforms
                else:
                    raise Exception(('Cannot recognize one or two waveforms.'))
            elif isinstance(realWaveforms, (list, tuple)) and len(realWaveforms) == 2:
                waveform1, waveform2 = realWaveforms
            else:
                raise Exception(('Cannot recognize one or two waveforms.'))

            wlen = len(waveform1)
            if wlen % 16 != 0:
                raise Exception('Waveform must be divisable by 16.')
            if wlen < 192:
                raise Exception('Waveform too short. Minimum length is 192.')
            if waveform2 is not None and len(waveform2) != wlen:
                raise Exception('Waveforms must have the same length.')
            if markers is not None:
                markersOK = isinstance(markers, (list, tuple)) and len(markers) == 2
                markersOK &= all([marker is None or len(marker) == wlen for marker in markers])
                if not markersOK:
                    raise Exception(
                        'Markers must be either None or a list of two arrays with the same length as waveform(s) or None.')
        except:
            print "Waveforms/Markers have a wrong format"
        return waveform1, waveform2

    def _downloadWaveform(self, data, channel=1, mode='SINGle', doPrint=False):
        """
        Downloads a waveform or an interleaved pair of waveforms, possibly with additional markers, in the Tabor memory.
        See Tabor WXxx84C user manual(publication N 010614 Rev1.2 July 2015) pages 4.11 and 4.61 - 4.66
        - channel: the integer index of the channel
        - data: a string(i.e. an array of bytes) encoding the waveform(s) and the marker(s) on 16 bits(2 bytes) per point;
        - mode can be  'SINGle', 'DUPLicate', 'ZERoed', or 'COMBined' can be used(see page 4.63).
        The length of data should be a multiple of 16 points = 32 bytes in 'SINGle', 'DUPLicate', or 'ZERoed' modes,
        and a multiple of 32 points = 64 bytes in 'COMBined' mode.

        Syntax is TRAC: MOD < mode > ; : TRAC  # <header><binary_block> with no termination chars allowed after the binary block!
            Hence the writeNoTermination function in the code below
        """
        size = len(data)
        header = "#%d%d" % (len("%d" % len(data)), len(data))
        t0 = time.time()
        self.write("INST %s;:TRAC:MODE %s" % (channel, mode))
        self.write("TRACe " + header + data)
        if doPrint:
            print "Data transfered in %f s." % (time.time() - t0)
            print "Please wait until the data has been processed by the awg...",
        self.ask('*OPC?')
        if doPrint:
            print 'Waveform loaded.'

    # Functions concerning sequence mode:  ####

    def setSequenceMode(self, mode):
        '''
        mode = 0  automatic
        mode = 1  once
        mode = 2  stepped
        '''
        if mode == 0:
            self.write("SEQuence:ADVance AUTO")
        elif mode == 1:
            self.write("SEQuence:ADVance ONCE")
        elif mode == 2:
            self.write("SEQuence:ADVance STEP")

    def loadSequence(self, channel, waveforms, loops, jump_flags):  # not yet implemented
        '''
        loads the entire sequence to a channel
        waveforms: numpy array containing the waveforms
        loops: numpy integer array containing info how often a segment should be repeated
        jump_flacs: numpy integer array with values 0 or 1 depending on if the jump condition should be considered after the sequence
        the idea of this implementation is the following:
        1. all segments are written as one big waveform into the memory
        2. the memory gets partitioned
        3. every segment gets its property (e.g. loops, jump_flag)
        '''
        No_segs = len(waveforms)  # number of segments
        seglen = len(waveforms[0])  # lenght of a segment
        waveform = waveform.flatten()  # creating the big waveform\
        self.loadRealWaveform(
            self, waveform, channel=channel)  # loading the waveform into the AWG (todo think about incorporating markers here)

        pass

    def defineSequence_old(self, channel, seg_nos, loops, jump_flags):  # TODO
        '''
        use this to define a sequence table
        '''
        self.write("INSTrument:SELect " + str(int(channel)))
        self.write("SEQ:DEL:ALL")  # delete all stored sequences
        data = ""
        for i in xrange(len(seg_nos)):
            loop = struct.pack("<I", int(loops[i]))
            seg_no = struct.pack("<H", int(seg_nos[i]))
            jump_flag = struct.pack("<H", int(jump_flags[i]))
            data += loop + seg_no + jump_flag
            # prepare 64 bit integer
            # data += struct.pack("<Q", loops[i] << 32 + seg_nos[i] << 16 + jump_flags[i] )
            # temp = struct.pack("<I",int(value))# & ((1 << 32)-1))
            # print struct.unpack('<L',temp)
        header = "#%d%d" % (len("%d" % len(data)), len(data))
        self.write("SEQuence " + header + data)

    def defineSequence(self, channel, seg_nos, loops, jump_flags):
        '''
        use this to define a sequence table
        '''
        self.write("INSTrument:SELect " + str(int(channel)))
        self.write("SEQ:DEL:ALL")  # delete all stored sequences
        self.write("SEQ:SEL 1")
        data = ""
        for i in xrange(len(seg_nos)):
            self.write("SEQuence:DEFine %d, %d, %d, %d" % (i + 1, seg_nos[i], loops[i], jump_flags[i]))

    def defineAdvancedSequence(self, channel, seq_nos, loops, jump_flags):
        '''
        use this to define a sequence table
        '''
        self.write("INSTrument:SELect " + str(int(channel)))
        self.write("ASEQ:DEL")  # delete the previous advanced sequence
        data = ""
        for i in xrange(len(seq_nos)):
            self.write("ASEQuence:DEFine %d, %d, %d, %d" % (i + 1, seq_nos[i], loops[i], jump_flags[i]))

    def deleteAllSequences(self, channel):
        '''
        deletes all sequences
        '''
        self.write("INSTrument:SELect " + str(int(channel)))
        self.write("SEQ:DEL:ALL")

    def deleteSequence(self, channel, seq_No):
        '''
        deletes one sequence
        the max number of sequences is 1000
        '''
        self.write("INSTrument:SELect " + str(int(channel)))
        self.write("SEQ:DEL " + str(int(seq_No)))

    def deleteAllSegments(self, channel):
        '''
        deletes all segments
        '''
        self.write("INSTrument:SELect " + str(int(channel)))
        self.write("TRAC:DEL:ALL")

    def createSegments(self, channel, seg_list):  # ToDo: this doesn't work. The AWG Visa connection crashes
        '''
        partition the memory in segments
        seg_list is a numpy array or list of integers specifying the length of the segments
        '''
        self.write("INSTrument:SELect " + str(int(channel)))
        data = ""
        for value in seg_list:
            # separating the 32 bit number into two two-byte words
            # part1 = struct.pack("<H",int(value) >> 16)
            # part2 = struct.pack("<H",int(value) & ((1 << 16)-1))
            # & ((1 << 32)-1))  #(value & ((1 << 32)-1)) ensures the 32 bit nature of the number
            data += struct.pack("<L", int(value))
        #  += part1
        #  += part2
            # temp = struct.pack("<I",int(value))# & ((1 << 32)-1))
            # print struct.unpack('<L',temp)
        header = "#%d%d" % (len("%d" % len(data)), len(data))
        self.write("SEGMent " + header + data)
        # import sys
        # print "bytes of data"
        # print sys.getsizeof(data)
        # print "size of data"
        # print len(data)
        # print data
        # print "command string"
        # print "SEGMent " + header + data

    def test(self):
        data = ""
        for i in range(10):
            data += struct.pack("<QL", int(0), int(0))
        header = "#%d%d" % (len("%d" % len(data)), len(data))
        self.write("PATTern:COMPosed:LINear " + header + data)

    def deleteTraceData(self, channel):
        '''
        deletes all waveforms for a channel pair
        '''
        self.write("INSTrument:SELect " + str(int(channel)))
        # delete segment memory
        self.write("TRAC:DEL:ALL")

    def definePulseSegments(self, channel, pulse_list):
        '''
        loads a list of pulses into memory
        the pulse length should be a multiple of 16
        otherwise an error occurs
        '''
        size_error = False
        for pulse in pulse_list:
            if len(pulse) % 16 != 0:
                size_error = True
        if not size_error:
            # select channel
            self.write("INSTrument:SELect " + str(int(channel)))
            # partition the memory according to the length of the pulse
            for i in xrange(len(pulse_list)):
                # define a new segment
                seg_id = i + 1  # the +1 is because the segment indices start from 1
                seg_len = len(pulse_list[i])
                self.write("TRACe:DEFine " + str(seg_id) + " " + str(seg_len))
            # load the new pulses into the segments
            for i in xrange(len(pulse_list)):
                # select segment
                seg_id = i + 1
                self.write("TRACe:SELect " + str(seg_id))
                # transfer data
                self.loadRealWaveform(pulse_list[i], channel=channel)
            return True
        else:
            return "Error: Pulse length is not a multiple of 16"

import sys
import getopt
import re
import struct
import numpy

from application.lib.datacube import Datacube

sys.path.append('.')
sys.path.append('../')

from application.lib.instrum_classes import *


class Instr(VisaInstrument):

    def parameters(self, lazy=True):
        return self._params

    def initialize(self, visaAddress="TCPIP0::192.168.0.30::inst0"):
        try:
            print "Initializing an Lecroy waveRunner with address %s" % visaAddress
            self._visaAddress = visaAddress
        except:
            self.statusStr(
                "An error has occured. Cannot initialize Lecroy 104Xi.")

    def getCommunicationSettings(self):
        response1 = self.ask("Comm_ForMat?")
        response2 = self.ask("Comm_HeaDeR?")
        response3 = self.ask("Comm_ORDer?")
        return response1 + " " + response2 + " " + response3

    def setCommunicationSettings(self, comm_Format="DEF9, WORD, BIN", comm_Header="LONG", comm_Order="HI"):
        self.write("Comm_ForMat " + comm_Format)
        self.write("comm_Header " + comm_Header)
        self.write("Comm_ORDer " + comm_Order)
        return self.getCommunicationSettings()

    def getParameters(self, trace="C1", parameter="ALL"):
        # <trace> : PArameter_VAlue? [<parameter>,...,<parameter>]
        # <trace> : = {TA, TB, TC, TD, C1, C2, C3,C4}
        # <parameter> : See table of parameter names on page 126 documentation
        response = self.ask(trace + ":PAVA? " + parameter)
        return response

    def getCursorValue(self, trace="C1", mode="ALL"):
        # <trace> : CuRsor_VAlue? [<mode>,...,<mode>]
        # <trace> : = {TA, TB, TC, TD, C1, C2, C3, C4}
        # <mode> : = {HABS, HREL, VABS, VREL, ALL}
        response = self.ask(trace + ":CuRsor_VAlue? " + mode)
        return response

    def clearSweeps(self):
        # CLear_SWeeps
        self.write("CLear_SWeeps")
        return "clear sweep command sent"

    def setWaveformSetup(self, sparsing=0, numberOfPoints=0, firstPoint=1, numberOfSegments=0):
        # WaveForm_SetUp SP,<sparsing>,NP,<number>,FP,<point>,SN,<segment>
        # <sparsing>: The sparsing parameter defines the interval between returned data points.
        # <number>: indicates how many points should be transmitted.
        # <point>: specifies the address of the first data point to be sent (in a segment).
        # <segment>: indicates which segment should be sent if the waveform was acquired in sequence mode.
        query = "WaveForm_SetUp " + "SP," + str(sparsing) + ",NP," + str(
            numberOfPoints) + ",FP," + str(firstPoint) + ",SN," + str(numberOfSegments)
        self.write(query)
        return self.ask("WaveForm_SetUp?")

    def getWaveformSetup(self):
        return self.ask("WaveForm_SetUp?")

    def getTemplate(self):
        return self.ask("TeMPLate?")

    def inspect(self, trace="C1", string1="WaveDESC", data_type=""):
        # <trace> : INSPect? <string>[,<data_type>]
        # <trace> : = {TA, TB, TC, TD, M1, M2, M3, M4, C1, C2,C3,C4}
        # <string> : = A valid name of a logical block or a valid name of a variable contained in block WAVEDESC (see the command TEMPLATE).
        #           i.e.: WAVEDESC, USERTEXT, TRIGTIME, RISTIME, DATA_ARRAY_1, DATA_ARRAY_2, SIMPLE, DUAL
        #           or in WAVEDESC:
        #               DESCRIPTOR_NAME, TEMPLATE_NAME, COMM_TYPE,COMM_ORDER,WAVE_DESCRIPTOR,USER_TEXT,
        #               RES_DESC1,TRIGTIME_ARRAY,RIS_TIME_ARRAY,RES_ARRAY1,WAVE_ARRAY_1,WAVE_ARRAY_2,RES_ARRAY2,
        #               RES_ARRAY3,INSTRUMENT_NAME,INSTRUMENT_NUMBER,TRACE_LABEL,RESERVED1,RESERVED2,WAVE_ARRAY_COUNT   : 1001
        #               PNTS_PER_SCREEN,FIRST_VALID_PNT,LAST_VALID_PNT,FIRST_POINT,SPARSING_FACTOR,SEGMENT_INDEX,
        #               SUBARRAY_COUNT,SWEEPS_PER_ACQ,POINTS_PER_PAIR,PAIR_OFFSET,VERTICAL_GAIN,VERTICAL_OFFSET,
        #               MAX_VALUE,MIN_VALUE,NOMINAL_BITS,NOM_SUBARRAY_COUNT,HORIZ_INTERVAL,HORIZ_OFFSET,PIXEL_OFFSET,
        #               VERTUNIT,HORUNIT,HORIZ_UNCERTAINTY,TRIGGER_TIME,ACQ_DURATION,RECORD_TYPE,PROCESSING_DONE,
        #               RESERVED5,RIS_SWEEPS,TIMEBASE,VERT_COUPLING,PROBE_ATT,FIXED_VERT_GAIN,BANDWIDTH_LIMIT,
        #               VERTICAL_VERNIER,ACQ_VERT_OFFSET,WAVE_SOURCE
        # <data_type> : = {BYTE, WORD, FLOAT} (only for data blocks)
        query = trace + ":INSPect? " + string1
        if data_type != "":
            query += "," + data_type
        return self.ask(query)

    def getHorizInfor(self, trace="C1"):
        wavedescriptor = self.inspect(
            trace=trace, string1="WaveDESC", data_type="").split()
        horizOffset = float(
            wavedescriptor[wavedescriptor.index('HORIZ_OFFSET') + 2])
        horizInterval = float(
            wavedescriptor[wavedescriptor.index('HORIZ_INTERVAL') + 2])
        return [horizOffset, horizInterval]

    def getWFFromInspect(self, trace="C1"):
        data = self.inspect(
            trace=trace, string1="DATA_ARRAY_1", data_type="").split()[2:-1]
        return data

    def getWaveforms(self, trace="C1", block="ALL"):
        # <trace> : WaveForm? <block>
        # <trace> : = {TA, TB, TC,TD, M1, M2, M3, M4, C1, C2, C3,C4}
        # <block> : = {DESC, TEXT, TIME, DAT1, DAT2, ALL}
        response = self.ask(trace + ":WaveForm? " + block)
        return response

    def getWaveform(self, channel=1):
        r = self.inspect("C%i" % channel, "DATA_ARRAY_1")[12:]
        r = r.replace("\r\n", "")
        r = r.replace("\"", "")
        r = r.replace("  ", " ")
        r = r.replace("  ", " ")
        r = r.replace("  ", " ")
        r = r.replace("  ", " ")
        r = r.replace("  ", " ")
        r = r.split(" ")
        r = [float(x) if x != '' else 0 for x in r]
        d = Datacube()
        d.createColumn("C%i" % channel, r)
        hi = self.inspect("C%i" % channel, "HORIZ_INTERVAL")[29:]
        hi = hi.replace("\"", "")
        hi = hi.replace(" ", "")
        hi = float(hi)
        ho = self.inspect("C%i" % channel, "HORIZ_OFFSET")[29:]
        ho = ho.replace("\"", "")
        ho = ho.replace(" ", "")
        ho = float(ho)

        t = numpy.zeros(len(r))
        for i in range(len(r)):
            t[i] = ho + i * hi
        d.createColumn('t', t)
        return d

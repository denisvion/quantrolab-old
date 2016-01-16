import sys
import getopt
import numpy
from numpy import *

from application.lib.instrum_classes import *
from application.helpers.instrumentmanager.instrumentsmgr import InstrumentManager


__DEBUG__ = False


class Instr(Instrument):

    def initialize(self, generators=[]):
        """
        Initialise the instrument at instantiation
        """
        self._generators = [[InstrumentManager().getInstrument(n[0]), n[
            1]] for n in generators]
        self._params = []

    def saveState(self, name):
        """
        returns the params dictionary
        """
        return self._params

    def restoreState(self, state):
        """
        Restores the pulse generator from the params dicitonary indicated
        """
        return None

    def pulses(self, generatorName=None):
        if generatorName is not None:
            def cond(i, n):
                if i[0] == n:
                    return i
            generators = [cond(i, generatorName) for i in self._generators]
        else:
            generators = self._generators
        g = dict()
        for generator in generators:
            g[generator[0]] = dict()
            i = 0
            for p in generator[0].pulseList:
                # {'shape':p._pulseArray,'frequency':p.frequency,'phase':p.phase,'corrections':p.applyCorrections,'name':p.name}
                g[generator[0]][i] = p
                i += 1
        return g

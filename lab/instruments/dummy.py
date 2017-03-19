from application.lib.instrum_classes import *


class Instr(Instrument):
    """
    Dummy instrument class for debugging purposes
    """
    # creator function

    def initialize(self, *args, **kwargs):
        """
        Initializes the dummy instrument.
        """
        self.initialized = True

    def method1(self, a):
        """
        Simply returns its argument
        """
        return a

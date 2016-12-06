from application.lib.instrum_classes import *


class Instr(Instrument):
    """
    Dummy instrument class for debugging purposes
    """
    # creator function

    def initialize(self, arg1, arg2, kwarg1=100, kwarg2="toto", kwarg3="100", **kwargs):
        """
        Initializes the dummy instrument.
        """
        self.initialized = True

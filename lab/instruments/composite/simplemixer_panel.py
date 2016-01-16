import sys

sys.path.append('.')
sys.path.append('../')

from application.lib.instrum_classes import *
from application.lib.instrum_panel import FrontPanel
from application.ide.widgets.numericedit import *

import datetime

import instruments


class Panel(FrontPanel):

    def calibrate(self):
        self.instrument.dispatch("calibrate",)

    def stop(self):
        self.instrument.stop()

    def reInit(self):
        self.instrument.dispatch("reInitCalibration")

    def __init__(self, instrument, parent=None):

        super(Panel, self).__init__(instrument, parent)

        self.title = QLabel(instrument.name())
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("QLabel {font:18px;}")
        self.fsbEdit = NumericEdit("")

        self.CalibrateButton = QPushButton("Calibrate")

        self.grid = QGridLayout(self)
        self.grid.addWidget(self.CalibrateButton)

        self.connect(self.CalibrateButton, SIGNAL("clicked()"), self.calibrate)

        self.qw.setLayout(self.grid)

        instrument.attach(self)
#        self.updateValues()

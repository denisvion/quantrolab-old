import sys
import time

from application.lib.instrum_classes import *
from application.lib.instrum_panel import FrontPanel

import instruments


class Panel(FrontPanel):

    def __init__(self, instrument, parent=None):
        super(Panel, self).__init__(instrument, parent)

        self.title = QLabel(instrument.name())
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("QLabel {font:18px;}")

        self.grid = QGridLayout(self)
        self.grid.addWidget(self.title, 0, 0)
        self.qw.setLayout(self.grid)

        instrument.attach(self)

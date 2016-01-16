import sys
import time

sys.path.append('.')
sys.path.append('../')

from application.lib.instrum_classes import *
from application.ide.mpl.canvas import MyMplCanvas as Canvas
from application.lib.instrum_panel import FrontPanel
from application.ide.widgets.numericedit import *
import pylab
import matplotlib.ticker as ticker
import datetime

import instruments


class Panel(FrontPanel):

    def __init__(self, instrument, parent=None):
        super(Panel, self).__init__(instrument, parent)

        self.title = QLabel(instrument.name())
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("QLabel {font:18px;}")

        self.canvas = Canvas(dpi=100)
        self.canvas.setFixedHeight(300)

        self.grid = QGridLayout(self)
        self.interval = 10000

        self.grid.addWidget(self.title, 0, 0)
        self.grid.addWidget(self.temperature, 1, 0)
        self.grid.addWidget(self.canvas)

        self.timer = QTimer(self)
        self.timer.setInterval(self.interval)
        self.timer.start()

#        self.connect(self.timer,SIGNAL("timeout()"),lambda :self.instrument.dispatch("temperature"))

        self.qw.setLayout(self.grid)

        instrument.attach(self)

import os
import sys

sys.path.append('.')
sys.path.append('../')

from application.lib.instrum_classes import *
from application.ide.mpl.canvas import MyMplCanvas
from application.lib.instrum_panel import FrontPanel
from application.ide.widgets.numericedit import *

import datetime

import instruments


class Panel(FrontPanel):

    def __init__(self, instrument, parent=None):
        super(Panel, self).__init__(instrument, parent)

        self._workingDirectory = None

        self.title = QLabel(instrument.name())
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("QLabel {font:18px;}")
        self.fsbEdit = NumericEdit("")

        self.paramBox = QTextEdit()
        self.paramBox.setReadOnly(True)
        self.paramBox.setMaximumSize(1000, 80)

        self.reInitButton = QPushButton("Re-init calibration")
        self.calibrateOffsetButton = QPushButton("Calibrate offsets")
        self.calibrateButton = QPushButton("Calibrate @ IF (GHz) = ")
        self.stopButton = QPushButton("Stop")
        self.enableButtons()
        self.saveButton = QPushButton("Save calibration...")
        self.loadButton = QPushButton("Load calibration...")
        self.calToDataManCheckBox = QCheckBox("Calib. => dataManager")
        self.optToDataManCheckBox = QCheckBox("Optim. => damaManager")
        self.calToDataManCheckBox.setChecked(True)
        self.optToDataManCheckBox.setChecked(True)

        self.testButton = QPushButton("Test sideband @ IF (GHz)")
        self.fsbEdit2 = NumericEdit("")

        self.grid = QGridLayout(self)

        self.grid.addWidget(QLabel('Parameters'), self.grid.rowCount(), 0)
        self.grid.addWidget(self.paramBox, self.grid.rowCount(), 0, 1, 3)

        row = self.grid.rowCount()
        self.grid.addWidget(self.reInitButton, row, 0)
        self.grid.addWidget(self.loadButton, row, 1)
        self.grid.addWidget(self.saveButton, row, 2)

        row = self.grid.rowCount()
        self.grid.addWidget(self.calibrateOffsetButton, row, 0)
        self.grid.addWidget(self.calibrateButton, row, 1)
        self.grid.addWidget(self.fsbEdit, row, 2)

        row = self.grid.rowCount()
        self.grid.addWidget(self.stopButton, row, 0)
        self.grid.addWidget(self.calToDataManCheckBox, row, 1)
        self.grid.addWidget(self.optToDataManCheckBox, row, 2)

        row = self.grid.rowCount()
        self.grid.addWidget(self.testButton, row, 1)
        self.grid.addWidget(self.fsbEdit2, row, 2)

        self.connect(self.reInitButton, SIGNAL("clicked()"), self.reInit)
        self.connect(self.calibrateOffsetButton, SIGNAL(
            "clicked()"), self.calibrateIQOffset)
        self.connect(self.calibrateButton, SIGNAL("clicked()"), self.calibrate)
        self.connect(self.stopButton, SIGNAL("clicked()"), self.stop)
        self.connect(self.saveButton, SIGNAL("clicked()"), self.saveState)
        self.connect(self.loadButton, SIGNAL("clicked()"), self.restoreState)
        self.connect(self.calToDataManCheckBox, SIGNAL(
            "stateChanged(int)"), self.calToDataManager)
        self.connect(self.optToDataManCheckBox, SIGNAL(
            "stateChanged(int)"), self.optToDataManager)
        self.connect(self.testButton, SIGNAL("clicked()"), self.testSideband)

        self.qw.setLayout(self.grid)

        instrument.attach(self)
        self.displayParams()

    def workingDirectory(self):
        if self._workingDirectory is None:
            return os.getcwd()
        return self._workingDirectory

    def setWorkingDirectory(self, filename):
        if filename != None:
            directory = os.path.dirname(str(filename))
            self._workingDirectory = directory
        else:
            self._workingDirectory = None

    def reInit(self):
        self.instrument.dispatch("reInitCal", save=False)

    def displayParams(self):
        params = self.instrument.parameters()
        self.paramBox.setText('')
        for key in params.keys():
            self.paramBox.setTextColor(QColor('Red'))
            self.paramBox.insertPlainText(QString(key + ': '))
            self.paramBox.setTextColor(QColor('Black'))
            self.paramBox.insertPlainText(QString(str(params[key]) + '\n'))

    def saveState(self):
        # myDialog=QFileDialog()
        # myDialog.setFileMode (2) # both files and folders
        directory = str(QFileDialog.getExistingDirectory(caption='Select folder for saving calibration files',
                                                         options=QFileDialog.DontUseNativeDialog, directory=QString(self.workingDirectory())))
        if os.path.isdir(directory):
            self.setWorkingDirectory(directory)
            self.instrument.dispatch("saveState", directory)

    def restoreState(self):
        directory = str(QFileDialog.getExistingDirectory(
            caption='Select folder with calibration files', directory=QString(self.workingDirectory())))
        if os.path.isdir(directory):
            self.setWorkingDirectory(directory)
            self.instrument.dispatch("restoreState", directory)

    def calToDataManager(self, i):
        if i > 0:
            self.instrument.dispatch("calToDataManager")

    def optToDataManager(self, i):
        if i > 0:
            self.instrument.dispatch("optToDataManager")

    def calibrateIQOffset(self):
        self.disableButtons()
        self.instrument.dispatch("calibrateIQOffset", calToDataMan=self.calToDataManCheckBox.isChecked(
        ), optToDataMan=self.optToDataManCheckBox.isChecked())

    def calibrate(self):
        self.disableButtons()
        self.instrument.dispatch("calibrate", self.fsbEdit.getValue(
        ), calToDataMan=self.calToDataManCheckBox.isChecked(), optToDataMan=self.optToDataManCheckBox.isChecked())

    def stop(self):
        self.enableButtons()
        self.instrument.terminate()

    def testSideband(self):
        self.instrument.dispatch(
            "loadSidebandWaveform", IF=self.fsbEdit2.getValue())

    def disableButtons(self):
        self.reInitButton.setEnabled(False)
        self.calibrateOffsetButton.setEnabled(False)
        self.calibrateButton.setEnabled(False)
        self.stopButton.setEnabled(True)

    def enableButtons(self):
        self.reInitButton.setEnabled(True)
        self.calibrateOffsetButton.setEnabled(True)
        self.calibrateButton.setEnabled(True)
        self.stopButton.setEnabled(False)

    def updatedGui(self, subject, property=None, value=None, message=None):
        if subject == self.instrument:
            if property in ['calibrate', 'calibrateIQOffset']:
                self.enableButtons()
                self.displayParams()
            elif property == ['saveCal', 'loadCal']:
                self.displayParams()

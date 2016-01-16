import sys
import string
import time
from datetime import *

sys.path.append('.')
sys.path.append('../')

from application.lib.instrum_classes import *
from gui.mpl.canvas import *
from gui.frontpanel import FrontPanel
from frontpanels.scpichat import *
from frontpanels.helpWidget import *


# This is the VNA dashboard.
class Panel(FrontPanel):

    # Initializes the front panel.
    def __init__(self, instrument, parent=None):
        super(Panel, self).__init__(instrument, parent)

        self._reference = None
        self._traces = []
        self._workingDirectory = ''
        self.fileDialog = QFileDialog()

        self.setWindowTitle('Keysight VNA Control Panel')

        # Stimulus and measurement control
        readButton = QPushButton('Read')
        self.connect(readButton, SIGNAL('clicked()'), self.requestSetup)
        sendButton = QPushButton('Send')
        self.connect(sendButton, SIGNAL('clicked()'), self.requestSetSetup)
        self.AvgON = QCheckBox('Average')
        self.connect(self.AvgON, SIGNAL('stateChanged(int)'),
                     lambda: self.requestSetAvg(self.AvgON.isChecked()))

        labels = ['Power (dBm)', 'Center freq.(GHz)', 'Span (GHz)', 'Start freq. (GHz)',
                  'Stop freq. (GHz)', 'Video BW (Hz)', 'Points', 'Avg counts']
        self.spinBoxNames = ['power', 'centerInGHz', 'spanInGHz',
                             'startInGHz', 'stopInGHz', 'videoBW', 'numOfPoints', 'avgCount']
        types = ['double', 'double', 'double',
                 'double', 'double', 'double', 'int', 'int']
        self.setNames = ['setTotalPower', 'setCenterInGHz', 'setSpanInGHz', 'setStartInGHz',
                         'setStopInGHz', 'setVideoBW', 'setNumberOfPoints', 'setNumberOfAveraging']
        self.getNames = ['totalPower', 'getCenterInGHz', 'getSpanInGHz', 'getStartInGHz',
                         'getStopInGHz', 'videoBW', 'numberOfPoints', 'numberOfAveraging']
        maxima = [0, 20, 20, 20, 20, 10000., 1601, 4000]
        minima = [-90, 0.04, 0.04, 0.04, 0.04, 10., 51, 1]
        decimals = [2, 9, 9, 9, 9, 0, 0, 0]
        # autosend below is deactivated
        # def connectInNewScope(spinBox0,setName0,getName0):
        #  self.connect(spinBox0,SIGNAL('valueChanged('+type0+')'),lambda: self.requestSetParam(setName0,getName0,spinBox0))

        def connectInNewScope(spinBox0):
            self.connect(spinBox0, SIGNAL('valueChanged(' + type0 + ')'),
                         lambda: self.setTextColor(spinBox0, 'red'))
        for spinBoxName, type0, setName, getName, minimum, maximum, decimal in zip(self.spinBoxNames, types, self.setNames, self.getNames, minima, maxima, decimals):
            if type0 == 'double':
                setattr(self, spinBoxName, QDoubleSpinBox())
            else:
                setattr(self, spinBoxName, QSpinBox())
            spinBox = getattr(self, spinBoxName)
            if type0 == 'double':
                spinBox.setDecimals(decimal)
            spinBox.setMaximum(maximum)
            spinBox.setMinimum(minimum)
            # autosend below is deactivated
            # connectInNewScope(spinBox,setName,getName)
            connectInNewScope(spinBox)

        # Graphs
        self.mag = MatplotlibCanvas(self, width=5, height=4, dpi=100)
        self.mag.axes.set_visible(True)
        self.phase = MatplotlibCanvas(self, width=5, height=4, dpi=100)
        self.phase.axes.set_visible(True)
        self.scpiChat = Scpichat(parentFrontPanel=self)
        # self.helpWidget=HelpWidget(parentFrontPanel=self)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.mag, 'Amplitude')
        self.tabs.addTab(self.phase, 'Phase')
        self.tabs.addTab(self.scpiChat, 'SCPI commands')
        # self.tabs.addTab(self.helpWidget,'Help')

        updateButton = QPushButton('Get traces')
        self.connect(updateButton, SIGNAL('clicked()'), self.requestAcquire)
        self.waitFullSweepButton = QCheckBox('New sweep', checked=False)
        updateButtonM = QPushButton('Get memory')
        self.connect(updateButtonM, SIGNAL('clicked()'), self.requestAcquireM)
        self.showLegend = QCheckBox('Legend', checked=False)
        self.connect(self.showLegend, SIGNAL(
            'stateChanged(int)'), self.plotTraces)
        clearButton = QPushButton('Clear traces')
        self.connect(clearButton, SIGNAL('clicked()'), self.clearTraces)
        saveButton = QPushButton('Save all')
        self.connect(saveButton, SIGNAL('clicked()'), self.saveTraces)
        saveFigButton = QPushButton('Save fig.')
        self.connect(saveFigButton, SIGNAL('clicked()'), self.savePlot)
        clearRefButton = QPushButton('Clear ref')
        self.connect(clearRefButton, SIGNAL('clicked()'),
                     lambda: self.makeReference(None))
        hideAllButton = QPushButton('Hide all')
        self.connect(hideAllButton, SIGNAL('clicked()'), self.hideAll)

        applyCorrec = QPushButton('Correct now')
        self.connect(applyCorrec, SIGNAL('clicked()'), self.applyCorrections)
        self.corrParams = ['addedAtten', 'unwind',
                           'subtractedSlope', 'deltaPhase', 'phaseOffset']
        self.addedAtten = QDoubleSpinBox()
        self.unwind = QCheckBox('Unwind')
        self.subtractedSlope = QDoubleSpinBox()
        self.deltaPhase = QDoubleSpinBox()
        self.phaseOffset = QDoubleSpinBox()

        self.traces = QTableWidget()
        self.traces.horizontalHeader().setStretchLastSection(True)
        self.traces.setColumnCount(3)
        self.traces.setColumnWidth(1, 300)
        self.traces.setHorizontalHeaderItem(0, QTableWidgetItem('filename'))
        dw = QTableWidgetItem('description')
        dw.setSizeHint(QSize(400, 30))
        self.traces.setHorizontalHeaderItem(1, dw)
        self.traces.setHorizontalHeaderItem(2, QTableWidgetItem('options'))
        self.connect(self.traces, SIGNAL('cellChanged(int,int)'),
                     self.updateTraceProperties)
        self.connect(self.traces, SIGNAL(
            'currentCellChanged(int,int,int,int)'), self.updateCorrections)

        # Place interface elements

        # top subgrid 1
        subGrid1 = QGridLayout()
        subGrid1.setSpacing(10)
        subGrid1.addWidget(readButton, 0, 0)
        subGrid1.addWidget(sendButton, 1, 0)
        for label, spinBoxName in zip(labels, self.spinBoxNames):
            col = subGrid1.columnCount()
            if spinBoxName != 'avgCount':
                subGrid1.addWidget(QLabel(label), 0, col)
            else:
                subGrid1.addWidget(self.AvgON, 0, col)
            subGrid1.addWidget(getattr(self, spinBoxName), 1, col)

        subGrid2 = QGridLayout()
        subGrid2.setSpacing(10)
        subGrid2.addWidget(updateButton, 0, 0)
        subGrid2.addWidget(self.waitFullSweepButton, 0, 1)
        subGrid2.addWidget(updateButtonM, 0, 2)
        subGrid2.addWidget(self.showLegend, 0, 3)
        subGrid2.addWidget(clearButton, 0, 4)
        subGrid2.addWidget(saveButton, 0, 5)
        subGrid2.addWidget(saveFigButton, 0, 6)
        subGrid2.addWidget(clearRefButton, 0, 7)
        subGrid2.addWidget(hideAllButton, 0, 8)

        subGrid3 = QGridLayout()
        subGrid3.setSpacing(10)
        subGrid3.addWidget(applyCorrec)
        subGrid3.addWidget(QLabel('Ext. atten (dB)='), 0,
                           subGrid3.columnCount(), alignment=Qt.Alignment(2))
        subGrid3.addWidget(self.addedAtten, 0, subGrid3.columnCount())
        self.addedAtten.setMinimum(0)
        self.addedAtten.setMaximum(200)
        subGrid3.addWidget(self.unwind, 0, subGrid3.columnCount())
        subGrid3.addWidget(QLabel('- slope (deg/GHz)'), 0,
                           subGrid3.columnCount(), alignment=Qt.Alignment(2))
        subGrid3.addWidget(self.subtractedSlope, 0, subGrid3.columnCount())
        self.subtractedSlope.setMinimum(-10000)
        self.subtractedSlope.setMaximum(10000)
        subGrid3.addWidget(QLabel('Dphi (deg)='), 0,
                           subGrid3.columnCount(), alignment=Qt.Alignment(2))
        subGrid3.addWidget(self.deltaPhase, 0, subGrid3.columnCount())
        self.deltaPhase.setMinimum(-1000)
        self.deltaPhase.setMaximum(1000)
        subGrid3.addWidget(QLabel('+ offset (deg)'), 0,
                           subGrid3.columnCount(), alignment=Qt.Alignment(2))
        subGrid3.addWidget(self.phaseOffset, 0, subGrid3.columnCount())
        self.phaseOffset.setMinimum(-360)
        self.phaseOffset.setMaximum(360)
        self.correcWidget = QWidget()
        self.correcWidget.setLayout(subGrid3)
        self.correcWidget.setVisible(False)

        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        self.grid.addItem(subGrid1, self.grid.rowCount(), 0)
        self.grid.addWidget(self.tabs, self.grid.rowCount(), 0)
        self.grid.addItem(subGrid2, self.grid.rowCount(), 0)
        self.grid.addWidget(self.correcWidget, self.grid.rowCount(), 0)
        self.grid.addWidget(self.traces, self.grid.rowCount(), 0)

        self.qw.setLayout(self.grid)
        self.setMinimumWidth(640)
        self.setMinimumHeight(500)

        self.plotTraces()

        try:
            self.requestSetup()
        except:
            print 'Error occured when trying to read vna parameters.'

    def updateTraceList(self):
        self.traces.setRowCount(len(self._traces))
        for i in range(0, len(self._traces)):
            self.traces.setItem(i, 0, QTableWidgetItem(self._traces[i].name()))
            self.traces.setItem(i, 1, QTableWidgetItem(
                self._traces[i].description()))

            myFullWidget = QWidget()
            myLayout = QGridLayout()
            myFullWidget.setLayout(myLayout)
            myFullWidget.setFixedHeight(50)
            checkBoxShow = QCheckBox('show')
            checkBoxShow.setCheckState(
                Qt.Checked if self.visibility(i) == True else Qt.Unchecked)
            checkBoxCorrec = QCheckBox('correc')
            checkBoxCorrec.setCheckState(
                Qt.Checked if self.correctivity(i) == True else Qt.Unchecked)
            subLayout = QGridLayout()
            subLayout.addWidget(checkBoxShow, 0, 0)
            subLayout.addWidget(checkBoxCorrec, 1, 0)

            # myLabel.setLayout(myLayout)
            deleteButton = QPushButton('Delete')
            saveButton = QPushButton('Save')
            refButton = QPushButton('Make ref')
            dataMangerButton = QPushButton('->DataMan.')
            myLayout.addLayout(subLayout, 0, 0)
            myLayout.addWidget(deleteButton, 0, 1)
            myLayout.addWidget(saveButton, 0, 2)
            myLayout.addWidget(refButton, 0, 3)
            myLayout.addWidget(dataMangerButton, 0, 4)

            # Programming with 'lambda' rocks :)
            self.connect(checkBoxShow, SIGNAL('stateChanged(int)'),
                         lambda state, x=i: self.setVisibility(x, state))
            self.connect(checkBoxCorrec, SIGNAL(
                'stateChanged(int)'), self.correcOnOff)
            self.connect(deleteButton, SIGNAL('clicked()'),
                         lambda x=i: self.deleteTrace(x))
            self.connect(saveButton, SIGNAL('clicked()'),
                         lambda x=i: self.saveTrace(x))
            self.connect(refButton, SIGNAL('clicked()'),
                         lambda x=i: self.makeReference(x))
            self.connect(dataMangerButton, SIGNAL('clicked()'),
                         lambda x=i: self.sendToDataManager(x))

            self.traces.setCellWidget(i, 2, myFullWidget)
            self.traces.setRowHeight(i, 50)

    def applyCorrections(self):
        cube = self._traces[self.traces.currentRow()]
        if self.addedAtten not in [None, 0, 0.]:
            self.instrument.dispatch(
                'correctMag', cube, addedAttenuators=self.addedAtten.value())
        self.instrument.dispatch('correctPhase', cube, unwindPhase=self.unwind.isChecked(), subtractedSlope=self.subtractedSlope.value(
        ) / 1e9, deltaPhase=self.deltaPhase.value(), phaseOffset=self.phaseOffset.value())

    def updateCorrections(self, newRow, newCol, oldRow, oldCol):
        # print newRow,newCol,oldRow,oldCol
        self.debugPrint('in updateCorrections')
        if newRow != oldRow:
            correc = self.traces.cellWidget(
                newRow, 2).children()[2].isChecked()
            self.correcWidget.setVisible(correc)
            if correc:
                self.resetCorrec()
                corrections = self._traces[newRow].parameters()
                for key in self.corrParams:
                    widget = getattr(self, key)
                    if key in corrections:
                        if key == 'subtractedSlope':
                            widget.setValue(corrections[key] * 1e9)
                        elif isinstance(widget, QDoubleSpinBox):
                            widget.setValue(corrections[key])
                        elif isinstance(widget, QCheckBox):
                            widget.setChecked(corrections[key])
            self.setCorrectivity(newRow, correc)
            self.plotTraces()

    def resetCorrec(self):
        for key in self.corrParams:
            widget = getattr(self, key)
            if isinstance(widget, QDoubleSpinBox):
                widget.setValue(0)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(False)

    def correcOnOff(self):
        """
        This function is a trick to generate a row change when clicking on a correc checkBox
        """
        optionsWidget = self.sender().parentWidget()
        rowCount = self.traces.rowCount()
        row = 0
        while True and row != rowCount:
            if self.traces.cellWidget(row, 2) == optionsWidget:
                break
            row += 1
        if row < rowCount:
            self.traces.setCurrentCell(-1, -1)
            # should generate a currentCellChanged with a new row
            self.traces.setCurrentCell(row, 2)

    # Plots the given traces.
    def plotTraces(self):
        if len(self._traces) == 0:
            self.mag.axes.set_visible(False)
            self.phase.axes.set_visible(False)
            self.mag.draw()
            self.phase.draw()
            return
        plots = []
        phaseplots = []
        legends = []
        for x in range(0, len(self._traces)):
            trace = self._traces[x]
            if self.visibility(x):
                plots.append(map(lambda x: x / 1e9, self._traces[x]['freq']))
                phaseplots.append(
                    map(lambda x: x / 1e9, self._traces[x]['freq']))
                if self.correctivity(x) and 'magCor' in trace.names():
                    mag = trace['magCor']
                    phase = trace['phaseCor']
                else:
                    mag = trace['mag']
                    phase = trace['phase']
                if self._reference != None and self._reference != trace:
                    mag = mag - self._reference['mag']
                    phase = phase - self._reference['phase']
                plots.append(mag)
                phaseplots.append(phase)
                legends.append(trace.name())
        if len(plots) == 0:
            self.mag.axes.set_visible(False)
            self.phase.axes.set_visible(False)
        else:
            self.mag.axes.clear()
            self.mag.axes.plot(*list(plots))
            self.mag.axes.grid(True)
            if self.showLegend.isChecked():
                self.mag.axes.legend(legends, 'lower left')
            self.mag.axes.set_xlabel('frequency [GHz]')
            self.mag.axes.set_ylabel('amplitude [dB]')
            self.mag.axes.set_visible(True)

            self.phase.axes.clear()
            self.phase.axes.plot(*list(phaseplots))
            self.phase.axes.grid(True)
            if self.showLegend.isChecked():
                self.phase.axes.legend(legends, 'lower left')
            self.phase.axes.set_xlabel('frequency [GHz]')
            self.phase.axes.set_ylabel('phase [deg]')
            self.phase.axes.set_visible(True)

        self.mag.draw()
        self.phase.draw()

    # Update handler. Gets invoked whenever the instrument gets a new trace.
    def updatedGui(self, subject, property=None, value=None, message=None):
        self.debugPrint('in vna frontpanel updatedGui with subject=', subject,
                        ' property=', property, ' value=', value, ' message=', message)
        if subject == self.instrument:
            if property == 'getFreqMagPhase':
                # print 'Trace data arrived!'
                if not value in self._traces:
                    self._traces.append(value)
                    self.plotTraces()
                    self.updateTraceList()
            elif property == 'getSetup':
                for key in value:
                    if hasattr(self, key):
                        widget = getattr(self, key)
                        # use the fact that spin boxes have the same names as
                        # the keys in the returned dictionary
                        widget.setValue(value[key])
                        self.setTextColor(widget, 'black')
                self.AvgON.blockSignals(True)
                self.AvgON.setChecked(value['avgONOFF'])
                self.AvgON.blockSignals(False)
            elif property == 'setAverage':
                if self.AvgON.isChecked() != value:
                    self.AvgON.setChecked(value)
            elif property in ['correctMag', 'correctPhase']:
                self.plotTraces()

    def requestSetup(self):
        self.instrument.dispatch('getSetup')

    def requestSetAvg(self, b):
        self.instrument.dispatch('setAverage', b)

    def requestSetParam(self, setName, getName, widget):
        self.setTextColor(widget, 'red')
        newVal = widget.value()
        oldVal = getattr(self.instrument, getName)()
        if oldVal != newVal:  # Here is a dirty trick to avoid setting again the same value because of the valueChanged event. This is the price to pay for using a QSpinBox as an output and an automatic input when the value changes
            self.instrument.dispatch(setName, newVal)
            self.requestSetup()
        self.setTextColor(widget, 'black')

    def requestSetSetup(self):
        for spinBoxName, setName in zip(self.spinBoxNames, self.setNames):
            spinBox = getattr(self, spinBoxName)
            if spinBox.palette().text().color() == QColor('red'):
                self.instrument.dispatch(setName, spinBox.value())
        self.requestSetup()

    def setTextColor(self, mySpinBox, color):
        pal = mySpinBox.palette()
        pal.setColor(pal.Text, QColor(color))
        mySpinBox.setPalette(pal)

    # Request a trace from the instrument.
    def requestAcquireM(self):
        self.requestAcquire(fromMemory=True)

    def requestAcquire(self, fromMemory=False):
        waitFullSweep = (not fromMemory) and bool(
            self.waitFullSweepButton.isChecked())
        self.instrument.dispatch(
            'getFreqMagPhase', waitFullSweep=waitFullSweep, fromMemory=fromMemory)

    def makeReference(self, i):
        if i is None:
            self._reference = None
        else:
            self._reference = self._traces[i]
        self.plotTraces()

    def sendToDataManager(self, i):
        """Sends trace i to datamanager. """
        self._traces[i].toDataManager()

    # Deletes a given trace.
    def deleteTrace(self, i):
        self._traces.pop(i)
        self.plotTraces()
        self.updateTraceList()

    # Save the plot with all the traces to a file (PDF, PNG, EPS, ...)
    def savePlot(self):
        plot = self.tabs.currentWidget()
        if plot.axes.get_visible() == False:
            return
        if self._workingDirectory != '':
            self.fileDialog.setDirectory(self._workingDirectory)
        self.fileDialog.setAcceptMode(1)
        self.fileDialog.setNameFilter("Image files (*.png *.eps *.jpg)")
        self.fileDialog.setDefaultSuffix('eps')
        filename = str(self.fileDialog.getSaveFileName())
        if len(filename) > 0:
            self._workingDirectory = str(self.fileDialog.directory().dirName())
            plot.figure.savefig(filename)

    def setVisibility(self, i, state):
        self._traces[i].parameters()["visible"] = state
        self.plotTraces()

    def visibility(self, i):
        if not "visible" in self._traces[i].parameters():
            self._traces[i].parameters()["visible"] = True
        return bool(self._traces[i].parameters()["visible"])

    def toggleVisibility(self, i):
        self.setVisibility(i, not self.visibility(i))

    def setCorrectivity(self, i, state):
        self.debugPrint('in setCorrectivity with i=', i, ' and state=', state)
        self._traces[i].parameters()["corrected"] = state
        self.plotTraces()

    def correctivity(self, i):
        if not "corrected" in self._traces[i].parameters():
            self._traces[i].parameters()["corrected"] = False
        return bool(self._traces[i].parameters()["corrected"])

    # Updates the properties of a trace according to the values the user
    # entered in the table.
    def updateTraceProperties(self, i, j):
        return
        if j == 0:
                    # We change the name of the trace...
            print "Updating name..."
            self._traces[i].setName(
                str(self.traces.item(i, j).text().toAscii()))
            self.plotTraces()
        if j == 1:
            # We change the name of the trace...
            print "Updating description..."
            self._traces[i].setDescription(
                str(self.traces.item(i, j).text().toAscii()))
            self.plotTraces()

    # Deletes all traces that have been taken so far.
    def clearTraces(self):
        self._traces = []
        self.plotTraces()
        self.updateTraceList()
        self.correcWidget.setVisible(False)

    # Write a given trace to a file.
    def writeTrace(self, filename, trace):
        """Save the datacube trace as a text file."""
        trace.savetxt(filename)

    # Saves all the traces to a directory chosen by the user. The individual traces will be named according to the filenames in the first column of the table.
    # The first column of each data file will contain the description entered
    # by the user in the second column of the table.
    def saveTraces(self):
        self.fileDialog.setAcceptMode(1)
        if self._workingDirectory != '':
            self.fileDialog.setDirectory(self._workingDirectory)
        valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        dirname = str(self.fileDialog.getExistingDirectory())
        if len(dirname) > 0:
            self._workingDirectory = dirname
            for x in range(0, len(self._traces)):
                trace = self._traces[x]
                sanitized_filename = ''.join(
                    c for c in trace.name() if c in valid_chars)
                print "Storing trace 1 in file %s" % sanitized_filename
                self.writeTrace(
                    dirname + '/' + sanitized_filename + '.dat', trace)

    # Saves one single trace to a file.
    def saveTrace(self, x):
        if self._workingDirectory != '':
            self.fileDialog.setDirectory(self._workingDirectory)
        self.fileDialog.setAcceptMode(1)
        filename = str(self.fileDialog.getSaveFileName())
        if len(filename) > 0:
            self._workingDirectory = self.fileDialog.directory().dirName()
            self.writeTrace(filename, self._traces[x])

    def hideAll(self):
        for i in range(0, len(self._traces)):
            self.setVisibility(i, False)

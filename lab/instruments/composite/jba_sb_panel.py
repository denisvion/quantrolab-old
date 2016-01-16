import sys

from application.lib.instrum_classes import *
import string

import re
import struct

import os
import os.path

from numpy import *
from numpy.random import *

___mixture_Available___ = False
try:
    from sklearn import mixture     # clustering library sklearn
except:
    pass
    ___mixture_Available___ = True

from application.ide.mpl.canvas import MatplotlibCanvas as Canvas
from application.lib.instrum_panel import FrontPanel


class Panel(FrontPanel):

    """
    The JBA frontpanel.
    """

    def __init__(self, instrument, parent=None):
        print "loading JBA FrontPanel"
        FrontPanel.__init__(self, instrument, parent)

        # GUI elements

        self.iq = Canvas(width=8, height=5)
        self.iqR = Canvas(width=8, height=5)
        self.iqP = Canvas(width=8, height=5)
        self.variance = Canvas(width=8, height=5)

        self.statusLabel = QLabel("")
        self.updateButton = QPushButton("Update data")
        self.adjustIQButton = QPushButton("Rotate shift IQ")
        self.measureSCurveButton = QPushButton("Measure S")
        self.levelEdit = QLineEdit("0.1")
        self.accuracyEdit = QLineEdit("0.02")
        self.setLevelButton = QPushButton("Set Level")
        self.StopButton = QPushButton("Stop")
        self.squareIQ = QCheckBox("Square IQ plots")

        self.frequencyEdit = QLineEdit("10")
        self.setFrequencyButton = QPushButton("Set")
        self.amplitudeEdit = QLineEdit("2")
        self.setAmplitudeButton = QPushButton("Set")

        # Layout

        self.histograms = Canvas(width=8, height=5)
        self.sCurve = Canvas(width=8, height=5)
        self.goto = Canvas(width=8, height=5)
        self.gotoValuesx = []
        self.gotoValuesy = []

        self.tabs = QTabWidget()
        self.tabs.addTab(self.iq, "IQ data")
        self.tabs.addTab(self.iqR, "IQR data")
        self.tabs.addTab(self.iqP, "IQ data vs power")
        self.tabs.addTab(self.histograms, "Histograms")
        self.tabs.addTab(self.variance, "Variance")
        self.tabs.addTab(self.sCurve, "S Curve")
        self.tabs.addTab(self.goto, "Goto")

        self.layout = QGridLayout()
        self.layout.addWidget(self.tabs, 1, 1)
        self.layout.addWidget(self.statusLabel, 2, 1)

        buttonsLayout1 = QBoxLayout(QBoxLayout.LeftToRight)
        buttonsLayout2 = QBoxLayout(QBoxLayout.LeftToRight)
        frequencyLayout = QBoxLayout(QBoxLayout.LeftToRight)
        amplitudeLayout = QBoxLayout(QBoxLayout.LeftToRight)

        buttonsLayout1.addWidget(self.adjustIQButton)
        buttonsLayout1.addWidget(self.updateButton)
        buttonsLayout1.addWidget(self.measureSCurveButton)
        buttonsLayout1.addWidget(self.StopButton)
        buttonsLayout1.addWidget(self.squareIQ)
        buttonsLayout1.addStretch()
        buttonsLayout2.addWidget(QLabel("p:"))
        buttonsLayout2.addWidget(self.levelEdit)
        buttonsLayout2.addWidget(QLabel("acc.:"))
        buttonsLayout2.addWidget(self.accuracyEdit)
        buttonsLayout2.addWidget(self.setLevelButton)
        buttonsLayout2.addStretch()
        frequencyLayout.addWidget(QLabel("Frequency :"))
        frequencyLayout.addWidget(self.frequencyEdit)
        frequencyLayout.addWidget(self.setFrequencyButton)
        frequencyLayout.addStretch()

        self.menu = QComboBox()
        self.menu.addItem("variable Attenuator")
        self.menu.addItem("envelope Amplitude")
        self.menu.addItem("microwave Amplitude")
        amplitudeLayout.addWidget(self.menu)

        amplitudeLayout.addWidget(QLabel("Amplitude :"))
        amplitudeLayout.addWidget(self.amplitudeEdit)
        amplitudeLayout.addWidget(self.setAmplitudeButton)
        amplitudeLayout.addStretch()

        rotationLayout = QBoxLayout(QBoxLayout.LeftToRight)
        self.I0Edit = QLineEdit("0.0")
        rotationLayout.addWidget(QLabel("I0 :"))
        rotationLayout.addWidget(self.I0Edit)
        rotationLayout.addWidget(QLabel("Q0 :"))
        self.Q0Edit = QLineEdit("0.0")
        rotationLayout.addWidget(self.Q0Edit)
        rotationLayout.addWidget(QLabel("angle :"))
        self.angleEdit = QLineEdit("0.0")
        rotationLayout.addWidget(self.angleEdit)
        self.setRotationButton = QPushButton("Set")
        rotationLayout.addWidget(self.setRotationButton)

        calibrationLayout = QBoxLayout(QBoxLayout.LeftToRight)
        self.vStartEdit = QLineEdit("0.0")
        calibrationLayout.addWidget(QLabel("v Start :"))
        calibrationLayout.addWidget(self.vStartEdit)
        self.vStopEdit = QLineEdit("5.0")
        calibrationLayout.addWidget(QLabel("v Stop :"))
        calibrationLayout.addWidget(self.vStopEdit)
        self.numberOfVEdit = QLineEdit("100")
        calibrationLayout.addWidget(QLabel("Step :"))
        calibrationLayout.addWidget(self.numberOfVEdit)
        self.calibrateButton = QPushButton("Calibrate")
        calibrationLayout.addWidget(self.calibrateButton)

        startStopLayout = QBoxLayout(QBoxLayout.LeftToRight)
        self.startButton = QPushButton("Start JBA")
        startStopLayout.addWidget(self.startButton)
        self.stopButton = QPushButton("Stop JBA")
        startStopLayout.addWidget(self.stopButton)

        self.layout.addLayout(buttonsLayout1, 3, 1)
        self.layout.addLayout(amplitudeLayout, 4, 1)
        self.layout.addLayout(buttonsLayout2, 5, 1)
        self.layout.addLayout(frequencyLayout, 6, 1)
        self.layout.addLayout(rotationLayout, 7, 1)
        self.layout.addLayout(calibrationLayout, 8, 1)
        self.layout.addLayout(startStopLayout, 9, 1)

        self.qw.setLayout(self.layout)
        self.enableButtons()
        # self.calibrateButton.setEnabled(True)
        # self.StopButton.setEnabled(False)

        # Signal connections:

        self.connect(self.calibrateButton, SIGNAL("clicked()"), self.calibrate)
        self.connect(self.measureSCurveButton,
                     SIGNAL("clicked()"), self.measureS)
        self.connect(self.updateButton, SIGNAL("clicked()"), self.updateGraphs)
        self.connect(self.adjustIQButton, SIGNAL("clicked()"), self.adjustIQ)
        self.connect(self.setLevelButton, SIGNAL(
            "clicked()"), self.adjustSwitchingLevel)
        self.connect(self.StopButton, SIGNAL("clicked()"), self.stop)
        self.connect(self.levelEdit, SIGNAL(
            "returnPressed()"), self.adjustSwitchingLevel)
        self.connect(self.accuracyEdit, SIGNAL(
            "returnPressed()"), self.adjustSwitchingLevel)
        self.connect(self.setAmplitudeButton, SIGNAL(
            "clicked()"), self.setAmplitude)
        self.connect(self.setRotationButton, SIGNAL(
            "clicked()"), self.setRotation)
        self.connect(self.setFrequencyButton, SIGNAL(
            "clicked()"), self.setFrequency)

        self.connect(self.startButton, SIGNAL("clicked()"), self.startJBA)
        self.connect(self.stopButton, SIGNAL("clicked()"), self.stopJBA)

    def setFrequency(self):
        self.instrument.dispatch(
            "setFrequency", float(self.frequencyEdit.text()))
        self.instrument.dispatch("sendWaveform")

    def disableButtons(self):
        self.calibrateButton.setEnabled(False)
        self.measureSCurveButton.setEnabled(False)
        self.adjustIQButton.setEnabled(False)
        self.updateButton.setEnabled(False)
        self.setLevelButton.setEnabled(False)
#    self.StopButton.setEnabled(True)

    def enableButtons(self):
        #    self.StopButton.setEnabled(False)
        self.calibrateButton.setEnabled(True)
        self.measureSCurveButton.setEnabled(True)
        self.adjustIQButton.setEnabled(True)
        self.updateButton.setEnabled(True)
        self.setLevelButton.setEnabled(True)

    def stop(self):
        self.updateStatus("Stopping ...")
        self.instrument.terminate()
        self.enableButtons()
        self.updateStatus("")

    def adjustSwitchingLevel(self):
        self.disableButtons()
        lastTab = self.tabs.currentIndex()
        self.tabs.setCurrentWidget(self.goto)
        self.updateStatus("Adjusting switching level to %g %% with %g %% accuracy" % (
            float(self.levelEdit.text()) * 100, float(self.accuracyEdit.text()) * 100))
        args = {'level': float(self.levelEdit.text()),
                'accuracy': float(self.accuracyEdit.text())}
        self.instrument.dispatch("adjustSwitchingLevel", **args)
        # self.tabs.setCurrentIndex(lastTab)
        self.enableButtons()

    def setAmplitude(self):
        if self.menu.currentIndex() == 0:
            magnitudeButton = "variableAttenuator"
        elif self.menu.currentIndex() == 1:
            magnitudeButton = "formAmplitude"
        elif self.menu.currentIndex() == 2:
            magnitudeButton = "microwaveSource"
        else:
            print "INTERNAL ERROR"
        self.instrument.dispatch("setAmplitude", float(
            self.amplitudeEdit.text()), magnitudeButton)
        self.instrument.dispatch("sendWaveform")

    def setRotation(self):
        self.instrument.dispatch("_setRotationAndOffset", float(
            self.I0Edit.text()), float(self.Q0Edit.text()), float(self.angleEdit.text()))

    def measureS(self):
        self.disableButtons()
        print "Measuring s curve"
        lastTab = self.tabs.currentIndex()
        self.tabs.setCurrentWidget(self.sCurve)
        self.instrument.dispatch("measureSCurve")
        # self.tabs.setCurrentIndex(lastTab)
        self.enableButtons()

    def adjustIQ(self):
        self.disableButtons()
        lastTab = self.tabs.currentIndex()
        self.tabs.setCurrentWidget(self.iq)
        # self.instrument.dispatch("adjustRotationAndOffset",float(self.levelEdit.text()))
        self.instrument.dispatch("_adjustRotationAndOffset")
        # self.tabs.setCurrentIndex(lastTab)
        self.enableButtons()

    def calibrate(self):
        self.disableButtons()
        lastTab = self.tabs.currentIndex()
        self.tabs.setCurrentWidget(self.iqP)
        self.instrument.dispatch("calibrate", bounds=[float(self.vStartEdit.text()), float(self.vStopEdit.text()), float(
            self.numberOfVEdit.text())], level=float(self.levelEdit.text()), accuracy=float(self.accuracyEdit.text()))
        # self.calibrateButton.setEnabled(False)
        # self.calibrateStopButton.setEnabled(True)
        # self.tabs.setCurrentIndex(lastTab)
        self.enableButtons()

    def updateStatus(self, message):
        self.statusLabel.setText(message)

    def updateGraphs(self):
        # self.disableButtons()
        #(p,o1,trends) = self.instrument.getThisMeasure(10)

        (components, results, rotatedComponents, clicks,
         probasInDict) = self.instrument.measure()
        components = components[self.instrument.bit]
        rotatedComponents = rotatedComponents[self.instrument.bit]
        print results
        results = results['b%i' % self.instrument.bit]

        self.histograms.axes.cla()
        range = max(abs(min(rotatedComponents[0])), abs(
            max(rotatedComponents[0])))
        self.histograms.axes.hist(
            rotatedComponents[0], normed=True, bins=40, range=(-range, range))
        self.histograms.axes.axvline(0, ls=":")
#    self.histograms.axes.hist(trends[1],normed = True,bins = 30)
        self.histograms.draw()
        self.iq.axes.cla()
        self.iq.axes.plot(components[0], components[1], 'o', markersize=2)
        self.iq.axes.axvline(0, ls=":")
        self.iq.axes.axhline(0, ls=":")
        self.iqR.axes.cla()
        self.iqR.axes.plot(rotatedComponents[0], rotatedComponents[
                           1], 'o', markersize=2)
        self.iqR.axes.axvline(0, ls=":")
        self.iqR.axes.axhline(0, ls=":")
        self.updateStatus("Switching probability: %g percent" %
                          (results * 100.0))
        self.iq.draw()
        self.iqR.draw()
        self.enableButtons()

    def updatedGui(self, subject, property, value):
        if subject == self.instrument:
            if property == "calibrate":
                self.calibrateButton.setEnabled(True)
                # self.StopButton.setEnabled(False)
#        self.iq.axes.cla()
#        self.iq.axes.scatter(iqdata[0,:],iqdata[1,:])
#        self.iq.draw()
#        self.variance.axes.cla()
#        self.variance.axes.set_xlabel("Yoko voltage [V]")
#        self.variance.axes.set_ylabel("$\sigma_I^2$+$\sigma_Q^2$")
#        self.variance.axes.plot(vs,ps,vs2,ps2)
#        self.variance.draw()
            elif property == 'variance':
                if value == 0:
                    self.variance.axes.cla()
                else:
                    self.variance.axes.set_xlabel("magnitude [V]")
                    self.variance.axes.set_ylabel("$\sigma_I^2$+$\sigma_Q^2$")
                    (vs, ps, color) = value
                    self.variance.axes.plot(vs, ps, color=color)
                self.variance.draw()
            elif property == 'sCurve':
                self.sCurve.axes.cla()
                self.sCurve.axes.plot(value[0], value[1])
                self.sCurve.draw()
            elif property == "iqdata":
                self.iq.axes.cla()
                self.iq.axes.scatter(value[0][0], value[0][1])
                self.iq.draw()
                self.iqR.axes.cla()
                self.iqR.axes.scatter(value[1][0], value[1][1])
                self.iqR.draw()
            elif property == "status":
                self.updateStatus(value)
            elif property == "iqP":
                if value == 0:
                    self.iqP.axes.cla()
                    self.iqP.squared = True
                    self.iqP.centered = False
                    self.iqP.draw()
                else:
                    (x, y, color) = value
                    self.iqP.axes.plot(x, y, 'o', markersize=3, color=color)
                    self.iqP.redraw()
            elif property == "iqPaxes":
                (i0, q0, angle) = value
                self.iqP.axes.plot([i0 - cos(angle), i0 + cos(angle)], [q0 -
                                                                        sin(angle), q0 + sin(angle)], linewidth=2, color=((0, 0, 0)))
                self.iqP.draw()
                self.iq.axes.plot([i0 - cos(angle), i0 + cos(angle)], [q0 -
                                                                       sin(angle), q0 + sin(angle)], linewidth=2, color=((0, 0, 0)))
                self.iq.draw()
            elif property == "histograms":
                self.histograms.axes.cla()
                range = max(abs(min(value)), abs(max(value)))
                self.histograms.axes.hist(
                    value, normed=True, bins=50, range=(-range, range))
                self.histograms.axes.axvline(0, ls=":")
                self.histograms.draw()
            elif property == "goto":
                (command, value) = value
                self.goto.axes.cla()
                if command == "clear":
                    self.gotoValuesx = []
                    self.gotoValuesy = []
                if command == "singlePoint":
                    self.gotoValuesx.append(value[0])
                    self.gotoValuesy.append(value[1])
                    self.goto.axes.scatter(self.gotoValuesx, self.gotoValuesy)
                if command == "fit":
                    f = value
                    p = linspace(0.01, 0.99, 99)
                    v = map(f, p)
                    self.goto.axes.plot(v, p)
                    self.goto.axes.scatter(self.gotoValuesx, self.gotoValuesy)
                self.goto.axes.set_ybound(0, 1)
                self.goto.draw()
            elif property == "status":
                self.updateStatus(value)
            elif property == "centersIQ":
                print "plotting centers"
                sepCenters = value[0]
                centers = value[1]
                self.iqP.axes.plot(sepCenters[0], sepCenters[
                                   1], 'o', markersize=10, color=(1, 1, 0))

                self.iqP.axes.plot(centers[0], centers[
                                   1], 'o', markersize=10, color=(0, 1, 1))
                # self.iqP.axes.plot(c2[0],c2[1],'o',markersize=10,color=(0,1,1))
                self.iqP.draw()

    def startJBA(self):
        self.instrument.dispatch("startJBA")
        self.instrument.dispatch("sendWaveform")
        self.calibrateButton.setEnabled(True)
        self.measureSCurveButton.setEnabled(True)
        self.updateButton.setEnabled(True)
        self.adjustIQButton.setEnabled(True)
        self.setLevelButton.setEnabled(True)
        self.StopButton.setEnabled(True)
        self.levelEdit.setEnabled(True)
        self.accuracyEdit.setEnabled(True)
        self.setAmplitudeButton.setEnabled(True)
        self.setRotationButton.setEnabled(True)
        self.setFrequencyButton.setEnabled(True)
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)

    def stopJBA(self):
        self.instrument.dispatch("stopJBA")
        self.instrument.dispatch("sendWaveform")
        self.calibrateButton.setEnabled(False)
        self.measureSCurveButton.setEnabled(False)
#    self.updateButton.setEnabled(False)
        self.adjustIQButton.setEnabled(False)
        self.setLevelButton.setEnabled(False)
        self.StopButton.setEnabled(False)
        self.levelEdit.setEnabled(False)
        self.accuracyEdit.setEnabled(False)
        self.setAmplitudeButton.setEnabled(False)
        self.setRotationButton.setEnabled(False)
        self.setFrequencyButton.setEnabled(False)
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)

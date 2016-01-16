#*************************************************************************
# 2D and 3D Plotter                                                            *
#*************************************************************************


def flatten(li):
    result = []
    for el in li:
        if hasattr(el, "__iter__"):
            result.extend(flatten(el))
        else:
            result.append(el)
    return result

#**************************************
# Imports
#**************************************

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.uic import *

import sys
import getopt
import os
import os.path
import weakref
import gc
import time
import warnings
import numpy
from itertools import groupby

from matplotlib import colors, cm  # Matplotlib
from mpl_toolkits.mplot3d import Axes3D

from application.ide.mpl.canvas import *                            # Canvas
reload(sys.modules['application.ide.mpl.canvas'])
from application.ide.mpl.canvas import *

from application.lib.datacube import *                              # Datacube
from application.lib.base_classes1 import Debugger                  # Debugger
from application.ide.widgets.observerwidget import ObserverWidget   # ObserveWidget
from application.helpers.userPromptDialogs import *

#********************************************
#  utility classes
#********************************************


class cube2DPlot:

    def __init__(self):
        pass


class cube3DPlot:
    """
    Class for a 3D plot with properties:
        - cube : the cube providing the data
        - data: the data to be used by matplotlib for plotting
        - xname, yname, zname : the names of the x,y,z data
        - legend: the legend of the plot to optionally display in the canvas
        - style: the type of matplotlib plot
        - color: the color scheme for the plot
        - MPLplot: the object build by the matplotlib plotting function
        - item: ???
    """

    def __init__(self):
        pass

#********************************************
#  PlotWidget classes
#********************************************

# Global variables
__styles2D__ = ['line', 'scatter', 'line+symbol']
# list of available styles for curves in a 2d graph
__defaultStyle2D__ = 0
__styles3D__ = ['Image(2D)', 'Contours(2-3D)', 'Filled contours(2-3D)',
                'Waterfall(3D)', 'Scatter(3D)', 'Line(3D)', 'Surface(3D)', 'Tri-surface(3D)']
__defaultStyle3D__ = 0      # list of available styles for curves in a 3d graph
# list of 3D styles that can be shown only on the x,y,z 3D frame of a
# matplotlib Axes3D
__styles3DAxes3DOnly__ = [
    'Waterfall(3D)', 'Scatter(3D)', 'Surface(3D)', 'Tri-surface(3D)', 'Line(3D)']
# list of 3D styles that can be shown only in the xy plane of a matplotlib Axes
__styles3DAxes2DOnly__ = ['Image(2D)']
# list of 3D styles that will be encoded as 1D x, y, and z lists
__styles3DEncode111__ = ['Scatter(3D)', 'Line(3D)', 'Tri-surface(3D)']
# list of 3D styles that will be encoded with x, y and z dimensions 2,1,2
# or 1,2,2
__styles3DEncodexx2__ = [
    'Image(2D)', 'Contours(2-3D)', 'Filled contours(2-3D)', 'Waterfall(3D)']
__styles3DEncode222__ = ['Surface(3D)']
# list of 3D styles that can be shown only on a rectangular x,y grid
__styles3DRectangularOnly__ = [
    'Image(2D)', 'Contours(2-3D)', 'Filled contours(2-3D)', 'Surface(3D)']
# list of 3D styles that can be shown only on a regular x,y grid (i.,e.
# equally spaced along x and y)
__styles3DRegularOnly__ = ['Image(2D)']
__colors3D__ = ['binary', 'gray', 'jet', 'hsv', 'autumn', 'cool']
# list of matplotlib color schemes
__defaultColor3D__ = 2
__regridize__ = ['None', 'skip', 'interpolate']
# list of methods to regularize unregular data (not programmed yet)
__defaultRegridize__ = 0


class PlotWidget(QWidget, ObserverWidget, Debugger):

    """
    Generic private widget class for plotting data from datacubes.
    Use subclasses PlotWidget2D and PlotWidget3D instead
    """

    def __del__(self):
        self.debugPrint("deleting ", self)

    def __init__(self, parent=None, dataManager=None, name=None, threeD=False):  # creator PlotWidget
        Debugger.__init__(self)
        self.debugPrint("in PlotWidget.__init__(parent,name,threeD) with parent=",
                        parent, " name=", name, " and threeD=", threeD)
        QWidget.__init__(self, parent)
        ObserverWidget.__init__(self)
        self.parent = parent
        self.name = name
        # never change this value after instance creation
        self._threeD = threeD
        self._cube = None
        self._showLegend = False
        self._plots = []
        self._updated = False
        self._currentIndex = None
        self.legends = []
        self.cubes = []
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.connect(self.timer, SIGNAL("timeout()"), self.onTimer)

        # attach  dataManager to this Plot2DWidget, i.e. Plot2DWidget receives
        # message from datamanager
        self._dataManager = dataManager
        self.debugPrint('attaching ', self._dataManager, ' to ', self)
        self._dataManager.attach(self)

        # definition of the Canvas
        self.canvas = MyMplCanvas(
            dpi=72, width=8, height=8, name=name, threeD=threeD)

        # Definition of top sub-layout ctrlLayout0
        ctrlLayout0 = QBoxLayout(QBoxLayout.LeftToRight)
        # Define controls,
        if not threeD:
            self.level = QSpinBox()
        self.xNames, self.yNames = QComboBox(), QComboBox()
        variableNames = [self.xNames, self.yNames]
        comboBoxes = variableNames
        if threeD:
            self.zNames = QComboBox()
            variableNames.append(self.zNames)
            self.regularGrid = QRadioButton('regular grid')
            self.regularGrid.setChecked(False)
            self.regularGrid.setEnabled(True)
            self.regridize = QComboBox()
            for method in __regridize__:
                self.regridize.addItem(method)
            self.regridize.setCurrentIndex(__defaultRegridize__)
            comboBoxes = variableNames
            comboBoxes.append(self.regridize)
        for combo in comboBoxes:
            combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        # then add controls to sublayout,
        if not threeD:
            widgets = [QLabel("Level:"), self.level, QLabel(
                "X:"), self.xNames, QLabel("Y:"), self.yNames]
            # widgets=[QLabel("Level:"),self.level,QLabel("X:"),self.xNames,QLabel("Y:"),self.yNames,self.addButton,self.autoplot,self.autoclear]
        else:
            widgets = [QLabel("X:"), self.xNames, QLabel("Y:"), self.yNames, QLabel(
                "Z:"), self.zNames, self.regularGrid, QLabel("regularize:"), self.regridize]
            # widgets=[QLabel("X:"),self.xNames,QLabel("Y:"),self.yNames,QLabel("Z:"),self.zNames,self.regularGrid,QLabel("regularize:"),self.regridize,self.addButton,self.autoplot,self.autoclear]
        for widget in widgets:
            ctrlLayout0.addWidget(widget)
        ctrlLayout0.addStretch()
        # and make connections between signals and slots.
        for variableName in variableNames:
            self.connect(variableName, SIGNAL(
                "currentIndexChanged (int)"), self.namesChanged)
        selectors = [self.xNames, self.yNames]
        if threeD:
            selectors.append(self.zNames)
        else:
            self.connect(self.level, SIGNAL(
                "valueChanged(int)"), self.levelChanged)
        # Definition of bottom-left layout ctrlLayout1
        ctrlLayout11 = QGridLayout()
        # define controls
        if threeD:
            label = 'Add plot'
        else:
            label = 'Add plot(s)'
        self.addButton = QPushButton(label)
        self.autoplot = QCheckBox("AutoPlot")
        self.styles = QComboBox()
        # self.styles.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Maximum)
        if not threeD:
            styles = __styles2D__
            default = __defaultStyle2D__
        else:
            styles = __styles3D__
            default = __defaultStyle3D__
        for style in styles:
            self.styles.addItem(style)
        self.styles.setCurrentIndex(default)
        self.colors = QComboBox()
        # self.colors.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Maximum)
        if not threeD:
            color_cycle = self.canvas.axes._get_lines.color_cycle
            colors = []
            for i, color in enumerate(color_cycle):
                if i == 0 or color != colors[0]:
                    colors.append(color)
                else:
                    break
            default = 0
        else:
            colors = __colors3D__
            default = __defaultColor3D__
        for color in colors:
            self.colors.addItem(color)
        self.colors.setCurrentIndex(default)
        self.showLegend = QCheckBox("Legend")
        self.showLegend.setCheckState(Qt.Checked)
        self.clearButton = QPushButton("Clear all")
        self.autoclear = QCheckBox("AutoClear")
        # then add controls to sublayout,
        ctrlLayout11.addWidget(self.addButton, 0, 0)
        ctrlLayout11.addWidget(self.autoplot, 0, 1)
        ctrlLayout11.addWidget(self.clearButton, 1, 0)
        ctrlLayout11.addWidget(self.autoclear, 1, 1)
        ctrlLayout11.addWidget(self.styles, 2, 0)
        ctrlLayout11.addWidget(self.showLegend, 3, 1)
        ctrlLayout11.addWidget(self.colors, 3, 0)

        #widgets=[QLabel('Default style:'),self.styles,QLabel('Default colors:'),self.colors,self.showLegend,self.clearButton]
        #for widget in widgets:    ctrlLayout1.addWidget(widget)
        ctrlLayout1 = QBoxLayout(QBoxLayout.TopToBottom)
        ctrlLayout1.addLayout(ctrlLayout11)
        ctrlLayout1.addStretch()
        # and make connections between signals and slots.
        self.connect(self.autoplot, SIGNAL(
            "stateChanged(int)"), self.autoplotChanged)
        addPlot = lambda: self.addPlot(
            names=[str(name.currentText()) for name in selectors])
        self.connect(self.addButton, SIGNAL("clicked()"), addPlot)
        self.connect(self.showLegend, SIGNAL(
            "stateChanged(int)"), self.showLegendStateChanged)
        self.connect(self.clearButton, SIGNAL("clicked()"), self.clearPlots)

        # Definition of bottom-right plotList QTreeWidget
        self.plotList = pl = QTreeWidget()
        if not threeD:
            headers = ("Datacube", "X variable",
                       "Y variable", "style", "colors")
        else:
            headers = ("Datacube", "X variable", "Y variable",
                       "Z variable", "style", "colors")
        pl.setColumnCount(len(headers))
        pl.setMinimumHeight(30)
        pl.setHeaderLabels(headers)

        def menuContextPlotlist(point):
            item = self.plotList.itemAt(point)
            if item:
                name = item.text(0)
                colorModel = None
                styleIndex = 3  # 2D
                colorIndex = 4
                if self._threeD:  # 3D
                    styleIndex = 4
                    colorIndex = 5
                styleItem = str(item.text(styleIndex))
                colorItem = str(item.text(colorIndex))
                menu = QMenu(self)
                actionRemove = menu.addAction("Remove")
                menu.addSeparator()
                actionRemove.triggered.connect(
                    lambda: self.removeLine(update=True))

                def makeFunc(style):
                    return lambda: self.setStyle(style=style)
                for style in styles:
                    action = menu.addAction(style)
                    if style == styleItem:
                        action.setCheckable(True)
                        action.setChecked(True)
                        action.setEnabled(False)
                    action.triggered.connect(makeFunc(style))
                menu.addSeparator()

                def makeFunc2(color):
                    return lambda: self.setColor(color=color)
                for color in colors:
                    action = menu.addAction(color)
                    if color == colorItem:
                        action.setCheckable(True)
                        action.setChecked(True)
                        action.setEnabled(False)
                    action.triggered.connect(makeFunc2(color))
                menu.exec_(self.plotList.mapToGlobal(point))
        pl.setContextMenuPolicy(Qt.CustomContextMenu)
        self.connect(pl, SIGNAL(
            "customContextMenuRequested(const QPoint &)"), menuContextPlotlist)

        # Full Layout
        ctrlLayout = QGridLayout()          # create a layout for
        ctrlLayout.addLayout(ctrlLayout0, 0, 0, 1, 2)   # the controls above
        # the line properties on the left
        ctrlLayout.addItem(ctrlLayout1, 1, 0)
        # and the list of plots on the right
        ctrlLayout.addWidget(self.plotList, 1, 1)
        splitter = QSplitter(Qt.Vertical)   # vertica splitter with
        splitter.addWidget(self.canvas)     # the canvas
        # the propLayout with the controlWidget, the line properites and the
        # plot list
        self.ctrlWidget = QWidget()
        self.ctrlWidget.setLayout(ctrlLayout)
        splitter.addWidget(self.ctrlWidget)
        layout = QGridLayout()              # overall layout
        layout.addWidget(splitter)          # takes the vertical splitter
        self.setLayout(layout)

        self.timer.start()

    def onTimer(self):
        if self._updated == True:
            return
        self.debugPrint(self.name, '.onTimer() calling updatePlot()')
        self._updated = True
        self.updatePlot(draw=True)

    # subclass in Plot2DWidget and Plot3DWidget
    def updatedGui(self, **kwargs):
        return

    # subclass in Plot2DWidget and Plot3DWidget
    def addPlot(self):
        return

    def removeFromCanvas(self, plot):
        self.debugPrint('in removeFromCanvas with plot =', plot)
        cv = self.canvas
        fig = cv._fig
        if not self._threeD:
            plot.MPLplot.remove()
            del plot.MPLplot
        else:
            try:
                plot.MPLplot.remove()                       # remove graphical object from canvas
            except:
                # graphical object has no remove attribute and canvas has to be
                # reconstructed from scratch
                self.updatePlot(clearFirst=True, draw=True)
            del plot.MPLplot                                # and delete from memory
            if len(self._plots) == 0 and len(fig.axes) >= 2:    # if no other plots
                # del colorbar axes = axes(1)
                fig.delaxes(fig.axes[1])
                # restore initial size here
                fig.axes[0].set_position(fig.axes[0].initialPosition)

    def clearPlots(self):  # simplify here by calling removeplot
        """
        Clears all the plots from the graph and from self._plotList.
        """
        self.debugPrint("in PlotWidget.clearPlots()")
        pl = self.plotList
        while pl.topLevelItemCount() != 0:
            pl.setCurrentItem(pl.topLevelItem(0))
            self.removeLine(update=False)
        self._updated = False

    def updatePlotLabels(self, draw=False):
        """
        Rebuilt axis labels, title and legend.
        """
        xnames = []
        ynames = []
        legend = []
        legendPlots = []
        filenames = []
        names = []
        for plot in self._plots:
            if not plot.xname in xnames:
                xnames.append(plot.xname)
            if not plot.yname in ynames:
                ynames.append(plot.yname)
            if not plot.cube.name() in names:
                names.append(plot.cube.name())
            if plot.cube.filename() != None and not plot.cube.filename() in filenames:
                legend.append(plot.yname + ":" + plot.cube.filename()[:-4])
                filenames.append(plot.cube.filename())
                if not self._threeD:
                    legendPlots.append(plot.MPLplot)
        xLabel = ", ".join(xnames)
        if len(xLabel) > 30:
            xLabel = xLabel[:27] + '...'
        yLabel = ", ".join(ynames)
        if len(yLabel) > 20:
            xLabel = yLabel[:27] + '...'
        title = ", ".join(names)
        if len(title) > 63:
            title = title[:60] + '...'
        self.canvas.axes.set_xlabel(xLabel)
        self.canvas.axes.set_ylabel(yLabel)
        self.canvas.axes.set_title(title)
        if self._showLegend and len(legend) > 0:
            from matplotlib.font_manager import FontProperties
            self.canvas.axes.legend(
                legendPlots, legend, prop=FontProperties(size=6))
        else:
            self.canvas.axes.legend_ = None
        if draw:
            self.canvas.redraw()

    def updatePlot(self, listOfPlots=None, draw=False, clearFirst=False):
        """
        Rebuilt axis labels, title and legend, then refill the listed plots with their points.
        If no list of plots is given, all plots in self._plots are updated.
        """
        self.debugPrint('in PlotWidget ', self.name,
                        '.updatePlot() with draw = ', draw)
        if clearFirst:
            self.canvas.axes.cla()
        self.updatePlotLabels(draw=False)
        # clear the graph without using clf, which would loose the fixed scales
        # if any.
        if len(self._plots) == 0:
            self.canvas.redraw()
            return
        if listOfPlots is None:
            listOfPlots = self._plots
        if listOfPlots is None or listOfPlots == []:
            return
        for plot in listOfPlots:
            self.updatePlotData(draw=False, plot=plot)
        if draw:
            self.canvas.redraw()

    # subclass in Plot2DWidget and Plot3DWidget
    def updatePlotData(self, **kwargs):
        return

    def setCube(self, cube, names=[None, None, None]):
        """"
        Set the selected datacube as current cube, update variable names in selectors, and call plot if autoplot
        """
        self.debugPrint(
            'in PlotWidget.setCube(cube,names) with cube =', cube, ' names=', names)
        detachPrevious = True
        if self._cube is not None and self._cube in self._dataManager.datacubes():
            # Detach previous cube if not in a plot or if removed from
            # datamanager
            found = False
            for plot in self._plots:
                if self._cube == plot.cube:
                    found = True
                    break
            if found:
                detachPrevious = False
        if self._cube is not None and detachPrevious:
            self.debugPrint('detaching ', self._cube, ' from ', self)
            self._cube.detach(self)
        # defines the new cube as current cube
        self._cube = cube
        if self._cube is not None:
            self.debugPrint("attaching", self._cube, 'to', self)
            # and observes the cube in case it changes names or gets new data
            self._cube.attach(self)
        if not self._threeD:
            # update the 2D variable selectors
            kwargs = {'level': 0, 'names': names[0:2]}
        else:
            # or the 3D variable selectors
            kwargs = {'names': names}
        self.updateControls(**kwargs)
        if self.autoplot.isChecked():
            self.addPlot()       # and plot if autoplot

    # subclass in Plot2DWidget and Plot3DWidget
    def preselectVariables(self):
        return

    # subclass in Plot2DWidget and Plot3DWidget
    def updateControls(self, **kwargs):
        return

    # subclass in Plot2DWidget and Plot3DWidget
    def setStyle(self, **kwargs):
        return

    # subclass in Plot2DWidget and Plot3DWidget
    def setColor(self, **kwargs):
        return

    def removePlot(self, plot, update=True):
        """
        Remove a plot from the graph and from self._plots.
        If index is not specified remove the current index.
        If index does not exist does nothing.
        """
        self.debugPrint("in PlotWidget.removePlot() with plot = ",
                        plot, " and update = ", update)
        if plot:
            self._plots.remove(plot)  # ... as well as from self._plots
            self.removeFromCanvas(plot)       # delete the plot from the canvas
            cube = plot.cube                    # retrieve the cube of the plot to be deleted
            del plot
            # detach the cube if it is not the current cube and if it is not in
            # another plot
            cubes = [plot.cube for plot in self._plots]
            if cube != self._cube and not cube in cubes:
                cube.detach(self)
            #self._currentIndex = None
            if update:
                self._updated = False

    def removeLine(self, update=True):
        self.debugPrint("in PlotWidget.removeLine with update =", update)
        self._currentIndex = self.plotList.indexOfTopLevelItem(
            self.plotList.currentItem())
        plot = self._plots[self._currentIndex]
        # remove the item from plotList
        self.plotList.takeTopLevelItem(self._currentIndex)
        self.removePlot(plot, update=update)

    def lineSelectionChanged(self, selected, previous):
        if selected != None:
            index = self.plotList.indexOfTopLevelItem(selected)
            self._currentIndex = index

    def autoplotChanged(self, CheckState):
        self.debugPrint("in PlotWidget.autoplotChanged()")
        if CheckState:
            self.updatedGui(subject=self._cube, property="names", value=None)

    # subclass in Plot2DWidget only
    def levelChanged(self):
        return

    def namesChanged(self):
        # self.debugPrint("in PlotWidget.namesChanged()")               # not used yet
        #self.updatedGui(subject=self,property = "redraw",value = None)
        return

    def showLegendStateChanged(self, state):
        self.debugPrint("in PlotWidget.showLegendStateChanged()")
        if state == Qt.Checked:
            self._showLegend = True
        else:
            self._showLegend = False
        self._updated = False


class Plot2DWidget(PlotWidget):

    """
    Widget class for plotting 2D datasets (i.e. y(x) curves) from datacubes, using the matplotlib library.
    This widget allows the user to choose a couple of x and y column names at the top level of datacube, or in all its children if they have common column names.
    It manages a list of plots shown on a single graph, with changeable graphical attributes.
    It is registered as an observer of all datacubes containing the plotted data, so that updates are made when necessary.
    Each plot points to the matplotlib object, which can be update directly.
    BUG: the notifications of plot updates at each new point are too precise so that to many redrawing are generated.
    """

    def __init__(self, parent=None, dataManager=None, name=None):  # creator Plot2DWidget
        PlotWidget.__init__(self, parent=parent,
                            dataManager=dataManager, name=name, threeD=False)
        self.colors.setEnabled(False)

    # notification listener of Plot2DWidget
    def updatedGui(self, subject=None, property=None, value=None):
        self.debugPrint('in ', self.name, '.updatedGui with subject=',
                        subject, ', property=', property, ', and value=', value)
        # 1) A new datacube arrived.
        if subject == self._dataManager and property == "addDatacube":
            if self.autoplot.isChecked():
                # if autoplot, addPlot it (or attach if it's empty for delayed
                # addplotting)
                self.addPlot(cube=value)
        # 2) New names of an attached datacube arrived
        elif isinstance(subject, Datacube) and property == "names":
            cube = subject  # the datacube cube is the notifed subject
            if cube == self._cube:
                self.updateControls()  # if current datacube => update controls
            if self.autoplot.isChecked():
                # allows autoplot of a datacube that gets its first columns
                self.addPlot(cube=cube)
        # 3) a datacube attached to this plotter has a new child
        elif isinstance(subject, Datacube) and property == "addChild":
            cube = subject
            child = value  # the datacube and the child are the notified property and value, respectively
            if cube == self._cube:
                self.updateControls()  # if current datacube and levels >0 => update controls
            if self.autoplot.isChecked():
                # if autoplot, addplot the added child (the value)
                self.addPlot(cube=child)
        # 4) a datacube of the datamanger not attached to this plotter
        # (otherwise would be case 3) has new child
        elif subject == self._dataManager and property == "addChild":
            if self.autoplot.isChecked():
                cube = None  # retrieve here the child datacube
                self.addPlot(cube=cube)
        # 5) New points arrived in an attached datacube:
        elif isinstance(subject, Datacube) and property == "commit":
            self.debugPrint("commit catched")
            cube = subject
            for plot in self._plots:  # If attached only as current cube for name update do nothing
                if cube == plot.cube:  # Otherwise update plot
                    self._updated = False
                    break
        # note that addPlot set self._updated to False after completion
        else:
            self.debugPrint("not managed")

    def addPlot(self, cube=None, level=None, names=[None, None], clear='auto', style=None, **kwargs):
        """
        Adds plots of a datacube at level level by calling addPlot2 for all children of that level or for the cube itself if level == 0.
        """
        self.debugPrint('in ', self.name, '.addPlot with cube=', cube, ',level=', level, ', names=',
                        names, ', clear=', clear, ', style=', style, ', and current cube = ', self._cube)
        if level is None:
            level = self.level.value()
        if cube is None:
            cube = self._cube              # if no datacube passed use the current datacube
        if cube is None:
            return                        # give-up if no datacube
        # if datacube has no column,...
        if len(cube.names()) == 0:
            if self.autoplot.isChecked():
                # attach it  if autoplot...
                self.debugPrint('attaching ', cube, ' to ', self)
                # ... so that on next names notification it is autoplotted;
                cube.attach(self)
            return                                    # then give up
        names = self.preselectVariables(
            cube=cube, level=level, names=names)  # Build valid x and y names
        if any([not bool(name) for name in names]):
            return                     # give up if no valid names
        cubes = cube.cubesAtLevel(level=level, allBranchesOnly=True)
        if self.autoclear.isChecked() or clear == True:
            self.clearPlots()
        for cubei in cubes:
            self.addPlot2(cube=cubei, names=names,
                          clear=False, style=style, **kwargs)

    def addPlot2(self, cube=None, names=[None, None], clear='auto', style=None, **kwargs):
        """
        Adds a plot of a datacube in self._plots with specified axes and pre-clearing if requested. In case cube=None, use the current datacube.
        Add the corresponding line in the table below the graph.
        Then calls self.updatePlot() for redrawing.
        Note: in case datacube has no column, no plot is added.
        """
        self.debugPrint('in ', self.name, '.addPlot2 with cube=', cube, ', names=', names,
                        ', clear=', clear, ', style= ', style, ' and current cube = ', self._cube)
        if cube is None:
            cube = self._cube              # if no datacube passed use the current datacube
        if cube is None:
            return                        # give-up if no datacube
        # give up if datacube has no column, but attach it if autoplot
        if len(cube.names()) == 0:
            if self.autoplot.isChecked():
                self.debugPrint('attaching ', cube, ' to ', self)
                # at the next names notification, opportunity to autoplot.
                cube.attach(self)
                return
        if (self.autoclear.isChecked() and clear == 'auto') or clear == True:       # clear if autoclear
            self.clearPlots()
        names = self.preselectVariables(
            cube=cube, names=names)  # Build valid x and y names
        if any([not bool(name) for name in names]):
            return                     # give up if no valid names
        for plot in self._plots:                      # Check if the plot is already present in the list of plots
            if cube == plot.cube:
                if [plot.xname, plot.yname] == names:
                    self._updated = False
                    # and update only and stop if the plot is already present
                    return
        plot = cube2DPlot()                           # Ohterwise build the new cube2DPlot
        plot.xname, plot.yname = names
        plot.cube = cube
        plot.legend = "%s, %s vs. %s" % (cube.name(), plot.xname, plot.yname)
        # The cube2DPlot has a property line that point to its corresponding axes' plot
        # Plotting with axes.plot returns a plot.
        # The strategy here is to first make an empty plot, get it and set the
        # line property to it; Then the plot will be filled with points and
        # redrawn.
        # initialize to empty matplolib plot
        plot.MPLplot = None
        # call the plotting function with all parameters stored in the plot
        # object
        self.updatePlotData(plot=plot, **kwargs)
        if (not style) or self.styles.findText(style) == -1:
            style = self.styles.currentText()
        plot.style = style
        if style == 'scatter':
            plot.MPLplot.set_linestyle('')
            plot.MPLplot.set_marker('o')
        elif style == 'line':
            plot.MPLplot.set_linestyle('-')
            plot.MPLplot.set_marker('')
        else:
            plot.MPLplot.set_linestyle('-')
            plot.MPLplot.set_marker('o')
        # self._cnt+=1
        self.debugPrint('attaching ', plot.cube, ' to ', self)
        plot.cube.attach(self)
        plot.color = color = plot.MPLplot.get_color()
        # Add the plot as a plotitem in the view plotList below the graph
        # window
        plotItem = QTreeWidgetItem(
            [cube.name(), plot.xname, plot.yname, plot.style, color])
        self.writeInColorInQTreeWidget(plotItem, 4, color, color)
        self.plotList.addTopLevelItem(plotItem)
        # self.plotList.setItemWidget(plotItem,4,plot.MPLplotStyleLabel)
        # update the view plotList of self._plot
        self.plotList.update()
        plot.item = plotItem
        # and add the plot to the list self._plots
        self._plots.append(plot)
        # update the graph (will fill with points, create all labels, and
        # redraw)
        self._updated = False

    def updatePlotData(self, plot=None, draw=False, **kwargs):
        """
        Refill the listed plots with their points.
        If no list of plots is given, all plots in self._plots are updated.
        """
        self.debugPrint(
            'in ', self.name, '.updatePlotData() with plot=', plot, ' and draw =', draw)
        if plot is None and self._currentIndex:
            plot = self._plots[self._currentIndex]
        if plot:
            if plot.MPLplot is None:
                # this is where the line plot is created
                plot.MPLplot, = self.canvas.axes.plot([], [], **kwargs)
            if plot.xname != "[row]":
                xvalues = plot.cube.column(plot.xname)
            else:
                xvalues = arange(0, len(plot.cube), 1)
            if plot.yname != "[row]":
                yvalues = plot.cube.column(plot.yname)
            else:
                yvalues = arange(0, len(plot.cube), 1)
            plot.MPLplot.set_xdata(xvalues)
            plot.MPLplot.set_ydata(yvalues)
            # Bug in matplotlib. Have to call "recache" to make sure the plot
            # is correctly updated.
            plot.MPLplot.recache()
        if draw:
            self.canvas.redraw()

    def updateControls(self, level=None, names=[None, None]):
        """
        Updates the level and the x and y names in the x and y selectors. Then makes a pre-selection by calling preselectVariables().
        """
        self.debugPrint("in Plot2DWidget.updateControls(level,names) with level=",
                        level, ", names=", names, ', and current datacube=', self._cube)
        cube = self._cube
        names = names[0:2]
        selectors = [self.xNames, self.yNames]
        # memorize current selection to reuse it if necessary
        previousNames = [str(selector.currentText()) for selector in selectors]
        for selector in selectors:
            selector.clear()    # clear the selectors
        if cube is not None:
            # gets all column names of the datacube and its children that are
            # common to a same level
            commonNames = cube.commonNames()
            self.level.setMaximum(len(commonNames) - 1)
            if level is not None:
                self.level.setValue(level)
            level = self.level.value()
            commonNames = commonNames[level]
            commonNames.insert(0, '[row]')  # Add the 'row number' choice
            for selector in selectors:
                # add all other choices from the current datacube
                selector.addItems(commonNames)
            names = self.preselectVariables(
                cube=cube, level=level, names=names, previousNames=previousNames)
            # select the requested x and y names if correct
            if all([bool(name) for name in names]):
                indices = map(lambda selector, name: selector.findText(
                    name), selectors, names)
                # print indices
                if all([index != -1 for index in indices]):
                    map(lambda selector, index: selector.setCurrentIndex(
                        index), selectors, indices)
        if selectors[0].count() > 0:
            self.addButton.setEnabled(True)
        else:
            self.addButton.setEnabled(False)

    def preselectVariables(self, cube=None, level=0, names=[None, None], previousNames=[None, None]):
        """
        Preselects x and y variables before plotting a datacube.
        """
        self.debugPrint('in Plot2DWidget.preselectVariables(cube,level,names,previousNames) with cube = ',
                        cube, ' level = ', level, ', names = ', names, ', and previousNames = ', previousNames)
        if cube is None:
            cube = self._cube           # if no datacube passed use the current datacube
        if cube is None:
            return [None, None]       # if no datacube give up
        if level is None:
            level = 0                   # prepare a plot at level 0 if no level speciifed
        # gets all column names of the datacube and its children that are
        # common to a same level
        commonNames = cube.commonNames()
        levelMax = len(commonNames) - 1
        if level > levelMax:
            level = levelMax
        commonNames = commonNames[level]
        if len(commonNames) != 0:
            commonNames.insert(0, '[row]')
        # select first the passed names if valid for both x and y
        if any([not bool(name) for name in names]) or any([not (name in commonNames) for name in names]):  # else
            cubes = cube.cubesAtLevel(level=level, allBranchesOnly=True)
            for cubei in cubes:
                # select the first valid default plot if defined in one of the
                # datacubes
                if cubei.parameters().has_key("defaultPlot"):
                    for defaultPlot in cube.parameters()['defaultPlot']:
                        if len(defaultPlot) >= 2:
                            names = defaultPlot[:2]
                        if all([name in commonNames for name in names]):
                            return names
            # else select names of previous plot if possible (except if one of
            # the names is row)
            selectors = [self.xNames, self.yNames]
            if all([bool(name) and name != '[row]' and name in commonNames for name in previousNames]):
                names = previousNames
            # else choose commonNames[0] and commonNames[1] if they exist
            elif len(commonNames) >= 3:
                names = commonNames[1:3]
            # else choose "[row]" and commonNames[1] if they exist
            elif len(commonNames) == 2:
                names = commonNames[0:2]
            else:
                self.debugPrint("can't select valid columns for x and y")
                names = [None, None]
        return names

    def setStyle(self, index=None, style=None):
        self.debugPrint("in Plot2DWidget.setStyle() with index=",
                        index, "and style=", style)
        # if index is not passed choose the current index in plotList
        if index is None:
            index = self.plotList.indexOfTopLevelItem(
                self.plotList.currentItem())
        if index == -1:
            # return if not valid index
            return
        # set the current index of the Plot2DWidget to index
        self._currentIndex = index
        # if style is not passed choose the current default style
        if not style:
            style = self.styles.itemData(index).toString()
        # if style is already correct do nothing and return
        if self._plots[self._currentIndex].style == style:
            return
        if style == 'scatter':                                        # set the style in the plot
            self._plots[self._currentIndex].MPLplot.set_linestyle('')
            self._plots[self._currentIndex].MPLplot.set_marker('o')
        elif style == 'line':
            self._plots[self._currentIndex].MPLplot.set_linestyle('-')
            self._plots[self._currentIndex].MPLplot.set_marker('')
        else:
            self._plots[self._currentIndex].MPLplot.set_linestyle('-')
            self._plots[self._currentIndex].MPLplot.set_marker('o')
        self._plots[self._currentIndex].style = style
        self._plots[self._currentIndex].item.setText(3, style)
        self._updated = False

    def setColor(self, index=None, color=None):
        self.debugPrint("in Plot2DWidget.setColor() with index=",
                        index, "and color=", color)
        # if index is not passed choose the current index in plotList
        if index is None:
            index = self.plotList.indexOfTopLevelItem(
                self.plotList.currentItem())
        if self._currentIndex == -1:
            # return if not valid index
            return
        # set the current index of the Plot2DWidget to index
        self._currentIndex = index
        # if style is not passed choose the current default style
        if not color:
            color = self.colors.itemData(index).toString()
        # if style is already correct do nothing and return
        if self._plots[self._currentIndex].MPLplot.get_color() == color:
            return
        self._plots[self._currentIndex].MPLplot.set_color(
            color)         # set the color in the plot
        item = self._plots[self._currentIndex].item
        self.writeInColorInQTreeWidget(item, 4, color, color)
        self._updated = False
        return

    def writeInColorInQTreeWidget(self, item, index, text, matPlotLibColor):
        colorb = QColor(colors.ColorConverter.colors[matPlotLibColor])
        brush = QBrush()
        brush.setColor(colorb)
        item.setForeground(index, brush)
        item.setText(index, text)

    def levelChanged(self):
        self.debugPrint("in Plot2DWidget.showLegendStateChanged()")
        self.updatedGui(subject=self._cube, property="names", value=None)


class Plot3DWidget(PlotWidget):

    """
    Widget class for plotting 3D datasets (i.e. z(x,y) surfaces) from datacubes.
    This widget allows the user to choose three x, y and z datasets either at the top level of a datacube,
    or by combining one column at the datacube top level or a common children attribute with two columns common to all children.
    It manages a list of plots to be shown on a single graph, with changeable graphical attributes.
    It is registered as an observer of all datacubes containing the plotted data, so that updates are made when necessary.
    Several types of 3D graphs available in matplolib can be used to represent a 3d plot, including z color coded 2d images or real 3D plots in an xyz frame.
    Some 3d plot types are incompatible with each other on a same graph.
    Because matplolib 3d graphics commands make use of different data structures, the x, y, and z data of a plot can be stored in different ways.
    Some translators are available to convert one structure into one another.
    The possible structures are
        - {x1D, y1D, z1D} with all 1D lists of the same length
        - {x1D,y2D,z2D} or  {x2D,y1D,z2D} with a 1D length of n, and two identical 2D dimensions of n x m
        - {x1D,y1D,z2D} with x1D's length = n, y1D's length = m, and z2D's length = n x m.
    Depending of the type of 3D plots, data provided to the matplotlib graphics command have to lay or not on a rectangular grid or a regular grid with constant spacing along x and y.
    When the grid is rectangular but incomplete because not all data are available, it is possible to fill the missing cells with fake masked data for plotting.
    When the meshing is not regular, optional regularizing functions are available for producing regular grids (not coded yet).

    BUG: the notifications of plot updates at each new point are too precise so that to many redrawing are generated.
    """

    def __init__(self, parent=None, name=None, dataManager=None):         # creator Plot3DWidget
        PlotWidget.__init__(self, parent=parent,
                            dataManager=dataManager, name=name, threeD=True)

    # notification listener of Plot3DWidget
    def updatedGui(self, subject=None, property=None, value=None):
        # Difficult programing especially for autoplotting of a datacube with
        # not enough information.
        """
        Manage all possible GUI updates depending on
            - received messages from attached objects (datacubes and datamanager)
            - the status of the plotter and the attached cubes
        This method is supposed to allow autoplot of new datacubes as soon as they are ready for that (i.e. when they have enough children and/or data)
        """
        self.debugPrint('in ', self.name, '.updatedGui with subject=',
                        subject, ', property=', property, ', and value=', value)
        # 1) A new datacube arrived in the datamanager.
        if subject == self._dataManager and property == "addDatacube":
            if self.autoplot.isChecked():  # if autoplot
                # addPlot it (attach the cube to the plotter and plot it if
                # possible)
                self.addPlot(cube=value)
        # 2) New names of an attached datacube arrived
        elif isinstance(subject, Datacube) and property == "names":
            cube = subject  # cube is the subject
            # if cube = current datacube or is child of current datacube
            if self._cube is not None and (cube == self._cube or cube in self._cube.children()):
                self.updateControls()  # => update controls
            if self.autoplot.isChecked():  # if autoplot
                # test if the cube is the child of an attached datacube not
                # already plotted
                parent = cube.parent()
                test = parent is not None and self in parent.observers() and parent not in [
                    plot.cube for plot in self._plots]  # if yes
                if test:
                    # addPlot the cube's parent cube in case it is now ready
                    # for plot creation
                    self.addPlot(cube=parent)
                else:  # if no
                    # addPlot the cube itself in case it is ready for plot
                    # creation
                    self.addPlot(cube=cube)
        # 3) a datacube attached to this plotter has a new child
        elif isinstance(subject, Datacube) and property == "addChild":
            # the datacube and the child are the notified property and value,
            # respectively
            cube, child = subject, value
            if cube == self._cube:
                self.updateControls()  # if current datacube => update controls
            plot, needChild = None, False  # if cube is plotted ...
            for ploti in self._plots:
                if ploti.cube == cube:
                    plot = ploti
                    break
            if plot:
                names = plot.xname, plot.yname, plot.zname  # ... with children variables
                needChild = any(['child:' in name for name in names])
                if needChild:
                    # => attach child to plot3DWidget
                    self.debugPrint('attaching ', child, ' to ', self)
                    child.attach(self)
                    self._updated = False  # and request an update
            elif self.autoplot.isChecked():
                # if autoplot and not already plotted => try addPlot
                self.addPlot(cube=cube)
        # 4) a datacube of the datamanger not attached to this plotter
        # (otherwise would be case 3) has new child
        elif subject == self._dataManager and property == "addChild":
            None  # do nothing
        # 5) New points arrived in an attached datacube or attached child:
        elif isinstance(subject, Datacube) and property == "commit":
            cube = subject  # If attached only as current cube for name update do nothing
            for plot in self._plots:
                if cube == plot.cube or cube in plot.cube.children():  # Otherwise update plot
                    self._updated = False
                    break
        # note that addPlot sets self._updated to False after completion
        else:
            self.debugPrint("not managed")

    def switchAxes2D3D(self, newStyle, newPlot=None):
        # switches between axes3D and axes if needed and if user agrees
        toAxes3D = not self.canvas.threeDAxes and newStyle in __styles3DAxes3DOnly__
        toAxes = self.canvas.threeDAxes and newStyle in __styles3DAxes2DOnly__
        self.debugPrint('new style=', newStyle, 'threeDAxes=',
                        self.canvas.threeDAxes, 'toAxes3D=', toAxes3D, 'toAxes=', toAxes)
        switched = False
        if toAxes3D or toAxes:
            switch = len(self._plots) == 0 or (
                len(self._plots) == 1 and self._plots[0] == newPlot)
            switch = switch or QMessageBox.question(
                self, 'Warning', 'Current plot(s) will be cleared. Confirm?', QMessageBox.Ok, QMessageBox.Cancel) == QMessageBox.Ok
            if switch:
                self.clearPlots()
                self.canvas.createSubplot(threeDAxes=toAxes3D)
                self.canvas.draw()
                switched = True
        return switched

    # subclass in Plot2DWidget and Plot3DWidget
    def addPlot(self, cube=None, names=[None, None, None], clear='auto', style=None, color=None, **kwargs):
        """
        Adds a plot of a datacube in self._plots with specified variables. In case cube=None, use the current datacube.
        Add the corresponding row in the table below the graph.
        Then calls self.updatePlot() for redrawing.
        Note 1: In case datacube has no valid columns, no plot is added but the datacube is attached to plotter for future update.
        Note 2: datacube is attached to the plotter for future notifications, as well as its children 
                                                                                if they are used in the 3D plot,
                                                                                or if autoplot for future notification
        """
        self.debugPrint('in ', self.name, '.addPlot with cube=', cube, ', names=', names,
                        ', clear=', clear, ', style= ', style, ' and current cube = ', self._cube)
        if cube is None:
            # if no datacube passed use the current datacube
            cube = self._cube
        if cube is None:
            return                                      # give-up if no datacube
        if (self.autoclear.isChecked() and clear == 'auto') or clear == True:       # clear if autoclear
            self.clearPlots()

        # switch between axes3D and axes if needed and if user agrees
        if (not style) or self.styles.findText(style) == -1:
            style = str(self.styles.currentText())
        self.switchAxes2D3D(style)
        # Build valid x and y names
        names = self.preselectVariables(cube=cube, names=names)
        # If the plot is already present in the list of plots...
        for plot in self._plots:
            if cube == plot.cube:
                if [plot.xname, plot.yname, plot.zname] == names:
                    self._updated = False
                    # ... request update only and stops.
                    return
        ready = all([bool(name) for name in names]) and names[0] != names[
            1] and names[0] != names[2] and names[1] != names[2]
        if not ready:                                               # if datacube is not ready, dont plot it but
            if self.autoplot.isChecked():                             # if autoplot
                self.debugPrint('attaching ', cube, ' to ', self)
                # attach it
                cube.attach(self)
                for child in cube.children():
                    self.debugPrint('attaching ', child, ' to ', self)
                    child.attach(self)
                # so that it has a chance to be autoplotted at the next
                # notifications from the cube or its children
                return

        # Ohterwise build the new cube3DPlot
        plot = cube3DPlot()
        plot.cube = cube
        plot.xname, plot.yname, plot.zname = xname, yname, zname = names
        plot.legend = "%s, %s vs %s and %s" % (
            cube.name(), plot.xname, plot.yname, plot.zname)
        if (not color) or self.colors.findText(color) == -1:
            color = str(self.colors.currentText())
        plot.style = style
        plot.color = color
        # The cube3DPlot has a property 'data', that will be filled later
        # attach cube to plot3DWidget...
        self.debugPrint('attaching ', plot.cube, ' to ', self)
        plot.cube.attach(self)
        needChildren = any([('child:' in name) for name in names])
        if needChildren:
            for child in cube.children():
                # ... and its relevant children for the plot
                self.debugPrint('attaching ', child, ' to ', self)
                child.attach(self)
        # Add the plot as a plotitem in the view plotList below the graph
        # window
        plotItem = QTreeWidgetItem(
            [cube.name(), xname, yname, zname, style, color])
        plot.item = plotItem
        self.plotList.addTopLevelItem(plotItem)
        # update the view plotList of self._plot
        self.plotList.update()

        # initialize empty plot3D
        plot.MPLplot = None
        # and add the plot to the list self._plots
        self._plots.append(plot)
        # let ontimer() call all functions updating the graph with points,
        # create all labels, and redraw if necessary)
        self._updated = False

    def updatePlotData(self, draw=False, plot=None, regularize=None, **kwargs):
        """
        Creates or update a plot.
        """
        self.debugPrint('in ', self.name, '.updatePlotData() with plot=', plot)
        if plot is None:
            if self._currentIndex:
                plot = self._plots[self._currentIndex]
            else:
                return
        fig = self.canvas._fig
        ax = self.canvas.axes
        cmap = cm.get_cmap(plot.color)
        # call the builder of data dictionary "plot.data".
        self.data2Plot(plot, regularize=regularize)
        dat = plot.data
        style = plot.style
        x, y, z, dims = dat['x'], dat['y'], dat['z'], dat['xyzDims']
        pl = plot.MPLplot
        # plot.MPLplot is a list of couples(ui, linei)
        if style == "Waterfall(3D)":
            u1d, u2d = x, y
            if dims[0] == 2:
                u1d, u2d = y, x
            if pl is None:
                pl = []
            uis = [pli[0] for pli in pl]
            for i in range(len(u1d)):
                if u1d[i] in uis:
                    index = uis.index(u1d[i])
                    oldLine = pl[i][1]
                    newLine = Line3D(
                        array([u1d[i]] * len(u2d[i])), u2d[i], z[i])
                    if u2d and len(u2d) > i and len(z) > i and newLine != oldLine:
                        pl[i] = newLine
                else:
                    line = ax.plot(array([u1d[i]] * len(u2d[i])), u2d[i], z[i])
                    pl.append([u1d[i], line])
        elif style in ["Image(2D)", "Contours(2-3D)", "Filled contours(2-3D)"]:
            if dat['regular']:
                # Remember that if z is bidimentionel, its first dimension
                # corresponds either to x if x is 1d and y is 2d, or to y if x
                # is 2d and y is 1d
                if dims[0] == 1:
                    dat['z'] = dat['z'].T
                    dat['mask'] = dat['mask'].T
                if pl is None:
                    # this is where the image or countour plot.MPLplot is
                    # created
                    if len(dat['z']) != 0:
                        if style == "Image(2D)":
                            pl = plot.MPLplot = ax.imshow(ma.array(dat['z'], mask=dat[
                                                          'mask']), interpolation='nearest', cmap=cmap, origin='lower', **kwargs)  # create 2D image
                            self.setExtent2DImage(pl, dat['xMin'], dat['xMax'], dat[
                                                  'yMin'], dat['yMax'], dat['dx'], dat['dy'])
                        elif style in ["Contours(2-3D)", "Filled contours(2-3D)"]:
                            if dims[0] == 2:
                                x = x[0]
                            if dims[1] == 2:
                                y = y[0]
                            plotMethod = ax.contour
                            if style == "Filled contours(2-3D)":
                                plotMethod = ax.contourf
                            pl = plot.MPLplot = plotMethod(x, y, ma.array(
                                dat['z'], mask=dat['mask']), cmap=cmap)
                        # and its colorbar
                        self.addColorBar(pl, label=plot.zname)
                else:                                                        # this is where the image's maskedArray is rebuilt
                    if style == "Image(2D)":
                        pl.set_array(ma.array(dat['z'], mask=dat['mask']))
                        self.setExtent2DImage(pl, dat['xMin'], dat['xMax'], dat[
                                              'yMin'], dat['yMax'], dat['dx'], dat['dy'])
                    elif style in ["Contours(2-3D)", "Filled contours(2-3D)"]:
                        x, y = dat['x'], dat['y']
                        if dims[0] == 2:
                            x = x[0]
                        if dims[1] == 2:
                            y = y[0]
                        plotMethod = ax.contour
                        if plot.style == "Filled contours(2-3D)":
                            plotMethod = ax.contourf
                        pl = plot.MPLplot = plotMethod(x, y, ma.array(
                            dat['z'], mask=dat['mask']), cmap=cmap)  # no possible update. Recalculate
                    pl.autoscale  # fixes a bug
        elif style == 'Scatter(3D)':
            if pl is None:
                if len(dat['z']) != 0:
                    pl = ax.scatter(x, y, z, cmap=cmap)
            else:
                pl._offsets3d = (tuple(x), tuple(y), array(z))
        elif style == 'Line(3D)':
            if pl is None:
                if len(dat['z']) != 0:
                    pl = ax.plot(x, y, z)
            else:
                plot.MPLplot = Line3D(x, y, z)
        elif style == 'Surface(3D)':
            if len(dat['z']) != 0:
                pl = plot_surface(x, y, z, cmap=cmap)
        elif style == 'Tri-surface(3D)':
            if len(dat['z']) != 0:
                pl = plot.MPLplot = ax.plot_trisurf(
                    x, y, z, cmap=cmap, linewidth=0.2)

    def collectData(self, plot):
        """
        Returns a tuple dims=[x dimension, y dimension, z dimension], rowxyz=[x,y,z], xLineInz.
            x,y,z have a structure  that reflect their structure in the datacube.
        dims stores the 1 or 2 dimensional character of x, y, and z.
        NOTE 1: '2D arrays' in rowxyz can be 1d arrays of 1d arrays instead of numpy 2d arrays if the array is not rectangular and full
        NOTE 2: if z is 2D, its first dimension corresponds either to x if x is 1d and y is 2d, or to y if x is 2d and y is 1d
        """
        self.debugPrint('in ', self.name, '.collectData() with plot=', plot)
        names = xname, yname, zname = plot.xname, plot.yname, plot.zname
        cube = plot.cube
        # rowxyz is the [x,y,z] structure containing the row data
        rowxyz = []
        # dim stores the corresponding dimensions [dim[x],dim[y],dim[z]]
        dims = []
        # xLinesInz=None
        for name in names:
            # If the variable is a child attribute
            if name.startswith('childAttr:'):
                shortName = name[len('childAttr:'):]
                # var is the 1D array of attribute values of all children
                var = array([cube.attributesOfChild(childCube)[shortName]
                             for childCube in cube.children()])
                dim = 1  # save the variable dimension as 1
            # If the variable is a children's column
            elif name.startswith('child:'):
                shortName = name[len('child:'):]
                if shortName == '[row]':
                    var = array([arange(0, len(childCube), 1)
                                 for childCube in cube.children()])
                else:
                    # var is the '2D array' (or 1 d array of 1d array) of these
                    # children's column
                    var = array([childCube.column(shortName)
                                 for childCube in cube.children()])
                dim = 2  # save the variable dimension as 2
            else:
                # If the variable is one of the column of the cube
                if name == '[row]':
                    var = arange(0, len(cube), 1)
                else:
                    var = cube.column(name)  # set var to it
                dim = 1  # save the variable dimension as 1
            # Save a first version of the data non necessarily regular,
            rowxyz.append(var)
            dims.append(dim)  # as well as the corresponding dimensions.
            #if dims == [1,2,2]:  xLinesInz=False
            # elif dims == [2,1,2]:  xLinesInz=True
        return dims, rowxyz

    def to1d(self, dims, rowxyz, xLinesInz=True):
        """
        Converts a rowxyz=[x,y,z] dataset with dimensions dims=[1,1,2] or [1,2,2] or [2,1,2] to 
        the corresponding [x,y,z] dataset with dimensions dims=[1,1,1].
        WARNING1: Original rowxyz, dims, and xLinesInz are overwritten in memory.
        WARNING2: This function does not check for all inconsistencies in input data.
        """
        self.debugPrint('in ', self.name, '.to1d() with dims=', dims)
        xList, yList, zList = [], [], []
        if dims == [1, 1, 2]:                         # dimensions are 1d,1d,2d
            # calculate lengthes of x, y, and z
            lx, ly, lz = [len(u) for u in rowxyz]
            # calculate lengthes of z[1], z[2], ...
            lz2 = [len(u) for u in rowxyz[2]]
            # z= [xListAty1, xListAty2, xListAty3,...]
            if xLinesInz == True:
                ly = min(ly, lz)
                for i in range(ly):
                    lxi = min(lx, lz2[i])
                    xList += list(rowxyz[0][0:lxi])
                    yList += [rowxyz[1][i]] * lxi
                    zList += list(rowxyz[2][i][0:lxi])
            # z= [yListAtx1, yListAtx2, yListAtx3,...]
            elif xLinesInz == False:
                lx = min(lx, lz)
                for i in range(lx):
                    lyi = min(ly, lz2[i])
                    yList += list(rowxyz[1][0:lyi])
                    xList += [rowxyz[0][i]] * lyi
                    zList += list(rowxyz[2][i][0:lyi])
        elif dims == [1, 2, 2]:
            # calculate lengthes of x, y, and z
            lx, ly, lz = [len(u) for u in rowxyz]
            lx = min(lx, ly, lz)
            # calculate lengthes of z[1], z[2], ...
            ly2 = [len(u) for u in rowxyz[1]]
            # calculate lengthes of z[1], z[2], ...
            lz2 = [len(u) for u in rowxyz[2]]
            for i in range(lx):
                lyi = min(ly2[i], lz2[i])
                yList += list(rowxyz[1][i][0:lyi])
                xList += [rowxyz[0][i]] * lyi
                zList += list(rowxyz[2][i][0:lyi])
        elif dims == [2, 1, 2]:
            # calculate lengthes of x, y, and z
            lx, ly, lz = [len(u) for u in rowxyz]
            ly = min(lx, ly, lz)
            # calculate lengthes of x[1], x[2], ...
            lx2 = [len(u) for u in rowxyz[0]]
            # calculate lengthes of z[1], z[2], ...
            lz2 = [len(u) for u in rowxyz[2]]
            for i in range(ly):
                lxi = min(lx2[i], lz2[i])
                xList += list(rowxyz[0][i][0:lxi])
                yList += [rowxyz[1][i]] * lxi
                zList += list(rowxyz[2][i][0:lxi])
        else:
            return False
        for u, i in zip([xList, yList, zList], range(3)):
            rowxyz[i] = u
            dims[i] = 1
        xLinesInz = None
        success = True
        return success

    def to2d(self, dims, rowxyz, sort=None):
        """
        Converts a rowxyz=[x,y,z] dataset with dimensions dims=[1,1,1] to 
        the corresponding [x,y,z] dataset with dimensions dims=[1,2,2] or dims=[2,1,2].
            dims=[2,1,2] if x has the form [x0,x1,,...,xn,x0,x1,...,xn,...];
            dims=[1,2,2] if x has the form [x0,x0,x0,...,x1,x1,x1,...,xn,xn,xn]
        WARNING1: Original rowxyz, dims, and xLinesInz are overwritten in memory.
        WARNING2: This function does not check for all inconsistencies in input data.
        """
        self.debugPrint('in ', self.name, '.to2d() with dims=', dims)
        if sort == 'x':
            pass  # to be coded
        elif sort == 'y':
            pass  # to be coded
        # y will be the 2d variable except if x[0] and x[1] exist and are
        # different
        i1d, i2d = 0, 1
        if len(rowxyz[0]) > 1 and rowxyz[0][1] != rowxyz[0][0]:
            i1d, i2d = 1, 0
        # reshape the 1d and 2d variables:
        rowxyz[i1d], pos = array([(u, n) for (n, u) in enumerate(rowxyz[i1d]) if n == 0 or u != rowxyz[i1d][
                                 n - 1]]).transpose()  # get the list of values and position of var1d elements different from the previous one
        rowxyz[i2d] = [rowxyz[i2d][pos[i]:pos[i + 1]] for i in range(len(pos) - 1)] + [
            rowxyz[i2d][pos[len(pos) - 1]:]]        # use position to slice the 2d variable
        rowxyz[2] = array([rowxyz[2][pos[i]:pos[i + 1]] for i in range(len(pos) - 1)] + [
                          rowxyz[2][pos[len(pos) - 1]:]])       # and the z. make an array
        dims[i2d] = 2
        dims[2] = 2

    def to222d(self, dims, rowxyz, sort=None):  # TO BE CODED
        self.debugPrint('in ', self.name, '.to222d() with dims=', dims)
        print 'not programmed yet'
        if dims[2] == 1:
            self.to2d(dims, rowxyz, sort=sort)
        if dims[0:1] == [1, 2]:
            rowxyz[0] = array()  # to be coded
        elif dims[0:1] == [2, 1]:
            rowxyz[1] = array()  # to be coded

    def data2Plot(self, plot, regularize=None):
        """
        Collects data in proper format, analyzes them, and builds the data dictionary plot.data used for plotting.
        (This dictionary contains:
        - x (ndarray), y (ndarray), z(ndarray), xyzDims(list),
        and optionally if format is not dims=[1,1,1]
            - mask (ndarray), 
            - rectangular(bool), regular(bool), full(bool),
            - xMin,xMax,yMin,yMax, and dx,dy if regular is True. Note that xMin,yMin are not necessarily smaller than xMax,yMax
        """
        self.debugPrint('in ', self.name, '.data2Plot() with plot=',
                        plot, " and regularize =", regularize)
        dims, rowxyz = self.collectData(plot)
        # call translator to2d if needed
        if dims == [1, 1, 1] and plot.style in __styles3DEncodexx2__:
            self.to2d(dims, rowxyz, sort=None)
        # call translator to1d if needed
        elif dims != [1, 1, 1] and plot.style in __styles3DEncode111__:
            self.to1d(dims, rowxyz)
        # call translator to222d if needed
        elif dims != [2, 2, 2] and plot.style in __styles3DEncode222__:
            self.to222d(dims, rowxyz)
        plot.data = {}
        plot.data['xyzDims'] = dims
        plot.data['x'], plot.data['y'], plot.data['z'] = rowxyz
        # In case the type of matplotlib plot requires regular data
        if plot.style in __styles3DRectangularOnly__ + __styles3DRegularOnly__:
            # The goal is now to build a valid rectangular and regular 2d array
            # dat['z'] and its mask dat[mask'] for building later a masked
            # array
            # checks regularity and stores
            # 'missing','dx','dy','xMin','xMax','yMin','yMax' in the plot.data
            # dictionary.
            # # fill the mask with False at the unvalid data locations
            self.checkRectRegAndComplete(plot)
            # if not regular and regularize requested
            if (not plot.data['rectangular'] or not plot.data['regular']) and regularize:
                # try to regularize and overwrite plot.data
                self.regularize(plot)

    def checkRectRegAndComplete(self, plot):
        """
        1) Checks if the data are on
            - a RECTANGULAR XY grid (same y's for all x except missing x in the last row or missing y in the last column),
            - a FULL grid  (i.e. with no data missing) or with missing X in the last row or missing Y in the last column,
            - a REGULAR grid (constant spacing in x, constant in y).
        2) Stores in the plot.data dictionary:
            - 3 booleans 'rectangular','regular',and 'full',
            - 8 numbers (or None if irrelevant) 'missingXOnLastRow','missingYOnLastColumn','dx','dy','xMin','xMax','yMin','yMax'.
            - A new mask of boolean values rectangular and full or rectangular and completed (see below)
        IMPORTANT:  If the grid is rectangular but not full, it is made artificially full by completing it with the last value,
                    and the mask plot.data['mask'] is set accordingly to indicate invalid added data to be masked.
        """
        dat = plot.data
        rectangular, regular, full = [False] * 3
        missingXOnLastRow, missingYOnLastColumn, dx, dy = [None] * 4
        xList, yList = map(lambda varName: list(
            set(flatten(dat[varName]))), ['x', 'y'])
        xMin, xMax, yMin, yMax = min(xList), max(xList), min(yList), max(yList)
        dims = dat['xyzDims']
        # simple columx, column y and column z
        if all([dim == 1 for dim in dims]):
            None  # sort in x, y, z, and check increments are constant for each => regular => a masked array can be formed
        # (1d x and 2d y) or (2d x and 1d y) and 2d z values
        elif dims[0] + dims[1] == 3 and dims[2] == 2:
            var1d, var2d = dat['x'], dat['y']
            if dims[0] == 2:
                var1d, var2d = dat['y'], dat['x']
            # First check that the 1d and 2d XY structures match the 2d Z
            # structure
            XYMatchZ = len(var1d) >= len(var2d) and len(var2d) == len(dat['z']) and all(
                [len(var2d[i]) == len(dat['z'][i]) for i in range(len(var2d))])
            self.debugPrint('XYMatchZ = ', XYMatchZ)
            # Second check for the  XY structure itself
            if XYMatchZ:
                rectangular = len(var2d) in [len(var1d), len(var1d) - 1]
                rectangular = rectangular and all([var == var2d[0] for var in var2d[
                                                  1:-1]]) and all(var2d[-1] == var2d[0][:len(var2d[-1])])
                self.debugPrint('rectangular = ', rectangular)
                if rectangular:
                    missingX, missingY = 0, 0
                    maxLe, le = len(var2d[0]), len(var2d[-1])
                    missing = maxLe - le
                    full = missing == 0
                    if not full:
                        if dims[0] == 2:
                            missingXOnLastRow = missing
                        else:
                            missingYOnLastColumn = missing
                    if len(var2d[0]) == 0:
                        regular2D = False
                    elif len(var2d[0]) == 1:
                        regular2D = True
                    else:
                        dys = map(lambda a, b: a - b,
                                  var2d[0][1:], var2d[0][:-1])
                        regular2D = all(
                            [abs(dyi / dys[0] - 1.) < 1.e-4 for dyi in dys])
                        self.debugPrint('regular2D = ', regular2D, ', MindX2D = ', min(
                            dys), ', MaxdX2D = ', max(dys))
                        if regular2D:
                            dy = dys[0]
                    if len(var1d) == 0:
                        regular1D = False
                    elif len(var1d) == 1:
                        regular1D = True
                    else:
                        dxs = map(lambda a, b: a - b, var1d[1:], var1d[:-1])
                        regular1D = all(
                            [abs(dxi / dxs[0] - 1.) < 1.e-4 for dxi in dxs])
                        self.debugPrint('regular1D = ', regular1D, ', MindX1D = ', min(
                            dxs), ', MaxdX1D = ', max(dxs))
                        if regular1D:
                            dx = dxs[0]
                    regular = regular2D and regular1D
                    if dims[0] == 2:
                        dx, dy = dy, dx
                    # although missing=true will be saved in
                    # plot.data['missing'],
                    if not full:
                        # the missing x or y values are added
                        var2d[-1] = var2d[0]
                        last = array([0.] * maxLe)
                        last[:le] = plot.data['z'][-1]
                        # as well as the missing z values set to the last z
                        # (will be masked later)
                        last[le:] = plot.data['z'][-1][-1]
                        plot.data['z'][-1] = last
                        # conversion to a 2d array instead of a 1d array of 1d
                        # arrays
                        plot.data['z'] = array(list(plot.data['z']))
                    mask = ma.make_mask_none(dat['z'].shape)
                    if not full:
                        mask[-1, le:] = True
                    dat['mask'] = mask
        if plot.cube == self._cube:
            self.regularGrid.setChecked(regular)
        dat['rectangular'], dat['regular'], dat[
            'full'] = rectangular, regular, full
        dat['missingXOnLastRow'], dat[
            'missingYOnLastColumn'] = missingXOnLastRow, missingYOnLastColumn
        dat['dx'], dat['dy'], dat['xMin'], dat['xMax'], dat[
            'yMin'], dat['yMax'] = dx, dy, xMin, xMax, yMin, yMax

    def regularize(self, plot):
        # SANDBOX CODE => TO BE REWRITTEN
        dat = plot.data
        rectangular, regular, xDim, yDim = dat[
            'rectangular'], dat['regular'], data['xyzDims'][0:2]
        if rectangular and not regular:
            xs0 = dat['x']
            if xDim == 2:
                xs0 = xs0[0]
            xMin, xMax = min(xs0), max(xs0)
            # smallest dx different from 0
            dx = min(
                set(map(lambda a, b: a - b, xs0[1:], xs0[:-1])).discard(0))
            ys0 = dat['y']
            if yDim == 2:
                ys0 = ys0[0]
            yMin, yMax = min(ys0), max(ys0)
            # smallest dy different from 0
            dy = min(
                set(map(lambda a, b: a - b, ys0[1:], ys0[:-1])).discard(0))
            zs0 = dat['z']
            xs, ys = np.mgrid[xMin:xMax:int(
                (xMax - xMin) / dx) + 1, yMin:yMax:int((yMax - yMin) / dy) + 1]
            resampled = griddata(xs0, ys0, zs0, xs, ys)
        elif not rectangular:
            pass
        return

    # subclass in Plot2DWidget and Plot3DWidget
    def updateControls(self, names=[None, None, None]):
        """
        Updates the x, y and z variable names in the x, y, and z selectors. Then makes a pre-selection by calling preselectVariables().
        """
        self.debugPrint('in Plot3DWidget.updateControls(names) with names=',
                        names, ', and current datacube=', self._cube)
        selectors = [self.xNames, self.yNames, self.zNames]
        cube = self._cube
        # memorize current selection to reuse it if necessary
        currentNames = [str(selector.currentText()) for selector in selectors]
        # First find the column name of datacube (possibly parent) and the
        # attributes and column names common to all children if any
        if cube is not None:                                     # if current cube exists
            names0 = cube.names()                            # get its column names
            names0.insert(0, '[row]')
            children = cube.children()
            hasChildren = len(children) > 0
            names1 = []
            attributes = []
            if hasChildren:
                # gets all column names common to all direct children
                names1 = cube.commonNames()
                if len(names1) >= 2:
                    names1 = names1[1]
            # Then create the lists of choices to add the [row] choices and let
            # the user know if a choice correspond to a parent name,or child
            # name or attribute
                names1.insert(0, '[row]')
                names1 = ['child:' + name for name in names1]
                # gets all attribute names common to all direct children
                attributes = cube.attributesOfChildren(common=True)
                attributes = ['childAttr:' + attr for attr in attributes]
            # update selectors if necessary
            for selector in selectors:
                # check if any name in names0, names1, or attributes is absent
                # from existing selector
                # if missing element
                if any([selector.findText(name) == -1 for name in names0 + names1 + attributes]):
                    # refill the selector
                    self.regularGrid.setChecked(False)
                    selector.clear()
                    if names0 and len(names0) > 0:
                        selector.addItems(names0)
                        selector.insertSeparator(selector.count())
                    if len(names1) > 0:
                        selector.addItems(names1)
                        selector.insertSeparator(selector.count())
                    if len(attributes) > 0:
                        selector.addItems(attributes)
            # Preselect variables
            names = self.preselectVariables(
                cube=cube, names=names, previousNames=currentNames)
            # select the requested x and y names if correct and necessary
            if names and names != [None, None, None] and names != currentNames and all([bool(name) for name in names]):
                indices = map(lambda selector, name: selector.findText(
                    name), selectors, names)
                if all(index != -1 for index in indices):
                    map(lambda selector, index: selector.setCurrentIndex(
                        index), selectors, indices)
        if selectors[0].count() >= 3:
            self.addButton.setEnabled(True)
        else:
            self.addButton.setEnabled(False)

    # subclass in Plot2DWidget and Plot3DWidget
    def preselectVariables(self, cube=None, names=[None, None, None], previousNames=[None, None, None]):
        """
        preselect x, y and z variables in the selectors before plotting a datacube.
        """
        if cube is None:
            cube = self._cube           # if no datacube passed use the current datacube
        if cube is None:
            return [None, None]                   # if no datacube give up
        # gets all possible variables
        names0 = cube.names()                       # otherwise gets its column names
        if len(names0) != 0:
            names0.insert(0, '[row]')    # add the row number choice
        allNames = names0
        children = cube.children()                  # Get its children
        hasChildren = len(children) > 0
        if hasChildren:                           # if the cube has children
            names1 = []
            if len(cube.commonNames()) >= 2:
                # gets all column names common to all direct children
                names1 = cube.commonNames()[1]
            if len(names1) != 0:
                names1.insert(0, '[row]')
            names1 = ['child:' + name for name in names1]
            allNames.extend(names1)
            # gets all attribute names common to all direct children
            attribs = cube.attributesOfChildren(common=True)
            attributes = ['childAttr:' + attr for attr in attribs]
            allNames.extend(names1)
        # Then defines how to preselect
        # if all passed names exist select them
        if all([(name and name in allNames) for name in names]):
            return names
        # if all previous names exist and are different from 'row'select them
        elif all([(bool(name) and name != '[row]' and name in allNames) for name in previousNames]):
            return previousNames
        # if no children or children with less than 2 variables (including row)
        elif (not hasChildren or (hasChildren and len(names1) <= 1)):
            if len(names0) < 3:
                # and less than 3 columns => no preselection and return
                return [None, None, None]
            # and 3 columns including row numbers => preselect them
            elif len(names0) == 3:
                names = names0                      # insert code here for proper preselection
            else:                                 # 3 columns or more after row numbers  => preselect them
                names = names0[1:4]               #
        # children and more than 2 children variables (including row)
        else:
            # if at least one column after row in parent, with a length ...
            parentColumn = cube.column(cube.columnName(0))
            # ... equal to the number of children
            if len(names0) >= 2 and parentColumn is not None and len(parentColumn) == len(children):
                # x is the first column after row of the parent cube
                names[0] = names0[1]
            else:
                attributes2 = list(attributes)      #
                attributes2.remove('childAttr:row')
                if len(attributes2) != 0:
                    names[0] = attributes2[0]
                else:
                    # x is the row attribute column
                    names[0] = 'childAttr:row'
            if len(names1) >= 3:
                # yz are is the children first two columns
                names[1:3] = names1[1:3]
            else:
                names[1:3] = names1[0:2]
        return names

    # subclass in Plot2DWidget and Plot3DWidget
    def setStyle(self, index=None, style=None):
        self.debugPrint("in Plot3DWidget.setStyle() with index=",
                        index, "and style=", style)
        # if index is not passed choose the current index in plotList
        if index is None:
            index = self.plotList.indexOfTopLevelItem(
                self.plotList.currentItem())
        if index == -1:
            # return if not valid index
            return
        plot = self._plots[index]
        # set the current index of the Plot2DWidget to index
        self._currentIndex = index
        # if style is not passed choose the current default style
        if not style:
            style = self.styles.itemData(index).toString()
        # if style is already correct do nothing and return
        if self.style == style:
            return
        plot.style = style
        # switch between 2D axes and 3D axes if needed and accepted by user
        switched = self.switchAxes2D3D(style, plot)
        if not switched:
            plot.MPLplot = None
            self._plots[self._currentIndex].style = style
            self._plots[self._currentIndex].item.setText(4, style)
            self.updatePlot(clearFirst=True, draw=True)
        else:  # switched => everything has been deleted => add plot
            cube, names, style, color = plot.cube, [
                plot.xname, plot.yname, plot.zname], plot.style, plot.color
            del plot
            self.addPlot(cube=cube, names=names, style=style, color=color)

    # subclass in Plot3DWidget
    def setColor(self, index=None, color=None):
        self.debugPrint("in Plot3DWidget.setColor() with index=",
                        index, "and color=", color)
        # if index is not passed choose the current index in plotList
        if index is None:
            index = self.plotList.indexOfTopLevelItem(
                self.plotList.currentItem())
        if self._currentIndex == -1:
            # return if not valid index
            return
        # set the current index of the Plot2DWidget to index
        self._currentIndex = index
        # if style is not passed choose the current default style
        if not color:
            color = self.colors.itemData(index).toString()
        # if style is already correct do nothing and return
        if self._plots[self._currentIndex].MPLplot.get_cmap() == cm.get_cmap(color):
            return
        self._plots[self._currentIndex].MPLplot.set_cmap(
            color)         # set the color in the plot
        item = self._plots[self._currentIndex].item
        item.setText(5, color)
        self._updated = False
        return

    def setExtent2DImage(self, pl, xMin, xMax, yMin, yMax, dx, dy):
        if not isinstance(dx, (int, float)):
            dx = 1.
        if not isinstance(dy, (int, float)):
            dy = 1.

        # set the x and y limits of the image
        def lowHigh(uMin, uMax, du):
            uLow = uMin - abs(du) / 2.
            uHigh = uMax + abs(du) / 2.
            if du < 0:
                uLow, uHigh = uHigh, uLow
            return uLow, uHigh
        xLow, xHigh = lowHigh(xMin, xMax, dx)
        yLow, yHigh = lowHigh(yMin, yMax, dy)
        pl.set_extent([xLow, xHigh, yLow, yHigh])

    def addColorBar(self, MPLplot, label='z'):
        """
        Adds to the canvas a colorbar attached to matplotlib plot MPLplot.
        """
        fig = self.canvas._fig
        axesList = fig.get_axes()
        if len(axesList) == 1:
            ax0 = axesList[0]
            # memorize data axes position for future restore
            if not hasattr(ax0, 'initialPosition'):
                ax0.initialPosition = ax0.get_position()
            cb = fig.colorbar(MPLplot, ax=ax0)
            if hasattr(ax0, 'colorbarPosition'):
                cb.ax.set_position(ax0.colorbarPosition)
                ax0.set_position(ax0.position)
            else:
                # memorize colorbar position for future use
                ax0.colorbarPosition = cb.ax.get_position()
                ax0.position = ax0.get_position()
            cb.set_label(label, rotation=90)

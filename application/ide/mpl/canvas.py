
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.uic import *
import sys
import os
import os.path
import tempfile

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt4agg import FigureManagerQTAgg
from matplotlib.figure import Figure
from application.ide.editor.codeeditor import CodeEditor
from math import fabs


class FigureManager(FigureManagerQTAgg):
    pass


class CanvasDialogTab(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self._options = dict()

    def addOption(self, name, enterType, defaultValue=None, row=None, column=None, rowSpan=None, colSpan=None):
        lay = self.layout
        row2, col2, rowSpan2, columnSpan2 = 0, 0, 0, 0
        validRowAndColumn = isinstance(row, int) and isinstance(column, int)
        validSpans = isinstance(rowSpan, int) and isinstance(colSpan, int)
        if enterType in ["QLineEdit", "QDoubleSpinBox"]:
            if enterType == "QLineEdit":
                option = QLineEdit()
                option.setText(str(defaultValue))
            elif enterType == "QDoubleSpinBox":
                option = QDoubleSpinBox()
                if defaultValue:
                    option.setValue(defaultValue)
            label = QLabel(name + ": ")
            if validRowAndColumn:
                if validSpans:
                    lay.addWidget(label, row, column, rowSpan, colSpan)
                    lay.addWidget(option, row + 1, column, rowSpan, colSpan)
                else:
                    lay.addWidget(label, row, column)
                    lay.addWidget(option, row + 1, column)
            else:
                lay.addWidget(label)
                row2, col2 = lay.getItemPosition(lay.indexOf(label))[:2]
                lay.addWidget(option, row2 + 1, col2)
        elif enterType == "QCheckBox":
            option = QCheckBox(name)
            if isinstance(defaultValue, bool):
                option.setChecked(defaultValue)
            if validRowAndColumn:
                if validSpans:
                    lay.addWidget(option, row, column, rowSpan, colSpan)
                else:
                    lay.addWidget(option, row, column)
            else:
                lay.addWidget(option)
        else:
            return None
        self._options[name] = option
        return option


class CanvasDialog(QDialog):  # The canvas dialog does not redraw by itself

    def __init__(self, canvas, parent=None):
        try:
            reload(sys.modules["application.ide.mpl.canvas"])
            from application.ide.mpl.canvas import CanvasDialogTab
        except:
            raise Error("Unable to import CanvasDialogTab")
        QDialog.__init__(self, parent)
        self.setFixedWidth(250)
        layout = QGridLayout()
        self.setLayout(layout)
        self._canvas = canvas
        self.setWindowTitle(self._canvas.title() + " properties")
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 0, 0)
        cancelButton = QPushButton("Cancel")
        applyButton = QPushButton("Apply")
        okButton = QPushButton("OK")
        buttonsLayout = QBoxLayout(QBoxLayout.RightToLeft)
        buttonsLayout.addWidget(okButton)
        buttonsLayout.addWidget(applyButton)
        buttonsLayout.addWidget(cancelButton)
        buttonsLayout.addStretch(0)
        layout.addLayout(buttonsLayout, 1, 0)

        st = self.scaleTab = CanvasDialogTab(self)
        cva = canvas.axes

        squared = st.addOption("Square XY", "QCheckBox",
                               defaultValue=not canvas.squared, row=0, column=0)
        centered = st.addOption("centered", "QCheckBox",
                                defaultValue=canvas.centered, row=0, column=1)
        squared.stateChanged.connect(
            lambda: centered.setEnabled(squared.isChecked()))
        squared.setChecked(canvas.squared)

        def enable(optionList, trueOrFalse):
            for option in optionList:
                option.setEnabled(trueOrFalse)

        xMinv, xMaxv = cva.get_xlim()
        xMin = st.addOption("X Min", "QLineEdit",
                            defaultValue=xMinv, row=1, column=0)
        xMax = st.addOption("X Max", "QLineEdit",
                            defaultValue=xMaxv, row=1, column=1)
        autoX = st.addOption("Auto X", "QCheckBox",
                             defaultValue=not canvas.autoX, row=2, column=2)
        autoX.stateChanged.connect(lambda: enable(
            [xMin, xMax], not autoX.isChecked()))
        autoX.setChecked(canvas.autoX)

        yMinv, yMaxv = cva.get_ylim()
        yMin = st.addOption("Y Min", "QLineEdit",
                            defaultValue=yMinv, row=3, column=0)
        yMax = st.addOption("Y Max", "QLineEdit",
                            defaultValue=yMaxv, row=3, column=1)
        autoY = st.addOption("Auto Y", "QCheckBox",
                             defaultValue=not canvas.autoY, row=4, column=2)
        autoY.stateChanged.connect(lambda: enable(
            [yMin, yMax], not autoY.isChecked()))
        autoY.setChecked(canvas.autoY)

        inputBoxes = [xMin, xMax, yMin, yMax]

        if canvas.threeD:      # find a way to retrieve Z extrema of the scale for any of the plot types
            minZ, maxZ = canvas.my_get_zlim()
            zMin = st.addOption("Z Min", "QLineEdit",
                                defaultValue=round(minZ, 5), row=5, column=0)
            zMax = st.addOption("Z Max", "QLineEdit",
                                defaultValue=round(maxZ, 5), row=5, column=1)
            autoZ = st.addOption("Auto Z", "QCheckBox",
                                 defaultValue=not canvas.autoZ, row=6, column=2)
            autoZ.stateChanged.connect(lambda: enable(
                [zMin, zMax], not autoZ.isChecked()))
            autoZ.setChecked(canvas.autoZ)
            inputBoxes.extend([zMin, zMax])
            if canvas.threeDAxes:
                elevation = st.addOption("Elevation", "QDoubleSpinBox", defaultValue=round(
                    cva.elev, 0), row=7, column=0)
                azimut = st.addOption("Azimut", "QDoubleSpinBox", defaultValue=round(
                    cva.azim, 0), row=7, column=1)
                elevation.setMinimum(-90.)
                elevation.setMaximum(+90.)
                elevation.setSingleStep(5.)
                azimut.setMinimum(-180.)
                azimut.setMaximum(+180.)
                azimut.setSingleStep(5.)
                azimut.setWrapping(True)
                elevation.valueChanged.connect(lambda: self.applyView3D)
                azimut.valueChanged.connect(lambda: self.applyView3D)
        objValidator = QDoubleValidator(self)
        for extr in inputBoxes:
            extr.setValidator(objValidator)
        # xMin.setValidator(objValidator);xMax.setValidator(objValidator);yMin.setValidator(objValidator);yMax.setValidator(objValidator)
        #self.connect(xMin,SIGNAL("textEdited(QString)"),lambda : autoX.setChecked(False))
        self.tabs.addTab(self.scaleTab, "Scale")
        self.connect(cancelButton, SIGNAL("clicked()"), self.close)
        self.connect(applyButton, SIGNAL("clicked()"), self.apply)
        self.connect(okButton, SIGNAL("clicked()"), self.ok)

    def ok(self):
        self.apply()
        self.close()

    def applyView3D(self):
        self._canvas.axes.view_init(
            sto["Elevation"].value(), sto["Azimut"].value())
        self._canvas.redraw()

    def apply(self):
        # memorize part of the settings in the canvas...
        cv = self._canvas
        fig = cv._fig
        cva = cv.axes
        sto = self.scaleTab._options
        cv.squared = sto["Square XY"].isChecked()
        cv.centered = sto["centered"].isChecked()
        cv.autoX = sto["Auto X"].isChecked()
        cv.autoY = sto["Auto Y"].isChecked()
        # ... and the absolute limits in the matpolib figure if necessary.
        if not cv.autoX:
            cva.set_xlim(float(sto["X Min"].text()),
                         float(sto["X Max"].text()))
        if not cv.autoY:
            cva.set_ylim(float(sto["Y Min"].text()),
                         float(sto["Y Max"].text()))
        if cv.threeD:  # set the z scale of the graph here
            cv.autoZ = sto["Auto Z"].isChecked()
            if len(fig.axes) > 0:       # if the figure contains axes
                if not cv.autoZ:
                    # set the clim of all images (including colorbar) of all
                    # axes
                    for axe in fig.axes:
                        for image in axe.get_images():
                            image.set_clim(
                                float(sto["Z Min"].text()), float(sto["Z Max"].text()))
                else:
                    zMin, zMax = cv.my_get_zlim()
                    for axe in fig.axes:
                        for image in axe.get_images():
                            image.set_clim(zMin, zMax)
            if cv.threeDAxes:
                cva.view_init(sto["Elevation"].value(), sto["Azimut"].value())
        # Don't modify xy autoscale or call draw here in this dialog. Call a
        # draw routine in the canvas itself
        cv.redraw()


class MyMplCanvas(FigureCanvas):

    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

    def __init__(self, parent=None, width=5, height=5, dpi=60, name=None, threeD=False, threeDAxes=False):

        fig = Figure(figsize=[width, height], dpi=dpi)
        FigureCanvas.__init__(self, fig)
        self._fig = fig
        self._width, self._height, self._dpi = width, height, dpi
        if name:
            self.name = name
        else:
            self.name = 'Figure'
        self.threeD = threeD
        self.threeDAxes = threeD and threeDAxes
        self.setParent(parent)
        self._dialog = None
        self._pressed = False

        # DV April 2014
        # In order to manage square plots such that xMax-xMin= yMax-yMin, we defines the following 4 variables
        # We don't use the matplotlib axes' properties to store the autorange configuration since they are incompatible with a square autorange
        # but the current x y limit are not stored here and are to be found in
        # the axes.
        self.squared = False
        self.centered = True
        self.axesLines = []
        self.autoX = True
        self.autoY = True
        if threeD:
            self.autoZ = True
        self.printer = QPrinter()
        # self.setFixedWidth(self._dpi*self._width)
        # self.setFixedHeight(self._dpi*self._height)

        # normally start with a normal 2D projection axes object for image plot
        self.createSubplot(threeDAxes=threeDAxes)

        self._isDrawing = False

        self._moveLabel = QLabel("", self)
        self._moveLabel.setText("tes")
        self._moveLabel.hide()
        self._moveLabel.setStyleSheet(
            "font-size:12px; margin:5px; padding:4px; background:#FFFFFF; border:2px solid #000;")
        # connect matplotlib events to functions
        self.mpl_connect('button_press_event', self.onPress)
        self.mpl_connect('button_release_event', self.onRelease)
        self.mpl_connect('motion_notify_event', self.onMove)
        self.mpl_connect('axes_leave_event', self.onLeave)
        self.mpl_connect('figure_leave_event', self.onLeave)
        self.mpl_connect('scroll_event', self.scroll)
        self.scrollable = [True, True]

        FigureCanvas.setSizePolicy(
            self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def createSubplot(self, number=1, threeDAxes=False):
        fig = self._fig
        fig.clf()
        if not threeDAxes:
            for i in range(number):
                self.axes = fig.add_subplot(111)
        else:
            for i in range(number):
                self.axes = fig.add_subplot(111, projection='3d')
        self.threeDAxes = threeDAxes
        self.axes.set_autoscale_on(True)
        self.axes.hold(True)
        self.draw()

    def square(self, xMinxMaxyMinyMaxList, centered=False):
        if centered:
            li = map(abs, xMinxMaxyMinyMaxList)
            m = max(li)
            return[-m, m, -m, m]
        else:
            xMin, xMax, yMin, yMax = xMinxMaxyMinyMaxList
            x = xMax - xMin
            y = yMax - yMin
            d = y - x
            if d > 0:
                xMin -= d / 2
                xMax += d / 2
            else:
                yMin += d / 2
                yMax -= d / 2
        return [xMin, xMax, yMin, yMax]

    def redraw(self):  # rescale and redraw according to the scaling parameters in the canvas and in the matplolib figure
        ax = self.axes
        # first recalculate the x and y limits with autoscale on the proper
        # axes if any;
        names = ['x', 'y']
        controls = [self.autoX, self.autoY]
        if self.threeD:
            tight = True
        else:
            tight = False
        # if self.threeD:
            # names.append('z')
            # controls.append(self.autoZ)
        #  tight=True
        ax.relim()
        map(lambda name, control: ax.autoscale(
            enable=control, axis=name, tight=tight), names, controls)
        # recalculate the xy limits
        ax.relim()
        if self.threeD:
            for im in ax.images:
                im.set_extent(im.get_extent())
                if self.autoZ:
                    im.autoscale()
        # Then if squared XY space
        if self.squared:
            xMin, xMax = ax.get_xlim()
            # read the calculated limits
            yMin, yMax = ax.get_ylim()
            # calculate the new ones in a squared space
            xMin, xMax, yMin, yMax = self.square(
                [xMin, xMax, yMin, yMax], centered=self.centered)
            ax.set_xlim(xMin, xMax)
            # set them in the matplolib axes
            ax.set_ylim(yMin, yMax)
            ax.autoscale(enable=False, axis='x')
            ax.autoscale(enable=False, axis='y')
            ax.set_aspect('equal', adjustable='box', anchor='C')
            if self.centered:
                # self.axesLines=[ax.axhline(y=0,color='k'),ax.axvline(x=0,color='k')]
                # # draw axes if centered
                None
        else:
            # and disable autoscale
            ax.set_aspect('auto', adjustable='box', anchor='C')
        # erase the x=0 and y=0 line if not squared and centered
        if not (self.squared and self.centered):
            for line in self.axesLines:
                # self.axesLines.remove(line)
                None  # del line
        # Finally, manage the z scale
        # and redraw in all cases
        self.draw()

    def title(self):
        return self.name

    def autoScale(self):
        self.autoX = True
        self.autoY = True
        if self.threeD:
            self.autoZ = True
        self.redraw()

    def my_get_zlim(self):
        # proprietary get_zlim that should combine get_zlim of 3DAxes (to be
        # done) with clim of images
        fig = self._fig
        zMin, zMax = 0, 1
        zMinList, zMaxList = [], []
        # take the min max of all the clim of all images except the colorbar in
        # the last axes
        for axe in fig.axes[:-1]:
            for image in axe.get_images():
                if self.autoZ:
                    image.autoscale()
                zMin, zMax = image.get_clim()
                zMinList.append(zMin)
                zMaxList.append(zMax)
        if len(zMinList) * len(zMaxList) > 0:
            zMin, zMax = min(zMinList), max(zMaxList)
        return zMin, zMax

    def zoomTo(self, rect):
        self.axes.set_xlim(rect.left(), rect.right())
        self.axes.set_ylim(rect.bottom(), rect.top())
        self.autoX = False
        self.autoY = False
        self.redraw()

    def toClipboard(self):
        pixmap = QPixmap.grabWidget(self)
        QApplication.clipboard().setPixmap(pixmap)

    def toPrinter(self):
        (w, h) = self.setScale(4, 6)
        dialog = QPrintDialog(self.printer)
        dialog.setModal(True)
        dialog.setWindowTitle("Print Document")
        dialog.addEnabledOption(QAbstractPrintDialog.PrintSelection)
        if dialog.exec_() == True:
            painter = QPainter(self.printer)
            xscale = self.printer.pageRect().width() / self.width()
            yscale = self.printer.pageRect().height() / self.height()
            scale = min(xscale, yscale)
            # self.printer.paperRect().y() +
            # self.printer.pageRect().height()/2)
            painter.translate(self.printer.paperRect().x() +
                              self.printer.pageRect().width() / 2, 0)
            painter.scale(scale, scale)
            painter.translate(-self.width() / 2, 0)  # -self.height()/2);

            self._moveLabel.hide()
            pixmap = QPixmap.grabWidget(self)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
        self.setScale(w, h)

    def scroll(self, event):
        ax = event.inaxes
        # get event location in pixel and data coordinates
        x, y, xd, yd = event.x, event.y, event.xdata, event.ydata
        if xd is not None and yd is not None:                           # in canvas == > zoom in or out
            if self.threeDAxes:
                xd, yd, zd = [
                    float(u[2:]) for u in event.inaxes.format_coord(xd, yd).split(', ')]
            cur_xlim = ax.get_xlim()
            cur_ylim = ax.get_ylim()
            cur_xrange = (cur_xlim[1] - cur_xlim[0]) * .5
            cur_yrange = (cur_ylim[1] - cur_ylim[0]) * .5
            if self.threeDAxes:
                pass
            if event.button == 'up':
                scale_factor = 1 / 1.3      # zoom in
            elif event.button == 'down':
                scale_factor = 1.3        # zoom out
            else:                                                   # deal with something that should never happen
                scale_factor = 1
                print "unknown even occured in zooming", event.button
            new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
            new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
            relx = (cur_xlim[1] - xd) / (cur_xlim[1] - cur_xlim[0])
            rely = (cur_ylim[1] - yd) / (cur_ylim[1] - cur_ylim[0])
            if(self.scrollable[0]):
                ax.set_xlim([xd - new_width * (1 - relx),
                             xd + new_width * (relx)])
            if(self.scrollable[1]):
                ax.set_ylim([yd - new_height * (1 - rely),
                             yd + new_height * (rely)])
        elif self.threeDAxes:
            inc = +5
            if event.button == 'down':
                inc = -5                       # outside canvas and 3D == > 3D rotate
            ax = self.axes
            elev, azim = ax.elev, ax.azim
            w, h = self.get_width_height()
            # scrolling  above half height of the axes == > elevation rotation
            if y > h / 2:
                elev += inc
            else:
                # scrolling below  == > azimutal rotation
                azim += inc
            ax.view_init(elev, azim)
        self.draw()

    def setScale(self, w, h):
        """
        Set size w,h
        Return previous size
        """
        (wOld, hOld) = self._fig.get_size_inches()
        self._fig.set_size_inches(w, h)
        return wOld, hOld

    def extraCode(self):
        return self._extraCode

    def setExtraCode(self, code):
        self._extraCode = code

    def execExtraCode(self):
        if self._extraCode is None:
            return
        lv = self.__dict__
        exec(self._extraCode, lv, lv)

    def onPress(self, event):
        if event.button == 1:
            if event.dblclick:
                self.showPropertyDialog()
            else:
                self._pressed = True
                self._pressEvent = event
                self._moveEvent = event

    def onRelease(self, event):
        if event.button == 1:
            self._pressed = False
            oldRect = QRectF()
            oldRect.setLeft(self.axes.get_xlim()[0])
            oldRect.setRight(self.axes.get_xlim()[1])
            oldRect.setBottom(self.axes.get_ylim()[0])
            oldRect.setTop(self.axes.get_ylim()[1])
            rect = QRectF()

            (x1, y1) = self.axes.transData.inverted().transform(
                [self._pressEvent.x, self._pressEvent.y])
            (x2, y2) = self.axes.transData.inverted(
            ).transform([event.x, event.y])

            rect.setLeft(min(x1, x2))
            rect.setRight(max(x1, x2))
            rect.setBottom(min(y1, y2))
            rect.setTop(max(y1, y2))
            if fabs(rect.width()) >= 0.01 * fabs(oldRect.width()) and fabs(rect.height()) >= fabs(0.01 * oldRect.height()):
                self.zoomTo(rect)

    def onMove(self, event):
        if not event.inaxes:
            self._moveLabel.hide()
            return
        elif not self._moveLabel.isVisible():
            self._moveLabel.show()
        if self._pressed:
            self._moveEvent = event
            self.update()
        if self.threeDAxes:
            x, y, z = [float(u[2:]) for u in event.inaxes.format_coord(
                event.xdata, event.ydata).split(', ')]
            st = "x=" + str(x) + "\ny=" + str(y) + "\nz=" + str(z)
        else:
            st = "x=" + str(event.xdata) + "\ny=" + str(event.ydata)
        self._moveLabel.setText(QString(st))
        self._moveLabel.adjustSize()
        offset = 10
        if self.width() - event.x < self._moveLabel.width():
            offset = -10 - self._moveLabel.width()
        self._moveLabel.move(event.x + offset, self.height() - event.y)

    def onLeave(self, e):
        if self._moveLabel.isVisible():
            self._moveLabel.hide()

    def mouseMoveEvent(self, e):
        try:
            FigureCanvas.mouseMoveEvent(self, e)
        except:
            pass

    def paintEvent(self, e):
        FigureCanvas.paintEvent(self, e)
        if self._pressed:
            painter = QPainter(self)
            painter.setPen(QPen(Qt.DotLine))
            (x1, y1) = self.figure.transFigure.inverted().transform(
                [self._pressEvent.x, self._pressEvent.y])
            (x2, y2) = self.figure.transFigure.inverted().transform(
                [self._moveEvent.x, self._moveEvent.y])
            painter.drawRect(x1 * self.width(), (1 - y1) * self.height(),
                             (x2 - x1) * self.width(), -(y2 - y1) * self.height())

    def onPaint(self, painter):
        print "painting..."

    def leaveEvent(self, e):
        FigureCanvas.leaveEvent(self, e)
        self._pressed = False
        self.update()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        fontSizeMenu = menu.addMenu("Graph fontsize")
        autoscaleAction = menu.addAction("Autoscale / Zoom Out")
        propertiesAction = menu.addAction("Graph properties...")
        menu.addSeparator()
        saveAsAction = menu.addAction("Save figure as PNG...")
        pdfAction = menu.addAction("Save and open figure as PDF...")
        menu.addSeparator()
        toClipboardAction = menu.addAction("Copy")
        toPrinterAction = menu.addAction("Print...")
        fontSizes = dict()
        for i in range(6, 16, 2):
            fontSizes[i] = fontSizeMenu.addAction("%d px" % i)

        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == saveAsAction:
            self.saveAs()
        elif action == pdfAction:
            self.openAndSaveAsPDF()
        elif action == propertiesAction:
            self.showPropertyDialog()
        elif action == toPrinterAction:
            self.toPrinter()
        elif action == toClipboardAction:
            self.toClipboard()
        elif action == autoscaleAction:
            self.autoScale()
        else:
            for fontSize in fontSizes.keys():
                if action == fontSizes[fontSize]:
                    print "Setting font size to %d" % fontSize
                    rcParams['font.size'] = str(fontSize)
                    self.draw()

    def showPropertyDialog(self):
        try:
            reload(sys.modules["application.ide.mpl.canvas"])
            from application.ide.mpl.canvas import CanvasDialog
        except ImportError:
            pass
        if not self._dialog is None:
            self._dialog.hide()
        self._dialog = CanvasDialog(self)
        self._dialog.setModal(False)
        self._dialog.show()

    def saveAs(self):
        filename = str(QFileDialog.getSaveFileName(self, "Save figure as", "",
                                                   "image (*.png, *.svg, *.pdf, *.emf, *.eps, *.pgf, *.ps, *.raw, *.rgba, *.svgz)"))
        if filename != '':
            self._fig.set_size_inches(self._width, self._height)
            self._fig.savefig(str(filename))

    def openAndSaveAsPDF(self):
        filename = str(QFileDialog.getSaveFileName(
            self, "Save and open figure as PDF", "", "PDF file (*.pdf)"))
        (w, h) = self._fig.get_size_inches()
        try:
            services = QDesktopServices()
            if filename != '':
                self._fig.set_size_inches(self._width, self._height)
                self._fig.savefig(str(filename))
                url = QUrl("file:///%s" % filename)
                services.openUrl(url)
        finally:
            self._fig.set_size_inches(w, h)
            self.draw()


class MatplotlibCanvas(MyMplCanvas):
    pass

""" Class module prefDialog.py defining the PrefAutoDialog class thet builds automatically a simple Qt modal dialog for specifying application's preferences."""

# Imports

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.uic import *

from application.lib.instrum_classes import *  # DEBUGGER

#********************************************
#  prefAutoDialog class
#********************************************


class PrefAutoDialog(QDialog, Debugger):
    """
    Class that builds automatically a simple Qt modal dialog for specifying application's preferences, from a preference dictionary passed to it.
    if no dictionary is passed but parent is passed and has a prefDict attribute, this  prefDict is used as the preference dictionnary.
    The syntax of the dictionnary should be {key:keyValue,...} where keyValue ={'label':label,'type':type,...} is type dependant:
        - boolean => keyValue ={'label':'my Boolean','type':bool,'value':True} => QCheckBox widget
        - int,long,double,complex,float => keyValue ={'label':'my Int','type':int,'value':5} => QLineEdit
        - 'multipleChoice' => keyValue ={'label':'my Choices','type':'multipleChoice','choices':[1,2,3],'value':1} => QComboBox widget
        - str or anything else => keyValue ={'label':'my String','type':str,'value':'string content'} => QLineEdit widget
    """

    def __init__(self, parent=None, prefDict=None):
        self._parent = parent
        QDialog.__init__(self, self._parent)
        self.setWindowTitle("DataManager frontend preferences")
        self.setMinimumWidth(300)
        l = QGridLayout()

        self._prefDict = prefDict
        if prefDict is None and parent is not None:
            if hasattr(parent, 'prefDict'):
                self._prefDict = getattr(parent, 'prefDict')

        self._widgetDict = {}

        # buid a simple representation of the preference dictionnary with
        # Qwidgets
        if self._prefDict:
            for key in self._prefDict:
                dicti = self._prefDict[key]
                typ = dicti['type']
                if typ == bool:  # QCheckBox
                    widget = QCheckBox(QString(dicti['label']))
                    widget.setChecked(dicti['value'])
                    l.addWidget(widget, l.rowCount(), 0)
                elif typ == 'multipleChoice':  # QComboBox
                    widget = QComboBox()
                    widget.addItems(
                        map(lambda x: QString(str(x)), dicti['choices']))
                    index = 0
                    while index < widget.count() and widget.itemText(index) != QString(str(dicti['value'])):
                        index += 1
                    widget.setCurrentIndex(index)
                    l.addWidget(
                        QLabel(QString(dicti['label'])), l.rowCount(), 0)
                    l.addWidget(widget, l.rowCount() - 1, 1)
                # put all other cases (int,long,double,complex,float) in
                # QLIneEdit widgets
                else:
                    widget = QLineEdit(QString(str(dicti['value'])))
                    l.addWidget(
                        QLabel(QString(dicti['label'])), l.rowCount(), 0)
                    l.addWidget(widget, l.rowCount() - 1, 1)
                self._widgetDict[key] = widget
        # end of build

        okButton = QPushButton("OK")
        cancelButton = QPushButton("Cancel")
        self.connect(okButton, SIGNAL("clicked()"), self.ok)
        self.connect(cancelButton, SIGNAL("clicked()"), self.cancel)
        l.addWidget(cancelButton, l.rowCount(), 0)
        l.addWidget(okButton, l.rowCount() - 1, 1)
        self.setLayout(l)

    def ok(self):
        # modify here the preference dictionnary from the widgets' states
        for key in self._widgetDict:
            widget, dicti = self._widgetDict[key], self._prefDict[key]
            typ = dicti['type']
            if typ == bool:  # QCheckBox
                dicti['value'] = widget.isChecked()
            elif typ == 'multipleChoice':  # QComboBox
                dicti['value'] = dicti['choices'][widget.currentIndex()]
            # put all other cases (int,long,double,complex,float) in QLIneEdit
            # widgets
            else:
                dicti['value'] = dicti['type'](widget.text())
        self.close()

    def cancel(self):
        # don't do anything and close
        self.close()

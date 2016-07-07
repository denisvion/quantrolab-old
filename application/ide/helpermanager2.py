"""
This module defines the HelperManager Class in charge of loading, unloading and keeping track of helpers loaded.
in Quantrolab.
It is itself loaded in a dedicated thread of the coderunner with thread id 'HelperManager'.
It instantiates all helpers in a child thread with a single QApplication, using coderunner_gui.
Like this the helper manager, he helpers and the scripts exist in the same Code process and can talk to each other.

"""
import os
import os.path
import sys
import imp
import inspect
import pyclbr
import time
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from ide.coderun.coderunner_gui import execInGui
from application.lib.helper_classes import Helper, HelperGUI

"""
from PyQt4.QtGui import QMainWindow
"""


class HelperManager(QApplication):
    """
    The helper manager has
        - a default helper root directory,
        - a dictionary _helpers for storing a reference to all open helpers:
    Its method loadHelpers can
            - prompt the user for the path to a helper file .pyh.
            - open a .pyh or .py helper file and look for all helpers in it.
            - run and memorize each helper by calling the runHelper() method,
    Its method runHelper
        - instantiates the helper in the QApplication using execingui
        - return a report
    The helper manager memorizes information about the loaded helpers in a dictionary _helpers, the structure of which is:
     # {classname: {'helper':classname,'helperPath':filename,'helperType':helperType,
     #              'associate':associateName,'associatePath':associatePath,'associateType':associateType},...}
    """

    def __init__(self, helpersRootDir=None):
        QApplication.__init__(self, sys.argv)
        if helpersRootDir is None:
            helpersRootDir = os.getcwd()
        self._helpersRootDir = helpersRootDir
        self._helpers = {}

    def helpers(self):
        return self._helpers			# return the helper directory

    def loadHelpers(self, filename=None):
        """
        The loadHelpers method tries to load and run all HelperGUI(s) and Helper(s) defined in a single python module
        specified by:
        - either filename if it is not None;
        - or from an open file dialog box if filename is None.
                Note that the open file dialog box will propose only files with extension '.pyh' (python helper);
                        => always have an empty .pyh file with the same name as the .py module containing the helper(s).

        A specified filename can have either extension .py or a .pyh.

        If a valid .py file is found:
            1) all classes inheriting from HelperGUI or Helper are found in the file;
            All gui helpers HelperGui will be treated before non-gui helpers Helper:
            2) If no helper with the same class name is already loaded, it is run;
            3) If run is sucessful, the helper is added to the helper dictionary _helpers if not already present;
            4) a global variable is created for the helper.
            5) if the helper has an associate, it is indicated in the helper dictionnary.
            6) If the associate is non-gui it is removed from the dictionary keys and appears only as an associate
            of the gui helper
            7) a global variable with the name of the associate is created;
            8) the _helpers dictionary is saved in the QSettings, for automatic reloading of helpers at IDE starting.
            9) Finally, the helperMenu is rebuild from the _helpers dictionary.
        """
        # Build the .py filename of the helper module and read the module
        print 'in loadHelpers'
        if filename is None:
            filename = str(QFileDialog.getOpenFileName(caption='Open Quantrolab helper',
                                                       filter="helper (*.pyh)", directory=self._helpersRootDir))
        return
        if not filename:
            return
        if os.path.isfile(filename):
            dirpath, basename = os.path.split(filename)
            name, ext = os.path.splitext(basename)
            # builds or rebuilds fullname with .py extension (don't use join to avoid \x special characters )
            pyFilename = dirpath + '/' + name + '.py'
        if not os.path.isfile(pyFilename):
            print "Error: could not find a file " + pyFilename + '.'
            return
        try:
            # dic will contain all classes AND subclasses in the module
            dic = pyclbr.readmodule(name, [dirpath])
        except:
            print 'Error:', sys.exc_info()[0]
            raise
        newHelpers = [[], []]
        # Find all helpers and helperGUIs in the helper module and put their class
        # names in temporary list newHelpers
        for targetBaseclass, helperList in zip(['HelperGUI', 'Helper'], newHelpers):
            if targetBaseclass in dic:
                for key in dic:
                    classes = dic[key].super
                    for cl in classes:
                        if (isinstance(cl, str) and cl == targetBaseclass) or (isinstance(cl, pyclbr.Class) and cl.name == targetBaseclass):
                            helperList.append(key)
        if newHelpers == [[], []]:
            print "Error: could not find a Helper or HelperGUI class in file " + pyFilename + '.'
        # Treat each HelperGUI and then each Helper
        for helpers, associateAttr, associateTypeName in zip(newHelpers, ['_helper', '_gui'], ['Helper', 'HelperGUI']):
            for key in helpers:
                # if a helper with the same name is not already present in the helper dictionary
                load = (key not in self._helpers) and key not in [dic['associate'] for k, dic in self._helpers.items()]
                if load:
                    self.runHelper(name, pyFilename, key, associateAttr, associateTypeName, 'lastHelper')
                else:
                    print 'Helper ' + key + ' already loaded. Close before reloading if necessary.'
        # print 'helpers dic = ', self._helpers

    def runHelper(self, modulename, filename, classname, associateAttr, associateTypeName, reportname, timeout=10):
        """
        This method runs a Helper by calling
        execInGui(lambda : startHelper(modulename,filename,classname,associateAttr,associateTypeName,reportname)
        """
        params = (modulename, filename, classname, associateAttr, associateTypeName, reportname)
        execInGui(lambda: startHelper('%s', '%s', '%s', '%s', '%s', '%s'), nameIfNew='Quantrolab helpers') % params

    def startHelper(modulename, filename, classname, associateAttr, associateTypeName, reportname):
        global helpers
        try:
            # import the module containing the helper
            module = imp.load_source(modulename, filename)
        except:
            print 'Error loading %s.' % filename
            raise
        try:
            # instantiate the helper with class name classname with gv as global variables
            helper = getattr(module, classname)(parent=None, globals=gv)
            # If it is a Qt window (HelperGUI)
            if isinstance(helper, QMainWindow):
                helper.show()  # show it
        except:
            print 'Error in loading ' + classname + '.'
            raise
        self._helpers.update({classname: helper})
        helpers.append(classname)
        print 'exiting startHelper with self._helpers = ', self._helpers


def startHelperManager():
    helperManager = HelperManager()

if __name__ == '__main__':
    startHelperManager()

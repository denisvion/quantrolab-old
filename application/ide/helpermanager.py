"""
This module defines the HelperManager Class in charge of loading, unloading and keeping track of helpers loaded
in Quantrolab.

A series of helpers loaded from a single python file is run in its own thread of the codeRunner's code process,
and share the same global variables as the scripts.
The helpers are referenced in this global variable namespace to be used by the script.

Nevertheless, since only one Qt application can exist by code process, coderunner_gui is used to group all helpers
and helpers_gui in a single QThread of the codeRunner's code process.
"""
import sys
import inspect
import os.path
import pyclbr
import time
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from ide.coderun.coderunner_gui import execInGui
import time


def startHelper(modulename, filename, classname, associateAttr, associateTypeName, reportname):
    import imp
    import inspect
    from PyQt4.QtGui import QMainWindow
    from application.lib.helper_classes import Helper, HelperGUI
    global helper  # make the helper variable global
    """
    if reportname in gv.__dict__:
        del gv.__dict__[reportname]
    """
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
        """# keep a reference to the helper in gv
        gv[classname] = helper
        # inform user
        print 'Helper %s loaded and accessible as gv.%s.' % (classname, classname)
        if isinstance(helper, HelperGUI):
            helperType = 'HelperGUI'
        elif isinstance(helper, Helper):
            helperType = 'Helper'
        """
    except:
        print 'Error in loading ' + classname + '.'
        raise
    print 'exiting startHelper with helper = ', helper
    """
    associatePath, associateName, helperType, associateType = None, None, None, None
    try:
        # Check if an associate exists (Helper for a HelperGUI or vice and versa)
        if hasattr(helper, associateAttr):                            # if an associate exists
            associate = getattr(helper, associateAttr)
            if isinstance(associate, eval(associateTypeName)): 		  # and is loaded,
                associatePath = inspect.getfile(associate.__class__)  # get information about it
                associateName = associate.__class__.__name__
                # keep a reference to the associate in gv
                gv[associateName] = associate
                # and inform user
                print 'Associate helper ' + associateName + ' loaded and accessible as gv.' + associateName + '.'
                if isinstance(associate, HelperGUI):
                    associateType = 'HelperGUI'
                elif isinstance(associate, Helper):
                    associateType = 'Helper'
    except:
        print "Error when looking for " + classname + "'s associate or when loading it."
        raise
    # information about the loaded helpers is temporarily stored in a dictionary lastHelpers put in gv for the IDE
    # force a non GUI helper to be the associate of a GUI helper
    if associateType == 'helperGUI' and helperType == 'helper':
        gv[reportname] = {'helper': associateName, 'helperPath': associatePath, 'helperType': associateType,
                          'associate': classname, 'associatePath': filename, 'associateType': helperType}
    else:
        gv[reportname] = {'helper': classname, 'helperPath': filename, 'helperType': helperType,
                          'associate': associateName, 'associatePath': associatePath, 'associateType': associateType}
    """


class HelperManager():
    """
    The helper manager has
        - a parent (the Quantrolab IDE),
        - a handle to the codeRunner,
        - the thread id of a unique codeRunner thread dedicated to all helpers
        - a default helper root directory,
        - a dictionary _helpers for storing a reference to all open helpers:
    Its method loadHelpers can
            - prompt the user for the path to a helper file .pyh.
            - open a .pyh or .py helper file and look for all helpers in it.
            - run and memorize each helper by calling the runHelper() method,
    Its method runHelper
        - builts and executes a script in the codeRunner's thread with id 'Helpers',
        - return a report
    The helper manager memorizes information about the loaded helpers in a dictionary _helpers, the structure of which is:
     # {classname: {'helper':classname,'helperPath':filename,'helperType':helperType,
     #              'associate':associateName,'associatePath':associatePath,'associateType':associateType},...}
    """

    def __init__(self, codeRunner, parent=None, helpersRootDir=None):
        self._parent = parent
        self._helpers = {}
        if helpersRootDir is None:
            helpersRootDir = sys.gcwd()
        self._helpersRootDir = helpersRootDir
        self._codeRunner = codeRunner  # handle to codeRunner to execute code
        self._threadID = 'Helpers'
        # code used to lauch a new series of helpers ...
        self._code = 'global helpers\nhelpers={}\n'     # ...starts with the declaration of the global variable helpers,
        self._code += inspect.getsource(startHelper)    # continues withe the definition of startHelper() above...
        # and continues with the import of execingui().
        self._code += '\nfrom ide.coderun.coderunner_gui import execInGui\n'
        # the script will be terminated execingui(starthelper(params)) when params are knonw from loadhelpers
        codeRunner.executeCode('helpers={}\n', identifier=self._threadID, filename='IDE')

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
        if filename is None:
            filename = str(QFileDialog.getOpenFileName(caption='Open Quantrolab helper',
                                                       filter="helper (*.pyh)", directory=self._helpersRootDir))
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
        This method runs a Helper by calling self._execute(code) with code including:
            - the definition of the startHelper() function in this module
            - execInGui(lambda : startHelper(modulename,filename,classname,associateAttr,associateTypeName,reportname)
        The code is executed in the CodeProcess shared by the scripts.
        """
        if self._codeRunner is None:
            print 'No codeRunner available for running helpers'
            return
        params = (modulename, filename, classname, associateAttr, associateTypeName, reportname)
        # print 'in runHelper(%s, %s, %s, %s, %s, %s)' % params
        code = self._code
        code += "execInGui(lambda : startHelper('%s','%s','%s','%s','%s','%s'),nameIfNew='Quantrolab helpers')" % params
        # print 'Trying to Launch %s' % classname
        # Note that we use classname as the thread id
        self._codeRunner.executeCode(code, identifier=self._threadID, filename='IDE')
        t0 = time.time()
        # wait for the thread to finish code execution
        while self._codeRunner.isExecutingCode(identifier=self._threadID) and time.time() - t0 < timeout:
            pass
        while time.time() - t0 < timeout:
            print 'waiting for helper to be loaded by execingui'
            self._codeRunner.executeCode("print 'helper = ', helper", identifier=self._threadID, filename='IDE')
        """
        if time.time() - t0 < timeout:
            helperId = self.helperId(threadId)
            if helperId:
                self._helpers.update({threadId: helperId})
        """

    def helperId(self, threadId):
        varname = 'helperId_' + threadId
        code = 'gv.%s = None\ntry:\n\tgv.%s = id(helper)\nexcept:\n\tpass\nprint helper, id(helper), gv.%s' % (
            varname, varname, varname)
        print '*******************'
        print code
        print '*******************'
        print threadId
        self._codeRunner.executeCode(code, identifier=threadId, filename='IDE')
        print self._codeRunner.gv(varname)
        return self._codeRunner.gv(varname)

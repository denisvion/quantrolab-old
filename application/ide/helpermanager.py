"""
This module defines the HelperManager Class in charge of loading, unloading and keeping track of helpers loaded.
in Quantrolab.
It is itself loaded in a dedicated thread of the coderunner with thread id 'HelperManager'.
It instantiates all helpers in a child thread with a single QApplication, using coderunner_gui.
Like this the HelperManager, the helpers and the scripts loaded in Quantrolab exist in the same process,
can talk to each other, and share the same global memory.
(Read the docstring of application.lib.helper_classes to understand helpers design in QuantroLab.)
"""
import os
import os.path
import sys
import imp
import inspect
import pyclbr
import time
import gc

import threading
from threading import Thread

from application.lib.base_classes1 import Debugger
from application.lib.helper_classes import Helper, HelperGUI
from application.lib.com_classes import Observer
from PyQt4.QtGui import QMainWindow
from ide.coderun.coderunner_gui import execInGui


class HelperManager(Observer, Debugger):
    """
    The HelperManager runs a set of GUI and non-GUI helpers in a separate and single Qt thread.
    (This choice is made because only one Qt application is allowed per process).
    In Quantrolab, this HelperManager is run in the CodeProcess of the MultiProcessCodeRunner, so that all helpers share
     the same memory as the scripts' threads.
    Although the thread running the HelperManager is visible in Quantrolab, the Qt thread beside is invisible.
    The HelperManager properties are
        - a default helper root directory, returned by the method helpersRootDir()
        - a dictionary _helpers of all open helpers, returned by the method helpers()
    In addition, the HelperManager has a public method loadHelpers, which can:
            - prompt the user for the path to a helper file .pyh ;
            - open a .pyh or .py helper file and look for all helpers classes in it ;
            - memorize each helper and run it.
    Note that in Quantrolab, the prompt for a helper's filename is done directly by the IDE and not by the
    HelperManager, for a good display of the 'open file' dialog box.

    The dictionary _helpers has the following structure:
    {helperName: {'helper':helperObject,'helperPath':filename,'helperType':helperType,'associateName':associateName,
        'associatePath':associatePath,'associateType':associateType,'associate':associateObject},...}
    with helperName the name of its class.
    """

    def __init__(self, helpersRootDir=None, gv=None):
        """
        HelperManager creator
        """
        Observer.__init__(self)
        Debugger.__init__(self)
        if helpersRootDir is None:
            helpersRootDir = os.getcwd()
        self._gv = gv
        self._helpersRootDir = helpersRootDir
        self._helpers = {}

    def helpersRootDir(self):
        """
        Returns the root directory for helpers.
        """
        return self._helpersRootDir

    def helpers(self, update=False, strRepr=False):
        """
        Returns a copy of the dictionary of loaded helpers.
        if update=true, calls the _updateHelperDic function to remove helpers that are no longer in memory;
        if strRepr = True, the helper objects (helper and possibly its associate) are replaced by their string
        representation (interesting for interprocess communication).
        """
        helpersCopy = dict(self._helpers)
        if strRepr:        # change the helpers object into their string representation
            for key, item in helpersCopy.iteritems():
                item['helper'] = str(item['helper'])
                if 'associate' in item:
                    item['associate'] = str(item['associate'])
        return helpersCopy

    def _updateHelperDic(self):
        """
        Removes from the _helpers dictionary helpers and associates that are no longer present in memory.
        """
        for helperName in self._helpers:
            helperDic = self._helpers[helperName]
            try:
                x = helperDic['helper']
                # no error occured => keep the helper and check the associate
                if 'associate' in helperDic:            # check for associate
                    try:
                        y = helperDic['associate']
                    except:                             # error occured => associate no longer in memeory
                        helperDic['associate'] = None
            except:                                     # an eror occured because the helper is no longer in memory
                if 'associate' in helperDic:            # check for associate
                    try:
                        y = helperDic['associate']
                        # no error occured => there is an associate to the helper => copy it before deleting
                        newName = helperDic['associateName']
                        helper = helperDic['associate']
                        filename = helperDic['associatePath']
                        helperType = helperDic['associateType']
                        # copy to a new item in the top dictionnary
                        self._helpers[newName] = {'helper': helper, 'helperPath': filename, 'helperType': helperType}
                    except:
                        pass
                self._helpers.pop(helperName)           # removes absent helper
        self.debugPrint('exiting _updateHelperDic with _helpers = ', self._helpers)

    def updated(self, subject=None, property=None, value=None):
        """
        Function called when receiving notificatons from a Subject.
        """
        self.debugPrint('in HelperManager.updated() with (subject, property, value) = ', (subject, property, value))
        if property == 'closing':
            self._updateHelperDic()
            """print sys.getrefcount(subject), 'references:'
            for ref in gc.get_referrers(subject):
                print ref
            """

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
            5) if the helper has an associate, it is indicated in the helper dictionary.
            6) If the associate is non-gui it is removed from the dictionary keys and appears only as an associate
            of the gui helper
            7) a global variable with the name of the associate is created;
            8) the _helpers dictionary is saved in the QSettings, for automatic reloading of helpers at IDE starting.
        """
        # Build the .py filename of the helper module and read the module
        if filename is None:
            filename = str(QFileDialog.getOpenFileName(caption='Open Quantrolab helper',
                                                       filter="helper (*.pyh)", directory=self._helpersRootDir))
        if not filename:
            return
        if os.path.isfile(filename):
            dirpath, basename = os.path.split(filename)
            modulename, ext = os.path.splitext(basename)
            # builds or rebuilds fullname with .py extension (don't use join to avoid \x special characters )
            pyFilename = dirpath + '/' + modulename + '.py'
        if not os.path.isfile(pyFilename):
            print "ERROR: could not find a file " + pyFilename + '.'
            return
        try:
            # dic will contain all classes AND subclasses in the module
            dic = pyclbr.readmodule(modulename, [dirpath])
        except:
            print 'ERROR:', sys.exc_info()[0]
            raise
        # Find all helperGUIs and helpers  in the helper module and put their class names in temporary list newHelpers
        newHelpers = [[], []]                           # [[HelperGUIs], [Helpers]]
        for targetBaseclass, helperList in zip(['HelperGUI', 'Helper'], newHelpers):
            if targetBaseclass in dic:
                for key in dic:
                    classes = dic[key].super
                    for cl in classes:
                        if (isinstance(cl, str) and cl == targetBaseclass) or (isinstance(cl, pyclbr.Class) and cl.name == targetBaseclass):
                            helperList.append(key)
        if newHelpers == [[], []]:
            print "ERROR: could not find any Helper or HelperGUI class in file " + pyFilename + '.'
        # Treat each HelperGUI and then each Helper: load them if necessary
        for helpers, associateAttr, associateTypeName in zip(newHelpers, ['_helper', '_gui'], ['Helper', 'HelperGUI']):
            for classname in helpers:
                # load the helper if a helper with the same name is not already present in the _helpers dictionary
                # (as a helper or its associate)
                #   Reminder: each _helpers item has the structure
                #   helperName: {'helper':helperObject,'helperPath':filename,'helperType':helperType} or
                #   helperName: {'helper':helperObject,'helperPath':filename,'helperType':helperType,
                #               'associateName':associateName,'associatePath':associatePath,
                #               'associateType':associateType,'associate':associateObject}
                associates = [dic['associateName'] for k, dic in self._helpers.items() if 'associateName' in dic]
                load = (classname not in self._helpers) and classname not in associates
                if load:
                    params = (modulename, pyFilename, classname, associateAttr, associateTypeName)
                    execInGui(lambda: self._startHelper(*params))
                else:
                    print 'WARNING: Helper ' + key + ' already loaded. Close before reloading if necessary.'
        # print 'helpers dic = ', self._helpers

    def _startHelper(self, modulename, filename, classname, associateAttr, associateTypeName):
        """
        This private method
         - instantiates a helper of class classname from a module modulename at location filename,
         with a possible associate associateAttr of type associateTypeName.
         - updates the _helpers dicitonnary by
            * adding an item
              helperName: {'helper':helperObject,'helperPath':filename,'helperType':helperType} or
              helperName: {'helper':helperObject,'helperPath':filename,'helperType':helperType,
              'associateName':associateName,'associatePath':associatePath,'associateType':associateType,
              'associate':associateObject}
            * possibly removing the item associate that was already loaded without its master helper
        """
        try:                                            # import the module containing the helper
            module = imp.load_source(modulename, filename)
        except:
            print 'ERROR loading %s.' % filename
            raise
        try:
            helper = getattr(module, classname)()       # instantiate the helper with class name classname
            helper.attach(self)                         # the helper will notify when it closes
            if isinstance(helper, HelperGUI):
                helperType = 'HelperGUI'
            elif isinstance(helper, Helper):
                helperType = 'Helper'
            if isinstance(helper, QMainWindow):         # If it is a Qt window (HelperGUI), show it
                helper.show()
            self._helpers[classname] = {'helper': helper, 'helperPath': filename, 'helperType': helperType}
            self._gv[classname] = helper             # keep a reference to the helper in gv and inform user
            print 'Helper %s loaded and accessible as gv.%s.' % (classname, classname),
        except:
            print 'ERROR in loading ' + classname + '.'
            raise
        try:                        # Check if an associate has been loaded (Helper for a HelperGUI or vice and versa)
            associatePath, associateName, helperType, associateType = None, None, None, None
            if hasattr(helper, associateAttr):                            # if an associate exists
                associate = getattr(helper, associateAttr)
                if isinstance(associate, eval(associateTypeName)): 		  # and is loaded,
                    associatePath = inspect.getfile(associate.__class__)  # get information about it
                    associateName = associate.__class__.__name__          # keep a reference to the associate in gv
                    self._gv[associateName] = associate                   # and inform user
                    if isinstance(associate, HelperGUI):
                        associateType = 'HelperGUI'
                    elif isinstance(associate, Helper):
                        associateType = 'Helper'
                    info = {'associateName': associateName, 'associatePath': associatePath,
                            'associateType': associateType, 'associate': associate}
                    self._helpers[classname].update(info)
                    if associateName in self._helpers:
                        self._helpers.pop(associateName)
                    print ' (associate helper ' + associateName + ' loaded and accessible as gv.' + associateName + ')'
                else:
                    print
        except:
            print "Error when looking for " + classname + "'s associate or when loading it."
            raise


def startHelperManager():
    helperManager = HelperManager()

if __name__ == '__main__':
    startHelperManager()

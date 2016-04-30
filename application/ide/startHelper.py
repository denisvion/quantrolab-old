"""
This file is not a stand-alone python module.
It contains a script used by the Quantrolab IDE to start a helper.
More precisely the IDE executes it in the coderunner child process rather than in the IDE main process.
Like this, helpers are run in the same code process and share the same global variables as the scripts
(and are referenced in this global variable namespace).
WARNING: This script is NOT stand-alone:
    it will work only if module, file, class, associate attribute and associate type variables
    (mn,fn,cn,aa,at) have been defined before running it.
"""
import imp
import inspect
import os.path
from PyQt4.QtGui import QMainWindow
from application.lib.helper_classes import *
from ide.coderun.coderunner_gui import execInGui

if rn in gv.__dict__:
    del gv.__dict__[rn]


def startHelper(modulename, filename, classname, associateAttr, associateTypeName, reportName):
    associatePath, associateName, helperType, associateType = None, None, None, None
    try:
        # import the module containing the helper
        module = imp.load_source(modulename, filename)
    except:
        print 'Error loading ' + filename + '.'
        raise
    try:
        global helper
        # instantiate the helper with class name classname with gv as global
        # variables
        helper = getattr(module, classname)(parent=None, globals=gv)
        if isinstance(helper, QMainWindow):					  		# If it is a Qt window (HelperGUI)
            helper.show()  # show it
        # keep a reference to the helper in gv
        gv[classname] = helper
        print 'Helper', classname, ' loaded, and accessible as gv.', classname, '.'  # inform user
        if isinstance(helper, HelperGUI):
            helperType = 'HelperGUI'
        elif isinstance(helper, Helper):
            helperType = 'Helper'
    except:
        print 'Error in loading ' + classname + '.'
        raise
    try:
        # Check if an associate exists (Helper for a HelperGUI or vice and
        # versa)
        if hasattr(helper, associateAttr):
            associate = getattr(helper, associateAttr)
            if isinstance(associate, eval(associateTypeName)): 		# and is loaded,
                associatePath = inspect.getfile(associate.__class__) 	# get information about it
                associateName = associate.__class__.__name__
                # keep a reference to the associate in gv
                gv[associateName] = associate
                # and inform user
                print 'Associate helper ' + associateName + ' loaded and accessible as gv.' + associateName
                if isinstance(associate, HelperGUI):
                    associateType = 'HelperGUI'
                elif isinstance(associate, Helper):
                    associateType = 'Helper'
    except:
        print "Error when looking for " + classname + "'s associate or when loading it."
        raise
    # information about the loaded helpers is temporarily stored in a
    # dictionary lastHelpers put in gv for the IDE
    # force a non GUI helper to be the associate of a GUI helper
    if associateType == 'helperGUI' and helperType == 'helper':
        gv[rn] = {'helper': associateName, 'helperPath': associatePath, 'helperType': associateType,
                  'associate': classname, 'associatePath': filename, 'associateType': helperType}
    else:
        gv[rn] = {'helper': classname, 'helperPath': filename, 'helperType': helperType,
                  'associate': associateName, 'associatePath': associatePath, 'associateType': associateType}
    # print gv[rn]

execInGui(lambda: startHelper(mn, fn, cn, aa, at, rn))

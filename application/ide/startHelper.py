"""
This file is not a stand-alone python module.
It contains a script used by the Quantrolab IDE to start a helper.
More precisely the IDE executes it in the coderunner child process rather than in the IDE main process.
Like this, helpers share the same global variables as the scripts (and are referenced in this global variable namespace).
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

if rn in gv.__dict__: del gv.__dict__[rn]

def startHelper(modulename,filename,classname,associateAttr,associateTypeName,reportName):
	associatePath,associateName,helperType,associateType=None,None,None,None
	try:
		module=imp.load_source(modulename,filename)			  # import the module containing the helper
	except:
		print 'Error loading ' + filename+'.'
		raise
	try:
		global helper
		helper=getattr(module,classname)(parent=None,globals=gv)		  # instantiate with gv as global variables
		if isinstance(helper,QMainWindow):					  # If it is a Qt window (HelperGUI)
			helper.show()									  #	  show it
		gv[classname]=helper 							      # keep a reference to the helper in gv
		print 'Helper',classname,' loaded, and accessible as gv.', classname,'.' # inform user
		if isinstance(helper,HelperGUI) : helperType = 'HelperGUI'
		elif isinstance(helper,Helper) : helperType = 'Helper'
	except:
		print 'Error in loading ' + classname +'.'
		raise
	try:
		if hasattr(helper,associateAttr):                     # Check if an associate exists (Helper for a HelperGUI or vice and versa)
			associate=getattr(helper,associateAttr)
			if isinstance(associate,eval(associateTypeName)): # and is loaded,
				associatePath=inspect.getfile(associate.__class__) # get information about it
				associateName=associate.__class__.__name__
				gv[associateName]=associate 				  # keep a reference to the associate in gv
				print 'Associate helper '+ associateName + ' loaded and accessible as gv.'+associateName # and inform user
				if isinstance(associate,HelperGUI) : associateType = 'HelperGUI'
				elif isinstance(associate,Helper) : associateType = 'Helper'
	except:
		print "Error when looking for "+classname+"'s associate or when loading it."
		raise
	# information about the loaded helpers is temporarily stored in a dictionary lastHelpers put in gv for the IDE
	if associateType == 'helperGUI' and helperType == 'helper':
		gv[rn]={'helper':associateName,'helperPath':associatePath,'helperType':associateType,'associate':classname,'associatePath':filename,'associateType':helperType}
	else:
		gv[rn]={'helper':classname,'helperPath':filename,'helperType':helperType,'associate':associateName,'associatePath':associatePath,'associateType':associateType}
	#print gv[rn]

execInGui(lambda : startHelper(mn,fn,cn,aa,at,rn))

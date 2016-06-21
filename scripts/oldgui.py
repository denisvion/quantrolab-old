import matplotlib
matplotlib.use('module://pyview.gui.mpl.backend')

from ide.coderun.coderunner_gui import execInGui
from helpers.datamanager.datamanager_gui.datamgr_gui import DataManager

def startHelpers():
	"""
	Start helpers' frontpanels,
	and store a handle to their backend manager (if it exists) in the global variable context gv.
	"""
	global dataManagerPanel
	dataManagerPanel= DataManager(globals = gv)	# instantiate both data manager and its frontend
	dataManagerPanel.show()								# show all helper panels
	gv['dataManager']=dataManagerPanel.manager

execInGui(startHelpers)

##
## For debugging only
# get a handle to the datamanager frontend in the scripts
#gv.dataManagerPanel=dataManagerPanel
#dataManager=dataManagerPanel.manager
#gv.dataManager=dataManager
	
# put the different modules in debug mode if necessary
#dataManagerPanel.debugOn() # this is the GUI
#dataManager.debugOn()
	
# manager.plotters2D[0].debugOn() # first 2D plotter
#manager.plotters3D[0].debugOn() # first 3D plotter
# for each datacube you want to debug in your scripts => cube.debugOn()
	
##
#dataManagerPanel.cubeList.debugOn()
import imp
from ide.coderun.coderunner_gui import execInGui
from application.lib.helper_classes import *


def startHelper(pyFileName, modulename, classname):
    module = imp.load_source(modulename, pyFileName)
    global dataManager
    dataManager = getattr(module, classname)()
    dataManager.show()
    gv['dataManager'] = dataManager


pyFileName = '//quantro-room4/room4-labo/lab_control/QuantroLab/application/helpers/datamanager/datamanager_gui\datamgr_gui.py'
modulename = "datamgr_gui"
classname = 'DataManager'

execInGui(lambda: startHelper(pyFileName, modulename, classname))
# startHelper(pyFileName,modulename,classname)

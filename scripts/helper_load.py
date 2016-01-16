import imp
from ide.coderun.coderunner_gui import execInGui
from application.lib.helper_classes import *


def startHelper():
    pyFileName = '//quantro-room4/room4-labo/lab_control/QuantroLab/application/helpers/datamanager/datamanager_gui\datamgr_gui.py'
    modulename = "datamgr_gui"
    classname = 'DataManager'
    module = imp.load_source(modulename, pyFileName)
    global datamanager
    datamanager = getattr(module, classname)()
    print datamanager, isinstance(datamanager, (HelperGUI))
    if isinstance(datamanager, (HelperGUI)):
        datamanager.show()
    gv.datamanager = datamanager

execInGui(startHelper)

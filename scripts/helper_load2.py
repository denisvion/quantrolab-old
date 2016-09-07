from ide.coderun.coderunner_gui import execInGui
from application.helpers.instrumentmanager.instrumentmgr_gui import InstrumentManager

def start():
	global InstrumentManager
	instrumentManager= InstrumentManager()
	instrumentManager.show()

execInGui(start)
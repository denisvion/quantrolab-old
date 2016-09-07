from PyQt4.QtGui import QMainWindow
from PyQt4.QtCore import Qt

class B(QMainWindow,object):
	def __init__(self):
		QMainWindow.__init__(self)
		self.setAttribute(Qt.WA_DeleteOnClose)
		self.show()
			
def startQMain(name):
	b =  B()
	b.name = name
	b.setWindowTitle(name)
	b.show()
	gv[name] = b
	
from ide.coderun.coderunner_gui import execInGui

##
execInGui(startQMain,'myB6')
##
print gv.myB6.name
##
import sys
print sys.getrefcount(gv.LoopMgr)
##
import gc
##
refs = gc.get_referrers(gv.LoopMgr)
print len(refs), ' references to ',gv.LoopMgr
for ref in refs:
	print ref
	
##
print gv.LoopMgr._instance	
gv.LoopMgr.delete()
print gv.LoopMgr._instance	
##
class Singleton(object):
    """
    A class deriving from this abstract class can have only one instance in Python memory.
    """
    _instance = None

    def delete(self):
    	print 'in delete'
        self._instance = None
        print _instance

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Singleton, cls).__new__(cls)
        return cls._instance
        
    def __del__(self):
    	print 'in del'
 
##
import gc	
myC= Singleton()
refs = gc.get_referrers(myC)
print len(refs)
for ref in refs:
	print
	print ref
	print
print dir()
myC.delete()
gc.collect()
refs = gc.get_referrers(myC)
print len(refs)
del myC
print dir()
##
myC.delete()
print myC._instance

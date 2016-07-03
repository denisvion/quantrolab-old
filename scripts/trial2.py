from PyQt4.QtGui import QApplication, QMainWindow
from ide.coderun.coderunner_gui import execInGui
import weakref
global a, window

a=0

def f():
	global a, window
	a=2
	window=QMainWindow()
	window.show()
execInGui(f,'toto')

##
print window
print a

##
app = QApplication.instance()
print str(app.applicationName())
print a
print app.allWindows()
##
b = weakref.proxy(window)
##
window=None
##
print window
window.show()
print b
##
print dir(app)
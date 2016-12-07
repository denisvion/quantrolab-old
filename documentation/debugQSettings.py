from PyQt4.QtCore import *
from PyQt4.QtGui import *
settings= QSettings()
##
keys=str(settings.allKeys().join(',')).split(',')
print keys
settings2={key:settings.value(key) for key in keys}
print settings2
##
print type(settings.value('pos'))
qpoint = settings.value('pos')
print qpoint.convert(QPoint)
x,y = qpoint.x(), qpoint.y()
print x,y
##
settings.remove('pos')
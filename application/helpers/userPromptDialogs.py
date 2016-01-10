
"""
Utility module with two functions 'userAsk' and 'userAskValue' defining Qt dialog boxes for user prompting.
"""
import sys
import os,os.path
import time

from PyQt4.QtGui import * 
from PyQt4.QtCore import *

from application.lib.base_classes1 import KillableThread

def timeOutFunction(t,qt):
  for i in range(0,t*10):
  	time.sleep(0.1)
  try:
  	qt.close()
  	print "userAsk : timeOut --> closing"
  except:
  	raise
  
def userAsk(message,title="None",timeOut=10,defaultValue=False):
  myMessageBox = QMessageBox()
  if title != "None":
    myMessageBox.setWindowTitle("Warning!")
  myMessageBox.setText(str(message))
  yes = myMessageBox.addButton("Yes",QMessageBox.YesRole)
  no = myMessageBox.addButton("No",QMessageBox.NoRole)
  cancel=myMessageBox.addButton("Cancel",QMessageBox.RejectRole)
  print "Action requested : %s"%str(message)

  t=KillableThread(target=timeOutFunction,args=(timeOut,myMessageBox,))
  t.start()

  myMessageBox.exec_()
  choice = myMessageBox.clickedButton()
  t.terminate()
  
  if choice == no:
    return False
  elif choice == yes:
    return True  
  else :
    return defaultValue
    
def userAskValue(message,title="Warning!"):
  answer,bool = QInputDialog().getText(QInputDialog(),title, message)
  if bool:
    return float(answer),bool
  else :
    return 0,bool





from application.helpers.instrumentmanager.instrumentmgr import InstrumentMgr
from application.lib.instrum_classes import *
mgr= InstrumentMgr()
import os, inspect
##
print mgr.instruments(),  mgr.instrumentNames()
print mgr. hasInstrument('dummy5'), mgr.hasInstrument('dummy'), mgr.getInstrument('dummy')
print mgr.currentConfig()
##
print mgr.loadInstrument(name='dummy')
print mgr.loadInstrument(name='dummy',mode='reload')
print mgr.loadInstrument(name='dummy',mode='add')
print mgr.loadInstrument(name='dummy',mode='replace')
##
print mgr._instruments.instrumentIndex('dummy')
print isinstance('dummy', Instr)
print mgr._instruments.names().index('dummy')
##
mgr._instruments.clear()
##
print mgr._instruments[1].loadInfo
##
print mgr.instruments()[0].getSourceFile()
##
print os.path.abspath(mgr.instruments()[0].getModule().__file__)
print os.path.abspath(inspect.getsourcefile(mgr.instruments()[0].getClass()))

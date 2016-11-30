"""
Initializes all the instruments and stores references to them in global variables.
"""
serverAddress = "rip://127.0.0.1:8000"

# ALL INSTRUMENT CLASS WILL BE CONVERTED TO LOWERCASE BY THE INSTRUMENT MANAGER
# IF A CLASS MODULE NAME IS NOT PROVIDED, LOWER(NAME) IS USED.

instruments = [
	{ 'name' : 'register',
      'load':False,
    },
	{ 'name' : 'dummy',
      'load':True,
    },
    { 'name' : 'adlink9826',
      'load':False,	
      'kwargs' : {}
    },
    { 'name' : 'Yoko',
      'load':False,	
      'class' : 'yokogawa',
      'kwargs' : {'name' : 'Yoko','visaAddress' : 'GPIB0::10'}
    },
    {
      'name' : 'tabor',
      'load':True,
      'class' : 'awg_taborv4',
      'kwargs' : {'visaAddress' : 'TCPIP0::192.168.0.75::5025::SOCKET', 'term_chars':'\n','testString':'*IDN?'}
    },
    {'name' : 'acqiris34',
     'load':False,
   	  'class' : 'acqiris6',
      'serverAddress' : 'rip://192.168.0.34:8000',
      'kwargs' : {'__includeModuleDLL2__':True}
    },
    { 'name' : 'awg',
      'load':False,
      'class' : 'awgv2',
      'kwargs' : {'visaAddress' : 'TCPIP0::192.168.0.28::inst0','testString':'*IDN?'}
    },
    { 'name' : 'vna',
      'load':False,
      'serverAddress': serverAddress,
      'kwargs' : {'visaAddress' : "GPIB0::6"}
    },
    { 'name' : 'afg',
      'load':False,
      'kwargs' : {'visaAddress' : 'TCPIP0::192.168.0.39::inst0'}
    } 
]

InstMgr=gv.InstrumentMgr
InstMgr.loadInstruments(instruments,globalParameters = {'forceReload' : True} )
print 
print 'LOADED INSTRUMENTS ARE:\n', InstMgr.instrumentNames()
for name in InstMgr.instrumentNames():
  	gv[name] = InstMgr.getInstrument(name)
print "GET ANY OF THEM IN ANY SCRIPTS USING THE SYNTAX gv.name"
import sys,getopt,imp,os.path,pyclbr,traceback,re,copy,xmlrpclib,yaml

from threading import Thread
from functools import wraps

from application.lib.instrum_classes import *
from application.lib.helper_classes import Helper

class InstrumentHandle:

  """
  Contains all information about an instrument, in a 'handle' used by the instruments manager.
  The handle attributes are _name,_baseClass,_instrument,_module,_remote,_remoteServer,_args and _kwargs
  """

  def instrumentModule(self):
    return self._module
  
  def __init__(self,name,baseClass,instrument,module = None,remote = False,remoteServer = None,args = [],kwargs = {}):
    self._name = name
    self._baseClass = baseClass
    self._instrument = instrument
    self._module = module
    self._remote = remote
    self._remoteServer = remoteServer
    self._args = args
    self._kwargs = kwargs
  
  def args(self):
    return self._args
    
  def kwargs(self):
    return self._kwargs
    
  def baseClass(self):
    return self._baseClass

  def module(self):
    return self._module
    
  def remote(self):
    return self._remote

  def remoteServer(self):
    return self._remoteServer
  
  def name(self):
    return self._name
    
  def instrument(self):
    return self._instrument

  def handleDict(self):
    """
    Returns a dictionnary of the handle properties 'name','baseClass','instrument','module','remote','remoteServer','args','kwargs'.
    """
    return {'name':self._name,'baseClass':self._baseClass,'instrument':self._instrument,'module':self._module,'remote':self._remote,'remoteServer':self._remoteServer,'args':self._args,'kwargs':self._kwargs}
    
class InstrumentMgr(Singleton,Helper):
 
  """ 
  The InstrumentManager manages a pull of instruments of class Instr:
  1) loads or reloads instruments from python modules on a local machine with or without local instrument server.
  2) loads a remote instrument, either through the HTTP XML-RPC protocol or through the custom Remote Instrument Protocol (RIP) .
  3) maintains a dictionary with the handles of class InstrumentHandle for each loaded instruments.
  The public methods instrumentHandles(), instrumentNames() and instruments() return this dictionnary, the instrument names, and the instruments, respectively. 
  4) It can load frontpanels associated to a local or remote instruments if a frontpanel module can be found.
    Frontpanels can be loaded but are not managed by the instrument manager.
  
  Note that there can be only one instance of the InstrumentManager per python shell (it is a singleton).
  """

  _initialized = False
  
  def __init__(self,parent=None,globals={},instrumentsRootDir = "instruments", frontpanelsRootDir = "instruments"):
    """
    Initialize the instrument manager.
    """   
    if self._initialized == True:
      return
        
    Singleton.__init__(self)
    Helper.__init__(self,parent,globals)

    self._instrumentsRootDir = instrumentsRootDir #  directory for intrument modules
    self._frontpanelsRootDir = frontpanelsRootDir #  directory for frontpanel modules
 
    self._instrumentHandles = dict()
    self._initialized = True

  ## Locating instrument and frontpanel modules

  def setInstrumentsRootDir(self,dir):
    """
    Sets the current root directory for instruments
    """
    self._instrumentsRootDir=dir

  def instrumentsRootDir(self):
    """
    Retruns the current root directory for instruments
    """
    return self._instrumentsRootDir

  def findInstrumentModule(self,instrumentModuleName):
    """
    Walks down the instrument directory tree, looks for the first valid instrument module with specified name instrumentModuleName,
    and returns:
      - a tuple (module name,filename) if a valid module was found
      - or None if no valid module was found.
    instrumentModuleName is a  dotted module name string possibly including '.' chars; it is NOT a filename string.
    The instrument module is considered as valid when it has the specified name and contains a definition for the class Instr.
    """
    for (dirpath, dirnames, filenames) in os.walk(self._instrumentsRootDir):  # start walking down the directory tree and at each step
      found=None
      # builds a list of all python file names (but _init__.py)
      pyFilenames=[filename for filename in filenames if ( os.path.splitext(filename)[1]=='.py' and filename!='__init__.py')]
      pyFilenames=[os.path.splitext(filename)[0] for filename in pyFilenames]
      if instrumentModuleName in pyFilenames:
        try:
          # build the class dictgionary with the pyclbr python class browser
          dic=pyclbr.readmodule(str(filename),[dirpath])
          # check that the module contains a class definition Instr in the file and not through an import.
          if 'Instr' in dic and dic['Instr'].file==os.path.join(os.path.realpath(dirpath), filename+'.py'):
            found=(dic['Instr'].module,dic['Instr'].file)
            break # stop the walk 
        except:
          print 'an error occured when trying to read the module.'
        finally:
          pass
      return found

  def findPanelModule(self,instrument):
    """
    Finds the module with a frontpanel that corresponds to the specified instrument, and return:
      - a tuple (module name,filename) if a valid module was found
      - or None if no valid module was found.
    instrument can be either an instrument of class Instr or an intrument module name (string).
    The search proceeds as follows:
      - retrieve the module of the instrument if instrument is a module name;
      - Look if a class Panel exists in this module: If yes returns this module and file names.
      - Otherwise look for a module with name name_panel where name is the instrument module name.
    """
    pass

  ## Loading and initializing local and remote instruments
    
  def loadInstrumentFromModule(self,name,instrumentModule,args = [],kwargs = {}):
    """
    Loads an instrument from a python module.
    - name is the name of the instrument to be initialized.
    - instrumentModule is the name of the python module containing the Instr class definition of the instrument.
    args and kwargs are the arguments to be passed to the initialization function at instantiation of the instrument.
    
    Returns the instrument object, or None if the initialization fails.
    """
    try:
      moduleName,fileName=self.findInstrumentModule(instrumentModule) 
      #module = __import__(moduleName,globals(),globals(),["Instr"],0)
      (path, name) = os.path.split(filename)
      (name, ext) = os.path.splitext(name)
      (file, filename, data) = imp.find_module(name, [path])
      try:
        module=imp.load_module(name, file, filename, data)
      finally:
        if file: file.close()
      instrument = module.Instr(name = name) # instantiation
      if isinstance(instrument,CompositeInstrument):
        instrument.setManager(self)
      instrument.initialize(*args,**kwargs)  # initialization with the passed arguments
    except:
      raise
    # Creates the instrument handle and notifies possible observers
    handle=InstrumentHandle(name,instrumentModule,instrument,module,args = args,kwargs = kwargs)
    self._instrumentHandles[name] = handle
    self.notify("instruments",self._instrumentHandles)
    return handle.instrument()

  def initInstrument(self,name,baseclass = None,args = [],kwargs = {},forceReload = False):
    """
    Loads an instrument if not already loaded or if forceReload is true.
    - name is the name of the instrument to be initialized.
    It can be a simple plain name (e.g. "vna1"), meaning that the instrument is to be loaded directly in local memory,
    or an URL (e.g. "rip://localhost:8000/vna1"), meaning that it is to be loaded through a server.
    - baseclass is the name of the python module containing the Instr class definition of the instrument.
    args and kwargs are the arguments to be passed to the initialization function at instantiation of the instrument.
    
    Returns the instrument object, or None if the initialization fails.
    """
    print "Initializing instrument %s" % name
    if name in self._instrumentHandles:
      if forceReload:
        return self.reloadInstrument(name,args = args, kwargs = kwargs)
      else:
        return self._instrumentHandles[name].instrument()
    else:
      if self._isUrl(name):
        return self.initRemoteInstrument(name,baseclass,args,kwargs,forceReload)
      if baseclass is None:
        baseclass = name
      baseclass = baseclass.lower()
      return self.loadInstrumentFromModule(name,baseclass,args = args,kwargs = kwargs)
  
  def reloadInstrument(self,name,baseclass = None,args = [],kwargs = {}):
    """
    Reloads a given instrument.
    """
    self.debugPrint('in InstrumentManager.reloadInstrument(',name,',',baseclass,')')
    print "Reloading %s" %  name
    if not name in self._instrumentHandles:
      raise KeyError("No instrument: %s to reload" % name)
    handle = self._instrumentHandles[name]
    if handle.instrument().isAlive():
      raise Exception("Cannot reload instrument while it is running...")
    if args != []:
      passedArgs = args
      handle._args = args
    else:
      passedArgs = handle.args()
    if kwargs != {}:
      passedKwArgs = kwargs
      handle._kwargs = kwargs
    else:
      passedKwArgs = handle.kwargs()
    if handle._remote == True:                                # remote instrument 
      if handle._remoteServer.hasInstrument(handle._name):
        handle._remoteServer.reloadInstrument(handle._name,handle._baseClass,passedArgs,passedKwArgs)
      else:
        handle._remoteServer.initInstrument(handle._name,handle._baseClass,passedArgs,passedKwArgs)
      self.notify("instruments",self._instrumentHandles)
      return handle.instrument()
    else:                                                     # local instrument 
      reload(handle._module)
      newClass = handle._module.Instr
      handle.instrument().__class__ = newClass
      handle.instrument().initialize(*passedArgs,**passedKwArgs)
      self.notify("instruments",self._instrumentHandles)
      return handle.instrument()

  def _isUrl(self,name):
    """
    Private method that determines if an instrument name is an URL for a remote instrument. 
    """
    if re.match(r'^rip\:\/\/',name) or  re.match(r'^http\:\/\/',name):
      return True
    return False

  def initRemoteInstrument(self,address,baseclass = None,args = [],kwargs = {},forceReload = False):
    """
    Loads a remote instrument, either through the HTTP XML-RPC protocol or through the custom Remote Instrument Protocol (RIP).
    - address includes the server name, port and instrument name;
    - baseclass is the name of a python module containing the Instr class definition of the instrument, accessible from the server.
    - args and kwargs are the arguments to be passed to the initialization function at instantiation of the instrument.
    - forceReload indicates if  reloading should be forced in case the remote instrument already exists.
    """
    self.debugPrint('in InstrumentManager.initRemoteInstrument(',address,',',baseclass,')')
    result =  re.match(r'^rip\:\/\/(.*)\:(\d+)\/(.*)$',address)
    # open the connection to server first
    if result:
      (host,port,name) = result.groups(0)
      try:
        remoteServer = ServerConnection(result.groups(0)[0],int(result.groups(0)[1]))
      except socket.error:
        print "Connection to remote host failed!"
        raise
    else:
      result = re.match(r'^http\:\/\/(.*)\:(\d+)\/(.*)$',address)
      if result:
        (host,port,name) = result.groups(0)
        try:
          remoteServer = xmlrpclib.ServerProxy("http://%s:%s" % (host,port))
        except socket.error:
          raise
      else:
        return None
    # If connection was oppened successfully, instantiate or get the instrument
    if baseclass is None:
      baseclass = name
    if name in self._instrumentHandles and forceReload == False:
      handle = self._instrumentHandles[name]
      return handle.instrument()      
    else:
      baseclass = baseclass.lower()
      try:
        # Instantiates the remote instrument that will call automatically the server
        instrument = RemoteInstrument(name,remoteServer,baseclass,args,kwargs,forceReload)
      except:
        raise
      # Build the handle to it
      handle = InstrumentHandle(name,baseclass,instrument,args = args,kwargs = kwargs,remote = True,remoteServer = remoteServer)
      self._instrumentHandles[name] = handle
      self.notify("instruments",self._instrumentHandles)
      # and return this handle
      return handle.instrument()

  def freeInstrumentName(self,name):
    """
    Builds a unique name for a new intrument.
    """
    name='instrument_1'
    names=self.instrumentNames()
    if name in names:
      i=1
      while True:
        name='instrument_'+str(i)
        if name not in names:
          break
    return name

  def initInstruments(self,instruments,globalParameters = {}):
    """
    Loads and initializes a pool of instruments described in a dictionary instruments.
    Each dictionary item is itself a dictionary with structure:
      {'name' : 'instrument name',
       'load':True||False,
       'class' : 'module class name',
       'serverAddress' : 'rip://192.168.0.22:8000', (for a remote instrument)
       'args': [] (a list of arguments to be passed to the initialization method of the instrument)
       'kwargs' : {} (a dictionary of keyword arguments to be passed to the initialization method of the instrument)
       }
      WARNING: Avoid passing an instrument name in args or kwargs, and changing the name in the instrument initialization function.
    """
    self.debugPrint('in InstrumentManager.initInstruments(',instruments,') ')
    for params in instruments:
      if not params.has_key('load') or params['load']:
        if ('name' not in params) :
          name =None
        else:
          name=params['name']
        if name == '' or name is None:
          name=self.freeInstrumentName()
        url = ""
        if 'serverAddress' in params:
          url+=params["serverAddress"]+"/"
        url+=name
        if 'class' in params:
          baseclass = params["class"]
        else:
          baseclass = name
        if 'kwargs' in params:
          kwargs = params["kwargs"]
        else:
          kwargs = {}
        #if not('name' in kwargs):
        # kwargs['name']=params['name']
        if 'args' in params:
          args = params["args"]
        else:
          args = []
        try:
          self.initInstrument(name=url,baseclass = baseclass,args = args,kwargs = kwargs,**globalParameters)
        except:
          print "Could not initialize instrument: %s" % url
          traceback.print_exc()

  ## Getting the instruments, their handles, their names

  def instrumentHandles(self):
    """
    Returns the handles of the managed instruments
    """
    return self._instrumentHandles
    
  def instrumentNames(self):
    """
    Returns the names of the managed instruments.
    """
    return self._instrumentHandles.keys()

  def handle(self,name):
    """
    Returns the handle of a an instrument specified by its name.
    """
    try:
      return self._instrumentHandles[name]
    except KeyError:
      return None

  def hasInstrument(self,name):
    """
    Return True if instrument with name name is mananged.
    """
    if name in self._instrumentHandles:  return True
    else: return False
    
  def getInstrument(self,name):
    """
    Returns the instrument with name name or raise an error.
    """
    if name in self._instrumentHandles:
      return self._instrumentHandles[name].instrument()
    else:
      raise AttributeError("Unknown instrument: %s" % name)

  ## Get parameters of all instruments at once

  def parameters(self):
    """
    Return a dictionary containing the parameter dictionnaries of all the instruments.
    """
    self.debugPrint('in InstrumentManager.parameters() ')
    params = dict()
    for name in self._instrumentHandles.keys():
      try:
        params[name]=self.getInstrument(name).parameters()
      except:
        print "An error occured when accessing parameters of instrument %s." % name
        print traceback.print_exc()
    return params

  ## Instrument states management

  def currentConfig(self,instrumentNames =None ,withInitialization = True):
    """
    InstrumentManager method that returns a dictionary containing the parameters of the instruments specified by the list of names 'instrumentNames';
    if 'instrumentNames' is None, includes all managed instruments.
    """
    self.debugPrint('in InstrumentManager.currentConfig(instrumentNames) with instrumentNames=',instrumentNames)
    config = dict()                                   # config directory will contain instrument directories that will contain the instrument state directory as well as optional initialization params 
    allInstrumentNames=instrumentNames()              # all managed instruments 
    if instrumentNames is None:
      instrumentNames=allInstrumentNames                              
    for name in instrumentNames:                      
      try:
        print "Storing state of instrument \"%s\"" % name
        config[name] = dict()
        config[name]["state"]=self.getInstrument(name).currentState()
        if withInitialization:
          config[name]["args"] = self.handle(name).args()
          config[name]["kwargs"] = self.handle(name).kwargs()
          config[name]["baseClass"] = self.handle(name).baseClass()
      except:
        print "Could not save the state of instrument %s:" % name
        print traceback.print_exc()
    return config

  def saveCurrentConfigInFile(self,filename,instrumentNames=None,withInitialization = True):
    """
    InstrumentManager method that saves the dictionary of the current configuration to a file.
    """
    currentConfig=self.currentConfig(instrumentNames=instrumentNames,withInitialization=withInitialization)
    filename=str(filename)
    configString = yaml.dump(currentConfig)
    configDir = os.path.dirname(filename)
    if not os.path.exists(configDir):
        os.mkdir(configDir)
    file = open(filename,"w")
    file.write(configString)
    file.close()
    
  def loadAndRestoreConfig(self,filename,instrumentNames=None):
    """
    Loads from a file and restores the config of the instruments in instrumentNames (or all managed instruments if instrumentNames is None).
    """
    self.debugPrint('in InstrumentManager.loadAndRestoreConfig(filename,instruments) with filename=',filename,' and instruments=',instruments)
    allInstrumentNames=self.instrumentNames() # all managed instruments 
    if instrumentNames is None:
      instrumentNames=allInstrumentNames  
    configFile = open(filename)
    config = yaml.load(configFile.read())          
    configFile.close()
    self.restoreConfig(config,instrumentNames)
    
  def restoreConfig(self,config,instrumentNames):
    """
    Restores the config of the instruments in instrumentNames (or all managed instruments if instrumentNames is None).
    """
    self.debugPrint('in InstrumentManager.restoreConfig(config) with config=',config)
    for instrumentName in instrumentNames:
      if config.has_key(instrumentName):
        try:
          state=config[instrumentName]['state']
          self.getInstrument(instrumentName).restoreState(state)
        except:
          print "Could not restore the state of instrument %s:" % name
          print traceback.print_exc()
      else:
        print 'No state found for ',instrumentName,' in config.'
        
  ## Frontpanel loading (no management at all)

  def frontpanel(self,name):
    """
    Loads and returns a new frontpanel for the instrument with name name.
    Note that the number of frontpanels per instrument is not limited.
    So check if another frontpanel already exists before calling this method, if you don't want multiple frontpanels of the same instrument.
    """
    self.debugPrint('in InstrumentManager.frontPanel(',name,')')
    self.debugPrint('handleDict=',self.handle(name).handleDict())
    handle = self.handle(name)
    if handle is None:
      return None
    moduleName = handle._baseClass
    try:
      module=self._frontpanelsRootDir+moduleName
      self.debugPrint('module=',module,' moduleName=',moduleName)
      frontpanelModule =  __import__(module,globals(),globals(),[moduleName],-1) # gets the module
      reload(frontpanelModule)                                                   # reloads it in case it has changed
      frontpanelModule =  __import__(module,globals(),globals(),[moduleName],-1) # and re import the new code
      self.debugPrint('frontpanelModule=',frontpanelModule)
      # all instrument frontpanel should be of the Panel() class.
      frontpanel = frontpanelModule.Panel(handle._instrument) # Instantiates the frontPanel and lets it know its associated instrument 
      frontpanel.setWindowTitle("%s front panel" % name)
      return frontpanel
    except:
      print 'No frontPanel could be loaded for instrument '+name+'.'
      print traceback.print_exc()

class RemoteInstrumentManager():
  """
  Manages the creation and reloading of instruments on a machine that has an instrument server.
  """
  def __init__(self):
    self._manager = InstrumentManager() # create an instrument manager as a property of the remoteManager (on the server side)
    
  def __getattr__(self,attr):           # This overidden __getattr__(attr) looks for the attribute attr in self.manager rather than in self
    if hasattr(self._manager,attr):     # and then returns a pure fonction able to call the attribute with its parameters and return True or False
      attr = getattr(self._manager,attr)
      return lambda *args,**kwargs : True if attr(*args,**kwargs) else False
      
  def dispatch(self,instrument,command,args = [],kwargs = {}):
    self.debugPrint('in RemoteManager.dispatch(',instrument,',',command,')')
    instr = self._manager.getInstrument(instrument)
    if command == 'ask':
      request = "instr."+str(*args)
      try:
        return eval(request)    
      except :
        raise
    elif command == 'evalByServer':
      return eval(*args)
    else: #elif hasattr(instr,command):
      # default behaviour initially programmed by Andreas Dewes  :
      method = getattr(instr,command)       # built instr.command
      if callable(method):                  # if it is a method :
        return  method(*args,**kwargs)      #   return its evaluation with arguments  *args and **kwargs
      else:                                 # else
        return method                       #   return the object itself
    #else:  # note that this behaviour forbid the syntax instr.object.function() -> see ask case above
    #  raise Exception("Unknown function name: %s" % command)
  
import sys
import getopt
import imp
import os.path
import pyclbr
import traceback
import re
import copy
import xmlrpclib
import yaml

from threading import Thread
from functools import wraps

from application.lib.instrum_classes import *
from application.lib.helper_classes import Helper

__instrumentsRootDir__ = 'lab/instruments'
__configsDir__ = 'lab/configs'
__lastConfigFilename__ = 'last_instrument_config.yml'


class InstrumentHandle(dict):

    """
    Contains relevant information about an instrument, in a 'handle' used by the instruments manager.
    The (all public) handle attributes are instrument, moduleName, module, remoteServer, args, and kwargs
    - Note that the instrument name is an attribute of the instrument, not of the InstrumentHandle.
    - moduleName is useful in case of a remote instrument, for which module=None
    """

    def __init__(self, instrument, module=None, moduleName=None, fullPath=None, remoteServer=None, args=[], kwargs={}):
        dict.__init__(self)
        self .update({'instrument': instrument, 'module': module, 'moduleName': moduleName, 'fullPath': fullPath,
                      'remoteServer': remoteServer, 'args': args, 'kwargs': kwargs})

    def name(self):
        return self['instrument'].name()


class InstrumentHandleList(list):

    """
    List of InstrumentHandles with methods to access names
    """

    def __init__(self):
        list.__init__(self)

    def names(self):
        return [handle.name() for handle in self]

    def withName(self, name):
        return [handle for handle in self if handle.name() == name]

    def instruments(self):
        return [handle['instrument'] for handle in self]


class InstrumentMgr(Singleton, Helper):

    """
    The InstrumentManager manages a pull of instruments of class Instr:
    1) loads or reloads instruments from python modules on a local machine with or without local instrument server.
    2) loads a remote instrument, either through the HTTP XML-RPC protocol or through the custom Remote Instrument Protocol (RIP) .
    3) maintains a dictionary with the handles of class InstrumentHandle for each loaded instruments.
      The public methods instrumentHandles(), instrumentNames() and instruments() return this dictionary, the instrument names, and the instruments, respectively.
    4) loads frontpanels associated to a local or remote instruments if a frontpanel module can be found.
      Frontpanels can be loaded but are not managed by the instrument manager.

    Note that there can be only one instance of the InstrumentManager per python shell (it is a singleton).
    """

    _initialized = False

    def __init__(self, name=None, parent=None, globals={}, instrumentsRootDir=__instrumentsRootDir__, frontpanelsRootDir=__instrumentsRootDir__):
        """
        Initialize the singleton instrument manager if not done yet.
        """
        if self._initialized:
            return

        Singleton.__init__(self)
        Helper.__init__(self, name, parent, globals)

        self._instrumentsRootDir = instrumentsRootDir  # root directory for intrument modules
        self._currentWorkingDir = instrumentsRootDir      # last directory for intrument modules
        self._frontpanelsRootDir = frontpanelsRootDir  # directory for frontpanel modules

        self._instrumentHandles = InstrumentHandleList()
        self._initialized = True
        try:
            self.loadAndRestoreConfig(loadIfNotLoaded=True)
        except:
            print 'ERROR when trying to load and restore configuration of instruments. '

    # Locating instrument and frontpanel modules

    def setInstrumentsRootDir(self, dir):
        """
        Sets the current root directory for instruments
        """
        self._instrumentsRootDir = dir

    def instrumentsRootDir(self):
        """
        Retruns the current root directory for instruments
        """
        return self._instrumentsRootDir

    def setCurrentWorkingDir(self, dir):
        """
        Sets the current root directory for instruments
        """
        self._currentWorkingDir = dir

    def currentWorkingDir(self):
        """
        Retruns the current root directory for instruments
        """
        return self._currentWorkingDir

    def findInstrumentModule(self, instrumentModuleName):
        """
        Walks down the instrument directory tree, looks for the first valid instrument module with specified name instrumentModuleName,
        and returns:
          - a tuple (module name,filename) if a valid module was found
          - or None if no valid module was found.
        instrumentModuleName is a dotted module name string possibly including '.' chars; it is NOT a filename string.
        The instrument module is considered as valid when it has the specified name and contains a definition for the class Instr.
        """
        found = None
        for (dirpath, dirnames, filenames) in os.walk(self._instrumentsRootDir):  # start walking down the directory tree and at each step
            # builds a list of all python file names (except _init__.py)
            pyFilenames = [filename for filename in filenames if (
                os.path.splitext(filename)[1] == '.py' and filename != '__init__.py')]
            pyFilenames = [os.path.splitext(filename)[0] for filename in pyFilenames]
            if instrumentModuleName in pyFilenames:
                try:
                    # build the class dictionary with the pyclbr python class browser
                    dic = pyclbr.readmodule(instrumentModuleName, [dirpath])
                    # check that the module contains a class definition Instr in the file and not through an import.
                    if 'Instr' in dic:
                        path1 = os.path.realpath(dic['Instr'].file)
                        path2 = os.path.join(os.path.realpath(dirpath), instrumentModuleName + '.py')
                        if path1 == path2:
                            found = (dic['Instr'].module, path1)
                            break  # stop the walk
                except:
                    print 'an error occured when trying to read the module.'
                finally:
                    pass
        return found

    def findPanelModule(self, instrument):
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

    # Loading and initializing local and remote instruments

    def loadInstrumentFromName(self, name, moduleName=None, args=[], kwargs={}, forceReload=False):
        """
        Loads an instrument from its name (or moduleName) if not already loaded or if forceReload is true.
        (If several instruments have the same name, only the first will be reloaded.)
        - name is the name of the instrument to be initialized.
        It can be a simple plain name (e.g. "vna1"), meaning that the instrument is to be loaded directly in local memory,
        or an URL (e.g. "rip://localhost:8000/vna1"), meaning that it is to be loaded through a server.
        - moduleName is the name of the python module containing the Instr class definition of the instrument;
        it will be set to name by default if not specified.
        - args and kwargs are the arguments to be passed to the initialize() method of the instrument after instantiation of the instrument.

        Returns the instrument object, or None if the initialization fails.
        """
        print "Initializing instrument %s" % name
        if name in self._instrumentHandles.names():
            handle = self._instrumentHandles.withName(name)
            if forceReload:
                return self.reloadInstrument(handle, args=args, kwargs=kwargs)
            else:
                return handle['instrument']
        else:
            if self._isUrl(name):
                return self.initRemoteInstrument(name, moduleName, args, kwargs, forceReload)
            if moduleName is None:
                moduleName = name
            # moduleName = moduleName.lower()  # why limiting to non capital letters ? Remove this limitation ?
            return self.loadInstrumentFromModuleName(name, moduleName, args=args, kwargs=kwargs)

    def loadInstrumentFromModuleName(self, name, moduleName, args=[], kwargs={}):
        """
        Loads an instrument from a python module name.
        - name is the name of the instrument to be initialized.
        - moduleName is the name of the python module containing the Instr class definition of the instrument.
        - args and kwargs are the arguments to be passed to the initialization function at instantiation of the instrument.

        Returns the instrument object, return None if the initialization fails,
        or raises an error if the module was not found.
        """
        try:
            moduleName, filePath = self.findInstrumentModule(moduleName)
        except:
            print 'Module %s not found' % moduleName
            raise
        instrument = self.loadInstrumentFromFilePath(name, filePath, args=args, kwargs=kwargs)
        return instrument

    def loadInstrumentFromFilePath(self, name, filePath, args=[], kwargs={}):
        """
        Loads an instrument from a python filePath.
        - name is the name of the instrument to be initialized.
        - filePath is the full path to the python module containing the Instr class definition of the instrument.
        - args and kwargs are the arguments to be passed to the initialization function at instantiation of the instrument.

        Returns the instrument object, returns None if the initialization fails,
        or raises an error if the module was not found.
        """
        (path, moduleName) = os.path.split(filePath)
        (moduleName, ext) = os.path.splitext(moduleName)
        if name is None:
            name = self.freeInstrumentName(moduleName)
        (file, filename, data) = imp.find_module(moduleName, [path])
        module = imp.load_module(moduleName, file, filename, data)
        if file:
            file.close()
        return self.instantiateInstrument(name, module, args=args, kwargs=kwargs)

    def instantiateInstrument(self, name, module, args=[], kwargs={}):
        """
        Instantiates an instrument from a python module.
        - name is the name of the instrument to be initialized.
        - moduleName is the name of the python module
        - module is the module containing the Instr class definition of the instrument.
        args and kwargs are the arguments to be passed to the initialization function at instantiation of the instrument.

        Returns the instrument object.
        """
        try:
            instrument = module.Instr(name=name)  # instantiation
            # attach the instrument manager to the instrument so that it can send notofications
            instrument.attach(self)
        except:
            raise 'No instrument of class Instr defined in file ' + filePath + '.'
        self._globals[name] = instrument
        print 'instrument %s in global memory and available as gv.%s.' % (name, name)
        if isinstance(instrument, CompositeInstrument):
            instrument.setManager(self)
        # Creates the instrument handle with empty args and kwargs
        fullPath = os.path.abspath(module.__file__)
        handle = InstrumentHandle(instrument, module, moduleName=module.__name__, fullPath=fullPath)
        self._instrumentHandles.append(handle)        # Adds the handle to the handles dictionnary
        # initialize with the passed args and kwargs. Handle will be update in the
        # initializeInstrument function if no error
        self.initializeInstrument(handle, args=args, kwargs=kwargs)
        self.notify("new_instrument", handle)         # and notifies possible observers
        return handle['instrument']

    def initializeInstrument(self, handle, args=[], kwargs={}, saveSettings=True):
        """
        Tries to initialize the instrument if it has an initialize method,
        and catches and displays an error if it occurs (without raising the error).
        Also saves the current config of instruments if saveSettings is true.
        """
        instrument = handle['instrument']
        if hasattr(instrument, 'initialize'):
            success = False
            try:
                instrument.initialized = False          # resets initialized to false
                instrument.initialize(*args, **kwargs)  # try initialization with the passed arguments
                instrument.initialized = True           # sets initialized to True if there was no error
                handle['args'] = args                      # then update handle cause there was no error
                handle['kwargs'] = kwargs
                success = True
                print 'instrument %s initialized successfully.' % instrument.name()
            except Exception as e:                      # in case of error build a clear message including the syntax used for the call
                code = instrument.name() + '.initialize('
                l1 = len(args)
                for index, arg in enumerate(args):
                    code += str(arg)
                    if index < l1 - 1:
                        code += ','
                if kwargs != {}:
                    code += ','
                    l1 = len(kwargs)
                    for index, key in enumerate(kwargs):
                        code += str(key) + '=' + str(kwargs[key])
                        if index < l1 - 1:
                            code += ','
                code += ')'
                print 'ERROR when initializing instrument with ' + code + ': ' + str(e)
            self.notify('initialized', handle)
        if saveSettings:
            self.saveCurrentConfigInFile()

    def reloadInstrument(self, handle, moduleName=None, args=[], kwargs={}):
        """
        Reloads a given instrument from its handle and returns the instrument
        """
        self.debugPrint('in InstrumentManager.reloadInstrument(', handle, ',', moduleName, ')')
        print "Reloading %s" % handle.name()
        if handle['instrument'].isAlive():
            raise Exception("Cannot reload instrument while it is running...")
        if args != []:
            passedArgs = args
            handle['args'] = args
        else:
            passedArgs = handle['args']
        if kwargs != {}:
            passedKwArgs = kwargs
            handle['kwargs'] = kwargs
        else:
            passedKwArgs = handle['kwargs']
        if handle['remoteServer'] is not None:                                # remote instrument
            name = handle.name()
            if handle['remoteServer'].hasInstrument(name):
                handle['remoteServer'].reloadInstrument(name, handle.moduleName, passedArgs, passedKwArgs)
            else:
                handle['remoteServer'].loadInstrumentFromName(name, handle.moduleName, passedArgs, passedKwArgs)
            self.notify('new_instrument', handle)
        else:                                                     # local instrument
            module = handle['module']
            path1 = os.path.split(module.__file__)[0]
            if path1 not in sys.path:
                sys.path.insert(0, path1)
            reload(module)
            newClass = module.Instr
            handle['instrument'].__class__ = newClass
            self.initializeInstrument(handle, args=passedArgs, kwargs=passedKwArgs)
        self.notify('new_instrument', handle)
        return handle['instrument']

    def _isUrl(self, name):
        """
        Private method that determines if an instrument name is an URL for a remote instrument.
        """
        if re.match(r'^rip\:\/\/', name) or re.match(r'^http\:\/\/', name):
            return True
        return False

    def initRemoteInstrument(self, address, moduleName=None, args=[], kwargs={}, forceReload=False):
        """
        Loads a remote instrument, either through the HTTP XML-RPC protocol or through the custom Remote Instrument Protocol (RIP).
        - address includes the server name, port and instrument name;
        - moduleName is the name of a python module containing the Instr class definition of the instrument, accessible from the server.
        - args and kwargs are the arguments to be passed to the initialization function at instantiation of the instrument.
        - forceReload indicates if  reloading should be forced in case the remote instrument already exists.
        """
        self.debugPrint('in InstrumentManager.initRemoteInstrument(', address, ',', moduleName, ')')
        result = re.match(r'^rip\:\/\/(.*)\:(\d+)\/(.*)$', address)
        # open the connection to server first
        if result:
            (host, port, name) = result.groups(0)
            try:
                remoteServer = ServerConnection(result.groups(0)[0], int(result.groups(0)[1]))
            except socket.error:
                print "Connection to remote host failed!"
                raise
        else:
            result = re.match(r'^http\:\/\/(.*)\:(\d+)\/(.*)$', address)
            if result:
                (host, port, name) = result.groups(0)
                try:
                    remoteServer = xmlrpclib.ServerProxy("http://%s:%s" % (host, port))
                except socket.error:
                    raise
            else:
                return None
        # If connection was opened successfully, instantiate or get the instrument
        if moduleName is None:
            moduleName = name
        if name in self._instrumentHandles.names() and not forceReload:
            handle = self._instrumentHandles.withName(name)[0]
            return handle['instrument']
        else:
            #moduleName = moduleName.lower()
            try:
                # Instantiates the remote instrument that will call
                # automatically the server
                instrument = RemoteInstrument(name, remoteServer, moduleName, args, kwargs, forceReload)
            except:
                raise
            # Build the handle to it
            handle = InstrumentHandle(instrument, moduleName=moduleName,
                                      remoteServer=remoteServer, args=args, kwargs=kwargs)
            self._instrumentHandles.append(handle)
            self.notify("new_instrument", handle)
            # and return this handle
            return handle['instrument']

    def freeInstrumentName(self, name):
        """
        Builds a unique name for a new intrument.
        New name will be name or name_i with i the lowest unused index >=2.
        """
        if name is None or name == '':
            name = 'instrument'
        newName = name
        names = self.instrumentNames()
        print newName, names
        if newName in names:
            i = 2
            k = newName.rfind("_")
            if k != -1:
                endStr = newName[k + 1:]
                if endStr.isdigit():
                    i = int(endStr) + 1
            while True:
                newName = name + '_' + str(i)
                print newName
                if newName not in names:
                    break
                i += 1
        return newName

    def loadInstruments(self, instruments, globalParameters={}):
        """
        Loads and initializes a pool of instruments described in a list of instrument dictionaries.
        Each instrument dictionary has the structure:
          {'name' : 'instrument name',
           'load':True||False,
           'class' : 'module class name',
           'serverAddress' : 'rip://192.168.0.22:8000', (for a remote instrument)
           'args': [] (a list of arguments to be passed to the initialization method of the instrument)
           'kwargs' : {} (a dictionary of keyword arguments to be passed to the initialization method of the instrument)
           }
          WARNING: Avoid passing an instrument name in args or kwargs, and/or changing the name in the instrument initialization function.
        """
        self.debugPrint('in InstrumentManager.loadInstruments(', instruments, ') ')
        for params in instruments:
            if 'load' not in params or params['load']:
                if ('name' not in params):
                    name = None
                else:
                    name = params['name']
                if name == '' or name is None:
                    name = self.freeInstrumentName()
                url = ""
                if 'serverAddress' in params:
                    url += params["serverAddress"] + "/"
                url += name
                if 'class' in params:
                    moduleName = params["class"]
                else:
                    moduleName = name
                if 'kwargs' in params:
                    kwargs = params["kwargs"]
                else:
                    kwargs = {}
                # if not('name' in kwargs):
                # kwargs['name']=params['name']
                if 'args' in params:
                    args = params["args"]
                else:
                    args = []
                try:
                    self.loadInstrumentFromName(name=url, moduleName=moduleName, args=args,
                                                kwargs=kwargs, **globalParameters)
                except:
                    print "Could not initialize instrument: %s" % url
                    traceback.print_exc()

    # Getting the instruments, their handles, their names

    def instrumentHandles(self):
        """
        Returns the handles of the managed instruments
        """
        return self._instrumentHandles

    def instrumentNames(self):
        """
        Returns the names of the managed instruments.
        """
        return self._instrumentHandles.names()

    def instruments(self):
        """
        Returns the managed instruments
        """
        return self._instrumentHandles.instruments()

    def hasInstrument(self, name):
        """
        Return True if instrument with name name is managed.
        """
        return name in self._instrumentHandles.names()

    def handle(self, name):
        """
        Returns the handle of the first instrument with a specified name, or None if not found.
        """
        if self.hasInstrument(name):
            return self._instrumentHandles.withName(name)[0]
        else:
            return None

    def getInstrument(self, name):
        """
        Returns the first instrument with a specified name or None.
        """
        if name in self._instrumentHandles.names():
            return self._instrumentHandles.withName(name)[0]['instrument']
        else:
            return None

    # Instrument configuration management

    def config1Instr(self, instrumentHandle, withCurrentState=True):
        """
        InstrumentManager method that returns the tuple (instrumentName,dic) where
        dic = {'moduleName': moduleName, 'fullPath': fullPath, 'remoteServer': remoteServer, 'args': args, 'kwargs': kwargs, state:{}}
        is the dictionary of parameters of the single instrument defines by its handle instrumentHandle.
        If withCurrentState is true, dic includes also the current state of the instrument.
        """
        config1 = dict(instrumentHandle)        # start with a copy of instrumentHandle
        for key in ['instrument', 'module']:    # delete non pickable items
            del config1[key]
        if withCurrentState:                    # add current state if requested
            try:
                config1['state'] = instrumentHandle['instrument'].currentState()
            except:
                print 'Could not get the state of instrument %s:' % instrumentHandle.name()
                print traceback.print_exc()
        return config1

    def currentConfig(self, instrumentHandles=None, withCurrentState=True):
        """
        InstrumentManager method that returns a dictionary {instrumentName1: dic1, instrumentName2: dic2 } containing dictionaries of parameters
        for the instruments in the list instrumentHandles;
        if instrumentHandles is None or [], includes all managed instruments;
        if withCurrentState is true, includes also the current states of the instruments.
        """
        config = dict()
        if instrumentHandles is None:
            instrumentHandles = self._instrumentHandles              # all managed instruments
        for handle in instrumentHandles:
            config[handle.name()] = self.config1Instr(handle, withCurrentState)
        return config

    def saveCurrentConfigInFile(self, instrumentHandles=None, withCurrentState=True, filename=None):
        """
        InstrumentManager method that saves the dictionary of the current configuration to a file.
        instrumentHandles: list of the instruments to include;
        (if instrumentHandles is None, includes all managed instruments;
        if withCurrentState is true, includes also the current state of the instrument.
        """
        currentConfig = self.currentConfig(instrumentHandles, withCurrentState)
        configString = yaml.dump(currentConfig)
        if filename in [None, '']:    # store at default destination
            filename = __configsDir__ + '/' + __lastConfigFilename__
        filename = str(filename)
        configDir = os.path.dirname(filename)
        if not os.path.exists(configDir):
            os.mkdir(configDir)
        file = open(filename, "w")
        file.write(configString)
        file.close()

    def restoreConfig(self, config, instrumentNames=None, loadIfNotLoaded=False):
        """
        Restores the config of the instruments in instrumentNames (or all instruments in config if instrumentNames is None).
        If loadIfNotLoaded is true, also loads the instruments if necessary.
        """
        if instrumentNames is None:
            instrumentNames = config.keys()
        for instrumentName in instrumentNames:
            if instrumentName in config:
                # print 'instrument %s in config' % instrumentName
                instrumentConfig = config[instrumentName]
                if instrumentName not in self._instrumentHandles.names() and loadIfNotLoaded:
                    # print 'instrument %s not loaded' % instrumentName
                    try:
                        fullPath, remoteServer, moduleName, args, kwargs = [instrumentConfig[key]
                                                                            for key in ['fullPath', 'remoteServer', 'moduleName', 'args', 'kwargs']]
                        if instrumentConfig['remoteServer'] is not None:
                            name = remoteServer + '/' + instrumentName
                            self.initRemoteInstrument(name, moduleName=moduleName, args=args,
                                                      kwargs=kwargs, forceReload=True)
                        else:
                            self.loadInstrumentFromFilePath(instrumentName, fullPath, args, kwargs)
                    except:
                        print "Could not load instrument %s:" % name
                        print traceback.print_exc()
                if instrumentName in self._instrumentHandles.names():
                    try:
                        state = config[instrumentName]['state']
                        self.getInstrument(instrumentName).restoreState(state)
                    except:
                        print "Could not restore the state of instrument %s:" % name
                        print traceback.print_exc()
            else:
                print 'No state found in config for instrument %s' % instrumentName

    def loadAndRestoreConfig(self, filename=None, instrumentNames=None, loadIfNotLoaded=False):
        """
        Loads from a file and restores the config of the instruments in instrumentNames (or all instruments in config if instrumentNames is None).
        If loadIfNotLoaded is true, also loads the instruments if necessary.
        """
        if filename is None:
            filename = __configsDir__ + '/' + __lastConfigFilename__
        configFile = open(filename)
        config = yaml.load(configFile.read())
        configFile.close()
        self.restoreConfig(config, instrumentNames, loadIfNotLoaded)

    # Frontpanel loading (no management at all)

    def frontpanel(self, name):
        """
        Loads and returns a new frontpanel for the instrument with name name.
        Note that the number of frontpanels per instrument is not limited.
        So check if another frontpanel already exists before calling this method, if you don't want multiple frontpanels of the same instrument.
        """
        self.debugPrint('in InstrumentManager.frontPanel(', name, ')')
        self.debugPrint('handle = ', self.handle(name))
        handle = self.handle(name)
        if handle is None:
            return None
        moduleName = handle['moduleName']
        try:
            module = self._frontpanelsRootDir + moduleName
            self.debugPrint('module=', module, ' moduleName=', moduleName)
            frontpanelModule = __import__(module, globals(), globals(), [moduleName], -1)  # gets the module
            # reloads it in case it has changed
            reload(frontpanelModule)
            frontpanelModule = __import__(module, globals(), globals(), [moduleName], -1)  # and re import the new code
            self.debugPrint('frontpanelModule=', frontpanelModule)
            # all instrument frontpanel should be of the Panel() class.
            # Instantiates the frontPanel and lets it know its associated
            # instrument
            frontpanel = frontpanelModule.Panel(handle['instrument'])
            frontpanel.setWindowTitle("%s front panel" % name)
            return frontpanel
        except:
            print 'No frontPanel could be loaded for instrument ' + name + '.'
            # print traceback.print_exc()


class RemoteInstrumentManager():
    """
    Manages the creation and reloading of instruments on a machine that has an instrument server.
    """

    def __init__(self):
        # create an instrument manager as a property of the remoteManager (on
        # the server side)
        self._manager = InstrumentManager()

    # This overidden __getattr__(attr) looks for the attribute attr in
    # self.manager rather than in self
    def __getattr__(self, attr):
        # and then returns a pure fonction able to call the attribute with its
        # parameters and return True or False
        if hasattr(self._manager, attr):
            attr = getattr(self._manager, attr)
            return lambda *args, **kwargs: True if attr(*args, **kwargs) else False

    def dispatch(self, instrument, command, args=[], kwargs={}):
        self.debugPrint('in RemoteManager.dispatch(',
                        instrument, ',', command, ')')
        instr = self._manager.getInstrument(instrument)
        if command == 'ask':
            request = "instr." + str(*args)
            try:
                return eval(request)
            except:
                raise
        elif command == 'evalByServer':
            return eval(*args)
        else:  # elif hasattr(instr,command):
            # default behaviour initially programmed by Andreas Dewes  :
            method = getattr(instr, command)       # built instr.command
            if callable(method):                  # if it is a method :
                # return its evaluation with arguments  *args and **kwargs
                return method(*args, **kwargs)
            else:                                 # else
                return method  # return the object itself
        # else:  # note that this behaviour forbid the syntax instr.object.function() -> see ask case above
        #  raise Exception("Unknown function name: %s" % command)

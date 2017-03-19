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

__instrumentsRootDir__ = os.path.join(os.getcwd(), 'lab/instruments')  # Debug here
__configsDir__ = os.path.join(os.getcwd(), 'lab/configs')
__lastConfigFilename__ = 'last_instrument_config.yml'


class InstrumentList(list):

    """
    List of Instruments with methods to access names
    """

    def __init__(self):
        list.__init__(self)

    def names(self):
        """
        Returns the list of names of the instruments the handles are pointing to.
        """
        return [instrument.name() for instrument in self]

    def withName(self, name):
        """
        Returns all the instruments with a certain name.
        (Should contain normally a single instrument since duplicate names are not allowed)
        """
        return [instrument for instrument in self if instrument.name() == name]

    def instrumentIndex(self, instrument):
        """
        Returns None or the index of an instrument present in self,
        either from the instrument itself, its name, or its index.
        """
        i = None
        try:
            if isinstance(instrument, int) and i < len(self):
                i = instrument
            elif isinstance(instrument, Instr):    # instrument.__class__.__name__ == 'Instr':
                i = self.index(instrument)
            else isinstance(instrument, str):
                i = self.names().index(instrument)
        except:
            pass
        return i


class InstrumentMgr(Singleton, Helper):
    """
    The InstrumentMgr manages a pull of instruments of class Instr:
    1) loads or reloads instruments from python modules on a local machine with or without local instrument server.
    2) loads a remote instrument, either through the HTTP XML-RPC protocol or through the custom Remote Instrument Protocol (RIP) .
    3) maintains a list of InstrumentHandle dictionaries (1 for each managed instruments).
      The public methods instrumentHandles(), instrumentNames() and instruments() return this dictionary, the instrument names, and the instrument objects, respectively.
    4) can remove (and try to delete) instruments from the managed instrument list
    5) loads frontpanels associated to a local or remote instruments if a frontpanel module can be found.
      Frontpanels can only be loaded but are not managed by the instrument manager.

    Note that there can be only one instance of the InstrumentMgr per python shell (it is a singleton).
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
        self._currentWorkingDir = instrumentsRootDir   # last directory for intrument modules
        self._frontpanelsRootDir = frontpanelsRootDir  # directory for frontpanel modules

        self._instruments = InstrumentList()
        self._initialized = True
        try:
            self.loadAndRestoreConfig(loadIfNotLoaded=True)
        except:
            print 'ERROR when trying to load and restore configuration of instruments. '

    # Locating instrument modules

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
          - a tuple (module name, filename) if a valid module was found
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

    # Loading, initializing, or adding local or remote instruments

    def addInstrument(self, instrument):
        """
        Adds an instrument of Class Instrument or RemoteInstrument to the instrument manager's instrument list.
        Raise an error if an instrument with the same name is already present.
        """
        if isInstance(instrument, (Instrument, RemoteInstrument)) and instrument.name() not in self.instrumentNames():
            self._instruments.append(instrument)
        else:
            raise Exception(
                'Cannot add instrument %s to instrument manager because another instrument with the same already exists.')

    def loadInstrument(self, name=None, mode=None, serverAddress=None, moduleFileOrDir=None, args=[], kwargs={}):
        """
        Loads, replaces, reloads or simply returns a new or already loaded local or remote instrument,
        and returns the instrument handle of type InstrumentHandle..
        Inputs are :
        - name (str): name requested for the instrument, possibly modified by the code if already existing.
        - mode (None, 'reload', 'replace', or 'add'): specifies the action to be done (see "how it works" below)
        - serverAddress (str): None, or RIP or HTTP XML-RPC remote server address;
            an address can be with or without port (like rip://127.0.0.1:8000 or ???)
        - moduleFileOrDir (str): directory or name of the py module file containing the Instr class, in one of the following formats:
            full file path (like 'L:/lab_control/quantrolab/lab/instruments/dummy.py')
            directory (like 'L:/lab_control/quantrolab/lab/instruments/', name.py will be added)
            short file name (like 'dummy' or 'dummy.py')
            None (address will be set to name)
        - args: list of arguments to be passed to the initialize method
        - kwargs: dictionnary of keyword arguments to be passed to the initialize method
        How it works:
        If name is provided and found in the already defined instruments:
            - does nothing if mode=None;
            - reloads the instrument if mode = 'reload';
            - closes the existing instrument and loads a new one if mode = 'replace';
            - adds an unused index to the name and continues loading if mode = 'add'.
        Then, if serverOrAddress is a valid remote server or server address, passes the parameters
             to _loadRemoteInstrument() with the name possibly modified as described above;
            Note that names already in use on a particular server can be obtained by calling
            self.remoteServer(serverOrAddress).instrumentNames()
        Otherwise:
            If name is not provided and fileOrDir is a correct module file name,
                creates a name from the module name and an unused index, and continues loading.
            If name is defined and fileOrDir does not contain a module name, adds the module name to fileOrDir
            If fileOrDir is defined and is an atomic name, looks for a module with this name in a default path
            If fileOrDir is defined and is a complete file path, uses this python file as the module
        """
        if self.hasInstrument(name):                          # if instrument(s) with the same name is (are) already loaded
            if mode is not 'add':
                instrument = self.getInstrument(name)          # find the handle of the first one
                if mode is 'reload':                           # reload it if requested
                    return self.reloadInstrument(name, handle, args, kwargs)
                elif mode is None:
                    return instrument                          # or return it otherwise
                elif mode is 'replace':
                    self.removeInstruments(instrument, tryDelete=True)  # and continue below
            # use the requested name as module name (before updating it)
            if moduleFileOrDir in ['', None]:
                moduleFileOrDir = name
        if name in ['', None] and moduleFileOrDir in ['', None]:
            raise ValueError('At least an instrument name or a module name has to be passed to loadInstrument.')
        elif moduleFileOrDir in ['', None]:                      # Set empty address to name if needed
            moduleFileOrDir = name
        elif name in ['', None]:                                 # Set name to base module name
            name = os.path.splitext(os.path.basename(moduleFileOrDir))[0]
        name = self.freeInstrumentName(name)                     # update name with index if necessary
        if server is None:                                       # if local instrument
            return self._loadLocalInstrument(name, moduleFileOrDir, args, kwargs)
        else:                                                    # if remote instrument
            return self._loadRemoteInstrument(name, mode, serverAddress, moduleFileOrDir, args, kwargs)

    def reloadInstrument(self, instrument, args=[], kwargs={}):
        """
        Reloads a local or remote  instrument and returns the updated handle.
        if initializing arguments and keyword arguments are not passed, those present in the instrument loadInfo dictionnary are used.
        """
        self.debugPrint('in InstrumentMgr.reloadInstrument()')
        if isInstance(instrument, (RemoteInstrument)):
            instrument._server.loadInstrument(name, None, moduleFileOrDir, args, kwargs, False, True)
        else:  # local instrument => use instrument.loadInfo
            if instrument.isAlive():
                raise Exception('Cannot reload instrument while it is running...')
            info = instrument.loadInfo
            if args != []:
                passedArgs = args
                info['args'] = args
            else:
                passedArgs = info['args']
            if kwargs != {}:
                passedKwArgs = kwargs
                info['kwargs'] = kwargs
            else:
                passedKwArgs = info['kwargs']
            module = instrument.getModule()
            path1 = os.path.split(module.__file__)[0]
            if path1 not in sys.path:
                sys.path.insert(0, path1)
            reload(module)
            newClass = module.Instr
            instrument.__class__ = newClass
            self.initializeInstrument(instrument, args=passedArgs, kwargs=passedKwArgs)
        self.notify('new_instrument', instrument)
        return instrument

    def _loadLocalInstrument(self, name, moduleFileOrDir, args=[], kwargs={}):
        """
        Private method for loading a local instrument. See loadInstrument docstring.
        How it works: builds the file path and calls _loadLocalInstrumentFromFilePath.
        Returns the instrument handle of type InstrumentHandle.
        """
        # if moduleFileOrDir is an atomic string
        if all([c not in moduleFileOrDir for c in [':', '.', '/', '\\']]):
            try:
                moduleName, moduleFileOrDir = self.findInstrumentModule(moduleFileOrDir)
            except Exception as e:
                raise (('Module %s not found: ' % moduleName) + str(e))
        elif os.path.isdir(moduleFileOrDir):            # if moduleFileOrDir is a directory
            name2 = name
            if '.' not in name:
                name2 += '.py'
            moduleFileOrDir += name2
        return self._loadLocalInstrumentFromFilePath(name, moduleFileOrDir, args, kwargs)

    def _loadLocalInstrumentFromFilePath(self, name, filePath, args=[], kwargs={}):
        """
        Private method for loading an instrument from a python filePath.
        Inputs are:
        - name is the name of the instrument to be initialized.
        - filePath is the full path to the python module containing the Instr class definition of the instrument.
        - args and kwargs are the arguments to be passed to the initialization function at instantiation of the instrument.

        Returns None if the initialization fails, raises an error if the module was not found,
        or returns the instrument handle of type InstrumentHandle.
        """
        (path, moduleName) = os.path.split(filePath)
        (moduleName, ext) = os.path.splitext(moduleName)
        if name is None:
            name = self.freeInstrumentName(moduleName)
        if not os.path.isabs(path):
            path = os.path.join(self._instrumentsRootDir, path)
        try:
            (file, filename, data) = imp.find_module(moduleName, [path])
            module = imp.load_module(moduleName, file, filename, data)
            if file:
                file.close()
        except Exception as e:
            raise ValueError('_loadLocalInstrumentFromFilePath error loading module %s' % filePath)
        return self._instantiateInstrument(name, module, args=args, kwargs=kwargs)

    def _instantiateInstrument(self, name, module, args=[], kwargs={}):
        """
        Private method that instantiates a local instrument from a python module.
        - name is the name of the instrument to be initialized.
        - moduleName is the name of the python module
        - module is the module containing the Instr class definition of the instrument.
        args and kwargs are the arguments to be passed to the initialization function at instantiation of the instrument.

        Returns the instrument.
        """
        try:
            # instantiation => instrumen.loadInfo is updated with module name and fullPath
            instrument = module.Instr(name=name)
            # attach the instrument manager to the instrument so that it can send notofications
            instrument.attach(self)
        except Exception as e:
            raise ValueError('No instrument of class Instr defined in file ' + filePath + ': ' + str(e))
        self._globals[name] = instrument
        print 'instrument %s in global memory and available as gv.%s.' % (name, name)
        if isinstance(instrument, CompositeInstrument):
            instrument.setManager(self)
        self._instruments.append(instrument)      # Adds the intrument to the instrument list
        # initialize with the passed args and kwargs.
        self.initializeInstrument(instrument, args=args, kwargs=kwargs)
        self.notify("new_instrument", instrument)         # and notifies possible observers
        return instrument

    def initializeInstrument(self, instrument, args=[], kwargs={}, saveSettings=True):
        """
        Tries to initialize the instrument if it has an initialize method,
        and catches and displays an error if it occurs (without raising the error).
        Also saves the current config of instruments if saveSettings is true.
        """
        if hasattr(instrument, 'initialize'):
            try:                                        # try initialization with the passed arguments
                instrument.initialize(*args, **kwargs)  # loadInfo will be automatically updated
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
            self.notify('initialized', instrument)
        if saveSettings:
            self.saveCurrentConfigInFile()

    def freeInstrumentName(self, name):
        """
        Builds a unique name for a new intrument.
        New name will be name or name_i with i the lowest unused index >=2.
        """
        if name is None or name == '':
            name = 'instrument'
        newName = name
        names = self.instrumentNames()
        if newName in names:
            i = 2
            k = newName.rfind("_")
            if k != -1:
                endStr = newName[k + 1:]
                if endStr.isdigit():
                    i = int(endStr) + 1
            while True:
                newName = name + '_' + str(i)
                # print newName
                if newName not in names:
                    break
                i += 1
        return newName

    def remoteServer(self, serverAddress):
        """
        Returns a new server connection from the xmlrpclib or rip server address serverAddress
        """
        server = None
        result = re.match(r'^rip\:\/\/(.*)\:(\d+)\/(.*)$', serverAddress)
        if result:
            (host, port, name) = result.groups(0)
            try:
                server = ServerConnection(result.groups(0)[0], int(result.groups(0)[1]))
            except socket.error as e:
                raise ValueError(('Connection to remote host %s failed: ' % serverAddress) + str(e))
        else:
            result = re.match(r'^http\:\/\/(.*)\:(\d+)\/(.*)$', serverAddress)
            if result:
                (host, port, name) = result.groups(0)
                try:
                    server = xmlrpclib.ServerProxy('http://%s:%s' % (host, port))
                except socket.error as e:
                    raise ValueError(('Connection to remote host %s failed: ' % serverAddress) + str(e))
        return server

    def _loadRemoteInstrument(self, name, mode, serverAddress, moduleFileOrDir, args=[], kwargs={}):
        """
        Private method for loading a remote instrument, either through the HTTP XML-RPC protocol
        or through the custom Remote Instrument Protocol (RIP).
        Inputs are the same as those of loadInstrument but with serverOrAddress different from None.
        Returns the instrument handle of type InstrumentHandle.
        """
        self.debugPrint('in InstrumentMgr.loadRemoteInstrument(%s, %s, %s)' % (name, mode if mode is not None else 'None', str(
            serverOrAddress), moduleFileOrDir if moduleFileOrDir is not None else 'None'))
        server = self.remoteServer(serverAddress)  # gets a new connection to the server
        try:    # Instantiates the remote instrument that will call automatically the server.loadInstrument()
            instrument = RemoteInstrument(name, mode, server, moduleFileOrDir, args, kwargs)
        except Exception as e:
            raise ValueError(('Connection to remote host %s failed: ' % serverOrAddress) + str(e))
        self._instruments.append(instrument)
        self.notify('new_instrument', instrument)
        return instrument   # and return this handle

    def loadInstruments(self, instrumentDicList, globalParameters={}):
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
        self.debugPrint('in InstrumentMgr.loadInstruments(', instrumentDicList, ') ')
        for params in instrumentDicList:
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

    def reloadInstruments(self, instruments):
        """
        Reloads a list of instruments.
        """
        for instrument in instruments:
            self.reloadInstrument(instrument)

    # Getting the instruments and their names

    def instruments(self):
        """
        Returns the managed instruments
        """
        return self._instruments()

    def instrumentNames(self):
        """
        Returns the names of the managed instruments.
        """
        return [instrument.name() for instrument in self._instruments()]

    def hasInstrument(self, name):
        """
        Return True if instrument with name name is managed.
        """
        return name in self.instrumentNames()

    def getInstrument(self, name):
        """
        Returns the first instrument with a specified name, or None if not found.
        """
        if self.hasInstrument(name):
            return self._instruments.withName(name)[0]
        else:
            return None

    # Instrument configuration management

    def config1Instr(self, instrument, withCurrentState=True):
        """
        InstrumentMgr method that returns a dictionnary dic giving the configuration of an instrument:
        dic include at least 'moduleName', 'fullPath', 'args', and 'kwargs' keys;
        If the instrument is a remoteInstrument, dic includes also a 'serverAddress' key;
        If withCurrentState is true, dic includes also the current state of the instrument.
        """
        config1 = dict(instrument.loadInfo)                 # start with a copy of instrumentHandle
        if isInstance(instrument, (RemoteInstrument)):      # add the server address if necessary
            config1['serverAddress'] = instrument._server.address()
        if withCurrentState:                                # add current state if requested
            try:
                config1['state'] = instrumentHandle['instrument'].currentState()
            except:
                print 'Could not get the state of instrument %s:' % instrumentHandle.name()
                print traceback.print_exc()
        return config1

    def currentConfig(self, instruments=None, withCurrentState=True):
        """
        InstrumentMgr method that returns a dictionary {instrumentName1: dic1, instrumentName2: dic2 } containing dictionaries of parameters
        for the instruments in the list instrumentHandles;
        if instrumentHandles is None or [], includes all managed instruments;
        if withCurrentState is true, includes also the current states of the instruments.
        """
        config = dict()
        if instruments is None:
            instruments = self._instruments              # all managed instruments
        for instrument in instruments:
            config[instrument.name()] = self.config1Instr(instrument, withCurrentState)
        return config

    def saveCurrentConfigInFile(self, instruments=None, withCurrentState=True, filename=None):
        """
        InstrumentMgr method that saves the dictionary of the current configuration to a file.
        Inputs are:
        - instruments: list of the instruments to be included (all managed instruments if None)
        - withCurrentState (bool): whetehr to include also the current state of each instrument
        - filename: the file name for saving the configuration
        """
        currentConfig = self.currentConfig(instruments, withCurrentState)
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

    def restoreConfig(self, config, instrumentNames=None, mode='reload', loadIfNotLoaded=False):
        """
        Restores the config of the instruments in instrumentNames (or all instruments in config if instrumentNames is None).
        If loadIfNotLoaded is true, also loads the instruments if necessary.
        Possible problem: consequence of the mode used
        """
        if instrumentNames is None:
            instrumentNames = config.keys()
        for name in instrumentNames:
            if name in config:
                # print 'instrument %s in config' % instrumentName
                instrumentConfig = config[name]
                if name not in self._instruments.names() and loadIfNotLoaded:
                    # print 'instrument %s not loaded' % instrumentName
                    try:
                        fullPath, moduleName, args, kwargs = [instrumentConfig[
                            key] for key in ['moduleName', 'fullPath', 'args', 'kwargs']]
                        if 'serverAddress' in instrumentConfig:
                            # _loadRemoteInstrument(self, name, mode, serverAddress, moduleFileOrDir, args=[], kwargs={})
                            self.loadRemoteInstrument(name, mode, instrumentConfig[
                                                      'serverAddress'], fullPath, args, kwargs)
                        else:
                            # _loadLocalInstrumentFromFilePath(self, name, filePath, args=[], kwargs={})
                            self._loadLocalInstrumentFromFilePath(name, fullPath, args, kwargs)
                    except:
                        print "Could not load instrument %s:" % name
                        print traceback.print_exc()
                if name in self._instruments.names():
                    try:
                        state = instrumentConfig['state']
                        self.getInstrument(name).restoreState(state)
                    except:
                        print "Could not restore the state of instrument %s:" % name
                        print traceback.print_exc()
            else:
                print 'No state found in config for instrument %s' % name

    def loadAndRestoreConfig(self, filename=None, instrumentNames=None, mode='reload', loadIfNotLoaded=False):
        """
        Loads from a file and restores the config of the instruments in instrumentNames (or all instruments in config if instrumentNames is None).
        If loadIfNotLoaded is true, also loads the instruments if necessary.
        """
        if filename is None:
            filename = __configsDir__ + '/' + __lastConfigFilename__
        configFile = open(filename)
        config = yaml.load(configFile.read())
        configFile.close()
        self.restoreConfig(config, instrumentNames, mode, loadIfNotLoaded)

    def _removeInstrument(self, instrument, tryDelete=False):
        """
        Private function removing an instrument from the managed intruments.
        See docstring of public function removeInstruments()
        """
        i = self._instruments.instrumentIndex(instrument)
        if i is not None:
            inst = self._instruments.pop(i)
            if tryDelete:
                del inst

    def removeInstruments(self, instrumentOrInstrumentList, tryDelete=False):
        """
        Removes the instruments specified by insrumentList from the managed intruments.
        instrumentOrInstrumentList: either
        - an instrument of type Instr
        - an instrument name
        - an index in list self._instruments
        - a list of instruments of type Instr
        - a list of intrument names
        - a list of index in list self._instruments
        tryDelete: whether to try to delete the instrument in the instrument handle
        WARNING: instrument will be deleted from memory only if no other reference to it exists in the python shell.
        """
        if isinstance(instrumentOrInstrumentList, list):
            # replace first any index by its corresponding instrument
            instrumentOrInstrumentList = [self._instruments[instrument] if isinstance(
                instrument, int) else instrument for instrument in instrumentOrInstrumentList]
            for instrument in instrumentOrInstrumentList:
                self._removeInstrument(instrument, tryDelete)
        else:
            self._removeInstrument(instrumentOrInstrumentList, tryDelete)
        self.saveCurrentConfigInFile()
        self.notify('removed_instruments', None)

    # Locating frontpanel modules

    def findFrontPanelModule(self, instrument):
        """
        Returns the frontpanel file corresponding to the instrument specified by itself, its name, or its index in the instrument list.
        The frontpanel file will be (in order):
        - the instrument file if it contains a Panel class definition;
        - a file at the same location as the instrument file with a name instrument_Panel.py instead of instrument.py;
        - a file instrument_Panel.py anywhere in the search pathes (not implemented yet)
        - None if not found
        """
        panelPath = None
        self.debugPrint('in InstrumentMgr.frontPanel(', instrument, ')')
        inst = None
        index = self._instruments.instrumentIndex(instrument)
        if isinstance(index, int):
            inst = self._instruments[index]
        instrument = inst
        if isinstance(instrument, (RemoteInstrument)):
            pass  # Strategy to load frontPanel for remote instrument is to be defined
        elif instrument.loadInfo['fullPath'] is not None:
            fullPath = instrument.loadInfo['fullPath']
            path, basename = os.path.split(fullPath)
            basename, extension = os.path.splitext(basename)
            print path, basename, extension
            attemptPath = path + '\\' + basename + '_panel' + '.py'
            if os.path.isfile(attemptPath):
                panelPath = attemptPath
        return attemptPath

        """frontpanelModule = __import__(module, globals(), globals(), [moduleName], -1)  # gets the module
        # reloads it in case it has changed
        reload(frontpanelModule)
        frontpanelModule = __import__(module, globals(), globals(), [moduleName], -1)  # and re import the new code
        # all instrument frontpanel should be of the Panel() class.
        # Instantiates the frontPanel and lets it know its associated instrument
        frontpanel = frontpanelModule.Panel(handle['instrument'])
        frontpanel.setWindowTitle("%s front panel" % name)
        print 'No frontPanel could be loaded for instrument ' + name + '.'
        """


class RemoteInstrumentMgr():
    """
    Manages the loading of, reloading of, and calls to instruments served by an instrument server.
    """

    def __init__(self):
        # create an instrument manager as a property of the remoteManager (on the server side)
        self._manager = InstrumentMgr()

    def __getattr__(self, attr):
        """
        This overidden __getattr__(attr) looks for the attribute attr in self.manager
        rather than in self (attr is assumed to be callable).
        If attr is found, the method returns a pure fonction of any arguments that:
            - returns true if attr returns a result;
            - returns false otherwise.
        Like this, a call to RemoteInstrumentMgr.attr(*args, **kwargs) will call
        InstrumentMgr.attr(*args, **kwargs) and return True or False
        """
        if hasattr(self._manager, attr):
            attr = getattr(self._manager, attr)
            return lambda *args, **kwargs: True if attr(*args, **kwargs) else False

    def dispatch(self, instrument, attribute, args=[], kwargs={}):
        """
        Dispatches an attribute (callable or not) to an instrument, with possibly arguments
         and keyword arguments for a callable attribute. Returns the result of the dispatch.
        """
        self.debugPrint('in RemoteManager.dispatch(', instrument, ',', attribute, ')')
        instr = self._manager.getInstrument(instrument)
        if attribute == 'ask':
            request = 'instr.' + str(*args)
            try:
                return eval(request)
            except Exception as e:
                raise valueError(('RemoteInstrumentMgr error evaluating %s :' % request) + str(e))
        elif attribute == 'evalByServer':
            return eval(*args)
        else:
            attrib = getattr(instr, attribute)     # built instr.command
            if callable(attrib):                   # if it is a method :
                return attrib(*args, **kwargs)     # return its evaluation with arguments  *args and **kwargs
            else:                                  # else
                return attrib                      # return simply the non callable attribute

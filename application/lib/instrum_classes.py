"""
Some convenience classes for managing instruments.
"""

import traceback
import socket
import inspect
import os.path
import yaml

try:
    import win32com.client
    import pythoncom
except:
    print 'Cannot import win32com.client or pythoncom'

try:
    from pyvisa import visa, vpp43
    from visa import VI_ERROR_CONN_LOST, VI_ERROR_INV_OBJECT, VisaIOError, Error, instrument
except:
    print 'Cannot import visa and/or vpp43 from pyvisa.'

from application.lib.base_classes1 import *
from application.lib.com_classes import *


class Instrument(Debugger, ThreadedDispatcher, Reloadable, object):
    """
    The generic Insrument class (also ThreadedDispatcher):
      - has access to its class (getClass()), its module (getModule), and its source file (getSourceFile())
      - has a name given at creation (name())
      - has a dictionary of parameters (parameters()).
        This dictionary may be used to store the current state of the instrument, or other parameters.
      - has a current state (currentState())
      - has a dictionary of states stored by saveState(stateName), accessed by state(stateName), and removed by removeState(stateName).
      - can save to a file the current state by saveStateInFile(filename) or a stored state by saveStateInFile(filename,stateName=stateName)
      - can restore itself in a previously stored state by restoreState(stateName), an empty method that should be overiden for each particular instrument.
    Note 1: If your python Instrument represents a piece of hardware having already state saving capability, overide saveState, removeState and restoreState,
    and don't use other state managemet methods.
    Note 2: an instrument does not own any GUI frontpanel. A single or several frontpanels, local or distant, can be used to interact with the instrument as any other piece of python code.
    """

    def __init__(self, name=None):  # One should always pass a name to instantiate an instrument
        """
        Private class creator initializing the name and an empty list of states.
        """
        Subject.__init__(self)
        Debugger.__init__(self)
        ThreadedDispatcher.__init__(self)
        self.setName(name)          # the only name of the instrument that the instrument knows.
        self._states = dict()       # dictionary of states of the instrument.
        self._params = dict()
        self.daemon = True
        self.initialized = False    # boolean value indicating that the initialize function was run without error

    def initialize(self, *args, **kwargs):
        """
        Instrument initialization.
        (Overide this function in each particular instrument sub-class.
        WARNING 1: Avoid changing the instrument name self._name in this function).
        WARNING 2: Always keep the 'self._initialized = True' line at the end.
        """
        self.initialized = True  # boolean value indicating that the initialize function was run without error

    def __str__(self):
        return "Instrument \"%s\"" % self.name()

    def __call__(self, request):
        """
        An instrument instr is callable with instr(requestString) = eval('instr.'+requestString)
        Example: instr.methodLeve1().methodLevel2() can be replaced by instr('methodLeve1().methodLevel2()')
        This alternative syntax happens to be useful in code editors.
        """
        return eval('self.' + request)

    # Access to private property attributes

    def name(self):
        """
        Returns the name of the instrument.
        """
        return self._name

    def setName(self, name):
        """
        Sets the name or renames the instrument
        """
        self._name = name

    def parameters(self):
        """
        Returns the dictionary of parameters.
        (Overide this function in each particular instrument sub-class if needed).
        """
        # insert code here to fill self._params() if necessary
        return self._params

    # Access to class, module, filename, and source code.

    def getModule(self):
        """
        Returns the module with instrument's code.
        """
        return inspect.getmodule(self)

    def getClass(self):
        """
        Returns the class of the instrument.
        """
        return self.__class__

    def getSourceFile(self):
        """
        Returns the file coding the instrument.
        """
        return inspect.getsourcefile(self.getClass())

    def getsource(self):
        """
        Returns the python code of the instrument.
        """
        return inspect.getsource(self.getClass())

    def getInitializationArgs(self):
        """
        Returns the tuple (argnames, kwargs) with the list of argument names and the dictionary of the keyword arguments.
        Example: (['arg1', 'arg2'],{kword1:'toto', kword2: 2, kword3: [1,2,3]})
        """
        argNames, kwargs = [], {}
        try:
            args, varargs, keywords, defaults = argspec = inspect.getargspec(self.initialize)
            try:
                args.remove('self')
            except:
                pass
            l1, l2 = 0, 0
            if args is not None:
                l1 = len(args)
            if defaults is not None:
                l2 = len(defaults)
            if args is not None:
                argNames = args[:l1 - l2]
            if defaults is not None:
                kwargNames = args[- l2:]
                kwargs = dict(zip(kwargNames, defaults))
        except Exception as e:
            print "Could not determine initialization arguments from instrument's code: " + str(e)
        return (argNames, kwargs)

    # Management of instrument states.

    def currentState(self):
        """
        Instrument class method that builds an object (often a dictionary) representating the actual state of the instrument.
        Default behavior is to return self.parameters().
        Overide this method to implement other state representation.
        """
        return self.parameters()

    def state(self, stateName):
        """
        Instrument class method that returns the state with name stateName from the dictionary of instrument states.
        Returns None if statename does not exist.
        """
        state = None
        if stateName in self._states:
            state = self._states[stateName]
        return state

    def saveState(self, stateName=None):
        """
        Adds or overwrites the current state of the instrument to the dicitonanry of states, using stateName or an automatic name if None.
        """
        if stateName is None:
            stateName = 'state_' + str(len(self._states))
        state = self.currentState()
        self._states[stateName] = state
        return state

    def removeState(self, stateName=None):
        """
        Instrument class method that removes state with name stateName (or random state if stateName='any') from the dictionary of states.
        """
        if len(self._states) > 0:
            if stateName == 'any':
                stateName = self._states.keys()[0]
            if stateName in self._states:
                self._states.pop(stateName, None)

    def restoreState(self, state):
        """
        Restores the instrument to the given state.
        If the state has been stored in the state dictionary, programmer should get it first by calling the state(stateName) method.
        (Overide this empty method in each particular instrument subclass).
        """
        pass

    def saveStateInFile(self, filename, stateName=None):
        """
        Instrument class method that saves a state with name stateName (or current state if stateName is None ) to a file.
        state is the object representating the actual state of the instrument, and not its name.
        If your python Instrument represents a piece of hardware having already state saving saving capability, overide saveState, removeState and restoreState,
        and don't use other state managemet methods.
        """
        filename = str(filename)
        if stateName is None:
            state = self.currentState()
        else:
            state = self.state(stateName)
        if state is not None:
            stateString = yaml.dump(state)
            stateDir = os.path.dirname(filename)
            if not os.path.exists(stateDir):
                os.mkdir(stateDir)
            file = open(filename, "w")
            file.write(stateString)
            file.close()
        return state

    def loadStateFromFile(self, filename):
        """
        Instrument class method that loads and returns an instrument state from a file.
        """
        stateFile = open(filename)
        state = yaml.load(stateFile.read())
        stateFile.close()
        return state

    def restoreStateFromFile(self, filename):
        """
        Restores the instrument to a state saved in the file fileName.
        """
        state = self.loadStateFromFile(filename)
        self.restoreState(state)
        return state

    def states():
        return self._states

    def stateNames():
        return self._states.keys()


class CompositeInstrument(Instrument):
    """
    Instrument with a dictionary of children instruments, and possibly a handle to an instrument manager.
    """

    def __init__(self, name, instrumentManager=None, childrenDict=None):
        """
        CompositeInstrument creator.
        Always pass a name for the instrument.
        """
        Instrument.__init__(self, name)
        # a composite instrument should not instantiate an intrument manager
        # but use an existing one passed to it.
        self._instrumentManager = instrumentManager
        self._children = {}                         # list of children instruments objects
        if childrenDict is not None:
            self.addChildren(childrenDict)

    def setManager(self, instrumentManager):
        """
        CompositeInstrument method that sets an instrument manager for the instrument and its children instrument.
        """
        self._instrumentManager = instrumentManager

    def manager(self):
        """
        CompositeInstrument method that returns its instrument manager.
        """
        return self._instrumentManager

    def initialize(self, *args, **kwargs):
        """
        CompositeInstrument initialization.
        (overide this method for each particular composite instrument)
        Use super(SubClass, self).initialize(*args,**kwargs) to run the code below
        """
        if 'children' in kwargs:
            self.addChildren(kwargs['children'])

    def removeChildren(self, listOfChildrenName):
        """
        CompositeInstrument method that removes a list of children instruments from its children instruments dictionary.
        """
        for childName in listOfChildrenName:
            self.removeChild(childName)

    def removeChild(self, childName):
        """
        CompositeInstrument method that removes a child instrument from its children instruments dictionary.
        """
        if childName in self._children.keys():
            self._children.remove(childName)
        else:
            print 'No child instrument ' + childName + ' in composite instrument ' + self.name

    def children(self):
        '''CompositeInstrument method that returns its children instruments dictionary.'''
        return self._children

    def childrenNames(self):
        """
        CompositeInstrument method that returns the names (also dictionary keys) of its children instruments.
        """
        return self._children.keys()

    def child(self, name):
        """
        CompositeInstrument method that returns its child instrument specified by name.
        """
        if name in self._children.keys():
            return self._children[name]
        else:
            print 'No child instrument ' + name + ' in composite instrument ' + self.name + '.'
            return None

    def addChildren(self, dictionary):
        '''
        CompositeInstrument method that adds a dictionary of children instrument to its children instruments dictionary.
        dictionary has the form {"instrument_name_1": instr1,"instrument_name_2": instr2,...} where
          instri is an instrument object or None.
          In case instri is None, addChildren first tries to use its instrument manager if it is defined,
          and second tries to load directly the instrument from the same location as that of its own module.
        '''
        for name in dictionary.keys():
            self.addChild(name, dictionary[name])

    def addChild(self, name, instrument=None, baseClass=None):
        """
        CompositeInstrument method that adds an instrument to the dictionary of its children instruments (if child not already present).
          - name is the name of the instrument to be added
          - instrument is an instrument object or None.
            In case instrument is None, addChild tries to load the child instrument:
              1) using its instrument manager if it is defined and already knows the instrument;
              2) from a module with name baseClass at the same location as the composite instrument, if baseClass is different from None;
              3) from a module with name name if baseClass is None.
        This method has limited capabilities in loading sub-instruments:
          It cannot for instance use remote instruments through a server;
            => Use an InstrumentManager known by the present composite instrument if you want this feature.
          It does not call the initialize method of the sub-instrument;
            => Call this initialize method afterwards if needed.
        """
        if name in self._children:
            print name + ' is already a child instrument of instrument ' + self._name
            return
        elif isinstance(instrument, (Instrument, RemoteInstrument)):
            pass
        elif self._instrumentManager is not None and self._instrumentManager.hasInstrument(name):
            instrument = self._instrumentManager.handle(name).instrument()
        else:
            try:
                if baseClass is None:
                    baseClass = name
                # debug here until a module in the smae directory is found
                module = __import__(baseClass, globals(),
                                    globals(), ["Instr"], 0)
                instrument = module.Instr(name=name)  # instantiation
            except:
                raise
        self._children[name] = instrument

    def __getattr__(self, attr):
        """
        CompositeInstrument private method that redefines an unknown attribute as a child instrument if it exists.
        """
        if attr in self._children:
            return self.child(attr)


class VisaInstrument(Instrument):

    """
    A class representing an instrument that can be interfaced via NI VISA protocol.
    """

    def __init__(self, name='', visaAddress=None, term_chars=None, testString='', **kwargs):
        """
        Initialization
        """
        # print '\tin VisaInstrument.__init__ with name, visaAddress and term_chars = ', (name, visaAddress, term_chars)
        Instrument.__init__(self, name)
        self._visaAddress = visaAddress
        self._handle = None
        self._term_chars = term_chars
        try:
            self.getHandle()
        except:
            print '\tERROR: Could not get handle to Visa instrument %s at address %s' % (name, visaAddress)
            return
        try:
            if self._handle is not None and self._term_chars is not None:
                self._handle.term_chars = term_chars
        except:
            print '\tERROR: Could not set Visa instrument %s at address %s with termination characters %s' % (name, visaAddress, term_chars)
        if testString != '':
            try:
                print '\t' + self.ask(testString)
            except:
                print '\tERROR: Could not get answer from Visa instrument %s at address %s when asking %s' % (name, visaAddress, testString)

    def getHandle(self, forceReload=False):
        """
        Return the VISA handle for this instrument.
        If the VISA connection was lost, it reopens the VISA handle.
        """
        if forceReload or self._handle is None:
            try:
                if self._handle is not None:
                    try:
                        self._handle.close()
                    except:
                        pass
                    self._handle = None
            except:
                pass
            self._handle = visa.instrument(self._visaAddress)
        return self._handle

    def executeVisaCommand(self, method, *args, **kwargs):
        """
        This function executes a VISA command.
        """
        try:
            returnValue = method(*args, **kwargs)
            return returnValue
        except Error as error:
            print 'Visa call error => Invalidating Visa handle.'
            self._handle = None
            raise

    def __getattr__(self, attr):
        """
        Forwards all unknown attribute calls to the VISA handle: instrument.attr becomes
        """
        handle = self.getHandle()
        if hasattr(handle, attr):
            attr1 = getattr(handle, attr)
            if hasattr(attr, '__call__'):
                return lambda *args, **kwargs: self.executeVisaCommand(attr1, *args, **kwargs)
            else:
                return attr1
        raise AttributeError('No such attribute: %s' % attr)


import pickle
# implements an algorithm for turning an arbitrary Python object into a series of bytes (or chars) or vice and versa.
import cPickle
from struct import pack, unpack

_DEBUG = False


class Command:
    """
    Class for a command to be sent as a string to a remote instrument through a server of instruments
    """

    def __init__(self, name=None, args=[], kwargs={}):
        self._name = name
        self._args = args
        self._kwargs = kwargs

    def __str__(self):
        return str([self._name, self._args, self._kwargs])

    def name(self):
        return self._name

    def args(self):
        return self._args

    def kwargs(self):
        return self._kwargs

    def toString(self):
        # encode the Python object into a string of bytes (or equivalently
        # chars)
        pickled = cPickle.dumps(self, cPickle.HIGHEST_PROTOCOL)
        s = pack('l', len(pickled))
        return s + pickled

    # decorator. Why using this here? It is not reused by other methods. Not
    # clear...
    @classmethod
    def fromString(self, string):
        m = cPickle.loads(string)  # decode the string as a Python object
        return m


class ServerConnection(object):

    """
    Class for a particular connection to a server of instruments
    """

    def __init__(self, ip, port):
        if _DEBUG:
            print 'in client serverConnection.__init__  with ip=', ip, 'and port=', port
        self._ip = ip
        self._port = port
        self._socket = self.openConnection()

    def openConnection(self):
        if _DEBUG:
            print 'in client serverConnection.openConnection() with ip=', self._ip, 'and port=', self._port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.connect((self._ip, self._port))
        return sock

    def ip(self):
        return self._ip

    def port(self):
        return self._port

    def _send(self, commandName, args=[], kwargs={}):
        """
        Method that both sends a command to an instrument server through a network socket, and receives a response from the server.
        """
        # We set some socket options that help to avoid errors like 10048
        # (socket already in use...)
        if _DEBUG:
            print 'in client serverConnection._send() with commandName=', commandName, ' args=', args, 'and kwargs=', kwargs
        command = Command(name=commandName, args=args, kwargs=kwargs)
        sock = self._socket
        try:
            # sends the command as a serialized string
            sock.send(command.toString())
            # reads 4 bytes to get a string containing the number of available
            # following bytes
            lendata = sock.recv(4)
            if len(lendata) == 0:                   # if no bytes areceived => connection lost
                raise Exception(
                    'Connection to server %s port %d failed.' % (self._ip, self._port))
            # unpack this 4 bytes using format 'l' and keep the length to be
            # read.
            length = unpack('l', lendata)[0]
            received = sock.recv(length)            # read length bytes
            binary = received
            # if you get the beginning of the data, waits for all bytes
            while len(received) > 0 and len(binary) < length:
                received = sock.recv(length - len(binary))
                binary += received
            if len(binary) == 0:                    # if you don't get anything, return
                return None
            # Now deserialize the data received to rebuild the python object
            response = Command().fromString(binary)
            if response is None:                    # No response => no connection to server
                raise Exception(
                    'Connection to server %s port %d failed.' % (self._ip, self._port))
            if response.name() == 'exception' and len(response.args()) > 0:
                # we receive an error from the server and raise it here on the
                # client side
                raise response.args()[0]
            if _DEBUG:
                print 'in client serverConnection._send() and getting response=', response
            # we return the valid response
            return response.args()[0]
        except:
            # if an error occured anywhere we reopen the connection (it is
            # strange because if an error occured on the distant instrument,
            # why reopening the connection)
            self._socket = self.openConnection()
            raise

    # Any attributes other than the ServerConnection's methods above will be
    # 'routed' to ServerConnection._send with its arguments.
    def __getattr__(self, attr):
        if _DEBUG:
            print 'in client serverConnection.__getattr__() with attr=', attr
        return lambda *args, **kwargs: self._send(attr, args, kwargs)


class RemoteInstrument(Debugger, ThreadedDispatcher, Reloadable, object):
    """
    Class that represents locally a distant remote instrument, and that is able to communicate with it through a ServerConnection.
    (does not inheritate from the Instrument class)
    """

    def __init__(self, name, server, baseclass=None, args=[], kwargs={}, forceReload=False):

        Debugger.__init__(self)
        ThreadedDispatcher.__init__(self)
        Reloadable.__init__(self)
        # server is a ServerConnection (indicated by the instrument manager)
        # that '_send's methods of a single Instrument accross the server
        # initialize the serverConnection with a particular instrument
        server.initInstrument(name, baseclass, args, kwargs, forceReload)
        # memorize the serverConnection
        self._server = server
        self._name = name
        self._baseclass = baseclass
        self._args = args
        self._kwargs = kwargs

    def dispatch(self, command, *args, **kwargs):
        # This is an ATTEMPT by DV to clean the strange dispatch behavior of remote instruments.
        # Indeed, without this overidden method, the use of dispatch in a remote instrument was directly calling the dispatch method of the ThreadedDispatcher,
        # then was coming back to the __getattr__ twice, and then to the targetted remoteDispatch below.
        # Here we directly go from dispatch to remoteDispatch by overrinding
        # dispatch
        """
        RemoteInstrument overriden 'dispatch' method of original 'ThreadedDispatcher'.
        Aliases 'remoteDispatch'.
        """
        self.debugPrint('in remoteInstrument.dispatch() with command = ',
                        command, ' args=', args, ' and kwargs=', kwargs)
        return self.remoteDispatch(command, args, kwargs)

    def remoteDispatch(self, command, *args, **kwargs):
        """
        Private method that sends a command to a remote instrument through the serverConnection.
        This method is called only if the command is not a RemoteInstrument's method (i.e. of RemoteInstrument, ThreadedDispatcher,Debugger).
        Consequently, it should not be called on remoteInstrument.dispatch(...) since 'dispatch' belongs to ThreadedDispatcher.
        """
        self.debugPrint('remoteInstrument.remoteDispatch() sending command = ',
                        command, ' to ', self._name, 'with args=', args, ' and kwargs=', kwargs)
        result = self._server.dispatch(self._name, command, *args, **kwargs)
        self.debugPrint('remoteDispatch notifying ', command, result)
        # once the result is sent back, we notify the command and its result to
        # all observers of this remote instrument.
        self.notify(command, result)
        return result

    def __str__(self):  # Standard method called when printing
        return "Remote Instrument \"%s\" on server %s:%d" % (self.name(), self._server.ip(), self._server.port())

    def name(self):
        """
        We redefine name, since it is already defined as an attribute in Thread
        """
        return self.remoteDispatch('name')

    def saveStateInFile(self, filename, stateName=None):
        """
        We copy here the saveStateInFile method of the Instrument class in order to save the file on the RemoteInstrument machine where the file path and name were defined.
        """
        filename = str(filename)
        if stateName is None:
            state = self.currentState()
        else:
            state = self.state(stateName)
        if state is not None:
            stateString = yaml.dump(state)
            stateDir = os.path.dirname(filename)
            if not os.path.exists(stateDir):
                os.mkdir(stateDir)
            file = open(filename, "w")
            file.write(stateString)
            file.close()

    def loadStateFromFile(self, filename):
        """
        We copy here the loadStateFromFile method of the Instrument class in order to load the file on the RemoteInstrument machine where the file path and name were defined.
        """
        stateFile = open(filename)
        state = yaml.load(stateFile.read())
        stateFile.close()
        return state

    def restoreStateFromFile(self, filename):
        """
        We copy here the restoreStateFromFile method of the Instrument class in order to load the file on the RemoteInstrument machine where the file path and name were defined.
        """
        state = self.loadStateFromFile(filename)
        self.restoreState(state)

    def __getitem__(self, key):
        return self.remoteDispatch('__getitem__', [str(key)])

    def __setitem__(self, key, value):
        self.debugPrint('Setting ', key)
        return self.remoteDispatch('__setitem__', [key, value])

    def __delitem__(self, key):
        return self.remoteDispatch('__delitem__', [key])

    def getAttribute(self, attr):
        self.debugPrint(
            'in remoteInstrument.getAttribute(attr) with attr = ', attr)
        return self.remoteDispatch('__getattribute__', [attr])

    def setAttribute(self, attr, value):
        return self.remoteDispatch('__setattr__', [attr, value])

    # any call remoteInstrument.method(args,kwargs) with method different from RemoteInstrument's methods will be treated by __getattr__ below and be transformed into remoteDispatch('method',args,kwargs)
    # but a call remoteInstrument.property is transformed into the meaningless function lambda *args,**kwargs:remoteDispatch(property,args,kwargs)
    # one should treat differently methods and properties
    def __getattr__(self, attr):
        self.debugPrint(
            'in remoteInstrument.__getattr__(attr) with attr = ', attr)
        return lambda *args, **kwargs: self.remoteDispatch(attr, args, kwargs)

    def __call__(self, request):
        """
        redefining instr(requestString) to instr.ask(requestString) for remote instruments that don't work well when using instr.request
        Example: Replace instr.methodLeve1().methodLevel2() by instr('methodLeve1().methodLevel2()')
        """
        return self.ask(request)

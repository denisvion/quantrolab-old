"""
This is a small script that exposes a remote instrument manager via a TCP/IP connection.
"""

import socket,threading,pickle,SocketServer,numpy,time,sys,os,weakref,traceback
from struct import *

_DEBUG = False

from application.helpers.intrumentmanager.instrumentmgr import *
from application.lib.instrum_classes import *

class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):
	"""
	This class is the server handler.
	Its handle method
		1) translates the input string into an input command
		2) propagates the input command to the remoteManager
		3) gets the result and put it in a return command
		4) translates this command into a string and send it to the client.
	Note that the input command is either dispatch or an attribute of the instrument manager remoteManager.manager.
	"""
	manager = None
	_DEBUG=False

	def handle(self):
		while True:
			try:
				lendata = self.request.recv(4)                # requests 4 bytes
				if len(lendata) == 0:                         # gives up and returns if nothing is received
					return None
				length = unpack("l",lendata)[0]               # determines the number of bytes to read
				received = self.request.recv(length)          # request the byte string
			except socket.error:
				#The connection was closed...
				return
			binary = received                               # wait for the whole string
			while len(received)>0 and len(binary) < length:
				received = self.request.recv(length-len(binary))
				binary+=received
			m = Command().fromString(binary)                # regenerates the python command from the byte string (the command Class and its method fromString are defined in the 'classes' module)
			if m is None:                                   # gives up and returns if command is None
				return
			if _DEBUG:  print "Server received command ",m
			if hasattr(self.manager,m.name()):              # if the command name is an attribute of remoteManager (either dispatch or also an attribute of its instrument manager)
				method = getattr(self.manager,m.name())       # get the attribute from the remoteManager, which returns either dispatch or a pure function lambda *args,**kwargs : True if attr(*args,**kwargs) else False, with attr an attribute of the instrument manager
				try:
					result = method(*m.args(),**m.kwargs())     # try to call the pure function that runs the command and returns True or False
					returnMessage = Command(name = "return",args = [result]) # puts the result in a new return Command
					if _DEBUG:  print "Server sending output command ",returnMessage
					self.request.send(returnMessage.toString()) # serializes and sends back to client
				except Exception as exception:                # manages errors
					print "An exception occured:"
					print "name: %s" % str(m.name())
					print "args: %s" % str(m.args())
					print "kwargs: %s" % str(m.kwargs())
					print "-"*40
					traceback.print_exc()
					print "-"*40
					try:
						returnMessage = Command(name = "exception",args = [exception,traceback.format_exc()])
					except:
						returnMessage = Command(name = "exception",args = [Exception("Unpickable exception!"),traceback.format_exc()])
					finally:
						self.request.send(returnMessage.toString())       

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
		pass
		
"""def client(ip, port, message): # this is to be removed
	conn  = ServerConnection(ip,port)
	print conn.instrument("qubit1mwg","anritsu_mwg",[],{},False)
	for i in range(0,10):
		print conn.dispatch("qubit1mwg","frequency")
"""

myManager = RemoteInstrumentManager() # instantiate a remote manager
ThreadedTCPRequestHandler.manager = myManager # declares that any ThreadedTCPRequestHandler has a property manager equal to the already existing RemoteManager

def startServer():
		# Port 0 means to select an arbitrary unused port
		if len(sys.argv) >= 2:
			hostname = sys.argv[1]
		else:
			hostname = "localhost"
		HOST, PORT = hostname, 8000
		server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler) # instantiates the ThreadedTCPServer.
																																				# Pass the name of class handler (ThreadedTCPRequestHandler) so that it will be instantiated by the init function of ThreadedTCPServer
		ip, port = server.server_address
		print "Running on ip %s, port %d" % (ip,port)
		server_thread = threading.Thread(target=server.serve_forever)
		server_thread.setDaemon(True)
		server_thread.start()                                               # and starts it in a thread
		print "Server loop running in thread:", server_thread.getName()
		while True: # test if close is requested
			try:
				time.sleep(1)
			except KeyboardInterrupt:
				break
		print "Shutting down..."
		server.shutdown()

if __name__ == "__main__":
	startServer()
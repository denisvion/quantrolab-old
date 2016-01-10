import sys
import os
import weakref
import SocketServer

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

sys.path.append(os.path.realpath('.'))
sys.path.append(os.path.realpath('../'))

from application.helpers.instrumentsmanager.instrumentmgr import InstrumentManager

# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

class AsyncXMLRPCServer(SocketServer.ThreadingMixIn,SimpleXMLRPCServer): pass

class MyFuncs:
    def div(self, x, y):
        return x // y

if __name__ == '__main__':
  myManager = InstrumentManager()
  server = AsyncXMLRPCServer(("localhost", 8000),requestHandler=RequestHandler,allow_none = True)
  server.register_introspection_functions()
  server.register_instance(RemoteInstrumentManager(myManager))

  server.serve_forever()

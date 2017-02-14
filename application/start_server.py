import sys
import os
import os.path

sys.path.append(os.path.realpath(os.path.dirname(__file__) + '/../'))
sys.path.append(os.path.realpath(os.path.dirname(__file__) + '/../../'))
sys.path.append(os.path.realpath(os.path.dirname(__file__) + '/../../libs/'))
print "\nWelcome to QUANTROLAB INSTRUMENT SERVER"
print
print "Search pathes are:"
for path1 in sys.path:
    print "  " + path1
print

print "Importing server.pickle_server.startServer()"
from server.pickle_server import startServer

if __name__ == '__main__':
    print "calling startServer()"
    startServer()

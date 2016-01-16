import sys
import getopt
import time

from application.lib.instrum_classes import *


class Instr(Instrument):

    def initialize(self, address='192.168.0.61', port=11061, thermoVarIndices=[5, 16, 22]):
        self.address = address
        self.port = port
        self.thermoVarIndices = thermoVarIndices
        if DEBUG:
            print 'Initializing mmr3_module with address' + address + ' and port ' + str(port)

    def parameters(self):
        params = dict()
        return params

    def saveState(self, name):
        return self.parameters()

    def getVar(self, varIndex=1):
        """
        Returns the value of variable varIndex
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect((self.address, self.port))
        sock.send('2;7;' + str(varIndex) + '\n')
        string = ''
        while True:           # progress until \n
            char = sock.recv(1)
            if char == '\n':
                break
            elif char == ';':     # and empty the string at each ';' to end with the last value, which is the length of the variable data
                string = ''
            elif char != '\r':
                string += char
        # receive the length obtained above, split at each ';', and keep the
        # third element which is the variable's value
        value = float(sock.recv(int(string)).split(';')[2])
        sock.close()
        return value

    def temperature(self, thermometerIndex=1):
        if 1 <= thermometerIndex <= len(self.thermoVarIndices):
            return self.getVar(self.thermoVarIndices[thermometerIndex - 1])
        else:
            return -1

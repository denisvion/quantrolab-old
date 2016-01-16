import sys
import getopt

from application.lib.instrum_classes import *


class Instr(Instrument):

    def temperature(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            sock.connect((self.host, self.port))
            return float(sock.recv(1024))
        except:
            raise
            return 0

    def parameters(self):
        params = dict()
        params['temperature'] = self.temperature()
        return params

    def initialize(self, address="132.166.19.2", port=444):
        try:
            if DEBUG or True:
                print "Initializing temperature sensor"
            self.host = address
            self.port = port
        except:
            self.statusStr("An error has occured. Cannot initialize sensor.")
            print "An error has occured. Cannot initialize sensor."

    def saveState(self, name):
        return self.parameters()

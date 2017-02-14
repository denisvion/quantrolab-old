"""
This is a small script that exposes a remote instrument manager via a TCP/IP connection.
"""

import socket
import threading
import pickle
import SocketServer
import numpy
import time
import sys
import os
import weakref
import traceback
from struct import *

_DEBUG = False


def startServer():

    print "Type Ctrl+C to quit."
    while True:  # test if close is requested
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break
    print "Shutting down..."

if __name__ == "__main__":
    startServer()

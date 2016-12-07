# *******************************************************************************
# # DataManager Singleton class which can be used to keep track of datacubes.   *
# # Just call addDatacube() to add a datacube to the DataManager.               *
# # gui.datamanager.DataManager                                                 *
# #  provides a graphical frontend of the DataManager class.                    *
# *******************************************************************************

# Imports

import sys
import getopt
import os.path
import traceback
from threading import Thread
import PyQt4.uic as uic

from application.lib.base_classes1 import Singleton
from application.lib.com_classes import ThreadedDispatcher
from application.lib.helper_classes import Helper

# This is a class that manages datacubes


class DataMgr(Singleton, ThreadedDispatcher, Helper):
    """
    The DataMgr (data manager) is a singleton class that manages a set of datacubes.
    It is a Reloadable Singleton (only one instance can exist at a given time).
    It is a Subject and an Observer that can receive and send notifications.
    It is a Quantrolab's Helper.
    Its methods are :
      - addDatacube and removeDatacube to add or remove a datacube to the DataManager;
      - datacubes to get the list of managed datacubes;
      - clear to empty the list of managed datacubes.
    """

    def __init__(self, name=None, parent=None, globals={}):
        if hasattr(self, "_initialized"):
            return
        Singleton.__init__(self)
        Helper.__init__(self, name, parent, globals)
        ThreadedDispatcher.__init__(self)
        self._datacubes = []
        self._initialized = True

    def datacubes(self):
        """
        Returns the datacubes.
        """
        return self._datacubes

    def addDatacube(self, datacube, checkTopLevelOnly=False):
        """
        Adds a datacube to the data manager if not already present in the datamanager if checkTopLevelOnly is true,
        or at any child level of the datacubes present otherwise.
        """
        cubes = list(self._datacubes)
        if not checkTopLevelOnly:
            family = []
            for cube in cubes:
                family.extend(cube.familyMembers())
        cubes.extend(family)
        if datacube not in cubes:
            self._datacubes.append(datacube)
            self.debugPrint(
                'DataManager notifying "addDatacube" for datacube', datacube)
            # datacube.attach(self)
            self.notify("addDatacube", datacube)
            return True

    def removeDatacube(self, datacube, deleteCube=False):
        """
        Removes a datacube from the data manager and delete it from memory if deleteCube=True.
        The deletion will be propagated to all descendants by the removeChild function of the datacube
        """
        cubes = self._datacubes
        if datacube in cubes:                             # the cube is at the top level of the hyerarchy
            del cubes[cubes.index(datacube)]
            self.debugPrint(
                'DataManager notifying "removeDatacube" for datacube', datacube)
            self.notify("removeDatacube", datacube)
            if deleteCube:
                del datacube
        else:                                             # the cube is not at the top level of the hyerarchy
            parent = datacube.parent()
            # check that it has a parent or ascendent in the datamanager
            while parent is not None and parent not in cubes:
                parent = parent.parent()
            if parent in cubes:                             # give up if the datacube is not managed by the dataManager
                datacube.parent().removeChild(datacube, deleteChildCube=deleteCube)

    def clear(self):
        """
        Removes all datacubes from the data manager.
        """
        self._datacubes = []
        self.debugPrint('DataManager notifying "cleared" ')
        self.notify("cleared")

    ##

    # ########################################################################################################
    # # Below is a function plot to notify a listener like the dataManager frontpanel to plot the datacube.  #
    # # Note that a datacube has methods to call this plot function.                                         #
    # ########################################################################################################

    def plot(self, datacube, *args, **kwargs):
        """
        1) If datacube not already present, adds it to dataManager;
        2) Notify the dataManager frontpanel to plot the datacube in a way possibly defined by additional parameters.
        See the listener response documentation or code to know the enumerated (*args) or named (**kwargs) parameters that can be passed
        """
        self.addDatacube(
            datacube, checkTopLevelOnly=False)  # will add it to the dataManager only if not already present
        self.debugPrint(
            'DataManager notifying ""plot"" for datacube ', datacube)
        # then sends a plot notification with value
        # ((datacube,arg1,arg2,...),{kwarg1:val1,kwarg2:val2,...})
        self.notify("plot", ((datacube,) + args, kwargs))

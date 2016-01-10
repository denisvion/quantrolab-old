# imports
import os,sys,getopt,time,traceback,scipy,scipy.optimize,scipy.interpolate
from numpy import *
from application.lib.instrum_classes import *
from application.lib.datacube import Datacube


class Instr(CompositeInstrument):
  """
  Subclass of a composite instrument for a readout instrument.
  As a composite instrument, a readout instrument has children instruments (like Instrument or VisaInstrument objects),
  and possibly knows an instrument manager managing them.
  The readout instrument manages
    - the generation of excitation signals used for readout
    - the acquisition of signals used for readout
    - the treatment of the acquired signal to generate a readout output
    - a set of readout modes or protocols (dictionary of dictionaries)
    - a time line for each readout mode, encoding the relevant times in the readout process   
  """

  #####################################################
  #  General methods                                  #
  #####################################################

  def initialize(self,*args,**kwargs):
    """
    Initialize instrument.
    """
    super(Instr,self).initialize(*args,**kwargs)  # run first the initialize method of CompositeInstrument class
    self._readoutModes=dict()


  def saveState(self,stateName=None):
    """
    Builds the object describing the current state of the instrument (usually a dictionary), possibly saves it on a media, and returns it.
    Statename is a state identifier that should be stored in the state object for future retrieval.
    """
    pass

  def restoreState(self,directory=None):
    """
    Restores the state of the instrument.
    """
    pass

  #########################################
  #  Readout modes and time lines         #
  #########################################

  def readoutModes(self):
    """
    Readout instrument method that returns the readoutModes dictionary of readoutMode dictionaries.
    """
    return self._readoutModes

  def readoutMode(self,readoutModeName):
    """
    Readout instrument method that returns a particular readoutMode dictionary specified by name readoutModeName.
    """
    return self._readoutModes[readoutModeName]

  def addReadoutMode(self,readoutModeName,**kwargs):
    self._readoutModes[readoutModeName]=kwargs


  #########################################
  #  Excitation signal                    #
  #########################################

  

  #########################################
  #  signal acquisition and treatment     #
  #########################################


 


  
          

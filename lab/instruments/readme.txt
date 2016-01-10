###############################################
# QuantroLab\lab\instruments\readme.txt file  #
###############################################

The 'instruments' directory is the default root directory of quantrolab's intruments.
Put all your instruments in this directory or its sub-directories.

The instrument manager is capable of walking in the directory tree.
It will find the instruments and their frontpanels defined in the different python modules.
An instrument is recognized in a module when a class 'Instr' is found.
A frontpanel is recognized in a module and properly asociated to its instrument in either of these two cases:
 - a class 'Panel' is found in the same module as a class 'Instr'
 - a class 'Panel' is found in a module name_panel.py if a module name.py exists and defines a class 'Instr' (name stands here for any valid module name different from __init__.py).
# Start the instruments panel and the data manager
import matplotlib

import sys
from application.ide.coderunner import *
from application.ide.variablepanel import *
reload(sys.modules["application.ide.variablepanel"])
from application.ide.variablepanel import *


def startVariablePanel():

    panel = VariablePanel(globals=gv)
    panel.show()

execInGui(startVariablePanel)

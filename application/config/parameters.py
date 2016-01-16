import sys
import os
import os.path

params = dict()

params['basePath'] = os.path.dirname(
    os.path.abspath(os.path.abspath(__file__) + "/.."))
params['configPath'] = os.path.dirname(os.path.abspath(__file__))
params['directories.resources'] = '/ide/resources'
params['directories.icons'] = '/ide/resources/icons'

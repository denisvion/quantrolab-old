"""
Start ide module
"""
import sys
import os
# parrent folder 'QuantroLab' including also the laboratory folder 'lab'
# and the 'script' folder for user scripts.
rootDir = os.path.realpath(os.path.dirname(__file__) + '/../')
sys.path.append(rootDir)

if __name__ == '__main__':
    # try to find ide_main and call its startIDE() function.
    try:
        from application.ide.ide_main import *
        startIDE()
    # if error trace it back, print it and wait for user acknowledgement.
    except:
        import traceback
        print traceback.format_exc()
        raw_input("Press enter to exit.")

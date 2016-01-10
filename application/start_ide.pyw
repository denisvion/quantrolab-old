import sys,os
# parrent directory 'QuantroLab' including the the directory 'application', 'lab' and 'script' directories.
rootDir=os.path.realpath(os.path.dirname(__file__)+'/../')
sys.path.append(rootDir)

if __name__ == '__main__':
	try:
		from application.ide.ide_main import *
	  	startIDE()
	except:
	    import traceback
	    print traceback.format_exc()
	    raw_input("Press enter to exit.")


    
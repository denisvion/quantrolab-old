import sys,os

# parrent folder 'QuantroLab' including also the laboratory folder 'lab' and the 'script' folder for user scripts.
rootDir=os.path.realpath(os.path.dirname(__file__)+'/../')
sys.path.append(rootDir)

if __name__ == '__main__':
	try:
		from server.pickle_server import *
	  	startServer()
	except:
	    import traceback
	    print traceback.format_exc()
	    raw_input("Press enter to exit.")


    


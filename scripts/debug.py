import os, pyclbr
instrumentsRootDir='lab/instruments'
def findInstrumentModule(instrumentModuleName):
	found = None
	for (dirpath, dirnames, filenames) in os.walk(instrumentsRootDir):
		print dirpath, dirnames, filenames
		# builds a list of all python file names (except _init__.py)
		pyFilenames = [filename for filename in filenames if (os.path.splitext(filename)[1] == '.py' and filename != '__init__.py')]
		print pyFilenames
		pyFilenames = [os.path.splitext(filename)[0] for filename in pyFilenames]
		print pyFilenames
		if instrumentModuleName in pyFilenames:
			try:
				print 'instrumentModuleName=', instrumentModuleName, 'dirpath = ', dirpath 
				# build the class dictionary with the pyclbr python class browser
				dic = pyclbr.readmodule(instrumentModuleName, [dirpath])
				# check that the module contains a class definition Instr in the file and not through an import.
				if 'Instr' in dic and os.path.realpath(dic['Instr'].file) == os.path.join(os.path.realpath(dirpath), instrumentModuleName + '.py'):
					found = (dic['Instr'].module, dic['Instr'].file)
					print 'found=', found
					break  # stop the walk
			except:
				print 'an error occured when trying to read the module.'
			finally:
				pass
	return found
##
print findInstrumentModule('dummy')
##
dic = pyclbr.readmodule('dummy', ['lab/instruments'])
##
print dic
##
print 'Instr' in dic
##
print os.path.realpath(dic['Instr'].file) 
print os.path.join(os.path.realpath('lab/instruments'), 'dummy' + '.py')
##
print os.path.realpath(dic['Instr'].file)
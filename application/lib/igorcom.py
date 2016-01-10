"""
class moduule used to communicate with IgorPro using ActiveX
"""

import traceback,socket,inspect,os.path,yaml

try:
  import win32com.client
  import pythoncom
except:
  print 'Cannot import win32com.client or pythoncom'
        
class IgorCommunicator:
  """
  A class used to communicate with IgorPro using ActiveX
  """
  def __init__(self,new=False):
    """
    Initialization
    """
    try:
      pythoncom.CoInitialize()
      self._app=win32com.client.Dispatch('IgorPro.Application') 
      self._app.Visible=1
    except:
      raise Exception('Unable to load IgorPro ActiveX Object, ensure that IGOR Pro and pythoncom are installed ')
    
  def execute(self, command):
    """
    Execution of single-line command (str)
    Return results (str or None)
    """
    flag_nolog = 0
    code_page = 0
    err_code = 0
    result_tuple = self._app.Execute2(flag_nolog, code_page, command,err_code)
    err_code, err_msg, history, results = result_tuple
    if len(err_msg)>1:
      raise Exception("Active X IgorApp exception: \n  Command : \"" + command +"\"\n  Returns : \""+ err_msg+"\"")
    history=str(history)
    history=history.split('\r')
    return str(results),history
    
  def run(self,commands):
    """
    Execute multi-lines commands, ie list of strings
    return list or results for each single-line
    """
    if len(commands)<1:
      return ''
    results=[]
    for command in commands:
      result=self.execute(command)
      if result != '':
        results.append(result)
    return results

  def __call__(self,commands):
    """
    'smart' alias of run ie. encapsulate commands in [] if commands is a string
    """
    if type(commands) == type('string'):
      return self.run([commands])
    elif type(commands) == type([]):
      return self.run(commands)
    else: raise Exception('IgorApp badly called')

  def dataFolderExists(self,path):
    if path[-1] != ':':
        path+=':'
    history=self.execute("print DataFolderExists(\""+path+"\")")[1]
    return int(history[1][-1]) == 1

  def createDataFolder(self,fullPath):
    path=''
    if fullPath == 'root:': return
    for subFolderName in fullPath.split(':'):
      path+=subFolderName
      if not(self.dataFolderExists(path+':')):
        self('NewDataFolder '+path)
      path+=':'
    return True


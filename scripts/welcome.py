"""
Welcome to Quantrolab!

Quantrolab is a simple integrated development environment (IDE) to control a physics laboratory in Python. 
It is itself programmed in Python (and Qt for the GUI interface). It was originally developped as an open source project by the quantum electronics group of CEA Saclay: Quantronics.
The main Quantrolab application is a general mutlithread script runner that can manage several scripts organised in a project, print results in a log, and logout and traceback errors.
In addition, the IDE can run helpers (or plugins) dedicated to laboratory management.
All the helpers and scripts are run in a code process separated from the main QT application; this code process involves a single secondary QT application (making possible to use GUI helpers for instance).
All the scripts and helpers have a private local memory and share a common global memory called gv (variable x is local wheras variable gv.x is accessible from anywhere).
Many Quantrolab components can save/restore their state when Quantrolab is closed/relaunched.

I) Opening, saving and closing scripts
Script files are displayed in Quantrolab's in the tab widget on the right (one tab per script)
I.1) Tabs can be reordered by horizontal sliding of the tab name.
I.2) A script can be added to the current project by dragging its tab name vertically and dropping it in the Project tab on the left.
I.3) Open a script using the "Open file" command of Quantrolab's "File" menu (or the corresponding icon in the icon bar)
I.4) Open a script already in your project by double clicking it in the "Project" tab.
I.5) Save a script using the "Save file" command of Quantrolab's "File" menu (or the corresponding icon in the icon bar)
I.6) Create a new empty script using the "New file" command of Quantrolab's "File" menu (or the corresponding icon in the icon bar)
I.7) Close a script using either the closing cross in the tab name, or the "Close file" command of Quantrolab's "File" menu.

II) Editing, running, and stopping scripts, blocks, or selections
II.1) Scripts are normally edited using the keyboard, or copy-cut-paste functions.
II.2) Script files can be divided into blocks of code using a double sharp ##.
II.3) A search and replace tool is available by typing Control+F. Use vertical upward or downward arrows to find next and previous occurences. Note that normal keyboard edition is not available during search. Press Escape to quit the tool.
II.4) Run an entire script by either
	- clicking in its window and typing Control+Enter
	- selecting its name in the project tab and clicking the "Run script" icon in the icon bar.
II.5) Run a block of code by clicking in its window anywhere inside the block, and typing Enter or clicking the "Run block" icon in the icon bar.
II.6) Run a piece of code by clicking selecting lines in a script window, and typing Shift+Enter or clicking the "Run selection" icon in the icon bar. (The selection is completed automatically to include the beginning of the first line and the end of the last line).
II.7) Kill a running script by clicking in its window and clicking the "Kill thread" icon in the icon bar.

III) Visualizing current threads and their status
Each thread run in Quantrolab appears in the Threads" tab on the left.
Each thread has an identifier that is a either name for a helper (plugin), or a number for a script.
In addition, it has a name, which is either "IDE" for a helper, or its  file name for a script.
The status of a thread is either "running" if it is being executed, "finished" if it was successfully executed, or "failed" if the last execution led to an error.
A script with status "running" can be killed by selecting it in the "Theads" tab and clicking the "Kill" button below.
Closing a script removes it from the Thread tab view.

IV) Manage your project in the project tab on the left
IV.1) Add a folder in the project using the secondary menu in the project tab 
IV.2) Add a script file in your project by
	- opening it using the File menu of Quantrolab;
	- drag and droping it in the "Project" tree.
IV.3) Delete a script from your project by selecting its name in the "Project" tree and selecting "Delete" in the secondary menu.
IV.4) Save your project at any time using the "File" menu of Quantrolab. The current project is also automatically saved when closing the application.
IV.5) Open another project using the "File" menu of Quantrolab

V) Quantrolab helpers.
Quantrolab comes with 3 standard helpers (plugins), but others can be programmed and added at will.
V.1) Load a helper using the Quantrolab's "Helpers" menu and browse to your .pyh helper file.
V.2) A loaded helper can be accessed from its GUI interface if it has one, and from its global variable name, as indicated by a message at loading.
V.3) Quantrolab remembers open helpers when quitting and reopen them the next time it is restarted.
V.4) The "LoopManager" helper is one of the standard helper in Quantrolab. It helps you managing special loops called Smarloops, the looping properties of which are editable at runtime. See the corresponding help, as well as the example file.
V.5) The "DataManager" helper is one of the standard helper in Quantrolab. It helps you organizing, saving, reopening and plotting your numerical data, organized in so-called Datacube objects. See the corresponding help and the example file.
V.6) The "InbstrumentManager" helper is one of the standard helper in Quantrolab. It helps you controlling the instruments in your laboratory, through pyhton drivers. See the corresponding help.

"""


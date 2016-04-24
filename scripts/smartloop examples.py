#####################################################
## HERE ARE EXAMPLES SHOWING HOW TO USE SMARTLOOPS ##
#####################################################

# Import the Smartloop, PredefinedLoop, and AdaptiveLoop classes.
from application.lib.smartloop import *

## Create an infinite smartloop by specifying its name and looping parameters start,step.
loop1=SmartLoop(0,step=2.2,name='loop1')
loop1.next()
# Create a finite smartloop, by specifying its name and looping parameters start,step, and stop.
loop1=SmartLoop(0,step=1.1,stop=15.3,name='loop1')

# Create a finite smartloop that restarts automatically from the beginning when oversteping stop.
loop1=SmartLoop(0,step=2.2,stop=15.3,name='loop1',autoloop=True)

# Create a smartloop that bounces back and forth between start and stop.
loop1=SmartLoop(0,step=2.2,stop=15.3,name='loop1',autoreverse=True)

# Use your smartloop as a normal python loop
for value in loop1:
	print value
	time.sleep(1)

# A smartloop is by default deleted after completion, unless you set deleteWhenFinished=False.
# It will be automatically reset in this case, and you can reuse it.
loop1=SmartLoop(0,step=2.2,stop=15.3,name='loop1',deleteWhenFinished=False)

# If you want to observe and/or control your smartloop, Send it to the loopManager at creation or afterwards:
loop1=SmartLoop(0,step=2.2,name='loop1',toLoopManager=True)
# or
loop1.toLoopManager()

# Get all the parameters of the loop in a dictionary or one by one:
print loop1.getParams()

print loop1.getName()
print loop1.getStart()
print loop1.getStop()
print loop1.getStep()
print loop1.getIndex()
print loop1.getValue()
print loop1.getMode() 		# Return the loop mode 'normal, 'autoRev', or 'autoLoop'

# Modifiy at any time a parameter:
loop1.setName()
loop1.setStart()
loop1.setStop()
loop1.setStep() 			# accelerate or decelerate your loop
loop1.setAutoreverse()
loop1.setAutoloop()

# reverse the step, jump to first value, last value, or any value
loop1.reverse()
loop1.jumpToFirst()
loop1.jumpToLast()
loop1.jumpToValue(3.48)

# pause, play, or stop at any time your smartloop
loop1.pause()
loop1.play()
loop1.stopAtNext()

# get at any time a history of the outputs since the beginning [(index_0,value_0,time_0),...]
print loop1.history()

# A loop can have 1 parent loop and 0, 1, or several children loops.
# set a parent at creation or afterwards:
loop2=SmartLoop(0,step=0.5,stop=10.0,name='loop2',parent=loop1)
# or
loop2.setParent(loop1)
# or
loop1.addChild(loop2)

# remove a family link at any time
loop1.removeChild(loop2)
# or
loop2.clearParent()

# get family links using
print loop1.children()
print loop2.parent()
print loop1.tree()				# list of list of lists...
print loop1.descendents()		# simple list with all members at the same level

#####################################################################################
## Here is an example showing how to use optimally smartloops for making a 2d plot ##
#####################################################################################

from application.lib.datacube import *

# Two loops that do not auto delete are created
loopVoltage=SmartLoop(0.,step=1.0,stop=10.0,name='Voltage',toLoopManager=True,autoremove=False)
loopPower=SmartLoop(0.,step=2.0,stop=20.0,name='Power',toLoopManager=True,autoremove=False)

# A dummy measurement function
def measure():
	time.sleep(0.5)
	return 1.
	
# We first choose to ramp the power for each value of the voltage
loopPower.setParent(loopVoltage)
mainLoop=loopVoltage

## We do the experiment
secondLoop=mainLoop.children()[0]
names=[loop.getName() for loop in (mainLoop,secondLoop)]
#cube=Datacube('myExperiment')
#cube.toDataManager()
mainLoop.reinit()
for x in mainLoop:
	print names[0],' = ',x
	secondLoop.reinit()
	for y in secondLoop:
		print names[1],' = ',y
		meas=measure()
		#cube.set(commit=True,**{names[0]:x,names[1]:y,'meas':meas})	

## We decide then to ramp rather in the other direction, with a voltage step twice as small:
loopVoltage.setStep(loopVoltage.getStep()/2.)
loopVoltage.setParent(loopPower)
mainLoop=loopPower
## and we reevaluate the code above with no change

###############################################
## Here is an example showing how to :		##
## 	1) interrupt the thread of a loop,		##
## 	2) run some code in the same thread,   	##
## 	3) and resume the loop.					##
###############################################

a=1.

def measure2():
	time.sleep(1)
	return a

# create a loop that does not auto delete
myXLoop=SmartLoop(0.,step=1.0,stop=10.0,name='myXLoop',toLoopManager=True,deleteWhenFinished=False)

## Start to run it, and then stop it in the loopmanager
for x in myXLoop:
	print 'x = ',x, ', meas =',measure2()

## now run this one line code to redefine tthe measure function
a=2.

## Finally re-run the for x in myXLoop block of code above to resume the loop at the next step.
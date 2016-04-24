from numpy import *

# Matplotlib is the simplest scientific library for plotting in python.
# To use it from our  multithread IDE, we import it and define the backend from the pyview.gui.mpl.backend module.
#This is done only once when starting the IDE application (up to now in the gui initialisation  scripts.

import matplotlib
matplotlib.use('module://pyview.gui.mpl.backend')

# Then you need to import matplotlib.pyplot in any script involving plots.

import matplotlib.pyplot as plt

# pyplot can have several figures in memory and they are all accessible from any scripts.
# A particular figure is accessed from its figure number
# to know the list of available pyplot figures just do:

print plt.get_fignums()

# to create a new figure with the next available figure number,
# or create figure i or make it active (if it already exists), just call
plt. figure()
plt.figure(3)

# Figures are neither automatically displayed at creation nor redrawn when updated with new graphical elements. You have to use show() and draw() for display and redraw
plt.show() 

# pyplot has always one and only one active figure that you get with
currentFig =  plt.gcf()

# all figures know their number
print currentFig.number

# The matplotlib backend is parametrized so that closing a figure window does not erase it from memory. # So it can be redisplayed using show().
# To erase the current figure, figure number 3 or all figures from memory, do call
plt.close()
plt.close(3)
plt.close('all')
# The figure is erased from the list of figures but can stay in memory if it is referenced somewhere in your code. As a consequence when you recreate a figure with the same number, you get the previous content. So it is safer to clear completely a new figure using clf(),just in case it has the same number as an old figure.
plt.figure()
plt.clf()

# The graphical elements of a figure are build using the numerous matplolib methods.
# You should refer to the matplotlib documentation for understanding the figure object models,
# and for being able to produce professional figures.
# Below are ultra simple examples for lazy people.

## Example of a simple line plot
plt.figure()
x=array([1,2,3])
y=x*x
plt.plot(x,y)
plt.xlabel('x')
plt.ylabel('y')
plt.title('title')
plt.show()

## Example of two simple line plots
plt.figure()
x=array([1,2,3])
y2=x*x
y3=x*x*x
plt.plot(x,y2,'b',x,y3,'r')
plt.xlabel('x')
plt.ylabel('y')
plt.title('title')
plt.show()

## Example of a simple image plot
plt.figure(20)
plt.clf()
x=arange(-6,6.05,.1)
y=x
X,Y = meshgrid(x, y)
Z=sin(X*X+Y*Y)
plt.imshow(Z, extent=(x.min(), x.max(), y.max(), y.min()),interpolation='nearest') # no interpolation
plt.colorbar(label='z') # optional, if you want a colorbar indicating the z scale
plt.xlabel('x')
plt.ylabel('y')
plt.show()

## Example of a simple 3D plot
from mpl_toolkits.mplot3d import Axes3D
plt.figure()
x=arange(-2,2.005,.01)
y=x
X,Y = meshgrid(x, y)
Z=sin(X*X+Y*Y)
ax =fig.add_subplot(111, projection='3d')
ax.plot_surface(X, Y, Z)
plt.show()

## Live graphics
# Matplotlib has an interactive mode for making live plots.
# You can switch it on using plt.ion()
# then you update your graph and call draw()
# NB: The results can be unreliable when you feed the graph faster than it redraws itself... 
import time
plt.figure()
plt.axis([0, 200, 0, 1])
plt.ion()
plt.show()
for i in range(200):
    y = np.random.random()
    plt.scatter(i, y)
    plt.draw()
    time.sleep(0.05)
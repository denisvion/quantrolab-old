import sys

sys.path.append('.')
sys.path.append('../')

from application.lib.instrum_classes import *
from application.lib.instrum_panel import FrontPanel
from application.ide.widgets.numericedit import *
from application.ide.mpl.canvas import *

import datetime

import instruments

class Panel(FrontPanel):
	def indexOf(self,g):
		for i in range(len(self._generatorsArray)):
			if g == self._generatorsArray[i][1]: return i

	def update(self):

		for i in self._generatorsArray: i[2].clear()

		import matplotlib.pyplot as plt
		i=0
		self.plot._fig.clear()
		allPulses=self.instrument.pulses()

		for i in range(len(self._generatorsArray)):
			if i != 0:
				ax=self.plot._fig.add_subplot(len(allPulses),1,i+1,sharex=ax)
			else:
				ax=self.plot._fig.add_subplot(len(allPulses),1,i+1)


#		f, axarr = plt.subplots(len(allPulses), sharex=True)
		for g in allPulses:
			indexInArray=self.indexOf(g)
			i=indexInArray
			# self.plot._fig.add_subplot(len(allPulses),1,i+1) # WHY 2 ???
			try:
				#g.preparePulseSequence()
				item = QTreeWidgetItem()
				item.setText(0,"total")
				self._generatorsArray[indexInArray][2].insertTopLevelItem(0,item)
				item.itemArray=self._generatorsArray[indexInArray][2]
				addOffset=True
				offset=g.getOffset(0) if addOffset else 0
				item.plot=self.plot._fig.axes[i].plot(g.pulseSequenceArray+offset)
			except :
				print "Unexpected error:", sys.exc_info()
			for p in allPulses[g].values():
				item = QTreeWidgetItem()
				item.setText(0,str(p.name))
				item._pulse=p
				item.itemArray=self._generatorsArray[indexInArray][2]
				self._generatorsArray[indexInArray][2].insertTopLevelItem(0,item)

				if p.pulseOn: 
					item.plot=self.plot._fig.axes[i].plot(p._pulseArray)
				else:
					f=QFont()
					f.setStrikeOut(True)
					item.setFont(0,f)

				if not(p.pulseOn) and self._showOffPulses : 
					item.plot=self.plot._fig.axes[i].plot(p._pulseArray,'--')
					
				if not(p.pulseOn) and not(self._showOffPulses): 
					item.plot=self.plot._fig.axes[i].plot(p._pulseArray,'  ')
					

			self.plot._fig.axes[i].xaxis.grid(True)
			li=self.plot._fig.axes[i].get_ylim()
			#set new lim
			c=(li[1]+li[0])/2
			l=li[1]-li[0]
			print "old lim: ", li, "newylim : ", [c-l/2*1.2,c+l/2*1.2]
			self.plot._fig.axes[i].set_ylim([c-l/2*1.2,c+l/2*1.2])
			i+=1

		self.plot._fig.subplots_adjust(hspace=self._hspace)
		plt.setp([a.get_xticklabels() for a in self.plot._fig.axes[:-1]], visible=False)

		self.plot.scrollable=[True,False]
		self.plot.redraw()





	def vSplitOption(self):
		self._hspace=abs(self._hspace-0.05)
		self.plot._fig.subplots_adjust(hspace=self._hspace)
		self.plot.redraw()

	def showOffPulsesOption(self):
		self._showOffPulses=not(self._showOffPulses)
		self.update()

	def itemClicked(self, item):
		if item.itemArray.lastSelectedItem is not None:
			item.itemArray.lastSelectedItem.plot[0].set_linewidth(1)
		item.plot[0].set_linewidth(3)
		item.itemArray.lastSelectedItem=item
		self.plot.redraw()

	def __init__(self,instrument,parent=None):
		super(Panel,self).__init__(instrument,parent)

		self.setWindowTitle("Pulsers manager")
		self.grid = QGridLayout()
		self.grid.setSpacing(10)
		self.plot = MatplotlibCanvas(self, width=8, height=10, dpi=100)
		self.plot.axes.set_visible(True)
		updateButton = QPushButton("Update")
		e = QPushButton("Update")
		self.connect(updateButton,SIGNAL("clicked()"),self.update)


		self.grid.addWidget(self.plot,0,0)
		self.grid.addWidget(updateButton,1,0)
		self.pulsesNames=QGridLayout()
		self.grid.addLayout(self.pulsesNames,0,1)

		self._generatorsArray=[]#dict()
		i=0
		for g in [u[0] for u in self.instrument._generators]:
			# g is the instrument (pulse generator type)
			w=QTreeWidget()
			self._generatorsArray.append([i,g,w])
			w.lastSelectedItem=None
			w.itemClicked.connect(self.itemClicked)
			gr=QGridLayout()
			gr.addWidget(QLabel(g.name()),0,0)
			gr.addWidget(w,1,0)
			self.pulsesNames.addLayout(gr,i,0)
			i+=1


		self.qw.setLayout(self.grid)
		self.setMinimumWidth(500)
		self.setMinimumHeight(500)
		
		self._hspace=0.05
		self._showOffPulses=True

		menubar=self.menuBar()
		myMenu=menubar.addMenu("&Options")
		vSplitCommand=myMenu.addAction("vertical &Split")
		showOffPulsesCommand=myMenu.addAction("show &Off pulses")
		self.connect(vSplitCommand,SIGNAL("triggered()"),self.vSplitOption)
		self.connect(showOffPulsesCommand,SIGNAL("triggered()"),self.showOffPulsesOption)

		self.update()

		self.instrument.fp=self

"""
Tektronix RSA API: Continuous Spectrum
Author: Morgan Allison
Date created: 6/15
Date edited: 11/16
Windows 7 64-bit
RSA API version 3.9.0029
Python 3.5.2 64-bit (Anaconda 4.2.0)
NumPy 1.11.0, MatPlotLib 1.5.3
PyQtGraph 0.9.10 (pyqt 4.8.7, qt 4.11.4)
To get Anaconda: http://continuum.io/downloads
Anaconda includes NumPy and MatPlotLib
Anaconda uses PyQt5 by default. PyQtGraph uses PyQt4.
You can use (conda install pyqtgraph) to handle dependency conflicts
"""

from ctypes import *
import numpy as np
import pyqtgraph as pg
from pyqtgraph import QtGui, QtCore
from os import chdir
from sys import exit


"""
################################################################
C:\Tektronix\RSA_API\lib\x64 needs to be added to the 
PATH system environment variable
################################################################
"""
chdir("C:\\Tektronix\\RSA_API\\lib\\x64")
rsa = cdll.LoadLibrary("RSA_API.dll")


"""#################CLASSES AND FUNCTIONS#################"""
class RSAError(Exception):
	pass


class Spectrum_Settings(Structure):
	_fields_ = [('span', c_double), 
	('rbw', c_double),
	('enableVBW', c_bool), 
	('vbw', c_double),
	('traceLength', c_int), 
	('window', c_int),
	('verticalUnit', c_int), 
	('actualStartFreq', c_double), 
	('actualStopFreq', c_double),
	('actualFreqStepSize', c_double), 
	('actualRBW', c_double),
	('actualVBW', c_double), 
	('actualNumIQSamples', c_double)]


class Spectrum_TraceInfo(Structure):
	_fields_ = [('timestamp', c_int64), ('acqDataStatus', c_uint16)]


class Window(QtGui.QMainWindow):
	def __init__(self):
		# getting parent object
		super(Window, self).__init__()
		self.setGeometry(50, 50, 1000, 800)
		self.setWindowTitle('RSA_API GUI')
		# self.setWindowIcon(QtGui.QIcon('pyLogo.png'))
		
		# Create an action
		# Set a keyboard shortcut for the action		
		# Again the connect method lets you choose what happens when a button or menu is clicked
		quit = QtGui.QAction('&Quit', self)
		quit.setShortcut('Alt+F4')
		quit.setStatusTip('Leave the app')
		quit.triggered.connect(exit)

		# Calls the status bar into being
		self.statusBar = self.statusBar()	# we don't need to make any changes to the status bar, so we can just create it
		mainMenu = self.menuBar()	# we need to do things with mainMenu, so we assign it to a variable
		fileMenu = mainMenu.addMenu('&File')
		fileMenu.addAction(quit)

		self.home()


	def rsa_controls(self):
		cfLabel = QtGui.QLabel(self)
		cfLabel.move(0,45)
		cfLabel.resize(100, 25)
		cfLabel.setText('Center Freq (Hz)')
		cfLabel.setAlignment(QtCore.Qt.AlignCenter)
		self.cfInput = QtGui.QLineEdit(self)
		self.cfInput.setValidator(QtGui.QDoubleValidator())
		self.cfInput.move(100,45)
		self.cfInput.resize(100,25)
		self.cfInput.returnPressed.connect(self.set_cf)

		rlLabel = QtGui.QLabel(self)
		rlLabel.move(200,45)
		rlLabel.resize(100, 25)
		rlLabel.setText('Ref Level (dBm)')
		rlLabel.setAlignment(QtCore.Qt.AlignCenter)
		self.rlInput = QtGui.QLineEdit(self)
		self.rlInput.setValidator(QtGui.QDoubleValidator())
		self.rlInput.move(300,45)
		self.rlInput.resize(100,25)
		self.rlInput.returnPressed.connect(self.set_rl)

		spanLabel = QtGui.QLabel(self)
		spanLabel.move(400,45)
		spanLabel.resize(100, 25)
		spanLabel.setText('Span (Hz)')
		spanLabel.setAlignment(QtCore.Qt.AlignCenter)
		self.spanInput = QtGui.QLineEdit(self)
		self.spanInput.setValidator(QtGui.QDoubleValidator())
		self.spanInput.move(500,45)
		self.spanInput.resize(100,25)
		self.spanInput.returnPressed.connect(self.set_span)

		rbwLabel = QtGui.QLabel(self)
		rbwLabel.move(600,45)
		rbwLabel.resize(100, 25)
		rbwLabel.setText('RBW (Hz)')
		rbwLabel.setAlignment(QtCore.Qt.AlignCenter)
		self.rbwInput = QtGui.QLineEdit(self)
		self.rbwInput.setValidator(QtGui.QDoubleValidator())
		self.rbwInput.move(700,45)
		self.rbwInput.resize(100,25)
		self.rbwInput.returnPressed.connect(self.set_rbw)

		self.runBtn = QtGui.QPushButton('Run', self)
		self.runBtn.clicked.connect(self.run)
		self.runBtn.move(0,20)
		self.runBtn.resize(100,25)
		self.stopBtn = QtGui.QPushButton('Stop', self)
		self.stopBtn.clicked.connect(self.stop)
		self.stopBtn.move(100,20)
		self.stopBtn.resize(100,25)
		self.singleBtn = QtGui.QPushButton('Single', self)
		self.singleBtn.clicked.connect(self.single)
		self.singleBtn.move(200,20)
		self.singleBtn.resize(100,25)

		searchConnectBtn = QtGui.QPushButton('Search/Connect', self)
		searchConnectBtn.clicked.connect(self.rsa_setup)
		searchConnectBtn.move(900,20)
		searchConnectBtn.resize(100,25)
		self.connectLabel = QtGui.QLabel(self)
		self.connectLabel.move(900,45)
		self.connectLabel.resize(100,25)
		self.connectLabel.setAlignment(QtCore.Qt.AlignCenter)
		self.connectLabel.setText('Disconnected')


	def home(self):
		self.p = pg.PlotWidget(self, title='Spectrum')
		self.p.move(0,70)
		self.p.resize(1000, 700)
		self.p.setLabels(left=('Amplitude','dBm'), bottom=('Frequency', 'Hz'))
		self.pData = self.p.plot()

		self.timer = QtCore.QTimer()
		self.timer.timeout.connect(self.spectrum_update)

		self.rsa_controls()
		self.rsa_setup()

		self.show()


	def check_connect(self):
		ret = rsa.DEVICE_StartFrameTransfer()
		if ret != 0:
			raise RSAError


	def run(self):
		self.timer.start(50)


	def stop(self):
		self.timer.stop()
		rsa.DEVICE_Stop()


	def single(self):
		self.timer.stop()
		self.spectrum_update()
		rsa.DEVICE_Stop()


	def spectrum_update(self):
		try:
			self.check_connect()
		except RSAError:
			self.statusBar.showMessage('Error in RSA connection.')
			self.connectLabel.setText('Disconnected')
			self.deactivate_controls()	
		else:
			ready = c_bool(False)
			rsa.DEVICE_Run()
			rsa.SPECTRUM_AcquireTrace()
			while ready.value == False:
				rsa.SPECTRUM_WaitForDataReady(c_int(100), byref(ready))
			rsa.SPECTRUM_GetTrace(c_int(0), self.specSet.traceLength, 
				byref(self.traceData), byref(self.outTracePoints))

			self.pData.setData(self.freq, np.array(self.traceData), pen='y')


	def plot_update(self):
		rsa.SPECTRUM_GetSettings(byref(self.specSet))
		self.freq = np.arange(self.specSet.actualStartFreq, 
			self.specSet.actualStartFreq + self.specSet.actualFreqStepSize*self.specSet.traceLength, 
			self.specSet.actualFreqStepSize)
		self.p.setYRange(self.refLevel-100, self.refLevel)
		self.p.setXRange(self.freq[0], self.freq[-1], padding=0)


	def set_cf(self):
		self.cf = float(self.cfInput.text())
		rsa.CONFIG_SetCenterFreq(c_double(self.cf))
		self.cfInput.setText(str(self.cf))
		self.plot_update()


	def set_span(self):
		self.specSet.span = float(self.spanInput.text())
		self.specSet.rbw = self.specSet.span/100
		rsa.SPECTRUM_SetSettings(self.specSet)
		self.spanInput.setText(str(self.specSet.span))
		self.rbwInput.setText(str(self.specSet.span/100))
		self.plot_update()


	def set_rl(self):
		self.refLevel = float(self.rlInput.text())
		rsa.CONFIG_SetReferenceLevel(c_double(self.refLevel))
		self.rlInput.setText(str(self.refLevel))
		self.plot_update()


	def set_rbw(self):
		self.specSet.rbw = c_double(float(self.rbwInput.text()))
		ret = rsa.SPECTRUM_SetSettings(self.specSet)
		self.rbwInput.setText(str(self.specSet.rbw))
		self.plot_update()


	def search_connect(self):
		#search/connect variables
		numFound = c_int(0)
		intArray = c_int*10
		deviceIDs = intArray()
		deviceSerial = create_string_buffer(8)
		deviceType = create_string_buffer(8)
		apiVersion = create_string_buffer(16)

		#get API version
		rsa.DEVICE_GetAPIVersion(apiVersion)
		self.statusBar.showMessage('API Version {}'.format(apiVersion.value.decode()))

		#search
		ret = rsa.DEVICE_Search(byref(numFound), deviceIDs, 
			deviceSerial, deviceType)

		if ret != 0:
			self.statusBar.showMessage('Error in Search: ' + str(ret))
			raise RSAError
		if numFound.value < 1:
			self.statusBar.showMessage('No instruments found.')
			raise RSAError
		# elif numFound.value == 1:
		else:
			self.statusBar.showMessage(
				'One device found. Device type: {}. Serial number: {}.'.format(
				deviceType.value.decode(), deviceSerial.value.decode()))
			ret = rsa.DEVICE_Connect(deviceIDs[0])
			if ret != 0:
				self.statusBar.showMessage('Error in Connect: ' + str(ret))
				raise RSAError
			self.connectLabel.setText('Connected')
		# else:
		# 	print('2 or more instruments found. Enumerating instruments, please wait.')
		# 	for inst in range(numFound.value):
		# 		rsa.DEVICE_Connect(deviceIDs[inst])
		# 		rsa.DEVICE_GetSerialNumber(deviceSerial)
		# 		rsa.DEVICE_GetNomenclature(deviceType)
		# 		self.statusBar.showMessage(
		# 		'Device: {} Device type: {} Serial number: {}'.format(
		# 		inst, deviceType.value.decode(), deviceSerial.value.decode()))
		# 		rsa.DEVICE_Disconnect()
		# 	#note: the API can only currently access one at a time
		# 	selection = 1024
		# 	while (selection > numFound.value-1) or (selection < 0):
		# 		selection = int(input('Select device between 0 and {}\n> '.format(numFound.value-1)))
		# 	rsa.DEVICE_Connect(deviceIDs[selection])
		# 	return selection
		#connect to the first RSA


	def configure_settings(self):
		"""#################INITIALIZE VARIABLES#################"""
		#Default SA parameters
		self.specSet = Spectrum_Settings()
		self.cf = 1e9          #center freq
		self.refLevel = 0      #ref level

		"""#################CONFIGURE INSTRUMENT#################"""
		rsa.CONFIG_Preset()
		rsa.CONFIG_SetCenterFreq(c_double(self.cf))
		rsa.CONFIG_SetReferenceLevel(c_double(self.refLevel))
		rsa.SPECTRUM_SetEnable(c_bool(True))
		rsa.SPECTRUM_SetDefault()
		rsa.SPECTRUM_GetSettings(byref(self.specSet))

		# configure desired spectrum settings
		# some fields are left blank because the default
		# values set by SPECTRUM_SetDefault() are acceptable
		# self.specSet.span = c_double(40e6)
		# self.specSet.rbw = c_double(300e3)
		# self.specSet.enableVBW = 
		# self.specSet.vbw = 
		# self.specSet.traceLength = c_int(801)
		# self.specSet.window = 
		# self.specSet.verticalUnit = 
		# self.specSet.actualStartFreq = 
		# self.specSet.actualFreqStepSize = 
		# self.specSet.actualRBW = 
		# self.specSet.actualVBW = 
		# self.specSet.actualNumIQSamples = 

		#set desired spectrum settings
		rsa.SPECTRUM_SetSettings(self.specSet)
		rsa.SPECTRUM_GetSettings(byref(self.specSet))


		"""#################INITIALIZE DATA TRANSFER VARIABLES#################"""
		#initialize variables for GetTrace
		traceArray = c_float*self.specSet.traceLength
		self.traceData = traceArray()
		self.outTracePoints = c_int()

		#generate frequency array for plotting the spectrum
		self.freq = np.arange(self.specSet.actualStartFreq, 
			self.specSet.actualStartFreq + 
			self.specSet.actualFreqStepSize*self.specSet.traceLength, 
			self.specSet.actualFreqStepSize)

		self.cfInput.setText(str(self.cf))
		self.rlInput.setText(str(self.refLevel))
		self.spanInput.setText(str(self.specSet.span))
		self.rbwInput.setText(str(self.specSet.rbw))
		self.p.setYRange(self.refLevel-100, self.refLevel)
		self.p.setXRange(self.freq[0], self.freq[-1], padding=0)
		

	def deactivate_controls(self):
		self.runBtn.setEnabled(False)
		self.stopBtn.setEnabled(False)
		self.singleBtn.setEnabled(False)
		self.cfInput.setReadOnly(True)
		self.rlInput.setReadOnly(True)
		self.spanInput.setReadOnly(True)
		self.rbwInput.setReadOnly(True)


	def activate_controls(self):
		self.runBtn.setEnabled(True)
		self.stopBtn.setEnabled(True)
		self.singleBtn.setEnabled(True)
		self.cfInput.setReadOnly(False)
		self.rlInput.setReadOnly(False)
		self.spanInput.setReadOnly(False)
		self.rbwInput.setReadOnly(False)
		self.configure_settings()


	def rsa_setup(self):
		try:
			self.search_connect()
		except RSAError:
			self.statusBar.showMessage('No Instruments found.')
			self.connectLabel.setText('Disconnected')
			self.deactivate_controls()	
		else:
			self.activate_controls()

def main():
	app = QtGui.QApplication([])
	GUI = Window()

	app.exec_()
	rsa.DEVICE_Disconnect()


if __name__ == "__main__":
	main()
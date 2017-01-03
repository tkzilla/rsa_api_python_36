"""
RSA API: DPX Spectrum Bitmap Visualizer
Author: Morgan Allison (and Dave Maciupa)
Date created: 11/15
Date edited: 1/17
Windows 7 64-bit
RSA API version 3.9.0029
Python 3.5.2 64-bit (Anaconda 4.2.0)
NumPy 1.11.2, MatPlotLib 1.5.3
To get Anaconda: http://continuum.io/downloads
Anaconda includes NumPy and MatPlotLib
"""

from ctypes import *
import numpy as np
from matplotlib import use
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os, time

"""
################################################################
C:\Tektronix\RSA_API\lib\x64 needs to be added to the 
PATH system environment variable
################################################################
"""
os.chdir("C:\\Tektronix\\RSA_API\\lib\\x64")
rsa = cdll.LoadLibrary("RSA_API.dll")


"""#################CLASSES AND FUNCTIONS#################"""
#create DPX Settings data structure
class DPX_SettingStruct(Structure):
	_fields_ = [('enableSpectrum', c_bool), ('enableSpectrogram', c_bool),
	('bitmapWidth', c_int32), ('bitmapHeight', c_int32),
	('traceLength', c_int32), ('decayFactor', c_float),
	('actualRBW', c_double)]
		 
#create DPX frame buffer data structure
class DPX_FrameBuffer(Structure):
		_fields_ = [('fftPerFrame', c_int32), ('fftCount', c_int64),
		('frameCount', c_int64), ('timestamp', c_double),
		('acqDataStatus', c_uint32), ('minSigDuration', c_double),
		('minSigDurOutOfRange', c_bool), ('spectrumBitmapWidth', c_int32), 
		('spectrumBitmapHeight', c_int32), ('spectrumBitmapSize', c_int32),
		('spectrumTraceLength', c_int32), ('numSpectrumTraces', c_int32),
		('spectrumEnabled', c_bool), ('spectrogramEnabled', c_bool),
		('spectrumBitmap', POINTER(c_float)), 
		('spectrumTraces', POINTER(POINTER(c_float))), 
		('sogramBitmapWidth', c_int32), ('sogramBitmapHeight',c_int32),
		('sogramBitmapSize', c_int32), ('sogramBitmapNumValidLines',c_int32),
		('sogramBitmap', POINTER(c_uint8)),
		('sogramBitmapTimestampArray', POINTER(c_double)), 
		('sogramBitmapContainTriggerArray', POINTER(c_double))]

def search_connect():
	#search/connect variables
	numFound = c_int(0)
	intArray = c_int*10
	deviceIDs = intArray()
	deviceSerial = create_string_buffer(8)
	deviceType = create_string_buffer(8)
	apiVersion = create_string_buffer(16)

	#get API version
	rsa.DEVICE_GetAPIVersion(apiVersion)
	print('API Version {}'.format(apiVersion.value.decode()))

	#search
	ret = rsa.DEVICE_Search(byref(numFound), deviceIDs, 
		deviceSerial, deviceType)

	if ret != 0:
		print('Error in Search: ' + str(ret))
		exit()
	if numFound.value < 1:
		print('No instruments found. Exiting script.')
		exit()
	elif numFound.value == 1:
		print('One device found.')
		print('Device type: {}'.format(deviceType.value.decode()))
		print('Device serial number: {}'.format(deviceSerial.value.decode()))
		ret = rsa.DEVICE_Connect(deviceIDs[0])
		if ret != 0:
			print('Error in Connect: ' + str(ret))
			exit()
	else:
		print('2 or more instruments found. Enumerating instruments, please wait.')
		for inst in range(numFound.value):
			rsa.DEVICE_Connect(deviceIDs[inst])
			rsa.DEVICE_GetSerialNumber(deviceSerial)
			rsa.DEVICE_GetNomenclature(deviceType)
			print('Device {}'.format(inst))
			print('Device Type: {}'.format(deviceType.value))
			print('Device serial number: {}'.format(deviceSerial.value))
			rsa.DEVICE_Disconnect()
		#note: the API can only currently access one at a time
		selection = 1024
		while (selection > numFound.value-1) or (selection < 0):
			selection = int(input('Select device between 0 and {}\n> '.format(numFound.value-1)))
		rsa.DEVICE_Connect(deviceIDs[selection])
		return selection
		
def print_dpxSettings(dpxSettings):
	print('\nDPX Settings')
	print('enableSpectrum: ' + str(dpxSettings.enableSpectrum))
	print('enableSpectrogram: ' + str(dpxSettings.enableSpectrogram))
	print('bitmapWidth: ' + str(dpxSettings.bitmapWidth))
	print('bitmapHeight: ' + str(dpxSettings.bitmapHeight))
	print('traceLength: ' + str(dpxSettings.traceLength))
	print('decayFactor: ' + str(dpxSettings.decayFactor))
	print('actualRBW: ' + str(dpxSettings.actualRBW))
				
def print_frameBuffer(frameBuffer):
	print('\nDPX Frame Buffer Information')
	print('fftPerFrame: ' + str(frameBuffer.fftPerFrame))
	print('fftCount: ' + str(frameBuffer.fftCount))
	print('frameCount: ' + str(frameBuffer.frameCount))
	print('timestamp: ' + str(frameBuffer.timestamp))
	print('acqDataStatus: ' + str(frameBuffer.acqDataStatus))
	print('minSigDuration: ' + str(frameBuffer.minSigDuration))
	print('minSigDurOutOfRange: ' + str(frameBuffer.minSigDurOutOfRange))
	print('spectrumBitmapWidth: ' + str(frameBuffer.spectrumBitmapWidth))
	print('spectrumBitmapHeight: ' + str(frameBuffer.spectrumBitmapHeight))
	print('spectrumBitmapSize: ' + str(frameBuffer.spectrumBitmapSize))
	print('spectrumTraceLength: ' + str(frameBuffer.spectrumTraceLength))
	print('numSpectrumTraces: ' + str(frameBuffer.numSpectrumTraces))
	print('spectrumEnabled: ' + str(frameBuffer.spectrumEnabled))
	print('spectrumTraces[0:10]: ' + str(frameBuffer.spectrumTraces[0][0:10])) 
	print('len(spectrumBitmap): ' + str(len(frameBuffer.spectrumBitmap)))
	print('max(spectrumBitmap): ' + str(max(frameBuffer.spectrumBitmap)))
	print('spectrumBitmap[0:10]: ' + str(frameBuffer.spectrumBitmap[0:10]))

def main():
	"""#################INITIALIZE VARIABLES#################"""
	TRACEPOINTS = 801

	dsStruct = DPX_SettingStruct()  #DPX Settings struct
	fb = DPX_FrameBuffer()          #DPX frame buffer, this will contain data

	#SA setup
	cf = c_double(2.4453e9)              #center freq
	refLevel = c_double(-40)          #ref level
	
	#bools/timeouts
	enable = c_bool(True)           #DPX enable
	frameAvailable = c_bool(False)  #DPX frame available check
	ready = c_bool(False)           #ready check
	timeoutMsec = c_int(500)        #timeout

	#for DPX_SetParameters
	fspan = c_double(40e6)
	rbw = c_double(fspan.value/100)
	tracePtsPerPixel = c_int(1)
	yUnit = c_int(0)        #VerticalUnit_dBm
	yTop = refLevel
	yBottom = c_double(yTop.value - 100)
	infinitePersistence = c_bool(0)
	persistenceTimeSec = c_double(1.0)
	showOnlyTrigFrame = c_bool(0)
	traceType = c_int(1)    #+peak

	#spectrum bitmap width, height, and size are all fixed values
	bitmapWidth = c_int(801)
	bitmapHeight = c_int(201)
	#bitmapSize = bitmapWidth.value*bitmapHeight.value

		
	"""#################SEARCH/CONNECT#################"""
	search_connect()


	"""#################CONFIGURE INSTRUMENT#################"""
	rsa.CONFIG_Preset()
	rsa.CONFIG_SetCenterFreq(cf)
	rsa.CONFIG_SetReferenceLevel(refLevel)
	
	rsa.DPX_SetEnable(enable)
	rsa.DPX_GetEnable(byref(enable))
	rsa.DPX_SetParameters(fspan, rbw, bitmapWidth, tracePtsPerPixel, yUnit,
		 yTop, yBottom, infinitePersistence, persistenceTimeSec, 
		 showOnlyTrigFrame)
	rsa.DPX_Configure(c_bool(True),c_bool(False))    #(spectrum, sogram)
	rsa.DPX_GetSettings(byref(dsStruct))

	# max hold c_int(2), min hold c_int(4), and average c_int(0) traces
	# see RSA_API documentation for more details
	rsa.DPX_SetSpectrumTraceType(c_int32(0), c_int(2))
	rsa.DPX_SetSpectrumTraceType(c_int32(1), c_int(4))
	rsa.DPX_SetSpectrumTraceType(c_int32(2), c_int(0))
	
	#print_dpxSettings(dsStruct)


	"""#################ACQUIRE DATA#################"""
	print('\nGenerating DPX Frame\n')

	#acquisition loop
	rsa.DEVICE_Run()
	rsa.DPX_Reset()

	while frameAvailable.value == False:
		rsa.DPX_IsFrameBufferAvailable(byref(frameAvailable))
		while ready.value == False:
			rsa.DPX_WaitForDataReady(c_int(100), byref(ready))
	rsa.DPX_GetFrameBuffer(byref(fb))
	rsa.DPX_FinishFrameBuffer()

	rsa.DEVICE_Stop()

	print('Frames: {}'.format(fb.frameCount))
	print('FFTs: {}'.format(fb.fftCount))
	print('Spectrum Traces: {}'.format(fb.numSpectrumTraces))
	print('Spectrum trace points: {}'.format(fb.spectrumTraceLength))

	"""#################PROCESS DATA#################"""
	bitmapFreq = np.linspace((cf.value - fspan.value/2), 
		(cf.value + fspan.value/2), fb.spectrumBitmapWidth)
	bitmapAmp = np.linspace(yBottom.value, yTop.value, fb.spectrumBitmapHeight)

	# grab spectrum bitmap
	# specifying the shape of the destination variable is IMPORTANT
	dpxBitmap = np.ctypeslib.as_array(fb.spectrumBitmap, 
		shape=(fb.spectrumBitmapSize,))
	dpxBitmap = dpxBitmap.reshape((fb.spectrumBitmapHeight, 
		fb.spectrumBitmapWidth))

	# grab trace data and convert from W to dBm
	specTrace1 = 20*np.log10(np.array(fb.spectrumTraces[0][:801])/1000)
	# specTrace1 = 10*np.log10(specTrace1/1000)
	specTrace2 = 20*np.log10(np.array(fb.spectrumTraces[1][:801])/1000)
	# specTrace2 = 10*np.log10(specTrace2/1000)
	specTrace3 = 20*np.log10(np.array(fb.spectrumTraces[2][:801])/1000)
	# specTrace3 = 10*np.log10(specTrace3/1000)


	"""#################PLOT#################"""
	# Plot out the three DPX spectrum traces
	fig1 = plt.figure(1, figsize=(20,10))
	ax1 = fig1.add_subplot(121)
	ax1.set_title('DPX Spectrum Traces')
	ax1.set_xlabel('Frequency (Hz)')
	ax1.set_ylabel('Amplitude (dBm)')
	st1, = plt.plot(bitmapFreq, specTrace1)
	st2, = plt.plot(bitmapFreq, specTrace2)
	st3, = plt.plot(bitmapFreq, specTrace3)
	ax1.legend([st1, st2, st3], ['Max Hold', 'Min Hold', 'Average'])
	ax1.set_xlim([bitmapFreq[0], bitmapFreq[-1]])
	# plt.show(block=False)

	# This figure is a 3D representation of the DPX bitmap  
	# The methodology was cobbled together from a few Matplotlib example files
	# If anyone can figure out how to do a 3D colormap, that'd be cool.
	ax2 = fig1.add_subplot(122, projection='3d')
	for i in range(fb.spectrumBitmapHeight):
		index = fb.spectrumBitmapHeight-1-i
		ax2.plot(dpxBitmap[i], bitmapFreq, bitmapAmp[index], c='b')
	ax2.set_title('DPX Bitmap')
	ax2.set_zlim(yBottom.value,yTop.value)
	ax2.set_xlabel('Spectral Density (counter hits)')
	ax2.set_ylabel('Frequency (Hz)')
	ax2.set_zlabel('Amplitude (dBm)')
	plt.show()


	"""#################DISCONNECT#################"""
	print('\nDisconnecting.')
	rsa.DEVICE_Disconnect()


if __name__ == "__main__":
	main()

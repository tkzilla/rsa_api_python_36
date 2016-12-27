"""
Tektronix RSA API: IF Streaming + Spectrum
Author: Morgan Allison
Date created: 5/16
Date edited: 11/16
Windows 7 64-bit
RSA API version 3.9.0029
Python 3.5.2 64-bit (Anaconda 4.2.0)
NumPy 1.11.0, MatPlotLib 1.5.3
To get Anaconda: http://continuum.io/downloads
Anaconda includes NumPy and MatPlotLib


NOTE: The IF streaming and spectrum consumers can ONLY be run simultaneously
if the spectrum span is set to 40 MHz or less. 
"""

from ctypes import *
import numpy as np
import matplotlib.pyplot as plt
import time, os

"""
################################################################
C:\Tektronix\RSA_API\lib\x64 needs to be added to the 
PATH system environment variable
################################################################
"""
os.chdir("C:\\Tektronix\\RSA_API\\lib\\x64")
rsa = cdll.LoadLibrary("RSA_API.dll")

"""#################CLASSES AND FUNCTIONS#################"""
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
        for inst in xrange(numFound.value):
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

def main():
	"""#################INITIALIZE VARIABLES#################"""
	#main SA parameters
	cf = c_double(2.412e9)
	refLevel = c_double(0)
	bwHz_act = c_double(0)
	sRate = c_double(0)
	durationMsec = 10000
	waitTime = 0.1
	fileDirectory = 'C:\SignalVu-PC Files\!garbage'
	fileName = 'stream_test'
	streamingMode = 1
	streaming = True

	specSet = Spectrum_Settings()
	specEnable = c_bool(True)
	writing = c_bool(True)
	ready = c_bool(False)
	timeoutMsec = 100


	"""#################SEARCH/CONNECT#################"""
	search_connect()


	"""#################CONFIGURE INSTRUMENT#################"""
	rsa.CONFIG_Preset()
	rsa.CONFIG_SetCenterFreq(cf)
	rsa.CONFIG_SetReferenceLevel(refLevel)

	rsa.TRIG_SetTriggerMode(c_int(1))

	rsa.IFSTREAM_SetDiskFilePath(c_wchar_p(fileDirectory))
	rsa.IFSTREAM_SetDiskFilenameBase(c_wchar_p(fileName))
	rsa.IFSTREAM_SetDiskFileLength(c_long(durationMsec))
	rsa.IFSTREAM_SetDiskFileMode(c_int(streamingMode))
	rsa.IFSTREAM_SetDiskFileCount(c_int(1))

	rsa.SPECTRUM_SetEnable(specEnable)
	rsa.SPECTRUM_SetDefault()
	rsa.SPECTRUM_GetSettings(byref(specSet))

	#configure desired spectrum settings
	#some fields are left blank because the default
	#values set by SPECTRUM_SetDefault() are acceptable
	specSet.span = c_double(40e6)
	specSet.rbw = c_double(300e3)
	#specSet.enableVBW = 
	#specSet.vbw = 
	specSet.traceLength = c_int(801)
	#specSet.window = 
	#specSet.verticalUnit = 
	#specSet.actualStartFreq = 
	#specSet.actualFreqStepSize = 
	#specSet.actualRBW = 
	#specSet.actualVBW = 
	#specSet.actualNumIQSamples = 

	#set desired spectrum settings
	rsa.SPECTRUM_SetSettings(specSet)
	rsa.SPECTRUM_GetSettings(byref(specSet))

	#print spectrum settings for sanity check
	#print_spectrum_settings(specSet)


	"""#################INITIALIZE DATA TRANSFER VARIABLES#################"""
	#initialize variables for GetTrace
	traceArray = c_float * specSet.traceLength
	traceData = traceArray()
	outTracePoints = c_int()

	#generate frequency array for plotting the spectrum
	freq = np.arange(specSet.actualStartFreq, 
		specSet.actualStartFreq + specSet.actualFreqStepSize*specSet.traceLength, 
		specSet.actualFreqStepSize)

	"""
	#prepare plot window for periodic updates
	specPlot, = plt.plot([],[])
	plt.xlabel('Frequency (Hz)')
	plt.ylabel('Amplitude (dBm)')
	plt.title('Spectrum')
	plt.show(block=False)	#required to update plot w/o stopping the script
	plt.xlim(np.amin(freq), np.amax(freq))
	plt.ylim(-100, 0)
	"""

	"""#################ACQUIRE/PROCESS DATA#################"""
	"""
	##########################################
	DEVICE_Run() MUST BE SENT before SetStreamADCToDiskEnabled()
	##########################################
	"""

	print('Beginning streaming.')
	rsa.DEVICE_Run()

	start = time.clock()
	rsa.IFSTREAM_SetEnable(c_bool(True))
	print("waiting for trigger")
	# time.sleep(3)
	rsa.TRIG_ForceTrigger()
	while streaming == True:
		rsa.SPECTRUM_AcquireTrace()
		while ready.value == False:
			rsa.SPECTRUM_WaitForDataReady(timeoutMsec, byref(ready))
		rsa.SPECTRUM_GetTrace(c_int(0), specSet.traceLength, 
			byref(traceData), byref(outTracePoints))

		#convert trace data from a ctypes array to a numpy array
		trace = np.ctypeslib.as_array(traceData)

		"""#################SPECTRUM PLOT#################"""
		"""
		#refresh spectrum by updating arrays used in the plot
		specPlot.set_xdata(freq)
		specPlot.set_ydata(trace)
		plt.draw()
		"""
		time.sleep(waitTime)
		rsa.IFSTREAM_GetActiveStatus(byref(writing))
		streaming = writing.value
	end = time.clock()

	rsa.DEVICE_Stop()
	# plt.close()
	print('Streaming finished.')
	print('Elapsed time: {} seconds.\n'.format(end-start))
	print('Disconnecting.')
	rsa.DEVICE_Disconnect()

if __name__ == "__main__":
    main()

"""
Tektronix RSA API: Streaming to a File
Author: Morgan Allison
Date created: 10/15
Date edited: 11/16
Windows 7 64-bit
RSA API version 3.9.0029
Python 3.5.2 64-bit (Anaconda 4.2.0)
NumPy 1.11.0, MatPlotLib 1.5.3
To get Anaconda: http://continuum.io/downloads
Anaconda includes NumPy and MatPlotLib
"""

from ctypes import *
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
class IQSTRMFILEINFO(Structure):
   _fields_ = [('numberSamples', c_uint64), 
   ('sample0Timestamp', c_uint64),
   ('triggerSampleIndex', c_uint64), 
   ('triggerTimestamp', c_uint64),
   ('acqStatus', c_uint32), 
   ('filenames', c_wchar_p)]

def iqstream_status_parser(acqStatus):
	#this function parses the IQ streaming status variable
	if acqStatus == 0:
		print('\nNo error.\n')
	if (bool(acqStatus & 0x10000)):	#mask bit 16
		print('\nInput overrange.\n')
	if (bool(acqStatus & 0x40000)):	#mask bit 18
		print('\nInput buffer > 75{} full.\n'.format('%'))
	if (bool(acqStatus & 0x80000)):	#mask bit 19
		print('\nInput buffer overflow. IQStream processing too slow, data loss has occurred.\n')
	if (bool(acqStatus & 0x100000)):	#mask bit 20
		print('\nOutput buffer > 75{} full.\n'.format('%'))
	if (bool(acqStatus & 0x200000)):	#mask bit 21
		print('Output buffer overflow. File writing too slow, data loss has occurred.\n')

def suf_ext_parser(streamtype, streamingMode, dest, suffixCtl):
	#this function handles printing the location of the saved file
	if streamtype == 1:
		if streamingMode == 0:
			ext = '.r3a/.r3h'
		elif streamingMode == 1:
			ext = '.r3f'
		suf = '<timestamp>'
		return suf, ext
	
	elif streamtype == 2:
		if dest == 1:
			ext = '.tiq'
		elif dest == 2:
			ext = '.siq'
		elif dest == 3:
			ext = '.siqh/.siqd'

		if suffixCtl.value == -2:
			suf = ''
		elif suffixCtl.value == -1:
			suf = '<timestamp>'
		elif suffixCtl.value >= 0:
			suf = '000x'
		return suf, ext

def streaming_setup_fixed():
	#this function sets up IQ streaming without command line user input
	bwHz_req = c_double(5e6)
	durationMsec = 1000
	waitTime = durationMsec/1e3/10
	fileDirectory = 'C:\SignalVu-PC Files\!garbage'
	fileName = 'stream_test'
	filenameBase = fileDirectory + '\\' + fileName
	streamingMode = 2
	#dest: 0 = client, 1 = .tiq, 2 = .siq, 3 = .siqd/.siqh
	dest = 1
	#dtype: 0 = single, 1 = int32, 2 = int16
	dtype = 2
	#SuffixCtl: -2 = none, -1 = YYYY.MM.DD.hh.mm.ss.msec, >0 = -xxxxx autoincrement
	suffixCtl = -2

	rsa.IQSTREAM_SetAcqBandwidth(bwHz_req)
	#rsa.IQSTREAM_GetAcqParameters(byref(bwHz_act), byref(sRate))
	rsa.IQSTREAM_SetOutputConfiguration(c_int(dest), c_int(dtype))
	rsa.IQSTREAM_SetDiskFilenameBase(c_char_p(filenameBase))
	rsa.IQSTREAM_SetDiskFilenameSuffix(c_int(suffixCtl))
	rsa.IQSTREAM_SetDiskFileLength(c_long(durationMsec))

	rsa.SetStreamADCToDiskPath(c_char_p(fileDirectory))
	rsa.SetStreamADCToDiskFilenameBase(c_char_p(fileName))
	rsa.SetStreamADCToDiskMaxTime(c_long(durationMsec))
	rsa.SetStreamADCToDiskMode(c_int(streamingMode))
	rsa.SetStreamADCToDiskMaxFileCount(c_int(1))

	return waitTime, dest, dtype, suffixCtl, fileDirectory, fileName, streamingMode

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
	cf = c_double(102.7e6)
	refLevel = c_double(-20)
	bwHz_act = c_double(0)
	sRate = c_double(0)
	dest = suffixCtl = streamingMode = streamtype = -1024

	#stream control variables
	#streaming status boolean variable
	complete = c_bool(False)
	#write status boolean variable (always true if non-triggered acquisition)
	writing = c_bool(False)
	#bool used for streaming IQ control
	streaming = True
	iqstream_info = IQSTRMFILEINFO()


	"""#################SEARCH/CONNECT#################"""
	search_connect()


	"""#################CONFIGURE INSTRUMENT#################"""
	rsa.CONFIG_Preset()
	rsa.CONFIG_SetCenterFreq(cf)
	rsa.CONFIG_SetReferenceLevel(refLevel)


	"""#################USER INPUT CONFIGURATION#################"""
	while (streamtype < 1) or (streamtype > 2):
		streamtype = int(input('Type 1 for IF streaming or 2 for IQ streaming.\n> '))
	#optional static setup functions for testing	
	#waitTime, dest, dtype, suffixCtl, fileDirectory, fileName, streamingMode = streaming_setup_fixed()

	
	if streamtype == 1:
		#default conditions
		streamingMode = maxFiles = -1024
		#configure streamed file location
		while True:
			try:
				fileDirectory = input('Enter destination directory without quotes.\n> ')
				if not os.path.isdir(fileDirectory):
					raise ValueError
				fileName = input('Enter file name in quotes without extension.\n> ')
				break
			except:
				print('Error in input. Try again.')
				pass
		rsa.IFSTREAM_SetDiskFilePath(c_wchar_p(fileDirectory))
		rsa.IFSTREAM_SetDiskFilenameBase(c_wchar_p(fileName))

		#file duration
		durationMsec = int(input('Enter file duration in milliseconds.\n> '))
		rsa.IFSTREAM_SetDiskFileLength(c_int(durationMsec))
		waitTime = durationMsec/1e3/10

		#streaming mode
		while (streamingMode < 0) or (streamingMode > 1):
			streamingMode = int(input('Enter streaming mode: 0 = raw, 1 = formatted.\n> '))
		rsa.IFSTREAM_SetDiskFileMode(c_int(streamingMode))

		#max files
		while maxFiles < 1:
			maxFiles = int(input('Enter maximum number of files to save.\n> '))
		rsa.IFSTREAM_SetDiskFileCount(c_int(maxFiles))

	elif streamtype == 2:
		bwHz_req = dest = dtype = suffixCtl = -1024	
		#IQ bandwidth
		while (bwHz_req != 5e6) and (bwHz_req != 10e6) and (bwHz_req != 20e6) and (bwHz_req != 40e6):
			bwHz_req = int(input('Input IQ bandwidth (5e6, 10e6, 20e6, or 40e6).\n> '))
		bwHz_req = c_double(bwHz_req)
		rsa.IQSTREAM_SetAcqBandwidth(bwHz_req)
		rsa.IQSTREAM_GetAcqParameters(byref(bwHz_act), byref(sRate))

		#destination and data type
		while (dest < 1) or (dest > 3):
			dest = input('Enter destination: 1 = .tiq, 2 = .siq, 3 = .siqd/.siqh.\n> ')
		while (dtype < 0) or (dtype > 2):
			dtype = int(input('Enter Data Type: 0 = single, 1 = int32, 2 = int16.\n> '))
		ret = rsa.IQSTREAM_SetOutputConfiguration(c_int(dest), c_int(dtype))
		if ret != 0:
			print('Error: '+ str(ret))

		#streamed file location	
		while True:
			try:
				fileDirectory = input('Enter destination directory in quotes.\n> ')
				if  not os.path.isdir(fileDirectory):
					raise ValueError
				fileName = input('Enter file name in quotes without extension.\n> ')
				break
			except:
				print('Error in input. Try again.\n')
				pass
		filenameBase = fileDirectory + '\\' + fileName
		ret = rsa.IQSTREAM_SetDiskFilenameBase(c_char_p(filenameBase))
		if ret != 0:
			print('Error in IQSTREAM_SetDiskFileNameBase. Exiting.\n')
			exit()

		#suffix control
		while (suffixCtl < -2):
			suffixCtl = int(input('Select suffix type: -2 = none, -1 = timestamp, >0 = 5-digit autoincrement.\n> '))
		suffixCtl = c_int(suffixCtl)
		rsa.IQSTREAM_SetDiskFilenameSuffix(suffixCtl)

		#file duration
		durationMsec = -1
		while durationMsec <= 0:
			durationMsec = input('Enter file duration in milliseconds.\n> ')
		rsa.IQSTREAM_SetDiskFileLength(c_long(durationMsec))
		waitTime = durationMsec/1e3/10
		

	"""#################STREAMING#################"""
	"""
	Note: When the time limit specified by durationMsec is reached, there is a de facto 
	IQSTREAM_Stop(). Acquisition can be terminated early by explicitly sending 
	IQSTREAM_Stop().

	##########################################
	Run() MUST BE SENT before IQSTREAM_Start()
	##########################################
	"""
	repeat = 'yes'
	while repeat == 'yes':
		print('Beginning streaming.')
		complete.value = False
		streaming = True
		rsa.DEVICE_Run()
		if streamtype == 1:
			start = time.clock()
			rsa.SetStreamADCToDiskEnabled(c_bool(True))
			while streaming == True:
				time.sleep(waitTime)
				rsa.GetStreamADCToDiskActive(byref(writing))
				streaming = writing.value
			end = time.clock()
		elif streamtype == 2:
			start = time.clock()
			rsa.IQSTREAM_Start()
			while streaming == True:
				time.sleep(waitTime)
				rsa.IQSTREAM_GetDiskFileWriteStatus(byref(complete), byref(writing))
				print(complete)
				if complete.value == True:
					streaming = False
			end = time.clock()
			rsa.IQSTREAM_Stop()
			rsa.IQSTREAM_GetFileInfo(byref(iqstream_info))
			iqstream_status_parser(iqstream_info.acqStatus)
		print('Elapsed time: {} seconds.\n'.format(end-start))
		repeat = input('Repeat? yes=yes, anything else=no\n> ')
	rsa.DEVICE_Stop()

	suf, ext = suf_ext_parser(streamtype, streamingMode, dest, suffixCtl)
	print('File(s) saved at ' + str(fileDirectory) + '\\' + str(fileName) +
		suf + ext)

	print('Disconnecting.')
	rsa.DEVICE_Disconnect()

if __name__ == "__main__":
    main()

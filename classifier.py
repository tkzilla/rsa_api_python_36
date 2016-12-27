"""
Tektronix RSA API: Occupied Bandwidth and Peak Power
Author: Morgan Allison
Date created: 6/15
Date edited: 11/16
Windows 7 64-bit
RSA API version 3.9.0029
Python 3.5.2 64-bit (Anaconda 4.2.0)
NumPy 1.11.0, MatPlotLib 1.5.3
To get Anaconda: http://continuum.io/downloads
Anaconda includes NumPy and MatPlotLib
"""

from ctypes import *
import numpy as np
import matplotlib.pyplot as plt
import os
from pickle import dump


"""
#############################################################
C:\Tektronix\RSA_API\lib\x64 needs to be added to the 
PATH system environment variable
#############################################################
"""
os.chdir("C:\\Tektronix\\RSA_API\\lib\\x64")
rsa = cdll.LoadLibrary("RSA_API.dll")


"""################CLASSES AND FUNCTIONS################"""
#create Spectrum_Settings data structure
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


def calc_int_power(trace, span, rbw, tLength):
	#convert dBm to mW and normalize to span
	mW = 10**(trace/10)*span/rbw/tLength
	# numerical integration --> total power in mW
	totPower = np.trapz(mW)
	# print('Total Power in dBm: {:.2f}'.format(10*np.log10(totPower)))
	return mW, totPower


def calc_channel_power(trace, f1, f2, freq, rbw):
	# Get indices of f1 and f2
	if f1 == f2 == 0:
		return 0
	else:
		f1Index = np.where(freq==f1)[0][0]
		f2Index = np.where(freq==f2)[0][0]
		# calculate integrated power betweeen f1 and f2
		mW = 10**(trace[f1Index:f2Index]/10)*(f2-f1)/rbw/(f2Index-f1Index)
		totPower = np.trapz(mW)
		# if totPower <= 0:
		# 	print('Total Power: {}'.format(totPower))
		# 	print('F1: {:.3f} GHz. F2: {:.3f} GHz'.format(f1/1e9, f2/1e9))
		# 	plt.figure(1)
		# 	plt.plot(freq, trace)
		# 	plt.show(block=False)
		return 10*np.log10(totPower)

def calc_obw_pcnt(trace, freq, span, rbw, tLength):
	#integrated power calculation
	mW, totPower = calc_int_power(trace, span, rbw, tLength)
	obwPcnt = 0.99

	#Sum the power of each point together working in from both sides of the 
	#trace until the sum is > 1-obwPcnt of total power. When the sum is reached, 
	#save the frequencies at which it occurs.
	psum = j = k = 0
	debug = []
	left = []
	right = []
	target = (1-obwPcnt)*totPower
	while psum <= target:
		# left side
		if psum <= target/2:
			j += 1
			psum += mW[j]
			left.append(mW[j])
		# right side
		else:
			k -= 1
			psum += mW[k]
			right.append(mW[k])
		debug.append(psum)
	f1 = freq[j]
	f2 = freq[k]

	if f2<f1:
		psum = j = k = 0
		while psum <= target:
		# right side
			if psum <= target/2:
				k -= 1
				psum += mW[k]
				right.append(mW[k])
			# left side
			else:
				j += 1
				psum += mW[j]
				left.append(mW[j])
			debug.append(psum)
		# if j == 0 or k == 0:
		# 	f1 = f2 = 0
		# else:
		f1 = freq[j]
		f2 = freq[k]
	# if f2-f1 > 25e6:
	# 	# print('F1: {:.3f} GHz. F2: {:.3f} GHz. OBW: {:.3f}'.format(f1/1e9, f2/1e9, (f2-f1)))
	# 	plt.figure(1)
	# 	plt.plot(freq, trace)
	# 	plt.axvline(freq[j], color='g')
	# 	plt.axvline(freq[k], color='r')
	# 	plt.show(block=False)
	# #occupied bandwidth is the difference between f1 and f2
	# obw = f2-f1
	# print('OBW: %f MHz' % (obw/1e6))
	#print('Power at f1: %3.2f dBm. Power at f2: %3.2f dBm' % (trace[j], trace[k]))
	return f1, f2


def calc_obw_db(trace, freq, dB):
	peakPower = np.amax(trace)
	l = r = 0
	t1 = (peakPower-dB)
	t2 = (peakPower-dB/2)
	# start from outside
	if (np.amax(trace) - np.amin(trace)) < dB:
		print('Insufficient SNR.')
		return 0, 0
	try:
		# go in further than you need to
		while trace[l] < t2:
			l+=1
		# then move back out
		while trace[l] > t1:
			l-=1
		# repeat for other side
		while trace[r] < t2:
			r-=1
		while trace[r] > t1:
			r+=1
	except IndexError as idx:
		print('r: {}\nl: {}'.format(r,l))
		print('{}, trying inside.'.format(idx))
		# plt.figure(5)
		# plt.plot(freq,trace)
		# plt.axvline(freq[l+1], color='red')
		# plt.axvline(freq[r-1], color='red')
		# plt.show()		

		try:
			l = r = np.argmax(trace)
			# start from inside
			while trace[l] > (peakPower-dB):
				l -= 1
			while trace[r] > (peakPower-dB):
				r += 1
		except IndexError as idx:
			print('{}, setting f1 = f2 = 0.'.format(idx))
			return 0, 0

	return freq[l], freq[r]


# def calc_obw_pcnt(trace, freq, span, rbw, tLength):
# 	mW, totPower = calc_int_power(trace, span, rbw, tLength)
# 	obwPcnt = 0.5
# 	#Sum the power of each point together working out from the max value of the  
# 	#trace until the sum is > 1-obwPcnt of total power. When the sum is reached, 
# 	#save the frequencies at which it occurs.
# 	psum = 0
# 	j = k = np.argmax(trace)
# 	debug = []
# 	left = []
# 	right = []
# 	target = obwPcnt*totPower
# 	toggle = 1
# 	print('Target: {:.5f} mW'.format(target))
# 	print('Power at roughcf: {:.5f}'.format(mW[j]))
# 	while psum <= target:
# 		# left side
# 		if toggle == 1 and psum < target:
# 			j += 1
# 			psum += mW[j]
# 			left.append(mW[j])
# 			toggle = -1
# 		# right side
# 		elif toggle == -1 and psum < target:
# 			k -= 1
# 			psum += mW[k]
# 			right.append(mW[k])
# 			toggle = 1
# 		else:
# 			print('???????')
# 		debug.append(psum)
# 	f1 = freq[k]
# 	f2 = freq[j]

# 	# plt.figure(4, figsize=(20,10))
# 	# plt.subplot(211)
# 	# plt.plot(left)
# 	# plt.plot(right)
# 	# plt.plot(debug)
# 	# plt.subplot(212, axisbg='k')
# 	# plt.plot(freq, trace, color='y')
# 	# plt.axvline(f1, color='y')
# 	# plt.axvline(f2, color='y')
# 	# plt.axvline(freq[np.argmax(trace)], color='b')
# 	# plt.show()

# 	return f1, f2

def print_spectrum_settings(specSet):
	#print out spectrum settings for a sanity check
	print('Span: ' + str(specSet.span))
	print('RBW: ' + str(specSet.rbw))
	print('VBW Enabled: ' + str(specSet.enableVBW))
	print('VBW: ' + str(specSet.vbw))
	print('Trace Length: ' + str(specSet.traceLength))
	print('Window: ' + str(specSet.window))
	print('Vertical Unit: ' + str(specSet.verticalUnit))
	print('Actual Start Freq: ' + str(specSet.actualStartFreq))
	print('Actual End Freq: ' + str(specSet.actualStopFreq))
	print('Actual Freq Step Size: ' + str(specSet.actualFreqStepSize))
	print('Actual RBW: ' + str(specSet.actualRBW))
	print('Actual VBW: ' + str(specSet.actualVBW))


def main():
	"""################INITIALIZE VARIABLES################"""
	#main SA parameters
	specSet = Spectrum_Settings()
	tSetSize = 100

	enable = True       #spectrum enable
	cf = 2.435e9        #center freq
	refLevel = -30      #ref level
	attn = 0
	
	trigMode = 1                  #0=freerun, 1=triggered
	trigLevel = -50               #trigger level in dBm
	trigSource = 1                #0=ext, 1=RFPower

	ready = c_bool(False)         #ready
	timeoutMsec = c_int(100)      #timeout
	trace = c_int(0)              #select Trace 1 
	detector = c_int(1)           #set detector type to max


	"""################SEARCH/CONNECT################"""
	search_connect()


	"""################CONFIGURE INSTRUMENT################"""
	rsa.CONFIG_Preset()
	rsa.CONFIG_SetCenterFreq(c_double(cf))
	rsa.CONFIG_SetReferenceLevel(c_double(refLevel))
	
	rsa.CONFIG_SetAutoAttenuationEnable(c_bool(False))
	rsa.CONFIG_SetRFAttenuator(c_double(attn))
	rsa.CONFIG_SetRFPreampEnable(c_bool(True))

	rsa.TRIG_SetTriggerMode(c_int(trigMode))
	rsa.TRIG_SetIFPowerTriggerLevel(c_double(trigLevel))
	rsa.TRIG_SetTriggerSource(c_int(trigSource))
	rsa.TRIG_SetTriggerPositionPercent(c_double(10))

	rsa.SPECTRUM_SetEnable(c_bool(enable))
	rsa.SPECTRUM_SetDefault()
	rsa.SPECTRUM_GetSettings(byref(specSet))

	#configure desired spectrum settings
	#some fields are left blank because the default
	#values set by SPECTRUM_SetDefault() are acceptable
	specSet.span = c_double(40e6)
	specSet.rbw = c_double(20e3)
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


	"""################INITIALIZE DATA TRANSFER VARIABLES################"""
	#initialize variables for GetTrace
	traceArray = c_float * specSet.traceLength
	traceData = traceArray()
	outTracePoints = c_int()

	#generate frequency array for plotting the spectrum
	freq = np.arange(specSet.actualStartFreq, 
		specSet.actualStartFreq + specSet.actualFreqStepSize*specSet.traceLength, 
		specSet.actualFreqStepSize)

	trace = np.zeros((tSetSize,specSet.traceLength))
	obw = []#np.zeros(tSetSize)
	roughCF = []#np.zeros(tSetSize)
	chPow = []#np.zeros(tSetSize)
	peakPower = []#np.zeros(tSetSize)
	errors = []
	f1e = []
	f2e = []


	"""################ACQUIRE/PROCESS DATA################"""
	#start acquisition
	for i in range(tSetSize):
		ready.value = False
		rsa.DEVICE_Run()
		rsa.SPECTRUM_AcquireTrace()
		while ready.value == False:
			rsa.SPECTRUM_WaitForDataReady(timeoutMsec, byref(ready))
		rsa.SPECTRUM_GetTrace(c_int(0), specSet.traceLength, 
			byref(traceData), byref(outTracePoints))
		rsa.DEVICE_Stop()

		#convert trace data from a ctypes array to a numpy array
		trace[i] = np.ctypeslib.as_array(traceData)

		"""################FEATURE CALCULATION################"""
		# f1, f2 = calc_obw_pcnt(trace[i], freq, specSet.span, specSet.actualRBW, specSet.traceLength)
		f1, f2 = calc_obw_db(trace[i], freq, 20)
		if (f2-f1 > 0 and f2-f1 < 25e6):
			obw.append(f2-f1)
			roughCF.append(np.mean([f1,f2]))
			chPow.append(calc_channel_power(trace[i], f1, f2, freq, specSet.actualRBW))	#calculate this from calc_owb
			peakPower.append(np.amax(trace[i]))
		# if obw[i] > 30e6:
		# 	f1,f2 = calc_obw_pcnt(trace[i], freq, specSet.span, specSet.actualRBW, specSet.traceLength)
		if f2-f1 > 25e6:
			errors.append(trace[i])
			plt.figure(1)
			plt.subplot(111, axisbg='k')
			plt.title('>25')
			plt.plot(freq, trace[i])
			plt.axvline(f1, color='w')
			plt.axvline(f2, color='b')
			plt.show(block=False)
		# if obw[i] <= 0:
		# 	plt.figure(6)
		# 	plt.subplot(111, axisbg='y')
		# 	plt.title('<0')
		# 	plt.plot(freq,trace[i])
		# 	plt.axvline(f1, color='w')
		# 	plt.axvline(f2, color='b')
		# 	plt.show(block=False)
		

		# print('Rough CF: {:.3f} GHz'.format(roughCF[i]/1e9))
		# print('Channel power: {:.3f} dBm'.format(chPow[i]))
		# print('Peak Power: {:.3f} dBm'.format(peakPower[i]))
		# print('Occupied Bandwidth: {:.3f} MHz'.format(obw[i]/1e6))

		"""################SPECTRUM PLOT################"""
		# #plot the spectrum trace (optional)
		# plt.figure(2, figsize=(20,10))
		# plt.subplot(111, axisbg='k')
		# plt.plot(freq, trace[i], 'y')
		# plt.xlabel('Frequency (Hz)')
		# plt.ylabel('Amplitude (dBm)')
		# plt.title('Spectrum')

		# #Place vertical bars at f1 and f2 and annotate measurement
		# plt.axvline(x=f1)
		# plt.axvline(x=f2)
		# plt.axvline(x=roughCF[i])
		# text_x = specSet.actualStartFreq + specSet.span/20
		# plt.text(text_x, np.amax(trace[i]), 'OBW: %5.4f MHz' % (obw[i]/1e6), color='white')

		# #BONUS clean up plot axes
		# xmin = np.amin(freq)
		# xmax = np.amax(freq)
		# plt.xlim(xmin,xmax)
		# ymin = np.amin(trace)-10
		# ymax = np.amax(trace)+10
		# plt.ylim(ymin,refLevel)
		# plt.show()


	with open('C:\\users\\mallison\\Documents\\GitHub\\RSA_API-Python-3.5\\error_traces.pickle', 'wb') as f:
		dump(errors, f)
	print('Disconnecting.')
	rsa.DEVICE_Disconnect()

	"""Save some features here"""
	# Feature matrix
	# delIndices = np.where(obw<=0)
	# np.delete(roughCF, delIndices)
	# np.delete(obw, delIndices)
	# np.delete(chPow, delIndices)
	# np.delete(peakPower, delIndices)
	X = np.stack((roughCF,obw,chPow,peakPower), axis=1)
	# with open("C:\users\mallison\Documents\GitHub\RSA_API-Python-3.5\ism_features.pickle", 'wb') as f:
		# dump(X,f)
	plt.figure(3, figsize=(20,10))
	plt.subplot(111)
	plt.scatter(np.array(roughCF)/1e9, np.array(obw)/1e6)
	plt.xlabel('Rough CF in GHz')
	plt.ylabel('OBW in MHz')
	plt.show()

	# for i in range(len(trace)):
	# 	plt.figure(1, figsize=(20,10))
	# 	plt.plot(freq, trace[i])
	# plt.show()


if __name__ == "__main__":
	main()

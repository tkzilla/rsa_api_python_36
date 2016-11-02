"""
Tektronix RSA API: GNSS Setup and Testing
Author: Morgan Allison
Date Created: 6/16
Date edited: 11/16
Windows 7 64-bit
RSA API version 3.7.0561
Python 3.5.2 64-bit (Anaconda 4.2.0)
NumPy 1.11.0, MatPlotLib 1.5.3
To get Anaconda: http://continuum.io/downloads
Anaconda includes NumPy and MatPlotLib
"""

from ctypes import *
import os, pynmea2, datetime, calendar

"""
################################################################
C:\Tektronix\RSA306 API\lib\x64 needs to be added to the 
PATH system environment variable
################################################################
"""
os.chdir("C:\\Tektronix\\RSA_API\\lib\\x64")
rsa = cdll.LoadLibrary("RSA_API.dll")

"""#################CLASSES AND FUNCTIONS#################"""
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


def setup_gnss(rsa, system=2):
	#setup variables
	enable = c_bool(True)
	powered = c_bool(True)
	installed = c_bool(False)
	msgLength = c_int(0)
	message = create_string_buffer(256)
	#1:GPS/GLONASS, 2:GPS/BEIDOU, 3:GPS, 4:GLONASS, 5:BEIDOU
	satSystem = c_int(system)

	#check for GNSS hardware
	rsa.GNSS_GetHwInstalled(byref(installed))
	if installed.value != True:
		print('No GNSS hardware installed, ensure there is a 1PPS signal present at the trigger/synch input.')
		input('Press ''ENTER'' to continue > ')
	else:
		#send setup commands to RSA
		rsa.GNSS_SetEnable(enable)
		rsa.GNSS_SetAntennaPower(powered)
		rsa.GNSS_SetSatSystem(satSystem)
		rsa.GNSS_GetEnable(byref(enable))
		rsa.GNSS_GetAntennaPower(byref(powered))
		rsa.GNSS_GetSatSystem(byref(satSystem))

	return installed.value


def get_gnss_message(rsa):
	msgLength = c_int(0)
	message = c_char_p('')
	numMessages = 10
	gnssMessage = []
	nmeaMessages = []

	#grab a certain number of GNSS message strings
	for i in range(numMessages):
		while msgLength.value == 0:
			rsa.GNSS_GetNavMessageData(byref(msgLength), byref(message))
		msgLength.value = 0
		#concatenate the new string
		gnssMessage += message.value
	#put all the continuous ascii text together
	messageString = ''.join(map(str, gnssMessage))
	#split message based on individual NMEA messages
	indivMessages = messageString.split('$')
	for i in range(len(indivMessages)):
		if 'GNGGA' in indivMessages[i]:
			print(indivMessages[i])
			try:
				nmeaMessages.append(pynmea2.parse(indivMessages[i]))
				print('Latitude: {}'.format(nmeaMessages[-1].latitude))
				print('Longitude: {}'.format(nmeaMessages[-1].longitude))
				print('Current time (GMT): {}'.format(nmeaMessages[-1].timestamp))
				#return the first complete parsable message
				return nmeaMessages[-1]
			#move on to the next message if there are problems with the first
			except pynmea2.nmea.ChecksumError:
				print('Checksum Error, trying again.')
			except AttributeError:
				print('Incomplete parsing, trying again.')
			except pynmea2.nmea.ParseError:
				print('Unable to parse data, trying again.')


def convert_to_unixtime(ts):
	#this function takes in a date-agnostic timestamp, combines it with 
	#the current date, and converts the full naive timestamp to unix time
	d = datetime.date.today()
	dts = datetime.datetime.combine(d, ts)
	unixTime = calendar.timegm(dts.timetuple())
	return unixTime


def main():
	"""#################INITIALIZE VARIABLES#################"""
	eventID = c_int(1)	#0:overrange, 1:ext trig, 2:1PPS
	eventOccurred = c_bool(False)
	eventTimestamp = c_uint64(0)
	hwInstalled = False

	"""#################SEARCH/CONNECT#################"""
	search_connect()

	"""#################CONFIGURE INSTRUMENT#################"""
	rsa.CONFIG_Preset()
	
	hwInstalled = setup_gnss(rsa)

	rsa.DEVICE_Run()
	
	if hwInstalled == True:
		"""#######USE THIS IF YOU HAVE AN RSA500/600 WITH GPS ANTENNA########"""
		print('Waiting for internal 1PPS.')
		while eventOccurred.value == False:
			rsa.GNSS_Get1PPSTimestamp(byref(eventOccurred), byref(eventTimestamp))
		nmeaMessage = get_gnss_message(rsa)
		unixTime = convert_to_unixtime(nmeaMessage.timestamp)
		print('Unix timestamp from NMEA messages: {}'.format(unixTime))
	else:
		"""#######USE THIS IF YOU HAVE AN RSA306 W/1PPS INPUT########"""
		print('Waiting for external 1PPS.')
		while eventOccurred.value == False:
			rsa.DEVICE_GetEventStatus(eventID, byref(eventOccurred), byref(eventTimestamp))
		
		"""################################################################
		<insert code that gets a unix timestamp from some GPS system here>
		   ################################################################"""
		
		unixTime = int(input('Enter any integer and press enter to continue. > '))

	print('Sample clock cycles at 1PPS event: {}'.format(eventTimestamp.value))
	
	refTimeSec = c_int64(unixTime)
	refTimeNsec = c_uint64(0)

	print('Setting reference time using GPS timestamp.')
	rsa.REFTIME_SetReferenceTime(refTimeSec, refTimeNsec, eventTimestamp)
	rsa.REFTIME_GetReferenceTime(byref(refTimeSec), byref(refTimeNsec), byref(eventTimestamp))
	print('Unix reference time assigned: {}'.format(refTimeSec.value))

	print('Disconnecting.')
	ret = rsa.DEVICE_Disconnect()

if __name__ == "__main__":
	main()

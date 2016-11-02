"""
Tektronix RSA API: Block IQ with Pulse Width Calculator
Author: Morgan Allison
Date Created: 5/15
Date edited: 11/16
Windows 7 64-bit
RSA API version 3.7.0561
Python 3.5.2 64-bit (Anaconda 4.2.0)
NumPy 1.11.0, MatPlotLib 1.5.3
To get Anaconda: http://continuum.io/downloads
Anaconda includes NumPy and MatPlotLib
"""

from ctypes import *
import numpy as np
import matplotlib.pyplot as plt
import os

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


def pulse_width_finder(data, thresh, startIndex):
    dPoint = np.amax(data) - thresh
    saved = data[startIndex]
    risingIndex = startIndex
    endIndex = len(data)
    fallingIndex = endIndex - 1

    for i in range(startIndex, endIndex):
        if data[i] <= dPoint:
            saved = data[i]
        else:
            if saved <= dPoint:
                saved = data[i]
                risingIndex = i
                break

    for j in range(risingIndex, endIndex):
        if data[j] >= dPoint:
            saved = data[j]
        else:
          if saved >= dPoint:
            saved = data[j]
            fallingIndex = j
            break

    return risingIndex, fallingIndex


def main():
    """#################INITIALIZE VARIABLES#################"""
    #main SA parameters
    refLevel = c_double(0)
    cf = c_double(1e9)
    iqBandwidth = c_double(40e6)
    acqTime = 1e-3
    """
    NB: Record length is set below because it depends on the IQ sample rate.
    Consequently, the iqArray data type is set below place for the same reason
    """

    actLength = c_int(0)
    trigMode = c_int(1)
    trigLevel = c_double(-10)
    trigSource = c_int(1)
    iqSampleRate = c_double(0)
    runMode = c_bool(False)
    timeoutMsec = c_int(1000)
    ready = c_bool(False)


    """#################SEARCH/CONNECT#################"""
    search_connect()


    """#################CONFIGURE INSTRUMENT#################"""
    rsa.CONFIG_Preset()
    rsa.IQBLK_SetIQBandwidth(iqBandwidth)
    rsa.IQBLK_GetIQSampleRate(byref(iqSampleRate))

    #record length dependent data transfer variables
    recordLength = c_int(int(iqSampleRate.value*acqTime))
    iqArray =  c_float*recordLength.value
    iData = iqArray()
    qData = iqArray()

    rsa.CONFIG_SetReferenceLevel(refLevel)
    rsa.CONFIG_SetCenterFreq(cf)
    rsa.IQBLK_SetIQRecordLength(recordLength)
    rsa.TRIG_SetTriggerMode(trigMode)
    rsa.TRIG_SetIFPowerTriggerLevel(trigLevel)
    rsa.TRIG_SetTriggerSource(trigSource)
    rsa.TRIG_SetTriggerPositionPercent(c_double(10))


    """#################ACQUIRE/PROCESS DATA#################"""
    rsa.DEVICE_Run()

    #get relevant settings values
    #this requires that the RSA306 be running
    rsa.CONFIG_GetCenterFreq(byref(cf))
    rsa.CONFIG_GetReferenceLevel(byref(refLevel))
    rsa.IQBLK_GetIQBandwidth(byref(iqBandwidth))
    rsa.IQBLK_GetIQRecordLength(byref(recordLength))
    rsa.IQBLK_GetIQSampleRate(byref(iqSampleRate))
    rsa.TRIG_GetTriggerMode(byref(trigMode))
    rsa.TRIG_GetIFPowerTriggerLevel(byref(trigLevel))
    rsa.TRIG_GetTriggerSource(byref(trigSource))
    rsa.DEVICE_GetEnable(byref(runMode))

    print('Run Mode:' + str(runMode.value))
    print('Reference level: ' + str(refLevel.value) + ' dBm')
    print('Center frequency: ' + str(cf.value/1e6) + ' MHz')
    print('IQ Bandwidth: ' + str(iqBandwidth.value/1e6) + ' MHz')
    print('Record length: ' + str(recordLength.value))
    print('Trigger mode: ' + str(trigMode.value))
    print('Trigger level: ' + str(trigLevel.value) + ' dBm')
    print('Trigger Source: ' + str(trigSource.value))
    print('IQ Sample rate: ' + str(iqSampleRate.value/1e6) + ' MS/sec')
    print('IQ Sample period: {0:.9f} sec'.format(1.0/iqSampleRate.value))

    print('\nAcquiring IQ data.')
    if trigMode.value == 1:
        print('Waiting for trigger.')

    rsa.IQBLK_AcquireIQData()
    #check for data ready
    while ready.value == False:
        ret = rsa.IQBLK_WaitForIQDataReady(timeoutMsec, byref(ready))

    #query I and Q data
    rsa.IQBLK_GetIQDataDeinterleaved(byref(iData), byref(qData), byref(actLength), recordLength)
    print('Got IQ data')
    print('Processing pulse widths, please wait.')
    rsa.DEVICE_Stop()

    #convert ctypes array to numpy array for ease of use
    I = np.ctypeslib.as_array(iData)
    Q = np.ctypeslib.as_array(qData)

    #power in dBm
    #10log(Vrms^2/(R*1mW)
    #There's an "extra" factor of 2 in the denominator from the RMS conversion
    avt = 10*np.log10((I**2+Q**2)/(2*50*1e-3))

    thresh = 10
    risingIndex = fallingIndex = 0
    """
    ########################################################
    NB: NEVER INITIALIZE MULTIPLE VARIABLES SIMULTANEOUSLY
    WITH EMPTY LISTS IN PYTHON. THEY SHARE THE SAME MEMORY
    AND CAUSE ALL SORTS OF ISSUES.
    ########################################################
    """
    pulseWidth = []
    pwRisingIndices = []
    pwFallingIndices = []
    time = np.linspace(0,recordLength.value/iqSampleRate.value,recordLength.value)

    #find pulse edge indices and convert to pulse width
    while fallingIndex < (recordLength.value-1):
        risingIndex, fallingIndex = pulse_width_finder(avt, thresh, fallingIndex)
        pwRisingIndices.append(risingIndex)
        pwFallingIndices.append(fallingIndex)
        pulseWidth.append(time[fallingIndex] - time[risingIndex])
      
    #remove first/last pulses, usually outliers. delete/comment this if you like
    try:
        del(pulseWidth[0])
        del(pulseWidth[-1])
        for i in range(len(pulseWidth)):
            print('Pulse {0} width: {1:.9f} sec'.format(i, (pulseWidth[i])))
            print('Average pulse width: {} seconds'.format(np.mean(pulseWidth)))
            print('Number of pulses detected: {}'.format(len(pulseWidth)-1))
    except IndexError:
        print('1 or fewer pulses detected.')
  

    """#################PLOTS#################"""
    plt.suptitle('Amplitude vs Time', fontsize='20')
    plt.subplot(111, axisbg='k')
    plt.title('Red = Rising Edge, Blue = Falling Edge', fontsize='12')
    plt.plot(time*1e3,avt, c='yellow')
    plt.ylabel('Amplitude (dBm)')
    plt.xlabel('Time (msec)')
    for i in range(len(pwRisingIndices)-1):
        plt.axvline(x=time[pwRisingIndices[i]]*1e3, c='red')
        plt.axvline(x=time[pwFallingIndices[i]]*1e3, c='blue')
    plt.show()

    print('Disconnecting.')
    ret = rsa.DEVICE_Disconnect()

if __name__ == "__main__":
    main()

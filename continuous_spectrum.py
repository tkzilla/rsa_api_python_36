"""
#### NEW RSA_API VERSION ####
Tektronix RSA API: Continuous Spectrum
Author: Morgan Allison
Date created: 6/15
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
    #connect to the first RSA

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
    """#################INITIALIZE VARIABLES#################"""
    #main SA parameters
    specSet = Spectrum_Settings()
    enable = c_bool(True)       #spectrum enable
    cf = c_double(2.4453e9)          #center freq
    refLevel = c_double(-30)      #ref level
    ready = c_bool(False)       #ready
    timeoutMsec = c_int(100)    #timeout
    trace = c_int(0)            #select Trace 1 
    detector = c_int(1)         #set detector type to max
    acqTime = 3                 #time to run script
    end = -1024


    """#################SEARCH/CONNECT#################"""
    selection = search_connect()


    """#################CONFIGURE INSTRUMENT#################"""
    rsa.CONFIG_Preset()
    rsa.CONFIG_SetCenterFreq(cf)
    rsa.CONFIG_SetReferenceLevel(refLevel)
    rsa.SPECTRUM_SetEnable(enable)
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
    ppow = np.zeros(specSet.traceLength)
    ppf = np.zeros(specSet.traceLength)

    
    #prepare plot window for periodic updates
    plt.figure(selection)
    plt.subplot(111, axisbg='k')
    specPlot,  = plt.plot(ppow, ppf, 'y')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Amplitude (dBm)')
    plt.title('Spectrum')
    peakFreqLine = plt.axvline(x=0)
    peakPowerText = plt.text(0,0,'')
    plt.ion()
    plt.xlim(np.amin(freq), np.amax(freq))
    plt.ylim(refLevel.value-100, refLevel.value)
    plt.show()    

    """#################ACQUIRE/PROCESS DATA#################"""
    #start acquisition
    spectrums = 0
    rsa.DEVICE_Run()
    start = time.clock()
    while end - start < acqTime:
        rsa.SPECTRUM_AcquireTrace()
        while ready.value == False:
            rsa.SPECTRUM_WaitForDataReady(timeoutMsec, byref(ready))
        ready.value = False
        rsa.SPECTRUM_GetTrace(c_int(0), specSet.traceLength, 
            byref(traceData), byref(outTracePoints))
        spectrums += 1
        
        
        """#################SPECTRUM PLOT#################"""
        
        #update spectrum trace
        peakFreqLine.remove()
        peakPowerText.remove()
        """
        if spectrums == 1:
            specPlot.set_xdata(freq)
        specPlot.set_ydata(traceData)
        """
        plt.plot(freq, traceData)

        #calculate and annotate peak power and frequency
        peakPower = np.amax(traceData)
        peakPowerFreq = freq[np.argmax(traceData)]
        print('Peak power in spectrum: %4.3f dBm @ %d Hz' % 
            (peakPower, peakPowerFreq))
        
        peakFreqLine = plt.axvline(x=peakPowerFreq)
        text_x = specSet.actualStartFreq + specSet.span/20
        peakPowerText = plt.text(text_x, peakPower, 
            'Peak power in spectrum: %4.3f dBm @ %5.4f MHz' % 
            (peakPower, peakPowerFreq/1e6), color='white')
        
        plt.draw()

        #plt.pause(.001)
        end = time.clock()

    #comment this out if you want the plot to stay until the script finishes
    rsa.DEVICE_Stop()
    plt.close()    
    print('Disconnecting.')
    print('{} spectrums in {} seconds: {} spectrums per second.'.format(spectrums, acqTime, spectrums/acqTime))
    sps = float(acqTime)/spectrums
    print('Also {} seconds per trace.'.format(sps))
    rsa.DEVICE_Disconnect()

if __name__ == "__main__":
    main()
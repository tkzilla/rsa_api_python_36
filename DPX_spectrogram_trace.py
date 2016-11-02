"""
RSA API: DPX Spectrogram Trace Visualizer
Author: Morgan Allison (and Dave Maciupa)
Date created: 11/15
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
         
 #create DPX Spectrogram Settings data structure
class DPX_SogramSettingStruct(Structure):
    _fields_ = [('bitmapWidth', c_int32), ('bitmapHeight', c_int32),
    ('sogramTraceLineTime', c_double), ('sogramBitmapLineTime', c_double)]

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
        
def print_sogramSettings(sogramSettings):
    print('\nSpectrogram Settings')
    print('bitmapWidth: ' + str(sogramSettings.bitmapWidth))
    print('bitmapHeight: ' + str(sogramSettings.bitmapHeight))
    print('sogramTraceLineTime: ' + str(sogramSettings.sogramTraceLineTime))
    print('sogramBitmapLineTime: ' + str(sogramSettings.sogramBitmapLineTime))
        
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

    ssStruct = DPX_SogramSettingStruct()
    dsStruct = DPX_SettingStruct()
    fb = DPX_FrameBuffer()

    #SA setup
    cf = c_double(2.4453e9)              #center freq
    refLevel = c_double(-40)          #ref level
    
    #bools/timeouts
    enable = c_bool(True)           #DPX enable
    frameAvailable = c_bool(False)  #DPX frame available check
    ready = c_bool(False)           #ready check
    timeoutMsec = c_int(500)        #timeout

    #for DPX_SetSogramParameters
    timePerBitmapLine = c_double(1e-3)  #time per bitmap line
    timeResolution = c_double(1e-3)     #time per DPXogram trace
    maxPower = c_double(0)
    minPower = c_double(maxPower.value - 100)

    #for DPX_SetParameters
    fspan = c_double(40e6)
    rbw = c_double(fspan.value/100)
    tracePtsPerPixel = c_int(1)
    yUnit = c_int(0)        #VerticalUnit_dBm
    yTop = c_double(0)
    yBottom = c_double(yTop.value - 100)
    infinitePersistence = c_bool(0)
    persistenceTimeSec = c_double(1.0)
    showOnlyTrigFrame = c_bool(0)
    traceType = c_int(1)    #+peak

    #spectrum bitmap width, height, and size are all fixed values
    bitmapWidth = c_int(801)
    bitmapHeight = c_int(201)
    #bitmapSize = bitmapWidth.value*bitmapHeight.value

    #for DPX_GetSogramHiResLine
    intArray = c_int16*TRACEPOINTS
    vData = intArray()
    vDataSize = c_int32(0)
    lineIndex = c_int32(0)
    dataSF = c_double(0)
    tracePoints = c_int32(TRACEPOINTS)
    firstValidPoint = c_int32(0)

    #for DPX_GetSogramHiResLineCount
    lineCount = c_int(0)

        
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
    rsa.DPX_SetSogramParameters(timePerBitmapLine, timeResolution, 
        maxPower, minPower)
    rsa.DPX_Configure(c_bool(True),c_bool(True))
    
    rsa.DPX_GetSogramSettings(byref(ssStruct))
    rsa.DPX_GetSettings(byref(dsStruct))

    print('DPX Bandwidth: %d MHz' % (fspan.value/1e6))

    print_sogramSettings(ssStruct)
    print_dpxSettings(dsStruct)


    """#################ACQUIRE DATA#################"""
    print('\nDPXogram is being generated')

    #acquisition loop
    rsa.DEVICE_Run()
    rsa.DPX_Reset()

    while frameAvailable.value == False:
        rsa.DPX_IsFrameBufferAvailable(byref(frameAvailable))
        while ready.value == False:
            rsa.DPX_WaitForDataReady(c_int(1000), byref(ready))
    rsa.DPX_GetFrameBuffer(byref(fb))
    rsa.DPX_FinishFrameBuffer()

    rsa.DEVICE_Stop()

    rsa.DPX_GetSogramHiResLineCountLatest(byref(lineCount));
    numTraces = lineCount.value-1
    print('Lines in DPXogram: %d' % numTraces)
    sogram = np.empty((numTraces,dsStruct.bitmapWidth))

    for i in range(numTraces):
        ret = rsa.DPX_GetSogramHiResLine(vData, byref(vDataSize), c_int32(i), 
        byref(dataSF), tracePoints, firstValidPoint)
        sogram[i] = np.ctypeslib.as_array(vData)

    if ret != 0:
        print('Error in DPX_GetSogramHiResLine: ' + str(ret))


    """#################PROCESS DATA#################"""
    bitmapFreq = np.linspace((cf.value - fspan.value/2), (cf.value + fspan.value/2), 
        fb.sogramBitmapWidth)
    
    #grab spectrogram bitmap
    #specifying the shape of the destination variable is important
    dpxogramBitmap = np.ctypeslib.as_array(fb.sogramBitmap, 
        shape=(fb.sogramBitmapSize,))
    dpxogramTimeArray = np.ctypeslib.as_array(fb.sogramBitmapTimestampArray, 
        shape=(numTraces,))
    dpxogramBitmap = dpxogramBitmap[0:10680].reshape((numTraces,fb.sogramBitmapWidth))


    """#################PLOT#################"""
    #create frequency array and scale DPXogram traces
    sogramFreq = np.linspace((cf.value - fspan.value/2), (cf.value + fspan.value/2), 
        dsStruct.bitmapWidth)
    sogram = sogram*dataSF.value

    #This plot is a composite 3D representation of all DPXogram traces
    fig2 = plt.figure(figsize=(12,12))
    ax2 = fig2.gca(projection='3d')
    for i in range(numTraces):
        ax2.plot(sogramFreq, sogram[i], i*timeResolution.value, 'b', zdir='y')
    plt.title('DPXogram Traces')
    plt.ylim(0, numTraces*timeResolution.value)
    ax2.set_zlim(np.amin(sogram), np.amax(sogram))
    ax2.set_xlabel('Frequency (Hz)')
    ax2.set_ylabel('Time (sec)')
    ax2.set_zlabel('Amplitude (dBm)')
    plt.show()

    #This commented section is a 3D representation of the DPXogram bitmap
    #This is not used directly because the amplitude values must be scaled
    """
    fig1 = plt.figure(figsize=(12,12))
    time = np.empty(fb.sogramBitmapWidth,)
    ax1 = fig1.gca(projection='3d')
    for i in range(numTraces):
        ax1.plot(bitmapFreq,dpxogramBitmap[i], i, zdir='y')
        plt.ylim(0,40)
        ax1.set_zlim(np.amin(dpxogramBitmap),np.amax(dpxogramBitmap))
    """
    

    """#################DISCONNECT#################"""
    print('\nDisconnecting.')
    rsa.DEVICE_Disconnect()

if __name__ == "__main__":
    main()
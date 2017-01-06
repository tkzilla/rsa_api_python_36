"""
Tektronix RSA_API Example
Author: Morgan Allison
Date created: 6/15
Date edited: 1/17
Windows 7 64-bit
RSA API version 3.9.0029
Python 3.5.2 64-bit (Anaconda 4.2.0)
NumPy 1.11.2, MatPlotLib 1.5.3
Download Anaconda: http://continuum.io/downloads
Anaconda includes NumPy and MatPlotLib
Download the RSA_API: http://www.tek.com/model/rsa306-software
Download the RSA_API Documentation:
http://www.tek.com/spectrum-analyzer/rsa306-manual-6

YOU WILL NEED TO REFERENCE THE API DOCUMENTATION
"""

from ctypes import *
from os import chdir
from mpl_toolkits.mplot3d import Axes3D
import time
import numpy as np
import matplotlib.pyplot as plt

"""
#############################################################
C:\Tektronix\RSA_API\lib\x64 needs to be added to the 
PATH system environment variable
#############################################################
"""
chdir("C:\\Tektronix\\RSA_API\\lib\\x64")
rsa = cdll.LoadLibrary("RSA_API.dll")


"""################CLASSES AND FUNCTIONS################"""
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
    _fields_ = [('timestamp', c_int64), 
    ('acqDataStatus', c_uint16)]


class DPX_SettingStruct(Structure):
    _fields_ = [('enableSpectrum', c_bool), 
    ('enableSpectrogram', c_bool),
    ('bitmapWidth', c_int32), 
    ('bitmapHeight', c_int32),
    ('traceLength', c_int32), 
    ('decayFactor', c_float),
    ('actualRBW', c_double)]
    

class DPX_SogramSettingStruct(Structure):
    _fields_ = [('bitmapWidth', c_int32), 
    ('bitmapHeight', c_int32),
    ('sogramTraceLineTime', c_double), 
    ('sogramBitmapLineTime', c_double)]


class DPX_FrameBuffer(Structure):
    _fields_ = [('fftPerFrame', c_int32), 
    ('fftCount', c_int64),
    ('frameCount', c_int64), 
    ('timestamp', c_double),
    ('acqDataStatus', c_uint32), 
    ('minSigDuration', c_double),
    ('minSigDurOutOfRange', c_bool), 
    ('spectrumBitmapWidth', c_int32), 
    ('spectrumBitmapHeight', c_int32), 
    ('spectrumBitmapSize', c_int32),
    ('spectrumTraceLength', c_int32), 
    ('numSpectrumTraces', c_int32),
    ('spectrumEnabled', c_bool), 
    ('spectrogramEnabled', c_bool),
    ('spectrumBitmap', POINTER(c_float)), 
    ('spectrumTraces', POINTER(POINTER(c_float))), 
    ('sogramBitmapWidth', c_int32), 
    ('sogramBitmapHeight',c_int32),
    ('sogramBitmapSize', c_int32), 
    ('sogramBitmapNumValidLines',c_int32),
    ('sogramBitmap', POINTER(c_uint8)),
    ('sogramBitmapTimestampArray', POINTER(c_double)), 
    ('sogramBitmapContainTriggerArray', POINTER(c_double))]


class IQSTREAM_File_Info(Structure):
   _fields_ = [('numberSamples', c_uint64), 
   ('sample0Timestamp', c_uint64),
   ('triggerSampleIndex', c_uint64), 
   ('triggerTimestamp', c_uint64),
   ('acqStatus', c_uint32), 
   ('filenames', c_wchar_p)]


def err_check(returnStatus):
    if returnStatus != 0:
        print('Error: {}'.format(returnStatus))
        print('Exiting script.')
        exit()


def search_connect():
    numFound = c_int(0)
    intArray = c_int*10
    deviceIDs = intArray()
    deviceSerial = create_string_buffer(8)
    deviceType = create_string_buffer(8)
    apiVersion = create_string_buffer(16)

    rsa.DEVICE_GetAPIVersion(apiVersion)
    print('API Version {}'.format(apiVersion.value.decode()))

    ret = rsa.DEVICE_Search(byref(numFound), deviceIDs, 
        deviceSerial, deviceType)
    err_check(ret)

    if numFound.value < 1:
        rsa.DEVICE_Reset(c_int(0))
        print('No instruments found. Exiting script.')
        exit()
    elif numFound.value == 1:
        print('One device found.')
        print('Device type: {}'.format(deviceType.value.decode()))
        print('Device serial number: {}'.format(deviceSerial.value.decode()))
        ret = rsa.DEVICE_Connect(deviceIDs[0])
        err_check(ret)
    else:
        # corner case
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
        ret = rsa.DEVICE_Connect(deviceIDs[selection])
        err_check(ret)
    rsa.CONFIG_Preset()


"""################SPECTRUM EXAMPLE################"""
def config_spectrum(cf=1e9, refLevel=0, span=40e6, rbw=300e3):
    rsa.SPECTRUM_SetEnable(c_bool(True))
    rsa.CONFIG_SetCenterFreq(c_double(cf))
    rsa.CONFIG_SetReferenceLevel(c_double(refLevel))

    rsa.SPECTRUM_SetDefault()
    specSet = Spectrum_Settings()
    rsa.SPECTRUM_GetSettings(byref(specSet))
    specSet.span = span
    specSet.rbw = rbw
    rsa.SPECTRUM_SetSettings(specSet)
    rsa.SPECTRUM_GetSettings(byref(specSet))
    return specSet


def create_frequency_array(specSet):
    # Create array of frequency data for plotting the spectrum.
    freq = np.arange(specSet.actualStartFreq, specSet.actualStartFreq 
        + specSet.actualFreqStepSize*specSet.traceLength, 
        specSet.actualFreqStepSize)
    return freq


def acquire_spectrum(specSet):
    ready = c_bool(False)
    traceArray = c_float*specSet.traceLength
    traceData = traceArray()
    outTracePoints = c_int(0)

    rsa.DEVICE_Run()
    rsa.SPECTRUM_AcquireTrace()
    while ready.value == False:
        rsa.SPECTRUM_WaitForDataReady(c_int(100), byref(ready))
    rsa.SPECTRUM_GetTrace(c_int(0), specSet.traceLength, byref(traceData), 
        byref(outTracePoints))
    rsa.DEVICE_Stop()
    return np.array(traceData)


def spectrum_example():
    search_connect()
    cf = 2.4453e9
    refLevel = -30
    span = 40e6
    rbw = 10e3
    specSet = config_spectrum(cf, refLevel, span, rbw)
    trace = acquire_spectrum(specSet)
    freq = create_frequency_array(specSet)
    peakPower, peakFreq = peak_power_detector(freq, trace)

    fig = plt.figure(1,figsize=(20,10))
    ax = plt.subplot(111, axisbg='k')
    ax.plot(freq, trace, color='y')
    ax.set_title('Spectrum Trace')
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Amplitude (dBm)')
    ax.axvline(peakFreq)
    ax.text((freq[0]+specSet.span/20), peakPower, 
        'Peak power in spectrum: {:.2f} dBm @ {} MHz'.format(peakPower, 
            peakFreq/1e6), color='white')
    ax.set_xlim([freq[0], freq[-1]])
    ax.set_ylim([refLevel-100, refLevel])
    plt.tight_layout()
    plt.show()
    rsa.DEVICE_Disconnect()


"""################BLOCK IQ EXAMPLE################"""
def config_block_iq(cf=1e9, refLevel=0, iqBw=40e6, recordLength=10e3):
    recordLength = int(recordLength)
    rsa.CONFIG_SetCenterFreq(c_double(cf))
    rsa.CONFIG_SetReferenceLevel(c_double(refLevel))

    rsa.IQBLK_SetIQBandwidth(c_double(iqBw))
    rsa.IQBLK_SetIQRecordLength(c_int(recordLength))
    
    iqSampleRate = c_double(0)
    rsa.IQBLK_GetIQSampleRate(byref(iqSampleRate))
    # Create array of time data for plotting IQ vs time
    time = np.linspace(0,recordLength/iqSampleRate.value, recordLength)
    return time


def acquire_block_iq(recordLength=10e3):
    recordLength = int(recordLength)
    ready = c_bool(False)
    iqArray = c_float*recordLength
    iData = iqArray()
    qData = iqArray()
    outLength = 0
    rsa.DEVICE_Run()
    rsa.IQBLK_AcquireIQData()
    while ready.value == False:
        rsa.IQBLK_WaitForIQDataReady(c_int(100), byref(ready))
    rsa.IQBLK_GetIQDataDeinterleaved(byref(iData), byref(qData), 
        byref(c_int(outLength)), c_int(recordLength))
    rsa.DEVICE_Stop()

    IQ = np.array(iData) + 1j*np.array(qData)
    return IQ


def block_iq_example():
    search_connect()
    cf = 1e9
    refLevel = 0
    iqBw = 40e6
    recordLength = 10e3

    time = config_block_iq(cf, refLevel, iqBw, recordLength)
    IQ = acquire_block_iq(recordLength)

    fig = plt.figure(1, figsize=(20,10))
    fig.suptitle('I and Q vs Time', fontsize='20')
    ax1 = plt.subplot(211, axisbg='k')
    ax1.plot(time*1e3, np.real(IQ), color='y')
    ax1.set_ylabel('I (V)')
    ax1.set_xlim([time[0]*1e3, time[-1]*1e3])
    ax2 = plt.subplot(212, axisbg='k')
    ax2.plot(time*1e3, np.imag(IQ), color='c')
    ax2.set_ylabel('I (V)')
    ax2.set_xlabel('Time (msec)')
    ax2.set_xlim([time[0]*1e3, time[-1]*1e3])
    plt.tight_layout()
    plt.show()
    rsa.DEVICE_Disconnect()


"""################DPX EXAMPLE################"""
def config_DPX(cf=1e9, refLevel=0, span=40e6, rbw=300e3):
    yTop = refLevel
    yBottom = yTop - 100
    dpxSet = DPX_SettingStruct()
    rsa.CONFIG_SetCenterFreq(c_double(cf))
    rsa.CONFIG_SetReferenceLevel(c_double(refLevel))

    rsa.DPX_SetEnable(c_bool(True))
    rsa.DPX_SetParameters(c_double(span), c_double(rbw), c_int(801), c_int(1),
        c_int(0), c_double(yTop), c_double(yBottom), c_bool(False),
        c_double(1.0), c_bool(False))
    rsa.DPX_SetSogramParameters(c_double(1e-3), c_double(1e-3), 
        c_double(refLevel), c_double(refLevel-100))
    rsa.DPX_Configure(c_bool(True), c_bool(True))

    rsa.DPX_SetSpectrumTraceType(c_int32(0), c_int(2))
    rsa.DPX_SetSpectrumTraceType(c_int32(1), c_int(4))
    rsa.DPX_SetSpectrumTraceType(c_int32(2), c_int(0))

    rsa.DPX_GetSettings(byref(dpxSet))
    dpxFreq = np.linspace((cf-span/2), (cf+span/2), dpxSet.bitmapWidth)
    dpxAmp = np.linspace(yBottom, yTop, dpxSet.bitmapHeight)
    return dpxFreq, dpxAmp


def acquire_dpx_frame():
    frameAvailable = c_bool(False)
    ready = c_bool(False)
    fb = DPX_FrameBuffer()

    rsa.DEVICE_Run()
    rsa.DPX_Reset()

    while frameAvailable.value == False:
        rsa.DPX_IsFrameBufferAvailable(byref(frameAvailable))
        while ready.value == False:
            rsa.DPX_WaitForDataReady(c_int(100), byref(ready))
    rsa.DPX_GetFrameBuffer(byref(fb))
    rsa.DPX_FinishFrameBuffer()
    rsa.DEVICE_Stop()
    return fb


def extract_dpx_spectrum(fb):
    # When converting a ctypes pointer to a numpy array, we need to 
    # explicitly specify its length to dereference it correctly
    dpxBitmap = np.array(fb.spectrumBitmap[:fb.spectrumBitmapSize])
    dpxBitmap = dpxBitmap.reshape((fb.spectrumBitmapHeight, 
        fb.spectrumBitmapWidth))

    # Grab trace data and convert from W to dBm
    # Note: fb.spectrumTraces is a pointer to a pointer, so we need to 
    # go through an additional dereferencing step
    specTrace1 = 20*np.log10(np.array(
        fb.spectrumTraces[0][:fb.spectrumTraceLength])/1000)
    specTrace2 = 20*np.log10(np.array(
        fb.spectrumTraces[1][:fb.spectrumTraceLength])/1000)
    specTrace3 = 20*np.log10(np.array(
        fb.spectrumTraces[2][:fb.spectrumTraceLength])/1000)

    return dpxBitmap, specTrace1, specTrace2, specTrace3


def extract_dpxogram(fb):
    sogramSet = DPX_SogramSettingStruct()
    rsa.DPX_GetSogramSettings(byref(sogramSet))
    timeResolution = sogramSet.sogramTraceLineTime

    intArray = c_int16*fb.spectrumTraceLength
    vData = intArray()
    vDataSize = c_int32(0)
    dataSF = c_double(0)
    validTraces = fb.sogramBitmapNumValidLines
    dpxogram = np.empty((validTraces,fb.spectrumTraceLength))

    for i in range(validTraces):
        rsa.DPX_GetSogramHiResLine(vData, byref(vDataSize), c_int32(i), 
        byref(dataSF), c_int32(fb.spectrumTraceLength), c_int32(0))
        dpxogram[i] = np.array(vData)
    dpxogram = dpxogram*dataSF.value

    return dpxogram, timeResolution


def dpx_example():
    search_connect()
    cf = 2.4453e9
    refLevel = -30
    span = 40e6
    rbw = 100e3

    dpxFreq, dpxAmp = config_DPX(cf, refLevel, span, rbw)
    fb = acquire_dpx_frame()

    dpxBitmap, specTrace1, specTrace2, specTrace3 = extract_dpx_spectrum(fb)
    dpxogram, timeResolution = extract_dpxogram(fb)

    """################PLOT################"""
    # Plot out the three DPX spectrum traces
    fig = plt.figure(1, figsize=(22,12))
    ax1 = fig.add_subplot(131)
    ax1.set_title('DPX Spectrum Traces')
    ax1.set_xlabel('Frequency (Hz)')
    ax1.set_ylabel('Amplitude (dBm)')
    st1, = plt.plot(dpxFreq, specTrace1)
    st2, = plt.plot(dpxFreq, specTrace2)
    st3, = plt.plot(dpxFreq, specTrace3)
    ax1.legend([st1, st2, st3], ['Max Hold', 'Min Hold', 'Average'])
    ax1.set_xlim([dpxFreq[0], dpxFreq[-1]])

    # This figure is a 3D representation of the DPX bitmap  
    # The methodology was patched together from a few Matplotlib example files
    # If anyone can figure out how to do a 3D colormap, that'd be cool.
    ax2 = fig.add_subplot(132, projection='3d')
    for i in range(fb.spectrumBitmapHeight):
        index = fb.spectrumBitmapHeight-1-i
        ax2.plot(dpxBitmap[i], dpxFreq, dpxAmp[index], color='b')
    ax2.set_title('DPX Bitmap')
    ax2.set_zlim(refLevel-100, refLevel)
    ax2.set_xlabel('Spectral Density (counter hits)')
    ax2.set_ylabel('Frequency (Hz)')
    ax2.set_zlabel('Amplitude (dBm)')

    # This plot is a composite 3D representation of all DPXogram traces
    ax3 = fig.add_subplot(133, projection='3d')
    for i in range(fb.sogramBitmapNumValidLines):
        ax3.plot(dpxFreq, dpxogram[i], i*timeResolution, color='b', zdir='y')
    ax3.set_title('DPXogram Traces')
    ax3.set_ylim(0, fb.sogramBitmapNumValidLines*timeResolution)
    ax3.set_zlim(np.amin(dpxogram), np.amax(dpxogram))
    ax3.set_xlabel('Frequency (Hz)')
    ax3.set_ylabel('Time (sec)')
    ax3.set_zlabel('Amplitude (dBm)')
    plt.tight_layout()
    plt.show()
    rsa.DEVICE_Disconnect()


"""################IF STREAMING EXAMPLE################"""
def config_if_stream(cf=1e9, refLevel=0, fileDir='C:\SignalVu-PC Files', 
    fileName='if_stream_test', durationMsec=100):
    rsa.CONFIG_SetCenterFreq(c_double(cf))
    rsa.CONFIG_SetReferenceLevel(c_double(refLevel))
    rsa.IFSTREAM_SetDiskFilePath(c_char_p(fileDir.encode()))
    rsa.IFSTREAM_SetDiskFilenameBase(c_char_p(fileName.encode()))
    rsa.IFSTREAM_SetDiskFilenameSuffix(c_int(-2))
    rsa.IFSTREAM_SetDiskFileLength(c_long(durationMsec))
    rsa.IFSTREAM_SetDiskFileMode(c_int(1))
    rsa.IFSTREAM_SetDiskFileCount(c_int(1))


def if_stream_example():
    search_connect()
    durationMsec = 100
    waitTime = durationMsec/10/1000
    config_if_stream(fileDir='C:\\SignalVu-PC Files', 
        fileName='if_stream_test', durationMsec=durationMsec)
    writing = c_bool(True)

    rsa.DEVICE_Run()
    rsa.IFSTREAM_SetEnable(c_bool(True))
    while writing.value == True:
        time.sleep(waitTime)
        rsa.IFSTREAM_GetActiveStatus(byref(writing))
    print('Streaming finished.')
    rsa.DEVICE_Stop()
    rsa.DEVICE_Disconnect()


"""################IQ STREAMING EXAMPLE################"""
def config_iq_stream(cf=1e9, refLevel=0, bw=10e6, 
    fileDir='C:\\SignalVu-PC Files', fileName='iq_stream_test', dest=2, 
    suffixCtl=-2, durationMsec=100):
    filenameBase = fileDir + '\\' + fileName
    bwActual = c_double(0)
    sampleRate = c_double(0)
    rsa.CONFIG_SetCenterFreq(c_double(cf))
    rsa.CONFIG_SetReferenceLevel(c_double(refLevel))
    
    rsa.IQSTREAM_SetAcqBandwidth(c_double(bw))
    rsa.IQSTREAM_SetOutputConfiguration(c_int(dest), c_int(2))
    rsa.IQSTREAM_SetDiskFilenameBase(c_char_p(filenameBase.encode()))
    rsa.IQSTREAM_SetDiskFilenameSuffix(c_int(suffixCtl))
    rsa.IQSTREAM_SetDiskFileLength(c_int(durationMsec))
    rsa.IQSTREAM_GetAcqParameters(byref(bwActual), byref(sampleRate))


def iqstream_status_parser(iqStreamInfo):
    # This function parses the IQ streaming status variable
    status = iqStreamInfo.acqStatus
    if status == 0:
        print('\nNo error.\n')
    if (bool(status & 0x10000)):    #mask bit 16
        print('\nInput overrange.\n')
    if (bool(status & 0x40000)):    #mask bit 18
        print('\nInput buffer > 75{} full.\n'.format('%'))
    if (bool(status & 0x80000)):    #mask bit 19
        print('\nInput buffer overflow. IQStream processing too slow, ',
            'data loss has occurred.\n')
    if (bool(status & 0x100000)):   #mask bit 20
        print('\nOutput buffer > 75{} full.\n'.format('%'))
    if (bool(status & 0x200000)):   #mask bit 21
        print('Output buffer overflow. File writing too slow, ', 
            'data loss has occurred.\n')


def iq_stream_example():
    search_connect()

    cf = 2.4453e9
    refLevel = 0

    bw = 5e6
    dest = 2
    suffixCtl = -2
    durationMsec = 100
    waitTime = durationMsec/1e3/10
    fileDir = 'C:\\SignalVu-PC Files'
    fileName = 'iq_stream_test'
    iqStreamInfo = IQSTREAM_File_Info()

    complete = c_bool(False)
    writing = c_bool(False)

    config_iq_stream()

    rsa.DEVICE_Run()    
    rsa.IQSTREAM_Start()
    while complete.value == False:
        time.sleep(waitTime)
        rsa.IQSTREAM_GetDiskFileWriteStatus(byref(complete), byref(writing))
    rsa.IQSTREAM_Stop()
    print('Streaming finished.')
    rsa.IQSTREAM_GetFileInfo(byref(iqStreamInfo))
    iqstream_status_parser(iqStreamInfo)
    rsa.DEVICE_Stop()
    rsa.DEVICE_Disconnect()


"""################MISC################"""
def config_trigger(trigMode=1, trigLevel=-10, trigSource=1):
    rsa.TRIG_SetTriggerMode(c_int(trigMode))
    rsa.TRIG_SetIFPowerTriggerLevel(c_double(trigLevel))
    rsa.TRIG_SetTriggerSource(c_int(trigSource))
    rsa.TRIG_SetTriggerPositionPercent(c_double(10))


def peak_power_detector(freq, trace):
    peakPower = np.amax(trace)
    peakFreq = freq[np.argmax(trace)]

    return peakPower, peakFreq  


def main():
    # uncomment the example you'd like to run
    spectrum_example()
    # block_iq_example()
    # dpx_example()
    # if_stream_example()
    # iq_stream_example()


if __name__ == '__main__':
    main()

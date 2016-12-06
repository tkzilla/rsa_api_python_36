"""
Tektronix RSA API: Block IQ Visualizer
Author: Morgan Allison
Date Created: 5/15
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
from scipy import signal
from scipy import stats
import matplotlib.pyplot as plt
import time, os

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


def running_mean(x, N):
    y = np.cumsum(x)
    z = np.arange(1,N+1)
    return y/z


def freq_correction(IQ, t, sRate):
    t1 = time.perf_counter()
    
    power = 2
    IQ_power = IQ**power
    fft = np.fft.fft(IQ_power/len(IQ))
    freq = np.fft.fftfreq(len(IQ), d=1/sRate)

    IQ_power_filtered = ref_filter(IQ_power, 1)
    fft_filtered = np.fft.fft(IQ_power_filtered/len(IQ))
    freq_filtered= np.fft.fftfreq(len(IQ), d=1/sRate)

    peakPowerFreq = freq[np.argmax(abs(fft))]/power
    
    IQ_fc = IQ * np.exp(1j*2*np.pi*-peakPowerFreq*t)

    # fft_fc = np.fft.fft(IQ_fc**power/len(IQ_fc))
    # freq_fc = np.fft.fftfreq(len(IQ_fc), d=1/sRate)
    # peakPowerFreq_fc = freq_fc[np.argmax(abs(fft_fc))]/power
    
    t2 = time.perf_counter()
    
    print('Carrier offset: %f Hz' % peakPowerFreq)
    print('Elapsed time: {}'.format(t2-t1))
    
    # plt.figure(1,figsize=(20,10))
    # plt.subplot(221)
    # plt.plot(IQ_power)
    # plt.title('IQ_power')
    # plt.xlim([0, 1e5])
    # plt.subplot(222)
    # plt.plot(freq, abs(fft))
    # plt.title('FFT of IQ_power')
    # plt.subplot(223)
    # plt.plot(IQ_power_filtered)
    # plt.title('IQ_power_filtered')
    # plt.xlim([0, 1e5])
    # plt.subplot(224)
    # plt.plot(freq, abs(fft_filtered))
    # plt.title('FFT of IQ_power_filtered')
    # plt.show()
    
    return peakPowerFreq


def phase_correction(IQ, time):
    phaseError = np.unwrap(np.arctan(np.imag(IQ*np.exp(1j*np.pi))/np.real(IQ*np.exp(1j*np.pi))))
    # phaseFilter = signal.firwin(64, 1e-9)
    # phaseError = signal.lfilter(phaseFilter, 1.0, phaseError)

    slope, intercept, r, p, sigma = stats.linregress(time, np.rad2deg(phaseError))
    fineFreqOffset = slope/time[-1]
    print('Secondary frequency offset: {}'.format(slope))

    # angles = np.unwrap(np.angle(IQ_fc))
    # phaseError = running_mean(angles, len(angles))
    # phaseErrorMean = np.mean(phaseError)
    
    print('Average Correction Phase: {:.4} radians ({:.2f} degrees)'.format(
        np.mean(phaseError), np.rad2deg(np.mean(phaseError))))
    return phaseError

def clock_recovery(IQ, sRate, time):
    IQ = np.real(IQ)
    
    power = 2
    fft = np.fft.fft(IQ**power)/len(IQ)
    freq = np.fft.fftfreq(len(IQ), d = 1/sRate)

    fundamental = freq[np.argmax(fft)]
    cRate = abs(freq[np.argmax(abs(fft[2:-1]))]/power)

    return cRate


def zero_crossing_detector(data):
    # zeroCrossings = data[np.where(np.diff(np.sign(data)))]
    zeroCrossings = []
    saved = data[0]
    for i in range(len(data)):
        # if data[i] <= 0:
        #     if saved > 0:
        #         zeroCrossings.append(i)
        # else:
        #     if saved <= 0:
        #         zeroCrossings.append(i)
        # saved = data[i]
        if data[i] > 0 and saved <= 0:
            zeroCrossings.append(i-1)
        saved = data[i]
    return np.array(zeroCrossings)


def clock_estimator(zeroCrossings):
    periods = np.diff(zeroCrossings)
    print('Minimum period: {}'.format(np.amin(periods)))

    return int(np.around(np.amin(periods)/2))


def ref_filter(IQ, nyq):
    h_filter = signal.firwin(64, 1e-9)
    IQ_filt = signal.lfilter(h_filter, 1.0, IQ)

    return IQ_filt


def eye_diagram(data, sRate, time):
    # Clock recovery and eye diagram
    cRate = clock_recovery(data, sRate, time)
    print('Clock Rate: {}'.format(cRate))
    zeroCrossings = zero_crossing_detector(data)
    saPerSym = clock_estimator(zeroCrossings)
    # saPerSym = int(sRate/cRate/2)
    decOffset = int(saPerSym/2)

    start = zeroCrossings[1]+decOffset
    # np.delete(zeroCrossings, 0)
    # zeroCrossings += decOffset
    start -= int(np.median(zeroCrossings%saPerSym))
    # zeroCrossings += decOffset
    data = data[start:]
    zeroCrossings -= start
    numSymbols = int(len(data)/saPerSym)

    decPoints = np.arange(decOffset, (start+numSymbols*saPerSym), saPerSym)

    # print('Start Index: {}'.format(start))
    print('Decision offset: {}'.format(decOffset))
    print('Samples per symbol: {}'.format(saPerSym))
    print('Number of symbols: {}'.format(numSymbols))

    upperThresh = np.amax(data) - 0.6*np.amax(data)
    lowerThresh = np.amin(data) - 0.6*np.amin(data)

    pts = np.zeros(numSymbols)
    symbols = np.zeros(numSymbols)

    """This section is all debugging plots"""
    """Plots out beginning of data with zcrossings and thresholds"""
    plotSymbols = 20
    plotPoints = int(plotSymbols*saPerSym)
    plt.figure(1, figsize=(20,10))
    plt.step(np.arange(plotPoints), data[:plotPoints])
    for i in range(plotSymbols):
        plt.axvline(zeroCrossings[i], color='c')
        plt.axvline((decPoints[i]), color='g')
    plt.axhline(upperThresh, color='r')
    plt.axhline(lowerThresh, color='r')
    plt.axhline(0, color='y')
    plt.xlim([0,saPerSym*i])
    # plt.show()

    """Plots out zero crossings%samples per symbol"""
    # plt.figure()
    # plt.step(np.arange(len(zeroCrossings)),zeroCrossings%saPerSym)
    # plt.title('Zero crossings modulo samples per symbol')
    # plt.show()

    # # Plots out the voltage at each zero crossing to look for outliers
    # plt.step(np.arange(len(zeroCrossings)), data[zeroCrossings])
    # plt.show()

    """Plots out the eye diagram"""
    plt.figure(2, figsize=(20,10))
    axEye = plt.subplot(111)
    axEye.set_title('Eye Diagram')
    beg = 0 
    end = 0
    for i in range(50):
        end = beg + saPerSym
        axEye.step(time[0:saPerSym],data[beg:end], color='b')
        plt.axvline(time[decPoints[i]%(saPerSym)], color='y')
        beg = end
    # plt.axvline(time[decOffset], color='r')
    axEye.set_ylabel('Amplitude')
    axEye.set_xlabel('Time (s)')
    # plt.show()
    return decPoints


def symbol_detector(IQ, sRate, cRate, time):
    return 0


    # decFactor = int(sRate/cRate/3)
    # print('Decimation factor: {}'.format(decFactor))
    # decIQ = signal.decimate(IQ, decFactor, ftype='fir')
    # sampleDelay = 0
    # decIQ = decIQ[sampleDelay:]

    # plt.figure(figsize=(20,10))
    # ax1 = plt.subplot(211)
    # ax1.plot(IQ[:1000])
    # ax2 = plt.subplot(212)
    # ax2.plot(decIQ[:int(1000/decFactor)])
    # plt.show()


def main():
    """#################SEARCH/CONNECT#################"""
    search_connect()

    for i in range(3):
        """#################INITIALIZE VARIABLES#################"""
        # main SA parameters
        refLevel = c_double(0)
        cf = c_double(1e9)
        iqBandwidth = c_double(20e6)
        acqTime = 5e-3
        recordLength = c_int(int(iqBandwidth.value*1.4*acqTime))

        actLength = c_int(0)
        iqSampleRate = c_double(0)
        timeoutMsec = c_int(1000)
        ready = c_bool(False)

        #data transfer variables
        iqArray =  c_float*recordLength.value
        iData = iqArray()
        qData = iqArray()

        """#################CONFIGURE INSTRUMENT#################"""
        rsa.CONFIG_Preset()
        rsa.CONFIG_SetReferenceLevel(refLevel)
        rsa.CONFIG_SetCenterFreq(cf)
        rsa.IQBLK_SetIQBandwidth(iqBandwidth)
        rsa.IQBLK_SetIQRecordLength(recordLength)

        """#################ACQUIRE/PROCESS DATA#################"""
        
        rsa.DEVICE_Run()

        #get relevant settings values
        #this requires that the RSA306 be running
        rsa.CONFIG_GetCenterFreq(byref(cf))
        rsa.CONFIG_GetReferenceLevel(byref(refLevel))
        rsa.IQBLK_GetIQBandwidth(byref(iqBandwidth))
        rsa.IQBLK_GetIQRecordLength(byref(recordLength))
        rsa.IQBLK_GetIQSampleRate(byref(iqSampleRate))

        print('Reference level: ' + str(refLevel.value) + ' dBm')
        print('Center frequency: ' + str(cf.value/1e6) + ' MHz')
        print('IQ Bandwidth: ' + str(iqBandwidth.value/1e6) + ' MHz')
        print('Record length: ' + str(recordLength.value))
        print('IQ Sample rate: ' + str(iqSampleRate.value/1e6) + ' MS/sec')

        rsa.IQBLK_AcquireIQData()
        #check for data ready
        while ready.value == False:
            ret = rsa.IQBLK_WaitForIQDataReady(timeoutMsec, byref(ready))

        #query I and Q data
        ret = rsa.IQBLK_GetIQDataDeinterleaved(byref(iData), byref(qData), byref(actLength), recordLength)
        print('Got IQ data')
        rsa.DEVICE_Stop()
        
        #convert ctypes array to numpy array for ease of use
        I = np.ctypeslib.as_array(iData)
        Q = np.ctypeslib.as_array(qData)
        IQ = I + 1j*Q

        """################OPTIONAL LOAD FROM FILE################"""
        # IQ = np.load('C:\\Users\\mallison\\Documents\\GitHub\\RSA_API-Python-3.5\\IQ_data.npy')
        # recordLength = c_int(280000)
        # iqSampleRate = c_double(28e6)

        time = np.linspace(0,recordLength.value/iqSampleRate.value,recordLength.value)

        freqOffset = freq_correction(IQ, time, iqSampleRate.value)
        IQ_fc = IQ * np.exp(1j*2*np.pi*-freqOffset*time)
        # IQ_filt = ref_filter(IQ_fc, iqSampleRate.value/2)

        # This is the phase detector
        phaseError = phase_correction(IQ_fc, time)

        IQ_pc = IQ_fc * np.exp(1j*-phaseError)


        """#################PLOTS#################"""
        symIndices = eye_diagram(np.real(IQ_pc), iqSampleRate.value, time)

        # plt.scatter(np.real(IQ_pc)[symIndices])
        # plt.show()

        plt.figure(2,figsize=(20,10))
        ax1 = plt.subplot2grid((3,2),(0,0), colspan=2)
        ax1.set_title('Phase angles of IQ points')
        ax1.plot(time, np.rad2deg(phaseError))
        # ax1.plot(time, (slope*time + intercept), color='red')
        ax1.set_ylabel('Phase Angle (deg)')
        ax1.axhline(np.rad2deg(np.mean(phaseError)), color='green')
        ax2 = plt.subplot2grid((3,2),(1,0), colspan=2)
        ax2.set_title('IQ_pc vs Time')
        ax2.plot(time, np.real(IQ_pc), 'b')
        ax2.plot(time, np.imag(IQ_pc), 'g')
        ax2.set_ylabel('IQ (V)')
        ax2.set_xlabel('Time (ms)')
        ax3 = plt.subplot2grid((3,2),(2,0))
        ax3.set_title('I vs Q frequency corrected')
        ax3.plot(np.real(IQ_fc)[:1000], np.imag(IQ_fc)[:1000])
        ax3.set_ylabel('Imag')
        ax3.set_xlabel('Real')
        ax3.set_xlim([-1, 1])
        ax3.set_ylim([-1, 1])
        ax4 = plt.subplot2grid((3,2),(2,1))
        ax4.set_title('I vs Q phase corrected')
        ax4.scatter(np.real(IQ_pc[symIndices]), np.imag(IQ_pc[symIndices]))
        ax4.set_ylabel('Imag')
        ax4.set_xlabel('Real')
        ax4.set_xlim([-1, 1])
        ax4.set_ylim([-1, 1])
        plt.show()


        # cRate = clock_recovery(np.real(IQ_pc), iqSampleRate.value, time)
        # symbol_detector(np.real(IQ_pc), iqSampleRate.value, cRate, time)

    print('Disconnecting.')
    rsa.DEVICE_Disconnect()
    

if __name__ == "__main__":
    main()

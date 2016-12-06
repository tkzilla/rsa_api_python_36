import numpy as np
import matplotlib.pyplot as plt

def pll(inSig, t, loopBW, sRate):
	inSigFft = np.fft.fft(inSig)
	inSigFreq = np.fft.fftfreq(len(inSig), d=1/sRate)
	fund = inSigFreq[np.argmax(inSigFft)]
	print('Fundamental frequency: {} Hz'.format(fund))

	refSig = np.cos(fund*t)

	plt.figure(1, figsize=(20,10))
	plt.subplot(211)
	plt.plot(t, inSig, t, refSig)
	plt.subplot(212)
	plt.plot(inSigFreq, abs(inSigFft))
	plt.show()

	phase = 0

	return phase

def main():
	sRate = 1000
	# this is phase, no need to convert to freq using 2pi
	t = np.linspace(0, 2*np.pi*10, 10000)
	inFreq = 10
	inSig = np.cos(inFreq*t)

	phase = pll(inSig, t, 5, sRate)

if __name__ == '__main__':
	main()
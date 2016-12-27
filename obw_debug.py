from pickle import load
import numpy as np
import matplotlib.pyplot as plt
from classifier import *

with open('C:\\users\\mallison\\Documents\\GitHub\\RSA_API-Python-3.5\\error_traces.pickle', 'rb') as f:
	errors = load(f)

dB = 20
eps = dB*.25

freq = np.arange(len(errors[0]))
for i in range(len(errors)):
	f1, f2 = calc_obw_db(errors[i], freq, dB)
	# f1, f2 = calc_obw_pcnt(errors[i], freq, 801, 801/2000, 801)

	plt.figure(1, figsize=(20,10))
	plt.subplot(211)
	plt.axvline(f1)
	plt.axvline(f2)
	plt.axvline(np.argmax(errors[i]))
	print(np.amax(errors[i]))
	print(errors[i][f1])
	print(errors[i][f2])
	plt.plot(errors[i])
	plt.subplot(212)
	plt.step(np.arange(len(errors[i])-1),np.diff(errors[i]))
	plt.show()
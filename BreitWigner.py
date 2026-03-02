import numpy as np
from scipy.optimize import curve_fit


def gaussian(E, A, mu, sigma):
    return A * np.exp(-(E - mu)**2 / (2 * sigma**2))

def breit_wigner(E, A, E0, Gamma):
    return A * (Gamma/2)**2 / ((E - E0)**2 + (Gamma/2)**2)



popt, pcov = curve_fit(breit_wigner, E_data, counts, p0=[1000, 7.68, 0.05])
#!/usr/bin/env python3

import numpy as np

# ==========================================================
# USER INPUTS
# ==========================================================

peak_area = 88000            # fitted peak area (counts)
monitor_counts = 6016  # total beam integrator counts


scale_factor = 1           # BCI scale factor from experiment

# ==========================================================
# EXPERIMENTAL PARAMETERS (from config file)
# ==========================================================

target_thickness = 9.25e-5      # g/cm^2
molar_mass = 9.012182           # g/mol
solid_angle = 0.00461641607338361  # sr

beam_charge_state = 3           # 6Li3+
sampling_rate = 100             # Hz

NA = 6.02214076e23              # Avogadro number
barn2cm2 = 1e-24                   # 1 barn in cm^2

# ==========================================================
# CALCULATIONS
# ==========================================================

# Number of counts in monitor
N_beam = monitor_counts * scale_factor

# Target nuclei per cm^2
rho = (target_thickness / molar_mass) * NA

# Differential cross section in cm^2/sr
dsigma = peak_area / (N_beam * (rho * barn2cm2) * solid_angle)


# ==========================================================
# OUTPUT
# ==========================================================

print("\n========= QUICK XSEC CALC =========")
print(f"Peak area              : {peak_area:12.1f} counts")
print(f"Monitor counts         : {monitor_counts:12,d}")
print(f"Scaled monitor counts  : {N_beam:12.3e}")
print(f"Target density         : {rho:12.3e} nuclei/cm^2")
print(f"Solid angle            : {solid_angle*1000:12.3f} msr")
print("------------------------------------")
print(f"dσ/dΩ = {dsigma:8.3f} mb/sr")
print("====================================\n")
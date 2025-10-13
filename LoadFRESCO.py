import numpy as np
import matplotlib.pyplot as plt

filepath = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/6Lid/9Be6Lid_fresco/7688keV/fort.16"

with open(filepath, "r") as f:
    lines = f.readlines()

# Find all header lines
header_indices = [i for i, line in enumerate(lines) if line.strip().startswith("#  Theta")]

if len(header_indices) < 2:
    raise ValueError("Could not find a second Theta header in the file.")

start_idx = header_indices[1]

# Load only first two columns, skip headers, ignore lines starting with # or END
data = np.loadtxt(
    filepath,
    skiprows=start_idx+1,
    usecols=(0,1),
    comments=('END','#')
)

theta = data[:, 0]
sigma = data[:, 1]

# Terminate at Theta = 70 deg
mask = theta <= 70
theta = theta[mask]
sigma = sigma[mask]

# Plot
plt.scatter(theta, sigma)
plt.xlabel("Scattering angle (deg)")
plt.ylabel("dσ/dΩ (mb/sr)")
plt.title("Excited State Angular Distribution (θ ≤ 70°)")
plt.show()


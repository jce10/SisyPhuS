from pathlib import Path
import numpy as np
import polars as pl
import matplotlib.pyplot as plt

# -----------------------------
# User inputs
# -----------------------------
parquet_file = Path("/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/12C_dp_H_included/20deg_5.8kG_200s_cut.parquet")
output_csv = Path("energy_calibrated_spectrum.csv")

column_name = "Xshap"

# Histogram settings in mm
x_min = -300.0
x_max = 300.0
n_bins = 600

# Linear calibration: E(mm) = b*x + c
b = -9.055
c = 8154.34

# Quadratic calibration: E(mm) = a*x^2 + b*x + c
# a = -0.038
# b = -0.955
# c = 7775.52

# Optional: remove obvious bad values
invalid_cut = -1e6

# -----------------------------
# Read parquet and extract column
# -----------------------------
df = pl.read_parquet(parquet_file)

if column_name not in df.columns:
    raise ValueError(f"Column '{column_name}' not found in file.")

xvals = (
    df
    .filter(pl.col(column_name).is_not_null())
    .filter(pl.col(column_name) > invalid_cut)
    .get_column(column_name)
    .to_numpy()
)

if len(xvals) == 0:
    raise ValueError("No valid data found in the selected column.")

# -----------------------------
# Build histogram in mm
# -----------------------------
counts, bin_edges_mm = np.histogram(xvals, bins=n_bins, range=(x_min, x_max))
bin_centers_mm = 0.5 * (bin_edges_mm[:-1] + bin_edges_mm[1:])

# -----------------------------
# Apply calibration to bin centers: linear or quadratic as needed
# -----------------------------

energy_keV_lin = b * bin_centers_mm + c
# energy_keV_quad = a * bin_centers_mm**2 + b * bin_centers_mm + c

# -----------------------------
# Save to CSV
# -----------------------------
out_df = pl.DataFrame({
    "bin_center_mm": bin_centers_mm,
    "energy_keV_lin": energy_keV_lin,
    # "energy_keV_quad": energy_keV_quad,
    "counts": counts,
})

out_df.write_csv(output_csv)

print(f"Min Xshap: {xvals.min()}")
print(f"Max Xshap: {xvals.max()}")
print(f"Number of events: {len(xvals)}")

print(f"Wrote spectrum to: {output_csv.resolve()}")
print(out_df.head())

plt.step(energy_keV_lin, counts, where="mid")
plt.xlabel("Energy (keV)")
plt.ylabel("Counts")
plt.show()
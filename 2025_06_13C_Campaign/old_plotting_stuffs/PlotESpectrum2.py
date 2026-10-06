from pathlib import Path
import numpy as np
import polars as pl

# -----------------------------
# User inputs
# -----------------------------
parquet_file = Path("input.parquet")
output_csv = Path("energy_spectrum.csv")

column_name = "Xshap"

# Calibration: E(mm) = a*x^2 + b*x + c
a = 0.0
b = 1.0
c = 0.0

# Energy histogram settings
e_min = 0.0
e_max = 10000.0
n_bins = 2000

invalid_cut = -1e6

# -----------------------------
# Read data
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
# Convert each event to energy
# -----------------------------
energies = a * xvals**2 + b * xvals + c

# -----------------------------
# Histogram directly in energy
# -----------------------------
counts, bin_edges = np.histogram(energies, bins=n_bins, range=(e_min, e_max))
bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])

# -----------------------------
# Save
# -----------------------------
out_df = pl.DataFrame({
    "energy_keV": bin_centers,
    "counts": counts,
})

out_df.write_csv(output_csv)

print(f"Wrote calibrated spectrum to: {output_csv.resolve()}")
print(out_df.head())
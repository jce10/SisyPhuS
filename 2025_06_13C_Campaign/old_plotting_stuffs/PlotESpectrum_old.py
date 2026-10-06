from pathlib import Path
import numpy as np
import polars as pl
import matplotlib.pyplot as plt

# -----------------------------
# User inputs
# -----------------------------
#Andrew's Energy calibration for 25deg, 7.2kG
# parquet_file = Path("/home/jce18b/Esparza_SPS/2025_07_29Si_dp/built/25deg_7.2kG_cut_total.parquet")
# parquet_file = Path("/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/9Be6Lid/10deg_14kG_total_cut.parquet")
parquet_file = Path("/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/9Be6Lid/15deg_13.85kG_total_cut.parquet")
# parquet_file = Path("/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/12Cdp/LowField/20deg_5.8kG_200s_cut.parquet")
output_csv = Path("energy_calibrated_spectrum.csv")

column_name = "Xshap"  # Column to extract from parquet file

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# Histogram settings in mm

# default full spectrum range
# x_min = -300.0
# x_max = 300.0
# n_bins = 600

# 9Be(6Li,d)13C range
# x_min = -300.0
# x_max = 300.0
# n_bins = 600

# 15deg 9Be(6Li,d)13C range
x_min = -300.0
x_max = 300.0
n_bins = 600

# # 20deg 12C(d,p)13C range
# x_min = -320.0
# x_max = 250.0
# n_bins = 570

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# Linear calibration: E(mm) = b*x + c

# # 20deg (d,p) calibration
# b = -0.00852
# c = 8.120

# Quadratic calibration: E(mm) = a*x^2 + b*x + c

# 15deg (6Li,d) calibration
a = -9.928367235e-06
b = -0.02230239502
c = 9.333177567

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

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

# # plot energy calibrated spectrum
# plt.step(energy_keV_lin, counts, where="mid")
# # plt.title(r"$^{29}\mathrm{Si(d,p)}^{30}\mathrm{Si}, 25^\circ, 7.2kG$")
# # plt.title(r"$^{9}\mathrm{Be(^{6}Li,d)}^{13}\mathrm{C}, 10^\circ, 14kG$")
# # plt.title(r"$^{12}\mathrm{C(d,p)}^{13}\mathrm{C}, 20^\circ, 5.8kG$")
# plt.xlabel(r"$^{13}\mathrm{C}$ Excitation Energy (MeV)",fontsize=14)
# plt.ylabel("Counts",fontsize=14)
# plt.xlim(energy_keV_lin.min(), energy_keV_lin.max())
# plt.ylim(0, counts.max() * 1.1)
# plt.show()

fig, ax = plt.subplots()

ax.step(energy_keV_lin, counts, where="mid")

# ax.set_title(r"$^{12}\mathrm{C(d,p)}^{13}\mathrm{C}$")
ax.set_xlabel(r"$^{13}\mathrm{C}$ Excitation Energy (MeV)", fontsize=17, loc="right")
ax.set_ylabel("Counts", fontsize=17)

ax.set_xlim(energy_keV_lin.min(), energy_keV_lin.max())
ax.set_ylim(0, counts.max() * 1.1)
ax.minorticks_on()

ax.tick_params(
    axis="both",
    which="major",
    direction="in",
    top=True,
    right=True,
    length=7
)

ax.tick_params(
    axis="both",
    which="minor",
    direction="in",
    top=True,
    right=True,
    length=4
)

# SPS experimental parameters
sps_text = (
    r"$E_d = 16$ MeV" "\n"
    r"$\theta_{\mathrm{SE-SPS}} = 20^\circ$" "\n"
    r"$B_{\mathrm{SE-SPS}} = 5.8$ kG"
)

ax.text(
    0.97, 0.95,
    sps_text,
    transform=ax.transAxes,
    ha="right",
    va="top",
    fontsize=15,
    bbox=dict(
        boxstyle="round,pad=0.4",
        facecolor="white",
        edgecolor="black",
        alpha=0.9,
    ),
)

plt.show()
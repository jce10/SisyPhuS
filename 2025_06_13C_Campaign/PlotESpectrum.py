from pathlib import Path
import numpy as np
import polars as pl
import matplotlib.pyplot as plt

# -----------------------------
# User inputs
# -----------------------------
#Andrew's Energy calibration for 25deg, 7.2kG
# parquet_file = Path("/home/jce18b/Esparza_SPS/2025_07_29Si_dp/built/25deg_7.2kG_cut_total.parquet")

# (6Li,d)
# parquet_file = Path("/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/9Be6Lid/10deg_14kG_total_cut.parquet")
parquet_file = Path("/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/9Be6Lid/15deg_13.85kG_total_cut.parquet")

# (d,p)
# parquet_file = Path("/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/12Cdp/LowField/15deg_5.6kG_total_cut.parquet")
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
x_min = -90.0
x_max = 140.0
n_bins = 230



# # 15deg 12C(d,p)13C range
# x_min = -300.0
# x_max = 300.0
# n_bins = 600

# # 20deg 12C(d,p)13C range
# x_min = -320.0
# x_max = 250.0
# n_bins = 570

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# Choose the calibration to apply: "linear" or "quadratic"

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# Linear calibration: E(x) = b*x + c
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# 20deg (d,p) calibration
linear_b = -0.008594831532
linear_c = 8.251265961
# calibration_type = "linear"


# # 20deg (d,p) calibration
# linear_b = -0.00852
# linear_c = 8.120
# calibration_type = "linear"

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# Quadratic calibration: E(x) = a*x^2 + b*x + c
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #


quad_a = -9.928367235e-06
quad_b = -0.02230239502
quad_c = 9.333177567
calibration_type = "quadratic"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# Optional: remove obvious bad values
invalid_cut = -1e6


def calibrate_energy(x, calibration):
    """Convert focal-plane position in mm to excitation energy in MeV."""
    calibration = calibration.lower()

    if calibration == "linear":
        return linear_b * x + linear_c

    if calibration == "quadratic":
        return quad_a * x**2 + quad_b * x + quad_c

    raise ValueError(
        f"Unknown calibration type '{calibration}'. "
        "Choose 'linear' or 'quadratic'."
    )

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
# Apply the selected calibration to the bin centers
# -----------------------------

energy_mev = calibrate_energy(bin_centers_mm, calibration_type)

# -----------------------------
# Save to CSV
# -----------------------------
out_df = pl.DataFrame({
    "bin_center_mm": bin_centers_mm,
    "energy_mev": energy_mev,
    "counts": counts,
})

out_df.write_csv(output_csv)

print(f"Min Xshap: {xvals.min()}")
print(f"Max Xshap: {xvals.max()}")
print(f"Number of events: {len(xvals)}")

print(f"Wrote spectrum to: {output_csv.resolve()}")
print(out_df.head())

fig, ax = plt.subplots()

ax.step(energy_mev, counts, where="mid")

# ax.set_title(r"$^{12}\mathrm{C(d,p)}^{13}\mathrm{C}$")
ax.set_xlabel(r"$^{13}\mathrm{C}$ Excitation Energy (MeV)", fontsize=17, loc="right")
ax.set_ylabel("Counts", fontsize=17)

ax.set_xlim(energy_mev.min(), energy_mev.max())
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
    r"$E_{^{6}\mathrm{Li}} = 32$ MeV" "\n"
    r"$\theta_{\mathrm{SE-SPS}} = 15^\circ$" "\n"
    r"$B_{\mathrm{SE-SPS}} = 13.852$ kG"

    # r"$E_{\mathrm{d}} = 16$ MeV" "\n"
    # r"$\theta_{\mathrm{SE-SPS}} = 15^\circ$" "\n"
    # r"$B_{\mathrm{SE-SPS}} = 5.625$ kG"
)

ax.text(
    # 0.97, 0.95,
    0.25, 0.95,
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

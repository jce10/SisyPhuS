"""Interactively compare energy-calibrated 13C spectra from two reactions.

Each event is converted from focal-plane position to excitation energy before
histogramming.  Both spectra are then placed on the same fixed energy-bin grid.

The GUI permits small residual ENERGY OFFSETS only.  It deliberately does not
stretch either x axis, because an x-axis stretch would modify the calibration.
Vertical comparison modes are explicitly labeled as raw counts or normalized
shape comparisons.
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.widgets import Button, RadioButtons, Slider
import numpy as np
import polars as pl


@dataclass(frozen=True)
class SpectrumConfig:
    """Input, calibration, and display settings for one spectrum."""

    name: str
    parquet_file: Path
    column_name: str
    calibration_type: str
    linear_b: float
    linear_c: float
    quad_a: float
    quad_b: float
    quad_c: float
    anchor_centroid_mev: float | None
    color: str
    legend_label: str


# =============================================================================
# User inputs
# =============================================================================

# 9Be(6Li,d)13C at 15 degrees
LI6D = SpectrumConfig(
    name="6Li,d",
    parquet_file=Path(
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/9Be6Lid/15deg_13.85kG_total_cut.parquet"
    ),
    column_name="Xshap",
    calibration_type="quadratic",  # "linear" or "quadratic"
    linear_b=0.0,
    linear_c=0,
    quad_a=-9.928367235e-06,
    quad_b=-0.02230239502,
    quad_c=9.333177567,
    # Set this to the fitted 6.860-MeV centroid only if a residual
    # zero-point correction is needed. Leave as None otherwise.
    anchor_centroid_mev=None,
    color="#0072B2",
    legend_label=(
        r"$^{9}\mathrm{Be}(^{6}\mathrm{Li},d)^{13}\mathrm{C}$"
        "\n"
        r"$B=13.852$ kG, $E_{^{6}\mathrm{Li}}=32$ MeV"
    ),
)

# 12C(d,p)13C at 15 degrees
DP = SpectrumConfig(
    name="d,p",
    parquet_file=Path(
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/12Cdp/LowField/15deg_5.6kG_total_cut.parquet"
    ),
    column_name="Xshap",
    calibration_type="linear",  # "linear" or "quadratic"
    # Replace these with the calibration coefficients for this specific run.
    # The defaults below are the linear coefficients from PlotESpectrum.py.
    linear_b=-0.008594831532,
    linear_c=8.251265961,
    quad_a=0.0,
    quad_b=-0.00852,
    quad_c=8.120,
    # Set this to the fitted 6.860-MeV centroid only if a residual
    # zero-point correction is needed. Leave as None otherwise.
    anchor_centroid_mev=None,
    color="#D55E00",
    legend_label=(
        r"$^{12}\mathrm{C}(d,p)^{13}\mathrm{C}$"
        "\n"
        r"$B=5.6$ kG, $E_d=16$ MeV"
    ),
)

SPECTRA = (LI6D, DP)

# Full displayed range. The complete (d,p) spectrum is shown across this range.
energy_min_mev = 6.0
energy_max_mev = 11.3

# Both reactions use this exact common energy-bin width. Five-keV bins are
# sufficiently fine compared with an approximately 30-keV experimental FWHM.
energy_bin_width_kev = 5.0

# Only this interval of the energy-calibrated (6Li,d) spectrum is drawn.
# Changing this does not rebin, smooth, or otherwise modify either spectrum.
li6_plot_range_mev = (6.0, 11.3)

# Optional residual zero-point alignment using the known 6.860-MeV state.
# Enter the FITTED calibrated centroid for each reaction in its SpectrumConfig
# above. When anchor_centroid_mev is None, no correction is applied.
anchor_reference_mev = 6.860

# Area and peak normalization are calculated only inside this window.
normalization_window_mev = (6.8, 11.0)
initial_normalization = "Raw counts"

# Residual energy-shift sliders. These are diagnostic alignment corrections;
# a large required shift indicates that the calibration should be revisited.
shift_min_mev = -0.100
shift_max_mev = 0.100
shift_step_mev = 0.001

invalid_cut = -1e6
title = r"$^{13}\mathrm{C}$ Spectra, $\theta_{\mathrm{SE-SPS}}=15^\circ$"
output_stem = Path("13C_spectra_overlay_15deg")


# =============================================================================
# Calibration and histogram helpers
# =============================================================================

def calibrate_energy(x_mm: np.ndarray, config: SpectrumConfig) -> np.ndarray:
    """Convert focal-plane position in mm to excitation energy in MeV."""
    calibration = config.calibration_type.lower()

    if calibration == "linear":
        return config.linear_b * x_mm + config.linear_c

    if calibration == "quadratic":
        return (
            config.quad_a * x_mm**2
            + config.quad_b * x_mm
            + config.quad_c
        )

    raise ValueError(
        f"Unknown calibration type '{config.calibration_type}' for "
        f"{config.name}. Choose 'linear' or 'quadratic'."
    )


def load_calibrated_energies(config: SpectrumConfig) -> np.ndarray:
    """Read one Parquet column and calibrate every valid event."""
    if not config.parquet_file.exists():
        raise FileNotFoundError(
            f"Input file for {config.name} was not found:\n"
            f"  {config.parquet_file}"
        )

    frame = pl.read_parquet(config.parquet_file)
    if config.column_name not in frame.columns:
        raise ValueError(
            f"Column '{config.column_name}' was not found in "
            f"{config.parquet_file}."
        )

    x_mm = (
        frame
        .filter(pl.col(config.column_name).is_not_null())
        .filter(pl.col(config.column_name) > invalid_cut)
        .get_column(config.column_name)
        .to_numpy()
    )
    x_mm = x_mm[np.isfinite(x_mm)]

    if x_mm.size == 0:
        raise ValueError(f"No valid {config.column_name} events for {config.name}.")

    energies = calibrate_energy(x_mm, config)
    energies = energies[np.isfinite(energies)]

    if config.anchor_centroid_mev is not None:
        energies = energies + (
            anchor_reference_mev - config.anchor_centroid_mev
        )

    return energies


def normalized_counts(
    counts: np.ndarray,
    mode: str,
    energy_centers: np.ndarray,
) -> np.ndarray:
    """Return raw counts or a clearly defined shape normalization."""
    values = counts.astype(float)
    lo, hi = normalization_window_mev
    window = (energy_centers >= lo) & (energy_centers <= hi)

    if not np.any(window):
        raise ValueError("The normalization window does not overlap the histogram.")

    if mode == "Raw counts":
        return values

    if mode == "Area normalized":
        denominator = values[window].sum()
    elif mode == "Peak normalized":
        denominator = values[window].max()
    else:
        raise ValueError(f"Unknown normalization mode '{mode}'.")

    if denominator <= 0:
        raise ValueError(
            f"Cannot apply '{mode}' because its normalization denominator is zero."
        )

    return values / denominator


def y_axis_label(mode: str) -> str:
    if mode == "Raw counts":
        return f"Counts / {energy_bin_width_kev:g} keV"
    if mode == "Area normalized":
        return "Area-normalized counts (arb. units)"
    return "Peak-normalized counts (arb. units)"


def style_spectrum_axis(axis: plt.Axes, mode: str) -> None:
    axis.set_title(title, fontsize=17)
    axis.set_xlabel(
        r"$^{13}\mathrm{C}$ Excitation Energy (MeV)",
        fontsize=17,
        loc="right",
    )
    axis.set_ylabel(y_axis_label(mode), fontsize=17)
    axis.set_xlim(energy_min_mev, energy_max_mev)
    axis.minorticks_on()
    axis.tick_params(
        axis="both",
        which="major",
        direction="in",
        top=True,
        right=True,
        length=7,
    )
    axis.tick_params(
        axis="both",
        which="minor",
        direction="in",
        top=True,
        right=True,
        length=4,
    )


# =============================================================================
# Load, calibrate, and histogram both spectra
# =============================================================================

if not energy_min_mev < energy_max_mev:
    raise ValueError("energy_min_mev must be smaller than energy_max_mev.")

li6_plot_min_mev, li6_plot_max_mev = li6_plot_range_mev
if not (
    energy_min_mev
    <= li6_plot_min_mev
    < li6_plot_max_mev
    <= energy_max_mev
):
    raise ValueError(
        "li6_plot_range_mev must lie inside the full displayed energy range."
    )

energy_bin_width_mev = energy_bin_width_kev / 1000.0
n_energy_bins = int(
    np.ceil(
        (energy_max_mev - energy_min_mev)
        / energy_bin_width_mev
    )
)
energy_edges = (
    energy_min_mev
    + np.arange(n_energy_bins + 1) * energy_bin_width_mev
)
energy_centers = 0.5 * (energy_edges[:-1] + energy_edges[1:])

# The (d,p) spectrum uses every bin. Only the selected calibrated-energy
# interval is displayed for (6Li,d); both still share identical bin edges.
display_masks = {
    LI6D.name: (
        (energy_centers >= li6_plot_min_mev)
        & (energy_centers <= li6_plot_max_mev)
    ),
    DP.name: np.ones_like(energy_centers, dtype=bool),
}

raw_counts = {}
event_totals = {}

for spectrum in SPECTRA:
    calibrated_energies = load_calibrated_energies(spectrum)
    raw_counts[spectrum.name], _ = np.histogram(
        calibrated_energies,
        bins=energy_edges,
    )
    event_totals[spectrum.name] = calibrated_energies.size
    print(
        f"{spectrum.name}: {calibrated_energies.size} calibrated events; "
        f"{raw_counts[spectrum.name].sum()} inside the plotted energy range."
    )
    if spectrum.anchor_centroid_mev is not None:
        anchor_offset = anchor_reference_mev - spectrum.anchor_centroid_mev
        print(
            f"{spectrum.name}: applied anchor offset "
            f"{anchor_offset:+.6f} MeV."
        )


# =============================================================================
# Interactive overlay
# =============================================================================

fig, ax = plt.subplots(figsize=(12, 7))
fig.subplots_adjust(left=0.10, right=0.76, bottom=0.27, top=0.91)

current_mode = initial_normalization
lines = {}

for spectrum in SPECTRA:
    y_values = normalized_counts(
        raw_counts[spectrum.name],
        current_mode,
        energy_centers,
    )
    display_mask = display_masks[spectrum.name]
    (lines[spectrum.name],) = ax.step(
        energy_centers[display_mask],
        y_values[display_mask],
        where="mid",
        color=spectrum.color,
        linewidth=1.5,
        label=spectrum.legend_label,
    )

style_spectrum_axis(ax, current_mode)
# ax.legend(loc="upper right", frameon=False, fontsize=11)

status_text = ax.text(
    0.01,
    0.98,
    "Residual shifts: 0.000 MeV, 0.000 MeV",
    transform=ax.transAxes,
    ha="left",
    va="top",
    fontsize=10,
)

# Slider axes
li6_slider_ax = fig.add_axes((0.13, 0.15, 0.50, 0.03))
dp_slider_ax = fig.add_axes((0.13, 0.09, 0.50, 0.03))

li6_shift_slider = Slider(
    ax=li6_slider_ax,
    label=r"$^{9}\mathrm{Be}(^{6}\mathrm{Li},d)$ $\Delta E$ (MeV)",
    valmin=shift_min_mev,
    valmax=shift_max_mev,
    valinit=0.0,
    valstep=shift_step_mev,
)
dp_shift_slider = Slider(
    ax=dp_slider_ax,
    label=r"$^{12}\mathrm{C}(d,p)$ $\Delta E$ (MeV)",
    valmin=shift_min_mev,
    valmax=shift_max_mev,
    valinit=0.0,
    valstep=shift_step_mev,
)

# Normalization selector and buttons
radio_ax = fig.add_axes((0.79, 0.55, 0.19, 0.19))
normalization_radio = RadioButtons(
    radio_ax,
    ("Raw counts", "Area normalized", "Peak normalized"),
    active=("Raw counts", "Area normalized", "Peak normalized").index(
        initial_normalization
    ),
)
radio_ax.set_title("Vertical comparison", fontsize=11)

reset_ax = fig.add_axes((0.80, 0.38, 0.08, 0.05))
save_ax = fig.add_axes((0.89, 0.38, 0.08, 0.05))
reset_button = Button(reset_ax, "Reset")
save_button = Button(save_ax, "Save")


def refresh_plot(_=None) -> None:
    """Apply the selected shifts and normalization to the live plot."""
    global current_mode
    current_mode = normalization_radio.value_selected

    shifts = {
        LI6D.name: li6_shift_slider.val,
        DP.name: dp_shift_slider.val,
    }

    maximum = 0.0
    for spectrum in SPECTRA:
        y_values = normalized_counts(
            raw_counts[spectrum.name],
            current_mode,
            energy_centers,
        )
        display_mask = display_masks[spectrum.name]
        lines[spectrum.name].set_data(
            energy_centers[display_mask] + shifts[spectrum.name],
            y_values[display_mask],
        )
        maximum = max(
            maximum,
            float(np.max(y_values[display_mask])),
        )

    ax.set_ylabel(y_axis_label(current_mode), fontsize=17)
    ax.set_ylim(0.0, 1.08 * maximum if maximum > 0 else 1.0)
    status_text.set_text(
        "Residual shifts: "
        f"{LI6D.name} = {shifts[LI6D.name]:+.3f} MeV, "
        f"{DP.name} = {shifts[DP.name]:+.3f} MeV"
    )
    fig.canvas.draw_idle()


def reset_controls(_event) -> None:
    li6_shift_slider.reset()
    dp_shift_slider.reset()
    normalization_radio.set_active(
        ("Raw counts", "Area normalized", "Peak normalized").index(
            initial_normalization
        )
    )
    refresh_plot()


def save_current_view(_event) -> None:
    """Save a clean figure and a machine-readable record of the GUI state."""
    shifts = {
        LI6D.name: float(li6_shift_slider.val),
        DP.name: float(dp_shift_slider.val),
    }

    export_fig, export_ax = plt.subplots(figsize=(12, 7))
    for spectrum in SPECTRA:
        y_values = normalized_counts(
            raw_counts[spectrum.name],
            current_mode,
            energy_centers,
        )
        display_mask = display_masks[spectrum.name]
        export_ax.step(
            energy_centers[display_mask] + shifts[spectrum.name],
            y_values[display_mask],
            where="mid",
            color=spectrum.color,
            linewidth=1.5,
            label=spectrum.legend_label,
        )

    style_spectrum_axis(export_ax, current_mode)
    export_ax.legend(loc="upper right", frameon=False, fontsize=11)
    export_fig.tight_layout()

    figure_path = output_stem.with_suffix(".png")
    settings_path = output_stem.with_suffix(".json")
    export_fig.savefig(figure_path, dpi=300, bbox_inches="tight")
    plt.close(export_fig)

    settings = {
        "normalization_mode": current_mode,
        "normalization_window_mev": normalization_window_mev,
        "energy_range_mev": (energy_min_mev, energy_max_mev),
        "energy_bin_width_kev": energy_bin_width_kev,
        "n_energy_bins": n_energy_bins,
        "li6_plot_range_mev": li6_plot_range_mev,
        "anchor_reference_mev": anchor_reference_mev,
        "residual_energy_shifts_mev": shifts,
        "event_totals_before_energy_range_cut": event_totals,
        "spectra": [
            {
                **asdict(spectrum),
                "parquet_file": str(spectrum.parquet_file),
            }
            for spectrum in SPECTRA
        ],
    }
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    print(f"Saved figure: {figure_path.resolve()}")
    print(f"Saved settings: {settings_path.resolve()}")


li6_shift_slider.on_changed(refresh_plot)
dp_shift_slider.on_changed(refresh_plot)
normalization_radio.on_clicked(refresh_plot)
reset_button.on_clicked(reset_controls)
save_button.on_clicked(save_current_view)

refresh_plot()
plt.show()

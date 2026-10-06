"""Overlay independently calibrated (6Li,d) and (d,p) spectra.

This script intentionally preserves each spectrum's original focal-plane
histogram.  It first bins Xshap using the configured native 1-mm bins, then
transforms those bin edges to excitation energy and draws them with
``Axes.stairs``.  It does not smooth, convolve, interpolate, or re-histogram
the events onto a new common energy grid.

By default, the (d,p) spectrum is multiplied by the ratio of the
background-subtracted 6.86-MeV peak areas,

    A[(6Li,d), 6.86] / A[(d,p), 6.86].

This is a single vertical scale factor.  It does not change either spectrum's
binning, energy calibration, centroid, line shape, or FWHM.  Use
``--normalization none`` to disable it.

Example
-------
python PlotTwoEnergySpectra.py \
    /path/to/15deg_13.85kG_total_cut.parquet \
    /path/to/15deg_5.6kG_total_cut.parquet
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl


@dataclass(frozen=True)
class SpectrumConfig:
    """Calibration, native binning, and display settings for one spectrum."""

    name: str
    column_name: str
    x_range_mm: tuple[float, float]
    x_bin_width_mm: float
    calibration_type: str
    linear_b: float
    linear_c: float
    quad_a: float
    quad_b: float
    quad_c: float
    color: str
    label: str


# =============================================================================
# Calibration and native-binning inputs
# =============================================================================

LI6D = SpectrumConfig(
    name="6Li,d",
    column_name="Xshap",
    x_range_mm=(-300.0, 200.0),
    x_bin_width_mm=1.0,
    calibration_type="quadratic",  # "linear" or "quadratic"
    linear_b=-0.00852,
    linear_c=8.120,
    quad_a=-9.928367235e-06,
    quad_b=-0.02230239502,
    quad_c=9.333177567,
    color="#0072B2",
    label=(
        r"$^{9}\mathrm{Be}(^{6}\mathrm{Li},d)^{13}\mathrm{C}$"
        "\n"
        r"$B=13.852$ kG, $E_{^{6}\mathrm{Li}}=32$ MeV"
    ),
)

DP = SpectrumConfig(
    name="d,p",
    column_name="Xshap",
    x_range_mm=(-320.0, 250.0),
    x_bin_width_mm=1.0,
    calibration_type="linear",  # "linear" or "quadratic"
    linear_b=-0.008594831532,
    linear_c=8.251265961,
    quad_a=0.0,
    quad_b=-0.008594831532,
    quad_c=8.251265961,
    color="#D55E00",
    label=(
        r"$^{12}\mathrm{C}(d,p)^{13}\mathrm{C}$"
        "\n"
        r"$B=5.625$ kG, $E_d=16$ MeV"
    ),
)

INVALID_CUT = -1e6
DEFAULT_XLIM_MEV = (6.0, 11.3)
DEFAULT_LI6_DISPLAY_RANGE_MEV = (6.0, 11.3)
DEFAULT_NORMALIZATION = "peak-area"
DEFAULT_PEAK_WINDOW_MEV = (6.82, 6.90)
DEFAULT_LEFT_SIDEBAND_MEV = (6.72, 6.80)
DEFAULT_RIGHT_SIDEBAND_MEV = (6.92, 7.00)
DEFAULT_OUTPUT = Path("13C_686_peak_normalized_overlay_15deg.png")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Overlay native-bin-preserving, independently energy-calibrated "
            "(6Li,d) and (d,p) Parquet spectra."
        )
    )
    parser.add_argument(
        "li6_file",
        type=Path,
        help="Parquet file containing the (6Li,d) Xshap spectrum.",
    )
    parser.add_argument(
        "dp_file",
        type=Path,
        help="Parquet file containing the (d,p) Xshap spectrum.",
    )
    parser.add_argument(
        "--li6-range",
        nargs=2,
        type=float,
        metavar=("MIN_MEV", "MAX_MEV"),
        default=DEFAULT_LI6_DISPLAY_RANGE_MEV,
        help=(
            "Energy interval drawn for (6Li,d). "
            f"Default: {DEFAULT_LI6_DISPLAY_RANGE_MEV}."
        ),
    )
    parser.add_argument(
        "--xlim",
        nargs=2,
        type=float,
        metavar=("MIN_MEV", "MAX_MEV"),
        default=DEFAULT_XLIM_MEV,
        help=f"Full plot range. Default: {DEFAULT_XLIM_MEV}.",
    )
    parser.add_argument(
        "--y-mode",
        choices=("native-counts", "counts-per-kev"),
        default="counts-per-kev",
        help=(
            "native-counts exactly preserves the original 1-mm-bin counts; "
            "counts-per-kev divides by each transformed energy-bin width "
            "and is the default for comparing the two reactions."
        ),
    )
    parser.add_argument(
        "--normalization",
        choices=("none", "peak-area"),
        default=DEFAULT_NORMALIZATION,
        help=(
            "peak-area leaves (6Li,d) unchanged and scales (d,p) by the "
            "ratio of their background-subtracted 6.86-MeV peak areas. "
            f"Default: {DEFAULT_NORMALIZATION}."
        ),
    )
    parser.add_argument(
        "--peak-window",
        nargs=2,
        type=float,
        metavar=("MIN_MEV", "MAX_MEV"),
        default=DEFAULT_PEAK_WINDOW_MEV,
        help=(
            "Integration window for the 6.86-MeV reference peak. "
            f"Default: {DEFAULT_PEAK_WINDOW_MEV}."
        ),
    )
    parser.add_argument(
        "--left-sideband",
        nargs=2,
        type=float,
        metavar=("MIN_MEV", "MAX_MEV"),
        default=DEFAULT_LEFT_SIDEBAND_MEV,
        help=(
            "Left background sideband for the reference peak. "
            f"Default: {DEFAULT_LEFT_SIDEBAND_MEV}."
        ),
    )
    parser.add_argument(
        "--right-sideband",
        nargs=2,
        type=float,
        metavar=("MIN_MEV", "MAX_MEV"),
        default=DEFAULT_RIGHT_SIDEBAND_MEV,
        help=(
            "Right background sideband for the reference peak. "
            f"Default: {DEFAULT_RIGHT_SIDEBAND_MEV}."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output PNG. Default: {DEFAULT_OUTPUT}.",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Save the figure without opening the interactive window.",
    )
    return parser.parse_args()


def read_xshap(path: Path, config: SpectrumConfig) -> np.ndarray:
    """Load finite, valid focal-plane positions from one Parquet file."""
    if not path.exists():
        raise FileNotFoundError(f"Input file was not found: {path}")

    frame = pl.read_parquet(path)
    if config.column_name not in frame.columns:
        raise ValueError(
            f"Column '{config.column_name}' was not found in {path}."
        )

    x_values = (
        frame
        .filter(pl.col(config.column_name).is_not_null())
        .filter(pl.col(config.column_name) > INVALID_CUT)
        .get_column(config.column_name)
        .to_numpy()
    )
    x_values = x_values[np.isfinite(x_values)]

    if x_values.size == 0:
        raise ValueError(f"No valid {config.column_name} events found in {path}.")

    return x_values


def calibrate_energy(x_mm: np.ndarray, config: SpectrumConfig) -> np.ndarray:
    """Apply the selected position-to-excitation-energy calibration."""
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
        f"Unknown calibration type '{config.calibration_type}' "
        f"for {config.name}."
    )


def native_histogram_in_energy(
    x_values: np.ndarray,
    config: SpectrumConfig,
) -> tuple[np.ndarray, np.ndarray]:
    """Histogram in native Xshap bins and transform only the bin edges."""
    x_min, x_max = config.x_range_mm
    span_mm = x_max - x_min
    n_bins_float = span_mm / config.x_bin_width_mm
    n_bins = int(round(n_bins_float))

    if not np.isclose(n_bins, n_bins_float):
        raise ValueError(
            f"The {config.name} Xshap range is not an integer multiple "
            "of x_bin_width_mm."
        )

    counts, x_edges = np.histogram(
        x_values,
        bins=n_bins,
        range=config.x_range_mm,
    )
    energy_edges = calibrate_energy(x_edges, config)

    edge_differences = np.diff(energy_edges)
    if np.all(edge_differences < 0):
        energy_edges = energy_edges[::-1]
        counts = counts[::-1]
    elif not np.all(edge_differences > 0):
        raise ValueError(
            f"The {config.name} calibration is not monotonic across "
            f"the configured Xshap range {config.x_range_mm}."
        )

    return counts.astype(float), energy_edges


def values_for_plot(
    counts: np.ndarray,
    energy_edges: np.ndarray,
    y_mode: str,
) -> np.ndarray:
    """Convert native-bin counts to the requested vertical representation."""
    values = counts.astype(float)
    if y_mode == "counts-per-kev":
        bin_widths_kev = np.diff(energy_edges) * 1000.0
        values = values / bin_widths_kev
    return values


def validate_reference_windows(
    peak_window: tuple[float, float] | list[float],
    left_sideband: tuple[float, float] | list[float],
    right_sideband: tuple[float, float] | list[float],
) -> None:
    """Require ordered, non-overlapping background and peak intervals."""
    left_lo, left_hi = left_sideband
    peak_lo, peak_hi = peak_window
    right_lo, right_hi = right_sideband

    if not (
        left_lo < left_hi < peak_lo < peak_hi < right_lo < right_hi
    ):
        raise ValueError(
            "Reference windows must be ordered and non-overlapping: "
            "left sideband < peak window < right sideband."
        )


def integrate_histogram_window(
    counts: np.ndarray,
    energy_edges: np.ndarray,
    window: tuple[float, float] | list[float],
) -> float:
    """Integrate a variable-width histogram over an energy interval.

    A constant density is assumed inside each native bin only when a requested
    boundary cuts through that bin.  Whole native bins retain their exact
    recorded counts.
    """
    lo, hi = window
    if lo >= hi:
        raise ValueError("Integration-window minimum must be below its maximum.")
    if lo < energy_edges[0] or hi > energy_edges[-1]:
        raise ValueError(
            f"Integration window ({lo:g}, {hi:g}) MeV lies outside the "
            f"calibrated histogram range ({energy_edges[0]:g}, "
            f"{energy_edges[-1]:g}) MeV."
        )

    bin_widths = np.diff(energy_edges)
    overlaps = np.maximum(
        0.0,
        np.minimum(energy_edges[1:], hi)
        - np.maximum(energy_edges[:-1], lo),
    )
    return float(np.sum(counts * overlaps / bin_widths))


def background_subtracted_peak_area(
    counts: np.ndarray,
    energy_edges: np.ndarray,
    peak_window: tuple[float, float] | list[float],
    left_sideband: tuple[float, float] | list[float],
    right_sideband: tuple[float, float] | list[float],
) -> dict[str, float]:
    """Measure a peak area above a line joining its two sidebands."""
    gross_counts = integrate_histogram_window(
        counts,
        energy_edges,
        peak_window,
    )
    left_counts = integrate_histogram_window(
        counts,
        energy_edges,
        left_sideband,
    )
    right_counts = integrate_histogram_window(
        counts,
        energy_edges,
        right_sideband,
    )

    left_width = left_sideband[1] - left_sideband[0]
    right_width = right_sideband[1] - right_sideband[0]
    left_density = left_counts / left_width
    right_density = right_counts / right_width

    left_center = 0.5 * (left_sideband[0] + left_sideband[1])
    right_center = 0.5 * (right_sideband[0] + right_sideband[1])
    peak_center = 0.5 * (peak_window[0] + peak_window[1])
    peak_width = peak_window[1] - peak_window[0]

    interpolation_fraction = (
        (peak_center - left_center) / (right_center - left_center)
    )
    background_density_at_peak = (
        left_density
        + interpolation_fraction * (right_density - left_density)
    )
    background_counts = background_density_at_peak * peak_width
    net_counts = gross_counts - background_counts

    if net_counts <= 0:
        raise ValueError(
            "The background-subtracted 6.86-MeV reference-peak area is "
            "not positive. Inspect or change the peak/sideband windows."
        )

    return {
        "gross_counts": gross_counts,
        "estimated_background_counts": background_counts,
        "net_peak_area_counts": net_counts,
        "left_sideband_counts": left_counts,
        "right_sideband_counts": right_counts,
        "left_sideband_density_counts_per_mev": left_density,
        "right_sideband_density_counts_per_mev": right_density,
    }


def crop_histogram(
    values: np.ndarray,
    edges: np.ndarray,
    display_range: tuple[float, float] | list[float],
) -> tuple[np.ndarray, np.ndarray]:
    """Return the contiguous bins whose centers fall inside a display range."""
    minimum, maximum = display_range
    if minimum >= maximum:
        raise ValueError("Display-range minimum must be smaller than maximum.")

    centers = 0.5 * (edges[:-1] + edges[1:])
    selected = np.flatnonzero((centers >= minimum) & (centers <= maximum))
    if selected.size == 0:
        raise ValueError(
            f"No calibrated bins fall inside ({minimum}, {maximum}) MeV."
        )

    first = int(selected[0])
    last = int(selected[-1])
    return values[first:last + 1], edges[first:last + 2]


def style_axis(axis: plt.Axes, y_mode: str, normalization: str) -> None:
    axis.set_title(
        r"$^{13}\mathrm{C}$ Spectra, "
        r"$\theta_{\mathrm{SE-SPS}}=15^\circ$",
        fontsize=17,
    )
    axis.set_xlabel(
        r"$^{13}\mathrm{C}$ Excitation Energy (MeV)",
        fontsize=17,
        loc="right",
    )
    if normalization == "peak-area" and y_mode == "native-counts":
        axis.set_ylabel(
            "Relative counts / native 1-mm bin (arb. units)",
            fontsize=17,
        )
    elif normalization == "peak-area":
        axis.set_ylabel("Relative yield / keV (arb. units)", fontsize=17)
    elif y_mode == "native-counts":
        axis.set_ylabel("Counts / native 1-mm bin", fontsize=17)
    else:
        axis.set_ylabel("Counts / keV", fontsize=17)

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


def main() -> None:
    args = parse_arguments()

    li6_x = read_xshap(args.li6_file, LI6D)
    dp_x = read_xshap(args.dp_file, DP)

    li6_counts, li6_energy_edges = native_histogram_in_energy(
        li6_x,
        LI6D,
    )
    dp_counts, dp_energy_edges = native_histogram_in_energy(
        dp_x,
        DP,
    )

    li6_scale = 1.0
    dp_scale = 1.0
    peak_diagnostics: dict[str, dict[str, float]] = {}

    if args.normalization == "peak-area":
        validate_reference_windows(
            args.peak_window,
            args.left_sideband,
            args.right_sideband,
        )
        peak_diagnostics[LI6D.name] = background_subtracted_peak_area(
            li6_counts,
            li6_energy_edges,
            args.peak_window,
            args.left_sideband,
            args.right_sideband,
        )
        peak_diagnostics[DP.name] = background_subtracted_peak_area(
            dp_counts,
            dp_energy_edges,
            args.peak_window,
            args.left_sideband,
            args.right_sideband,
        )
        dp_scale = (
            peak_diagnostics[LI6D.name]["net_peak_area_counts"]
            / peak_diagnostics[DP.name]["net_peak_area_counts"]
        )

    li6_values = (
        values_for_plot(li6_counts, li6_energy_edges, args.y_mode)
        * li6_scale
    )
    dp_values = (
        values_for_plot(dp_counts, dp_energy_edges, args.y_mode)
        * dp_scale
    )

    # Draw only the requested calibrated-energy interval for (6Li,d).
    li6_values, li6_energy_edges = crop_histogram(
        li6_values,
        li6_energy_edges,
        args.li6_range,
    )

    figure, axis = plt.subplots(figsize=(12, 7))
    dp_label = DP.label
    li6_label = LI6D.label
    if args.normalization == "peak-area":
        li6_label += "\n" + r"$\times\,1$ (6.86-MeV reference)"
        dp_label += "\n" + rf"$\times\,{dp_scale:.4g}$"

    axis.stairs(
        dp_values,
        dp_energy_edges,
        color=DP.color,
        linewidth=1.4,
        label=dp_label,
    )
    axis.stairs(
        li6_values,
        li6_energy_edges,
        color=LI6D.color,
        linewidth=1.4,
        label=li6_label,
    )

    style_axis(axis, args.y_mode, args.normalization)
    axis.set_xlim(*args.xlim)
    axis.set_ylim(bottom=0.0)
    axis.legend(loc="upper right", frameon=False, fontsize=11)
    figure.tight_layout()

    figure.savefig(args.output, dpi=300, bbox_inches="tight")

    metadata_path = args.output.with_suffix(".json")
    metadata = {
        "input_files": {
            LI6D.name: str(args.li6_file.resolve()),
            DP.name: str(args.dp_file.resolve()),
        },
        "y_mode": args.y_mode,
        "normalization": args.normalization,
        "normalization_definition": (
            "The (6Li,d) spectrum is held at scale 1. The (d,p) spectrum "
            "is multiplied by the ratio of the background-subtracted "
            "6.86-MeV peak areas: A_(6Li,d) / A_(d,p). A linear local "
            "background is estimated from the two sidebands."
            if args.normalization == "peak-area"
            else "No relative vertical normalization was applied."
        ),
        "reference_windows_mev": {
            "peak": list(args.peak_window),
            "left_sideband": list(args.left_sideband),
            "right_sideband": list(args.right_sideband),
        },
        "scale_factors": {
            LI6D.name: li6_scale,
            DP.name: dp_scale,
        },
        "reference_peak_diagnostics": peak_diagnostics,
        "xlim_mev": list(args.xlim),
        "li6_display_range_mev": list(args.li6_range),
        "valid_event_totals": {
            LI6D.name: int(li6_x.size),
            DP.name: int(dp_x.size),
        },
        "spectrum_configuration": {
            LI6D.name: asdict(LI6D),
            DP.name: asdict(DP),
        },
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(f"Saved overlay: {args.output.resolve()}")
    print(f"Saved normalization record: {metadata_path.resolve()}")
    print(
        f"(6Li,d): {li6_x.size} valid events; "
        f"displayed from {args.li6_range[0]:g} to "
        f"{args.li6_range[1]:g} MeV."
    )
    print(f"(d,p): {dp_x.size} valid events; full native histogram plotted.")

    if args.normalization == "peak-area":
        li6_area = peak_diagnostics[LI6D.name]["net_peak_area_counts"]
        dp_area = peak_diagnostics[DP.name]["net_peak_area_counts"]
        print(
            "6.86-MeV reference-peak normalization:"
            f"\n  peak window       = {tuple(args.peak_window)} MeV"
            f"\n  left sideband     = {tuple(args.left_sideband)} MeV"
            f"\n  right sideband    = {tuple(args.right_sideband)} MeV"
            f"\n  (6Li,d) net area  = {li6_area:.6g} counts"
            f"\n  (d,p) net area    = {dp_area:.6g} counts"
            f"\n  (6Li,d) scale     = {li6_scale:.8g}"
            f"\n  (d,p) scale       = {dp_scale:.8g}"
        )

    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()

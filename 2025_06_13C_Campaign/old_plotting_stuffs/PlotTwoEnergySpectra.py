"""Overlay independently calibrated (6Li,d) and (d,p) spectra.

This script intentionally preserves each spectrum's original focal-plane
histogram.  It first bins Xshap using the configured native 1-mm bins, then
transforms those bin edges to excitation energy and draws them with
``Axes.stairs``.  It does not smooth, convolve, interpolate, or re-histogram
the events onto a new common energy grid.

Example
-------
python PlotTwoEnergySpectra.py \
    /path/to/15deg_13.85kG_total_cut.parquet \
    /path/to/15deg_5.6kG_total_cut.parquet
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
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
# DEFAULT_XLIM_MEV = (6.0, 11.3)
DEFAULT_XLIM_MEV = (6.0, 10.4)
# DEFAULT_LI6_DISPLAY_RANGE_MEV = (6.0, 11.3)
DEFAULT_LI6_DISPLAY_RANGE_MEV = (6.0, 10.4)
DEFAULT_OUTPUT = Path("13C_native_bin_overlay_15deg.png")


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
        default="native-counts",
        help=(
            "native-counts exactly preserves the original 1-mm-bin counts; "
            "counts-per-kev divides by each transformed energy-bin width."
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
    y_mode: str,
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

    values = counts.astype(float)
    if y_mode == "counts-per-kev":
        bin_widths_kev = np.diff(energy_edges) * 1000.0
        values = values / bin_widths_kev

    return values, energy_edges


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


def style_axis(axis: plt.Axes, y_mode: str) -> None:
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
    if y_mode == "native-counts":
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
        labelsize=14,
    )
    axis.tick_params(
        axis="both",
        which="minor",
        direction="in",
        top=True,
        right=True,
        length=4,
        labelsize=14,
    )


def main() -> None:
    args = parse_arguments()

    li6_x = read_xshap(args.li6_file, LI6D)
    dp_x = read_xshap(args.dp_file, DP)

    li6_values, li6_energy_edges = native_histogram_in_energy(
        li6_x,
        LI6D,
        args.y_mode,
    )
    dp_values, dp_energy_edges = native_histogram_in_energy(
        dp_x,
        DP,
        args.y_mode,
    )

    # Draw only the requested calibrated-energy interval for (6Li,d).
    li6_values, li6_energy_edges = crop_histogram(
        li6_values,
        li6_energy_edges,
        args.li6_range,
    )

    figure, axis = plt.subplots(figsize=(12, 7))

    li6_scale = 1.0
    dp_scale = 1.0
    li6_values *= li6_scale
    dp_values *= dp_scale

    axis.stairs(
        dp_values,
        dp_energy_edges,
        color=DP.color,
        linewidth=1.4,
        label=DP.label + rf"  $\times\,{dp_scale:g}$",
    )
    axis.stairs(
        li6_values,
        li6_energy_edges,
        color=LI6D.color,
        linewidth=1.4,
        label=LI6D.label+ rf"  $\times\,{dp_scale:g}$",
    )

    style_axis(axis, args.y_mode)
    axis.set_xlim(*args.xlim)
    axis.set_ylim(bottom=0.0)
    # axis.legend(loc="upper left", frameon=False, fontsize=11)
    figure.tight_layout()

    figure.savefig(args.output, dpi=300, bbox_inches="tight")
    print(f"Saved overlay: {args.output.resolve()}")
    print(
        f"(6Li,d): {li6_x.size} valid events; "
        f"displayed from {args.li6_range[0]:g} to "
        f"{args.li6_range[1]:g} MeV."
    )
    print(f"(d,p): {dp_x.size} valid events; full native histogram plotted.")

    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()

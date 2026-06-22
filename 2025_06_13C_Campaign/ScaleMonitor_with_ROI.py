#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os


def scale_and_plot_multiple(
    parquet_files,
    scaling_factors,
    bins=256,
    energy_range=(0, 4096),
    integration_range=None,
):
    """
    Scale multiple MonitorEnergy spectra and plot them together.

    Args:
        parquet_files (list of str): list of parquet filenames (full path or relative)
        scaling_factors (list of float): scaling factor for each file
        bins (int): number of bins for histograms
        energy_range (tuple): (min, max) for x-axis
        integration_range (tuple or None): (min, max) ROI to integrate.
            If provided, prints raw and scaled integrals for each spectrum.
    """

    if len(parquet_files) != len(scaling_factors):
        raise ValueError("Number of parquet files must match number of scaling factors.")

    if integration_range is not None:
        x_min, x_max = integration_range
        print("\nMonitorEnergy ROI integrals")
        print(f"ROI: [{x_min}, {x_max}]")
        print("-" * 82)
        print(f"{'File':40s} {'Scale':>8s} {'Raw integral':>15s} {'Scaled integral':>17s}")
        print("-" * 82)

    plt.figure(figsize=(10, 7))

    for pf, scale in zip(parquet_files, scaling_factors):
        df = pd.read_parquet(pf)

        if "MonitorEnergy" not in df.columns:
            raise ValueError(f"{pf} does not contain 'MonitorEnergy' column.")

        # Build histogram and scale counts
        counts, bin_edges = np.histogram(df["MonitorEnergy"], bins=bins, range=energy_range)
        scaled_counts = counts * scale
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # Integrate chosen ROI, if requested
        if integration_range is not None:
            x_min, x_max = integration_range
            roi_mask = (bin_centers >= x_min) & (bin_centers <= x_max)

            raw_integral = counts[roi_mask].sum()
            scaled_integral = scaled_counts[roi_mask].sum()

            print(
                f"{os.path.basename(pf):40s} "
                f"{scale:8.3f} "
                f"{raw_integral:15.2f} "
                f"{scaled_integral:17.2f}"
            )

        # Plot scaled spectrum
        plt.step(
            bin_centers,
            scaled_counts,
            where="mid",
            linewidth=1.5,
            label=f"{os.path.basename(pf)} ×{scale}",
        )

        # Save individual scaled parquet
        scaled_df = pd.DataFrame({
            "BinLowEdge": bin_edges[:-1],
            "BinHighEdge": bin_edges[1:],
            "Counts": counts,
            "ScaledCounts": scaled_counts,
        })
        base, ext = os.path.splitext(pf)
        new_file = f"{base}_scaled{ext}"
        scaled_df.to_parquet(new_file, index=False)
        # print(f"✅ Scaled histogram saved as: {new_file}")

    if integration_range is not None:
        print("-" * 82)

        # Optional visual ROI markers on the plot
        x_min, x_max = integration_range
        plt.axvline(x_min, linestyle="--", linewidth=1.2, color="black")
        plt.axvline(x_max, linestyle="--", linewidth=1.2, color="black")

    # Final overlay plot formatting
    plt.xlabel("Monitor Energy (arb. units)")
    plt.ylabel("Counts (scaled)")
    plt.title("Scaled Monitor Spectra for All Runs")
    # plt.title("Unscaled Monitor Spectra for All Runs")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # <--- manually specify parquet files and their scaling factors
    parquet_files = [
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/9Be6Lid_H_included/10deg_14kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/9Be6Lid_H_included/12deg_14kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/9Be6Lid_H_included/15deg_13.85kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/9Be6Lid_H_included/17deg_13.85kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/9Be6Lid_H_included/20deg_13.7kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/9Be6Lid_H_included/25deg_13.6kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/9Be6Lid_H_included/35deg_13.25kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/9Be6Lid_H_included/40deg_12.9kG_total.parquet",
    ]

    scaling_factors = [1.000, 1.676, 1.286, 3.093, 1.471, 3.036, 3.458, 2.581]
    # scaling_factors = [1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000]
    # scaling_factors = [1.000, 1.676, 1.419, 3.093, 4.607, 3.036, 10.37, 7.882]

    scale_and_plot_multiple(
        parquet_files,
        scaling_factors,
        bins=256,
        energy_range=(0, 4096),
        integration_range=(3000, 4000),  # <--- change this to your monitor ROI
    )

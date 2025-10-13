#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def scale_and_plot_multiple(parquet_files, scaling_factors, bins=256, energy_range=(0, 4096)):
    """
    Scale multiple MonitorEnergy spectra and plot them together.
    
    Args:
        parquet_files (list of str): list of parquet filenames (full path or relative)
        scaling_factors (list of float): scaling factor for each file
        bins (int): number of bins for histograms
        energy_range (tuple): (min, max) for x-axis
    """

    if len(parquet_files) != len(scaling_factors):
        raise ValueError("Number of parquet files must match number of scaling factors.")

    plt.figure(figsize=(10,7))

    for pf, scale in zip(parquet_files, scaling_factors):
        df = pd.read_parquet(pf)

        if "MonitorEnergy" not in df.columns:
            raise ValueError(f"{pf} does not contain 'MonitorEnergy' column.")

        # Build histogram and scale counts
        counts, bin_edges = np.histogram(df["MonitorEnergy"], bins=bins, range=energy_range)
        scaled_counts = counts * scale
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # Plot scaled spectrum
        plt.step(bin_centers, scaled_counts, where='mid', linewidth=1.5, label=f"{os.path.basename(pf)} ×{scale}")

        # Save individual scaled parquet
        scaled_df = pd.DataFrame({
            "BinLowEdge": bin_edges[:-1],
            "BinHighEdge": bin_edges[1:],
            "Counts": counts,
            "ScaledCounts": scaled_counts
        })
        base, ext = os.path.splitext(pf)
        new_file = f"{base}_scaled{ext}"
        scaled_df.to_parquet(new_file, index=False)
        #print(f"✅ Scaled histogram saved as: {new_file}")

    # Final overlay plot formatting
    plt.xlabel("Monitor Energy (arb. units)")
    plt.ylabel("Counts (scaled)")
    plt.title("Scaled Monitor Spectra for All Runs")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # <--- manually specify parquet files and their scaling factors
    parquet_files = [
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/10deg_14kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/12deg_14kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/15deg_13.85kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/17deg_13.85kG_runs_369_375.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/20deg_13.7kG_runs_355_364.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/25deg_13.6kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/35deg_13.25kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/40deg_12.9kG_total.parquet"
    ]
    scaling_factors = [1.000, 1.676, 1.286, 3.093, 1.471, 3.036, 3.458, 2.581]  # <--- manually set per run

    scale_and_plot_multiple(parquet_files, scaling_factors)


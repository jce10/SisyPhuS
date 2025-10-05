#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def scale_and_plot_subplots(parquet_files, scaling_factors, bins=512, energy_range=(0, 4096)):
    """
    Plot original and scaled MonitorEnergy spectra in a 1x2 subplot.
    
    Args:
        parquet_files (list of str): list of parquet filenames
        scaling_factors (list of float): scaling factor for each file
        bins (int): number of bins for histograms
        energy_range (tuple): (min, max) for x-axis
    """

    if len(parquet_files) != len(scaling_factors):
        raise ValueError("Number of parquet files must match number of scaling factors.")

    # Create figure with 1x2 subplots
    fig, axes = plt.subplots(1, 2, figsize=(14,6), sharey=True)

    for pf, scale in zip(parquet_files, scaling_factors):
        df = pd.read_parquet(pf)

        if "MonitorEnergy" not in df.columns:
            raise ValueError(f"{pf} does not contain 'MonitorEnergy' column.")

        # Build histogram
        counts, bin_edges = np.histogram(df["MonitorEnergy"], bins=bins, range=energy_range)
        scaled_counts = counts * scale
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        # Plot original on right subplot
        axes[1].step(bin_centers, counts, where='mid', linewidth=1.5, label=os.path.basename(pf))

        # Plot scaled on left subplot
        axes[0].step(bin_centers, scaled_counts, where='mid', linewidth=1.5, label=f"{os.path.basename(pf)} ×{scale}")

        # Save scaled parquet
        scaled_df = pd.DataFrame({
            "BinLowEdge": bin_edges[:-1],
            "BinHighEdge": bin_edges[1:],
            "Counts": counts,
            "ScaledCounts": scaled_counts
        })
        base, ext = os.path.splitext(pf)
        new_file = f"{base}_scaled{ext}"
        scaled_df.to_parquet(new_file, index=False)
        # print(f"✅ Scaled histogram saved as: {new_file}")

    # Format left subplot (scaled)
    axes[0].set_xlabel("Monitor Energy (arb. units)")
    axes[0].set_ylabel("Counts (scaled)")
    axes[0].set_title("Scaled Monitor Spectra")
    axes[0].grid(True, linestyle="--", alpha=0.5)
    axes[0].legend(fontsize=8)

    # Format right subplot (original)
    axes[1].set_xlabel("Monitor Energy (arb. units)")
    axes[1].set_title("Original Monitor Spectra")
    axes[1].grid(True, linestyle="--", alpha=0.5)
    axes[1].legend(fontsize=8)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # <--- manually specify parquet files and their scaling factors
    parquet_files = [
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/10deg_14kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/12deg_14kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/15deg_13.85kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/17deg_13.85kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/20deg_13.7kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/25deg_13.6kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/35deg_13.25kG_total.parquet",
        "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built/40deg_12.9kG_total.parquet",
    ]
                    #   10     12     15     17     20     25     35     40   
    # scaling_factors = [1.000, 1.676, 1.419, 3.093, 1.536, 3.036, 3.457, 2.627]  # <--- manually set per run 
    scaling_factors = [1.000, 1.676, 1.419, 3.093, 4.607, 3.036, 10.37, 7.882]  # <--- manually set per run this one works

    scale_and_plot_subplots(parquet_files, scaling_factors)

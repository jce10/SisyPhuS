#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_integrator_map(csv_path=None, integrator_dict=None):
    """
    Return a dict mapping run->integrator_value.
    If csv_path is given it expects columns ['Run','Integrator'].
    integrator_dict takes precedence if provided.
    """
    if integrator_dict:
        return dict(integrator_dict)
    if csv_path:
        df = pd.read_csv(csv_path)

        # Drop rows with missing Run or Integrator
        df = df.dropna(subset=["Run", "Counts"])

        # Force numeric conversion, coercing errors to NaN then dropping
        df["Run"] = pd.to_numeric(df["Run"], errors="coerce").astype("Int64")
        df["Counts"] = pd.to_numeric(df["Counts"], errors="coerce")

        df = df.dropna(subset=["Run", "Counts"])

        return dict(zip(df["Run"].astype(int), df["Counts"].astype(float)))

    return {}


def monitor_energies_scaled(dir,
                            run_start,
                            run_end,
                            integrator_map=None,
                            integrator_csv=None,
                            bins=512,
                            energy_range=(0, 4096)):
    """
    Plot MonitorEnergy spectra normalized by beam integrator (counts per integrator unit).
    Parameters:
      dir, run_start, run_end : directory and run range
      integrator_map : dict {run: integrator_value}  OR
      integrator_csv : path to CSV with columns ['Run','Integrator']
      bins, energy_range : histogram settings
    """
    integr_map = load_integrator_map(csv_path=integrator_csv, integrator_dict=integrator_map)

    plt.figure(figsize=(8,6))
    colors = plt.cm.tab20.colors
    color_idx = 0

    for run in range(run_start, run_end + 1):
        file = f"run_{run}.parquet"
        path = os.path.join(dir, file)
        if not os.path.exists(path):
            print(f"⚠️ File not found: {file}, skipping.")
            continue

        df = pd.read_parquet(path)
        if "MonitorEnergy" not in df.columns:
            print(f"⚠️ No 'MonitorEnergy' column in {file}, skipping.")
            continue

        counts, edges = np.histogram(df["MonitorEnergy"], bins=bins, range=energy_range)
        bin_centers = 0.5 * (edges[:-1] + edges[1:])

        I = integr_map.get(run, None)
        if I is None or I == 0:
            print(f"⚠️ No integrator for run {run} or integrator=0; plotting raw counts (not scaled).")
            counts_scaled = counts.astype(float)
            label_note = "raw"
        else:
            counts_scaled = counts.astype(float) / float(I)
            label_note = f"/{I}"

        color = colors[color_idx % len(colors)]
        plt.step(bin_centers, counts_scaled, where='mid', color=color, label=f"Run {run} ({label_note})")
        color_idx += 1

    plt.xlabel("MonitorEnergy")
    plt.ylabel("Counts per integrator unit")
    plt.title(f"MonitorEnergy scaled by integrator: Runs {run_start}–{run_end}")
    # plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


summary_df = monitor_energies_scaled(
    dir="/home/jce18b/Esparza_SPS/2025_06_13C_campaign/built",
    run_start=408,
    run_end=413,
    integrator_csv="BCI_counts.csv",
    bins=512,
    energy_range=(0,4096),
    # output_csv="MonitorEnergy_scaled_summary.csv"
)


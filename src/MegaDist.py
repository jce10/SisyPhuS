import csv
import os
import re
import glob
import numpy as np
import time
import matplotlib.pyplot as plt
import math
import pandas as pd
import textwrap


"""

MegaDist.py
----------------
A module to generate comprehensive angular distribution plots
combining calculated data, old experimental data, and FRESCO theoretical curves.

The two functions that are tested are load_all_fresco and mega_plotter. 

The user only needs to modify the paths in the main() function to point to their
calculated CSV, old experimental ODS file, and FRESCO directory.

J.C. Esparza
Oct. 2025

"""

def load_all_fresco(fresco_dir, theta_max=70):
    fresco_data = {}
    # find all subdirectories
    subdirs = [d for d in sorted(os.listdir(fresco_dir))
               if os.path.isdir(os.path.join(fresco_dir, d))]

    for subdir in subdirs:
        filepath = os.path.join(fresco_dir, subdir, "fort.16")
        if not os.path.exists(filepath):
            continue  # skip if no fort.16

        with open(filepath, "r") as f:
            lines = f.readlines()

        # find all "#  Theta" headers
        headers = [i for i, line in enumerate(lines) if line.strip().startswith("#  Theta")]
        if len(headers) < 2:
            continue  # skip if no second block

        start_idx = headers[1]

        data_list = []
        for line in lines[start_idx+1:]:
            l = line.strip()
            if not l or l.startswith("#") or l.startswith("END"):
                continue
            try:
                nums = [float(x) for x in l.split()]
                data_list.append(nums)
            except ValueError:
                continue

        if not data_list:
            continue

        arr = np.array(data_list)
        if arr.shape[1] >= 2:
            angles, xsecs = arr[:, 0], arr[:, 1]
            mask = angles <= theta_max
            fresco_data[subdir] = (angles[mask], xsecs[mask])

    return fresco_data


def mega_plotter(calc_csv, old_data_ods, fresco_data=None, save_path=None):
    """
    Combine and plot calculated angular distributions, old experimental data,
    and FRESCO theoretical curves into a 3x3 (or dynamic) grid.

    Parameters
    ----------
    calc_csv : str
        Path to the calculated CSV output (with cross sections and errors)
    old_data_ods : str
        Path to the old ODS experimental data file
    fresco_dir : str
        Directory containing FRESCO fort.16 files for each energy state
    save_path : str, optional
        If provided, saves the figure to this path instead of showing it
    """

    # --- 1. Load Esparza CSV ---
    df_esp = pd.read_csv(calc_csv)
    df_esp_angles = df_esp["Angle (deg)"].to_numpy()

    # Extract only (dσ/dΩ) columns (ignore Δσ)
    calc_columns = [col for col in df_esp.columns if "(dσ/dΩ)" in col]

    # --- 2. Load Aslanoglou ODS experimental data ---
    df_aslan = pd.read_excel(old_data_ods, engine="odf", header=None)
    aslan_headers = []
    aslan_blocks = []

    for col in range(0, df_aslan.shape[1], 2):
        # Get header (energy + Jπ)
        energy = str(df_aslan.iloc[0, col]).strip()
        spin   = str(df_aslan.iloc[0, col+1]).strip()
        header = f"{energy} {spin}"

        # Get numerical data below header
        data = df_aslan.iloc[2:, [col, col+1]].copy()
        data = data.apply(pd.to_numeric, errors='coerce').dropna(how='all').reset_index(drop=True)

        if data.shape[1] == 2:
            theta = data.iloc[:, 0].to_numpy()
            xsec = data.iloc[:, 1].to_numpy()
            aslan_headers.append(header)
            aslan_blocks.append((theta, xsec))

    # --- 3. Load FRESCO fort.16 files ---
    # if fresco_data is None and os.path.isdir(fresco_dir):
    #     fresco_data = load_all_fresco(fresco_dir, theta_max=70)



    # --- 4. Determine subplot grid size ---
    n_states = len(calc_columns)
    n_cols = 3
    n_rows = int(np.ceil(n_states / n_cols))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, 4*n_rows), sharex=False, sharey=False)
    axes = axes.flatten()

    # --- 5. Plot each state ---
    for i, col in enumerate(calc_columns):
        ax = axes[i]
        label = col.replace("(dσ/dΩ)", "").strip()

        # Esparza data
        theta_new = df_esp_angles
        xsec_new = df_esp[col].to_numpy()
        yerr = None
        err_col = label + " (Δσ)"
        if err_col in df_esp.columns:
            yerr = df_esp[err_col].to_numpy()

        ax.errorbar(theta_new, xsec_new, yerr=yerr, fmt='o', color='tab:blue', label='This Work')

        # Aslan data (if matching label)
        for hdr, (theta, xsec) in zip(aslan_headers, aslan_blocks):
            if hdr.split()[0] in label:  # partial match by energy
                ax.plot(theta, xsec, 'o', mfc='none', color='tab:red', label='Aslanoglou et al.')

        # FRESCO data (if available)
        if fresco_data:
            for fkey, (theta, xsec) in fresco_data.items():
                # match the FRESCO subdir to the state label in the plot
                if fkey.replace("keV", "").strip() in label.replace("keV", "").strip():
                    ax.plot(theta, xsec, '--', color='tab:green', label=f'FRESCO {fkey}')

        ax.set_yscale('log')
        ax.set_xlabel("θ_lab (deg)")
        ax.set_ylabel("dσ/dΩ (mb/sr)")
        ax.set_title("\n".join(textwrap.wrap(label, width=25)))
        ax.legend(fontsize=9)
        ax.grid(True, which="both", ls="--", alpha=0.5)

    # Hide unused subplots
    for j in range(i+1, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300)
        print(f"✅ Mega plot saved to: {save_path}")
    else:
        plt.show()



# ======= Main ======= #
def main():

    # User-defined paths - CHANGE THESE AS NEEDED
    dir = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign"
    dir_6Lid = dir + "/6Lid"
    dir_dp = dir + "/dp"
    fresco_dir = dir_6Lid + "/9Be6Lid_fresco"
    rxn_name = "9Be_6Li_d_13C"
    rxn_name2 = "12C_dp_13C"
    
    calc_csv = dir_6Lid + "/output_peak_files/" + rxn_name + "_angular_distributions.csv"
    old_data_ods = dir_6Lid + "/output_peak_files/aslan_data.ods"

    # Load FRESCO data once
    fresco_data = load_all_fresco(fresco_dir, theta_max=70)
    
    # Generate mega plot
    mega_plotter(calc_csv, old_data_ods, fresco_data=fresco_data)
    # mega_plotter(calc_csv, old_data_ods=old_data_ods, fresco_data=None) # if no FRESCO data is available/desired


# ----------------------------
if __name__ == "__main__":
    main()
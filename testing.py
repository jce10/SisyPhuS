import csv
import os
import numpy as np
import time
import matplotlib.pyplot as plt
import math
import pandas as pd
from MassLookup import get_nuclear_mass

dir = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign"
dir_6Lid = dir + "/6Lid"
dir_dp = dir + "/dp"

#region
# Physical Constants #

avogadro_number = 6.02214076e23    # atoms/mol
barn_to_cm2 = 1e-24                # 1 barn = 1e-24 cm^2
U_TO_MEV = 931.49410242            # MeV per atomic mass unit (u)
Z = 1                              # proton #'s

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# Equipment Inputs #

# sampling electronics
sampling_rate = 100       # integrator sampling rate in Hz

# beam properties
beam_charge = 1.602e-19     # Coulombs per elementary charge (e)

# detector geometry
solid_angle = 0.00461641607338361    # sr, example value, set from your setup

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# Target Information #

# target thickness
target_thickness = 9.25e-6

# target molar mass
target_molar_mass = 9.012182    # g/mol for 9Be

# target nuclei/cm^2
rho_cm = (target_thickness / target_molar_mass) * avogadro_number # atoms/cm^2

# nuclei per barn
rho_barn = rho_cm * barn_to_cm2  

print(rho_barn, "nuclei/barn")
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#endregion


def lab_to_cm(theta_lab_deg, E_lab, m_A, m_a, m_b, m_B, Q):
    """
    Calculates conversion Jacobians for angles and differential cross-sections
    between the lab and center-of-mass (CM) frames for two-body reactions.

    Parameters
    ----------
    theta_lab_deg : float or ndarray
        Lab angle in degrees.
    E_lab : float
        Beam energy (MeV).
    m_proj : float
        Projectile mass (MeV/c^2).
    m_targ : float
        Target mass (MeV/c^2).
    m_eject : float
        Ejectile mass (MeV/c^2).
    m_recoil : float
        Recoil mass (MeV/c^2).
    Q : float
        Reaction Q-value (MeV).

    Returns
    -------
    theta_cm_deg : float or ndarray
        CM angle (degrees).
    """

    E_lab = 32 # MeV
    Q = (m_A + m_a) - (m_b + m_B)  # MeV
    # gamma 


    theta_lab = np.radians(theta_lab_deg)





    # tangent relation (standard two-body kinematics)
    tan_theta_cm = (np.sin(theta_lab) / 
                   (np.cos(theta_lab) + (p_in / p_out)))
    theta_cm = np.arctan(tan_theta_cm)

    return np.degrees(theta_cm)


def BCI_handler(file_path):
    """
    Reads a BCI_totals.txt file with columns:
    angle | total | scale
    Returns three lists: angles, counts, scales
    """
    BCI_angles = []
    BCI_counts = []
    BCI_scales = []

    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Skip header line
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue  # skip blank lines
        # Split by '|' and remove extra whitespace
        parts = [p.strip() for p in line.split('|')]
        if len(parts) != 3:
            continue  # skip malformed lines

        try:
            angle = float(parts[0])
            counts = float(parts[1])
            scale = float(parts[2])
        except ValueError:
            continue  # skip lines that cannot be converted

        BCI_angles.append(angle)
        BCI_counts.append(counts)
        BCI_scales.append(scale)

    return BCI_angles, BCI_counts, BCI_scales


    # # 12C(d,p)13C
    # BCI_angles_dp = []
    # BCI_hits_dp = []
    # BCI_scale_dp = []

    # with open(dir_dp + "/BCI_totals.txt") as f:
    #     stripped = [s.strip() for s in f]
    #     for line in stripped:
    #         angle, hits, scale = line.split()
    #         BCI_angles_dp.append(angle)              # store angle label
    #         BCI_hits_dp.append(float(hits))          # store counts
    #         BCI_scale_dp.append(float(scale))        # store scale
    # return BCI_angles_dp, BCI_hits_dp, BCI_scale_dp


def parse_input_peaks(file_path):
    """
    parses an ODS spreadsheet with pairs of columns.

    """
    
    df = pd.read_excel(file_path, engine="odf", header=None)
    
    energy_labels = []
    volume_blocks = []
    uncertainty_blocks = []

    # Step through columns in pairs: (0,1), (2,3), ...
    for col in range(0, df.shape[1], 2):
        # Read the excitation energy and spin-parity label (first row)
        energy = str(df.iloc[0, col]).strip()
        spin   = str(df.iloc[0, col+1]).strip()
        header = f"{energy} {spin}"

        # Store label for reference
        energy_labels.append(header)

        # Get numerical data starting from row 2 onward
        data = df.iloc[2:, [col, col+1]].copy()
        data = data.apply(pd.to_numeric, errors='coerce')
        data = data.dropna(how='all').reset_index(drop=True)

        # Split into separate lists
        volumes = data.iloc[:, 0].tolist()
        uncertainties = data.iloc[:, 1].tolist()

        volume_blocks.append(volumes)
        uncertainty_blocks.append(uncertainties)

    # Return all three: energy headers, volumes, and uncertainties
    return energy_labels, volume_blocks, uncertainty_blocks


def x_sec_calc(BCI_hits, BCI_scale, volume_list): 
    """
    Returns a list of diff. cross-sections (mb/sr) for a given peak.

    """

    j=0
    cross_section_vals = []
    for i in BCI_hits:
        
        Q_beam = (i * 1E-9 * BCI_scale[j])/(sampling_rate)
        N_beam = Q_beam / beam_charge

        dsigma_domega = (volume_list[j] * 1000)/(N_beam * rho_barn * solid_angle)  # cross-sec in mb/sr
        cross_section_vals.append(dsigma_domega)

        j +=1

    return cross_section_vals


def error_handler(x_sec, vol_list, vol_err_list, BCI_hits):
    """
    Returns a list of errors that correspond to the list of cross-sections
    generated for a given peak.

    """
    errs = []
    n = min(len(x_sec), len(vol_list), len(vol_err_list), len(BCI_hits))  # sync to shortest
    
    for i in range(n):
        err_BCI = 0.20 * BCI_hits[i]   # 20% relative error on BCI
        if vol_list[i] == 0.0 or BCI_hits[i] == 0.0:
            deltaX = 0.0
        else:
            frac_err = (vol_err_list[i] / vol_list[i])**2 + (err_BCI / BCI_hits[i])**2
            deltaX = np.sqrt(frac_err) * x_sec[i]
        errs.append(deltaX)
    
    return errs


def file_writer_combined(blocks, BCI_angle, BCI_counts, BCI_scale, rxn_name, output_dir="."):
    """
    Combines all angular distributions into a single CSV file.

    Parameters
    ----------
    blocks : list[dict]
        Parsed data blocks from parse_input_peaks()
    BCI_angle : list[float]
        List of lab angles (deg)
    BCI_counts : list[float]
        Beam integrator counts
    BCI_scale : list[float]
        Scale factors for beam integrator
    rxn_name : str
        Reaction name (used for output filename)
    output_dir : str
        Directory to save output file
    """

    master_df = pd.DataFrame({"Angle (deg)": BCI_angle})

    for block in blocks:
        energy_label = block["header"]
        volume_list = block["volumes"]
        vol_err_list = block["uncertainties"]

        # Calculate cross sections and errors
        xsec = x_sec_calc(BCI_counts, BCI_scale, volume_list)
        xsec_err = error_handler(xsec, volume_list, vol_err_list, BCI_counts)

        # Add two columns to master DataFrame
        master_df[f"{energy_label} (dσ/dΩ)"] = xsec
        master_df[f"{energy_label} (Δσ)"] = xsec_err

    # Define output path
    filename = f"{rxn_name}_angular_distributions.csv"
    output_path = os.path.join(output_dir, filename)

    # Save combined CSV
    master_df.to_csv(output_path, index=False)
    print(f"✅ Combined CSV saved: {output_path}")


def plot_angular_distributions(csv_file, save_path=None):
    """
    Reads a CSV of angular distributions and plots each excitation state
    as a subplot with error bars.
    
    Parameters
    ----------
    csv_file : str
        Path to the CSV file with columns: "Angle (deg)", "E1 (dσ/dΩ)", "E1 (Δσ)", ...
    save_path : str, optional
        If provided, saves the figure to this path.
    """
    df = pd.read_csv(csv_file)

    # Extract angles
    angles = df.iloc[:, 0].values

    # Extract all excitation states (columns are in pairs: cross section & error)
    state_cols = [col for col in df.columns if "(dσ/dΩ)" in col]
    err_cols   = [col for col in df.columns if "(Δσ)" in col]

    # Group states in sets of 3 for 1x3 subplots
    n_states = len(state_cols)
    n_groups = math.ceil(n_states / 3)

    for g in range(n_groups):
        start = g * 3
        end = min(start + 3, n_states)
        cols_group = state_cols[start:end]
        errs_group = err_cols[start:end]

        fig, axs = plt.subplots(1, len(cols_group), figsize=(5*len(cols_group), 4), sharey=True)
        if len(cols_group) == 1:
            axs = [axs]  # Ensure axs is always iterable

        for ax, col, err_col in zip(axs, cols_group, errs_group):
            ax.errorbar(angles, df[col], yerr=df[err_col], fmt='o', capsize=3)
            ax.set_xlabel("Lab Angle (deg)")
            ax.set_ylabel(r"$d\sigma/d\Omega$ (mb/sr)")
            ax.set_yscale("log")
            ax.set_title(col, fontsize=10)
            ax.grid(True)

        plt.tight_layout()
        plt.show()



def main():
    
    rxn_name = "9Be_6Li_d_13C"
    file_path = dir_6Lid + "/input_peaks/6Lid_inputs.ods"
    
    # --- 1. Parse input peaks ---
    energy_labels, volume_list, vol_err_list = parse_input_peaks(file_path)

    # --- 2. Make sure output dir exists ---
    output_dir = os.path.join(dir_6Lid, "output_peak_files")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # --- 3. Read BCI info ---
    BCI_angle, BCI_counts, BCI_scale = BCI_handler(dir_6Lid + "/BCI_totals.txt")

    # --- 4. Prepare "blocks" structure for file_writer_combined ---
    # file_writer_combined expects a list of dicts with keys: header, volumes, uncertainties
    blocks = []
    for i, label in enumerate(energy_labels):
        blocks.append({
            "header": label,
            "volumes": volume_list[i],
            "uncertainties": vol_err_list[i]
        })

    # --- 5. Calculate cross sections & write combined CSV ---
    file_writer_combined(
        blocks=blocks,
        BCI_angle=BCI_angle,
        BCI_counts=BCI_counts,
        BCI_scale=BCI_scale,
        rxn_name=rxn_name,
        output_dir=dir_6Lid + "/output_peak_files"
    )

    # --- 6. Plot distributions ---
    plot_angular_distributions(dir_6Lid + "/output_peak_files/" + rxn_name + "_angular_distributions.csv", rxn_name)

# ----------------------------
if __name__ == "__main__":
    main()





import csv
import os
import re
import glob
import numpy as np
import time
import matplotlib.pyplot as plt
import math
import pandas as pd
import polars as pl
import textwrap
from MassLookup import get_nuclear_mass

"""
AngDistCalc.py
---------------

A module for calculating angular distributions in nuclear reactions.

User provided inputs include: 

User inputs peak volume and uncertainty data from an ODS spreadsheet,
and beam integrator (BCI) data from a text file. 

"""

# ======= Reaction and Target Info ======= #
#region
# Physical Constants #

avogadro_number = 6.02214076e23    # atoms/mol
barn_to_cm2 = 1e-24                # 1 barn = 1e-24 cm^2
U_TO_MEV = 931.49410242            # MeV per atomic mass unit (u)
Z = 3                              # proton #

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# Equipment Inputs #

# sampling electronics
sampling_rate = 100       # integrator sampling rate in Hz

# beam properties
beam_charge = Z*1.602e-19     # Coulombs per elementary charge (e)

# detector geometry
solid_angle = 0.00461641607338361    # sr, example value, set from your setup

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# Target Information #

# target thickness
target_thickness = 9.25e-5

# target molar mass
target_molar_mass = 9.012182    # g/mol for 9Be

# target nuclei/cm^2
rho_cm = (target_thickness / target_molar_mass) * avogadro_number # atoms/cm^2

# nuclei per barn
rho_barn = rho_cm * barn_to_cm2  

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#endregion

# not finished 10/06
def lab_to_cm(theta_lab_deg, E_lab, m_A, m_a, m_b, m_B):
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

    # Q-value of rxn (MeV)
    Q = (m_A + m_a) - (m_b + m_B)
    
    # calculating gamma factor
    g_numerator = (m_a * m_b * E_lab)/(m_A * m_B)
    g_denominator = (E_lab + Q  + Q*m_a/m_A)
    gamma  = np.sqrt(g_numerator / g_denominator)

    theta_lab_rad = np.radians(theta_lab_deg)
    theta_CM_rad = np.acos(-gamma*np.sin(theta_lab_rad)**2 +np.cos(theta_lab_rad))
    theta_cm_deg = np.degrees(theta_CM_rad)

    # Jacobian for lab -> cm
    j_numerator = 1 - (gamma**2 * np.sin(theta_lab_rad)**2)
    j_denominator = gamma*np.cos(theta_lab_deg) + np.sqrt(1 - (gamma**2 * np.sin(theta_lab_rad)**2))
    jacobian = (j_numerator / j_denominator)


    return Q, theta_cm_deg, jacobian
  

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


def error_handler(x_sec, volume_list, volume_err_list, BCI_hits, rel_err_BCI=0.10):
    """
    Compute symmetric uncertainties (±1σ) on differential cross sections (mb/sr).

    Parameters
    ----------
    x_sec : list or array
        Calculated cross-section values (mb/sr).
    volume_list : list or array
        Integrated peak volumes (arbitrary units).
    volume_err_list : list or array
        Uncertainties on integrated peak volumes.
    BCI_hits : list or array
        Beam integrator counts (arbitrary units).
    rel_err_BCI : float
        Relative error (fractional) on BCI, default 10%.
        checked with picoampmeter directly into integrator - JCE 10/2025

    Returns
    -------
    errs : list
        List of symmetric ± errors corresponding to each x_sec value.
    """

    errs = []
    for xs, vol, vol_err, bci in zip(x_sec, volume_list, volume_err_list, BCI_hits):
        # handle edge cases safely
        if vol <= 0 or bci <= 0 or xs <= 0:
            errs.append(0.0)
            continue

        # relative error propagation in quadrature
        rel_err_vol = vol_err / vol
        rel_err_bci = rel_err_BCI  # 20% relative uncertainty on BCI
        total_rel_err = np.sqrt(rel_err_vol**2 + rel_err_bci**2)

        errs.append(xs * total_rel_err)

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



# ======= USER EDITS HERE ======= #

# ======= Main ======= #
def main():
    
    # root directory
    dir = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign"

    # jce differect rxn dirs
    dir_6Lid = dir + "/6Lid"
    dir_dp = dir + "/dp"
    
    # ESSENTIAL TO RUNNING
    rxn_name = "9Be_6Li_d_13C"
    file_path = dir_6Lid + "/input_peaks/6Lid_inputs_shapira.ods"
    

    # ~~~~~~~~~~~~~~~~~~~~~~~~ begin workflow ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
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

    #reaction info
    masses = []
    for nuc in ["6Li", "9Be", "2H", "13C"]:
        m = get_nuclear_mass(nuc)
        masses.append(m)
        # print(f"{nuc}: {m:.3f} MeV/c^2") #optional print

    Q_val, theta_cm, xsec_jacob = lab_to_cm(BCI_angle, 32, masses[0], masses[1], masses[2], masses[3])




# ----------------------------
if __name__ == "__main__":
    main()






# AngDistCalc.py
# Modernized version using YAML config + Polars
# --------------------------------------------------

import os
import yaml
import numpy as np
import polars as pl
import pandas as pd
from MassLookup import get_nuclear_mass


# --------------------------------------------------
#  Load User Configuration
# --------------------------------------------------
def load_config():
    with open("config/config.yaml", "r") as f:
        return yaml.safe_load(f)


# --------------------------------------------------
#  Physics Functions
# --------------------------------------------------
def lab_to_cm(theta_lab_deg, E_lab, m_A, m_a, m_b, m_B):
    Q = (m_A + m_a) - (m_b + m_B)

    g_num = (m_a * m_b * E_lab) / (m_A * m_B)
    g_den = (E_lab + Q + Q * m_a / m_A)
    gamma = np.sqrt(g_num / g_den)

    theta_lab_rad = np.radians(theta_lab_deg)
    theta_CM_rad = np.acos(-gamma * np.sin(theta_lab_rad)**2 + np.cos(theta_lab_rad))
    theta_cm_deg = np.degrees(theta_CM_rad)

    j_num = 1 - (gamma**2 * np.sin(theta_lab_rad)**2)
    j_den = gamma * np.cos(theta_lab_rad) + np.sqrt(1 - (gamma**2 * np.sin(theta_lab_rad)**2))
    jacobian = j_num / j_den

    return Q, theta_cm_deg, jacobian


# --------------------------------------------------
#  Read BCI
# --------------------------------------------------
def BCI_handler(file_path):
    df = (
        pl.read_csv(
            file_path,
            separator="|",
            has_header=True,
            ignore_errors=True
        )
        .select([
            pl.col("angle").cast(pl.Float64),
            pl.col("total").cast(pl.Float64),
            pl.col("scale").cast(pl.Float64)
        ])
    )
    return (
        df["angle"].to_list(),
        df["total"].to_list(),
        df["scale"].to_list()
    )


# --------------------------------------------------
#  Parse Peak Input File
# --------------------------------------------------
def parse_input_peaks(file_path):
    # Read ODS using pandas (odf engine), convert → Polars
    pdf = pd.read_excel(file_path, engine="odf", header=None)
    df = pl.from_pandas(pdf)

    energy_labels = []
    volume_blocks = []
    uncertainty_blocks = []

    ncols = df.width()

    for col in range(0, ncols, 2):
        energy = str(df.item(0, col)).strip()
        spin   = str(df.item(0, col + 1)).strip()
        header = f"{energy} {spin}"

        energy_labels.append(header)

        # Extract data rows
        block = (
            df.slice(2)     # drop first two rows
              .select([pl.col(col), pl.col(col+1)])
              .cast(pl.Float64, strict=False)
              .drop_nulls(subset=[col])   # drop rows where volume is null
        )

        volume_blocks.append(block.select(col).to_list())
        uncertainty_blocks.append(block.select(col+1).to_list())

    return energy_labels, volume_blocks, uncertainty_blocks


# --------------------------------------------------
#  Cross-section Calculation
# --------------------------------------------------
def x_sec_calc(BCI_hits, BCI_scale, volume_list, cfg):
    cross = []
    Z = cfg["reaction"]["projectile_Z"]
    beam_charge = Z * 1.602e-19

    rho_barn = cfg["target"]["rho_per_barn"]
    sampling_rate = cfg["equipment"]["sampling_rate"]
    solid_angle = cfg["detector"]["solid_angle"]

    for i, vol in enumerate(volume_list):
        Q_beam = (BCI_hits[i] * 1e-9 * BCI_scale[i]) / sampling_rate
        N_beam = Q_beam / beam_charge
        dsdo = (vol * 1_000) / (N_beam * rho_barn * solid_angle)
        cross.append(dsdo)

    return cross


# --------------------------------------------------
#  Uncertainty Propagation
# --------------------------------------------------
def error_handler(x_sec, vol, vol_err, BCI_hits):
    errs = []
    rel_err_BCI = 0.10

    for xs, v, dv, bci in zip(x_sec, vol, vol_err, BCI_hits):
        if v <= 0 or bci <= 0 or xs <= 0:
            errs.append(0.0)
            continue
        rel_err = np.sqrt((dv/v)**2 + rel_err_BCI**2)
        errs.append(xs * rel_err)

    return errs


# --------------------------------------------------
#  CSV Writer
# --------------------------------------------------
def file_writer_combined(blocks, BCI_angle, BCI_counts, BCI_scale, rxn_name, output_dir, cfg):

    cols = {"Angle (deg)": BCI_angle}
    for block in blocks:
        header = block["header"]
        vols   = block["volumes"]
        verrs  = block["uncertainties"]

        xsec = x_sec_calc(BCI_counts, BCI_scale, vols, cfg)
        xerr = error_handler(xsec, vols, verrs, BCI_counts)

        cols[f"{header} (dσ/dΩ)"] = xsec
        cols[f"{header} (Δσ)"] = xerr

    df = pl.DataFrame(cols)

    output_path = os.path.join(output_dir, f"{rxn_name}_angular_distributions.csv")
    df.write_csv(output_path)

    print(f"✅ Saved: {output_path}")


# --------------------------------------------------
#  Main Pipeline
# --------------------------------------------------
def main():
    # load that bitch
    cfg = load_config()

    # select rxn
    rxn_key = cfg["selected_reaction"]
    rxn = cfg["reactions"][rxn_key]

    # Root paths from config
    root = cfg["directories"]["root_dir"]
    rxndir = os.path.join(root, rxn["subdir"])

    # input paths
    peaks_path = os.path.join(rxndir, cfg["directories"]["peak_file"])
    bci_path   = os.path.join(rxndir, cfg["directories"]["bci_file"])

    # Create output directory
    outdir = os.path.join(rxndir, "output_peak_files")
    os.makedirs(outdir, exist_ok=True)

    # Parse peak data
    labels, volumes, errors = parse_input_peaks(peaks_path)

    # Read BCI data
    BCI_angle, BCI_hits, BCI_scale = BCI_handler(bci_path)

    # Build blocks
    blocks = [
        {"header": labels[i], "volumes": volumes[i], "uncertainties": errors[i]}
        for i in range(len(labels))
    ]

    # Write combined output
    file_writer_combined(
        blocks,
        BCI_angle,
        BCI_hits,
        BCI_scale,
        cfg["reaction"]["name"],
        outdir,
        cfg
    )

    # Reaction mass inputs
    masses = [get_nuclear_mass(n) for n in cfg["reaction"]["mass_order"]]

    Q, theta_cm, jac = lab_to_cm(
        BCI_angle,
        cfg["reaction"]["beam_energy"],
        masses[0], masses[1], masses[2], masses[3]
    )


# --------------------------------------------------
if __name__ == "__main__":
    main()


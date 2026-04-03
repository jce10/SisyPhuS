from __future__ import annotations

import polars as pl

from sisyphus.config import load_config
from sisyphus.BCI import load_bci
from sisyphus.ParseInputPeaks import parse_input_peaks_ods
from sisyphus.XSec import calc_rho_barn, add_xsec_columns
from sisyphus.XSecError import add_xsec_uncertainty
from sisyphus.XSecFileWriter import write_angular_distributions_long


def main():
    # 1) Load config
    
    # # (6Li,d) config
    # cfg = load_config("config/config_6Li.yaml")

    # (d,p) configs
    cfg = load_config("config/config_dpLF.yaml")
    # cfg = load_config("config/config_dpHF.yaml")

    # 2) Load BCI -> DF: angle,counts,scale
    bci_df = load_bci(cfg.paths.bci_file).with_row_index("index")

    # 3) Load peaks (ODS) -> tidy DF: state,index,volume,uncertainty
    peaks_df = parse_input_peaks_ods(cfg.paths.peak_file)
 
    # 4) Join by row index (angle order)
    combined = peaks_df.join(bci_df, on="index", how="left")

    # 5) Target nuclei density in barns
    rho_barn = calc_rho_barn(
        cfg.target_thickness_g_cm2,
        cfg.target_molar_mass_g_mol,
        cfg.constants["avogadro"],
        cfg.constants["barn_to_cm2"],
    )

    # 6) Compute xsec + uncertainty (vectorized)
    combined = add_xsec_columns(
        combined,
        sampling_rate_hz=cfg.sampling_rate_Hz,
        beam_Z=cfg.beam_Z,
        rho_barn=rho_barn,
        solid_angle_sr=cfg.solid_angle_sr,
    )
    combined = add_xsec_uncertainty(
        combined,
        rel_err_bci=0.10,  # measured beam integrator systematic
    )

    # 7) Write outputs
    write_angular_distributions_long(
        combined,
        rxn_name=cfg.reaction.name,
        output_dir=cfg.paths.output_subdir,
    )

    print("✅ Done.")


if __name__ == "__main__":
    main()


from __future__ import annotations

from pathlib import Path
import polars as pl

from sisyphus.config import load_config
from sisyphus.LoadFRESCO import load_all_fresco_long, load_fresco_data_fort200, load_all_fresco_fort200_long
from sisyphus.MegaDistLong import mega_plotter_long


def find_calc_csv(output_subdir: str | Path, pattern: str = "*angular_distributions*.csv") -> Path:
    output_subdir = Path(output_subdir)
    matches = sorted(
        output_subdir.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not matches:
        raise FileNotFoundError(
            f"No angular distribution CSV found in {output_subdir}"
        )

    return matches[0]


def main() -> None:
    # 1) Load config
    # # (6Li,d) config
    cfg = load_config("config/config_6Li.yaml")

    # (d,p) configs
    # cfg = load_config("config/config_dpLF.yaml")
    # cfg = load_config("config/config_dpHF.yaml")

    # 2) Locate calculated CSV
    calc_csv = find_calc_csv(cfg.paths.output_subdir)

    # 3) Load FRESCO tidy dataframe
    fresco_df = load_all_fresco_long(
        cfg.paths.fresco_dir,
        theta_max=180.0,
    )
    # print("fresco directory: ",cfg.paths.fresco_dir)

    # fresco_df = load_all_fresco_fort200_long(
    #     cfg.paths.fresco_dir,
    #     theta_max=180.0,
    # )

    # print(fresco_df)
    # print(f"FRESCO rows: {fresco_df.height}")
    # 4) Plot
    mega_plotter_long(
        calc_csv,
        old_data_ods=cfg.paths.aslan_dir,
        fresco_df=fresco_df,
        save_path=None,  # could add config key later if desired
        n_cols=3,
        theta_max=70.0,
        logy=True,
    )

    print("✅ Mega plot complete.")


if __name__ == "__main__":
    main()
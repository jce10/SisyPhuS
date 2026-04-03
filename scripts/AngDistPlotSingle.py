from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

from sisyphus.config import load_config
from sisyphus.LoadFRESCO import load_all_fresco_long
from sisyphus.MegaDistLong import plot_single_long


def find_calc_csv(output_subdir: str | Path, pattern: str = "*angular_distributions*.csv") -> Path:
    output_subdir = Path(output_subdir)
    matches = sorted(output_subdir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(f"No files matching '{pattern}' found in {output_subdir}")
    return matches[0]


def list_states(calc_csv: str | Path, theta_max: float | None = None) -> None:
    df = pl.read_csv(calc_csv).with_columns([
        pl.col("state").cast(pl.Utf8),
        pl.col("angle").cast(pl.Float64, strict=False),
        pl.col("xsec").cast(pl.Float64, strict=False),
    ]).drop_nulls(["state", "angle", "xsec"])

    if theta_max is not None:
        df = df.filter(pl.col("angle") <= float(theta_max))

    # Summary per state: npts + angle range
    summary = (
        df.group_by("state")
          .agg([
              pl.len().alias("npts"),
              pl.min("angle").alias("theta_min"),
              pl.max("angle").alias("theta_max"),
          ])
          .sort("state")
    )

    rows = summary.iter_rows(named=True)
    print("\nAvailable states:\n")
    for i, r in enumerate(rows):
        print(f"[{i:02d}] {r['state']}   (n={r['npts']}, θ={r['theta_min']:.1f}–{r['theta_max']:.1f} deg)")
    print("")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot a single angular distribution from long-format CSV.")
    # parser.add_argument("--config", default="config/config_6Li.yaml")
    # parser.add_argument("--config", default="config/config_dpHF.yaml")
    parser.add_argument("--config", default="config/config_dpLF.yaml")
    parser.add_argument("--list", action="store_true", help="List available states (with indices) and exit.")
    parser.add_argument("--state", default=None, help="Exact (or substring) state label, e.g. '10753 keV 7/2-'")
    parser.add_argument("--match", default=None, help="Substring match, e.g. '10753' or '7/2-'")
    parser.add_argument("--index", type=int, default=None, help="Index in sorted unique state list (0-based)")
    parser.add_argument("--theta-max", type=float, default=70.0)
    parser.add_argument("--save", default=None, help="Optional output image path")
    args = parser.parse_args()

    cfg = load_config(args.config)
    paths = cfg.paths

    calc_csv = find_calc_csv(paths.output_subdir)

    # If user just wants list, do it and exit
    if args.list:
        list_states(calc_csv, theta_max=args.theta_max)
        return

    fresco_df = load_all_fresco_long(paths.fresco_dir, theta_max=args.theta_max)

    resolved = plot_single_long(
        calc_csv,
        state=args.state,
        match=args.match,
        state_index=args.index,
        old_data_ods=paths.aslan_dir,
        fresco_df=fresco_df,
        save_path=args.save,
        theta_max=args.theta_max,
        logy=True,
    )

    print(f"✅ Plotted state: {resolved}")


if __name__ == "__main__":
    main()
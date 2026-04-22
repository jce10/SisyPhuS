from __future__ import annotations

from pathlib import Path
import pandas as pd
import polars as pl

def parse_old_data_ods_split_headers(file_path: str | Path) -> pl.DataFrame:
    """
    
    Read one .ods file containing previous experimental data
    stored as repeating pairs of columns:
      [state_tag, blank, state_tag, blank, ...]
      [theta, xsec, theta, xsec, ...]
      [data...]

    Returns one long Polars DataFrame with columns:
      angle, xsec, state, source

    """
    raw = pd.read_excel(file_path, engine="odf", header=None)

    frames = []
    ncols = raw.shape[1]

    for i in range(0, ncols, 2):
        ex_energy = raw.iloc[0, i]
        jpi = raw.iloc[0, i + 1] if i + 1 < ncols else None

        if pd.isna(ex_energy) or pd.isna(jpi):
            continue

        state_tag = f"{str(ex_energy).strip()} | {str(jpi).strip()}"

        sub = raw.iloc[2:, [i, i + 1]].copy()
        sub.columns = ["angle", "xsec"]
        sub = sub.reset_index(drop=True)

        sub["angle"] = pd.to_numeric(sub["angle"], errors="coerce")
        sub["xsec"] = pd.to_numeric(sub["xsec"], errors="coerce")
        sub = sub.dropna(subset=["angle", "xsec"])

        sub["state"] = state_tag

        frames.append(pl.from_pandas(sub))

    if not frames:
        return pl.DataFrame(schema={
            "state": pl.String,
            "angle": pl.Float64,
            "xsec": pl.Float64,
        })

    return pl.concat(frames, how="vertical").select(["state", "angle", "xsec"])
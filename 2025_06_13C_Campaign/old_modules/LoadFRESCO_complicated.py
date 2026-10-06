from __future__ import annotations

from pathlib import Path
from typing import Dict

import polars as pl


def load_all_fresco_long(
    fresco_dir: str | Path,
    *,
    theta_max: float = 180.0,
    fort_name: str = "fort.16",
    theta_header_prefix: str = "#  Theta",
    block_index: int = 1,
) -> pl.DataFrame:
    """
    Load FRESCO angular distributions from subdirectories into ONE long/tidy DataFrame.

    Each subdirectory is treated as a "state" label.
    Parses the Nth theta block (default: second block, block_index=1) like your original code.

    Returns a DataFrame with columns:
        state: str (subdirectory name)
        theta_deg: float
        xsec: float

    Filtered to theta_deg <= theta_max.
    """
    fresco_dir = Path(fresco_dir)
    if not fresco_dir.is_dir():
        return pl.DataFrame(
            {"state": [], "theta_deg": [], "xsec": []},
            schema={"state": pl.Utf8, "theta_deg": pl.Float64, "xsec": pl.Float64},
        )

    frames: list[pl.DataFrame] = []

    for subdir in sorted([p for p in fresco_dir.iterdir() if p.is_dir()]):
        filepath = subdir / fort_name
        if not filepath.exists():
            continue

        try:
            lines = filepath.read_text().splitlines()
        except Exception:
            continue

        headers = [i for i, line in enumerate(lines) if line.strip().startswith(theta_header_prefix)]
        if len(headers) <= block_index:
            continue

        start_idx = headers[block_index] + 1

        theta_vals: list[float] = []
        xsec_vals: list[float] = []

        for line in lines[start_idx:]:
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("END"):
                continue

            parts = s.split()
            if len(parts) < 2:
                continue

            try:
                theta = float(parts[0])
                xsec = float(parts[1])
            except ValueError:
                continue

            if theta <= theta_max:
                theta_vals.append(theta)
                xsec_vals.append(xsec)

        if not theta_vals:
            continue

        frames.append(
            pl.DataFrame(
                {
                    "state": [subdir.name] * len(theta_vals),
                    "theta_deg": theta_vals,
                    "xsec": xsec_vals,
                },
                schema={"state": pl.Utf8, "theta_deg": pl.Float64, "xsec": pl.Float64},
            )
        )

    if not frames:
        return pl.DataFrame(
            {"state": [], "theta_deg": [], "xsec": []},
            schema={"state": pl.Utf8, "theta_deg": pl.Float64, "xsec": pl.Float64},
        )

    return pl.concat(frames, how="vertical").sort(["state", "theta_deg"])


def load_all_fresco_dict(
    fresco_dir: str | Path,
    *,
    theta_max: float = 180.0,
    fort_name: str = "fort.16",
    theta_header_prefix: str = "#  Theta",
    block_index: int = 1,
) -> Dict[str, pl.DataFrame]:
    """
    Convenience wrapper: returns a dict[state -> DataFrame] using load_all_fresco_long().

    """
    df = load_all_fresco_long(
        fresco_dir,
        theta_max=theta_max,
        fort_name=fort_name,
        theta_header_prefix=theta_header_prefix,
        block_index=block_index,
    )

    out: Dict[str, pl.DataFrame] = {}
    if df.height == 0:
        return out

    for state in df.get_column("state").unique().to_list():
        out[str(state)] = df.filter(pl.col("state") == state).select(["theta_deg", "xsec"]).sort("theta_deg")

    return out



def load_fresco_data_fort200(
    filepath: str | Path,
    *,
    theta_max: float | None = None,
    state: str | None = None,
) -> pl.DataFrame:
    """
    Load a single FRESCO fort.20x-style file (already split section).
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    if not filepath.is_file():
        raise IsADirectoryError(f"Expected a file, got directory: {filepath}")

    theta_vals: list[float] = []
    xsec_vals: list[float] = []

    lines = filepath.read_text().splitlines()

    for line in lines:
        s = line.strip()

        if not s or s.startswith("#") or s.startswith("END"):
            continue

        parts = s.split()
        if len(parts) < 2:
            continue

        try:
            theta = float(parts[0])
            xsec = float(parts[1])
        except ValueError:
            continue

        if theta_max is None or theta <= theta_max:
            theta_vals.append(theta)
            xsec_vals.append(xsec)

    if not theta_vals:
        base = {
            "theta_deg": [],
            "xsec": [],
        }
        if state is not None:
            base["state"] = []
            return pl.DataFrame(
                base,
                schema={"theta_deg": pl.Float64, "xsec": pl.Float64, "state": pl.Utf8},
            )
        return pl.DataFrame(
            base,
            schema={"theta_deg": pl.Float64, "xsec": pl.Float64},
        )

    df = pl.DataFrame(
        {
            "theta_deg": theta_vals,
            "xsec": xsec_vals,
        },
        schema={"theta_deg": pl.Float64, "xsec": pl.Float64},
    ).sort("theta_deg")

    if state is not None:
        df = df.with_columns(pl.lit(state).alias("state"))

    return df


def load_all_fresco_fort200_long(
    fresco_dir: str | Path,
    *,
    theta_max: float | None = None,
    pattern: str = "fort.20*",
) -> pl.DataFrame:
    """
    Load all split fort.20x files in a directory into one long/tidy DataFrame.

    Returns columns:
        state, theta_deg, xsec

    Uses filename as the default state label.
    """
    fresco_dir = Path(fresco_dir)

    if not fresco_dir.exists():
        raise FileNotFoundError(f"Directory not found: {fresco_dir}")
    if not fresco_dir.is_dir():
        raise NotADirectoryError(f"Expected a directory, got file: {fresco_dir}")

    frames: list[pl.DataFrame] = []

    for filepath in sorted(fresco_dir.rglob(pattern)):
        if not filepath.is_file():
            continue

        state = filepath.parent.name
        df = load_fresco_data_fort200(
            filepath,
            theta_max=theta_max,
            state=state,
        )

        if df.height > 0:
            frames.append(df)

    if not frames:
        return pl.DataFrame(
            {"state": [], "theta_deg": [], "xsec": []},
            schema={"state": pl.Utf8, "theta_deg": pl.Float64, "xsec": pl.Float64},
        )

    return pl.concat(frames, how="vertical").select(["state", "theta_deg", "xsec"])
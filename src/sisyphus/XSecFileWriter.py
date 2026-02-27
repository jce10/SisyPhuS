from __future__ import annotations

from pathlib import Path
import polars as pl


def write_angular_distributions_long(
    df: pl.DataFrame,
    *,
    rxn_name: str,
    output_dir: str | Path,
    filename: str | None = None,
) -> Path:
    """
    Writes a tidy/long CSV with columns:
        angle, state, xsec_mb_sr, xsec_err_mb_sr
    """
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = f"{rxn_name}_angular_distributions_long.csv"

    outpath = output_dir / filename

    out = (
        df.select(["angle", "state", "xsec_mb_sr", "xsec_err_mb_sr"])
          .sort(["state", "angle"])
    )

    out.write_csv(outpath)
    print(f"✅ Combined CSV saved: {outpath}")
    return outpath
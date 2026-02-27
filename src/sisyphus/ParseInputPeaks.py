from __future__ import annotations

from pathlib import Path
import pandas as pd
import polars as pl


def parse_input_peaks_ods(file_path: str | Path) -> pl.DataFrame:
    """
    Parse an ODS spreadsheet arranged as paired columns:
        col0=volume, col1=uncertainty for state 1
        col2=volume, col3=uncertainty for state 2
        ...

    Row 0 contains headers:
        [energy_label, spin_parity] per pair
    Row 1 is ignored (matches your original behavior)
    Data starts at row 2.

    Returns
    -------
    Polars DataFrame (tidy/long) with columns:
        state        : str   (e.g., "7.68 3/2+")
        index        : i64   (row index within that state block, starting 0)
        volume       : f64
        uncertainty  : f64
    """

    file_path = Path(file_path).expanduser().resolve()

    # Pandas is the most reliable way to read ODS right now.
    pdf = pd.read_excel(file_path, engine="odf", header=None)

    ncols = pdf.shape[1]
    rows = []

    for col in range(0, ncols, 2):
        if col + 1 >= ncols:
            break  # odd last column, ignore

        energy = str(pdf.iloc[0, col]).strip()
        spin = str(pdf.iloc[0, col + 1]).strip()
        state = f"{energy} {spin}".strip()

        # Grab data from row 2 onward for this pair
        block = pdf.iloc[2:, [col, col + 1]].copy()
        block = block.apply(pd.to_numeric, errors="coerce")
        block = block.dropna(how="all").reset_index(drop=True)

        # Build rows
        for i, (vol, unc) in enumerate(zip(block.iloc[:, 0].tolist(), block.iloc[:, 1].tolist())):
            # Skip rows where both are NaN
            if pd.isna(vol) and pd.isna(unc):
                continue
            rows.append((state, i, vol, unc))

    return pl.DataFrame(
        rows,
        schema={
            "state": pl.Utf8,
            "index": pl.Int64,
            "volume": pl.Float64,
            "uncertainty": pl.Float64,
        },
    )
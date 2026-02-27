import polars as pl
from pathlib import Path


def load_bci(file_path: str | Path) -> pl.DataFrame:
    """
    Reads a BCI_totals.txt file with columns:
        angle | total | scale

    Returns a Polars DataFrame with:
        angle  (f64)
        counts (f64)
        scale  (f64)
    """

    df = (
        pl.read_csv(
            file_path,
            separator="|",
            has_header=True,
        )
        # Strip whitespace from column names
        .rename(lambda name: name.strip())
        # Rename for consistency in pipeline
        .rename({
            "angle": "angle",
            "total": "counts",
            "scale": "scale",
        })
        # Strip whitespace from values and cast
        .with_columns([
            pl.col("angle").cast(pl.Utf8).str.strip_chars().cast(pl.Float64),
            pl.col("counts").cast(pl.Utf8).str.strip_chars().cast(pl.Float64),
            pl.col("scale").cast(pl.Utf8).str.strip_chars().cast(pl.Float64),
        ])
    )

    return df
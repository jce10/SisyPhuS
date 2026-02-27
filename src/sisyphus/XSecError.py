import polars as pl
import numpy as np  # only needed if you want np.sqrt, but we'll use polars' sqrt below


def add_xsec_uncertainty(
    df: pl.DataFrame,
    *,
    rel_err_bci: float = 0.10,
    xsec_col: str = "xsec_mb_sr",
    vol_col: str = "volume",
    vol_err_col: str = "uncertainty",
    bci_counts_col: str = "counts",
) -> pl.DataFrame:
    """
    Adds symmetric ±1σ uncertainty column for differential cross sections.

    Uses quadrature on relative errors:
        (σ_xs / xs)^2 = (σ_vol/vol)^2 + (rel_err_bci)^2

    Produces:
        xsec_err_mb_sr
    """

    # Safety mask: if vol<=0 or counts<=0 or xsec<=0 -> error = 0
    safe = (
        (pl.col(vol_col) > 0) &
        (pl.col(bci_counts_col) > 0) &
        (pl.col(xsec_col) > 0)
    )

    rel_err_vol = (pl.col(vol_err_col) / pl.col(vol_col))

    total_rel = (rel_err_vol.pow(2) + (pl.lit(rel_err_bci).pow(2))).sqrt()

    return df.with_columns(
        pl.when(safe)
        .then(pl.col(xsec_col) * total_rel)
        .otherwise(pl.lit(0.0))
        .alias("xsec_err_mb_sr")
    )
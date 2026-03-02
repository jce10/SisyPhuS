from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import polars as pl
import matplotlib.pyplot as plt
import textwrap
import pandas as pd


def load_aslan_ods_blocks(old_data_ods: str | Path):
    old_data_ods = Path(old_data_ods)
    if not old_data_ods.exists():
        return [], []

    df_aslan = pd.read_excel(old_data_ods, engine="odf", header=None)

    headers, blocks = [], []
    for col in range(0, df_aslan.shape[1], 2):
        energy = str(df_aslan.iloc[0, col]).strip()
        spin = str(df_aslan.iloc[0, col + 1]).strip()
        header = f"{energy} {spin}".strip()

        data = df_aslan.iloc[2:, [col, col + 1]].copy()
        data = data.apply(pd.to_numeric, errors="coerce").dropna(how="all").reset_index(drop=True)
        if data.shape[1] != 2:
            continue

        theta = data.iloc[:, 0].to_numpy(dtype=float)
        xsec = data.iloc[:, 1].to_numpy(dtype=float)

        m = np.isfinite(theta) & np.isfinite(xsec)
        theta, xsec = theta[m], xsec[m]
        if len(theta) == 0:
            continue

        headers.append(header)
        blocks.append((theta, xsec))

    return headers, blocks


def _extract_energy_token(s: str) -> Optional[str]:
    if not s:
        return None
    import re
    m = re.search(r"(\d+\.\d+)", s)
    if m:
        return m.group(1)
    m = re.search(r"(\d{3,5})", s)
    if m:
        return m.group(1)
    return None


def aslan_matches_state(aslan_header: str, state_label: str) -> bool:
    ah = (aslan_header or "").strip()
    sl = (state_label or "").strip()
    if not ah or not sl:
        return False

    ea = _extract_energy_token(ah)
    es = _extract_energy_token(sl)
    if ea and es:
        try:
            if ea.isdigit() and "." in es:
                return abs(float(ea) / 1000.0 - float(es)) < 1e-3
            if es.isdigit() and "." in ea:
                return abs(float(es) / 1000.0 - float(ea)) < 1e-3
        except Exception:
            pass
        return ea == es

    return ah.split()[0].lower() in sl.lower()


def fresco_matches_state(fresco_state: str, state_label: str) -> bool:
    fk = (fresco_state or "").replace(" ", "")
    sl = (state_label or "").replace(" ", "")
    if not fk or not sl:
        return False

    if fk.lower() in sl.lower() or sl.lower() in fk.lower():
        return True

    ef = _extract_energy_token(fk)
    es = _extract_energy_token(sl)
    if ef and es:
        try:
            if ef.isdigit() and "." in es:
                return abs(float(ef) / 1000.0 - float(es)) < 1e-3
            if es.isdigit() and "." in ef:
                return abs(float(es) / 1000.0 - float(ef)) < 1e-3
        except Exception:
            pass
        return ef == es

    return False


def read_calc_long_csv(calc_csv: str | Path) -> pl.DataFrame:
    calc_csv = Path(calc_csv)
    if not calc_csv.exists():
        raise FileNotFoundError(f"calc_csv not found: {calc_csv}")

    df = pl.read_csv(calc_csv)

    required = {"angle", "state", "xsec"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Calculated CSV missing columns {missing}. Found: {df.columns}")

    df = (
        df.with_columns([
            pl.col("angle").cast(pl.Float64, strict=False),
            pl.col("state").cast(pl.Utf8),
            pl.col("xsec").cast(pl.Float64, strict=False),
        ])
        .drop_nulls(["angle", "state", "xsec"])
        .sort(["state", "angle"])
    )

    if "xsec_err" in df.columns:
        df = df.with_columns(pl.col("xsec_err").cast(pl.Float64, strict=False))

    return df


def mega_plotter_long(
    calc_csv: str | Path,
    *,
    old_data_ods: Optional[str | Path] = None,
    fresco_df: Optional[pl.DataFrame] = None,  # tidy: state, theta_deg, xsec
    save_path: Optional[str | Path] = None,
    n_cols: int = 3,
    theta_max: Optional[float] = 70.0,
    logy: bool = True,
) -> None:
    df = read_calc_long_csv(calc_csv)
    if theta_max is not None:
        df = df.filter(pl.col("angle") <= float(theta_max))

    states = df.select(pl.col("state").unique().sort()).to_series().to_list()
    if not states:
        raise ValueError("No states found in calculated CSV after cleaning/cuts.")

    aslan_headers, aslan_blocks = ([], [])
    if old_data_ods is not None:
        aslan_headers, aslan_blocks = load_aslan_ods_blocks(old_data_ods)

    fdf = None
    fresco_states = []
    if fresco_df is not None:
        needed = {"state", "theta_deg", "xsec"}
        if not needed.issubset(set(fresco_df.columns)):
            raise ValueError(f"fresco_df must have columns {needed}, got {fresco_df.columns}")

        fdf = (
            fresco_df
            .with_columns([
                pl.col("state").cast(pl.Utf8),
                pl.col("theta_deg").cast(pl.Float64, strict=False),
                pl.col("xsec").cast(pl.Float64, strict=False),
            ])
            .drop_nulls(["state", "theta_deg", "xsec"])
        )
        if theta_max is not None:
            fdf = fdf.filter(pl.col("theta_deg") <= float(theta_max))

        fresco_states = fdf.select(pl.col("state").unique()).to_series().to_list()

    n_states = len(states)
    n_rows = int(np.ceil(n_states / n_cols))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, 4 * n_rows), sharex=False, sharey=False)
    axes = np.array(axes).reshape(-1)

    for i, state in enumerate(states):
        ax = axes[i]

        sdf = df.filter(pl.col("state") == state).sort("angle")
        theta = sdf.get_column("angle").to_numpy()
        xsec = sdf.get_column("xsec").to_numpy()

        yerr = None
        if "xsec_err" in sdf.columns:
            yerr = sdf.get_column("xsec_err").to_numpy()

        ax.errorbar(theta, xsec, yerr=yerr, fmt="o", label="This Work")

        for hdr, (t_old, x_old) in zip(aslan_headers, aslan_blocks):
            if aslan_matches_state(hdr, str(state)):
                ax.plot(t_old, x_old, "o", mfc="none", color ="red", label="Aslanoglou et al.")

        if fdf is not None:
            for fstate in fresco_states:
                if fresco_matches_state(str(fstate), str(state)):
                    cdf = fdf.filter(pl.col("state") == fstate).sort("theta_deg")
                    ax.plot(
                        cdf.get_column("theta_deg").to_numpy(),
                        cdf.get_column("xsec").to_numpy(),
                        "--",
                        color="green",
                        label=f"FRESCO {fstate}",
                    )

        if logy:
            ax.set_yscale("log")

        ax.set_xlabel(r"$\theta_{lab}$ (deg)")
        ax.set_ylabel(r"$d\sigma/d\Omega$ (mb/sr)")
        ax.set_title("\n".join(textwrap.wrap(str(state), width=28)))
        ax.legend(fontsize=9)
        ax.grid(True, which="both", ls="--", alpha=0.5)

    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout()

    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300)
        print(f"✅ Mega plot saved to: {save_path}")
    else:
        plt.show()


### single plot capability ###
def resolve_state(
    df: pl.DataFrame,
    *,
    state: str | None = None,
    match: str | None = None,
    state_index: int | None = None,
) -> str:
    """
    Resolve a state label from a long calc DataFrame.

    Priority:
      1) exact/substring state
      2) match substring
      3) state_index
      4) default first state
    """
    states = df.select(pl.col("state").unique().sort()).to_series().to_list()
    if not states:
        raise ValueError("No states found in calculated CSV.")

    # 1) explicit state
    if state is not None:
        # exact
        for s in states:
            if str(s) == str(state):
                return str(s)
        # substring fallback
        for s in states:
            if str(state).lower() in str(s).lower():
                return str(s)
        raise ValueError(f"State not found: {state}\nAvailable states:\n" + "\n".join(map(str, states)))

    # 2) match
    if match is not None:
        for s in states:
            if str(match).lower() in str(s).lower():
                return str(s)
        raise ValueError(f"No state matched substring: {match}\nAvailable states:\n" + "\n".join(map(str, states)))

    # 3) index
    if state_index is not None:
        if state_index < 0 or state_index >= len(states):
            raise IndexError(f"state_index={state_index} out of range (0..{len(states)-1})")
        return str(states[state_index])

    # 4) default
    return str(states[0])


def plot_single_long(
    calc_csv: str | Path,
    *,
    state: str | None = None,
    match: str | None = None,
    state_index: int | None = None,
    old_data_ods: Optional[str | Path] = None,
    fresco_df: Optional[pl.DataFrame] = None,   # tidy: state, theta_deg, xsec
    save_path: Optional[str | Path] = None,
    theta_max: Optional[float] = 70.0,
    logy: bool = True,
) -> str:
    """
    Plot a single angular distribution from the long-format calculated CSV.

    Returns the resolved state label.
    """
    df = read_calc_long_csv(calc_csv)
    if theta_max is not None:
        df = df.filter(pl.col("angle") <= float(theta_max))

    resolved = resolve_state(df, state=state, match=match, state_index=state_index)

    # Aslan blocks
    aslan_headers, aslan_blocks = ([], [])
    if old_data_ods is not None:
        aslan_headers, aslan_blocks = load_aslan_ods_blocks(old_data_ods)

    # Prep FRESCO DF
    fdf = None
    fresco_states = []
    if fresco_df is not None:
        needed = {"state", "theta_deg", "xsec"}
        if not needed.issubset(set(fresco_df.columns)):
            raise ValueError(f"fresco_df must have columns {needed}, got {fresco_df.columns}")

        fdf = (
            fresco_df
            .with_columns([
                pl.col("state").cast(pl.Utf8),
                pl.col("theta_deg").cast(pl.Float64, strict=False),
                pl.col("xsec").cast(pl.Float64, strict=False),
            ])
            .drop_nulls(["state", "theta_deg", "xsec"])
        )
        if theta_max is not None:
            fdf = fdf.filter(pl.col("theta_deg") <= float(theta_max))

        fresco_states = fdf.select(pl.col("state").unique()).to_series().to_list()

    # Extract this work
    sdf = df.filter(pl.col("state") == resolved).sort("angle")
    theta = sdf.get_column("angle").to_numpy()
    xsec = sdf.get_column("xsec").to_numpy()

    yerr = None
    if "xsec_err" in sdf.columns:
        yerr = sdf.get_column("xsec_err").to_numpy()

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.errorbar(theta, xsec, yerr=yerr, fmt="o", label="This Work")

    # Aslan overlay
    for hdr, (t_old, x_old) in zip(aslan_headers, aslan_blocks):
        if aslan_matches_state(hdr, resolved):
            ax.plot(t_old, x_old, "o", color="red", label="Aslanoglou et al.")

    # FRESCO overlay
    if fdf is not None:
        for fstate in fresco_states:
            if fresco_matches_state(str(fstate), resolved):
                cdf = fdf.filter(pl.col("state") == fstate).sort("theta_deg")
                ax.plot(
                    cdf.get_column("theta_deg").to_numpy(),
                    cdf.get_column("xsec").to_numpy(),
                    "--",
                    label=f"FRESCO {fstate}",
                    color="green"
                )

    if logy:
        ax.set_yscale("log")

    ax.set_xlabel(r"$\theta_{lab}$ (deg)")
    ax.set_ylabel(r"$d\sigma/d\Omega$ (mb/sr)")
    ax.set_title("\n".join(textwrap.wrap(resolved, width=40)))
    ax.legend(fontsize=9)
    ax.grid(True, which="both", ls="--", alpha=0.5)
    plt.tight_layout()

    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300)
        print(f"✅ Single plot saved to: {save_path}")
    else:
        plt.show()

    return resolved
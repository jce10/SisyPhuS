import polars as pl

E_CHARGE_C = 1.602176634e-19  # Coulombs


def calc_rho_barn(
    thickness_g_cm2: float,
    molar_mass_g_mol: float,
    avogadro: float,
    barn_to_cm2: float,
) -> float:
    rho_cm2 = (thickness_g_cm2 / molar_mass_g_mol) * avogadro  # nuclei / cm^2
    return rho_cm2 * barn_to_cm2  # nuclei / barn


def add_xsec_columns(
    df: pl.DataFrame,
    *,
    sampling_rate_hz: float,
    beam_Z: int,
    rho_barn: float,
    solid_angle_sr: float,
) -> pl.DataFrame:
    beam_charge_c = beam_Z * E_CHARGE_C

    # --- Pass 1: compute beam charge + beam particles (so N_beam exists) ---
    df = df.with_columns([
        # Coulombs (per your original formula)
        ((pl.col("counts") * 1e-9 * pl.col("scale")) / sampling_rate_hz).alias("Q_beam_C"),

        # Beam particles
        (
            ((pl.col("counts") * 1e-9 * pl.col("scale")) / sampling_rate_hz)
            / beam_charge_c
        ).alias("N_beam"),
    ])

    # --- Pass 2: compute cross section using N_beam ---
    df = df.with_columns([
        # mb/sr
        (
            (pl.col("volume") * 1000.0)
            / (pl.col("N_beam") * rho_barn * solid_angle_sr)
        ).alias("xsec"),
    ])

    return df
from pathlib import Path
import re

import pandas as pd
import polars as pl


# ----------------------------
# helpers
# ----------------------------
def normalize_tag(ex_energy: str, jpi: str) -> str:
    """
    Build a common state tag like:
    '6860 keV | 5/2+'
    """
    return f"{str(ex_energy).strip()} | {str(jpi).strip()}"


def parse_fresco_ods_long(file_path):

    raw = pd.read_excel(file_path, engine="odf", header=None)

    # ---- state info ----
    ex_energy = str(raw.iloc[0, 0]).strip()
    jpi = str(raw.iloc[0, 1]).strip()
    state_tag = f"{ex_energy} | {jpi}"

    # ---- promote header ----
    df = raw.iloc[2:].copy()
    df.columns = raw.iloc[1]
    df = df.reset_index(drop=True)

    # clean column names
    df.columns = df.columns.astype(str).str.strip()

    # convert numeric
    df = df.apply(pd.to_numeric, errors="coerce")

    # drop empty rows
    df = df.dropna(how="all")

    # ---- reshape to long format ----
    records = []

    angle_vals = df["angle"]

    xsec_cols = [col for col in df.columns if col.startswith("xsec")]

    for col in xsec_cols:
        ell = col.replace("xsec", "")  # "1", "3", "13"

        # handle combined ℓ nicely
        if len(ell) > 1:
            ell_label = "+".join(list(ell))   # "13" → "1+3"
        else:
            ell_label = ell

        for angle, xsec in zip(angle_vals, df[col]):
            if pd.isna(xsec):
                continue

            records.append({
                "state": state_tag,
                "ell": ell_label,
                "angle": angle,
                "xsec": xsec,
                "source": "fresco",
            })

    return pl.DataFrame(records)


def parse_aslan_ods_split_headers(file_path: str | Path) -> pl.DataFrame:
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


def parse_sisyphus_csv(file_path: str | Path) -> pl.DataFrame:
    """
    Read SisyPhuS long-format CSV:
      state, angle, xsec, xsec_err
    """
    df = pl.read_csv(file_path)

    # normalize state tags to match the same format you want everywhere
    df = df.with_columns(
        pl.col("state")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
        .alias("state")
    )

    # optionally convert "6860 keV 5/2+" -> "6860 keV | 5/2+"
    df = df.with_columns(
        pl.col("state")
        .str.replace(r"^(.+keV)\s+(.+)$", r"${1} | ${2}")
        .alias("state")
    )

    df = df.with_columns(pl.lit("my_data").alias("source"))
    return df


# ----------------------------
# main
# ----------------------------
csv_file = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/6Lid/output_peak_files/9Be6Lid_angular_distributions_long.csv"
fresco_ods = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/6Lid/9Be6Lid_fresco/6860keV/6860keV.ods"
prev_exp_ods = "/home/jce18b/Esparza_SPS/2025_06_13C_campaign/6Lid/output_peak_files/aslan_data.ods"

my_data = parse_sisyphus_csv(csv_file)
fresco_data = parse_fresco_ods_long(fresco_ods)
prev_exp_data = parse_aslan_ods_split_headers(prev_exp_ods)

# pick the state tag from the FRESCO file as the one to match
target_state = fresco_data["state"][0]

print(f"Target state: {target_state}")

my_state = my_data.filter(pl.col("state") == target_state)
fresco_state = fresco_data.filter(pl.col("state") == target_state)
prev_state = prev_exp_data.filter(pl.col("state") == target_state)

print("\nMy data:")
print(my_state)

print("\nFRESCO data:")
print(fresco_state)

print("\nPrevious experimental data:")
print(prev_state)
from __future__ import annotations

from pathlib import Path
from typing import Dict
import polars as pl
import re


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#                                                                                             #
#                   Main parsing for FRESCO fort.16 files                                     #
#                                                                                             #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

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
    From each subdirectory's fort.16 file, parse only the selected theta block.

    Notes
    -----
    Python indexing is zero-based:
        block_index = 0  -> first theta block
        block_index = 1  -> second theta block
        block_index = 32 -> 33rd theta block

    Returns
    -------
    pl.DataFrame with columns:
        state: str
        theta_deg: float
        xsec: float
    """

    fresco_dir = Path(fresco_dir)

    empty_df = pl.DataFrame(
        {"state": [], "theta_deg": [], "xsec": []},
        schema={
            "state": pl.Utf8,
            "theta_deg": pl.Float64,
            "xsec": pl.Float64,
        },
    )

    if not fresco_dir.is_dir():
        return empty_df

    if block_index < 0:
        raise ValueError("block_index must be >= 0")

    frames: list[pl.DataFrame] = []

    for subdir in sorted(p for p in fresco_dir.iterdir() if p.is_dir()):
        filepath = subdir / fort_name

        if not filepath.exists():
            continue

        try:
            lines = filepath.read_text().splitlines()
        except Exception:
            continue

        headers = [
            i for i, line in enumerate(lines)
            if line.strip().startswith(theta_header_prefix)
        ]

        if block_index >= len(headers):
            continue

        start_idx = headers[block_index] + 1
        end_idx = headers[block_index + 1] if block_index + 1 < len(headers) else len(lines)

        theta_vals: list[float] = []
        xsec_vals: list[float] = []

        for line in lines[start_idx:end_idx]:
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
                schema={
                    "state": pl.Utf8,
                    "theta_deg": pl.Float64,
                    "xsec": pl.Float64,
                },
            )
        )

    if not frames:
        return empty_df

    return pl.concat(frames, how="vertical").sort(["state", "theta_deg"])


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#                                                                                             #
#           Old FRESCO parsers                                                                #
#                                                                                             #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# def load_all_fresco_long(
#     fresco_dir: str | Path,
#     *,
#     theta_max: float = 180.0,
#     fort_name: str = "fort.16",
#     theta_header_prefix: str = "#  Theta",
#     block_index: int = 1,
# ) -> pl.DataFrame:
#     """
#     Load FRESCO angular distributions from subdirectories into ONE long/tidy DataFrame.

#     Each subdirectory is treated as a "state" label.
#     Parses the Nth theta block (default: second block, block_index=1) like your original code.

#     Returns a DataFrame with columns:
#         state: str (subdirectory name)
#         theta_deg: float
#         xsec: float

#     Filtered to theta_deg <= theta_max.
#     """
#     fresco_dir = Path(fresco_dir)
#     if not fresco_dir.is_dir():
#         return pl.DataFrame(
#             {"state": [], "theta_deg": [], "xsec": []},
#             schema={"state": pl.Utf8, "theta_deg": pl.Float64, "xsec": pl.Float64},
#         )

#     frames: list[pl.DataFrame] = []

#     for subdir in sorted([p for p in fresco_dir.iterdir() if p.is_dir()]):
#         filepath = subdir / fort_name
#         if not filepath.exists():
#             continue

#         try:
#             lines = filepath.read_text().splitlines()
#         except Exception:
#             continue

#         headers = [i for i, line in enumerate(lines) if line.strip().startswith(theta_header_prefix)]
#         if len(headers) <= block_index:
#             continue

#         start_idx = headers[block_index] + 1

#         theta_vals: list[float] = []
#         xsec_vals: list[float] = []

#         for line in lines[start_idx:]:
#             s = line.strip()
#             if not s or s.startswith("#") or s.startswith("END"):
#                 continue

#             parts = s.split()
#             if len(parts) < 2:
#                 continue

#             try:
#                 theta = float(parts[0])
#                 xsec = float(parts[1])
#             except ValueError:
#                 continue

#             if theta <= theta_max:
#                 theta_vals.append(theta)
#                 xsec_vals.append(xsec)

#         if not theta_vals:
#             continue

#         frames.append(
#             pl.DataFrame(
#                 {
#                     "state": [subdir.name] * len(theta_vals),
#                     "theta_deg": theta_vals,
#                     "xsec": xsec_vals,
#                 },
#                 schema={"state": pl.Utf8, "theta_deg": pl.Float64, "xsec": pl.Float64},
#             )
#         )

#     if not frames:
#         return pl.DataFrame(
#             {"state": [], "theta_deg": [], "xsec": []},
#             schema={"state": pl.Utf8, "theta_deg": pl.Float64, "xsec": pl.Float64},
#         )

#     return pl.concat(frames, how="vertical").sort(["state", "theta_deg"])



# def load_all_fresco_dict(
#     fresco_dir: str | Path,
#     *,
#     theta_max: float = 180.0,
#     fort_name: str = "fort.16",
#     theta_header_prefix: str = "#  Theta",
#     block_index: int = 1,
# ) -> Dict[str, pl.DataFrame]:
#     """
#     Convenience wrapper: returns a dict[state -> DataFrame] using load_all_fresco_long().

#     """
#     df = load_all_fresco_long(
#         fresco_dir,
#         theta_max=theta_max,
#         fort_name=fort_name,
#         theta_header_prefix=theta_header_prefix,
#         block_index=block_index,
#     )

#     out: Dict[str, pl.DataFrame] = {}
#     if df.height == 0:
#         return out

#     for state in df.get_column("state").unique().to_list():
#         out[str(state)] = df.filter(pl.col("state") == state).select(["theta_deg", "xsec"]).sort("theta_deg")

#     return out

# def scrape_fort16_sections(
#     file_path: str | Path,
#     ncols: int | None = 2,
#     verbose: bool = True,
#     output_file: str | Path | None = None,
# ):
#     """
#     Scrape a FRESCO fort.16 style file into separate reaction sections
#     and optionally write all sections to one CSV file.

#     Output format:
#     section,angle,xsec
#     @s0,0.01,1.0
#     @s0,0.5,1.004
#     ...
#     """

#     file_path = Path(file_path)

#     if output_file is not None:
#         output_file = Path(output_file)
#         output_file.parent.mkdir(parents=True, exist_ok=True)

#     sections = []
#     current_data = []
#     current_header_lines = []
#     section_idx = 0

#     def finalize_section():
#         nonlocal current_data, current_header_lines, sections, section_idx

#         if not current_data:
#             current_header_lines = []
#             return

#         min_len = min(len(row) for row in current_data)
#         trimmed_data = [row[:min_len] for row in current_data]

#         if ncols is not None:
#             trimmed_data = [row[:ncols] for row in trimmed_data]
#             min_len = min(min_len, ncols)

#         cols = [f"col{i}" for i in range(min_len)]
#         df = pl.DataFrame(trimmed_data, schema=cols, orient="row")

#         header = " | ".join(current_header_lines).strip()

#         match = re.search(r"@s\d+", header)
#         if match:
#             section_tag = match.group(0)
#         else:
#             section_tag = f"@s{section_idx}"

#         sections.append({
#             "section_tag": section_tag,
#             "header": header,
#             "data": df
#         })

#         section_idx += 1
#         current_data = []
#         current_header_lines = []

#     with open(file_path, "r") as f:
#         for line in f:
#             stripped = line.strip()

#             if stripped == "END":
#                 finalize_section()
#                 continue

#             parts = stripped.split()
#             try:
#                 row = [float(x) for x in parts]
#                 current_data.append(row)
#             except ValueError:
#                 if stripped:
#                     current_header_lines.append(stripped)

#     finalize_section()

#     # 🔥 WRITE ONE BIG CSV FILE
#     if output_file is not None:
#         rows = []

#         for sec in sections:
#             tag = sec["section_tag"]
#             df = sec["data"]

#             for row in df.iter_rows():
#                 if len(row) >= 2:
#                     rows.append({
#                         "section": tag,
#                         "angle": row[0],
#                         "xsec": row[1],
#                     })

#         out_df = pl.DataFrame(rows)
#         out_df.write_csv(output_file)

#         if verbose:
#             print(f"  → Saved CSV file: {output_file}")

#     if verbose:
#         print(f"\nFound {len(sections)} section(s) in {file_path.name}\n")
#         for i, sec in enumerate(sections):
#             df = sec["data"]

#             if df.height > 0:
#                 theta_min = df["col0"].min()
#                 theta_max = df["col0"].max()
#                 print(f"Section {i}:")
#                 print(f"  Tag         : {sec['section_tag']}")
#                 print(f"  Theta range : {theta_min:.2f} -> {theta_max:.2f} deg")
#                 print(f"  Rows        : {df.height}\n")
#             else:
#                 print(f"Section {i}: empty\n")

#     return sections






# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#                                                                                             #
#           OLD FORT.200 STYLE PARSING (not used currently, but keeping for reference)        #
#                                                                                             #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# def load_fresco_data_fort200(
#     filepath: str | Path,
#     *,
#     theta_max: float | None = None,
#     state: str | None = None,
# ) -> pl.DataFrame:
#     filepath = Path(filepath)

#     if not filepath.exists():
#         raise FileNotFoundError(f"File not found: {filepath}")
#     if not filepath.is_file():
#         raise IsADirectoryError(f"Expected a file, got directory: {filepath}")

#     theta_vals: list[float] = []
#     xsec_vals: list[float] = []

#     lines = filepath.read_text().splitlines()

#     for line in lines:
#         s = line.strip()

#         if not s or s.startswith("#") or s.startswith("END"):
#             continue

#         parts = s.split()
#         if len(parts) < 2:
#             continue

#         try:
#             theta = float(parts[0].replace("D", "E").replace("d", "e"))
#             xsec = float(parts[1].replace("D", "E").replace("d", "e"))
#         except ValueError:
#             continue

#         if theta_max is None or theta <= theta_max:
#             theta_vals.append(theta)
#             xsec_vals.append(xsec)

#     if not theta_vals:
#         base = {"theta_deg": [], "xsec": []}
#         if state is not None:
#             base["state"] = []
#             return pl.DataFrame(
#                 base,
#                 schema={"theta_deg": pl.Float64, "xsec": pl.Float64, "state": pl.Utf8},
#             )
#         return pl.DataFrame(
#             base,
#             schema={"theta_deg": pl.Float64, "xsec": pl.Float64},
#         )

#     df = pl.DataFrame(
#         {"theta_deg": theta_vals, "xsec": xsec_vals},
#         schema={"theta_deg": pl.Float64, "xsec": pl.Float64},
#     ).sort("theta_deg")

#     if state is not None:
#         df = df.with_columns(pl.lit(state).alias("state"))

#     return df



# def load_all_fresco_fort200_long(
#     fresco_dir: str | Path,
#     *,
#     theta_max: float | None = None,
#     pattern: str = "fort.2*",
#     state_map: dict[str, str] | None = None,
# ) -> pl.DataFrame:
#     """
#     Load all split fort.20x files in a directory into one long/tidy DataFrame.

#     Parameters
#     ----------
#     fresco_dir
#         Directory containing fort.20x files
#     theta_max
#         Optional max theta cut
#     pattern
#         Filename pattern to match
#     state_map
#         Optional mapping like:
#             {"fort.201": "10753 keV 7/2-", "fort.202": "8800 keV 5/2+"}

#     Returns
#     -------
#     pl.DataFrame with columns:
#         state, theta_deg, xsec
#     """
#     fresco_dir = Path(fresco_dir)

#     if not fresco_dir.exists():
#         raise FileNotFoundError(f"Directory not found: {fresco_dir}")
#     if not fresco_dir.is_dir():
#         raise NotADirectoryError(f"Expected a directory, got file: {fresco_dir}")

#     frames: list[pl.DataFrame] = []

#     for filepath in sorted(fresco_dir.glob(pattern)):
#         if not filepath.is_file():
#             continue

#         if state_map is not None:
#             state = state_map.get(filepath.name, filepath.name)
#         else:
#             state = filepath.name

#         df = load_fresco_data_fort200(
#             filepath,
#             theta_max=theta_max,
#             state=state,
#         )

#         if df.height > 0:
#             frames.append(df)

#     if not frames:
#         return pl.DataFrame(
#             {"state": [], "theta_deg": [], "xsec": []},
#             schema={"state": pl.Utf8, "theta_deg": pl.Float64, "xsec": pl.Float64},
#         )

#     return pl.concat(frames, how="vertical").select(["state", "theta_deg", "xsec"])

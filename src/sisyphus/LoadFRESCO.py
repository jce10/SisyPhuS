from __future__ import annotations

from pathlib import Path
from typing import Dict
import polars as pl
import re

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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
 # scrape fort.16 file , separate sections by headers, and optionally write all sections to one CSV file
def scrape_fort16_sections(
    file_path: str | Path,
    ncols: int | None = 2,
    verbose: bool = True,
    output_file: str | Path | None = None,
):
    """
    Scrape a FRESCO fort.16 style file into separate reaction sections
    and optionally write all sections to one CSV file.

    Output format:
    section,angle,xsec
    @s0,0.01,1.0
    @s0,0.5,1.004
    ...
    """

    file_path = Path(file_path)

    if output_file is not None:
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)

    sections = []
    current_data = []
    current_header_lines = []
    section_idx = 0

    def finalize_section():
        nonlocal current_data, current_header_lines, sections, section_idx

        if not current_data:
            current_header_lines = []
            return

        min_len = min(len(row) for row in current_data)
        trimmed_data = [row[:min_len] for row in current_data]

        if ncols is not None:
            trimmed_data = [row[:ncols] for row in trimmed_data]
            min_len = min(min_len, ncols)

        cols = [f"col{i}" for i in range(min_len)]
        df = pl.DataFrame(trimmed_data, schema=cols, orient="row")

        header = " | ".join(current_header_lines).strip()

        match = re.search(r"@s\d+", header)
        if match:
            section_tag = match.group(0)
        else:
            section_tag = f"@s{section_idx}"

        sections.append({
            "section_tag": section_tag,
            "header": header,
            "data": df
        })

        section_idx += 1
        current_data = []
        current_header_lines = []

    with open(file_path, "r") as f:
        for line in f:
            stripped = line.strip()

            if stripped == "END":
                finalize_section()
                continue

            parts = stripped.split()
            try:
                row = [float(x) for x in parts]
                current_data.append(row)
            except ValueError:
                if stripped:
                    current_header_lines.append(stripped)

    finalize_section()

    # 🔥 WRITE ONE BIG CSV FILE
    if output_file is not None:
        rows = []

        for sec in sections:
            tag = sec["section_tag"]
            df = sec["data"]

            for row in df.iter_rows():
                if len(row) >= 2:
                    rows.append({
                        "section": tag,
                        "angle": row[0],
                        "xsec": row[1],
                    })

        out_df = pl.DataFrame(rows)
        out_df.write_csv(output_file)

        if verbose:
            print(f"  → Saved CSV file: {output_file}")

    if verbose:
        print(f"\nFound {len(sections)} section(s) in {file_path.name}\n")
        for i, sec in enumerate(sections):
            df = sec["data"]

            if df.height > 0:
                theta_min = df["col0"].min()
                theta_max = df["col0"].max()
                print(f"Section {i}:")
                print(f"  Tag         : {sec['section_tag']}")
                print(f"  Theta range : {theta_min:.2f} -> {theta_max:.2f} deg")
                print(f"  Rows        : {df.height}\n")
            else:
                print(f"Section {i}: empty\n")

    return sections
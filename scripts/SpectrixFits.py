#!/usr/bin/env python3
"""
Extract fitted Gaussian peak parameters from Spectrix JSON files.

Typical directory layout:

    input_peaks/
        fits/
            10degfits.json
            12degfits.json
            ...

Examples:

    # Config-driven mode, recommended for SisyPhuS workflows
    python SpectrixFits.py spectrix_config.yaml

    # Old command-line mode still works
    python SpectrixFits.py input_peaks/fits \
        --cal-m -9.055 --cal-b 8154.34 \
        --energy-unit keV \
        --targets 6860 7492 7688 8866 9499 9894 10753 10812 \
        --out-prefix input_peaks/spectrix_peak_table

Outputs:
    <out-prefix>_long.csv   : one row per fitted peak
    <out-prefix>_wide.tsv   : copy/paste-friendly table, paired area/uncertainty columns
    <out-prefix>_peak_index_areas.csv : one row per JSON file, columns are peak_00_area, peak_00_area_unc, ...

Notes:
    - For Gaussian fits in Spectrix, the fitted 'amplitude' appears to be the integrated
      peak area / volume, not the peak height.
    - If --targets are supplied, peaks are assigned to the nearest target energy.
    - If --targets are omitted, peaks are labeled peak_00, peak_01, ... sorted by energy.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - helpful message given at runtime
    yaml = None

FWHM_FACTOR = 2.0 * math.sqrt(2.0 * math.log(2.0))


def calibrated_energy(x: float, cal_a: float | None, cal_b: float | None, cal_c: float | None) -> float | None:
    """Evaluate either E = m*x + b or E = a*x^2 + b*x + c.

    Linear mode uses --cal-m and --cal-b.
    Quadratic mode uses --cal-a, --cal-b, and --cal-c.
    """
    if cal_a is not None and cal_b is not None and cal_c is not None:
        return cal_a * x * x + cal_b * x + cal_c
    return None


def calibration_derivative(x: float, cal_a: float | None, cal_b: float | None, cal_c: float | None) -> float | None:
    """Return dE/dx for uncertainty and local FWHM conversion."""
    if cal_a is not None and cal_b is not None and cal_c is not None:
        return 2.0 * cal_a * x + cal_b
    return None


def get_value(param: dict[str, Any], key: str = "value") -> float | None:
    value = param.get(key)
    return None if value is None else float(value)


def angle_from_filename(path: Path) -> float | None:
    """Extract angle from names like 10degfits.json, 12.5deg.json, 12p5degfits.json."""
    match = re.search(r"([0-9]+(?:[._p][0-9]+)?)\s*deg", path.stem, flags=re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1).replace("p", ".").replace("_", "."))


def find_gaussian_result(blob: dict[str, Any]) -> dict[str, Any]:
    """Return the Spectrix Gaussian fit_result block."""
    candidates = []

    if "temp_fit" in blob:
        candidates.append(blob["temp_fit"])

    # Some Spectrix saves may keep previous fits under stored_fits.
    stored = blob.get("stored_fits")
    if isinstance(stored, list):
        candidates.extend(stored)
    elif isinstance(stored, dict):
        candidates.extend(stored.values())

    candidates.append(blob)

    for candidate in candidates:
        try:
            return candidate["fit_result"]["Gaussian"]
        except Exception:
            pass

    raise KeyError("Could not find ['fit_result']['Gaussian'] in this JSON file.")


def extract_peaks(path: Path, cal_a: float | None, cal_b: float | None, cal_c: float | None) -> list[dict[str, Any]]:
    with path.open("r") as f:
        blob = json.load(f)

    gaussian = find_gaussian_result(blob)
    fit_result = gaussian.get("fit_result", [])
    angle = angle_from_filename(path)

    rows: list[dict[str, Any]] = []
    for i, peak in enumerate(fit_result):
        mean = get_value(peak["mean"])
        mean_unc = get_value(peak["mean"], "uncertainty")
        sigma = get_value(peak["sigma"])
        sigma_unc = get_value(peak["sigma"], "uncertainty")
        area = get_value(peak["amplitude"])
        area_unc = get_value(peak["amplitude"], "uncertainty")

        fwhm = FWHM_FACTOR * sigma if sigma is not None else None
        fwhm_unc = FWHM_FACTOR * sigma_unc if sigma_unc is not None else None

        energy = None
        energy_unc = None
        fwhm_energy = None
        fwhm_energy_unc = None
        if mean is not None:
            energy = calibrated_energy(mean, cal_a, cal_b, cal_c)
            dE_dx = calibration_derivative(mean, cal_a, cal_b, cal_c)
            if dE_dx is not None:
                energy_unc = abs(dE_dx) * mean_unc if mean_unc is not None else None
                fwhm_energy = abs(dE_dx) * fwhm if fwhm is not None else None
                fwhm_energy_unc = abs(dE_dx) * fwhm_unc if fwhm_unc is not None else None

        rows.append(
            {
                "file": path.name,
                "angle_deg": angle,
                "peak_index": i,
                "mean_x": mean,
                "mean_x_unc": mean_unc,
                "energy": energy,
                "energy_unc": energy_unc,
                "sigma_x": sigma,
                "sigma_x_unc": sigma_unc,
                "fwhm_x": fwhm,
                "fwhm_x_unc": fwhm_unc,
                "fwhm_energy": fwhm_energy,
                "fwhm_energy_unc": fwhm_energy_unc,
                "area": area,
                "area_unc": area_unc,
            }
        )

    # Prefer physically useful ordering if calibrated; otherwise keep focal-plane ordering.
    sort_key = "energy" if cal_a is not None and cal_b is not None and cal_c is not None else "mean_x"
    return sorted(rows, key=lambda r: (float("inf") if r[sort_key] is None else r[sort_key]))


def assign_labels(rows: list[dict[str, Any]], targets: list[float] | None, energy_unit: str) -> None:
    """Add state_label to each row, using nearest target energy if provided."""
    if not targets:
        for i, row in enumerate(rows):
            row["state_label"] = f"peak_{i:02d}"
        return

    unused = set(range(len(rows)))
    for target in targets:
        if not unused:
            break
        best_i = min(
            unused,
            key=lambda idx: abs((rows[idx].get("energy") or float("inf")) - target),
        )
        rows[best_i]["state_label"] = f"{target:g} {energy_unit}"
        rows[best_i]["target_energy"] = target
        rows[best_i]["delta_energy"] = (
            rows[best_i]["energy"] - target if rows[best_i].get("energy") is not None else None
        )
        unused.remove(best_i)

    for idx in unused:
        rows[idx]["state_label"] = f"unassigned_peak_{rows[idx]['peak_index']:02d}"
        rows[idx]["target_energy"] = None
        rows[idx]["delta_energy"] = None


def write_long_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "file", "angle_deg", "state_label", "target_energy", "delta_energy", "peak_index",
        "mean_x", "mean_x_unc", "energy", "energy_unc", "sigma_x", "sigma_x_unc",
        "fwhm_x", "fwhm_x_unc", "fwhm_energy", "fwhm_energy_unc", "area", "area_unc",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_wide_tsv(path: Path, all_rows: list[dict[str, Any]], labels: list[str]) -> None:
    by_angle: dict[float, dict[str, dict[str, Any]]] = {}
    for row in all_rows:
        angle = row["angle_deg"]
        if angle is None:
            raise ValueError(f"Could not parse angle from filename {row['file']}")
        by_angle.setdefault(angle, {})[row["state_label"]] = row

    header = ["angle_deg"]
    for label in labels:
        header.extend([f"{label} peak volume", f"{label} uncertainty"])

    with path.open("w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(header)
        for angle in sorted(by_angle):
            line = [angle]
            for label in labels:
                row = by_angle[angle].get(label, {})
                line.extend([row.get("area", ""), row.get("area_unc", "")])
            writer.writerow(line)



def write_peak_index_area_csv(path: Path, all_rows: list[dict[str, Any]]) -> None:
    """Write one row per JSON file with area/area_unc pairs ordered by peak_index.

    Output columns look like:
        file, angle_deg, peak_09_area, peak_09_area_unc, peak_08_area, ...
    """
    by_file: dict[str, list[dict[str, Any]]] = {}
    for row in all_rows:
        by_file.setdefault(str(row["file"]), []).append(row)

    max_peak_index = max(int(row["peak_index"]) for row in all_rows)

    # Reverse peak order: 9 -> 0 instead of 0 -> 9
    peak_indices = range(max_peak_index, -1, -1)

    header = ["file", "angle_deg"]
    for i in peak_indices:
        header.extend([f"peak_{i:02d}_area", f"peak_{i:02d}_area_unc"])

    def file_sort_key(file_name: str) -> tuple[float, str]:
        angle = angle_from_filename(Path(file_name))
        return (float("inf") if angle is None else angle, file_name)

    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for file_name in sorted(by_file, key=file_sort_key):
            rows = by_file[file_name]
            angle = rows[0].get("angle_deg")
            by_index = {int(row["peak_index"]): row for row in rows}

            line: list[Any] = [file_name, angle]
            for i in peak_indices:
                row = by_index.get(i, {})
                line.extend([row.get("area", ""), row.get("area_unc", "")])

            writer.writerow(line)

def load_config(path: Path) -> dict[str, Any]:
    """Load a YAML or JSON config file."""
    if not path.exists():
        raise SystemExit(f"Config file not found: {path}")

    suffix = path.suffix.lower()
    text = path.read_text()

    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise SystemExit(
                "PyYAML is required for YAML configs. Install with: pip install pyyaml"
            )
        loaded = yaml.safe_load(text) or {}
    elif suffix == ".json":
        loaded = json.loads(text)
    else:
        raise SystemExit("Config must be .yaml, .yml, or .json")

    if not isinstance(loaded, dict):
        raise SystemExit("Config file must contain a mapping/dictionary at top level.")

    # Allow either a bare config or a SisyPhuS-style nested block.
    return loaded.get("spectrix", loaded)


def resolve_path(value: str | Path | None, base_dir: Path) -> Path | None:
    """Resolve relative paths with respect to the config file directory."""
    if value is None:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else base_dir / path


def parse_targets(raw_targets: Any) -> tuple[list[float] | None, dict[float, str]]:
    """Parse target energies from either a list or a mapping.

    Supported YAML styles:

        targets: [6860, 7688, 8220]

        targets:
          6860: 6860keV
          7688: trapped
          8220: superrad

        targets:
          - energy: 6860
            label: 6860keV
          - energy: 8220
            label: superrad
    """
    if raw_targets in (None, []):
        return None, {}

    targets: list[float] = []
    labels: dict[float, str] = {}

    if isinstance(raw_targets, dict):
        for energy, label in raw_targets.items():
            e = float(energy)
            targets.append(e)
            labels[e] = str(label)
        return targets, labels

    if isinstance(raw_targets, list):
        for item in raw_targets:
            if isinstance(item, dict):
                e = float(item["energy"])
                label = item.get("label")
                targets.append(e)
                if label is not None:
                    labels[e] = str(label)
            else:
                targets.append(float(item))
        return targets, labels

    raise SystemExit("peak_matching.targets must be a list or mapping.")


def calibration_from_config(config: dict[str, Any]) -> tuple[float | None, float | None, float | None]:
    """Normalize calibration config to E = a*x^2 + b*x + c."""
    cal = config.get("calibration", {}) or {}
    if not isinstance(cal, dict):
        raise SystemExit("calibration must be a mapping/dictionary.")

    cal_type = str(cal.get("type", "quadratic" if "a" in cal else "linear")).lower()

    if cal_type == "linear":
        # Accept either m/intercept or b/c style.
        if "m" in cal:
            m = float(cal["m"])
            intercept = float(cal.get("intercept", cal.get("b")))
        else:
            m = float(cal["b"])
            intercept = float(cal.get("c", cal.get("intercept")))
        return 0.0, m, intercept

    if cal_type == "quadratic":
        return float(cal["a"]), float(cal["b"]), float(cal["c"])

    if cal_type in {"none", "off", "disabled"}:
        return None, None, None

    raise SystemExit("calibration.type must be linear, quadratic, or none.")


def apply_custom_target_labels(rows: list[dict[str, Any]], target_labels: dict[float, str]) -> None:
    """Replace default target labels like '6860 keV' with user labels."""
    for row in rows:
        target = row.get("target_energy")
        if target is None:
            continue
        for energy, label in target_labels.items():
            if math.isclose(float(target), float(energy), rel_tol=0.0, abs_tol=1e-9):
                row["state_label"] = label
                break


def filter_target_tolerance(rows: list[dict[str, Any]], tolerance: float | None) -> None:
    """Mark peaks as unassigned if target matching exceeded the configured tolerance."""
    if tolerance is None:
        return
    for row in rows:
        delta = row.get("delta_energy")
        if delta is not None and abs(float(delta)) > tolerance:
            row["state_label"] = f"unassigned_peak_{row['peak_index']:02d}"
            row["target_energy"] = None
            row["delta_energy"] = None


def run_extraction(
    fits_dir: Path,
    out_prefix: Path,
    cal_a: float | None,
    cal_b: float | None,
    cal_c: float | None,
    energy_unit: str = "keV",
    targets: list[float] | None = None,
    target_labels: dict[float, str] | None = None,
    tolerance: float | None = None,
) -> tuple[Path, Path, Path]:
    """Extract Spectrix peaks and write long CSV plus copy/paste TSV/CSV files."""
    json_files = sorted(fits_dir.glob("*.json"))
    if not json_files:
        raise SystemExit(f"No .json files found in {fits_dir}")

    all_rows: list[dict[str, Any]] = []
    labels: list[str] | None = None
    target_labels = target_labels or {}

    for path in json_files:
        rows = extract_peaks(path, cal_a, cal_b, cal_c)
        assign_labels(rows, targets, energy_unit)
        filter_target_tolerance(rows, tolerance)
        apply_custom_target_labels(rows, target_labels)
        all_rows.extend(rows)

        current_labels = [r["state_label"] for r in rows]
        if labels is None:
            labels = current_labels

    if labels is None:
        labels = []

    # Use custom target label order in the wide table when given.
    if targets and target_labels:
        labels = [target_labels.get(float(t), f"{t:g} {energy_unit}") for t in targets]

    long_path = out_prefix.with_name(out_prefix.name + "_long.csv")
    wide_path = out_prefix.with_name(out_prefix.name + "_wide.tsv")
    peak_index_area_path = out_prefix.with_name(out_prefix.name + "_peak_index_areas.csv")
    long_path.parent.mkdir(parents=True, exist_ok=True)

    write_long_csv(long_path, all_rows)
    write_wide_tsv(wide_path, all_rows, labels)
    write_peak_index_area_csv(peak_index_area_path, all_rows)

    return long_path, wide_path, peak_index_area_path


def run_from_config(config_path: Path) -> tuple[Path, Path, Path]:
    """Run extraction from a YAML/JSON config."""
    config = load_config(config_path)
    base_dir = config_path.parent

    fits_dir = resolve_path(config.get("fits_dir", config.get("input_dir", "fits")), base_dir)
    out_prefix = resolve_path(config.get("output_prefix", "fits_peak_table"), base_dir)
    assert fits_dir is not None and out_prefix is not None

    cal_a, cal_b, cal_c = calibration_from_config(config)
    energy_unit = str(config.get("energy_unit", "keV"))

    peak_matching = config.get("peak_matching", {}) or {}
    raw_targets = peak_matching.get("targets", config.get("targets"))
    targets, target_labels = parse_targets(raw_targets)
    tolerance = peak_matching.get("tolerance_keV", peak_matching.get("tolerance"))
    tolerance = None if tolerance is None else float(tolerance)

    return run_extraction(
        fits_dir=fits_dir,
        out_prefix=out_prefix,
        cal_a=cal_a,
        cal_b=cal_b,
        cal_c=cal_c,
        energy_unit=energy_unit,
        targets=targets,
        target_labels=target_labels,
        tolerance=tolerance,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Spectrix Gaussian fit results.")
    parser.add_argument(
        "input",
        type=Path,
        help=(
            "Either a YAML/JSON config file or a directory containing Spectrix .json fit files "
            "for legacy command-line mode."
        ),
    )
    parser.add_argument("--cal-m", type=float, default=None, help="Linear slope in E = m*x + b. Alias for --cal-b in quadratic notation.")
    parser.add_argument("--cal-a", type=float, default=None, help="Quadratic coefficient in E = a*x^2 + b*x + c")
    parser.add_argument("--cal-b", type=float, default=None, help="Linear coefficient. In linear mode this is the intercept for E = m*x + b; in quadratic mode this is b.")
    parser.add_argument("--cal-c", type=float, default=None, help="Constant term in E = a*x^2 + b*x + c")
    parser.add_argument("--energy-unit", default="keV", help="Energy unit label, e.g. keV or MeV")
    parser.add_argument("--targets", nargs="*", type=float, default=None, help="Expected state energies in same units as calibration")
    parser.add_argument("--out-prefix", type=Path, default=Path("spectrix_peaks"), help="Output prefix")
    args = parser.parse_args()

    # Recommended mode: python spectrix_extract_peaks.py spectrix_config.yaml
    if args.input.suffix.lower() in {".yaml", ".yml", ".json"} and args.input.is_file():
        long_path, wide_path, peak_index_area_path = run_from_config(args.input)
    else:
        # Legacy mode retained for quick one-off use.
        fits_dir = args.input

        # Normalize calibration inputs to one internal form: E = a*x^2 + b*x + c.
        if args.cal_m is not None:
            if args.cal_a is not None or args.cal_c is not None:
                raise SystemExit("Use either linear (--cal-m --cal-b) or quadratic (--cal-a --cal-b --cal-c), not both.")
            if args.cal_b is None:
                raise SystemExit("Linear calibration requires both --cal-m and --cal-b.")
            cal_a = 0.0
            cal_b = args.cal_m
            cal_c = args.cal_b
        elif args.cal_a is not None or args.cal_b is not None or args.cal_c is not None:
            if args.cal_a is None or args.cal_b is None or args.cal_c is None:
                raise SystemExit("Quadratic calibration requires --cal-a, --cal-b, and --cal-c.")
            cal_a = args.cal_a
            cal_b = args.cal_b
            cal_c = args.cal_c
        else:
            cal_a = cal_b = cal_c = None

        long_path, wide_path, peak_index_area_path = run_extraction(
            fits_dir=fits_dir,
            out_prefix=args.out_prefix,
            cal_a=cal_a,
            cal_b=cal_b,
            cal_c=cal_c,
            energy_unit=args.energy_unit,
            targets=args.targets,
        )

    print(f"Wrote: {long_path}")
    print(f"Wrote: {wide_path}")
    print(f"Wrote: {peak_index_area_path}")
    print("\nPeak-index area table preview:\n")
    print(peak_index_area_path.read_text())


if __name__ == "__main__":
    main()

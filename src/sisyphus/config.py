from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml

DEFAULT_CONSTANTS = {
    "avogadro": 6.02214076e23,
    "barn_to_cm2": 1e-24,
    "U_TO_MEV": 931.49410242,
}

@dataclass(frozen=True)
class Paths:
    peak_file: Path
    bci_file: Path
    fresco_dir: Path
    aslan_dir: Path
    output_subdir: Path

@dataclass(frozen=True)
class Reaction:
    name: str
    nuclei: list[str]
    beam_energy_MeV: float

@dataclass(frozen=True)
class PipelineConfig:
    paths: Paths
    reaction: Reaction
    target_thickness_g_cm2: float
    target_molar_mass_g_mol: float
    solid_angle_sr: float
    beam_Z: int
    sampling_rate_Hz: float
    constants: dict


def load_config(config_path: str | Path) -> PipelineConfig:
    config_path = Path(config_path).expanduser().resolve()

    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    # --- paths ---
    d = raw["directories"]
    peak_file = Path(d["peak_file"]).expanduser().resolve()
    bci_file = Path(d["bci_file"]).expanduser().resolve()
    fresco_dir = Path(d["fresco_dir"]).expanduser().resolve()
    aslan_dir = Path(d["aslan_dir"]).expanduser().resolve()
    output_subdir = Path(d["output_subdir"]).expanduser().resolve()

    # create output dir if needed
    output_subdir.mkdir(parents=True, exist_ok=True)

    # --- reaction ---
    r = raw["reactions"]
    reaction = Reaction(
        name=r["name"],
        nuclei=list(r["nuclei"]),
        beam_energy_MeV=float(r["beam_energy_MeV"]),
    )

    raw_constants = dict(raw.get("constants", {}))
    constants = DEFAULT_CONSTANTS | raw_constants
    constants = {k: float(v) for k, v in constants.items()}

    cfg = PipelineConfig(
        paths=Paths(
            peak_file=peak_file,
            bci_file=bci_file,
            output_subdir=output_subdir,
            fresco_dir=fresco_dir,
            aslan_dir=aslan_dir,
        ),
        reaction=reaction,
        target_thickness_g_cm2=float(raw["target"]["thickness_g_cm2"]),
        target_molar_mass_g_mol=float(raw["target"]["molar_mass_g_mol"]),
        solid_angle_sr=float(raw["detector"]["solid_angle_sr"]),
        beam_Z=int(raw["beam"]["proton_number_Z"]),
        sampling_rate_Hz=float(raw["beam"]["sampling_rate_Hz"]),
        constants=constants,
    )

    # friendly validation
    missing = []
    if not cfg.paths.peak_file.exists():
        missing.append(f"peak_file not found: {cfg.paths.peak_file}")
    if not cfg.paths.bci_file.exists():
        missing.append(f"bci_file not found: {cfg.paths.bci_file}")

    if missing:
        raise FileNotFoundError("Config paths invalid:\n  " + "\n  ".join(missing))

    return cfg
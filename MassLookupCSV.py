import requests
import csv
import io
from pathlib import Path

# constants
U_TO_MEV = 931.49410242
M_ELECTRON_U = 0.000548579909


def get_nuclear_mass(nuclide: str) -> float:
    url = "https://nds.iaea.org/relnsd/v1/data"
    params = {
        "fields": "ground_states",
        "nuclides": nuclide.lower()
    }

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    if not rows:
        raise ValueError(f"No data returned for {nuclide}")

    gs = rows[0]

    atomic_mass_u = float(gs["atomic_mass"])
    Z = int(gs["z"])

    nuclear_mass_u = atomic_mass_u * 1e-6 - Z * M_ELECTRON_U
    return nuclear_mass_u * U_TO_MEV


def fetch_levels(nuclide: str):
    """Fetch level data from IAEA API."""
    url = "https://nds.iaea.org/relnsd/v1/data"
    params = {
        "fields": "levels",
        "nuclides": nuclide.lower()
    }

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    return list(reader)


def write_levels_to_csv(nuclide: str, levels, outdir="levels_output"):
    """Write levels to CSV file."""
    Path(outdir).mkdir(parents=True, exist_ok=True)

    outfile = Path(outdir) / f"{nuclide}_levels.csv"

    if not levels:
        print(f"No levels found for {nuclide}")
        return

    # Use keys from API as headers
    fieldnames = levels[0].keys()

    with open(outfile, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(levels)

    print(f"Saved levels → {outfile}")


# Example usage
if __name__ == "__main__":
    nuclides = ["13C"]

    for nuc in nuclides:
        # mass
        m = get_nuclear_mass(nuc)
        print(f"{nuc}: {m:.3f} MeV/c^2")

        # levels
        levels = fetch_levels(nuc)
        write_levels_to_csv(nuc, levels)
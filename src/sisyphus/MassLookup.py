import requests
import csv
import io

"""
    Fetch nuclear mass (in MeV/c^2) for a given nuclide using IAEA LiveChart API.
    Subtracts electron masses from the atomic mass.

    Parameters
    ----------
    nuclide : str
        Nuclide symbol, e.g. "6Li", "9Be", "13C", "2H".

    Returns
    -------
    float
        Nuclear mass in MeV/c^2.

"""

# constants
U_TO_MEV = 931.49410242      # MeV per atomic mass unit
M_ELECTRON_U = 0.000548579909  # electron mass in atomic mass units (u)

def get_nuclear_mass(nuclide: str) -> float:

    url = "https://nds.iaea.org/relnsd/v1/data"
    params = {
        "fields": "ground_states",
        "nuclides": nuclide.lower()
             }
    
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()

    # parse CSV response
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    if not rows:
        raise ValueError(f"No data returned for {nuclide}")

    gs = rows[0]

    # atomic mass is in 'atomic_mass' (in u)
    if "atomic_mass" not in gs:
        raise KeyError(f"No atomic_mass field for {nuclide}: {gs.keys()}")
    atomic_mass_u = float(gs["atomic_mass"])

    # subtract electrons (in u) to get nuclear mass
    Z = int(gs["z"])
    nuclear_mass_u = atomic_mass_u*1e-6 - Z * M_ELECTRON_U

    # convert to MeV/c^2
    return nuclear_mass_u * U_TO_MEV

# # Example usage
# if __name__ == "__main__":
#     for nuc in ["6Li", "9Be", "2H", "13C"]:
#         m = get_nuclear_mass(nuc)
#         print(f"{nuc}: {m:.3f} MeV/c^2")

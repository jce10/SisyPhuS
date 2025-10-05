import numpy as np

def rutherford_normalization(E_lab_MeV, Z1, Z2, A_proj, A_targ,
                             theta_deg, monitor_counts, solid_angle_sr):
    """
    Compute Rutherford cross section and use monitor counts to determine beam normalization.
    
    Parameters
    ----------
    E_lab_MeV : float
        Beam energy in MeV (lab frame).
    Z1 : int
        Projectile charge (e.g. 3 for 6Li).
    Z2 : int
        Target charge (e.g. 4 for 9Be).
    A_proj : int
        Projectile mass number.
    A_targ : int
        Target mass number.
    theta_deg : float
        Scattering angle in lab (deg).
    monitor_counts : int
        Number of monitor counts recorded.
    solid_angle_sr : float
        Solid angle subtended by monitor detector (sr).
    
    Returns
    -------
    sigma_ruth_mb : float
        Rutherford cross section at that angle (mb/sr).
    N_beam : float
        Effective number of beam particles inferred from monitor counts.
    """
    # Convert to CM energy
    E_cm = E_lab_MeV * A_targ / (A_proj + A_targ)
    
    # Rutherford prefactor (in fm)
    prefactor = (Z1 * Z2 * 1.44) / (4 * E_cm)  # MeV·fm / MeV = fm
    prefactor_sq = prefactor**2  # fm^2
    
    # Angular factor
    theta_rad = np.radians(theta_deg)
    sigma_fm2 = prefactor_sq / (np.sin(theta_rad / 2)**4)
    
    # Convert to mb/sr (1 fm^2 = 0.01 barn = 10 mb)
    sigma_ruth_mb = sigma_fm2 * 10.0
    
    # Solve for number of beam particles
    # dσ/dΩ = (Y / (N_beam * ΔΩ)) => N_beam = Y / (σ * ΔΩ)
    N_beam = monitor_counts / (sigma_ruth_mb * 1e-27 * solid_angle_sr)
    
    return sigma_ruth_mb, N_beam


# Example: 6Li + 9Be at 32 MeV, monitor at 60 deg
sigma, Nbeam = rutherford_normalization(
    E_lab_MeV=32.0,
    Z1=3, Z2=4,
    A_proj=6, A_targ=9,
    theta_deg=60.0,
    monitor_counts=5000,
    solid_angle_sr=5e-3
)

print(f"Rutherford cross section = {sigma:.3f} mb/sr")
print(f"Beam particles inferred = {Nbeam:.3e}")

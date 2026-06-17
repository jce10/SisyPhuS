import numpy as np
from MassLookup import get_nuclear_mass


def lab_to_cm(E_lab, m_A, m_a, m_b, m_B):
    """
    Calculates conversion Jacobians for angles and differential cross-sections
    between the lab and center-of-mass (CM) frames for two-body reactions.

    Parameters
    ----------
    theta_lab_deg : float or ndarray
        Lab angle in degrees.
    E_lab : float
        Beam energy (MeV).
    m_proj : float
        Projectile mass (MeV/c^2).
    m_targ : float
        Target mass (MeV/c^2).
    m_eject : float
        Ejectile mass (MeV/c^2).
    m_recoil : float
        Recoil mass (MeV/c^2).
    Q : float
        Reaction Q-value (MeV).

    Returns
    -------
    theta_cm_deg : float or ndarray
        CM angle (degrees).
    """

    # Q-value of rxn (MeV)
    Q = (m_A + m_a) - (m_b + m_B)
    

    return Q


# Example usage
if __name__ == "__main__":
    
    #reaction info
    
    masses = []
    for nuc in ["58Ni", "6Li", "4He", "60Cu"]:
        m = get_nuclear_mass(nuc)
        masses.append(m)
        # print(f"{nuc}: {m:.3f} MeV/c^2") #optional print

    
    Q_val = lab_to_cm(32, masses[0], masses[1], masses[2], masses[3])
    print("Reaction: 29Si(d,p)30Si")
    print(f"Masses (MeV/c^2): {masses[0]:.3f} (29Si), {masses[1]:.3f} (2H), {masses[2]:.3f} (1H), {masses[3]:.3f} (30Si)")
    print(f"Q-value: {Q_val:.3f} MeV")
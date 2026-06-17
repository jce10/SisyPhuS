import numpy as np
from sisyphus.MassLookup import get_nuclear_mass


def calculate_q_value(m_A, m_a, m_b, m_B):
    """
    Intendid to calculate the Q-value of a nuclear reaction in MeV

    Parameters
    ----------
    m_A : float
    Target mass (MeV/c^2).
    m_a : float
        Projectile mass (MeV/c^2).
    m_b : float
        Ejectile mass (MeV/c^2).
    m_B : float
        Recoil mass (MeV/c^2).
    Q : float
        Reaction Q-value (MeV).

    Returns
    -------
    Q : float
        Q-value (MeV).
    """

    # Q-value of rxn (MeV)
    Q = (m_A + m_a) - (m_b + m_B)
    

    return Q


if __name__ == "__main__":

    # ======================================
    # Reaction definition. Change this!!!
    # ======================================

    reaction = ["9Be", "6Li", "4He", "11B"]

    A, a, b, B = reaction

    # ======================================
    # Mass lookup
    # ======================================

    masses = []

    for nuc in reaction:
        m = get_nuclear_mass(nuc)
        masses.append(m)

        # Optional verbose print
        # print(f"{nuc}: {m:.3f} MeV/c^2")

    m_A, m_a, m_b, m_B = masses

    # ======================================
    # Q-value calculation
    # ======================================

    Q_val = calculate_q_value(m_A, m_a, m_b, m_B)

    # ======================================
    # Output
    # ======================================

    print("\n" + "=" * 45)
    print(f"\tReaction: {A}({a},{b}){B}")
    print("=" * 45)

    print("\nMasses (MeV):")
    print(f"{A:>6}: {m_A/931.5 :.3f} u x 931.5 MeV = {m_A:.3f} MeV/c^2")
    print(f"{a:>6}: {m_a/931.5 :.3f} u x 931.5 MeV = {m_a:.3f} MeV/c^2")
    print(f"{b:>6}: {m_b/931.5 :.3f} u x 931.5 MeV = {m_b:.3f} MeV/c^2")
    print(f"{B:>6}: {m_B/931.5 :.3f} u x 931.5 MeV = {m_B:.3f} MeV/c^2")

    print(f"\nQ-value: {Q_val:.3f} MeV\n")
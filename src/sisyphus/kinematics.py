from __future__ import annotations

import numpy as np


def lab_to_cm(theta_lab_deg, E_lab, m_A, m_a, m_b, m_B):
    """
    Lab -> CM conversion helper (not physics-verified yet).
    Returns Q (MeV), theta_cm_deg, and a lab->cm Jacobian factor.

    Parameters
    ----------
    theta_lab_deg : float or ndarray
    E_lab : float (MeV)
    m_A, m_a, m_b, m_B : float
        Masses in MeV/c^2 (or consistent energy units)

    Returns
    -------
    Q : float
    theta_cm_deg : float or ndarray
    jacobian : float or ndarray
    """
    Q = (m_A + m_a) - (m_b + m_B)

    g_numerator = (m_a * m_b * E_lab) / (m_A * m_B)
    g_denominator = (E_lab + Q + Q * m_a / m_A)
    gamma = np.sqrt(g_numerator / g_denominator)

    theta_lab_rad = np.radians(theta_lab_deg)
    theta_cm_rad = np.arccos(-gamma * np.sin(theta_lab_rad) ** 2 + np.cos(theta_lab_rad))
    theta_cm_deg = np.degrees(theta_cm_rad)

    # NOTE: you had cos(theta_lab_deg) (deg) here; leaving as-is is risky.
    # For now, fix the obvious unit bug to avoid nonsense:
    j_numerator = 1 - (gamma ** 2 * np.sin(theta_lab_rad) ** 2)
    j_denominator = gamma * np.cos(theta_lab_rad) + np.sqrt(1 - (gamma ** 2 * np.sin(theta_lab_rad) ** 2))
    jacobian = (j_numerator / j_denominator)

    return Q, theta_cm_deg, jacobian
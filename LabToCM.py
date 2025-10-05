import numpy as np

def lab_to_cm(theta_lab_deg, dsdomega_lab, m_b, M_B):
    """
    Convert lab-frame differential cross sections to CM-frame.
    
    Parameters:
        theta_lab_deg : array-like, lab angles in degrees
        dsdomega_lab : array-like, differential cross sections in lab frame (same units)
        m_b : float, mass of scattered particle
        M_B : float, mass of recoil particle
    
    Returns:
        theta_cm_deg : array, CM angles in degrees
        dsdomega_cm : array, CM differential cross sections
    """
    theta_lab = np.radians(theta_lab_deg)
    
    # Solve for theta_cm using the kinematic relation
    theta_cm = np.arctan2(np.sin(theta_lab), np.cos(theta_lab) - m_b/M_B)
    
    # Jacobian for lab -> cm
    jacobian = (1 + (m_b/M_B) * np.cos(theta_cm))**3 / (1 + (m_b/M_B)**2 + 2*(m_b/M_B)*np.cos(theta_cm))
    
    dsdomega_cm = dsdomega_lab * jacobian
    theta_cm_deg = np.degrees(theta_cm)
    
    return theta_cm_deg, dsdomega_cm



# lab data
lab_angles = np.array([7, 10, 12, 15, 17, 20, 22])  # degrees
dsdomega_lab = np.array([5.0, 4.2, 3.5, 2.7, 1.8, 2.6, 5.1])  # mb/sr

# particle masses in u (or any consistent units)
m_b = 2.0  # e.g., deuteron
M_B = 13.0  # e.g., 13C

theta_cm, dsdomega_cm = lab_to_cm(lab_angles, dsdomega_lab, m_b, M_B)

print("CM Angles (deg):", theta_cm)
print("CM dσ/dΩ (mb/sr):", dsdomega_cm)

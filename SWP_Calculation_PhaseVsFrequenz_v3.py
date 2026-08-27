
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# Thermische Substratparameter (Armco-Reineisen)
K_SUBSTRAT = 73.0       
RHO_SUBSTRAT = 7870.0   
C_SUBSTRAT = 460.0      

# Parameter Nitrierschicht
RHO_LAYER = 7870.0
C_LAYER = 460.0
K_LAYER_DEFAULT = 14.4  


def get_effusivity(k, rho, c):
    return np.sqrt(rho * k * c)

def get_diffusivity(k, rho, c):
    return k / (rho * c)


def fit_model_d_only(f, d_um, k_L=K_LAYER_DEFAULT):
    """ Exakte Formel 2 nach Mikulewitsch et al. """
    omega = 2.0 * np.pi * f
    d = d_um * 1e-6

    b_L = get_effusivity(k_L, RHO_LAYER, C_LAYER)
    b_S = get_effusivity(K_SUBSTRAT, RHO_SUBSTRAT, C_SUBSTRAT)
    alpha_L = get_diffusivity(k_L, RHO_LAYER, C_LAYER)

    mu_L = np.sqrt(2.0 * alpha_L / omega)
    term_d_mu = (2.0 * d) / mu_L

    b_diff = b_S - b_L
    b_sum  = b_S + b_L

    numerator = (b_S**2 - b_L**2) * (np.exp(term_d_mu) - np.exp(-term_d_mu)) + 2.0 * (b_S**2 - b_L**2) * np.sin(term_d_mu)
    denominator = -(b_diff**2) + (b_sum**2) * np.exp(2.0 * term_d_mu) + 2.0 * (b_S**2 - b_L**2) * np.sin(term_d_mu)

    phi_rad = np.arctan(numerator / denominator)
    return np.degrees(phi_rad)


def process_live_measurement(f_measured, phi_measured, initial_d_guess=10.0):
    """
    Diese Funktion wird in der GUI nach dem Mess-Sweep aufgerufen.
    """
    # 1. Non-linear Curve Fitting
    popt, pcov = curve_fit(
        fit_model_d_only, 
        f_measured, 
        phi_measured, 
        p0=[initial_d_guess], 
        bounds=(0.1, 500.0)
    )

    d_fitted_um = popt[0]
    d_error_um = np.sqrt(np.diag(pcov))[0]

    # 2. VERIFIKATION & FIT-QUALITÄT (R²-Wert berechnen)
    phi_model_fitted = fit_model_d_only(f_measured, d_fitted_um)
    residuals = phi_measured - phi_model_fitted
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((phi_measured - np.mean(phi_measured))**2)
    
    # Bestimmtheitsmaß R²
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

    # 3. Konsolen-Log
    print("=" * 60)
    print("  LIVE-EVALUATION & VERIFIKATION")
    print("=" * 60)
    print(f"  Gefittete Schichtdicke d:  {d_fitted_um:.2f} ± {d_error_um:.2f} µm")
    print(f"  Bestimmtheitsmaß (R²):     {r_squared:.4f}")
    if r_squared > 0.95:
        print("  Status:                   Fit ist valide und hochpräzise.")
    else:
        print("  Warnung:                  R² niedrig. Messdaten prüfen!")
    print("=" * 60)

    # Rückgabe an die GUI: Dicke, Fehler, R²-Wert und gefittete Kurve
    return d_fitted_um, d_error_um, r_squared, phi_model_fitted



# ==============================================================================

# DEMO / DIRECT EXECUTION

# ==============================================================================


if __name__ == "__main__":

    print("Starte Demo-Test mit synthetischen PTR-Messdaten...\n")

    # 1. Messdaten des Lock-In-Verstärkers simulieren (z. B. 10 Hz bis 250 kHz)

    np.random.seed(42)

    f_simulated = np.logspace(1, 5.4, 100)

    # Reale Schichtdicke von d = 14.2 µm simulieren

    d_true = 45.0

    noise = np.random.normal(0, 0.35, size=len(f_simulated)) # Experimentelles Rauschen

    phi_simulated = fit_model_d_only(f_simulated, d_true) + noise


    # 2. Auswertungsfunktion aufrufen

    d_fit, d_err, r2, phi_fit = process_live_measurement(f_simulated, phi_simulated)


    # 3. Ergebnis in Matplotlib darstellen

    plt.figure(figsize=(9, 5))

    sqrt_omega_sim = np.sqrt(2 * np.pi * f_simulated)

    f_dense = np.logspace(1, 5.4, 500)

    sqrt_omega_dense = np.sqrt(2 * np.pi * f_dense)

    phi_dense_fit = fit_model_d_only(f_dense, d_fit)


    plt.plot(sqrt_omega_sim, phi_simulated, 'ro', alpha=0.7, label='Messdaten (Lock-In)')

    plt.plot(sqrt_omega_dense, phi_dense_fit, 'b-', linewidth=2, label=f'Fit (d = {d_fit:.2f} µm, R² = {r2:.4f})')

    plt.xlabel(r'$\sqrt{\omega}$ [$\sqrt{\mathrm{Hz}}$]', fontsize=11)

    plt.ylabel('Phase φ [°]', fontsize=11)

    plt.title('Photothermische Radiometrie - Nitrierschichtdicken-Fit', fontsize=12, fontweight='bold')

    plt.grid(True, linestyle=':', alpha=0.7)

    plt.legend(fontsize=10)

    plt.tight_layout()

    plt.show()
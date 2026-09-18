"""
Photothermische Radiometrie (PTR) - Modellbasierte Bestimmung der
Nitrierschichtdicke aus Phasenverschiebungs-Frequenzsweeps.

Basierend auf:
M. Mikulewitsch et al.: "Influences on Quantitative Nitriding Layer
Thickness Measurements using Model-Based Photothermal Radiometry",
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# Tkinter für den Datei-Explorer importieren
import tkinter as tk
from tkinter import filedialog


def select_file_via_explorer(title="Datei auswählen"):

    # Öffnet ein Datei-Explorer-Fenster zur Auswahl einer Datei.

    root = tk.Tk()
    root.withdraw()  # Versteckt das Hauptfenster von Tkinter
    root.attributes('-topmost', True)  # Bringt den Explorer in den Vordergrund

    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=[("Textdateien", "*.txt"), ("Alle Dateien", "*.*")]
    )
    root.destroy()
    return file_path


# ---------------------------------------------------------------------
# 1) Einlesen der Lock-in-Messdateien
# ---------------------------------------------------------------------
def parse_lockin_file(path):
    
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [l.rstrip("\n") for l in f]

    # --- a) Frequenz-Tabelle am Dateianfang einlesen ---
    freqs = []
    i = 1  # Zeile 0 ist der Tabellenkopf "A(v) f(hz) ..."
    while i < len(lines):
        parts = lines[i].split()
        if len(parts) >= 2:
            try:
                f_val = float(parts[1])
                freqs.append(f_val)
                i += 1
                continue
            except ValueError:
                break
        else:
            break
    freq = np.array(freqs, dtype=float)
    n_freq = len(freq)
    if n_freq == 0:
        raise ValueError(f"Konnte keine Frequenz-Tabelle in {path} finden.")

    # --- b) Datenblöcke suchen (Zeilen, die NUR eine ganze Zahl enthalten) ---
    block_start_idx = [idx for idx in range(i, len(lines))
                        if lines[idx].strip().isdigit()]
    if not block_start_idx:
        raise ValueError(f"Keine Messblöcke in Datei gefunden: {path}")

    amp_blocks, phase_blocks = [], []
    for start in block_start_idx:
        data_lines = lines[start + 1: start + 1 + n_freq]
        amps, phases = [], []
        for dl in data_lines:
            parts = dl.split()
            if len(parts) < 2:
                continue
            amps.append(float(parts[0]))
            phases.append(float(parts[1]))
        if len(amps) == n_freq:
            amp_blocks.append(amps)
            phase_blocks.append(phases)

    amp_blocks = np.array(amp_blocks)      # (n_blocks, n_freq)
    phase_blocks = np.array(phase_blocks)  # (n_blocks, n_freq)
    n_blocks = amp_blocks.shape[0]

    # --- c) Zirkulare Mittelung der Phase über die Wiederholungen ---
    phase_rad = np.deg2rad(phase_blocks)
    mean_vec = np.mean(np.exp(1j * phase_rad), axis=0)
    phase_mean = np.rad2deg(np.angle(mean_vec)) % 360.0
    phase_std = np.rad2deg(np.std(phase_rad, axis=0))
    amp_mean = np.mean(amp_blocks, axis=0)

    return freq, phase_mean, phase_std, amp_mean, n_blocks


def unwrap_phase_deg(freq, phase_deg):
    """
    Entfaltet (unwrapped) eine über der Frequenz gemessene Phase in Grad,
    sortiert dabei zusätzlich nach aufsteigender Frequenz.
    """
    order = np.argsort(freq)
    f_sorted = freq[order]
    phase_unwrapped = np.rad2deg(np.unwrap(np.deg2rad(phase_deg[order])))
    return f_sorted, phase_unwrapped


# ---------------------------------------------------------------------
# 2) Physikalisches Modell
# ---------------------------------------------------------------------
def thermal_effusivity(k, rho, C):
    """b = sqrt(rho * k * C)   [Wärmeeindringkoeffizient / Effusivität]"""
    return np.sqrt(rho * k * C)


def surface_temperature_phase(freq, d, k_L, b_S, rho_L, C_L):
    """
    Berechnet die Phase (in Grad) der komplexen Oberflächentemperatur.
    """
    omega = 2.0 * np.pi * np.asarray(freq, dtype=float)
    alpha_L = k_L / (rho_L * C_L)
    b_L = thermal_effusivity(k_L, rho_L, C_L)

    mu_L = np.sqrt(2.0 * alpha_L / omega)      # thermische Diffusionslänge
    sigma_L = (1.0 + 1j) / mu_L                 # komplexe Wärmewellenzahl

    R = (b_S - b_L) / (b_S + b_L)              # Reflexionskoeffizient
    x = np.exp(-2.0 * sigma_L * d)              # gedämpfte Wärmewelle (Weg 2d)

    T0 = -1.0 / sigma_L * (1.0 + R * x) / (1.0 - R * x)
    return np.rad2deg(np.angle(T0))


def make_phase_signal_model(b_S, rho_S, C_S, layer_rho=None, layer_C=None):
    """
    Erzeugt die Modellfunktion Phi(freq, d, k_L) für curve_fit.
    """
    rho_L = layer_rho if layer_rho is not None else rho_S
    C_L = layer_C if layer_C is not None else C_S

    def phi_ref(freq):
        return surface_temperature_phase(freq, 0.0, 1.0, b_S, rho_L, C_L)

    def Phi_model(freq, d, k_L):
        phi_probe = surface_temperature_phase(freq, d, k_L, b_S, rho_L, C_L)
        return phi_ref(freq) - phi_probe

    return Phi_model


# ---------------------------------------------------------------------
# 3) Fit-Routine: Schichtdicke & Wärmeleitfähigkeit bestimmen
# ---------------------------------------------------------------------
def fit_layer_parameters(freq_hz, Phi_deg, b_S, rho_S, C_S,
                         d0=5e-6, kL0=10.0,
                         d_bounds=(0.1e-6, 100e-6),
                         kL_bounds=(0.5, 100.0)):
    """
    Führt die nichtlineare Kleinste-Quadrate-Anpassung der Modellfunktion durch.
    """
    model_func = make_phase_signal_model(b_S, rho_S, C_S)

    popt, pcov = curve_fit(
        model_func, freq_hz, Phi_deg,
        p0=[d0, kL0],
        bounds=([d_bounds[0], kL_bounds[0]], [d_bounds[1], kL_bounds[1]]),
        maxfev=20000,
    )
    perr = np.sqrt(np.diag(pcov))
    d_fit, kL_fit = popt
    d_err, kL_err = perr
    return d_fit, kL_fit, d_err, kL_err, model_func


# ---------------------------------------------------------------------
# 4) Gesamtablauf
# ---------------------------------------------------------------------
if __name__ == "__main__":

    # --- Materialparameter des Substrats (z.B. 42CrMo4) ---
    k_S = 42.0       # W/(m*K)   Wärmeleitfähigkeit Substrat
    rho_S = 7800.0   # kg/m^3    Dichte Substrat
    C_S = 460.0      # J/(kg*K)  spezifische Wärmekapazität Substrat
    b_S = thermal_effusivity(k_S, rho_S, C_S)
    print(f"Substrat-Effusivität b_S = {b_S:.1f} Ws^0.5/(m^2 K)")

    # --- 1. Dateiauswahl via Explorer: Referenzmessung ---
    print("\nBitte wählen Sie im Explorer die REFERENZMESSUNG (unnitrierte Probe) aus...")
    ref_path = select_file_via_explorer(title="1. Referenzmessung auswählen (unnitriert)")

    if not ref_path:
        print("[Abbruch] Es wurde keine Referenzdatei ausgewählt.")
        sys.exit()

    print(f"Ausgewählte Referenzdatei: {ref_path}")
    freq_ref, phase_ref, phase_ref_std, amp_ref, n_ref = parse_lockin_file(ref_path)
    print(f"Referenzmessung eingelesen: {n_ref} Wiederholungen, {len(freq_ref)} Frequenzpunkte")
    f_ref, phase_ref_unwr = unwrap_phase_deg(freq_ref, phase_ref)

    # --- 2. Dateiauswahl via Explorer: Probenmessung ---
    print("\nBitte wählen Sie im Explorer die PROBENMESSUNG (nitrierte Probe) aus...")
    probe_path = select_file_via_explorer(title="2. Probenmessung auswählen (nitriert)")

    if not probe_path:
        print("[Abbruch] Es wurde keine Probenmessungsdatei ausgewählt.")
        sys.exit()

    print(f"Ausgewählte Probendatei: {probe_path}")

    try:
        freq_probe, phase_probe, phase_probe_std, amp_probe, n_probe = \
            parse_lockin_file(probe_path)
        f_probe, phase_probe_unwr = unwrap_phase_deg(freq_probe, phase_probe)

        assert np.allclose(f_ref, f_probe), \
            "Referenz- und Probenmessung verwenden unterschiedliche Frequenzstützstellen!"
        freq_common = f_ref

        # --- photothermisches Phasensignal (Referenz minus Probe) ---
        Phi = phase_ref_unwr - phase_probe_unwr

        # --- nichtlinearen Fit durchführen ---
        d_fit, kL_fit, d_err, kL_err, model_func = fit_layer_parameters(
            freq_common, Phi, b_S, rho_S, C_S
        )

        print("\n==================================================")
        print("Ergebnis der modellbasierten Schichtdickenbestimmung:")
        print(f"  Schichtdicke          d   = {d_fit*1e6:.2f} +- {d_err*1e6:.2f} µm")
        print(f"  Wärmeleitfähigkeit   k_L  = {kL_fit:.2f} +- {kL_err:.2f} W/(m*K)")
        print("==================================================\n")

        # --- Plot ---
        freq_fine = np.logspace(np.log10(freq_common.min()),
                                 np.log10(freq_common.max()), 500)
        Phi_fit_curve = model_func(freq_fine, d_fit, kL_fit)

        plt.figure(figsize=(7, 5))
        plt.plot(np.sqrt(2*np.pi*freq_common), Phi, "o",
                 label="Messdaten $\\Phi(\\omega) = \\varphi_{ref} - \\varphi_{probe}$")
        plt.plot(np.sqrt(2*np.pi*freq_fine), Phi_fit_curve, "--",
                 label="angepasste Modellfunktion")
        plt.xlabel(r"$\sqrt{\omega}$ in $\sqrt{Hz}$")
        plt.ylabel(r"referenzkorrigierte Phasendifferenz $\Phi$ in °"
                   "\n(nicht die absolute Lock-in-Rohphase!)")
        plt.title(f"d = {d_fit*1e6:.2f} µm,  k_L = {kL_fit:.2f} W/(m·K)")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    except Exception as e:
        print(f"\n[Fehler bei der Auswertung] {e}")
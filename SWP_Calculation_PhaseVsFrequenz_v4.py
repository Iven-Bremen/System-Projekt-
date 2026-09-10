import os
import csv
import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import tkinter as tk
from tkinter import messagebox, filedialog


# THERMISCHE MATERIALPARAMETER

# Substrat: Armco-Reineisen
K_SUBSTRAT = 73.0      # Wärmeleitfähigkeit Substrat [W/(m·K)]
RHO_SUBSTRAT = 7870.0  # Dichte Substrat [kg/m³]
C_SUBSTRAT = 460.0     # Spezifische Wärmekapazität Substrat [J/(kg·K)]

# Nitrierschicht (Verbindungsschicht)
RHO_LAYER = 7870.0     # Dichte Schicht [kg/m³]
C_LAYER = 460.0        # Spezifische Wärmekapazität Schicht [J/(kg·K)]
K_LAYER_DEFAULT = 14.4 # Standard-Wärmeleitfähigkeit Schicht [W/(m·K)]


# MATH. PHYSIK-MODELL (Formel 2 nach Mikulewitsch et al.)

def get_effusivity(k, rho, c):
    return np.sqrt(k * rho * c)

def get_diffusivity(k, rho, c):
    return k / (rho * c)

def fit_model_d_only(f, d_um, k_L=K_LAYER_DEFAULT):
    omega = 2.0 * np.pi * f
    d = d_um * 1e-6

    b_L = get_effusivity(k_L, RHO_LAYER, C_LAYER)
    b_S = get_effusivity(K_SUBSTRAT, RHO_SUBSTRAT, C_SUBSTRAT)
    alpha_L = get_diffusivity(k_L, RHO_LAYER, C_LAYER)

    mu_L = np.sqrt(2.0 * alpha_L / omega)
    term_d_mu = (2.0 * d) / mu_L

    b_diff = b_S - b_L
    b_sum = b_S + b_L

    numerator = (b_S ** 2 - b_L ** 2) * (np.exp(term_d_mu) - np.exp(-term_d_mu)) + 2.0 * (b_S ** 2 - b_L ** 2) * np.sin(term_d_mu)
    denominator = -(b_diff ** 2) + (b_sum ** 2) * np.exp(2.0 * term_d_mu) + 2.0 * (b_S ** 2 - b_L ** 2) * np.sin(term_d_mu)

    phi_rad = np.arctan(numerator / denominator)
    return np.degrees(phi_rad)


# EVALUATIONS- UND POPUP-FUNKTIONEN

def show_error_popup(title, message):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    messagebox.showerror(title, message)
    root.destroy()


# CSV-IMPORT MIT 13 SPALTEN, STRUKTUR-VALIDIERUNG & ZUORDNUNG

# Liest das Log zeilenweise chronologisch aus und merkt sich jeweils die zuletzt gesetzte Frequenz (FREQ),
# um sie den nachfolgenden Phasenwerten (PHAS) korrekt zuzuordnen und mathematisch sortiert zu plotten.
def import_csv_file():
    # Öffnet den Explorer im aktuellen Skriptverzeichnis
    initial_dir = os.path.dirname(os.path.abspath(__file__))
    
    file_path = filedialog.askopenfilename(
        initialdir=initial_dir,
        title="CSV-Messlog auswählen",
        filetypes=[("CSV Dateien", "*.csv")]
    )

    if not file_path:
        return None, None

    # Format-Prüfung (.csv)
    if not file_path.lower().endswith('.csv'):
        show_error_popup("Formatfehler", "Die ausgewählte Datei ist keine gültige .csv Datei.")
        return None, None

    # 13 erwartete Spalten gemäss Log-Struktur
    expected_headers = [
        'Date', 'Time', 'Ms', 'Category', 'Tag', 'State', 
        'Message', 'Value', 'Info', 'AdditionalMessage', 
        'AdditionalValue', 'AdditionalInfo', 'Else'
    ]

    try:
        with open(file_path, mode='r', encoding='utf-8', newline='') as f:
            sample = f.read(2048)
            f.seek(0)
            delimiter = ';' if ';' in sample else ','
            
            reader = csv.reader(f, delimiter=delimiter)
            header = next(reader, None)

            if header is None:
                raise ValueError("Die CSV-Datei ist leer.")

            cleaned_header = [col.strip().lstrip('\ufeff') for col in header]

            if cleaned_header != expected_headers:
                raise ValueError(
                    f"Ungültige Spaltenstruktur!\n\n"
                    f"Erwartet ({len(expected_headers)} Spalten): {expected_headers}\n\n"
                    f"Gefunden ({len(cleaned_header)} Spalten): {cleaned_header}"
                )

            f.seek(0)
            dict_reader = csv.DictReader(f, delimiter=delimiter)
            
            f_measured = []
            phi_measured = []
            current_freq = None


            for row in dict_reader:
                if row.get('Tag') == 'SR830':
                    msg = row.get('Message')
                    try:
                        val = float(row.get('Value'))
                        if msg == 'FREQ':
                            current_freq = val
                        elif msg == 'PHAS':
                            if current_freq is not None:
                                f_measured.append(current_freq)
                                phi_measured.append(val)
                    except (ValueError, TypeError):
                        continue

            if not f_measured or not phi_measured:
                raise ValueError("Es konnten keine verwertbaren 'FREQ'-/'PHAS'-Paare für SR830 gefunden werden.")

            print(f"Erfolgreich geladen: {os.path.basename(file_path)} ({len(f_measured)} Wertepaare)")
            return np.array(f_measured), np.array(phi_measured)

    except Exception as e:
        show_error_popup("CSV Import-Fehler", f"Fehler beim Laden der Datei:\n{str(e)}")
        return None, None


def process_live_measurement(f_measured, phi_measured, initial_d_guess=10.0, show_plot=True):
    try:
        if f_measured is None or phi_measured is None:
            raise ValueError("Keine Daten übergeben (Lock-In Verstärker nicht verbunden).")

        f_measured = np.asarray(f_measured, dtype=float)
        phi_measured = np.asarray(phi_measured, dtype=float)

        if f_measured.size == 0 or phi_measured.size == 0:
            raise ValueError("Keine Werte gegeben. Die Daten-Arrays sind leer.")

        if len(f_measured) != len(phi_measured):
            raise ValueError("Frequenz- und Phasen-Arrays haben unterschiedliche Längen.")

    except Exception as e:
        show_error_popup("Messdaten-Fehler", f"Es konnten keine Daten ausgewertet werden:\n{str(e)}")
        return None, None, None, None

    # FIT BERECHNEN (Non-Linear Least Squares)
    try:
        popt, pcov = curve_fit(
            fit_model_d_only,
            f_measured,
            phi_measured,
            p0=[initial_d_guess],
            bounds=(0.1, 500.0)
        )
        d_fitted_um = popt[0]
        d_error_um = np.sqrt(np.diag(pcov))[0]
    except Exception as e:
        show_error_popup("Fit-Fehler", f"Der mathematische Fit ist fehlgeschlagen:\n{str(e)}")
        return None, None, None, None

    # VERIFIKATION & R²-BERECHNUNG
    phi_model_fitted = fit_model_d_only(f_measured, d_fitted_um)
    residuals = phi_measured - phi_model_fitted
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((phi_measured - np.mean(phi_measured)) ** 2)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

    print("=" * 60)
    print("  PTR MESSDATEN-EVALUATION & VERIFIKATION")
    print("=" * 60)
    print(f"  Gemessene Punkte:           {len(f_measured)}")
    print(f"  Frequenzbereich:            {f_measured.min():.1f} Hz bis {f_measured.max():.1f} Hz")
    print("-" * 60)
    print(f"  --> GEFITTETE SCHICHTDICKE d: {d_fitted_um:.2f} ± {d_error_um:.2f} µm")
    print(f"  --> BESTIMMTHEITSMASS (R²):  {r_squared:.4f}")

    if r_squared >= 0.95:
        print("  --> STATUS:                  FIT VALIDE UND PRÄZISE")
    else:
        print("  --> WARNUNG:                 R² NIEDRIG! MESSDATEN ODER RAUSCHEN PRÜFEN.")
    print("=" * 60)

    if show_plot:
        plt.figure(figsize=(9, 5))
        sqrt_omega_meas = np.sqrt(2 * np.pi * f_measured)

        f_dense = np.logspace(np.log10(f_measured.min()), np.log10(f_measured.max()), 500)
        sqrt_omega_dense = np.sqrt(2 * np.pi * f_dense)
        phi_dense_fit = fit_model_d_only(f_dense, d_fitted_um)

        plt.plot(sqrt_omega_meas, phi_measured, 'o', color='darkred', alpha=0.7, label='Lock-In Messdaten')
        plt.plot(sqrt_omega_dense, phi_dense_fit, color='darkblue', linewidth=2,
                 label=f'Fit (d = {d_fitted_um:.2f} µm, R² = {r_squared:.4f})')

        plt.xlabel(r'$\sqrt{\omega}$ [$\sqrt{\mathrm{Hz}}$]', fontsize=11)
        plt.ylabel('Phase φ [°]', fontsize=11)
        plt.title('PTR Live-Messung — Nitrierschichtdicke', fontsize=12, fontweight='bold')
        plt.grid(True, linestyle=':', alpha=0.7)
        plt.legend(fontsize=10)
        plt.tight_layout()
        plt.show()

    return d_fitted_um, d_error_um, r_squared, phi_model_fitted


if __name__ == "__main__":
    # Aufruf der Import-Funktion über den Dateidialog
    f_csv, phi_csv = import_csv_file()
    
    if f_csv is not None and phi_csv is not None:
        process_live_measurement(f_csv, phi_csv, initial_d_guess=20.0)
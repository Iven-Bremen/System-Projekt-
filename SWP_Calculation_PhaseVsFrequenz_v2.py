"""
σ(f) = (1+j)·√(π·f/α₁) = thermische Wellenzahl
R_1/2 = (1-Kc)/(1+Kc) = thermischer Reflexionskoeffizient
z(f,d) = (1 + R_1/2 * e^(-2σd)) / (1 - R_1/2 * e^(-2σd)) = komplexe Reflexionsantwort
Φ(f) = arg[z(f,d)] - arg[z(f,0)] = Phasensignal vs. Referenz

Einfache Einzelschicht-Näherung φ = -arctan(d·√(πf/α)) wird diesmal net verwendet.

Code zur Berechnung des Modells der Nitrierschicht mit Berücksichtigung der Reflexion
der Wärmewelle an der Grenzfläche, damit Phasen-Höcker (lokales Maximum) entstehen,
die auch in realen Messkurven auftreten.

    φ: Phase [°]
    f: Frequenz [Hz]
    d: Nitrierschichtdicke [µm]
    α_1: thermische Diffusivität der Nitrierschicht [µm²/s] (also wie schnell ein
         Material sich auf eine definierte Temperatur aufwärmen oder abkühlen lässt)
    Kc : Effusivitätskontrast Kc = b_2 / b_1 (Substrat / Nitrierschicht)
         (Veränderung der Materialeigenschaften an der Grenze zwischen zwei werkstoffen:
         Dichte, Wärmeleitfähigkeit, u.Ä.)

Benutzereingabe: Phase φ [°] → Berechnung der Schichtdicke d [µm]
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.optimize import curve_fit, brentq



# wie tief und wie schnell die Wärme des Lasers in das Material eindringt (Alpha in µm²/s),
ALPHA_UM2_S = 3.5e6   # UM2_S = µm²/s in 10^(-6)

# Effusivitätskontrast Kc = e_Substrat / e_Nitrierschicht
# Kc > 1 bedeutet: Substrat (Stahl) ist thermisch effusiver
# hier: Kc = 2/1 = 2.0 (repräsentiert das typische physikalische Materialverhältnis bei nitrierten Stählen)
KC_DEFAULT = 2.0

# für die Wiederverwendbarkeit Definitionen ('def') aufstellen

# räumliche Ausbreitung und Dämpfung einer gedämpften Wärmewelle (= periodisch erwärmt (Bsp.: Laser, Licht)) im Material
def thermal_wavenumber(f, alpha=ALPHA_UM2_S):
    """
    Komplexe thermische Wellenzahl:  σ(f) = (1+j)·√(π·f/α)
    f     : Frequenz [Hz]
    alpha : thermische Diffusivität [µm²/s]
    """
    return (1.0 + 1.0j) * np.sqrt(np.pi * f / alpha)


# beschreibt wie stark eine thermische Wärmewelle an der Grenzfläche zwischen zwei Schichten reflektiert wird
def reflection_coefficient(Kc=KC_DEFAULT):
    """
    Thermischer Reflexionskoeffizient an der Grenzfläche Schicht/Substrat:
        R_1/2 = (e1 - e2) / (e1 + e2) = (1 - Kc) / (1 + Kc)
    Kc : Effusivitätskontrast Kc = e2/e1
    """
    return (1.0 - Kc) / (1.0 + Kc)


# berechnet die theoretische Phasenverschiebung Phi(f) des photothermischen Signals
# in Abhängigkeit von der Anregungsfrequenz f und der Nitrierschichtdicke d.
def phase_model(f, d, alpha=ALPHA_UM2_S, Kc=KC_DEFAULT):
    """
    Vollständiges Zweischicht-Reflexionsmodell :
        z(f,d) = (1 + R_1/2*e^(-2σ·d)) / (1 - R_1/2*e^(-2σ·d))
        Φ(f)   = arg[z(f,d)] - arg[z(f,0)]

    Da z(f,0) = (1+R_1/2)/(1-R_1/2) reell und positiv ist (Phase 0°) (der Startwert ist d = 0, da d (Schichtdicke)
    nicht negativ sein kann, reduziert sich die Differenz auf Φ(f) = arg[z(f,d)]. Rückgabe in Grad.
    """
    sigma = thermal_wavenumber(f, alpha)
    R12 = reflection_coefficient(Kc)
    exp_term = np.exp(-2.0 * sigma * d)
    z = (1.0 + R12 * exp_term) / (1.0 - R12 * exp_term)
    return np.degrees(np.angle(z))


# der primitive Ansatz mit der "falschen" Formel:
    def phase_model_simplified(f, d, alpha=ALPHA_UM2_S):
        """
        Vereinfachtes Einzelschicht-Modell (frühere Version, nur zum Vergleich):
            φ(f) = -arctan(d·√(πf/α))
        Bildet keine Grenzflächenreflexion ab → kein Phasen-Höcker, weicht daher
        von realen Messkurven (z. B. Bild 5a in Mikulewitsch et al.) deutlich ab.
        """
    return -np.degrees(np.arctan(d * np.sqrt(np.pi * f / alpha)))


# Die Funktion phase_to_thickness macht genau die Umkehrung (Inversion) von phase_model:
# Sie nimmt einen gemessenen Phasenwert φ bei einer bestimmten Frequenz f und berechnet daraus
# die unbekannte Nitrierschichtdicke d in Mikrometern
def phase_to_thickness(phi_deg, f_hz, alpha=ALPHA_UM2_S, Kc=KC_DEFAULT,
                       d_min=1.0, d_max=50.0, n_scan=4000):
    # typische Nitrierschichten bei Stählen liegen industriell fast immer im Bereich zwischen 1µm und 50µm.
    # Abtastrate zwischen 1µm und 50µm = 4000
    """
    Invertiert das Zweischicht-Modell numerisch: sucht d mit phase_model(f,d) = φ.

    Für eine belastbare Schichtdickenbestimmung sollte statt eines einzelnen
    (φ,f)-Punkts eine vollständige Frequenzsweep-Messung mit fit_phase_curve()
    gefittet werden — die Einzelpunkt-Inversion dient nur zur Abschätzung.
    """
    # also tasten wir die Dicke von 1 bis 50 Mikrometern ab, um die wirkliche Schichtdicke einzugrenzen
    d_scan = np.linspace(d_min, d_max, n_scan)
    diff = phase_model(f_hz, d_scan, alpha, Kc) - phi_deg
    sign_changes = np.where(np.diff(np.sign(diff)) != 0)[0]
    if len(sign_changes) == 0:
        print(f"[Warnung] Keine Lösung im Bereich {d_min:.1f}…{d_max:.0f} µm gefunden.")
        return np.nan

    i0 = sign_changes[0]
    try:
        d_root = brentq(lambda d: phase_model(f_hz, d, alpha, Kc) - phi_deg, d_scan[i0], d_scan[i0 + 1])
        return d_root
    except Exception as e:
        print(f"[Warnung] Inversion fehlgeschlagen: {e}")
        return np.nan


# Vergleichswerte aus der PDF
def get_literature_data():
    """
    Repräsentative PTR-Phasenkurven für verschiedene Nitrierschichtdicken,
    berechnet mit dem Zweischicht-Reflexionsmodell.
    42CrMo4, 550 °C – abgeleitet aus Mikulewitsch et al. (2022) und
    Bento et al. (2013, QIRT).

    Frequenzraster: 1 Hz – 100 kHz (logarithmisch)
    Schichtdicken  [µm]: 2.5, 5.0, 7.5, 10.0, 15.0
    """
    f_hz = np.logspace(0, 5, 300)   # 1 Hz … 100 kHz

    thicknesses = [2.5, 5.0, 7.5, 10.0, 15.0]   # µm
    curves = {d: phase_model(f_hz, d) for d in thicknesses}

    return f_hz, thicknesses, curves


# generiert eine vollständige gemessene Phasenkurve über den gesamten Frequenzverlauf und bestimmt die Schichtdicke d
# über einen Nichtlinearen Kleinste-Quadrate-Regression (Regressionsanalyse)
def fit_phase_curve(f_data, phi_data, Kc=KC_DEFAULT):
    """
    Fittet (curve fitting) d in Φ(f) = arg[(1+R_1/2*e^(-2σd))/(1-R_1/2*e^(-2σd))] an Messdaten.
    α und Kc werden als bekannt angenommen (ALPHA_UM2_S, Kc).
    """
    def model_fixed_alpha(f, d):
        return phase_model(f, d, Kc=Kc)

    try:
        popt, pcov = curve_fit(model_fixed_alpha, f_data, phi_data,
                               p0=[5.0], bounds=(0.01, 100.0), maxfev=10000)
        perr = np.sqrt(np.diag(pcov))
        return popt[0], perr[0]
    # exception wird geworfen, wenn keine Konvergenz / ungültige Rechenwerte / Grenzen überschritten
    except Exception as e:
        print(f"[Warnung] Fit fehlgeschlagen: {e}")
        return None, None


# Plot
def plot_all(f_hz, thicknesses, curves, phi_query, f_query, d_query):
    """
    Layout:
      Links  : Phase-vs-Frequenz-Kurven für alle Literatur-Schichtdicken
               (Zweischicht-Reflexionsmodell) + markierte Abfrage (φ, f) → d
      Rechts : Datentabelle (Literaturdaten + Abfrageergebnis)
    """
    # Helles Design: weißer Hintergrund, schwarze Beschriftungen
    BG_COLOR     = "#ffffff"
    PANEL_BG     = "#ffffff"
    TABLE_BG     = "#f5f5f5"
    TEXT_COLOR   = "#000000"
    GRID_COLOR   = "#bbbbbb"
    BORDER_COLOR = "#333333"
    GREEN        = "#1a9e1a"

    # Farben je Nitrierschichtdicke bleiben unverändert
    COLORS = ["#00d4ff", "#ff6b35", "#a855f7", "#ffd700", "#39ff14"]

    fig = plt.figure(figsize=(15, 7))
    fig.patch.set_facecolor(BG_COLOR)

    gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.38, width_ratios=[1.6, 1.0])
    ax_phase = fig.add_subplot(gs[0])
    ax_table = fig.add_subplot(gs[1])

    # Phase-vs-Frequenz-Kurven
    ax_phase.set_facecolor(PANEL_BG)
    ax_phase.spines[:].set_color(BORDER_COLOR)
    ax_phase.tick_params(colors=TEXT_COLOR)
    ax_phase.xaxis.label.set_color(TEXT_COLOR)
    ax_phase.yaxis.label.set_color(TEXT_COLOR)
    ax_phase.title.set_color(TEXT_COLOR)

    sqrt_omega_hz = np.sqrt(2.0 * np.pi * f_hz)

    for i, d in enumerate(thicknesses):
        phi_curve = curves[d]
        ax_phase.plot(sqrt_omega_hz, phi_curve, color=COLORS[i], linewidth=2.2,
                     label=f"d = {d: 0.1f} µm", zorder=3)


    # Berechnete Abfrage-Kurve (grau gestrichelt)
    phi_query_curve = phase_model(f_hz, d_query)
    ax_phase.plot(sqrt_omega_hz, phi_query_curve,
                 color="#555555", linewidth=2.0, linestyle="--",
                 dashes=(6, 3), zorder=4,
                 label=f"Berechnet: d = {d_query: 0.2f} µm")


    # Abfrage-Marker
    sqrt_omega_query = np.sqrt(2.0 * np.pi * f_query)
    ax_phase.axvline(sqrt_omega_query, color=GREEN, linestyle="--", linewidth=1.4, alpha=0.85, zorder=5)
    ax_phase.axhline(phi_query, color=GREEN, linestyle="--", linewidth=1.4, alpha=0.85, zorder=5)
    ax_phase.scatter([sqrt_omega_query], [phi_query], color=GREEN, s=130, zorder=7,
                     edgecolors="black", linewidths=1.2,
                     label=f"Abfrage: φ={phi_query: 0.1f}° → d={d_query: 0.2f} µm")

    ax_phase.annotate(
        f"  d = {d_query: 0.2f} µm",
        xy=(sqrt_omega_query, phi_query),
        xytext=(sqrt_omega_query * 1.15, phi_query + 2),
        color=GREEN, fontsize=11, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.5),
    )

    ax_phase.set_xlabel(r"$\sqrt{\omega}$ in $\sqrt{\mathrm{Hz}}$", fontsize=12)
    ax_phase.set_ylabel("Phase φ [°]", fontsize=12)
    ax_phase.set_title(
        "PTR-Phasenverschiebungs-Simulation  |  Nitrierschichtdickenbestimmung\n"
        r"Zweischicht-Reflexionsmodell: $\Phi(f)=\arg\!\left[\dfrac{1+R_{12}e^{-2\sigma d}}{1-R_{12}e^{-2\sigma d}}\right]$",
        fontsize=13, fontweight="bold", pad=12
    )
    ax_phase.legend(fontsize=9, facecolor="#eeeeee", labelcolor=TEXT_COLOR,
                    framealpha=0.9, loc="best")
    ax_phase.set_xlim(0, sqrt_omega_hz[-1])
    ax_phase.grid(True, color=GRID_COLOR, alpha=0.6, linestyle=":")


    # Datentabelle
    ax_table.set_facecolor(TABLE_BG)
    ax_table.set_xticks([])
    ax_table.set_yticks([])
    for spine in ax_table.spines.values():
        spine.set_color(BORDER_COLOR)
        spine.set_linewidth(1.5)

    # Tabellenkopf
    # Syntax f"{'─'*38}\n: eine gestrichelte Linie aus 38 strichen
    header = f"{'─'*38}\n  PTR-SIMULATION  |  DATENTABELLE\n{'─'*38}\n"


    # Spaltenüberschriften
    col_head = f"  {'d [µm]':>8}  {'φ @ 1 Hz':>10}  {'φ @ 100 Hz':>12}  {'φ @ 10 kHz':>11}\n"
    col_sep  = f"  {'─'*8}  {'─'*10}  {'─'*12}  {'─'*11}\n"

    rows = ""
    check_freqs = [1.0, 100.0, 1e4]
    for d in thicknesses:
        phi_vals = [phase_model(fq, d) for fq in check_freqs]
        rows += f"  {d:>8.1f}  {phi_vals[0]:>10.2f}°  {phi_vals[1]:>10.2f}°  {phi_vals[2]:>10.2f}°\n"

    sep2 = f"{'─'*38}\n"

    # Parameter-Block
    params = (
        f"\n  Modell:  Zweischicht-Reflexion\n"
        f"  σ(f)    = (1+j)√(πf/α)\n"
        f"  R12     = (1-Kc)/(1+Kc)\n"
        f"  α       = {ALPHA_UM2_S:.2e} µm²/s\n"
        f"  Kc      = {KC_DEFAULT:.2f}\n"
        f"  Material: 42CrMo4\n"
        f"  Prozess:  Gasnitrieren, 550 °C\n"
    )

    sep3 = f"\n{'─'*38}\n"

    # Abfrage-Ergebnis
    result = (
        f"   Abfrage-Phase:  φ = {phi_query: 0.1f}°\n"
        f"   Frequenz:       f = {f_query: 0.1f} Hz\n"
        f"   Schichtdicke:   d = {d_query: 0.3f} µm\n"
    )

    sep4 = f"{'─'*38}\n"

    source = (
        f"\n  Quelle:\n"
        f"  Mikulewitsch et al. (2022)\n"
        f"  HTM J. Heat Treatm. Mat.\n"
        f"  77 (5), 357–373\n"
        f"  Bennett & Patty (1981), Appl. Opt.\n"
        f"  Bento et al. (2013), QIRT\n"
    )

    full_text = header + col_head + col_sep + rows + sep2 + params + sep3 + result + sep4 + source

    ax_table.text(
        0.04, 0.97, full_text,
        transform=ax_table.transAxes,
        fontsize=8.5, verticalalignment="top",
        fontfamily="monospace", color=TEXT_COLOR,
    )

    # plt.tight_layout()

    # Ermittelt den Ordner, in dem diese Python-Datei liegt und schmeißt das den Plot als Bild da rein
    save_dir = os.path.dirname(os.path.abspath(__file__))
    save_path = os.path.join(save_dir, "ptr_phase_simulation.png")
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.show()
    print(f"\n[✓] Grafik gespeichert: {save_path}")


# Eingabe-Dialog

def ask_inputs_gui():
    """Tkinter-Popup: Eingabe von Phase [°] und Frequenz [Hz]."""
    try:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        # minvalue sollte eigentlich 0 sein, aber -5 als Akzeptanztoleranz falls -0.4° oder so
        # LockInAmplifier kann eigentlich nur -90° bis 0°. Aber positive Konvention
        phi = simpledialog.askfloat(
            "PTR-Simulation",
            "Gemessene Phase φ eingeben [°]:\n"
            "Eingabebereich von 0° bis 90°",
            minvalue=-5.0, maxvalue=90.0
        )
        if phi is None:
            root.destroy()
            return None, None

        f = simpledialog.askfloat(
            "PTR-Simulation",
            "Modulationsfrequenz f eingeben [Hz]:\n"
            "(Eingabebereich von 0.1Hz bis 1MHz)",
            minvalue=0.1, maxvalue=1e6
        )
        root.destroy()
        return phi, f

    except Exception:
        return None, None


def ask_inputs_console():
    """Fallback-Konsoleneingabe: Phase [°] und Frequenz [Hz]."""
    print("\nBereich Phase: 0° … +90°  |  Frequenz: 0.1 … 1 000 000 Hz")
    while True:
        try:
            phi = float(input("Gemessene Phase φ [°]: "))
            if not (-5.0 <= phi <= 90.0):
                print("Phase muss zwischen 0° und +90° liegen.")
                continue
            break
        except ValueError:
            print("Ungültige Eingabe.")

    while True:
        try:
            f = float(input("Modulationsfrequenz f [Hz]: "))
            if f <= 0:
                print("Frequenz muss positiv sein.")
                continue
            break
        except ValueError:
            print("Ungültige Eingabe.")

    return phi, f


# Hauptprogramm

def main():
    print("=" * 50)
    print("  PTR-Phasenverschiebungs-Simulation")
    print("  Software zur Berechnung der Nitrierschicht ")
    print("=" * 50)

    # Referenz-Daten aus dem Modell / Literatur laden
    f_hz, thicknesses, curves = get_literature_data()

    # Benutzereingabe abfragen (GUI -> Konsole -> Fallback)
    phi_query, f_query = ask_inputs_gui()
    if phi_query is None or f_query is None:
        phi_query, f_query = ask_inputs_console()
    if phi_query is None:
        phi_query, f_query = 8.0, 1000.0   # Fallback

    # Schichtdicke berechnen
    d_query = phase_to_thickness(phi_query, f_query)

    print(f"\n{'=' * 45}")
    print(f"  Phase:         {phi_query: 0.2f} °")
    print(f"  Frequenz:      {f_query: 0.1f} Hz")
    print(f"  Schichtdicke:  {d_query: 0.3f} µm")
    print(f"  α (Nitrid):    {ALPHA_UM2_S: 0.2e} µm²/s")
    print(f"  Kc:            {KC_DEFAULT: 0.2f}")
    print(f"{'=' * 45}\n")

    plot_all(f_hz, thicknesses, curves, phi_query, f_query, d_query)
    # plot_all(phi_query, f_query, d_query)

if __name__ == "__main__":
    main()

# Version2
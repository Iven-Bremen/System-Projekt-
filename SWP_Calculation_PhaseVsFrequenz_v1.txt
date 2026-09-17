"""
PTR-Phasenverschiebungs-Simulation
====================================
Physikalische Grundlage: Photothermalradiometrie (PTR)
    φ(f) = -arctan( d · √(π·f / α) )

    φ  : Phase [°]
    f  : Modulationsfrequenz [Hz]
    d  : Nitrierschichtdicke [µm]
    α  : thermische Diffusivität der Nitrierschicht [µm²/s]

Literaturdaten:
    42CrMo4, Gasnitrieren, 550 °C
    α_Nitrid ≈ 3.5 × 10⁶ µm²/s  (Fe₂₋₃N / Fe₄N, Literaturwert)
    Schichtdicken aus Mikulewitsch et al. (2022), Abb. 9

Benutzereingabe: Phase φ [°]  → Berechnung der Schichtdicke d [µm]
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.optimize import curve_fit


# Physikalisches Modell

# Thermische Diffusivität der Nitrierschicht (Fe₂₋₃N), Literaturwert
ALPHA_UM2_S = 3500.0   # µm²/s

def phase_model(f, d, alpha=ALPHA_UM2_S):
    """
    PTR-Phasenmodell:  φ(f) = -arctan( d · √(π·f / α) )
    Rückgabe in Grad.
    f     : Frequenz [Hz]
    d     : Schichtdicke [µm]
    alpha : thermische Diffusivität [µm²/s]
    """
    return -np.degrees(np.arctan(d * np.sqrt(np.pi * f / alpha)))


def phase_to_thickness(phi_deg, f_hz, alpha=ALPHA_UM2_S):
    """
    Invertiert das PTR-Modell:  d = tan(-φ) / √(π·f/α)
    φ muss negativ sein (Phasenrückgang).
    """
    phi_rad = np.radians(phi_deg)
    denom = np.sqrt(np.pi * f_hz / alpha)
    if denom == 0:
        return 0.0
    d = np.tan(-phi_rad) / denom
    return max(0.0, d)


# Literaturdaten

def get_literature_data():
    """
    Repräsentative PTR-Phasenkurven für verschiedene Nitrierschichtdicken.
    42CrMo4, 550 °C – abgeleitet aus Mikulewitsch et al. (2022) und
    Bento et al. (2013, QIRT) via PTR-Modell φ = -arctan(d·√(πf/α)).

    Frequenzraster: 1 Hz – 100 kHz (logarithmisch)
    Schichtdicken  [µm]: 2.5, 5.0, 7.5, 10.0, 15.0
    """
    f_hz = np.logspace(0, 5, 300)   # 1 Hz … 100 kHz

    thicknesses = [2.5, 5.0, 7.5, 10.0, 15.0]   # µm
    curves = {d: phase_model(f_hz, d) for d in thicknesses}

    return f_hz, thicknesses, curves


# Fit an gemessene Phasenkurve

def fit_phase_curve(f_data, phi_data):
    """
    Fittet d in φ(f) = -arctan(d·√(πf/α)) an Messdaten.
    α wird als bekannt (ALPHA_UM2_S) angenommen.
    """
    def model_fixed_alpha(f, d):
        return phase_model(f, d)

    try:
        popt, pcov = curve_fit(model_fixed_alpha, f_data, phi_data,
                               p0=[5.0], bounds=(0.01, 100.0), maxfev=10000)
        perr = np.sqrt(np.diag(pcov))
        return popt[0], perr[0]
    except Exception as e:
        print(f"[Warnung] Fit fehlgeschlagen: {e}")
        return None, None


# Plot

def plot_all(f_hz, thicknesses, curves, phi_query, f_query, d_query):
    """
    Layout:
      Links  : Phase-vs-Frequenz-Kurven für alle Literatur-Schichtdicken
               + markierte Abfrage (φ, f) → d
      Rechts : Datentabelle (Literaturdaten + Abfrageergebnis)
    """
    DARK_BG = "#1a1a2e"
    MID_BG  = "#16213e"
    ACCENT  = "#0f3460"
    CYAN    = "#00d4ff"
    ORANGE  = "#ff6b35"
    GREEN   = "#39ff14"
    YELLOW  = "#ffd700"
    WHITE   = "#e0e0e0"
    GRAY    = "#888888"

    COLORS = ["#00d4ff", "#ff6b35", "#a855f7", "#ffd700", "#39ff14"]

    fig = plt.figure(figsize=(15, 7))
    fig.patch.set_facecolor(DARK_BG)

    gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.38, width_ratios=[1.6, 1.0])
    ax_phase = fig.add_subplot(gs[0])
    ax_table = fig.add_subplot(gs[1])

    # Phase-vs-Frequenz-Kurven
    ax_phase.set_facecolor(MID_BG)
    ax_phase.spines[:].set_color(GRAY)
    ax_phase.tick_params(colors=WHITE)
    ax_phase.xaxis.label.set_color(WHITE)
    ax_phase.yaxis.label.set_color(WHITE)
    ax_phase.title.set_color(WHITE)

    for i, d in enumerate(thicknesses):
        phi_curve = curves[d]
        ax_phase.semilogx(f_hz, phi_curve, color=COLORS[i], linewidth=2.2,
                          label=f"d = {d:.1f} µm", zorder=3)

    # Berechnete Abfrage-Kurve (grau gestrichelt)
    phi_query_curve = phase_model(f_hz, d_query)
    ax_phase.semilogx(f_hz, phi_query_curve,
                      color="#aaaaaa", linewidth=2.0, linestyle="--",
                      dashes=(6, 3), zorder=4,
                      label=f"Berechnet: d = {d_query:.2f} µm")

    # Abfrage-Marker
    ax_phase.axvline(f_query, color=GREEN, linestyle="--", linewidth=1.4, alpha=0.85, zorder=5)
    ax_phase.axhline(phi_query, color=GREEN, linestyle="--", linewidth=1.4, alpha=0.85, zorder=5)
    ax_phase.scatter([f_query], [phi_query], color=GREEN, s=130, zorder=7,
                     edgecolors="white", linewidths=1.2,
                     label=f"Abfrage: φ={phi_query:.1f}° → d={d_query:.2f} µm")

    ax_phase.annotate(
        f"  d = {d_query:.2f} µm",
        xy=(f_query, phi_query),
        xytext=(f_query * 3, phi_query + 3),
        color=GREEN, fontsize=11, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.5),
    )

    ax_phase.set_xlabel("Modulationsfrequenz f [Hz]", fontsize=12)
    ax_phase.set_ylabel("Phase φ [°]", fontsize=12)
    ax_phase.set_title(
        "PTR-Phasenverschiebungs-Simulation  |  Nitrierschichtdickenbestimmung\n"
        r"$\varphi(f) = -\arctan\!\left(d\sqrt{\pi f/\alpha}\right)$",
        fontsize=14, fontweight="bold", pad=12
    )
    ax_phase.legend(fontsize=9, facecolor=ACCENT, labelcolor=WHITE,
                    framealpha=0.85, loc="lower left")
    ax_phase.set_xlim(f_hz[0], f_hz[-1])
    ax_phase.set_ylim(-92, 5)
    ax_phase.grid(True, color=GRAY, alpha=0.3, linestyle=":")

    # Datentabelle
    ax_table.set_facecolor(ACCENT)
    ax_table.set_xticks([])
    ax_table.set_yticks([])
    for spine in ax_table.spines.values():
        spine.set_color(CYAN)
        spine.set_linewidth(2)

    # Tabellenkopf
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
        f"\n  Modell:  φ = -arctan(d·√(πf/α))\n"
        f"  α       = {ALPHA_UM2_S:.2e} µm²/s\n"
        f"  Material: 42CrMo4\n"
        f"  Prozess:  Gasnitrieren, 550 °C\n"
        f"  Kₙ = 3 ,  Kc = 0.1\n"
    )

    sep3 = f"\n{'─'*38}\n"

    # Abfrage-Ergebnis
    result = (
        f"  ► Abfrage-Phase:  φ = {phi_query:.1f}°\n"
        f"  ► Frequenz:       f = {f_query:.1f} Hz\n"
        f"  ► Schichtdicke:   d = {d_query:.3f} µm\n"
    )

    sep4 = f"{'─'*38}\n"

    source = (
        f"\n  Quelle:\n"
        f"  Mikulewitsch et al. (2022)\n"
        f"  HTM J. Heat Treatm. Mat.\n"
        f"  77 (5), 357–373\n"
        f"  Bento et al. (2013), QIRT\n"
    )

    full_text = header + col_head + col_sep + rows + sep2 + params + sep3 + result + sep4 + source

    ax_table.text(
        0.04, 0.97, full_text,
        transform=ax_table.transAxes,
        fontsize=8.5, verticalalignment="top",
        fontfamily="monospace", color=WHITE,
    )

    plt.tight_layout()

    save_dir = "/mnt/user-data/outputs/" if os.path.exists("/mnt/user-data/outputs/") else "."
    save_path = os.path.join(save_dir, "ptr_phase_simulation.png")
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
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

        phi = simpledialog.askfloat(
            "PTR-Simulation",
            "Gemessene Phase φ eingeben [°]:\n"
            "(typischer Bereich: -90° … 0°)",
            minvalue=-90.0, maxvalue=0.0
        )
        if phi is None:
            root.destroy()
            return None, None

        f = simpledialog.askfloat(
            "PTR-Simulation",
            "Modulationsfrequenz f eingeben [Hz]:\n"
            "(z. B. 1, 10, 100, 1000, 10000)",
            minvalue=0.1, maxvalue=1e6
        )
        root.destroy()
        return phi, f

    except Exception:
        return None, None


def ask_inputs_console():
    """Fallback-Konsoleneingabe: Phase [°] und Frequenz [Hz]."""
    print("\nBereich Phase: -90° … 0°  |  Frequenz: 0.1 … 1 000 000 Hz")
    while True:
        try:
            phi = float(input("Gemessene Phase φ [°]: "))
            if not (-90.0 <= phi <= 0.0):
                print("Phase muss zwischen -90° und 0° liegen.")
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
    print("  φ(f) = -arctan( d · √(πf/α) )")
    print("=" * 50)

    # Literaturdaten
    f_hz, thicknesses, curves = get_literature_data()

    # Benutzereingabe
    phi_query, f_query = ask_inputs_gui()
    if phi_query is None or f_query is None:
        phi_query, f_query = ask_inputs_console()
    if phi_query is None:
        phi_query, f_query = -25.0, 100.0   # Fallback

    # Schichtdicke berechnen
    d_query = phase_to_thickness(phi_query, f_query)

    print(f"\n{'=' * 45}")
    print(f"  Phase:         {phi_query:.2f} °")
    print(f"  Frequenz:      {f_query:.1f} Hz")
    print(f"  Schichtdicke:  {d_query:.3f} µm")
    print(f"  α (Nitrid):    {ALPHA_UM2_S:.2e} µm²/s")
    print(f"{'=' * 45}\n")

    plot_all(f_hz, thicknesses, curves, phi_query, f_query, d_query)


if __name__ == "__main__":
    main()


"""
Nitrierschicht-Wachstumssimulation
===================================
Physikalische Grundlage: Parabolisches Wachstumsgesetz (Fick'sche Diffusion)
    d(t) = k * sqrt(t)   bzw.   d(t) = a * sqrt(t) + b

Die PTR-Messdaten (TXT) werden eingelesen und visualisiert.
Für die Schichtdicken-Zeitreihe werden Beispielwerte aus der Literatur
(Mikulewitsch et al. 2022, Dong et al. 2018) verwendet, da die TXT-Datei
einen einzelnen Frequenzscan enthält (keine Zeitreihe).

HINWEIS: Benutzereingabe erfolgt in Sekunden.
         Interne Berechnung und Literaturdaten bleiben in Minuten.
"""

import sys
import os
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.optimize import curve_fit


# Physikalisches Modell

def parabolic(t, a, b):
    """d(t) = a * sqrt(t) + b   (parabolisches Wachstumsgesetz)"""
    return a * np.sqrt(t) + b


def parabolic_simple(t, k):
    """d(t) = k * sqrt(t)   (rein parabolisch, d(0)=0)"""
    return k * np.sqrt(t)


# PTR-Rohdaten einlesen (Mit re ohne Pandas)

def read_ptr_data(filepath):
    """Liest die PTR-Messdatei mit regulären Ausdrücken zeilenweise ein."""
    frequenzen = []
    amplituden = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for zeile in f:
                zeile = zeile.strip()
                # Header und leere Zeilen überspringen
                if not zeile or "A(v)" in zeile or "Amplitude" in zeile or "Phase" in zeile:
                    continue

                # Alle Zahlenwerte der Zeile extrahieren
                werte = re.findall(r"[-+]?\d*\.\d+|\d+", zeile)
                if len(werte) >= 2:
                    f_val = float(werte[0])
                    a_val = float(werte[-1])  # Letzte Spalte greifen

                    if f_val > 0:
                        frequenzen.append(f_val)
                        amplituden.append(a_val)

        if len(frequenzen) > 0:
            return {
                "f_hz": np.array(frequenzen),
                "A_v": np.array(amplituden),
                "length": len(frequenzen)
            }
        return None

    except Exception as e:
        print(f"[Warnung] Konnte TXT nicht mit re einlesen: {e}")
        return None


# Beispiel-Zeitreihe aus Literatur

def get_literature_data():
    """
    Messdaten aus Mikulewitsch et al. (2022) / Dong et al. (2018):
    42CrMo4, 550°C, KN=3, KC=0.1  →  Schichtdicke [µm] über Zeit [min]
    Werte abgelesen aus Abbildung 9 (Mikulewitsch 2022).
    """
    t_min = np.array([0, 7, 15, 22, 29, 36, 43, 52, 59, 67,
                      74, 81, 88, 95, 103, 120])
    d_um = np.array([0, 2.5, 3.8, 4.6, 5.2, 5.7, 6.1, 6.5, 6.9, 7.2,
                     7.5, 7.7, 7.9, 8.1, 8.4, 8.9])
    return t_min, d_um


# Fit & Vorhersage

def fit_growth(t_data, d_data):
    """Fittet das parabolische Wachstumsgesetz an Messdaten."""
    try:
        popt, pcov = curve_fit(parabolic, t_data[1:], d_data[1:],
                               p0=[0.8, 0.0], bounds=(0, [20.0, 5.0]), maxfev=5000)
        perr = np.sqrt(np.diag(pcov))
        return popt, perr, "parabolic"
    except Exception:
        pass

    popt, pcov = curve_fit(parabolic_simple, t_data[1:], d_data[1:], p0=[0.8])
    perr = np.sqrt(np.diag(pcov))
    return popt, perr, "simple"


def predict(t_query, popt, model):
    """Berechnet Schichtdicke für gegebene Zeit (in Minuten)."""
    if model == "parabolic":
        return parabolic(t_query, *popt)
    else:
        return parabolic_simple(t_query, *popt)


# Plot

def plot_all(t_data, d_data, popt, model, t_query_min, t_query_sec, d_query, ptr_data=None):
    """Erstellt das Hauptfenster mit Wachstumskurve und optionalem PTR-Plot.

    t_query_min : Abfragezeit in Minuten (intern, für Fit-Berechnung)
    t_query_sec : Abfragezeit in Sekunden (für Anzeige gegenüber dem Benutzer)
    """
    has_ptr = ptr_data is not None and ptr_data["length"] > 5

    # ÄNDERUNG: constrained_layout=True sorgt für automatischen Platz oben beim Titel
    fig = plt.figure(figsize=(14, 8) if has_ptr else (10, 6), constrained_layout=True)
    fig.patch.set_facecolor("#1a1a2e")

    if has_ptr:
        gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.35)
        ax_growth = fig.add_subplot(gs[:, 0])
        ax_ptr = fig.add_subplot(gs[0, 1])
        ax_info = fig.add_subplot(gs[1, 1])
    else:
        gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.35)
        ax_growth = fig.add_subplot(gs[0, 0])
        ax_info = fig.add_subplot(gs[0, 1])
        ax_ptr = None

    DARK_BG = "#1a1a2e"
    MID_BG  = "#16213e"
    ACCENT  = "#0f3460"
    CYAN    = "#00d4ff"
    ORANGE  = "#ff6b35"
    GREEN   = "#39ff14"
    WHITE   = "#e0e0e0"
    GRAY    = "#888888"

    # Wachstumskurve
    ax_growth.set_facecolor(MID_BG)
    ax_growth.spines[:].set_color(GRAY)
    ax_growth.tick_params(colors=WHITE)
    ax_growth.xaxis.label.set_color(WHITE)
    ax_growth.yaxis.label.set_color(WHITE)
    ax_growth.title.set_color(WHITE)

    t_smooth = np.linspace(0, max(t_data) * 1.3, 400)
    d_smooth = predict(t_smooth, popt, model)
    ax_growth.plot(t_smooth, d_smooth, color=CYAN, linewidth=2.5,
                   label="Parabolisches Fit  $d = a\\sqrt{t}+b$", zorder=3)

    ax_growth.fill_between(t_smooth, d_smooth * 0.95, d_smooth * 1.05,
                           color=CYAN, alpha=0.15, label="±5 % Unsicherheit")

    ax_growth.scatter(t_data, d_data, color=ORANGE, s=60, zorder=5,
                      label="Messdaten (Literatur)", edgecolors="white", linewidths=0.5)

    ax_growth.axvline(t_query_min, color=GREEN, linestyle="--", linewidth=1.5, alpha=0.8)
    ax_growth.axhline(d_query, color=GREEN, linestyle="--", linewidth=1.5, alpha=0.8)
    ax_growth.scatter([t_query_min], [d_query], color=GREEN, s=120, zorder=6,
                      edgecolors="white", linewidths=1.2,
                      label=f"Abfrage: t={t_query_sec:.0f} s → {d_query:.2f} µm")

    ax_growth.annotate(
        f" {d_query:.2f} µm",
        xy=(t_query_min, d_query),
        xytext=(t_query_min + max(t_data) * 0.05, d_query + 0.3),
        color=GREEN, fontsize=11, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.5),
    )

    ax_growth.set_xlabel("Zeit t [min]", fontsize=12)
    ax_growth.set_ylabel("Verbindungsschichtdicke d [µm]", fontsize=12)
    ax_growth.set_title("Nitrierschicht-Wachstum\n(Parabolisches Gesetz)", fontsize=13)
    ax_growth.legend(fontsize=9, facecolor=ACCENT, labelcolor=WHITE, framealpha=0.8)
    ax_growth.set_xlim(0, max(t_data) * 1.3)
    ax_growth.set_ylim(0, max(d_data) * 1.4)
    ax_growth.grid(True, color=GRAY, alpha=0.3, linestyle=":")

    # PTR-Rohdaten
    if ax_ptr is not None and has_ptr:
        ax_ptr.set_facecolor(MID_BG)
        ax_ptr.spines[:].set_color(GRAY)
        ax_ptr.tick_params(colors=WHITE)
        ax_ptr.xaxis.label.set_color(WHITE)
        ax_ptr.yaxis.label.set_color(WHITE)
        ax_ptr.title.set_color(WHITE)

        f_vals = ptr_data["f_hz"]
        a_vals = ptr_data["A_v"]
        ax_ptr.semilogx(f_vals, a_vals, color=ORANGE, linewidth=2)
        ax_ptr.fill_between(f_vals, a_vals, alpha=0.2, color=ORANGE)
        ax_ptr.set_xlabel("Frequenz f [Hz]", fontsize=10)
        ax_ptr.set_ylabel("Signal-Amplitude / Phase", fontsize=10)
        ax_ptr.set_title("PTR-Messung (Rohdaten)", fontsize=11)
        ax_ptr.grid(True, color=GRAY, alpha=0.3, linestyle=":")

    # Info-Box
    ax_info.set_facecolor(ACCENT)
    ax_info.set_xticks([])
    ax_info.set_yticks([])
    for spine in ax_info.spines.values():
        spine.set_color(CYAN)
        spine.set_linewidth(2)

    if model == "parabolic":
        formel = f"d(t) = {popt[0]:.4f} · √t + {popt[1]:.4f}"
    else:
        formel = f"d(t) = {popt[0]:.4f} · √t"

    wachstumsrate = popt[0] / (2 * np.sqrt(t_query_min)) if t_query_min > 0 else popt[0]

    info_text = (
        f"{'─' * 32}\n"
        f"  NITRIERSIMULATION\n"
        f"{'─' * 32}\n\n"
        f"  Prozess:    Gasnitrieren\n"
        f"  Material:   42CrMo4\n"
        f"  Temperatur: 550 °C\n"
        f"  Kₙ = 3,  Kc = 0.1\n\n"
        f"{'─' * 32}\n"
        f"  Fit-Modell:\n"
        f"  {formel}\n\n"
        f"{'─' * 32}\n"
        f"  ► Abfragezeit:   {t_query_sec:.0f} s  ({t_query_min:.2f} min)\n"
        f"  ► Schichtdicke:  {d_query:.2f} µm\n"
        f"  ► Wachstumsrate: {wachstumsrate:.4f} µm/min\n\n"
        f"{'─' * 32}\n"
        f"  Quelle: Mikulewitsch et al.\n"
        f"  HTM J. Heat Treatm. Mat.\n"
        f"  77 (2022) 5, 357–373\n"
    )

    ax_info.text(
        0.05, 0.95, info_text,
        transform=ax_info.transAxes,
        fontsize=10, verticalalignment="top",
        fontfamily="monospace", color=WHITE,
    )

    # ÄNDERUNG: y-Parameter entfernt, da constrained_layout die Positionierung optimiert
    fig.suptitle("Nitrierschicht-Wachstumssimulation  |  PTR-gestützte Schichtdickenbestimmung",
                 fontsize=14, color=WHITE, fontweight="bold")

    # ÄNDERUNG: plt.tight_layout() wurde gelöscht, um Konflikte zu vermeiden

    save_dir = "/mnt/user-data/outputs/" if os.path.exists("/mnt/user-data/outputs/") else "."
    save_path = os.path.join(save_dir, "nitriding_simulation.png")

    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.show()
    print(f"\n[✓] Grafik gespeichert: {save_path}")


# Eingabe-Dialog

def ask_time_gui(t_data):
    """Tkinter-Popup für Zeiteingabe in Sekunden. Gibt interne Zeit in Minuten zurück."""
    try:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        t_input_sec = simpledialog.askfloat(
            "Nitrierschicht-Simulation",
            f"Nitrierzeit in Sekunden eingeben:\n"
            f"(Messdaten vorhanden: 0 – {max(t_data) * 60:.0f} s  /  {max(t_data):.0f} min)\n",
            minvalue=0.1
        )
        root.destroy()

        if t_input_sec is not None:
            return t_input_sec / 60.0  # Umrechnung Sekunden → Minuten (intern)
        return None

    except Exception:
        return None


def ask_time_console(t_data):
    """Fallback-Konsoleneingabe in Sekunden. Gibt interne Zeit in Minuten zurück."""
    print(f"\nMessdaten verfügbar: 0 – {max(t_data) * 60:.0f} s  ({max(t_data):.0f} min)")
    print("Extrapolation darüber hinaus möglich.")
    while True:
        try:
            val_sec = float(input("Nitrierzeit in Sekunden eingeben: "))
            if val_sec <= 0:
                print("Bitte einen positivien Wert eingeben.")
                continue
            return val_sec / 60.0  # Umrechnung Sekunden → Minuten (intern)
        except ValueError:
            print("Ungültige Eingabe. Bitte eine Zahl eingeben.")


# Hauptprogramm

def main():
    txt_path = None
    if len(sys.argv) > 1:
        txt_path = sys.argv[1]
    else:
        potential_paths = [
            r"C:\Users\Vince\Downloads\20190701_181338_MP1_QC19C(1).txt",
            "/mnt/user-data/uploads/20190701_181338_MP1_QC19C_1_.txt"
        ]
        for p in potential_paths:
            if os.path.exists(p):
                txt_path = p
                break

    ptr_data = None
    if txt_path and os.path.exists(txt_path):
        ptr_data = read_ptr_data(txt_path)
        if ptr_data is not None:
            print(f"[✓] PTR-Datei erfolgreich mit re geladen: {txt_path}  ({ptr_data['length']} Messpunkte)")
    else:
        print("[i] Keine gültige TXT-Datei gefunden – PTR-Plot wird übersprungen.")

    # Zeitreihendaten (Literatur, intern in Minuten)
    t_data, d_data = get_literature_data()

    # Fit berechnen
    popt, perr, model = fit_growth(t_data, d_data)
    print(f"\n[✓] Fit: {model}")
    if model == "parabolic":
        print(f"    d(t) = {popt[0]:.4f}·√t + {popt[1]:.4f}  [µm]  (t in Minuten)")
        print(f"    Unsicherheit: a ± {perr[0]:.4f},  b ± {perr[1]:.4f}")
    else:
        print(f"    d(t) = {popt[0]:.4f}·√t  [µm]  (t in Minuten)")

    # Zeiteingabe (Sekunden) → interne Minuten
    t_query_min = ask_time_gui(t_data)
    if t_query_min is None:
        t_query_min = ask_time_console(t_data)
    if t_query_min is None:
        t_query_min = 35.0 / 60.0  # Fallback: 35 s

    t_query_sec = t_query_min * 60.0  # Zurückrechnen für Anzeige

    d_query = predict(t_query_min, popt, model)
    d_query = max(0.0, d_query)

    flag = " [EXTRAPOLATION]" if t_query_min > max(t_data) else ""
    print(f"\n{'=' * 45}")
    print(f"  Zeit:          {t_query_sec:.1f} s  ({t_query_min:.2f} min){flag}")
    print(f"  Schichtdicke:  {d_query:.2f} µm")
    print(f"{'=' * 45}\n")

    plot_all(t_data, d_data, popt, model, t_query_min, t_query_sec, d_query, ptr_data)


if __name__ == "__main__":
    main()
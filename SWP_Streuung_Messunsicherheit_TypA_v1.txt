#Katastrophaler Code

import os
import re
import sys
import matplotlib
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import norm

matplotlib.use("TkAgg")


# Dateianalyse

def lade_ptr_datei(dateipfad):
    zahl = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
    frequenzen = []
    sweeps = []
    amp = []
    phase = []
    messblock = False
    sweep_nr = 0

    with open(dateipfad, "r", encoding="utf-8") as f:
        for zeile in f:
            z = zeile.strip()
            if not z:
                continue

            if "Amplitude" in z and "Phase" in z:
                messblock = True
                continue

            werte = re.findall(zahl, z)

            if not messblock:
                if len(werte) == 5:
                    frequenzen.append(float(werte[1]))
                elif len(werte) == 4:
                    # Zeile mit "NaN" als Frequenz (z.B. "1.1  NaN  20  3  8000").
                    # WICHTIG: Nicht einfach überspringen! Sonst verschiebt sich der Index
                    # gegenüber den zugehörigen Amplitude/Phase-Messwerten weiter unten
                    # in der Datei, die für JEDE Zeile (auch die NaN-Zeilen) einen
                    # Messwert enthalten. Stattdessen Platzhalter einfügen, damit die
                    # Indizes von frequenzen[] und sweep["phase"][] synchron bleiben.
                    frequenzen.append(np.nan)
                continue

            if len(werte) == 1 and z.isdigit():
                if amp:
                    sweeps.append({
                        "nr": sweep_nr,
                        "amplitude": np.array(amp),
                        "phase": np.array(phase)
                    })
                amp = []
                phase = []
                sweep_nr = int(z)
            elif len(werte) == 2:
                amp.append(float(werte[0]))
                phase.append(float(werte[1]))

    if amp:
        sweeps.append({
            "nr": sweep_nr,
            "amplitude": np.array(amp),
            "phase": np.array(phase)
        })

    return np.array(frequenzen), sweeps


def unwrap_phase(p):
    return np.degrees(np.unwrap(np.radians(p)))


def bereite_daten_auf(frequenzen, sweeps):
    n = min(len(frequenzen), min(len(s["phase"]) for s in sweeps))
    f = frequenzen[:n]
    phasen = []

    for s in sweeps:
        p = s["phase"][:n]
        p = unwrap_phase(p)
        phasen.append(p)

    phasen = np.array(phasen)
    mittel = np.mean(phasen, axis=0)
    std = np.std(phasen, axis=0, ddof=1)

    std[std == 0] = np.median(std[std > 0])

    # np.isfinite(f) entfernt jetzt korrekt genau die NaN-Platzhalter-Frequenzen
    # -- und zwar an der richtigen Position, weil f und mittel/std immer noch
    # index-synchron zueinander sind.
    maske = (np.isfinite(f) & np.isfinite(mittel) & (f > 0) & (f <= 80000))
    return f[maske], mittel[maske], std[maske]


# PTR Modell & Regression

def ptr_modell(x, phi0, k, R, d_over_alpha, tau):
    # Kombiniertes Modell: Zwei-Schicht-Interferenz + apparative Totzeit.

    f = x ** 2

    # 1. Thermische Wellenzahl und Schichtreflexion
    sigma_d = (1 + 1j) * np.sqrt(np.pi) * x * d_over_alpha
    e_term = np.exp(-2 * sigma_d)
    H = (1 + R * e_term) / (1 - R * e_term)
    phase_thermisch = np.degrees(np.angle(H))

    # 2. Apparative Totzeit als saettigender Tiefpass-1.-Ordnung-Term.
    # WICHTIG: Ein reiner linearer Term "-360*f*tau" waechst unbegrenzt und
    # "explodiert" bei hohen Frequenzen (siehe Diskussion) - physikalisch
    # saettigt eine reale Totzeit/Tiefpassfilterung dagegen bei -90 Grad.
    phase_totzeit = -np.degrees(np.arctan(2 * np.pi * f * tau))

    return phi0 - np.degrees(np.arctan(k * x)) + phase_thermisch + phase_totzeit


def fitte_regression(f, phase, sigma, n_starts=250, seed=0):

    """
    Weil das Modell 5 Parameter hat, die sich gegenseitig beeinflussen, funktioniert
    ein normaler Fit nicht wirklich und bleibt im lokalen Minimum stecken.
    Deshalb werden hier viele zufällige Startwerte innerhalb der Bounds probiert und das
    Ergebnis mit dem kleinsten Rauschen behalten.
    """
    x = np.sqrt(f)
    p0_phi0 = np.max(phase)

    lower_bounds = [p0_phi0 - 40, 1e-5, -0.95, 1e-5, 1e-7]
    upper_bounds = [p0_phi0 + 20, 1.0, 0.95, 0.10, 2e-3]

    rng = np.random.default_rng(seed)
    bester_popt = None
    beste_pcov = None
    bester_rmse = np.inf

    for _ in range(n_starts):
        p0 = [
            rng.uniform(lower_bounds[0], upper_bounds[0]),
            rng.uniform(1e-4, 0.5),
            rng.uniform(-0.9, 0.9),
            rng.uniform(1e-4, 0.08),
            10 ** rng.uniform(-7, -2.7),
        ]
        try:
            popt, pcov = curve_fit(
                ptr_modell,
                x,
                phase,
                sigma=sigma,
                absolute_sigma=True,
                p0=p0,
                bounds=(lower_bounds, upper_bounds),
                maxfev=20000
            )
        except RuntimeError:
            continue

        fit = ptr_modell(x, *popt)
        rmse = np.sqrt(np.mean((phase - fit) ** 2))
        if rmse < bester_rmse:
            bester_rmse = rmse
            bester_popt = popt
            beste_pcov = pcov

    if bester_popt is None:
        raise RuntimeError("Kein Fit konnte konvergieren - Bounds/Daten prüfen.")

    # Feinschliff: nochmal von der besten gefundenen Messpunkt aus starten,
    popt, pcov = curve_fit(
        ptr_modell,
        x,
        phase,
        sigma=sigma,
        absolute_sigma=True,
        p0=bester_popt,
        bounds=(lower_bounds, upper_bounds),
        maxfev=300000
    )

    perr = np.sqrt(np.diag(pcov))
    return popt, perr


def berechne_residuen(f, phase, popt):
    fit = ptr_modell(np.sqrt(f), *popt)
    residuen = phase - fit
    return fit, residuen


# Statistik & Analyse

def statistik(f, residuen):
    rmse = np.sqrt(np.mean(residuen ** 2))

    print("\n" + "=" * 50)
    print("Residuenanalyse")
    print("=" * 50)
    print(f"RMSE       : {rmse:.3f} °")
    print(f"Mittelwert : {np.mean(residuen):.3f} °")
    print(f"Std        : {np.std(residuen):.3f} °")

    idx = np.argsort(np.abs(residuen))[::-1]

    print("\nGrößte Abweichungen")
    for i in idx[:10]:
        print(f"{f[i]:8.1f} Hz   {residuen[i]:+7.3f} °")

    return rmse


# Visualisierung

def plot_ergebnis(f, phase, sigma, fit, residuen, popt, sweeps):
    rmse = np.sqrt(np.mean(residuen ** 2))

    fig = plt.figure(figsize=(15, 9))
    gs = gridspec.GridSpec(2, 2, figure=fig)

    ax1 = fig.add_subplot(gs[0, :])
    ax2 = fig.add_subplot(gs[1, 0])
    ax3 = fig.add_subplot(gs[1, 1])

    fs_plot = np.logspace(np.log10(f.min()), np.log10(f.max()), 500)

    # Hauptplot logarithmisch gegen die Frequenz f
    ax1.errorbar(f, phase, yerr=sigma, fmt="o", markersize=5, capsize=3, label="Messung")
    ax1.plot(fs_plot, ptr_modell(np.sqrt(fs_plot), *popt), linewidth=2, color="darkorange", label="PTR Fit")

    ax1.set_xscale("log")
    ax1.set_xlabel("Frequenz f [Hz]")
    ax1.set_ylabel("Phase [°]")
    ax1.grid(True, which="both", linestyle="--", alpha=0.5)
    ax1.legend()

    # Residuenplot über Frequenz
    ax2.scatter(f, residuen)
    ax2.axhline(0, linestyle="--", color="black", alpha=0.7)
    ax2.set_xscale("log")
    ax2.set_xlabel("Frequenz [Hz]")
    ax2.set_ylabel("Residuum [°]")
    ax2.grid(True, which="both", linestyle="--", alpha=0.5)

    # Histogramm der Residuen mit Gauß-Kurve
    ax3.hist(residuen, bins=20, density=False)
    mu, std = norm.fit(residuen)
    xx = np.linspace(residuen.min(), residuen.max(), 200)
    yy = norm.pdf(xx, mu, std) * len(residuen) * (residuen.max() - residuen.min()) / 20

    ax3.plot(xx, yy, linewidth=2, label=f"µ={mu:.2f} σ={std:.2f}")
    ax3.set_xlabel("Residuum [°]")
    ax3.set_ylabel("Häufigkeit")
    ax3.grid(True)
    ax3.legend()

    fig.suptitle("PTR Frequenz-Phase Analyse\ngewichtete Regression mit Sweep-Mittelwert")

    text = (
        f"φ0 = {popt[0]:.3f}°\n"
        f"k = {popt[1]:.6f}\n"
        f"R = {popt[2]:.3f}\n"
        f"d/√α = {popt[3]:.5f}\n\n"
        f"RMSE = {rmse:.3f}°\n"
        f"Sweeps = {len(sweeps)}\n"
        f"Punkte = {len(f)}"
    )
    fig.text(0.80, 0.15, text, fontsize=11)

    plt.tight_layout()

    #plt.savefig('SWP_Calculations_Streuung.pdf', bbox_inches='tight')  # Als PDF speichern
    #plt.savefig('SWP_Calculations_Streuung.png', dpi=300, bbox_inches='tight') # Als PNG speichern

    plt.show()


# Hauptprogramm
# Einlesen bissen umständlich, Dateipfad muss manuel gesetzt werden

def main():
    dateipfad = (
        sys.argv[1] if len(sys.argv) > 1
        else r"C:\Users\Vince\Desktop\Softwareprojekt -  Concept Development for Optical Access and Hardware Integration in a Nitriding Furnace (SysEng)\20190701_181338_MP1_QC19C(1).txt"
    )

    if not os.path.exists(dateipfad):
        print("Datei nicht gefunden:", dateipfad)
        sys.exit()

    print("Lese:", dateipfad)
    frequenzen, sweeps = lade_ptr_datei(dateipfad)

    print(len(frequenzen), "Frequenzpunkte")
    print(len(sweeps), "Sweeps")

    f, phase, sigma = bereite_daten_auf(frequenzen, sweeps)
    print(len(f), "gültige Punkte")

    popt, perr = fitte_regression(f, phase, sigma)

    print("\nFitparameter")
    print(f"phi0 = {popt[0]:.5f} ± {perr[0]:.5f}")
    print(f"k    = {popt[1]:.8f} ± {perr[1]:.8f}")
    print(f"A    = {popt[2]:.5f} ± {perr[2]:.5f}")

    fit, residuen = berechne_residuen(f, phase, popt)
    statistik(f, residuen)
    plot_ergebnis(f, phase, sigma, fit, residuen, popt, sweeps)


if __name__ == "__main__":
    main()

# 8 Stunden verschwendete Lebenszeit
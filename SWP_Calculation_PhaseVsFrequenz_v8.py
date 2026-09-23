"""
Photothermische Radiometrie (PTR) - Modellbasierte Bestimmung der
Nitrierschichtdicke aus Phasenverschiebungs-Frequenzsweeps.

Basierend auf:
M. Mikulewitsch et al.: "Influences on Quantitative Nitriding Layer
Thickness Measurements using Model-Based Photothermal Radiometry"
"""

import os
import sys
import csv
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# Tkinter für den Datei-Explorer importieren
import tkinter as tk
from tkinter import filedialog


# 0) Eigene Exceptions

class InvalidFileTypeError(Exception):
# Wird geworfen, wenn die ausgewählte Datei keine .csv- oder .txt-Datei ist
    pass

class InvalidFileContentError(Exception):
# Wird geworfen, wenn die Datei keine gültigen Phasen- und Frequenzwerte enthält
    pass

ALLOWED_EXTENSIONS = (".csv", ".txt")

# SR830 SNAP?-Parameterindizes (siehe Gerätehandbuch)
SNAP_PARAM_PHASE = 4   # Theta (Phase)
SNAP_PARAM_FREQ = 9    # Reference Frequency


# 1) Dateiauswahl über Explorerfenster (nur CSV/TXT)

def select_file_via_explorer(title="Datei auswählen"):
# Öffnet ein Datei-Explorer-Fenster, gefiltert auf .csv- und .txt-Dateien.

    root = tk.Tk()
    root.withdraw()  # Versteckt das Hauptfenster von Tkinter
    root.attributes('-topmost', True)  # Bringt den Explorer in den Vordergrund

    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=[
            ("CSV- und TXT-Dateien", "*.csv *.txt"),
            ("CSV-Dateien", "*.csv"),
            ("Textdateien", "*.txt"),
        ],
    )
    root.destroy()
    return file_path


def validate_extension(path: str) -> None:
# Prüft, ob die Datei die Endung .csv oder .txt besitzt.
# :raises InvalidFileTypeError: wenn die Endung nicht erlaubt ist

    _, ext = os.path.splitext(path)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise InvalidFileTypeError(
            f"Ungültiger Dateityp '{ext}' bei Datei '{path}'. "
            f"Erlaubt sind nur: {', '.join(ALLOWED_EXTENSIONS)}"
        )


# Einlesen: TXT-Format (spaltenbasiert)

def parse_lockin_txt(path):
    """
    Liest eine Lock-in-Rohdatendatei (.txt) im Format ein:

        A(v)    f(hz)   sens   ctime   delay(ms)
        1.1     0.5     25     11      5000
        ...
        Amplitude in mV     Phase in Grad
                    1
        0.8545          263.5380
        ...
                    2
        ...

    :raises InvalidFileContentError: wenn keine Frequenz-Spalte "f(hz)"/
        "Frequenz" bzw. keine "Phase"-Spalte gefunden werden kann, oder
        keine gültigen Datenblöcke vorliegen.
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [l.rstrip("\n") for l in f]

    if not lines:
        raise InvalidFileContentError(f"Datei '{path}' ist leer.")

    # --- a) Kopfzeile auf Frequenz-Spalte prüfen ---
    header = lines[0].lower()
    freq_keywords = ["f(hz)", "frequenz", "frequency", "freq"]
    if not any(kw in header for kw in freq_keywords):
        raise InvalidFileContentError(
            f"Datei '{path}': In der Kopfzeile '{lines[0].strip()}' wurde "
            f"keine Frequenzspalte (z.B. 'f(hz)') gefunden."
        )

    # Frequenz-Tabelle am Dateianfang einlesen
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
        raise InvalidFileContentError(f"Konnte keine Frequenz-Tabelle in '{path}' finden.")

    # Phasen-Unterüberschrift prüfen ("Amplitude ... Phase ...")
    phase_keywords = ["phase", "phasenwinkel", "phi"]
    remaining_header_text = " ".join(lines[i:i + 3]).lower()
    if not any(kw in remaining_header_text for kw in phase_keywords):
        raise InvalidFileContentError(
            f"Datei '{path}': Es wurde keine Phasen-Spalte (z.B. 'Phase in Grad') gefunden."
        )

    # Datenblöcke suchen (Zeilen, die NUR eine ganze Zahl enthalten)
    block_start_idx = [idx for idx in range(i, len(lines))
                        if lines[idx].strip().isdigit()]
    if not block_start_idx:
        raise InvalidFileContentError(f"Keine Messblöcke (Phase/Amplitude) in Datei gefunden: '{path}'")

    amp_blocks, phase_blocks = [], []
    for start in block_start_idx:
        data_lines = lines[start + 1: start + 1 + n_freq]
        amps, phases = [], []
        for dl in data_lines:
            parts = dl.split()
            if len(parts) < 2:
                continue
            try:
                amps.append(float(parts[0]))
                phases.append(float(parts[1]))
            except ValueError:
                continue
        if len(amps) == n_freq:
            amp_blocks.append(amps)
            phase_blocks.append(phases)

    if not amp_blocks:
        raise InvalidFileContentError(
            f"Datei '{path}': Keine vollständigen Phase/Amplitude-Datenblöcke gefunden."
        )

    amp_blocks = np.array(amp_blocks)      # (n_blocks, n_freq)
    phase_blocks = np.array(phase_blocks)  # (n_blocks, n_freq)
    n_blocks = amp_blocks.shape[0]

    # Zirkulare Mittelung der Phase über die Wiederholungen
    phase_rad = np.deg2rad(phase_blocks)
    mean_vec = np.mean(np.exp(1j * phase_rad), axis=0)
    phase_mean = np.rad2deg(np.angle(mean_vec)) % 360.0
    phase_std = np.rad2deg(np.std(phase_rad, axis=0))
    amp_mean = np.mean(amp_blocks, axis=0)

    return freq, phase_mean, phase_std, amp_mean, n_blocks


    # CSV-Format (SNAP-Kommando-Log)
def parse_lockin_csv(path):
    """
    Liest eine SNAP-Kommando-Logdatei (.csv) im Format ein:

        Date,Time,Ms,Category,Tag,State,Message,Value,Info,...
        ...,"SNAP 1,2,3,4,10,11","-9.29e-007,5.1e-007,1.06e-006,151.2,...",...
        ...,"SNAP 5,6,7,8,9","-0.00033,0.0067,0.0023,-0.002,1008.26",...

    Die Parameterindizes im Message-Feld (SNAP? i,j,k,l,m,n) werden
    verwendet, um aus dem zugehörigen Value-Feld die Phase (Index 4 = Theta)
    und die Frequenz (Index 9 = Reference Frequency) auszulesen. Da beide
    Werte im Messprotokoll häufig über zwei aufeinanderfolgende SNAP-Aufrufe
    verteilt sind, werden zeitlich benachbarte Phase-/Frequenzwerte zu
    Messpunktpaaren zusammengeführt.

    :raises InvalidFileContentError: wenn die benötigten Spalten fehlen oder
        keine zusammengehörigen Phasen-/Frequenzwerte gefunden werden.
    """
    pending_phase = None
    pending_freq = None
    freq_list, phase_list = [], []

    with open(path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None or "Message" not in reader.fieldnames or "Value" not in reader.fieldnames:
            raise InvalidFileContentError(
                f"CSV-Datei '{path}' besitzt nicht die erwarteten Spalten 'Message'/'Value' "
                f"(gefunden: {reader.fieldnames})."
            )

        for row in reader:
            message = (row.get("Message") or "").strip()
            value_str = (row.get("Value") or "").strip()

            if not message.upper().startswith("SNAP"):
                continue

            # Parameterliste aus "SNAP 1,2,3,4,10,11" extrahieren
            param_part = message[len("SNAP"):].strip()
            try:
                params = [int(p.strip()) for p in param_part.split(",") if p.strip() != ""]
                values = [float(v.strip()) for v in value_str.split(",") if v.strip() != ""]
            except ValueError:
                continue  # unerwartete/fehlerhafte Zeile ignorieren

            if len(params) != len(values):
                continue

            param_to_value = dict(zip(params, values))

            if SNAP_PARAM_PHASE in param_to_value:
                pending_phase = param_to_value[SNAP_PARAM_PHASE]
            if SNAP_PARAM_FREQ in param_to_value:
                pending_freq = param_to_value[SNAP_PARAM_FREQ]

            # Sobald Phase UND Frequenz aus zeitlich benachbarten SNAP-Aufrufen
            # vorliegen, als zusammengehöriges Messpunktpaar übernehmen
            if pending_phase is not None and pending_freq is not None:
                freq_list.append(pending_freq)
                phase_list.append(pending_phase)
                pending_phase = None
                pending_freq = None

    if not freq_list or not phase_list:
        raise InvalidFileContentError(
            f"In der CSV-Datei '{path}' konnten über 'SNAP'-Nachrichten keine "
            f"zusammengehörigen Phasen- (Index {SNAP_PARAM_PHASE}) und "
            f"Frequenzwerte (Index {SNAP_PARAM_FREQ}) gefunden werden."
        )

    freq = np.array(freq_list, dtype=float)
    phase_mean = np.array(phase_list, dtype=float)
    phase_std = np.zeros_like(phase_mean)   # keine Wiederholungen -> keine Streuung berechenbar
    amp_mean = None                          # Amplitude im CSV-Log nicht benötigt
    n_blocks = 1

    return freq, phase_mean, phase_std, amp_mean, n_blocks


# 2c) Einheitlicher Dispatcher: Typ + Inhalt prüfen und einlesen

def load_and_validate_measurement(path):
    """
    Prüft den Dateityp (.csv/.txt) und liest die Datei mit der passenden
    Routine ein. Wirft InvalidFileTypeError bzw. InvalidFileContentError,
    falls Typ oder Inhalt nicht den Anforderungen entsprechen.

    :return: (freq, phase_mean, phase_std, amp_mean, n_blocks)
    """
    validate_extension(path)

    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        return parse_lockin_txt(path)
    elif ext == ".csv":
        return parse_lockin_csv(path)
    else:
        # Sollte durch validate_extension bereits abgefangen sein
        raise InvalidFileTypeError(f"Nicht unterstützter Dateityp: '{ext}'")


def unwrap_phase_deg(freq, phase_deg):
    """
    Entfaltet (unwrapped) eine über der Frequenz gemessene Phase in Grad,
    sortiert dabei zusätzlich nach aufsteigender Frequenz.
    """
    order = np.argsort(freq)
    f_sorted = freq[order]
    phase_unwrapped = np.rad2deg(np.unwrap(np.deg2rad(phase_deg[order])))
    return f_sorted, phase_unwrapped


def align_measurements(freq_ref, phase_ref, freq_probe, phase_probe, rtol=1e-6):
    """
    Bringt Referenz- und Probenmessung auf eine gemeinsame Frequenzachse.

    Da .txt- (Lock-in-Rohdump) und .csv-Dateien (SNAP-Kommando-Log) i.d.R.
    unterschiedlich viele bzw. unterschiedliche Frequenzstützstellen liefern,
    werden die Messwerte NICHT per striktem np.allclose() verglichen (das
    führt bei abweichender Länge sofort zu einem Broadcast-Fehler), sondern
    bei Bedarf per linearer Interpolation im gemeinsamen Frequenzbereich
    zusammengeführt.

    :param freq_ref, freq_probe: aufsteigend sortierte Frequenzarrays
    :param phase_ref, phase_probe: zugehörige (entfaltete) Phasenwerte
    :return: (freq_common, phase_ref_common, phase_probe_common)
    :raises ValueError: wenn kein gemeinsamer Frequenzbereich existiert
    """
    # Fall 1: identische Stützstellen -> direkt verwenden
    if len(freq_ref) == len(freq_probe) and np.allclose(freq_ref, freq_probe, rtol=rtol):
        return freq_ref, phase_ref, phase_probe

    # Fall 2: unterschiedliche Stützstellen -> gemeinsamen Bereich ermitteln
    f_min = max(freq_ref.min(), freq_probe.min())
    f_max = min(freq_ref.max(), freq_probe.max())
    if f_min >= f_max:
        raise ValueError(
            "Referenz- und Probenmessung haben keinen gemeinsamen Frequenzbereich "
            f"(Referenz: {freq_ref.min():.4g}-{freq_ref.max():.4g} Hz, "
            f"Probe: {freq_probe.min():.4g}-{freq_probe.max():.4g} Hz)."
        )

    # Als Basisgitter dasjenige verwenden, das im Überlappungsbereich die
    # meisten eigenen Stützstellen besitzt (feineres/dichteres Gitter).
    # Das andere wird per linearer Interpolation darauf gebracht - das
    # funktioniert auch dann, wenn die Überlappung sehr schmal ist (z.B.
    # ein SNAP-Log mit nahezu konstanter Frequenz innerhalb eines breiten
    # Referenz-Sweeps).
    ref_mask = (freq_ref >= f_min) & (freq_ref <= f_max)
    probe_mask = (freq_probe >= f_min) & (freq_probe <= f_max)
    n_ref_in_overlap = int(np.count_nonzero(ref_mask))
    n_probe_in_overlap = int(np.count_nonzero(probe_mask))

    if n_ref_in_overlap == 0 and n_probe_in_overlap == 0:
        raise ValueError(
            "Im gemeinsamen Frequenzbereich "
            f"({f_min:.4g}-{f_max:.4g} Hz) liegen weder Referenz- noch "
            "Probenstützstellen; eine Interpolation ist nicht möglich."
        )

    if n_probe_in_overlap >= n_ref_in_overlap:
        freq_common = freq_probe[probe_mask]
        phase_probe_common = phase_probe[probe_mask]
        phase_ref_common = np.interp(freq_common, freq_ref, phase_ref)
        base_name, other_name = "Probe", "Referenz"
    else:
        freq_common = freq_ref[ref_mask]
        phase_ref_common = phase_ref[ref_mask]
        phase_probe_common = np.interp(freq_common, freq_probe, phase_probe)
        base_name, other_name = "Referenz", "Probe"

    print(
        f"[Hinweis] Referenz ({len(freq_ref)} Punkte, {freq_ref.min():.4g}-{freq_ref.max():.4g} Hz) "
        f"und Probe ({len(freq_probe)} Punkte, {freq_probe.min():.4g}-{freq_probe.max():.4g} Hz) "
        f"nutzen unterschiedliche Frequenzstützstellen. Als gemeinsames Gitter wurden die "
        f"{len(freq_common)} {base_name}-Stützstellen im Überlappungsbereich "
        f"({f_min:.4g}-{f_max:.4g} Hz) verwendet; die {other_name}-Phase wurde linear darauf interpoliert."
    )

    return freq_common, phase_ref_common, phase_probe_common


# 3) Physikalisches Modell
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


# 4) Fit-Routine: Schichtdicke & Wärmeleitfähigkeit bestimmen
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


# 5) Gesamtablauf
if __name__ == "__main__":

    # --- Materialparameter des Substrats (z.B. 42CrMo4) ---
    k_S = 42.0       # W/(m*K)   Wärmeleitfähigkeit Substrat
    rho_S = 7800.0   # kg/m^3    Dichte Substrat
    C_S = 460.0      # J/(kg*K)  spezifische Wärmekapazität Substrat
    b_S = thermal_effusivity(k_S, rho_S, C_S)
    print(f"Substrat-Effusivität b_S = {b_S:.1f} Ws^0.5/(m^2 K)")

    # --- 1. Dateiauswahl via Explorer: Referenzmessung (unnitriert) ---
    print("\nBitte wählen Sie im Explorer die REFERENZMESSUNG (unnitrierte Probe) aus...")
    ref_path = select_file_via_explorer(title="1. Referenzmessung auswählen (unnitriert, .csv/.txt)")

    if not ref_path:
        print("[Abbruch] Es wurde keine Referenzdatei ausgewählt.")
        sys.exit()

    print(f"Ausgewählte Referenzdatei: {ref_path}")
    try:
        freq_ref, phase_ref, phase_ref_std, amp_ref, n_ref = load_and_validate_measurement(ref_path)
    except (InvalidFileTypeError, InvalidFileContentError) as e:
        print(f"\n[Fehler bei der Referenzdatei] {e}")
        sys.exit(1)

    print(f"Referenzmessung eingelesen: {n_ref} Wiederholungen, {len(freq_ref)} Frequenzpunkte")
    f_ref, phase_ref_unwr = unwrap_phase_deg(freq_ref, phase_ref)

    # --- 2. Dateiauswahl via Explorer: Probenmessung (nitriert) ---
    print("\nBitte wählen Sie im Explorer die PROBENMESSUNG (nitrierte Probe) aus...")
    probe_path = select_file_via_explorer(title="2. Probenmessung auswählen (nitriert, .csv/.txt)")

    if not probe_path:
        print("[Abbruch] Es wurde keine Probenmessungsdatei ausgewählt.")
        sys.exit()

    print(f"Ausgewählte Probendatei: {probe_path}")

    try:
        freq_probe, phase_probe, phase_probe_std, amp_probe, n_probe = \
            load_and_validate_measurement(probe_path)
        f_probe, phase_probe_unwr = unwrap_phase_deg(freq_probe, phase_probe)

        # --- Referenz und Probe auf gemeinsame Frequenzachse bringen ---
        freq_common, phase_ref_common, phase_probe_common = align_measurements(
            f_ref, phase_ref_unwr, f_probe, phase_probe_unwr
        )

        # --- photothermisches Phasensignal (Referenz minus Probe) ---
        Phi = phase_ref_common - phase_probe_common

        # --- nichtlinearen Fit durchführen ---
        d_fit, kL_fit, d_err, kL_err, model_func = fit_layer_parameters(
            freq_common, Phi, b_S, rho_S, C_S
        )

        print("\n==================================================")
        print("Ergebnis der modellbasierten Schichtdickenbestimmung:")
        print(f"  Schichtdicke          d   = {d_fit*1e6:.2f} +- {d_err*1e6:.2f} µm")
        print(f"  Wärmeleitfähigkeit   k_L  = {kL_fit:.2f} +- {kL_err:.2f} W/(m*K)")
        print("==================================================\n")

        # --- Plot: oben Rohdaten-Sichtvergleich, unten Fit-Ergebnis ---
        freq_fine = np.logspace(np.log10(freq_common.min()),
                                 np.log10(freq_common.max()), 500)
        Phi_fit_curve = model_func(freq_fine, d_fit, kL_fit)

        fig, (ax_raw, ax_fit) = plt.subplots(2, 1, figsize=(8, 10))

        # -- Oben: reiner Sicht-Vergleich der beiden Rohmessungen --
        ax_raw.plot(f_ref, phase_ref_unwr, "o-",
                    label=f"Referenz: {os.path.basename(ref_path)}")
        ax_raw.plot(f_probe, phase_probe_unwr, "s--",
                    label=f"Probe: {os.path.basename(probe_path)}")
        ax_raw.set_xscale("log")
        ax_raw.set_xlabel("Frequenz in Hz (log-Skala)")
        ax_raw.set_ylabel("Phase (entfaltet) in °")
        ax_raw.set_title("Sicht-Vergleich der Rohdaten: Referenz vs. Probe")
        ax_raw.legend()
        ax_raw.grid(True, which="both", alpha=0.4)

        # -- Unten: referenzkorrigierte Phasendifferenz + Fit --
        ax_fit.plot(np.sqrt(2*np.pi*freq_common), Phi, "o",
                    label="Messdaten $\\Phi(\\omega) = \\varphi_{ref} - \\varphi_{probe}$")
        ax_fit.plot(np.sqrt(2*np.pi*freq_fine), Phi_fit_curve, "--",
                    label="angepasste Modellfunktion")
        ax_fit.set_xlabel(r"$\sqrt{\omega}$ in $\sqrt{Hz}$")
        ax_fit.set_ylabel(r"referenzkorrigierte Phasendifferenz $\Phi$ in °"
                           "\n(nicht die absolute Lock-in-Rohphase!)")
        ax_fit.set_title(f"d = {d_fit*1e6:.2f} µm,  k_L = {kL_fit:.2f} W/(m·K)")
        ax_fit.legend()
        ax_fit.grid(True)

        plt.tight_layout()
        plt.show()

    except (InvalidFileTypeError, InvalidFileContentError) as e:
        print(f"\n[Fehler bei der Probendatei] {e}")
    except Exception as e:
        print(f"\n[Fehler bei der Auswertung] {e}")


def start_PhaseFreq(ref_path: str, probe_path: str,
                    k_S: float = 42.0, rho_S: float = 7800.0, C_S: float = 460.0):
    """
    Führt die modellbasierte Auswertung der Nitrierschichtdicke aus zwei
    Dateipfaden (Referenz und Probe) durch.

    :param ref_path: Dateipfad zur Referenzmessung (.csv oder .txt)
    :param probe_path: Dateipfad zur Probenmessung (.csv oder .txt)
    :param k_S: Wärmeleitfähigkeit Substrat in W/(m*K)
    :param rho_S: Dichte Substrat in kg/m^3
    :param C_S: Spezifische Wärmekapazität Substrat in J/(kg*K)

    :return: dict mit allen Ergebnissen und Plot-Daten für die GUI
    """
    if not ref_path or not os.path.exists(ref_path):
        raise FileNotFoundError(f"Referenzdatei nicht gefunden: '{ref_path}'")
    if not probe_path or not os.path.exists(probe_path):
        raise FileNotFoundError(f"Probendatei nicht gefunden: '{probe_path}'")

    # 1. Substrat-Effusivität
    b_S = thermal_effusivity(k_S, rho_S, C_S)

    # 2. Referenzmessung einlesen & entfalten
    freq_ref, phase_ref, phase_ref_std, amp_ref, n_ref = load_and_validate_measurement(ref_path)
    f_ref, phase_ref_unwr = unwrap_phase_deg(freq_ref, phase_ref)

    # 3. Probenmessung einlesen & entfalten
    freq_probe, phase_probe, phase_probe_std, amp_probe, n_probe = load_and_validate_measurement(probe_path)
    f_probe, phase_probe_unwr = unwrap_phase_deg(freq_probe, phase_probe)

    # 4. Gemeinsame Frequenzachse & Phasendifferenz
    freq_common, phase_ref_common, phase_probe_common = align_measurements(
        f_ref, phase_ref_unwr, f_probe, phase_probe_unwr
    )
    Phi = phase_ref_common - phase_probe_common

    # 5. Fit durchführen
    d_fit, kL_fit, d_err, kL_err, model_func = fit_layer_parameters(
        freq_common, Phi, b_S, rho_S, C_S
    )

    # 6. Fit-Kurve für Visualisierung aufbereiten
    freq_fine = np.logspace(np.log10(freq_common.min()), np.log10(freq_common.max()), 500)
    Phi_fit_curve = model_func(freq_fine, d_fit, kL_fit)

    # 7. Ergebnisse als Dictionary zur Weiterverarbeitung in der GUI zurückgeben
    return {
        "d_fit_um": d_fit * 1e6,
        "d_err_um": d_err * 1e6,
        "kL_fit": kL_fit,
        "kL_err": kL_err,
        "plot_data": {
            "f_ref": f_ref,
            "phase_ref_unwr": phase_ref_unwr,
            "f_probe": f_probe,
            "phase_probe_unwr": phase_probe_unwr,
            "freq_common": freq_common,
            "Phi": Phi,
            "freq_fine": freq_fine,
            "Phi_fit_curve": Phi_fit_curve,
            "ref_filename": os.path.basename(ref_path),
            "probe_filename": os.path.basename(probe_path)
        }
    }

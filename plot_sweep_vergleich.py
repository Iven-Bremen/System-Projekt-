"""
Reiner Sicht-Vergleich: Plottet die Phase-Frequenz-Kurve einer .txt- und
einer .csv-Messdatei (Lock-in-Rohdump bzw. SNAP-Kommando-Log) in EINEM
Diagramm übereinander.

Dient nur der visuellen Kontrolle ("Wie sehen beide Sweeps aus?") -
KEIN Fit, KEIN Referenzabzug, keine Schichtdickenberechnung.

Einlese-Logik ist bewusst identisch zu ptr_nitrierschicht.py, damit die
Kurven exakt so aussehen, wie sie später auch im Fit verwendet würden.
"""

import os
import numpy as np
import matplotlib.pyplot as plt

import tkinter as tk
from tkinter import filedialog

import csv


# ---------------------------------------------------------------------
# Eigene Exceptions
# ---------------------------------------------------------------------

class InvalidFileTypeError(Exception):
    """Wird geworfen, wenn die ausgewählte Datei keine .csv- oder .txt-Datei ist."""
    pass


class InvalidFileContentError(Exception):
    """Wird geworfen, wenn die Datei keine gültigen Phasen- und Frequenzwerte enthält."""
    pass


ALLOWED_EXTENSIONS = (".csv", ".txt")
SNAP_PARAM_PHASE = 4   # Theta (Phase)
SNAP_PARAM_FREQ = 9    # Reference Frequency


# ---------------------------------------------------------------------
# Dateiauswahl
# ---------------------------------------------------------------------

def select_file_via_explorer(title, pattern):
    """Öffnet den Explorer, gefiltert auf den angegebenen Dateityp (*.txt oder *.csv)."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=[(f"{pattern.upper()}-Dateien", f"*.{pattern}")],
    )
    root.destroy()
    return file_path


def validate_extension(path):
    _, ext = os.path.splitext(path)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise InvalidFileTypeError(
            f"Ungültiger Dateityp '{ext}' bei Datei '{path}'. "
            f"Erlaubt sind nur: {', '.join(ALLOWED_EXTENSIONS)}"
        )


# ---------------------------------------------------------------------
# Einlesen: TXT-Format (spaltenbasiert, Lock-in-Rohdump)
# ---------------------------------------------------------------------

def parse_lockin_txt(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [l.rstrip("\n") for l in f]

    if not lines:
        raise InvalidFileContentError(f"Datei '{path}' ist leer.")

    header = lines[0].lower()
    if not any(kw in header for kw in ["f(hz)", "frequenz", "frequency", "freq"]):
        raise InvalidFileContentError(
            f"Datei '{path}': keine Frequenzspalte in der Kopfzeile gefunden."
        )

    freqs = []
    i = 1
    while i < len(lines):
        parts = lines[i].split()
        if len(parts) >= 2:
            try:
                freqs.append(float(parts[1]))
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

    remaining_header_text = " ".join(lines[i:i + 3]).lower()
    if not any(kw in remaining_header_text for kw in ["phase", "phasenwinkel", "phi"]):
        raise InvalidFileContentError(f"Datei '{path}': keine Phasen-Spalte gefunden.")

    block_start_idx = [idx for idx in range(i, len(lines)) if lines[idx].strip().isdigit()]
    if not block_start_idx:
        raise InvalidFileContentError(f"Keine Messblöcke in Datei gefunden: '{path}'")

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
        raise InvalidFileContentError(f"Datei '{path}': keine vollständigen Datenblöcke gefunden.")

    phase_blocks = np.array(phase_blocks)
    phase_rad = np.deg2rad(phase_blocks)
    mean_vec = np.mean(np.exp(1j * phase_rad), axis=0)
    phase_mean = np.rad2deg(np.angle(mean_vec)) % 360.0

    return freq, phase_mean


# ---------------------------------------------------------------------
# Einlesen: CSV-Format (SNAP-Kommando-Log)
# ---------------------------------------------------------------------

def parse_lockin_csv(path):
    pending_phase = None
    pending_freq = None
    freq_list, phase_list = [], []

    with open(path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "Message" not in reader.fieldnames or "Value" not in reader.fieldnames:
            raise InvalidFileContentError(
                f"CSV-Datei '{path}' besitzt nicht die erwarteten Spalten 'Message'/'Value'."
            )

        for row in reader:
            message = (row.get("Message") or "").strip()
            value_str = (row.get("Value") or "").strip()

            if not message.upper().startswith("SNAP"):
                continue

            param_part = message[len("SNAP"):].strip()
            try:
                params = [int(p.strip()) for p in param_part.split(",") if p.strip() != ""]
                values = [float(v.strip()) for v in value_str.split(",") if v.strip() != ""]
            except ValueError:
                continue
            if len(params) != len(values):
                continue

            param_to_value = dict(zip(params, values))
            if SNAP_PARAM_PHASE in param_to_value:
                pending_phase = param_to_value[SNAP_PARAM_PHASE]
            if SNAP_PARAM_FREQ in param_to_value:
                pending_freq = param_to_value[SNAP_PARAM_FREQ]

            if pending_phase is not None and pending_freq is not None:
                freq_list.append(pending_freq)
                phase_list.append(pending_phase)
                pending_phase = None
                pending_freq = None

    if not freq_list or not phase_list:
        raise InvalidFileContentError(
            f"In der CSV-Datei '{path}' konnten über 'SNAP'-Nachrichten keine "
            f"zusammengehörigen Phasen- und Frequenzwerte gefunden werden."
        )

    return np.array(freq_list, dtype=float), np.array(phase_list, dtype=float)


def unwrap_phase_deg(freq, phase_deg):
    order = np.argsort(freq)
    f_sorted = freq[order]
    phase_unwrapped = np.rad2deg(np.unwrap(np.deg2rad(phase_deg[order])))
    return f_sorted, phase_unwrapped


def load_measurement(path):
    validate_extension(path)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        freq, phase = parse_lockin_txt(path)
    else:
        freq, phase = parse_lockin_csv(path)
    return unwrap_phase_deg(freq, phase)


# ---------------------------------------------------------------------
# Hauptablauf: Dateien wählen und beide Kurven in einem Plot übereinanderlegen
# ---------------------------------------------------------------------

if __name__ == "__main__":

    print("Bitte TXT-Messdatei auswählen...")
    txt_path = select_file_via_explorer("TXT-Messdatei auswählen", "txt")
    if not txt_path:
        print("[Abbruch] Keine TXT-Datei ausgewählt.")
        raise SystemExit

    print("Bitte CSV-Messdatei auswählen...")
    csv_path = select_file_via_explorer("CSV-Messdatei auswählen", "csv")
    if not csv_path:
        print("[Abbruch] Keine CSV-Datei ausgewählt.")
        raise SystemExit

    try:
        freq_txt, phase_txt = load_measurement(txt_path)
        freq_csv, phase_csv = load_measurement(csv_path)
    except (InvalidFileTypeError, InvalidFileContentError) as e:
        print(f"\n[Fehler] {e}")
        raise SystemExit

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(freq_txt, phase_txt, "o-", label=f"TXT: {os.path.basename(txt_path)}")
    ax.plot(freq_csv, phase_csv, "s--", label=f"CSV: {os.path.basename(csv_path)}")

    ax.set_xscale("log")
    ax.set_xlabel("Frequenz in Hz (log-Skala)")
    ax.set_ylabel("Phase (entfaltet) in °")
    ax.set_title("Sicht-Vergleich der Rohdaten: TXT vs. CSV")
    ax.legend()
    ax.grid(True, which="both", alpha=0.4)
    plt.tight_layout()
    plt.show()

import  time
def LogMassage(TAG:str,Category:str,Massage:str,INFO:str,AdditionalInfo:str):
        print(time.strftime("%Y-%m-%d %H:%M:%S")+ "  |  " + TAG + "  |  " + Category + "  |  " + Massage + "  |  " + AdditionalInfo)"""
Hilfsfunktionen für das Loggen der Messdaten und der Terminalausgaben.
Die CSV-Datei wird automatisch angelegt, wenn sie noch nicht existiert.
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

CSV_COLUMNS = ["Timestamp", "Device", "Command", "Raw_Response", "Decoded_Info", "Latency_ms"]
CSV_DELIMITER = "|"
PROJECT_NAME = Path(__file__).resolve().parent.name


def _project_log_path():
    """Erzeugt pro Tag einen Ordner und darin genau eine Projekt-Logdatei."""
    date_folder = datetime.now().strftime("%Y-%m-%d")
    log_dir = Path("logs") / date_folder
    log_dir.mkdir(parents=True, exist_ok=True)
    return str(log_dir / f"{PROJECT_NAME}_log.csv")


def LogMassage(TAG: str, Category: str, Massage: str, INFO: str, AdditionalInfo: str = ""):
    """Gibt eine Meldung aus und schreibt sie automatisch in die Projekt-CSV."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    console_line = f"{timestamp}  |  {TAG}  |  {Category}  |  {Massage}  |  {AdditionalInfo}"
    print(console_line, file=sys.__stdout__)
    append_csv_row(
        _project_log_path(),
        TAG,
        Category,
        Massage,
        f"{INFO} {AdditionalInfo}".strip(),
        0,
        timestamp=timestamp,
    )

def make_log_path(prefix="M", base_name=None):
    """Liefert den Tagespfad; optionale Dateinamen bleiben kompatibel."""
    if base_name:
        date_folder = datetime.now().strftime("%Y-%m-%d")
        log_dir = Path("logs") / date_folder
        log_dir.mkdir(parents=True, exist_ok=True)
        return str(log_dir / base_name)
    return _project_log_path()


def ensure_log_file(csv_path):
    """Erzeuge die CSV-Datei mit Spaltenkopfzeile, falls sie noch nicht existiert."""
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=CSV_DELIMITER)
            writer.writerow(CSV_COLUMNS)
        return True
    return False


def insert_session_separator(csv_path, mode="HARDWARE"):
    """Fuege eine sichtbare Session-Trennung in die CSV-Datei ein."""
    ensure_log_file(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=CSV_DELIMITER)
        for _ in range(10):
            writer.writerow([])
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([timestamp, "SESSION", "START", mode, "", "0"])


def append_csv_row(csv_path, device, command, raw_response, decoded_info, latency_ms, timestamp=None):
    """Schreibe eine Zeile in die CSV-Datei."""
    ensure_log_file(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=CSV_DELIMITER)
        timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        writer.writerow([timestamp, device, command, raw_response, decoded_info, f"{latency_ms:.2f}"])


def append_terminal_row(csv_path, text):
    """Logge einzelne Terminalzeilen in dieselbe CSV-Datei."""
    ensure_log_file(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=CSV_DELIMITER)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        writer.writerow([timestamp, "TERMINAL", "OUTPUT", text, "", "0"])


class _Tee:
    def __init__(self, original, csv_path):
        self.original = original
        self.csv_path = csv_path

    def write(self, message):
        self.original.write(message)
        if message and not message.isspace():
            for line in message.rstrip("\n").splitlines():
                append_terminal_row(self.csv_path, line)

    def flush(self):
        self.original.flush()


def start_terminal_logging(prefix="M", csv_path=None, capture_input=True, insert_separator=True):
    """Aktiviere Terminal-Logging und zeichne stdout/stderr (und optional input) in der CSV mit auf."""
    if csv_path is None:
        csv_path = make_log_path(prefix)

    ensure_log_file(csv_path)
    if insert_separator:
        insert_session_separator(csv_path, mode="SIMULATION" if prefix == "T" else "HARDWARE")

    sys.stdout = _Tee(sys.__stdout__, csv_path)
    sys.stderr = _Tee(sys.__stderr__, csv_path)

    if capture_input:
        import builtins
        original_input = builtins.input

        def logged_input(prompt=''):
            response = original_input(prompt)
            try:
                append_terminal_row(csv_path, f"[INPUT] {prompt}{response}")
            except Exception:
                pass
            return response

        builtins.input = logged_input

    return csv_path


import csv
import os
import sys
from datetime import datetime

CSV_COLUMNS = ["Timestamp", "Device", "Command", "Raw_Response", "Decoded_Info", "Latency_ms"]


def make_log_path(prefix="M", base_name=None):
    """Erzeuge den Tagesordner und liefere den CSV-Pfad zurueck."""
    prefix = prefix.upper() if isinstance(prefix, str) else "M"
    if prefix not in ("M", "T"):
        prefix = "M"

    date_folder = datetime.now().strftime("%Y-%m-%d")
    log_dir = os.path.join("logs", date_folder)
    os.makedirs(log_dir, exist_ok=True)

    if base_name:
        filename = base_name
    elif prefix == "T":
        filename = "plis_simulation_log.csv"
    else:
        filename = "plis_measurement_log.csv"

    return os.path.join(log_dir, filename)


def ensure_log_file(csv_path):
    """Erzeuge die CSV-Datei mit Spaltenkopfzeile, falls sie noch nicht existiert."""
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(CSV_COLUMNS)
        return True
    return False


def insert_session_separator(csv_path, mode="HARDWARE"):
    """Fuege eine sichtbare Session-Trennung in die CSV-Datei ein."""
    ensure_log_file(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        for _ in range(10):
            writer.writerow([])
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([timestamp, "SESSION", "START", mode, "", "0"])


def append_csv_row(csv_path, device, command, raw_response, decoded_info, latency_ms):
    """Schreibe eine Zeile in die CSV-Datei."""
    ensure_log_file(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        writer.writerow([timestamp, device, command, raw_response, decoded_info, f"{latency_ms:.2f}"])


def append_terminal_row(csv_path, text):
    """Logge einzelne Terminalzeilen in dieselbe CSV-Datei."""
    ensure_log_file(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
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

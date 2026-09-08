"""
Hilfsfunktionen für das Loggen der Messdaten und der Terminalausgaben.
Die CSV-Datei wird direkt im Tagesordner abgelegt und enthält die Uhrzeit im Dateinamen.
Struktur pro Zelle: Date , Time , Tag , Category , Message , Info , AdditionalInfo , Else
(Im Terminal wird weiterhin | als Trenner für die Optik verwendet!)
"""
import datetime

import csv
import os
from datetime import datetime
from pathlib import Path

# Neue aufgespaltene Spaltenstruktur
CSV_COLUMNS = ["Date", "Time", "Tag", "Category", "Message", "Info", "AdditionalInfo", "Else"]
CSV_DELIMITER = ","  # Für perfekte Zellentrennung im Viewer
CSV_COLUMNS_NEW = ["Date","Time","Category","Tag","State","Message","Value","Info","AdditionalMessage","AdditionalValue","AdditionalInfo","Else"]

_CURRENT_SESSION_LOG_PATH = None

# --- NEU: Callbacks für die GUI ---
_gui_callbacks = []



def register_gui_callback(callback_func):
    """Erlaubt der GUI, sich für Live-Logs anzumelden."""
    _gui_callbacks.append(callback_func)
# ----------------------------------

def make_log_path(prefix="M", base_name=None):
    """Erzeuge den Log-Pfad direkt im Tagesordner mit Uhrzeit im Dateinamen."""
    prefix = prefix.upper() if isinstance(prefix, str) else "M"
    if prefix not in ("M", "T"):
        prefix = "M"

    now = datetime.now()
    date_folder = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")
    
    log_dir = os.path.join("logs", date_folder)
    os.makedirs(log_dir, exist_ok=True)

    if base_name:
        filename = base_name
    elif prefix == "T":
        filename = f"{time_str}_{date_folder}_simulation_log.csv"
    else:
        filename = f"{time_str}_{date_folder}_measurement_log.csv"

    return os.path.join(log_dir, filename)


def _get_active_log_path():
    """Gibt den aktuellen Log-Pfad zurück oder initialisiert ihn einmalig."""
    global _CURRENT_SESSION_LOG_PATH
    if _CURRENT_SESSION_LOG_PATH is None:
        _CURRENT_SESSION_LOG_PATH = make_log_path("M")
        ensure_log_file(_CURRENT_SESSION_LOG_PATH)
    return _CURRENT_SESSION_LOG_PATH


def get_csv_writer(f):
    """Hilfsfunktion: Erstellt den Writer, der sicherstellt, dass Kommas im Text nicht die Zellen sprengen."""
    return csv.writer(f, delimiter=CSV_DELIMITER, quoting=csv.QUOTE_MINIMAL)


def ensure_log_file(csv_path):
    """Erzeuge die CSV-Datei mit Spaltenkopfzeile, falls sie noch nicht existiert."""
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = get_csv_writer(f)
            writer.writerow(CSV_COLUMNS)
        return True
    return False


def insert_session_separator(csv_path, mode="HARDWARE"):
    """Fuege eine sichtbare Session-Trennung in die CSV-Datei ein."""
    ensure_log_file(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = get_csv_writer(f)
        for _ in range(10):
            writer.writerow([])
        date_str = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%H:%M:%S")
        # Leere Felder sind jetzt explizite Leerzeichen " "
        writer.writerow([date_str, time_str, "SESSION", "START", mode, " ", " ", " "])


def append_csv_row(csv_path, tag, category, message, info, additional_info, else_val=" ", dt_obj=None):
    """Schreibe eine sauber aufgespaltene Zeile in die CSV-Datei."""
    ensure_log_file(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = get_csv_writer(f)
        dt = dt_obj or datetime.now()
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M:%S.%f")[:-3]
        
        # Falls Werte ganz leer sind, durch " " ersetzen
        info = info if info else " "
        additional_info = additional_info if additional_info else " "
        
        writer.writerow([date_str, time_str, tag, category, message, info, additional_info, else_val])


def append_terminal_row(csv_path, text, device_tag="TERMINAL"):
    """Logge einzelne Terminalzeilen (oder Errors) aufgespalten in die CSV."""
    ensure_log_file(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = get_csv_writer(f)
        dt = datetime.now()
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M:%S.%f")[:-3]
        writer.writerow([date_str, time_str, device_tag, "OUTPUT", text, " ", " ", " "])


def LogMassage(TAG: str, Category: str, Massage: str, INFO: str, AdditionalInfo: str = ""):
    """Schreibt direkt auf das originale Terminal (mit |) UND sofort aufgespalten in die CSV-Datei (mit Komma)."""
    dt = datetime.now()
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H:%M:%S.%f")[:-3]
    
    console_line = f"{date_str} {time_str}  |  {TAG}  |  {Category}  |  {Massage}  |  {INFO}  |  {AdditionalInfo}"
    
    # 2. An die GUI senden (falls registriert)
    for cb in _gui_callbacks:
        cb(console_line + "\n")

    # 3. Direkt in die CSV schreiben
    log_path = _get_active_log_path()
    append_csv_row(
        log_path,
        tag=TAG,
        category=Category,
        message=Massage,
        info=INFO,
        additional_info=AdditionalInfo,
        else_val=" ",
        dt_obj=dt
    )


class _Tee:
    def __init__(self, original, csv_path, device_tag="TERMINAL"):
        self.original = original
        self.csv_path = csv_path
        self.device_tag = device_tag

    def write(self, message):
        self.original.write(message)
        self.original.flush()
        sys.stdout.flush()
        
        if message and not message.isspace():
            for line in message.rstrip("\n").splitlines():
                clean_line = line.strip()
                
                # --- NEU: Filter ---
                # Überspringe komplett leere Zeilen ODER Zeilen, die nur aus "^" oder "~" bestehen
                if not clean_line or set(clean_line).issubset(set(" ^~")):
                    continue
                
                append_terminal_row(self.csv_path, clean_line, device_tag=self.device_tag)
                
                # An die GUI senden
                for cb in _gui_callbacks:
                    cb(f"[{self.device_tag}] {clean_line}\n")

    def flush(self):
        self.original.flush()


def start_terminal_logging(prefix="M", csv_path=None, capture_input=True, insert_separator=True):
    """Aktiviere Terminal-Logging für stdout, stderr (Fehler) und input."""
    global _CURRENT_SESSION_LOG_PATH
    if csv_path is None:
        csv_path = make_log_path(prefix)
    
    _CURRENT_SESSION_LOG_PATH = csv_path

    ensure_log_file(csv_path)
    if insert_separator:
        insert_session_separator(csv_path, mode="SIMULATION" if prefix == "T" else "HARDWARE")

    sys.stdout = _Tee(sys.__stdout__, csv_path, device_tag="TERMINAL")
    sys.stderr = _Tee(sys.__stderr__, csv_path, device_tag="ERROR")

    if capture_input:
        import builtins
        original_input = builtins.input

        def logged_input(prompt=''):
            response = original_input(prompt)
            try:
                append_terminal_row(csv_path, f"[INPUT] {prompt}{response}", device_tag="INPUT")
            except Exception:
                pass
            return response

        builtins.input = logged_input

    return csv_path

def Log(Category: str, TAG: str, State: str, Message: str, Value: str, Info: str = "", AdditionalMessage: str = "", AdditionalValue: str = "", AdditionalInfo: str = "", Else: str = ""):

    # Aktuelle Zeit abrufen
    now = datetime.now()
    
   
    date_str = now.strftime("%Y-%m-%d")                                      # Tag (Jahr-Monat-Tag)
    time_str = now.strftime("%H:%M:%S")                                     # Stunde:Minute:Sekunde
    ms_str = f"{now.microsecond // 1000:03d},{now.microsecond % 1000:03d}"  # microsecond,microsecond

    ausgabe = (
        f"{date_str:<10.10} | "
        f"{time_str:<10.10} | "
        f"{ms_str:<10.10} | "
        f"{Category:<15.15} | "
        f"{TAG:<10.10} | "
        f"{State:<20.20} | " 
        f"{Message:<50.50} | "
        f"{Value:<50.50} | "
        f"{Info:<15.15} | "
        f"{AdditionalMessage:<15.15} | "
        f"{AdditionalValue:<15.15} | "
        f"{AdditionalInfo:<10.10} | "
        f"{Else:<10.10}"
    )
    
    print(ausgabe)

def Test_Log():
    print("--- Starte Log-Tests ---")
    
    # Test 1: Nur Pflichtfelder (optionale Felder bleiben leer)
    Log(
        Category="SYSTEM", 
        TAG="INFO", 
        State="Start", 
        Message="Anwendung gestartet", 
        Value="0"
    )
    
    # Test 2: Voll ausgefüllter Log-Eintrag
    Log(
        Category="NETWORK", 
        TAG="ERR", 
        State="Verbindung verloren", 
        Message="FAILED", 
        Value="404", 
        Info="Retry in 3s", 
        AdditionalMessage="Timeout Error", 
        AdditionalValue="5000ms", 
        AdditionalInfo="Port 80", 
        Else="Fatal"
    )
    
    # Test 3: Überlängentest (wird dank .XX sauber abgeschnitten, kein Absturz)
    Log(
        Category="DATABASE_SYSTEM_LONG", 
        TAG="WARNING_TAG", 
        State="Dieser Status ist viel zu lang", 
        Message="Diese Nachricht überschreitet die erlaubten 50 Zeichen massiv und wird abgeschnitten.", 
        Value="Unendlicher Wert"
    )
    
    print("--- Tests beendet ---")

# Test-Funktion ausführen
Test_Log()
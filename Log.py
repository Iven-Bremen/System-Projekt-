"""Zentrale Logging-Komponente fuer das Messprogramm.

Dieses Modul sammelt alle Meldungen an einer Stelle. Die anderen Programmteile
muessen dadurch weder CSV-Dateien oeffnen noch deren Spaltenaufbau kennen.

Eine Meldung kann gleichzeitig an drei Stellen erscheinen:

1. sofort im Terminal,
2. in der GUI ueber registrierte Callbacks,
3. in der aktiven CSV-Datei.

`Log()` ist die einzige oeffentliche Schnittstelle. `Category` beschreibt den
Bereich (`Sys`, `Comm`, `Gui`, `Calc`, `Log`), `TAG` die Quelle oder das
Geraet, `State` den Zustand, `Message` das Ereignis oder den Befehl, `Value`
den Mess- oder Antwortwert und `Info` den Zusatzkontext.

Beispiel aus einer anderen Klasse:

    import Log
    Log.Log("Calc", "MEASUREMENT", "Start", "Messung gestartet", "0")

Das Modul ist keine Klasse, die zuerst instanziiert werden muss. Es wird direkt
importiert und stellt seine Funktionen als gemeinsame Schnittstelle bereit.
"""
import csv
import os
import sys
import threading
from datetime import datetime

import State

CSV_COLUMNS_NEW = [
    # Diese Reihenfolge ist verbindlich fuer jede geschriebene Datenzeile.
    "Date", "Time", "Ms", "Category", "Tag", "State", "Message", "Value", "Info",
    "AdditionalMessage", "AdditionalValue", "AdditionalInfo", "Else",
]
CSV_COLUMNS = CSV_COLUMNS_NEW
CSV_DELIMITER = ","
LOG_CATEGORIES = ("Sys", "Comm", "Gui", "Calc", "Log")
LOG_STATES = ("Start", "End", "Info", "Warning", "Error")
# Category, Tag, State und Message sind fuer jede Datenzeile Pflichtfelder.
REQUIRED_COLUMN_INDEXES = (3, 4, 5, 6)

# Alle Log-Funktionen verwenden waehrend einer Sitzung denselben Dateipfad.
# Der Lock ist notwendig, weil Geraete-, GUI- und Logging-Threads gleichzeitig
# Meldungen erzeugen koennen. Jede komplette CSV-Zeile wird atomar gegen andere
# Schreiber abgeschirmt, damit keine Zeilen ineinander geschrieben werden.
_CURRENT_SESSION_LOG_PATH = None
_LOG_LOCK = threading.RLock()
# GUI-Funktionen, die bei jeder neuen Meldung mit dem formatierten Text
# aufgerufen werden. Jede Callback kann optional einen eigenen Filter besitzen,
# damit die GUI nur noch das relevante Live-Log auswählt, während die Logik
# selbst zentral in dieser Datei bleibt.
_gui_callbacks = []
_GUI_LOG_BUFFER = []
_MAX_GUI_LOG_BUFFER = 200

LIVE_LOG_ALLOWED_RUNNING_TOKENS = (
    "LR", "LS", "GVS", "GVN", "*IDN?", "ERRS?", "LIAS?",
    "LCA", "LVA", "LPCA", "LPA", "T1A", "GT", "GS", "GM",
    "1TA", "1TCA", "1TVA", "LCT", "LCL", "LVC",
)


def _compact_gui_entry(raw_message, fallback_tag="LOG"):
    """Konvertiert rohe Logzeilen in die Kurzfassung fuer die GUI."""
    text = (raw_message or "").strip()
    if not text:
        return ""
    if " | " in text and "|" in text:
        return text

    try:
        parsed = next(csv.reader([text]))
    except Exception:
        parsed = []

    if len(parsed) >= 9:
        fields = parsed[3:9]
        compact = " | ".join((value or "").strip() for value in fields)
        if compact:
            return compact + "\n"

    if text.startswith("[") and "]" in text:
        return text.strip() + "\n"
    return f"{fallback_tag} | {text}\n"


def gui_live_log_filter(formatted_message):
    """Central visibility rule for the GUI Live Log."
    "All entries except 'Running' are always displayed. 
    For 'Running', only defined relevant commands are allowed 
    so that the live log is not flooded with polling and status noise."""
    if not isinstance(formatted_message, str):
        return True
    if "| Running |" not in formatted_message:
        return True
    return any(token in formatted_message for token in LIVE_LOG_ALLOWED_RUNNING_TOKENS)


def flush_gui_startup_buffer():
    """Leert den Start-Buffer einmalig in alle registrierten GUI-Callbacks."""
    if not _gui_callbacks:
        return
    pending_messages = list(_GUI_LOG_BUFFER)
    _GUI_LOG_BUFFER.clear()
    for message in pending_messages:
        for callback, callback_filter in list(_gui_callbacks):
            if not _should_emit_to_gui(message, callback_filter):
                continue
            try:
                callback(message)
            except Exception:
                pass


def register_gui_callback(callback_func, filter_func=None):
    """Registriert eine Funktion fuer neue Logzeilen.

    `callback_func` muss genau einen Parameter akzeptieren. Beim Auftreten
    einer neuen Meldung wird dieser Funktion der bereits formatierte Text
    uebergeben. Optional kann `filter_func` ebenfalls einen Parameter nutzen
    und entscheidet, ob die Zeile an den Callback weitergereicht wird.

    Bereits vorhandene Eintraege aus dem Start-Buffer werden beim ersten
    Registrieren genau einmal an den Callback weitergereicht, damit Logzeilen,
    die vor dem GUI-Start entstanden sind, nicht verloren gehen.
    """
    _gui_callbacks.append((callback_func, filter_func))
    if len(_gui_callbacks) == 1:
        flush_gui_startup_buffer()


def _should_emit_to_gui(formatted_message, filter_func=None):
    """Entscheidet, ob ein formatierter Logeintrag an den GUI-Callback geht."""
    if filter_func is None:
        return True
    try:
        return bool(filter_func(formatted_message))
    except Exception:
        return True

def make_log_path(prefix="M", base_name=None):
    """Erzeugt den Dateipfad fuer eine Logdatei.

    `prefix` kennzeichnet die Sitzung: `M` steht fuer Messung und `T` fuer
    Simulation. Andere Werte werden automatisch wie `M` behandelt.
    Mit `base_name` kann ein fester Dateiname fuer Tests oder Sonderfaelle
    vorgegeben werden. Ohne diesen Namen entsteht ein Dateiname aus Uhrzeit,
    Datum und Sitzungsart.

    Der Tagesordner `logs/JJJJ-MM-TT` wird bei Bedarf angelegt. Zurueckgegeben
    wird der relative Pfad, unter dem die CSV-Datei gespeichert werden soll.
    """
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
        filename = f"{time_str}_simulation_log.csv"
    else:
        filename = f"{time_str}_{State.Experiment}_log.csv"

    return os.path.join(log_dir, filename)


def _get_active_log_path():
    """Liefert den aktiven Log-Pfad und erzeugt ihn beim ersten Aufruf."""
    global _CURRENT_SESSION_LOG_PATH
    if _CURRENT_SESSION_LOG_PATH is None:
        _CURRENT_SESSION_LOG_PATH = make_log_path("M")
        ensure_log_file(_CURRENT_SESSION_LOG_PATH)
    return _CURRENT_SESSION_LOG_PATH


def get_csv_writer(f):
    """Erzeugt den gemeinsamen CSV-Schreiber fuer alle Logdateien."""
    return csv.writer(f, delimiter=CSV_DELIMITER, quoting=csv.QUOTE_MINIMAL)


def ensure_log_file(csv_path):
    """Stellt sicher, dass `csv_path` eine verwendbare CSV-Datei bezeichnet."""
    directory = os.path.dirname(csv_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with _LOG_LOCK:
        if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
            with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
                writer = get_csv_writer(f)
                writer.writerow(CSV_COLUMNS_NEW)
            return True
    return False


def insert_session_separator(csv_path, mode="HARDWARE"):
    """Schreibt den Beginn einer neuen Sitzung in die CSV-Datei."""
    with _LOG_LOCK:
        ensure_log_file(csv_path)
        with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = get_csv_writer(f)
            date_str = datetime.now().strftime("%Y-%m-%d")
            time_str = datetime.now().strftime("%H:%M:%S")
            ms_str = datetime.now().strftime("%f")[:3]
            writer.writerow([
                date_str, time_str, ms_str, "SESSION", "SYSTEM", mode, "Session started", "", "", "", "", "", "",
            ])


def _append_row(csv_path, row):
    """Speichert eine vorbereitete CSV-Zeile, wenn sie gueltig ist."""
    if any(not str(row[index]).strip() for index in REQUIRED_COLUMN_INDEXES):
        return False
    with _LOG_LOCK:
        ensure_log_file(csv_path)
        with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
            get_csv_writer(f).writerow(row)
    return True


def append_terminal_row(csv_path, text, device_tag="TERMINAL"):
    """Schreibt eine Ausgabezeile aus Terminal, Fehlerstrom oder Eingabe."""
    with _LOG_LOCK:
        ensure_log_file(csv_path)
        with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = get_csv_writer(f)
            dt = datetime.now()
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M:%S")
            ms_str = dt.strftime("%f")[:3]
            writer.writerow([
                date_str, time_str, ms_str, "OUTPUT", device_tag, "OUTPUT", text, "", "", "", "", "", "",
            ])


class _Tee:
    """Verteilt eine Standardausgabe auf Terminal, CSV und GUI-Callbacks."""

    def __init__(self, original, csv_path, device_tag="TERMINAL"):
        self.original = original
        self.csv_path = csv_path
        self.device_tag = device_tag

    def write(self, message):
        """Schreibt `message` in Stream, CSV und registrierte GUIs."""
        # Sicherheitsprüfung für fensterlosen Modus (-w / PyInstaller)
        if self.original is not None:
            self.original.write(message)
            self.original.flush()

        if message and not message.isspace():
            for line in message.rstrip("\n").splitlines():
                clean_line = line.strip()

                if not clean_line or set(clean_line).issubset(set(" ^~")):
                    continue

                append_terminal_row(self.csv_path, clean_line, device_tag=self.device_tag)

                compact_line = _compact_gui_entry(clean_line, fallback_tag=self.device_tag)
                if not compact_line:
                    continue
                for callback, callback_filter in list(_gui_callbacks):
                    if not _should_emit_to_gui(compact_line, callback_filter):
                        continue
                    try:
                        callback(compact_line)
                    except Exception:
                        pass

    def flush(self):
        """Leert den urspruenglichen Ausgabestream."""
        if self.original is not None:
            self.original.flush()


def start_terminal_logging(prefix="M", csv_path=None, capture_input=True, insert_separator=True):
    """Aktiviert die automatische Protokollierung von Terminalausgaben."""
    global _CURRENT_SESSION_LOG_PATH
    if csv_path is None:
        csv_path = make_log_path(prefix)

    _CURRENT_SESSION_LOG_PATH = csv_path

    ensure_log_file(csv_path)
    if insert_separator:
        insert_session_separator(csv_path, mode="SIMULATION" if prefix == "T" else "HARDWARE")

    # Sichere Zuweisung für PyInstaller ohne Konsole (-w)
    sys.stdout = _Tee(getattr(sys, "__stdout__", None), csv_path, device_tag="TERMINAL")
    sys.stderr = _Tee(getattr(sys, "__stderr__", None), csv_path, device_tag="ERROR")

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
    """Schreibt einen vollstaendigen Logeintrag an alle drei Ausgabestellen."""
    now = datetime.now()
    time_str = now.strftime("%H:%M:%S")
    ms_str = now.strftime("%f")[:3]

    Category = str(Category)
    TAG = str(TAG)
    State = str(State)
    Message = str(Message)
    Value = str(Value)
    Info = str(Info)
    AdditionalMessage = str(AdditionalMessage)
    AdditionalValue = str(AdditionalValue)
    AdditionalInfo = str(AdditionalInfo)
    Else = str(Else)

    row = [
        now.strftime("%Y-%m-%d"), time_str, ms_str,
        Category, TAG, State, Message, Value, Info, AdditionalMessage,
        AdditionalValue, AdditionalInfo, Else,
    ]
    row = ["" if value is None else str(value) for value in row]
    ausgabe = (
        f"{row[0]:<10.10} | "
        f"{time_str}.{ms_str:<7.7} | "
        f"{Category:<15.15} | "
        f"{TAG:<10.10} | "
        f"{State:<20.20} | " 
        f"{Message:<50.50} | "
        f"{Value:<50.50} | "
        f"{Info:<15.25} | "
        f"{AdditionalMessage:<15.15} | "
        f"{AdditionalValue:<15.15} | "
        f"{AdditionalInfo:<10.10} | "
        f"{Else:<10.10}"
    )

    # Nur schreiben, wenn ein stdout-Stream existiert (verhindert Crash bei -w)
    if sys.__stdout__ is not None:
        sys.__stdout__.write(ausgabe + "\n")
        sys.__stdout__.flush()

    gui_message = " | ".join(
        field.strip() if isinstance(field, str) else str(field)
        for field in (Category, TAG, State, Message, Value, Info)
    ) + "\n"

    log_path = _get_active_log_path()
    _append_row(log_path, row)

    if not _gui_callbacks:
        if len(_GUI_LOG_BUFFER) >= _MAX_GUI_LOG_BUFFER:
            _GUI_LOG_BUFFER.pop(0)
        _GUI_LOG_BUFFER.append(gui_message)
        return

    for callback, filter_func in _gui_callbacks:
        if not _should_emit_to_gui(gui_message, filter_func):
            continue
        try:
            callback(gui_message)
        except Exception:
            pass

def Look_Up_CSV(Category: str, TAG: str, Message: str, State: str = " "):
    """Sucht nach übereinstimmenden Einträgen in der aktuell verwendeten CSV-Datei."""
    log_path = _get_active_log_path()
    result = []
    requested_fields = (
        "Date", "Time", "Ms", "Value", "Info",
        "AdditionalValue", "AdditionalInfo",
    )

    with open(log_path, mode="r", newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            if (
                row.get("Category") == Category
                and row.get("Tag") == TAG
                and row.get("Message") == Message
                and (not State.strip() or row.get("State") == State)
            ):
                result.append({field: row.get(field, "") for field in requested_fields})

    return result


def Merge_Look_Up_CSV(first_lookup, second_lookup):
    """Führt zwei Suchergebnisse anhand ihrer Zeitstempel zusammen."""
    def timestamp(row):
        try:
            return datetime.strptime(
                f"{row.get('Date', '')} {row.get('Time', '')}.{row.get('Ms', '0')}",
                "%Y-%m-%d %H:%M:%S.%f",
            )
        except (TypeError, ValueError):
            return datetime.max

    first_lookup = sorted(
        (dict(row) for row in first_lookup),
        key=timestamp,
    )
    second_lookup = sorted(
        (dict(row) for row in second_lookup),
        key=timestamp,
    )

    first_index = 0
    second_index = 0
    merged = []

    while first_index < len(first_lookup) or second_index < len(second_lookup):
        if second_index >= len(second_lookup):
            source = 1
        elif first_index >= len(first_lookup):
            source = 2
        elif timestamp(first_lookup[first_index]) < timestamp(second_lookup[second_index]):
            source = 1
        else:
            source = 2

        if source == 1:
            row = first_lookup[first_index]
            first_index += 1
        else:
            row = second_lookup[second_index]
            second_index += 1

        row["Source"] = source
        merged.append(row)

    return merged



if __name__ == "__main__":
    Log("Sys", "INFO", "Start", "Log-Modul direkt gestartet", "0")
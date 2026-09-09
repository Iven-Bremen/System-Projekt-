"""Zentrale Logging-Komponente fuer das Messprogramm.

Dieses Modul sammelt alle Meldungen an einer Stelle. Die anderen Programmteile
muessen dadurch weder CSV-Dateien oeffnen noch deren Spaltenaufbau kennen.

Eine Meldung kann gleichzeitig an drei Stellen erscheinen:

1. sofort im Terminal,
2. in der GUI ueber registrierte Callbacks,
3. in der aktiven CSV-Datei.

Fuer neuen Code ist `Log()` die vollstaendige Schnittstelle. `LogMassage()`
bleibt fuer bestehende Aufrufe erhalten und wandelt deren alte
Parameterreihenfolge in das aktuelle CSV-Format um.

Beispiel aus einer anderen Klasse:

    import Log
    Log.Log("MEASUREMENT", "INFO", "RUNNING", "Messung gestartet", "0")

Das Modul ist keine Klasse, die zuerst instanziiert werden muss. Es wird direkt
importiert und stellt seine Funktionen als gemeinsame Schnittstelle bereit.
"""
import csv
import os
import sys
from datetime import datetime

CSV_COLUMNS_NEW = [
    # Diese Reihenfolge ist verbindlich fuer jede geschriebene Datenzeile.
    "Date", "Time", "Ms", "Category", "Tag", "State", "Message", "Value", "Info",
    "AdditionalMessage", "AdditionalValue", "AdditionalInfo", "Else",
]
CSV_COLUMNS = CSV_COLUMNS_NEW
CSV_DELIMITER = ","
# Category, Tag, State und Message sind fuer jede Datenzeile Pflichtfelder.
REQUIRED_COLUMN_INDEXES = (3, 4, 5, 6)

# Alle Log-Funktionen verwenden waehrend einer Sitzung denselben Dateipfad.
_CURRENT_SESSION_LOG_PATH = None
# GUI-Funktionen, die bei jeder neuen Meldung mit dem formatierten Text
# aufgerufen werden.
_gui_callbacks = []

def register_gui_callback(callback_func):
    """Registriert eine Funktion fuer neue Logzeilen.

    `callback_func` muss genau einen Parameter akzeptieren. Beim Auftreten
    einer neuen Meldung wird dieser Funktion der bereits formatierte Text
    uebergeben. Die GUI kann damit ein Logfenster aktualisieren, ohne selbst
    CSV-Dateien zu oeffnen.

    Die Funktion wird hier noch nicht aufgerufen, sondern nur fuer spaetere
    Meldungen vorgemerkt.
    """
    _gui_callbacks.append(callback_func)

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
        filename = f"{time_str}_{date_folder}_simulation_log.csv"
    else:
        filename = f"{time_str}_{date_folder}_measurement_log.csv"

    return os.path.join(log_dir, filename)


def _get_active_log_path():
    """Liefert den aktiven Log-Pfad und erzeugt ihn beim ersten Aufruf.

    Wird noch keine Datei verwendet, legt die Funktion automatisch eine
    Messdatei an. Danach liefert sie immer denselben Pfad zurueck, damit eine
    laufende Sitzung nicht versehentlich auf mehrere Dateien verteilt wird.
    Diese Funktion ist intern und wird normalerweise nicht direkt aufgerufen.
    """
    global _CURRENT_SESSION_LOG_PATH
    if _CURRENT_SESSION_LOG_PATH is None:
        _CURRENT_SESSION_LOG_PATH = make_log_path("M")
        ensure_log_file(_CURRENT_SESSION_LOG_PATH)
    return _CURRENT_SESSION_LOG_PATH


def get_csv_writer(f):
    """Erzeugt den gemeinsamen CSV-Schreiber fuer alle Logdateien.

    `f` ist eine bereits geoeffnete Textdatei. Der Rueckgabewert ist ein
    `csv.writer` mit dem zentral festgelegten Trennzeichen. Alle Schreibwege
    verwenden diesen Helfer, damit jede CSV-Datei gleich aufgebaut ist.
    """
    return csv.writer(f, delimiter=CSV_DELIMITER, quoting=csv.QUOTE_MINIMAL)


def ensure_log_file(csv_path):
    """Stellt sicher, dass `csv_path` eine verwendbare CSV-Datei bezeichnet.

    Der benoetigte Ordner und die Datei werden angelegt, falls sie fehlen.
    Bei einer neuen oder leeren Datei wird ausserdem die Kopfzeile aus
    `CSV_COLUMNS_NEW` geschrieben. Bereits vorhandene Logdaten werden nicht
    ueberschrieben. Der Rueckgabewert ist `True` bei einer neuen Datei,
    ansonsten `False`.
    """
    directory = os.path.dirname(csv_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = get_csv_writer(f)
            writer.writerow(CSV_COLUMNS_NEW)
        return True
    return False


def insert_session_separator(csv_path, mode="HARDWARE"):
    """Schreibt den Beginn einer neuen Sitzung in die CSV-Datei.

    `csv_path` ist der Pfad der aktiven CSV-Datei. `mode` beschreibt, wie die
    Sitzung gestartet wurde, zum Beispiel `HARDWARE` oder `SIMULATION`.
    Der Eintrag ist eine normale, auswertbare CSV-Zeile mit den Pflichtwerten
    `SESSION`, `SYSTEM`, dem Sitzungsmodus und `Session started`.

    Frueher wurden hier mehrere leere Trennzeilen geschrieben. Das wurde
    bewusst entfernt, weil leere CSV-Zeilen die spaetere Auswertung stoeren.
    """
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
    """Speichert eine vorbereitete CSV-Zeile, wenn sie gueltig ist.

    `csv_path` bezeichnet die Zieldatei und `row` muss eine vollstaendige Liste
    in der Reihenfolge von `CSV_COLUMNS_NEW` sein. Vor dem Schreiben werden
    `Category`, `Tag`, `State` und `Message` geprueft. Ist eines dieser Felder
    leer, wird nichts geschrieben und `False` zurueckgegeben. Bei Erfolg ist
    der Rueckgabewert `True`.

    Diese zentrale Pruefung verhindert, dass einzelne Aufrufer versehentlich
    unbrauchbare oder teilweise leere Logzeilen in die CSV-Datei schreiben.
    """
    if any(not str(row[index]).strip() for index in REQUIRED_COLUMN_INDEXES):
        return False
    ensure_log_file(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        get_csv_writer(f).writerow(row)
    return True


def append_csv_row(csv_path, tag, category, message, info, additional_info, else_val=" ", dt_obj=None):
    """Uebersetzt einen alten LogMassage-Aufruf in eine CSV-Zeile.

    Parameter:
        csv_path: Ziel der CSV-Datei.
        tag: Herkunft oder Kennzeichnung der Meldung, zum Beispiel `COM3`.
        category: Gruppe der Meldung, zum Beispiel `Info` oder `Warning`.
        message: Beschreibung des Ereignisses. Dieses Feld ist Pflicht.
        info: Statuswert, der als `State` gespeichert wird. Fehlt er, wird
            ersatzweise `INFO` verwendet.
        additional_info: Optionaler Zusatzwert fuer `AdditionalInfo`.
        else_val: Optionaler Wert fuer die letzte CSV-Spalte.
        dt_obj: Optionaler Zeitpunkt. Ohne Angabe wird jetzt verwendet.

    Die Funktion existiert vor allem fuer die alte `LogMassage`-Schnittstelle.
    Neue Stellen sollten direkt `Log()` verwenden.
    """
    dt = dt_obj or datetime.now()
    _append_row(csv_path, [
        dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S"), dt.strftime("%f")[:3],
        category, tag, info or "INFO", message, info or "", "", "", "", additional_info or "", else_val or "",
    ])


def append_terminal_row(csv_path, text, device_tag="TERMINAL"):
    """Schreibt eine Ausgabezeile aus Terminal, Fehlerstrom oder Eingabe.

    `csv_path` ist die Zieldatei, `text` der auszugebende Inhalt und
    `device_tag` kennzeichnet die Quelle, zum Beispiel `TERMINAL`, `ERROR` oder
    `INPUT`. Die Funktion verwendet feste technische Werte fuer Category und
    State, damit auch automatisch abgefangene Ausgaben die Pflichtfelder
    besitzen.
    """
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


def LogMassage(TAG: str, Category: str, Massage: str, INFO: str, AdditionalInfo: str = ""):
    """Verarbeitet einen Log-Aufruf im alten Projektformat.

    Parameter:
        TAG: Herkunft der Meldung, zum Beispiel `COM3`, `Gui` oder ein
            Klassenname.
        Category: Art der Meldung, zum Beispiel `Info` oder `Warning`.
        Massage: Der eigentliche Beschreibungstext des Ereignisses. Der
            historische Schreibfehler im Parameternamen bleibt aus
            Kompatibilitaetsgruenden bestehen.
        INFO: Zusatzstatus oder Ergebnis, zum Beispiel `Test`, `Fail` oder
            `9600`.
        AdditionalInfo: Optionaler weiterer Hinweis fuer die CSV-Datei.

    Ablauf:
        1. Die Meldung wird mit Datum, Uhrzeit und Millisekunden formatiert.
        2. Sie wird sofort in das echte Terminal geschrieben.
        3. Alle registrierten GUI-Callbacks erhalten denselben Text.
        4. Die Meldung wird in der aktiven CSV-Datei gespeichert.

    Die ungewoehnliche Reihenfolge der Parameter bleibt absichtlich erhalten,
    damit bestehende Aufrufer aus `Starter.py`, `Commands.py` und
    `Komunikation.py` weiter funktionieren. Fuer neuen Code ist `Log()` besser
    geeignet, weil dessen Parameter die CSV-Struktur deutlicher abbilden.
    """
    dt = datetime.now()
    date_str = dt.strftime("%Y-%m-%d")
    time_str = dt.strftime("%H:%M:%S")
    ms_str = dt.strftime("%f")[:3]
    
    console_line = f"{date_str} {time_str}.{ms_str}  |  {TAG}  |  {Category}  |  {Massage}  |  {INFO}  |  {AdditionalInfo}"

    sys.__stdout__.write(console_line + "\n")
    sys.__stdout__.flush()
    
    for cb in _gui_callbacks:
        cb(console_line + "\n")

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
    """Verteilt eine Standardausgabe auf mehrere Ziele.

    Die Klasse wird intern von `start_terminal_logging()` verwendet. Sie laesst
    Ausgaben im echten Terminal sichtbar, schreibt gleichzeitig verwertbare
    Zeilen in die CSV und informiert die GUI. Leere Zeilen und reine
    Fortschrittszeichen werden nicht als Logzeilen gespeichert.
    """

    def __init__(self, original, csv_path, device_tag="TERMINAL"):
        """Erzeugt eine Weiterleitung fuer einen Ausgabekanal.

        `original` ist der urspruengliche Stream, etwa `sys.__stdout__` oder
        `sys.__stderr__`. `csv_path` ist die Datei, in die Ausgaben geschrieben
        werden. `device_tag` kennzeichnet den Kanal in der CSV.
        """
        self.original = original
        self.csv_path = csv_path
        self.device_tag = device_tag

    def write(self, message):
        """Schreibt `message` in Stream, CSV und registrierte GUIs."""
        self.original.write(message)
        self.original.flush()

        if message and not message.isspace():
            for line in message.rstrip("\n").splitlines():
                clean_line = line.strip()

                # Fortschrittszeichen und Leerzeilen sind keine verwertbaren Logs.
                if not clean_line or set(clean_line).issubset(set(" ^~")):
                    continue

                append_terminal_row(self.csv_path, clean_line, device_tag=self.device_tag)

                for cb in _gui_callbacks:
                    cb(f"[{self.device_tag}] {clean_line}\n")

    def flush(self):
        """Leert den urspruenglichen Ausgabestream."""
        self.original.flush()


def start_terminal_logging(prefix="M", csv_path=None, capture_input=True, insert_separator=True):
    """Aktiviert die automatische Protokollierung von Terminalausgaben.

    Parameter:
        prefix: `M` fuer Messung oder `T` fuer Simulation. Bestimmt den
            automatischen Dateinamen und den Sessionmodus.
        csv_path: Optionaler eigener Dateipfad. Ohne Angabe wird ein neuer
            Tagesordner mit automatisch erzeugtem Dateinamen verwendet.
        capture_input: Wenn `True`, werden Antworten auf `input()` ebenfalls
            protokolliert. Bei `False` bleibt die Eingabe unveraendert.
        insert_separator: Wenn `True`, wird am Anfang ein Sessioneintrag
            geschrieben.

    Rueckgabe:
        Der verwendete CSV-Pfad.

    Die Funktion sollte einmal beim Programmstart aufgerufen werden. Danach
    bleiben `print()` und Fehlermeldungen im Terminal sichtbar, werden aber
    zusaetzlich in der CSV-Datei und bei registrierten GUIs abgelegt.
    """
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
    """Schreibt einen vollstaendigen Logeintrag an alle drei Ausgabestellen.

    Pflichtparameter:
        Category: Fachliche oder technische Gruppe, zum Beispiel `SYSTEM`,
            `COMMUNICATION` oder `MEASUREMENT`.
        TAG: Kurze Kennzeichnung der Quelle oder des Geraets, zum Beispiel
            `SR830`, `COM3` oder `GUI`.
        State: Zustand oder Ergebnis, zum Beispiel `START`, `OK`, `WARNING`
            oder `FAILED`.
        Message: Menschenlesbare Beschreibung des Ereignisses.
        Value: Zugehoeriger Wert. Dieser darf leer sein, weil er nicht zu den
            vier Pflichtspalten gehoert.

    Optionale Parameter:
        Info: Kurzer Zusatzstatus.
        AdditionalMessage: Weiterer beschreibender Text.
        AdditionalValue: Weiterer Mess- oder Konfigurationswert.
        AdditionalInfo: Zusatzinformation, etwa Port oder Geraete-ID.
        Else: Freies Zusatzfeld fuer Sonderfaelle.

    Die Funktion erzeugt Datum, Uhrzeit und Millisekunden automatisch. Sie
    zeigt den Eintrag sofort im Terminal, informiert alle GUI-Callbacks und
    schreibt anschliessend eine CSV-Zeile. Ist eines der Pflichtfelder leer,
    verhindert `_append_row()` das Speichern dieser Zeile.
    """
    now = datetime.now()
    time_str = now.strftime("%H:%M:%S")
    ms_str = now.strftime("%f")[:3]

    row = [
        now.strftime("%Y-%m-%d"), time_str, ms_str,
        Category, TAG, State, Message, Value, Info, AdditionalMessage,
        AdditionalValue, AdditionalInfo, Else,
    ]
    ausgabe = (
        f"{row[0]:<10.10} | "
        f"{time_str}.{ms_str:<7.7} | "
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

    sys.__stdout__.write(ausgabe + "\n")
    sys.__stdout__.flush()

    log_path = _get_active_log_path()
    _append_row(log_path, row)
    
    for cb in _gui_callbacks:
        cb(ausgabe + "\n")

def Look_Up_CVS(Category: str, TAG: str, Message: str, State: str = " "):
    """Sucht passende Eintraege in der aktuell verwendeten CSV-Datei.

    `Category`, `TAG` und `Message` werden immer exakt verglichen. Wenn
    `State` leer oder nur aus Leerzeichen besteht, wird jeder Status akzeptiert;
    andernfalls muss auch der Status exakt passen. Zur weiteren Verarbeitung
    werden nur die angeforderten Datenfelder als Liste von Dictionaries
    zurueckgegeben.
    """
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

def Test_Log():
    """Fuehrt drei einfache manuelle Tests fuer das Logging aus.

    Getestet werden ein normaler Eintrag mit wenigen Werten, ein vollstaendig
    ausgefuellter Eintrag und ein langer Text. Die Funktion ist fuer lokale
    Kontrolle gedacht und wird nur ausgefuehrt, wenn `Log.py` direkt gestartet
    wird. Beim Import des Moduls startet sie nicht automatisch.
    """
    print("--- Starte Log-Tests ---")
    
    # Test 1: Pflichtfelder mit leer gelassenen optionalen Feldern.
    Log(
        Category="SYSTEM", 
        TAG="INFO", 
        State="Start", 
        Message="Anwendung gestartet", 
        Value="0"
    )
    
    # Test 2: Ein Eintrag, bei dem auch die optionalen Felder verwendet werden.
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
    
    # Test 3: Langer Inhalt. Der Formatter darf dabei nicht abstuerzen.
    Log(
        Category="DATABASE_SYSTEM_LONG", 
        TAG="WARNING_TAG", 
        State="Dieser Status ist viel zu lang", 
        Message="Diese Nachricht überschreitet die erlaubten 50 Zeichen massiv und wird abgeschnitten.", 
        Value="Unendlicher Wert"
    )
    
    print("--- Tests beendet ---")

if __name__ == "__main__":
    Test_Log()


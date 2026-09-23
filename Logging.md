# Logging-Architektur

## 1. Zweck und reale Verantwortung

Das Logging in diesem Projekt ist keine bloße Konsolenausgabe, sondern die zentrale Beobachtungs- und Diagnose-Schicht für die gesamte Anwendung. Alle Ereignisse aus GUI, Threads, Berechnung, Kommunikationslogik und Hardware werden an genau einer Stelle zusammengeführt.

Das bedeutet praktisch:

- `Log.py` schreibt Einträge in die aktive CSV-Datei
- dieselben Einträge werden zusätzlich auf der Konsole ausgegeben
- registrierte GUI-Callbacks erhalten die Live-Version der Ereignisse

Der Projekt-Code verwendet diese Log-Schicht bewusst als öffentliche API. Alle relevanten Module sollten über `Log.Log(...)` laufen, statt selbst CSV-Dateien oder Formatierungslogik zu implementieren.

Die Architektur ist bewusst zentralisiert:

```text
GUI / Starter / Kommunikation / Threads / Berechnung
                   |
                   v
                Log.Log(...)
                   |
       +-----------+-----------+
       |                       |
       v                       v
  Terminalausgabe           CSV-Datei
       |                       |
       v                       v
   GUI-Live-Log            Analyse / Auswertung
```

Wichtig ist: Ein Ereignis wird nur einmal erzeugt und dann an mehrere Ausgabekanäle verteilt.

---

## 2. Die konkreten Log-Elemente in `Log.py`

Die Datei `Log.py` definiert die Kernpunkte der Lösung:

- `CSV_COLUMNS_NEW`: feste Spaltenreihenfolge
- `REQUIRED_COLUMN_INDEXES = (3, 4, 5, 6)`: `Category`, `Tag`, `State`, `Message`
- `_CURRENT_SESSION_LOG_PATH`: Pfad der aktuell aktiven Session-Datei
- `_LOG_LOCK = threading.RLock()`: globaler Schreibschutz
- `_gui_callbacks`: registrierte GUI-Callbacks
- `_GUI_LOG_BUFFER`: Puffer für frühe Einträge vor dem GUI-Start

Die Kernfunktion ist:

```python
Log(Category, TAG, State, Message, Value, Info="", ...)
```

Diese Funktion baut aus den einzelnen Feldern eine vollständige CSV-Zeile und erzeugt zusätzlich eine lesbare Terminaldarstellung. Die CSV-Version ist die maschinenlesbare Hauptrepräsentation; die Terminal-Version ist für Menschen gedacht.

---

## 3. CSV-Format und Pflichtfelder

Jede Logdatei beginnt mit einem festen Header:

```text
Date,Time,Ms,Category,Tag,State,Message,Value,Info,AdditionalMessage,AdditionalValue,AdditionalInfo,Else
```

Die Reihenfolge ist in `CSV_COLUMNS_NEW` explizit festgelegt:

```python
CSV_COLUMNS_NEW = [
    "Date", "Time", "Ms", "Category", "Tag", "State", "Message", "Value", "Info",
    "AdditionalMessage", "AdditionalValue", "AdditionalInfo", "Else",
]
```

Die vier Pflichtfelder sind:

```python
REQUIRED_COLUMN_INDEXES = (3, 4, 5, 6)
```

Das entspricht:

- `Category`
- `Tag`
- `State`
- `Message`

Wenn eines dieser Felder fehlt oder leer ist, verwirft `_append_row()` den Eintrag. Das ist wichtig, weil spätere Auswertungen nur mit gültigen Kategorien, Tags, Zuständen und Meldungen sauber funktionieren.

---

## 4. Dateinamen und Sitzungsstruktur

Beim Start wird ein Logpfad generiert. Die Funktion `make_log_path()` bildet den Pfad aus:

- Tagesordner: `logs/YYYY-MM-DD`
- Dateiname:
  - Messbetrieb: `HH-MM-SS_<State.Experiment>_log.csv`
  - Simulation: `HH-MM-SS_simulation_log.csv`

Das passiert in dieser Form:

```python
log_dir = os.path.join("logs", date_folder)
os.makedirs(log_dir, exist_ok=True)

if prefix == "T":
    filename = f"{time_str}_simulation_log.csv"
else:
    filename = f"{time_str}_{State.Experiment}_log.csv"
```

Wichtig ist: Der aktive Pfad wird nur einmal pro Sitzung gesetzt. `_CURRENT_SESSION_LOG_PATH` verhindert, dass mehrere Threads nachträglich eine zweite Datei öffnen und dieselbe Messung aufspalten.

---

## 5. Sitzungsstart und Session-Protokollierung

`start_terminal_logging()` ist der Initialisierungspunkt beim Programmstart. Darin passiert konkret:

1. Pfad bestimmen
2. Ordner sicherstellen
3. Datei anlegen und Header schreiben
4. optionalen Session-Separator einfügen
5. `sys.stdout` durch `_Tee` ersetzen
6. `sys.stderr` durch `_Tee` ersetzen
7. `input()` nachprotokollieren, falls aktiviert

Der Session-Eintrag wird mit `insert_session_separator()` in die CSV geschrieben. Beispiel:

```python
writer.writerow([
    date_str, time_str, ms_str, "SESSION", "SYSTEM", mode,
    "Session started", "", "", "", "", "", "",
])
```

Das heißt: Auch der Start einer Programmsitzung ist als normale CSV-Zeile geführt und nicht als verborgenes Nebenprodukt.

---

## 6. Typischer Verlauf von `Log.Log()`

Der reale Ablauf ist:

```python
now = datetime.now()
row = [Date, Time, Ms, Category, Tag, State, Message, Value, Info, ...]

terminal_line = f"{Date} | {Time}.{Ms} | {Category} | {Tag} | {State} | {Message}"

sys.__stdout__.write(terminal_line + "\n")
_append_row(_CURRENT_SESSION_LOG_PATH, row)
```

Das zeigt den eigentlichen Ablauf:

1. Zeitstempel erzeugen
2. CSV-Zeile vorbereiten
3. Terminalformat erzeugen
4. Ausgabe auf echten Standardstrom schreiben
5. CSV-Datei sichern
6. GUI-Callbacks informieren

Der Logger ist damit die zentrale Fan-out-Stelle: Ein Ereignis wird nicht mehrfach erzeugt, sondern einmal erzeugt und mehrfach weitergeleitet.

---

## 7. Thread-Sicherheit und Dateiintegrität

Das zentrale Sicherheitsmerkmal ist:

```python
_LOG_LOCK = threading.RLock()
```

Das ist bewusst ein `RLock` und kein einfaches `Lock`, weil `ensure_log_file()` intern ebenfalls mit demselben Lock arbeitet. Dadurch sind die folgenden Vorgänge seriell:

- Dateiexistenz prüfen
- Header schreiben
- eine komplette Zeile schreiben
- Session-Marker schreiben
- Terminal-/Fehlerausgaben in die CSV übernehmen

Die kritische Stelle ist `_append_row()`:

```python
if any(not str(row[index]).strip() for index in REQUIRED_COLUMN_INDEXES):
    return False

with _LOG_LOCK:
    ensure_log_file(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)
```

Damit werden kaputte oder halbgeschriebene Zeilen verhindert. Ein Logeintrag wird nur dann gespeichert, wenn `Category`, `Tag`, `State` und `Message` sinnvoll gesetzt sind.

---

## 8. Warum der Lock nötig ist

Ohne Lock könnte das passieren:

```text
Thread A: öffnet Datei
Thread B: öffnet Datei
Thread A: schreibt erste Hälfte einer Zeile
Thread B: schreibt eigene Zeile
Thread A: schreibt Rest
```

Das würde die CSV-Datei beschädigen. Der Lock bildet also eine echte Serialisierung des Dateischreibens, obwohl mehrere Worker-Threads gleichzeitig Eventdaten liefern.

Wichtig: Dieser Lock schützt nur den Dateizugriff. Er ersetzt nicht die Geräte-Locks in `Komunikation.py` und nicht die Tkinter-Regel, dass GUI-Komponenten nur im Hauptthread verändert werden dürfen.

---

## 9. GUI-Logging und Callback-Mechanik

Das Design trennt sauber:

- Logik: `Log.Log()`
- Präsentation: GUI-Callback
- Filter: `gui_live_log_filter()`

Registrierte Callbacks werden in `_gui_callbacks` gespeichert:

```python
_gui_callbacks.append((callback_func, filter_func))
```

Vor dem ersten GUI-Start werden frühe Logeinträge in `_GUI_LOG_BUFFER` gesammelt. Sobald das GUI aktiv ist, werden diese Pufferzeilen mit `flush_gui_startup_buffer()` ausgeliefert.

Die Filterregel in `gui_live_log_filter()` verhindert eine Überflutung mit Polling-Rauschen. Für `Running`-Einträge werden nur bestimmte Befehle zugelassen, z. B.:

```python
LIVE_LOG_ALLOWED_RUNNING_TOKENS = (
    "LR", "LS", "GVS", "GVN", "*IDN?", "ERRS?", "LIAS?",
    "LCA", "LVA", "LPCA", "LPA", "T1A", "GT", "GS", "GM",
    "1TA", "1TCA", "1TVA", "LCT", "LCL", "LVC",
)
```

Damit bleibt das Live-Log lesbar, auch wenn das Gerät ständig abfragt.

---

## 10. `_Tee` für `stdout` und `stderr`

`start_terminal_logging()` ersetzt `sys.stdout` und `sys.stderr` nicht durch stumme Dateien, sondern durch `_Tee`-Instanzen. `_Tee.write()` macht dabei drei Dinge:

1. Originaltext weiterhin an den echten Standardstrom senden
2. Textzeilen in die CSV als `OUTPUT`/`ERROR`-Einträge schreiben
3. registrierte GUI-Callbacks mit dem kompakten Text informieren

Wichtige Filterregel:

- leere Zeilen werden verworfen
- reine Fortschrittszeichen wie `^`, `~`, `-` und Leerzeichen werden verworfen

Dadurch entsteht eine saubere Logdatei ohne technische Leerzeilen und ohne „Rauschen“ aus dem Terminal.

Beispiel:

```python
print("No COM ports available")
```

wird in der CSV als Terminaleintrag abgespeichert, bleibt aber zugleich im echten Konsolenfenster sichtbar.

---

## 11. Log-Konventionen für Kommunikationsdaten

Diese Konvention ist im Code durchgängig sichtbar:

- Befehle und Anweisungen gehören in `Message`
- empfangene Antworten und Messwerte gehören in `Value`
- Zusatzkontext gehört in `Info`

Das gilt auch für SR830-Statusabfragen wie `ERRS?` und `LIAS?`: Sie sind reine Leseoperationen, aber kein Messwert im engeren Sinn. Daher werden ihre Antworten als Statusbytes protokolliert, auch wenn der Rohwert technisch ein Integer ist.

Beispiel:

```python
Log.Log("Send", "SR830", "Running", command_name, "read request", "query")
```

oder bei einem Fehler:

```python
Log.Log("Comm", tag, "Error", command, value, info)
```

Dadurch bleibt die Semantik der Spalten konsistent. Das macht spätere Auswertungen, Filterungen und Fehlersuche deutlich einfacher.

---

## 12. Praktische Bedeutung für das Programm

Das Logging ist für dieses Projekt die primäre Datenquelle für alles, was in der Laufzeit passiert. Es dokumentiert:

- Geräte-Start und Verbindungsfehler
- gefundene COM-Ports und Device-IDs
- Polling-basierte Messdaten
- Fehlerzustände
- GUI-Events
- Terminalausgaben und Benutzereingaben

Ohne dieses zentrale Logging wäre die Fehlersuche bei seriellen Hardwareproblemen und Messwert-Abweichungen deutlich schwieriger.

---

## 13. Beispiel einer kompletten Log-Zeile

Ein typischer Eintrag kann so aussehen:

```text
2026-09-22 | 12:00:43.123 | Comm | SR830 | Running | SNAP? 1,2,3,4,10,11 | 1.23,2.34,3.45,... | measurement snapshot
```

In CSV-Form sieht das ungefähr so aus:

```text
2026-09-22,12:00:43,123,Comm,SR830,Running,SNAP? 1,2,3,4,10,11,"1.23,2.34,3.45,...",measurement snapshot,,,,
```

Das zeigt die Bedeutung der Spalten sehr klar:

- `Message` = Vorgang oder Befehl
- `Value` = Antwort, Messwert oder Status
- `Info` = Zusatzkontext

---

## 14. Abschluss

Die Logik ist klar, zentralisiert und für reale Hardware-Software-Integration geeignet:

- `Log.py` verwaltet Format, Pfad, Lock, Terminal und CSV
- `Threads.py` liefert Ereignisse aus dem Hintergrund
- `Komunikation.py` erzeugt die eigentlichen Mess- und Statusmeldungen
- `Send.py` stellt die Befehls-API bereit

Das System ist robust gebaut: zentralisiert, thread-sicher, GUI-freundlich und für Messdaten- und Fehleranalyse geeignet.

---

## 15. Kurzform der Kernprinzipien

- Logs sind kein Nebenaspekt, sondern ein Kernbestandteil der Runtime
- Ein Event wird einmal erzeugt und dann nach außen verteilt
- Schreibzugriff wird über `_LOG_LOCK` seriellisiert
- Dateiformat und Spaltennamen sind fest definiert
- Logik und Kommunikationslogik sind bewusst getrennt
- Geräteoperationen laufen über die gemeinsame API und nicht über verstreute Einzeldateien

Damit bleibt das System auch bei asynchroner Kommunikation, mehreren Threads und realen Messgeräten nachvollziehbar und gut diagnostizierbar.

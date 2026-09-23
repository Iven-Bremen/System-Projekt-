# Kommunikationsarchitektur

## 1. Ziel dieses Dokuments

Dieses Dokument beschreibt die tatsächliche Kommunikationslogik zwischen der Python-Anwendung und den beiden Mess- und Steuergeräten:

- SR830: Lock-In-Verstärker von Stanford Research Systems
- OSTECH: Laser-/TEC-Controller

Es geht nicht nur um die allgemeine Idee, sondern um die reale Architektur im Code: `Komunikation.py`, `Send.py`, `Threads.py`, `State.py` und `Log.py` arbeiten als eines zusammen, aber mit klaren Verantwortlichkeiten.

Das Kernprinzip lautet:

> Hardwarezugriff, Protokoll-Parsing und State-Updates gehören in die Kommunikations- und Thread-Schicht. Die GUI darf nicht direkt mit seriellen Worker-Threads interagieren.

Das schützt vor Deadlocks, Race Conditions und GUI-Fehlern, die durch direkten Zugriff aus dem Hintergrundthread entstehen würden.

---

## 2. Gesamtarchitektur des Projekts

Das System ist bewusst geschichtet:

```text
GUI / Starter
    |
    v
Send.py
    |
    |  Befehls-Definitionen + High-Level API
    v
Komunikation.py
    |
    |  serielle I/O + Protokollparsing + Geräteregeln + State-Updates
    v
Threads.py
    |
    |  Hintergrundschleifen, Queues, Worker-Threads
    v
Log.py
    |
    +--> CSV-Datei
    +--> Terminal
    +--> GUI-Callbacks
```

Zusätzlich gibt es `State.py`, das den aktuellen Messzustand hält:

```text
Gerät -> Komunikation -> State.update_values() -> GUI liest State
                |
                +--> Log.Log() -> CSV/Terminal/GUI
```

Das heißt: Der Hardware-Input wird dekodiert, in den State geschrieben und zusätzlich protokolliert.

---

## 3. Zuständigkeit der einzelnen Module

### `Send.py`: öffentliche Befehls-API

`Send.py` ist die Benutzer-/Anwendungs-Schnittstelle. Es enthält:

- `SR830G` für Read-Only-Befehle
- `SR830S` für Set-/Action-Befehle
- `OSTechG` und `OSTechS` analog für OSTECH
- `resolve_sr830_setting(...)` für menschenlesbare Werte wie `"Normal"` oder `"1 s"`
- öffentliche API-Funktionen `send()`, `read()`, `set()`, `run()`

Wichtig ist: Diese Datei definiert den Befehl und seine Semantik. Sie enthält keine echte serielle Übertragung.

### `Komunikation.py`: echte Hardware-Schicht

In `Komunikation.py` passieren die eigentlichen Hardware-Operationen:

- COM-Port öffnen und schließen
- serielle Kommunikation mit `pyserial`
- Befehlskodierung und Antwortdekodierung
- Parsing von ASCII- und Binärprotokollen
- Status- und Messwert-Updates im `State`
- gerätespezifische Abfragen und Timeouts

Diese Datei ist die eigentliche technische Verbindung zur Hardware.

### `Threads.py`: Hintergrundarbeit und Orchestrierung

`Threads.py` definiert die Worker-Schicht:

- `DeviceThread`
- `MessageThread`
- `CommandThread`
- `CalculationThread`
- `CommunicationThreads`

Diese Threads sind dafür da, I/O, Messaging und Berechnungen von der GUI zu trennen. Die GUI wird nicht in den Gerätethreads direkt verändert.

### `State.py`: gemeinsamer Zustands-Speicher

`State.py` ist der In-Memory-Zustand der laufenden Messung. Typische Werte sind:

- `OUTP1`, `OUTP2`, `OUTP3`, `OUTP4`
- `PHAS`, `FREQ`
- `LCT`, `GS`, `GM`

Die GUI liest diese Werte aus dem State. Die Hardware-Threads schreiben sie hinein.

### `Log.py`: zentrale Audit- und Debug-Logs

`Log.py` sammelt Ereignisse aus allen Bereichen und schreibt sie an mehrere Ziele:

- Terminal
- CSV-Datei
- GUI-Callbacks

Damit bleibt das Logging zentralisiert und konsistent.

---

## 4. Verbindungs- und Startlogik

### `CheckCOM()`

`CheckCOM(COM, ID, Command, returnvalue)` ist eine kurze Port-Erkennung. Sie:

1. öffnet den Port
2. sendet einen Testbefehl
3. liest die Antwort
4. validiert sie
5. schließt den Port wieder

Der Zweck ist nicht das normale Gerätedaten-Handling, sondern der gezielte Porttest. Wenn ein Port nicht passt oder nicht antwortet, liefert die Funktion `False`.

### `_find_device_ports(ports)`

Diese Hilfsfunktion durchläuft die verfügbaren COM-Ports und erkennt die Geräte anhand typischer Antworten:

- SR830: `*IDN?`
- OSTECH: `GVN`

Das ist wichtig, weil die Anwendung die Geräte anhand des realen Protokolls identifizieren muss und nicht nur anhand fester Portnummern.

### `open_devices()`

`open_devices(sr830_port=None, ostech_port=None)` öffnet die beiden Geräte separat und unabhängig:

- SR830 wird mit SR830-Handshake erkannt
- OSTECH wird mit Text- und ggf. Binärmodus initialisiert
- ein fehlendes Gerät darf das andere nicht komplett blockieren

Der eigentliche serielle Zugriff wird aus `pyserial` als `serial.Serial(...)`-Objekt aufgebaut.

### `close_devices()`

Beim Beenden werden die offenen Geräte sauber geschlossen. Es wird geprüft, ob der Port noch offen ist und ob der Handle noch gültig ist.

---

## 5. SR830-Kommunikation im Detail

Der SR830 verwendet ASCII-Befehle mit einem Zeilenende `\r`.

Beispiele:

```text
FREQ?
PHAS?
SNAP? 1,2,3,4,10,11
```

### `ask_SR830()`

`ask_SR830(command, value=None, return_type=None)` ist der zentrale Lese-Mechanismus. Typischer Ablauf:

```python
with SR830_LOCK:
    SR830.write(f"{_format_command(resolved_command, value)}\r".encode("ascii"))
    SR830.flush()
    response = SR830.read_until(b"\r").decode("ascii", errors="replace").strip()
    return _convert_response(response, resolved_type)
```

Das ist das zentrale Muster:

- Befehl formatieren
- mit `\r` abschließen
- Antwort lesen
- in gewünschten Typ umwandeln
- mit Gerätelock schützen

Das verhindert, dass zwei Threads denselben seriellen Stream gleichzeitig vermischen.

### `send_SR830()`

`send_SR830(...)` sendet Befehle ohne ein Rückgabeergebnis zu erwarten. Das ist sinnvoll für reine Set- oder Action-Kommandos.

### Explizit zu `ERRS?` und `LIAS?`

Diese beiden Befehle sind ein gutes Beispiel für die Reihenfolge der Abstraktion:

- `Send.py` definiert sie als `SR830G`-Befehle
- `Komunikation.ask_SR830()` verarbeitet sie mit derselben Standardlogik wie andere SR830-Read-Befehle
- die Antwort wird als Integer interpretiert
- sie liefern ein Statusbyte, kein konfigurierbarer Wert

Das ist der entscheidende Punkt:

> `ERRS?` und `LIAS?` sind keine Setter, sondern Statusabfragen.

Sie fragen den Zustand des Lock-In-Verstärkers ab, sie verändern nichts am Gerät. Deshalb gehören sie in die `SR830G`-Gruppe der Lesebefehle, nicht in `SR830S`.

Das ist keine bloße Namensfrage, sondern eine wichtige Architekturentscheidung, weil die gesamte API zwischen:

- Lesen von Werten/Zuständen
- Schreiben von Konfigurationen/Actions

sauber trennen will.

### `_convert_response()`

Dieser Helper wandelt die Antwort je nach gewünschtem Typ um:

- `str` bleibt unverändert
- `bool` akzeptiert `1`, `0`, `true`, `false`, `on`, `off`
- numerische Typen werden mit `float`/`int` geparst

Wenn ein Wert nicht in den erwarteten Typ passt, wird eine Exception ausgelöst. Das ist bewusst, damit ein fehlerhaftes Protokoll nicht stillschweigend als gültiger Messwert akzeptiert wird.

---

## 6. OSTECH-Kommunikation: Textmodus und Binärmodus

OSTECH ist in diesem Code in zwei Betriebsarten organisiert.

### Textmodus beim Start

Beim Initialisieren wird zunächst ein einfacher ASCII-Dialog verwendet, z. B. mit:

- `GVN`
- `GS`
- `GMS8`

Die Funktion `query_ostech_text()` prüft dabei ein wichtiges Detail: Das Echo muss exakt mit dem gesendeten Befehl übereinstimmen. Wenn das nicht passiert, wird die Antwort verworfen.

```python
echo = OSTECH.read_until(b"\r")
expected_echo = f"{command.upper()}\r".encode("ascii")
if echo != expected_echo:
    raise RuntimeError(f"Unerwartetes {command}-Echo: {echo!r}")
```

Das verhindert, dass veraltete Antwortbytes aus einem Puffer als neue Messung interpretiert werden.

### Binärmodus nach `GMS8`

Nach dem erfolgreichen Handshake wechselt OSTECH in einen Binärmodus. Dann erwartet die Bibliothek bzw. die Kommunikationsschicht:

- ASCII-Echo
- Payload-Bytes
- Checksumme am Ende

Die Antwort wird mit `struct.unpack()` in numerische Typen oder Statuswerte übersetzt. Wenn der Frame zu kurz ist oder die Prüfsumme nicht stimmt, wird ein Fehler ausgelöst.

Das ist ein typisches Design für Geräteprotokolle: Eine Antwort ist erst dann gültig, wenn sie nicht nur „sichtbar“, sondern auch strukturell und checksum-basiert korrekt ist.

### `decode_ostech_status(status_word)`

Für `GS` bzw. den Status-Befehl wird das Bitfeld in semantische Zustände umgewandelt. Ein `status_word` wird dann als Kombination von Flags interpretiert, z. B.:

```python
masks = {
    "interlock_ok": 0x0001,
    "driver_supply_ok": 0x0004,
    "driver_temperature_ok": 0x0008,
    "lt_sensor_ok": 0x0400,
    "ct_sensor_ok": 0x0800,
    "lc_on": 0x4000,
    "lc_error": 0x8000,
}
```

So kann die Anwendung mit verständlichen Zuständen arbeiten, statt rohe Bitmuster im Code herumzutragen.

---

## 7. State-Updates und Messwert-Logik

Nach dem erfolgreichen Lesen werden die Werte in `State.py` geschrieben. Das ist ein zentraler Teil der Architektur, weil die GUI nicht die Geräte direkt liest, sondern nur den State übernimmt.

Beispiele:

- `PHAS` und `FREQ` aus SR830
- `LCT` und `GS` aus OSTECH
- `OUTP1` bis `OUTP4` als Messwerte

Das designet eine klare Pipeline:

```text
Gerät -> serieller Buffer -> parse -> State -> GUI
```

Das ist wichtig, weil die GUI-Logik und die Hardware-Logik somit entkoppelt sind. Wenn ein Gerätfehler auftritt, bleibt der State konsistent und die GUI kann sauber reagieren.

---

## 8. SNAP- und Multiwert-Abfragen am SR830

Der SR830 unterstützt mehrere Mehrwertabfragen mit `SNAP?`. Typische Beispiele:

```python
SNAP? 1,2,3,4,10,11
SNAP? 5,6,7,8,9
```

Diese Abfragen liefern mehrere Werte in einer Antwort. Die Anwendung parst danach die Antwort und ordnet die Werte den einzelnen State-Feldern zu.

Beispiel aus dem Code:

```python
values = [float(value.strip()) for value in response.split(",")]
if len(values) != len(names):
    raise ValueError(f"Unerwartete SNAP-Antwort fuer {commands}: {response!r}")
```

Das ist ein wichtiges Sicherheitsmerkmal: Eine Antwort mit falscher Länge wird nicht stillschweigend akzeptiert, sondern als Fehler behandelt.

---

## 9. Threads und Geräte-Locks

Die Kommunikationsschicht nutzt separate Locks für die Geräte:

```python
SR830_LOCK = threading.Lock()
OSTECH_LOCK = threading.Lock()
```

Das ist strategisch richtig, weil die Geräte technisch unabhängig sind. Ein SR830-Timeout darf nicht automatisch das OSTECH-Protokoll blockieren.

Das Design ist damit:

- getrennte Gerätepfade
- getrennte Locks
- gemeinsame Zustandsobjekte
- zentrale Logging-Ablage

Dadurch ist die Anwendung robust gegenüber Parallelität und Gerät-Fehlern.

---

## 10. Warum `Send.py` und `Komunikation.py` getrennt sind

Das Projekt trennt bewusst zwei Ebenen:

1. `Send.py` definiert den Befehl und seine Bedeutung
2. `Komunikation.py` führt den realen Hardware-Transport aus

Dieser Aufbau ist wichtig, weil:

- GUI, Threads und Berechnungen sich auf die Befehlsemantik konzentrieren können
- serielle Protokolllogik nicht in der Oberfläche landet
- Geräte- und Format-Details isoliert werden
- die Anwendung wartbarer und testbarer bleibt

Kurz gesagt: `Send.py` erklärt, was ein Befehl bedeutet; `Komunikation.py` sagt, wie er abgearbeitet wird.

---

## 11. Fehlerbehandlung und Robustheit

Die Kommunikationsschicht prüft Fehler aktiv:

- falsche Echo-Antworten
- zu kurze Binärframes
- falsche Anzahl von Antwortwerten
- inkompatible Typumwandlungen
- fehlende oder geschlossene COM-Ports

Diese Prüfungen sind bewusst nicht nur „benutzerfreundlich“, sondern systemrelevant: Ein fehlerhaftes Protokoll darf nicht sauber wie ein gültiger Messwert weiterlaufen.

Das ist ein wesentliches Qualitätsmerkmal in Hardware-Interfaces.

---

## 12. Typischer Ablauf einer Messung

Ein realistischer Ablauf sieht so aus:

1. App startet
2. COM-Ports werden erkannt
3. SR830 und OSTECH werden geöffnet
4. Identifikationen werden abgefragt
5. OSTECH wird ggf. in Binärmodus gesetzt
6. Messwerte werden im Ablauf zyklisch gelesen
7. Antwortwerte werden geparst
8. State wird aktualisiert
9. Log wird geschrieben
10. GUI wird informiert

Das ist genau die Architektur, die das Projekt verfolgt: sauber trennbar, aber logisch zusammenhängend.

---

## 13. Fazit

Die Kommunikationsarchitektur dieses Projekts ist bewusst nach klaren Schichten aufgebaut:

- `Send.py` beschreibt die Befehlssprache
- `Komunikation.py` realisiert den seriellen Gerätezugriff
- `Threads.py` entkoppelt Hardware- und UI-Abläufe
- `State.py` hält den tatsächlichen Messzustand
- `Log.py` dokumentiert alles sauber und zentral

Das ist eine robuste Architektur für reale Gerätekommunikation. Sie ist gerade für Messgeräte und asynchrone I/O-Prozesse geeignet, weil sie auf klare Zuständigkeiten, Locks und semantische Trennung setzt.

Die wichtigsten Erkenntnisse für zukünftige Mitarbeiter sind:

- Read/Write-Befehle sind semantisch getrennt
- SR830-Statusbefehle wie `ERRS?` und `LIAS?` sind Lesebefehle
- die Hardware-Schicht ist streng von der GUI getrennt
- der State ist die verbindende Schicht zwischen Gerät und UI
- Log und Statusbildung sind keine Nebensache, sondern Kernbestandteil des Systems

Die OSTECH-Worker-Schritte sind in `_device_steps()` definiert:

### Periodische Messwerte

```python
ostech_periodic_steps = tuple(
    (command.name, lambda command=command: LabOSTECHCommand(OSTECH, command))
    for command in (
        OSTECHCommand.LCT,
        OSTECHCommand.XTA,
        OSTECHCommand.LVA,
        OSTECHCommand.XTCA,
        OSTECHCommand.XTVA,
        OSTECHCommand.LCA,
    )
)
```

Das bedeutet: Der OSTECH-Thread liest zyklisch die aktuellen Werte für:

- `LCT`
- `XTA`
- `LVA`
- `XTCA`
- `XTVA`
- `LCA`

### Start-/Startup-Schritte

Zusätzlich gibt es einmalige Startabfragen:

```python
ostech_startup_steps = tuple(
    (command.name, lambda command=command: LabOSTECHCommand(OSTECH, command))
    for command in (
        OSTECHCommand.XTT,
        OSTECHCommand.LTM,
        OSTECHCommand.GT,
        OSTECHCommand.GS,
        OSTECHCommand.GVN,
    )
)
```

Damit werden nach dem Verbindungsaufbau nicht nur laufende Messwerte, sondern auch Geräteinformationen und Zustände abgefragt.

---

## Threading-Modell und Ablauf

`Threads.py` definiert die Kern-Worker-Struktur. Das zentrale Koordinationsobjekt ist `CommunicationThreads`.

Im `start()` passieren die Reihenfolge und die Lebenszyklen:

```python
def start(self):
    self.logging.start()
    self.gui.start()
    if self.commands:
        self.commands.start()
    if self.calculations:
        self.calculations.start()
    self.sr830.start()
    self.ostech.start()
```

Das ist eine bewusste Reihenfolge: Zuerst werden die Konsumenten gestartet, dann Produzenten. Beim Stop wird genau umgekehrt vorgegangen. Dadurch gibt es keine „schlafenden“ Consumer-Zugriffe beim Beenden der Worker.

### `ThreadMessage`

Die Worker kommunizieren nicht direkt mit GUI und Log, sondern über ein immutables Objekt:

```python
@dataclass(frozen=True)
class ThreadMessage:
    source: str
    kind: str
    value: object
```

Damit bleiben Nachrichten konsistent und kein Verbraucher kann einen Eintrag an einer anderen Stelle ändern.

### `_publish()` in `CommunicationThreads`

`_publish()` normalisiert den Wert und verteilt ihn an beide Konsumenten:

```python
self.logging.publish(message)
self.gui.publish(message)
```

Das ist die Kernidee der Nachrichtenübertragung: Ein Geräte-Thread erzeugt eine Nachricht, und zwei Queue-Consumer verarbeiten sie unabhängig voneinander.

---

## `start_threaded_measurement()` – Koordination der Gesamtpipeline

`start_threaded_measurement()` baut die komplette Kommunikationspipeline. Dabei werden die beiden Device-Läufe durch `_run_device()` gestartet, jeweils mit den passenden Schritten:

```python
sr830_steps, ostech_periodic_steps, _ = _device_steps()
```

Und danach:

- SR830 Polling läuft in einem eigenen `DeviceThread`
- OSTECH Polling läuft in einem eigenen `DeviceThread`
- optionales `command_runner` läuft in einem `CommandThread`
- GUI- und Logging-Konsumenten laufen als `MessageThread`s

Wenn ein Polling-Schritt fehlschlägt, wird eine Fehlernachricht mit `step="error"` publiziert, aber nur dieser Worker stoppt. Der andere Gerätethread und die GUI können weiterlaufen.

---

## Logging- und GUI-Integration im Kommunikations-Thread

`log_handler(message: ThreadMessage)` in `start_threaded_measurement()` schreibt für jeden publizierten Wert einen strukturierten Eintrag:

```python
if message.kind == "error" or payload.get("step") == "error":
    Log.Log("Comm", payload.get("tag", message.source), "Error", ...)
    return
```

Für normale Statuswerte:

```python
Log.Log("Comm", tag, "Running", command, value, info)
```

Das heißt: Communication-Worker erzeugen keine CSV-Schreibungen direkt; sie veröffentlichen nur eine Nachricht, und das Log-Subsystem formatiert dann den Eintrag zentral.

---

## Beispiel eines kompletten Ablaufpfads

Typischer Ablauf bei einer SR830-Abfrage:

1. GUI oder Thread ruft `Send.SR830G.read(...)` auf
2. `Send.py` erzeugt `command_info`
3. `Komunikation.ask_SR830(...)` sendet das Kommando an das Gerät
4. Antwort wird per `read_until(b"\r")` geholt
5. `_convert_response(...)` wandelt sie in `float`/`int`/`str`
6. `State.update_values(...)` schreibt den Wert in den State
7. `ThreadMessage` wird publiziert
8. `Log.Log(...)` schreibt im Logger in CSV/Terminal/GUI

Damit ist das System klar getrennt: API, Wire-Protokoll, State, Logging und UI sind voneinander unabhängig, aber über feste Schnittstellen verbunden.

---

## Abschluss

Die Kommunikationsarchitektur ist in diesem Projekt bewusst als mehrschichtige Pipeline entworfen:

- `Send.py` definiert „was“ gesendet werden soll
- `Komunikation.py` realisiert „wie“ das Gerät über seriellen IO kontaktiert wird
- `Threads.py` verwaltet das asynchrone Laufzeitmodell
- `State.py` hält die aktuellen Messwerte
- `Log.py` dokumentiert Ereignisse zentral und konsistent

Diese Struktur ist robust, weil sie die realen Hardware- und Thread-Grenzen sauber abbildet. Sie vermeidet direkte GUI-Zugriffe aus Worker-Threads und garantiert, dass Messdaten und Fehlersituationen zentral protokolliert werden.
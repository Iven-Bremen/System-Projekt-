# Logging-Architektur

## Ziel des Loggings

Das Logging dokumentiert alle wichtigen Ereignisse des Programms dauerhaft
und nachvollziehbar. Es gibt drei parallele Ausgabewege:

1. Terminalausgabe für den direkten Entwickler- und Bedienerblick
2. CSV-Datei für spätere Auswertung und Messhistorie
3. optionale GUI-Callbacks für eine Live-Anzeige innerhalb der Anwendung

Die drei Wege werden zentral in `Log.py` zusammengeführt. Die übrigen Module
müssen keine CSV-Dateien öffnen und müssen die Spaltenstruktur nicht kennen.
Sie rufen ausschließlich `Log.Log()` auf.

---

## Grundprinzip

```text
Starter / GUI / Kommunikation
			  |
			  v
	   Log.Log()
			  |
	  +-------+--------+
	  |       |        |
	  v       v        v
 Terminal   GUI      CSV-Datei
```

Ein Ereignis wird möglichst nur einmal erzeugt und danach an mehrere Ziele
verteilt. So unterscheiden sich Terminal und CSV nicht inhaltlich.

Das Logging ist außerdem thread-sicher. SR830, OSTECH, CommandThread, GUI
und Terminalweiterleitung können gleichzeitig Meldungen erzeugen.

---

## CSV-Schema

Jede CSV-Datei erhält beim Erstellen diese Kopfzeile:

```text
Date,Time,Ms,Category,Tag,State,Message,Value,Info,AdditionalMessage,AdditionalValue,AdditionalInfo,Else
```

### Spaltenbedeutung

| Spalte | Bedeutung |
|---|---|
| `Date` | Datum des Ereignisses im Format `YYYY-MM-DD` |
| `Time` | Uhrzeit des Ereignisses im Format `HH:MM:SS` |
| `Ms` | Millisekundenanteil |
| `Category` | Bereich: `Sys`, `Comm`, `Gui`, `Calc`, `Log` |
| `Tag` | Quelle oder Gerät, etwa `SR830`, `OSTECH`, `Button` oder `GUI` |
| `State` | Zustand, etwa `Start`, `End`, `Info`, `Warning` oder `Error` |
| `Message` | Ereignis oder gesendeter/empfangener Befehl, nicht der Messwert |
| `Value` | Empfangener Wert, Messwert, Ergebnis oder `FAILED` |
| `Info` | Weiterführender Kontext, etwa Port oder Befehlsbeschreibung |
| `AdditionalMessage` | Weiterer beschreibender Text |
| `AdditionalValue` | Weiterer Mess- oder Konfigurationswert |
| `AdditionalInfo` | Zusatzinformationen wie Port oder Testname |
| `Else` | Freies Zusatzfeld |

Die Pflichtfelder befinden sich in den Spalten:

```python
REQUIRED_COLUMN_INDEXES = (3, 4, 5, 6)
```

Das entspricht:

- `Category`
- `Tag`
- `State`
- `Message`

Ohne diese vier Angaben wäre ein Logeintrag später nur schwer filterbar oder
nicht eindeutig zuzuordnen.

---

## Dateiname und Sitzungsordner

Die Dateien werden nach Tagesordnern abgelegt:

```text
logs/
  2026-09-17/
	07-34-31_Test_log.csv
```

Für Hardwaremessungen wird `State.Experiment` verwendet:

```python
filename = f"{time_str}_{State.Experiment}_log.csv"
```

Bei Simulation kann das Präfix `T` verwendet werden. Dann entsteht ein
Simulationsname:

```text
HH-MM-SS_simulation_log.csv
```

Der Pfad wird nur einmal pro Sitzung festgelegt. `_CURRENT_SESSION_LOG_PATH`
verhindert, dass spätere Logeinträge plötzlich eine zweite Datei anlegen.

---

## Erstellung einer Sitzung

`start_terminal_logging()` wird beim Programmstart aufgerufen.

Der Ablauf ist:

1. Logpfad bestimmen.
2. Tagesordner anlegen.
3. CSV-Datei und Kopfzeile sicherstellen.
4. optionalen Sessioneintrag schreiben.
5. `sys.stdout` durch `_Tee` ersetzen.
6. `sys.stderr` durch einen zweiten `_Tee` ersetzen.
7. optional `input()` protokollieren.

Der Sessioneintrag sieht logisch etwa so aus:

```text
Category = Sys
Tag      = SYSTEM
State    = Start
Message  = Session started
```

Damit ist in der CSV erkennbar, wann eine Programmsitzung begonnen hat.

---

## `Log()` - strukturierte API

Die bevorzugte neue Schnittstelle ist:

```python
Log.Log(
	Category="Comm",
	TAG="SR830",
	State="Info",
	Message="SNAP received",
	Value="1.25",
	Info="Measurement",
)
```

Die Parameter sind bewusst an die CSV-Struktur angelehnt. Dadurch ist klar,
welche Information in welcher Spalte landet.

Der Ablauf von `Log()`:

1. Zeitstempel erzeugen.
2. vollständige CSV-Zeile vorbereiten.
3. lesbare Fixed-Width-Zeile fürs Terminal erzeugen.
4. Terminal ausgeben.
5. `_get_active_log_path()` aufrufen.
6. Zeile über `_append_row()` schreiben.
7. registrierte GUI-Callbacks informieren.

Die CSV-Zeile ist die maschinenlesbare Hauptrepräsentation. Die Terminalzeile
ist für Menschen optimiert und kann abgeschnittene Spalten enthalten, ohne
dass die CSV-Daten verändert werden.

---

## Einheitliche Log-Konvention

Kommunikationsbefehle gehören in `Message`; empfangene Antworten und Messwerte
gehören in `Value`. Beispielsweise wird eine `LCL`-Antwort mit
`Message="LCL received"`, dem Antwortwert in `Value` und
`Info="Current limit"` protokolliert. Ein fehlgeschlagener Vorgang verwendet
`Value="FAILED"` und einen passenden Zustand wie `Error`.

Alle Aufrufer verwenden die vollständige Signatur von `Log()`; die frühere
`LogMassage()`-Kompatibilitätsschicht wurde entfernt.

---

## Thread-Sicherheit

Der zentrale Schutz ist:

```python
_LOG_LOCK = threading.RLock()
```

Der Lock schützt:

- Prüfung, ob die Datei existiert
- Schreiben der Kopfzeile
- Schreiben einer vollständigen CSV-Zeile
- Sessionmarker
- Terminal-/Fehlerausgaben in der CSV

Ein `RLock` statt eines einfachen `Lock` wird verwendet, weil geschützte
Schreibfunktionen intern wiederum `ensure_log_file()` aufrufen können.

### Warum der Lock notwendig ist

Ohne Lock könnte dieser Ablauf passieren:

```text
SR830Thread: öffnet Datei
OSTECHThread: öffnet Datei
SR830Thread: schreibt halbe Zeile
OSTECHThread: schreibt eigene Zeile
SR830Thread: schreibt Rest
```

Das Ergebnis wäre eine beschädigte CSV-Datei. Mit dem Lock wird jede komplette
Zeile als zusammenhängender Schreibvorgang behandelt.

Der Lock schützt nur den Dateizugriff. Er ersetzt keine Geräte-Locks und keine
GUI-Thread-Regel. Für Geräte sind die Locks in `Komunikation.py` zuständig;
für Tkinter bleibt der Hauptthread zuständig.

---

## `_Tee` für Terminal und Fehlerstrom

`start_terminal_logging()` ersetzt `sys.stdout` und `sys.stderr` nicht durch
stille Dateien, sondern durch `_Tee`-Objekte.

`_Tee.write()` macht drei Dinge:

1. Originaltext weiterhin ins echte Terminal schreiben.
2. sinnvolle Textzeilen als `OUTPUT`- oder `ERROR`-Zeilen in die CSV schreiben.
3. registrierte GUI-Callbacks informieren.

Leere Zeilen und reine Fortschrittszeichen werden verworfen. Dadurch wird die
CSV nicht mit unbrauchbaren Leerzeilen gefüllt.

Beispiel für eine Terminalausgabe:

```python
print("No COM ports available")
```

Diese Ausgabe bleibt sichtbar und wird zusätzlich als technische Ausgabe mit
`Tag = TERMINAL` gespeichert.

Fehlerausgaben aus `stderr` erhalten `Tag = ERROR`.

---

## Logging von `input()`

Wenn `capture_input=True` gesetzt ist, wird `builtins.input` durch eine
Wrapper-Funktion ersetzt. Der Wrapper:

1. ruft die ursprüngliche Eingabe auf,
2. wartet auf die Antwort des Benutzers,
3. schreibt Prompt und Antwort als `INPUT`-Ausgabe.

Die ursprüngliche Eingabefunktion bleibt erhalten und wird intern aufgerufen.
Das Logging verändert deshalb nicht die Semantik von `input()`.

---

## GUI-Callbacks

Mit `register_gui_callback()` kann eine Anzeige registriert werden:

```python
Log.register_gui_callback(callback)
```

Der Callback erhält bereits formatierten Text. `Log.py` kennt dabei keine
Tkinter-Widgets. Das ist beabsichtigt, weil der Logger auch ohne GUI laufen
muss.

Wichtig: Ein Callback darf nicht einfach aus einem beliebigen Worker-Thread
Tkinter-Widgets verändern. Für Tkinter muss der Callback die Nachricht in den
GUI-Hauptthread übertragen, zum Beispiel über `root.after()` oder eine eigene
Queue.

---

## Kommunikation und Logging zusammen

Eine Kommunikationsmeldung läuft normalerweise so:

```text
SR830-Abfrage
	|
	v
Antwort dekodieren
	|
	+--> State.OUTP1 aktualisieren
	|
	+--> ThreadMessage erzeugen
			  |
			  +--> LoggingThread
			  |       |
			  |       +--> Log.Log(...)
			  |               |
			  |               +--> Terminal
			  |               +--> CSV
			  |               +--> GUI-Callback
			  |
			  +--> GuiThread
```

Dadurch sind Messwertspeicherung und Anzeige logisch getrennt. Die GUI kann
den aktuellen Wert aus `State` lesen, während der Logger die konkrete
historische Antwort mit Zeitstempel in der CSV bewahrt.

---

## Fehlerlogging

Fehler werden nicht als normale Ergebnisse behandelt. Typische Zustände sind:

```text
Category = SYSTEM
State    = Error
```

oder bei Kommunikationstests:

```text
Category = KOM_Test
State    = E
```

Ein Gerätefehler enthält normalerweise:

- Quelle, zum Beispiel `SR830` oder `OSTECH`
- fehlenden oder fehlerhaften Schritt
- Exception-Typ
- konkrete Fehlermeldung

Beispiel:

```text
OSTECH | E | error | LCT: RuntimeError: Unerwartetes Echo
```

Ein fehlender COM-Port wird beim Start als `Warning` protokolliert, weil er
ein erwartbarer Betriebszustand sein kann. Ein unerwarteter Programmfehler
wird als `Error` protokolliert.

---

## Sessionende

Beim Schließen der GUI wird ein eigener Eintrag geschrieben:

```text
Category = SYSTEM
State    = Info
Message  = Foreground Shutdown
```

Vor dem Zerstören der Tkinter-Oberfläche werden geplante GUI- und
Simulations-Callbacks beendet. So entstehen keine nachträglichen Meldungen
wie `invalid command name ...refresh_shared_values`.

Anschließend schließt `Starter.py` die Geräteports im `finally`-Block.

---

## Logsuche und Zusammenführung

`Look_Up_CVS()` filtert die aktive CSV exakt nach:

- `Category`
- `Tag`
- `Message`
- optional `State`

Es werden nur ausgewählte Felder zurückgegeben, damit nachfolgende Auswertung
nicht von der kompletten Rohzeile abhängen muss.

`Merge_Look_Up_CVS()` führt zwei Suchergebnisse nach Datum, Uhrzeit und
Millisekunden zusammen. Jeder Datensatz erhält zusätzlich:

```python
Source = 1
```

oder:

```python
Source = 2
```

Die ursprünglichen Eingabelisten werden nicht verändert.

---

## Beispiel einer vollständigen Sitzung

Eine typische Hardware-Sitzung kann folgende Reihenfolge enthalten:

```text
SYSTEM  | START   | Programm gestartet
COM3    | Info    | OpenPort
COM4    | Warning | Port nicht verbunden
Gui     | Info    | Starting Gui
SR830   | T       | SNAP 1,2,3,4,10,11
SR830   | T       | SNAP 5,6,7,8,9
SR830   | T       | PHAS
SR830   | T       | FREQ
CALCULATION | T   | phase calculation
GUI     | CLICK   | Button clicked
GUI     | Error   | Input Error
SYSTEM  | Info    | Foreground Shutdown
```

Damit lässt sich später nachvollziehen:

- wann die Anwendung gestartet wurde,
- welche Geräte verfügbar waren,
- welche Messwerte empfangen wurden,
- welche Buttons geklickt wurden,
- ob Benutzereingaben ungültig waren,
- wann die Anwendung geschlossen wurde.

---

## Neue Logkategorien ergänzen

Neue Meldungen sollten möglichst diese Regeln einhalten:

1. `Category` beschreibt die fachliche Gruppe.
2. `Tag` beschreibt die Quelle.
3. `State` beschreibt das Ergebnis oder den Zustand.
4. `Message` beschreibt das Ereignis verständlich.
5. `Value` enthält den relevanten Wert.
6. technische Zusatzdaten kommen in `Info` oder weitere Zusatzfelder.

Beispiel:

```python
Log.Log(
	Category="MEASUREMENT",
	TAG="OSTECH",
	State="OK",
	Message="LCT received",
	Value=str(State.LCT),
	Info="mA",
)
```

Es sollte vermieden werden, direkt in CSV-Dateien zu schreiben. Direkte
Schreibvorgänge umgehen Header, Lock, Format und Callback-Verteilung.

---

## Zusammenfassung

Die Loggingarchitektur ist zentral, thread-sicher und auswertbar:

- Kommunikation erzeugt strukturierte Ereignisse.
- `Log.py` vereinheitlicht alle Ausgabewege.
- `_LOG_LOCK` verhindert beschädigte CSV-Zeilen.
- `_Tee` erfasst Terminal und Fehlerstrom.
- GUI-Callbacks ermöglichen Live-Anzeige ohne feste GUI-Abhängigkeit.
- Pflichtfelder sichern die spätere Suche.
- Session- und Shutdown-Einträge machen Programmläufe nachvollziehbar.
- Hardware- und Simulationsbetrieb können denselben Loggingweg verwenden.

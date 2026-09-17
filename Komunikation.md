# Kommunikationsarchitektur

## Zweck dieses Dokuments

Dieses Dokument beschreibt die Kommunikation zwischen der Anwendung und den
beiden Messgeräten:

- dem Lock-In-Verstärker **Stanford Research Systems SR830**
- dem Laser-/TEC-Controller **OSTECH**

Beschrieben werden nicht nur die einzelnen Funktionen in `Komunikation.py`,
sondern auch die Gründe für die Aufteilung in Zustände, Threads, Queues und
Protokollschichten. Die Kommunikation ist absichtlich von der GUI getrennt.
Die Geräte liefern Daten, `State.py` hält den neuesten bekannten Zustand, und
die GUI liest diesen Zustand im Tkinter-Hauptthread.

Das wichtigste Architekturprinzip lautet:

> Kommunikationscode darf Geräte abfragen und `State` aktualisieren, aber er
> darf niemals direkt Tkinter-Widgets verändern.

Dadurch bleiben Hardwareabfragen, Simulation und Anzeige austauschbar.

---

## Gesamtaufbau

```text
Starter.py
	|
	| initial scan; GUI Connect calls open_devices()
	v
Komunikation.py
	|
	| SR830Thread              OSTECHThread              CommandThread
	|       |                       |                         |
	|       +-----------+-----------+-------------------------+
	|                   |
	|                   | ThreadMessage
	|                   v
	|          CommunicationThreads
	|             |              |
	|             |              +--> LoggingThread --> Log.py --> CSV/Terminal
	|             |
	|             +-----------------> GuiThread --> GUI-Nachrichten
	|
	+--> State.py <----------------- dekodierte Messwerte
					^
					|
			  GUI.py liest State
			  im Tkinter-Hauptthread
```

Die Geräte-Threads laufen parallel. Innerhalb eines einzelnen Geräts bleiben
die Befehle jedoch sequenziell, weil eine serielle Schnittstelle eine
geordnete Befehlsfolge benötigt.

---

## Zuständigkeiten der Module

### `Komunikation.py`

Dieses Modul besitzt die Protokollkenntnis:

- COM-Port öffnen und schließen
- Befehle formatieren
- Antworten lesen
- ASCII-Antworten umwandeln
- OSTECH-Binärframes prüfen
- Checksumme berechnen
- `GS`-Statusbits dekodieren
- Messwerte nach `State.py` schreiben
- Polling-Aktionen für die Threads erzeugen

### `State.py`

Dieses Modul ist die gemeinsame Datenablage. Beispiele:

```python
State.OUTP1
State.OUTP4
State.LCT
State.XTA
State.GS
State.OSTECH_STATUS
```

Die GUI liest diese Werte. Kommunikations- und Simulationsteil schreiben sie.
Der State enthält immer den aktuellsten bekannten Wert, aber keine komplette
Historie. Die Historie wird vom Logger in der CSV-Datei geführt.

### `Threads.py`

Dieses Modul startet und stoppt die Worker. Es kennt keine konkreten
Gerätebefehle und keine Tkinter-Widgets. Dadurch bleibt es generisch.

### `Log.py`

Jede Kommunikationsmeldung kann in zwei unabhängigen Queues landen:

- in der Logging-Queue
- in der GUI-Queue

Die Logging-Queue schreibt die Meldung in die CSV. Die GUI-Queue kann die
Meldung anzeigen, ohne dass der Geräte-Thread auf Dateischreiben oder GUI-Code
warten muss.

---

## Geräteparameter

Die aktuellen Grundeinstellungen in `Komunikation.py` sind:

```python
SR830_PORT = "COM3"
OSTECH_PORT = "COM4"
BAUDRATE = 9600
TIMEOUT = 2
```

`SR830_LOCK` und `OSTECH_LOCK` sind getrennte Locks. Das ist wichtig, weil
SR830 und OSTECH unabhängig voneinander arbeiten können. Eine langsame
Antwort des OSTECH darf eine SR830-Abfrage nicht blockieren.

---

## Öffnen der Geräte

### `CheckCOM()`

`CheckCOM()` führt eine kurze, temporäre Prüfung durch:

1. COM-Port mit Baudrate und Timeout öffnen.
2. Befehl mit Wagenrücklauf senden.
3. Antwort bis `\r` lesen.
4. Optional ein Echo überspringen.
5. Prüfen, ob eine Antwort vorhanden ist.
6. Port immer im `finally`-Block schließen.

Die Funktion gibt bei Port-, Betriebssystem- oder Dekodierungsfehlern `False`
zurück. Ein nicht angeschlossenes Gerät ist beim Programmstart kein Absturz,
sondern ein erwartbarer Zustand.

### `open_devices()`

SR830 und OSTECH werden unabhängig geprüft. Das bedeutet:

- SR830 kann fehlen, während OSTECH geöffnet wird.
- OSTECH kann fehlen, während SR830 geöffnet wird.
- Ein fehlendes Gerät verhindert nicht automatisch den Start der GUI.

Beim SR830 wird nach der Prüfung die Gerätekennung über `*IDN?` gelesen.
Beim OSTECH wird zuerst die Textkommunikation verwendet, danach wird mit
`GMS8` in den Binärmodus gewechselt.

### `close_devices()`

Beim Programmende werden alle noch offenen Ports geschlossen. Die Funktion
prüft vorher, ob ein Port existiert und geöffnet ist. Sie darf deshalb auch
dann aufgerufen werden, wenn nur eines oder kein Gerät verfügbar war.

---

## SR830-Protokoll

Der SR830 verwendet eine zeilenorientierte ASCII-Kommunikation. Ein Befehl
wird mit `\r` abgeschlossen:

```text
FREQ?\r
PHAS?\r
SNAP? 1,2,3,4,10,11\r
```

### Lesen mit `ask_SR830()`

Der Ablauf lautet:

1. Prüfen, ob `SR830` geöffnet ist.
2. `SR830_LOCK` betreten.
3. Befehl formatieren.
4. ASCII-Bytes schreiben.
5. Stream flushen.
6. Bis `\r` lesen.
7. ASCII dekodieren.
8. Ergebnis mit `_convert_response()` umwandeln.
9. Lock verlassen.

Der Lock verhindert, dass zwei Threads gleichzeitig Bytes in denselben
seriellen Datenstrom schreiben oder Antworten vertauschen.

### SR830-Messwertmapping

Die SR830-Abfragen bleiben bewusst in zwei getrennten SNAP-Gruppen:

```text
SNAP? 1,2,3,4,10,11
```

| SR830-Kanal | Bedeutung | State-Variable |
|---:|---|---|
| 1 | X | `OUTP1` |
| 2 | Y | `OUTP2` |
| 3 | R | `OUTP3` |
| 4 | Theta | `OUTP4` |
| 10 | CH1 display | `CH1_DISPLAY` |
| 11 | CH2 display | `CH2_DISPLAY` |

Die zweite Gruppe lautet:

```text
SNAP? 5,6,7,8,9
```

| SR830-Kanal | Bedeutung | State-Variable |
|---:|---|---|
| 5 | Aux In 1 | `OAUX1` |
| 6 | Aux In 2 | `OAUX2` |
| 7 | Aux In 3 | `OAUX3` |
| 8 | Aux In 4 | `OAUX4` |
| 9 | Reference Frequency | `REFERENCE_FREQUENCY` |

Die Antwort wird in einzelne Werte zerlegt und mit `float()` umgewandelt.
Stimmt die Anzahl der Werte nicht mit der erwarteten Anzahl überein, wird ein
Fehler erzeugt. Es wird dann kein unvollständiges Mapping verwendet.

Zusätzliche Abfragen:

```text
PHAS? -> State.PHAS
FREQ? -> State.FREQ
```

---

## OSTECH-Protokoll

OSTECH verwendet zwei Phasen.

### Phase 1: Textmodus

Während des Starts werden Befehle als ASCII gesendet. Die Antwort besteht aus
Echo und Nutzantwort. Das Echo wird geprüft, damit keine alte Antwort aus dem
seriellen Puffer versehentlich als aktuelle Antwort interpretiert wird.

### Phase 2: Binärmodus

Nach erfolgreichem `GMS8`-Handshake werden Messwerte binär übertragen. Ein
Frame enthält:

```text
ASCII-Echo + Payload + Checksumme
```

Die erwartete Payload-Länge hängt vom Datentyp ab:

| Datentyp | Payload |
|---|---:|
| `float` | 4 Bytes |
| `int` | 2 Bytes |
| `bool` | 1 Byte |

Für numerische Werte wird Big-Endian verwendet. Die Checksumme wird aus dem
Startwert `0x55` und allen Payload-Bytes berechnet:

```python
checksum = (0x55 + sum(payload)) % 256
```

Ist das Echo falsch, die Antwort zu kurz oder die Checksumme ungültig, wird
eine Exception ausgelöst. Der Messwert wird dann nicht als gültiger Wert in
`State` übernommen.

---

## OSTECH-Befehle

`OSTECHCommandInfo` beschreibt pro Befehl:

- Wire-Befehl
- erwarteten Datentyp
- Einheit

Beispiel:

```python
LCT = OSTECHCommandInfo("LCT", float, "mA")
```

Die Enum-Gruppen sind:

### Periodische Messwerte

```text
LCT, XTA, LVA, XTCA, XTVA, LCA
```

### Startup-Werte und Status

```text
XTT, LTM, GT, GS, GVN
```

### Befehle nach Benutzeraktion

```text
LMDX, L
```

`LabOSTECHCommand()` führt den Befehl aus und schreibt normale Ergebnisse
unter dem Enum-Namen nach `State`:

```python
State.LCT
State.XTA
State.GVN
```

---

## Besonderheit `GS`

`GS` liefert ein Statuswort. Dieses Statuswort wird nicht als unlesbare Zahl
weitergereicht, sondern mit `decode_ostech_status()` in ein Dictionary
übersetzt:

```python
{
	"status_word": 0x4C0D,
	"interlock_ok": True,
	"driver_supply_ok": True,
	"driver_temperature_ok": True,
	"lt_sensor_ok": True,
	"ct_sensor_ok": True,
	"lc_on": True,
	"lc_error": False,
}
```

Die Werte werden sowohl in `State.GS` als auch in
`State.OSTECH_STATUS` gespeichert. Die doppelte Benennung macht den Zweck
klar: `GS` ist der Gerätebefehl, `OSTECH_STATUS` beschreibt die Bedeutung für
die Anzeige und Sicherheitslogik.

---

## Threadablauf

`start_threaded_measurement()` erstellt die Kommunikationsworker:

1. `SR830Thread`
2. `OSTECHThread`
3. `CommandThread`
4. `LoggingThread`
5. `GuiThread`

Die Verbraucher (`LoggingThread`, `GuiThread`) werden zuerst gestartet. Danach
werden die Produzenten gestartet. So kann bereits die erste Geräteantwort
verarbeitet werden, ohne dass eine Queue oder ein Handler fehlt.

### Gerätefehler

Wenn eine Geräteaktion fehlschlägt:

1. Die Exception wird im Geräte-Thread gefangen.
2. Ein Payload mit `step = "error"` wird erzeugt.
3. `CommunicationThreads` klassifiziert die Nachricht als Fehler.
4. Logging und GUI erhalten dieselbe Fehlernachricht.
5. Der betroffene Geräte-Loop endet.
6. Andere unabhängige Threads können weiterlaufen.

Das ist der Grund, warum ein fehlendes OSTECH nicht zwangsläufig den SR830-
Thread oder die GUI beendet.

### CalculationThread

Berechnungen werden nicht direkt in `State.py` als Thread implementiert.
`State.py` ist ausschließlich der gemeinsame Datencontainer. Der eigentliche
Worker lebt in `Threads.py`, wird aber von `Starter.py` erzeugt und gestartet:

```python
calculation_thread = CalculationThread(
	my_calculation_runner,
	publish_calculation_result,
)
calculation_thread.start()
```

Der Runner erhält:

```python
stop_requested, publish
```

Er darf aktuelle Werte aus `State` lesen, daraus beispielsweise Phase,
Frequenz, Mittelwerte oder Fit-Ergebnisse berechnen und anschließend melden:

```python
publish({
	"step": "phase calculation",
	"value": calculated_value,
})
```

Die Anwendung startet diesen Worker direkt in `Starter.py`. Sein aktueller
Callback schreibt die Statusmeldung mit der Quelle `CALCULATION` ins Logging;
eine spätere fachliche Berechnung kann zusätzlich über eine passende
Nachrichten-Queue an die GUI weitergegeben werden. Ein Berechnungsfehler
beendet nicht automatisch die Geräte-Threads, sondern wird als strukturierte
Fehlermeldung weitergegeben. Der Starter-Runner berechnet zunächst absichtlich
nichts. Er meldet nur `READY` beim Start und `STOPPED` beim Herunterfahren.
Die eigentlichen Formeln können später im Runner in `Starter.py` ergänzt
werden.

---

## State und GUI

Die Kommunikation schreibt nur nach `State.py`. Die GUI liest die Werte im
Tkinter-Hauptthread. Dadurch gibt es keine direkten Widget-Zugriffe aus einem
seriellen Worker.

Die Emergency-Simulation nutzt denselben Weg. Sie ersetzt nicht die
Kommunikationsfunktionen, sondern schreibt synthetische Werte in dieselben
State-Variablen. Dadurch ist der Anzeigeweg im Hardware- und Simulationsmodus
identisch.

---

## Typische Fehler und ihre Bedeutung

### Kein Gerät verbunden

```text
RuntimeError: SR830 ist nicht verbunden.
```

Das Gerät wurde nicht erfolgreich geöffnet. Das ist ein Verbindungszustand,
kein Protokollfehler.

### Falsches Echo

```text
Unerwartetes Echo
```

Die Antwort gehört wahrscheinlich nicht zum gesendeten Befehl, oder der
Controller befindet sich im falschen Protokollmodus.

### Leere OSTECH-Antwort

```text
Antwort ist zu kurz
```

Der Controller hat innerhalb des Timeouts nicht genügend Bytes geliefert.

### Ungültige Checksumme

Die Daten sind möglicherweise beschädigt. Der Wert wird nicht akzeptiert,
weil ein scheinbar plausibler Messwert gefährlicher wäre als ein sichtbarer
Kommunikationsfehler.

---

## Erweiterung neuer Befehle

Ein neuer OSTECH-Befehl sollte in dieser Reihenfolge ergänzt werden:

1. `OSTECHCommandInfo` definieren.
2. Eintrag in `OSTECHCommand` hinzufügen.
3. Zielvariable in `State.py` anlegen.
4. Falls periodisch: in `ostech_periodic_steps` ergänzen.
5. Falls Startup-Abfrage: in `ostech_startup_steps` ergänzen.
6. Falls Benutzeraktion: als Command-Workflow anbinden.
7. Anzeige oder Logging ergänzen.
8. Antwort mit Fake-Port oder Simulation testen.

Die Reihenfolge verhindert, dass ein Befehl zwar abgefragt, aber nicht
gespeichert oder angezeigt wird.

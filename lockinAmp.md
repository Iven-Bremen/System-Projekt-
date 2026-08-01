# SR830 Lock-In Amplifier – Aufbau, Nutzung und Troubleshooting

Diese Datei beschreibt, wie die SR830-Kommunikation in diesem Projekt aufgebaut ist, wie man sie initialisiert, welche Schritte für eine Verbindung nötig sind und welche Probleme auftreten können.

---

## 1. Ziel der Integration

Das Projekt stellt eine Python-basierte Schnittstelle für den Stanford Research SR830 Lock-In-Verstärker bereit.

Die Hauptziele sind:
- einfache Befehlsausführung über eine saubere API
- direkte Nutzung von Kurzbefehlen wie `PHAS(45)` oder `FREQ(589)`
- einfache Tests ohne echte Hardware über den Simulationsmodus
- Logging aller gesendeten Befehle und Antworten
- Integration in die vorhandene Kommunikationsschicht des Projekts

---

## 2. Wichtige Bausteine

### 2.1 `lockin_amplifier.py`

Hier liegt die eigentliche SR830-API.

Sie enthält:
- die Klasse `LAM`
- Methoden zum Senden von Befehlen
- Kurzformen für die SR830-Befehle
- Validierung der erlaubten Werte
- optionales CSV-Logging

Beispiel:

```python
from lockin_amplifier import LAM

lam = LAM(port="COM4", simulate=True, log_path="logs/test_sr830.csv")
lam.connect()
lam.PHAS(45)
lam.FREQ(589)
print(lam.PHAS())
lam.disconnect()
```

### 2.2 `Komunikation.py`

Dieses Modul stellt die Projekt-Integration bereit.

Dort wird die SR830-Schnittstelle über die Klasse `SR830Driver` eingebunden und mit einer einfachen Initialisierungsfunktion verfügbar gemacht:

```python
from Komunikation import initialize_lockin

lam = initialize_lockin(port="COM4", simulate=True)
lam.PHAS(45)
lam.close()
```

### 2.3 `Log.py`

Das Logging-System schreibt Kommunikationsdaten in CSV-Dateien. Dadurch bleiben sowohl Befehle als auch Antworten nachvollziehbar.

---

## 3. So funktioniert die Verbindung

### 3.1 Voraussetzungen

Damit der Lock-In wirklich angeschlossen werden kann, braucht es:
- einen funktionierenden seriellen Port
- die richtige Baudrate
- die korrekte Verbindung zum SR830
- die Installation von `pyserial`

Die Standard-Baudrate ist im Projekt auf `19200` eingestellt.

### 3.2 Initialisierung

Die Initialisierung erfolgt in mehreren Schritten:

1. Objekt erzeugen
2. Verbindung öffnen
3. Befehle senden
4. Antworten auswerten
5. Verbindung schließen

Beispiel:

```python
from Komunikation import initialize_lockin

lam = initialize_lockin(port="COM4", baudrate=19200, simulate=False)

if lam is not None:
    lam.PHAS(45)
    lam.FREQ(1000)
    print(lam.PHAS())
    lam.close()
```

### 3.3 Simulationsmodus

Für Tests und Entwicklung kann der SR830 auch ohne echte Hardware betrieben werden:

```python
from Komunikation import initialize_lockin

lam = initialize_lockin(port="COM1", simulate=True)
lam.PHAS(45)
print(lam.PHAS())
lam.close()
```

Der Simulationsmodus ist besonders sinnvoll, wenn:
- kein Gerät verfügbar ist
- Tests automatisiert laufen sollen
- die Software entwickelt wird, bevor das Gerät angeschlossen ist

---

## 4. Befehlssyntax und API

Die API arbeitet mit kurzen, gut lesbaren Aufrufen.

### 4.1 Einzelbefehle

Beispiele:

```python
lam.PHAS(45)
lam.FREQ(589)
lam.SENS(12)
lam.OFLT(10)
```

### 4.2 Abfragen

Wenn kein Wert übergeben wird, wird der aktuelle Wert abgefragt:

```python
print(lam.PHAS())
print(lam.FREQ())
```

### 4.3 Komplexe Konfiguration

Es gibt auch zusammengesetzte Methoden:

```python
lam.init(phase=45.0, frequency=589.0)
lam.configure_reference(reference_source=1, frequency=1000.0, phase=45.0)
lam.configure_filter(sensitivity=12, time_constant=10)
```

---

## 5. Eingabebeschränkungen

Die API ist bewusst auf die zulässigen Werte des SR830 angepasst.

Das bedeutet:
- ungültige Werte werden direkt abgewiesen
- der Nutzer erhält eine Fehlermeldung, statt einen ungültigen Befehl zu senden
- nur Werte aus dem zulässigen Bereich werden akzeptiert

Beispiele:
- `PHAS` muss in einem sinnvollen Phasenbereich liegen
- `FREQ` muss im zulässigen Frequenzbereich liegen
- `FMOD` darf nur `0` oder `1` sein
- `SENS` und `OFLT` sind auf die Gerätedefinitionen begrenzt
- nur unterstützte Baudraten sind erlaubt

Dadurch wird verhindert, dass der Lock-In mit unzulässigen Kommandos überlastet oder falsch programmiert wird.

---

## 6. Logging

Jeder Kommunikationsschritt wird protokolliert.

### 6.1 Was wird geloggt?

Für jeden Befehl und jede Antwort werden gespeichert:
- Zeitstempel
- Richtung (`TX` oder `RX`)
- gesendeter Befehl
- Antwort oder Rückgabewert
- Latenz in Millisekunden

### 6.2 Speicherort

Das Logging kann in eine CSV-Datei geschrieben werden:

```python
lam = LAM(port="COM4", simulate=False, log_path="logs/sr830_session.csv")
```

Dadurch lassen sich spätere Fehlersituationen oder Kommunikationsprobleme sauber nachvollziehen.

---

## 7. Mögliche Probleme und Fehlersituationen

### 7.1 Falscher Port

Wenn der angegebene Port nicht existiert oder falsch ist, kann keine Verbindung aufgebaut werden.

Typische Symptome:
- Verbindung schlägt fehl
- `pyserial` meldet einen Fehler
- kein Befehl wird verarbeitet

Lösung:
- den richtigen Port prüfen
- ggf. die Portliste im Projekt verwenden
- den Port im Programm korrekt übergeben

### 7.2 Falsche Baudrate

Der SR830 arbeitet nur mit unterstützten Baudraten.

Falls eine falsche Baudrate verwendet wird, kann die Kommunikation nicht korrekt stattfinden.

Lösung:
- nur unterstützte Werte verwenden
- Standardwert ist `19200`

### 7.3 Gerät nicht angeschlossen

Wenn kein Lock-In vorhanden ist oder die Verbindung nicht hergestellt werden kann, treten Fehler auf.

Lösung:
- Hardware prüfen
- Kabel kontrollieren
- Gerät einschalten
- Port und Baudrate prüfen

### 7.4 Ungültige Befehle

Wenn ein Wert außerhalb des erlaubten Bereichs gesendet wird, wird ein Fehler erzeugt.

Lösung:
- nur erlaubte Werte verwenden
- beim Programmieren auf die Validierung achten

### 7.5 Timing-Probleme

Bei serieller Kommunikation kann es durch kurze Verzögerungen zu Problemen kommen.

Lösung:
- kurze Pausen zwischen Befehlen einhalten, falls nötig
- auf korrekte Antwortwerte achten
- Logs prüfen

---

## 8. Praktischer Ablauf für den Einstieg

Ein typischer Ablauf sieht so aus:

1. Verbindung öffnen
2. Geräteparameter einstellen
3. Referenz konfigurieren
4. Eingang und Filter konfigurieren
5. Messwerte abfragen
6. Verbindung schließen

Beispiel:

```python
from Komunikation import initialize_lockin

lam = initialize_lockin(port="COM4", baudrate=19200, simulate=False)

lam.configure_reference(reference_source=1, frequency=1000.0, phase=45.0)
lam.configure_input(input_source=0, grounding=0, coupling=0, notch=0)
lam.configure_filter(sensitivity=12, reserve_mode=1, time_constant=10)

print(lam.PHAS())
print(lam.FREQ())
print(lam.snapshot_xy())

lam.close()
```

---

## 9. Empfehlung für die Nutzung im Projekt

Für die weitere Entwicklung ist es sinnvoll:
- die Kommunikation immer über `initialize_lockin()` zu starten
- Tests zuerst im Simulationsmodus durchzuführen
- das Logging aktiv zu lassen
- neue Befehle erst nach Validierung einzubauen
- Fehlerfälle sauber zu behandeln

Damit bleibt die Verbindung stabil, sauber dokumentiert und einfacher erweiterbar.

---

## 10. Kurzfazit

Die SR830-Schnittstelle ist jetzt so aufgebaut, dass sie:
- zuverlässig initialisiert werden kann
- direkt über kurze Befehle angesprochen werden kann
- im Testmodus ohne Hardware funktioniert
- Werte prüft und nur zulässige Eingaben akzeptiert
- alle Befehle und Antworten in Logs festhält

Damit ist sie gut geeignet, um mit dem Lock-In-Verstärker im Projekt zu arbeiten und später weiter auszubauen.

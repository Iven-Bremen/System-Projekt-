# OsTech LaserDriver – Aufbau, Nutzung und Troubleshooting

Diese Datei beschreibt, wie die Laser-Kommunikation in diesem Projekt aufgebaut ist, wie man sie initialisiert, welche Schritte für eine Verbindung nötig sind und welche Probleme auftreten können.

---

## 1. Ziel der Integration

Das Projekt stellt eine Python-basierte Schnittstelle für den OsTech-Laser bereit.

Die Hauptziele sind:
- einfache Befehlsausführung über eine saubere API
- direkte Nutzung kurzer Befehle wie `GS()`, `GT()` oder `GMS(True)`
- einfache Tests ohne echte Hardware über den Simulationsmodus
- Logging aller gesendeten Befehle und Antworten
- Integration in die vorhandene Kommunikationsschicht des Projekts

---

## 2. Wichtige Bausteine

### 2.1 `LaserDriver.py`

Hier liegt die eigentliche Laser-API.

Sie enthält:
- die Klasse `LaserDriver`
- Methoden zum Senden von Befehlen
- Kurzformen für typische Laserbefehle
- Validierung der erlaubten Werte
- optionales CSV-Logging

Beispiel:

```python
from LaserDriver import LaserDriver

laser = LaserDriver(port="COM3", simulate=True, log_path="logs/test_laser.csv")
laser.connect()
laser.GMS(True)
print(laser.GS())
laser.close()
```

### 2.2 `Komunikation.py`

Dieses Modul stellt die Projekt-Integration bereit.

Dort wird die Laser-Schnittstelle über die vorhandene Kommunikationsschicht eingebunden und mit einer einfachen Nutzung verfügbar gemacht.

### 2.3 `Log.py`

Das Logging-System schreibt Kommunikationsdaten in CSV-Dateien. Dadurch bleiben sowohl Befehle als auch Antworten nachvollziehbar.

---

## 3. So funktioniert die Verbindung

### 3.1 Voraussetzungen

Damit der Laser wirklich angeschlossen werden kann, braucht es:
- einen funktionierenden seriellen Port
- die richtige Baudrate
- die korrekte Verbindung zum OsTech-Laser
- die Installation von `pyserial`

Die Standard-Baudrate ist im Projekt auf `9600` eingestellt.

### 3.2 Initialisierung

Die Initialisierung erfolgt in mehreren Schritten:

1. Objekt erzeugen
2. Verbindung öffnen
3. Befehle senden
4. Antworten auswerten
5. Verbindung schließen

Beispiel:

```python
from LaserDriver import LaserDriver

laser = LaserDriver(port="COM3", baudrate=9600, simulate=False)

if laser.connect():
    print(laser.GS())
    print(laser.GT())
    laser.GMS(True)
    laser.close()
```

### 3.3 Simulationsmodus

Für Tests und Entwicklung kann der Laser auch ohne echte Hardware betrieben werden:

```python
from LaserDriver import LaserDriver

laser = LaserDriver(port="COM1", simulate=True)
laser.connect()
print(laser.GS())
laser.close()
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
laser.GMS(True)
laser.GMS(False)
laser.GS()
laser.GT()
```

### 4.2 Abfragen

Wenn kein Wert übergeben wird, wird der aktuelle Wert oder die aktuelle Darstellung des Befehls erzeugt:

```python
print(laser.GS())
print(laser.GT())
```

### 4.3 Direkte Schreibbefehle

Auch direkte Schreibbefehle sind möglich:

```python
laser.write("LCT", 500)
laser.write("LVC", 3.0)
```

---

## 5. Eingabebeschränkungen

Die API ist bewusst auf die zulässigen Werte des OsTech-Lasers angepasst.

Das bedeutet:
- ungültige Werte werden direkt abgewiesen
- der Nutzer erhält eine Fehlermeldung, statt einen ungültigen Befehl zu senden
- nur Werte aus dem zulässigen Bereich werden akzeptiert

Beispiele:
- `GMS` akzeptiert nur Bool-Werte oder Hex-Strings wie `0x1234`
- `LCT` und `LCB` sind auf den zulässigen Strombereich begrenzt
- `LVC` ist nur im zulässigen Spannungsbereich erlaubt
- `LMDIC` ist auf einen Wortbereich begrenzt
- `LZTR` ist auf einen definierten Rampenzeitbereich begrenzt
- `xTLU`, `xTLL`, `xTT` sind auf Temperaturgrenzen begrenzt

Dadurch wird verhindert, dass der Laser mit unzulässigen Kommandos überlastet oder falsch programmiert wird.

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
laser = LaserDriver(port="COM3", simulate=False, log_path="logs/laser_session.csv")
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

Der Laser arbeitet nur mit unterstützten Baudraten.

Falls eine falsche Baudrate verwendet wird, kann die Kommunikation nicht korrekt stattfinden.

Lösung:
- nur unterstützte Werte verwenden
- Standardwert ist `9600`

### 7.3 Gerät nicht angeschlossen

Wenn kein Laser vorhanden ist oder die Verbindung nicht hergestellt werden kann, treten Fehler auf.

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
2. Status abfragen
3. Temperatur abfragen
4. Laser einschalten
5. Werte kontrollieren
6. Verbindung schließen

Beispiel:

```python
from LaserDriver import LaserDriver

laser = LaserDriver(port="COM3", baudrate=9600, simulate=False)

if laser.connect():
    print(laser.GS())
    print(laser.GT())
    laser.GMS(True)
    print(laser.GS())
    laser.close()
```

---

## 9. Empfehlung für die Nutzung im Projekt

Für die weitere Entwicklung ist es sinnvoll:
- die Kommunikation immer über die Laser-Klasse zu starten
- Tests zuerst im Simulationsmodus durchzuführen
- das Logging aktiv zu lassen
- neue Befehle erst nach Validierung einzubauen
- Fehlerfälle sauber zu behandeln

Damit bleibt die Verbindung stabil, sauber dokumentiert und einfacher erweiterbar.

---

## 10. Wie man den Laser testet

Es gibt zwei einfache Wege, die Funktion der Laser-Klasse zu prüfen.

### 10.1 Test ohne echte Hardware

Der einfachste Test ist der Simulationsmodus:

```python
from LaserDriver import LaserDriver

laser = LaserDriver(port="COM1", simulate=True, log_path="logs/test_laser.csv")
laser.connect()

print(laser.GS())
print(laser.GT())
laser.GMS(True)
laser.GMS(False)

laser.close()
```

Erwartetes Verhalten:
- die Verbindung wird aufgebaut
- `GS()` und `GT()` liefern simulierte Werte
- `GMS(True)` und `GMS(False)` funktionieren ohne echte Hardware

### 10.2 Test mit pytest

Im Projekt gibt es bereits einen Testlauf für die Kommunikation. Du kannst direkt so testen:

```powershell
pytest -q
```

Wenn du nur den Laser-Test prüfen willst:

```powershell
pytest -q tests/test_laser_driver.py
```

### 10.3 Prüfung von Fehlermeldungen

Du kannst auch testen, ob ungültige Werte sauber abgewiesen werden:

```python
from LaserDriver import LaserDriver

laser = LaserDriver(port="COM1", simulate=True)
laser.connect()

try:
    laser.write("LCT", 2000)
except ValueError as exc:
    print(exc)
```

Das sollte eine verständliche Fehlermeldung liefern, wenn der Wert außerhalb der erlaubten Grenzen liegt.

### 10.4 Prüfung des Loggings

Wenn du `log_path` setzt, kannst du prüfen, ob die Kommunikation korrekt protokolliert wird:

```python
laser = LaserDriver(port="COM1", simulate=True, log_path="logs/laser_test.csv")
laser.connect()
laser.GS()
laser.close()
```

Danach kannst du die Datei `logs/laser_test.csv` öffnen und sehen, ob Befehle und Antworten dort gespeichert wurden.

---

## 11. Kurzfazit

Die Laser-Schnittstelle ist jetzt so aufgebaut, dass sie:
- zuverlässig initialisiert werden kann
- direkt über kurze Befehle angesprochen werden kann
- im Testmodus ohne Hardware funktioniert
- Werte prüft und nur zulässige Eingaben akzeptiert
- alle Befehle und Antworten in Logs festhält

Damit ist sie gut geeignet, um mit dem OsTech-Laser im Projekt zu arbeiten und später weiter auszubauen.

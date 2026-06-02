# PLIS - Kurz-Anleitung

Dies ist das Steuerprogramm für dein RS232-Kommunikationssystem.
Es unterstützt einen aktiven Hardware-Modus und einen Simulationsmodus, bei dem die Testdaten
aus der Datei `20190701_181338_MP1_QC19C.txt` verwendet werden.

## Was macht das Projekt?
- `main.py` startet den aktiven Modus mit realer Hardware.
- `mainTest.py` startet den Testmodus und nutzt die Messdaten aus der Textdatei.
- Das Programm schreibt seine Ergebnisse in CSV-Dateien im Ordner `logs/`.

## Installation
1) Installiere die Grundabhängigkeiten:
```bash
python -m pip install -r requirements.txt
```

2) Wenn du Hardware verwenden willst, installiere `pyserial`:
```bash
python -m pip install pyserial
```

## Starten
- Simulationsmodus (automatisch):
```bash
python mainTest.py
```

- Simulationsmodus (interaktiv):
```bash
python mainTest.py --interactive
```

- Hardware-Modus:
```bash
python main.py
```

- Liste der verfügbaren Ports anzeigen:
```bash
python main.py --list
```

- Ports direkt angeben:
```bash
python main.py --laser-port COM3 --lockin-port COM4
```

## Logs und Daten
- Die Testdaten-Datei ist `20190701_181338_MP1_QC19C.txt`.
- Alle Logdateien landen im Ordner `logs/`.
- Pro Tag wird ein Unterordner erstellt, z.B. `logs/2026-06-02/`.
- In jeder Sitzung wird eine CSV-Datei angelegt.

## Hinweise
- Im Simulationsmodus braucht das Programm keine echte serielle Verbindung.
- Wenn du den Hardware-Modus verwendest, musst du sicherstellen, dass `pyserial` installiert ist.
- Falls du mehr menschliche Kommentare oder eine ausführlichere Entwickler-Dokumentation möchtest,
  kann ich dir gern noch eine `DEVELOPMENT.md` oder ausführliche Erläuterungen schreiben.

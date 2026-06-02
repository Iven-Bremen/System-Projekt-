PLIS - Startanleitung

Kurz:
- `main.py` enthält zwei Entrypoints:
  - `main()` — aktiver Modus: spricht reale Geräte über COM/USB an (nutzt `pyserial` wenn verfügbar).
  - `mainTest()` — Simulations-/Testmodus: nutzt die Datei `20190701_181338_MP1_QC19C.txt` als Datenquelle.

Schnellstart:
1) Abhängigkeiten installieren
```bash
python -m pip install -r requirements.txt
```

Wenn du den Hardware-Modus nutzen möchtest, installiere zusätzlich `pyserial`:
```bash
python -m pip install pyserial
```

2) Simulations-Test (automatisch)
```bash
python mainTest.py
```

3) Simulations-Test (interaktiv)
```bash
python mainTest.py --interactive
```

4) Aktiver Hardware-Modus (echte COM-Ports)
```bash
python main.py
```

5) Hardware-Portliste anzeigen
```bash
python main.py --list
```

6) Hardware-Ports direkt angeben
```bash
python main.py --laser-port COM3 --lockin-port COM4
# oder unter Linux:
python main.py --laser-port /dev/serial/by-id/usb-... --lockin-port /dev/serial/by-id/usb-...
```

Dateien & Logs:
- Simulationsdaten: `20190701_181338_MP1_QC19C.txt` (im Projektordner)
- Test-Log: `plis_comm_test_log.csv`
- Mess-Log: `plis_measurement_log.csv`

Logs-Ordnerstruktur (neu):
- Alle Logdateien werden unterhalb des Projekts im Ordner `logs/` abgelegt.
- Pro Tag wird ein Unterordner im Format `DD-MM-YYYY` erstellt, z.B. `logs/31-05-2026/`.
- Jede Programmausführung erzeugt eine neue CSV-Datei im Tagesordner mit Zeit-Stempel:
  - `M_HH-MM-SS.csv` für `main()` (Hardware-Lauf)
  - `T_HH-MM-SS.csv` für `mainTest()` (Simulationslauf)
- Beispiel: `logs/31-05-2026/M_14-30-05.csv`

Terminal-Logging (neu):
- Es wird KEINE separate Terminal-Logdatei mehr erstellt. Stattdessen werden alle Terminalausgaben und Benutzereingaben in der Tages-CSV erfasst.
- Terminal-relevante Zeilen werden als `Device=TERMINAL` in der CSV geschrieben (Spalte `Command` enthält `OUTPUT` oder `INPUT`).

Beispiel-Verzeichnis nach einem Lauf:

```
logs/
└─ 31-05-2026/
  ├─ M_31-05-2026.csv
  └─ T_31-05-2026.csv
```

Hinweis zur Dokumentation & Kommentaren:
- Der Code enthält jetzt zusätzliche Docstrings und Kommentare für die neuen Funktionen `ensure_dependencies()`, `make_log_path()` und `start_terminal_logging()`.
- Wenn du mehr Inline-Kommentare oder ein Entwickler-Handbuch im Repository möchtest, sage mir welches Format du bevorzugst (Markdown, reStructuredText) und ich erstelle es.

Hinweis:
- Passe in `main.py` die Default-Ports `COM3`/`COM4` an deine Systemkonfiguration an.
- Für reale Hardware sicherstellen, dass `pyserial` installiert ist und die Benutzerrechte den Zugriff auf COM-Ports erlauben.
 - Hinweis: Das Programm versucht fehlende Abhängigkeiten beim Start automatisch zu installieren (z.B. `pyserial`).
 - Alle Logdateien werden ausschließlich in den `logs/`-Tagesordnern abgelegt.

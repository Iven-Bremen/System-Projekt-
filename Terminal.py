"""
Dieses Modul enthält alle Ausgaben für die Konsole: Header, Statustexte und
Benutzerhinweise für den interaktiven Modus.
"""

import time

from Komunikation import scan_ports_with_spinner, print_available_ports

LINE = "=" * 80


def parse_interactive_command(raw_command: str):
    """Parst interaktive Eingaben und unterstützt kurze Abkürzungen."""
    command = (raw_command or "").strip().lower()
    if not command:
        return "noop", None
    if command in {"/help", "help", "?"}:
        return "help", None
    if command in {"s", "scan"}:
        return "scan", None
    if command in {"t", "test"}:
        return "test", None
    if command in {"q", "quit", "exit"}:
        return "quit", None
    if command in {"connect", "conn"}:
        return "connect", None
    if command in {"disconnect", "disc", "close"}:
        return "disconnect", None

    tokens = command.split()
    if tokens and tokens[0] == "laser":
        if len(tokens) >= 2 and tokens[1] in {"gs", "status"}:
            return "device", {"device": "laser", "action": "gs"}
        if len(tokens) >= 2 and tokens[1] in {"gt", "temp", "temperature"}:
            return "device", {"device": "laser", "action": "gt"}
        if len(tokens) >= 2 and tokens[1] in {"on", "start", "enable"}:
            return "device", {"device": "laser", "action": "on"}
        if len(tokens) >= 2 and tokens[1] in {"off", "stop", "disable"}:
            return "device", {"device": "laser", "action": "off"}

    if tokens and tokens[0] == "lockin":
        if len(tokens) >= 2 and tokens[1] in {"phas", "phase"}:
            return "device", {"device": "lockin", "action": "phas"}
        if len(tokens) >= 2 and tokens[1] in {"freq", "frequency"}:
            return "device", {"device": "lockin", "action": "freq"}
        if len(tokens) >= 2 and tokens[1] in {"snap", "xy"}:
            return "device", {"device": "lockin", "action": "snap"}

    if command in {"gs", "gt", "phas", "freq", "snap"}:
        if command == "gs":
            return "device", {"device": "laser", "action": "gs"}
        if command == "gt":
            return "device", {"device": "laser", "action": "gt"}
        if command in {"phas", "phase"}:
            return "device", {"device": "lockin", "action": "phas"}
        if command in {"freq", "frequency"}:
            return "device", {"device": "lockin", "action": "freq"}
        if command in {"snap", "xy"}:
            return "device", {"device": "lockin", "action": "snap"}

    return "unknown", command


def header(title: str):
    print("\n" + LINE)
    print(title)
    print(LINE)


def mode_status(use_simulation: bool):
    if use_simulation:
        print("⚠️  WARNUNG: pyserial ist nicht installiert.")
        print("   Starte stattdessen den Simulationsmodus.")
        print("   Installiere pyserial mit: pip install pyserial")
    else:
        print("✓ pyserial ist verfügbar - Hardware-Modus aktiv")


def port_search_header():
    header("SUCHE NACH VERFÜGBAREN SERIELLEN PORTS...")


def no_ports_found():
    print("\n⏳ Es wurden keine Ports gefunden. Prüfe weiter, während du den Adapter anschließt...")


def prompt_for_port(prompt_text: str):
    while True:
        port = input(prompt_text).strip()
        if not port:
            print("  ⚠️  Bitte einen gültigen Port eingeben oder Gerät anschließen...")
            continue
        if port.lower() == "scan":
            ports = scan_ports_with_spinner(timeout=5)
            print_available_ports(ports)
            continue
        return port


def startup_info(port_laser: str, port_lockin: str, csv_path: str, laser_interval: float, lockin_interval: float):
    header("STARTE AKTIVE RS232/USB-KOMMUNIKATION")
    print(f"🔴 OsTech Laser-Treiber:        {port_laser}")
    print(f"   └─ Baudrate: 9600, Protokoll: 8N1")
    print(f"   └─ Befehle: GT (Temp), GS (Status), GMS (Laser ON/OFF)")
    print(f"\n🔵 SR830 Lock-In-Verstärker:    {port_lockin}")
    print(f"   └─ Baudrate: 19200, Protokoll: 8N1")
    print(f"   └─ Befehle: SNAP? (X/Y-Daten), PHAS? (Phase), FREQ? (Frequenz)")
    print(f"\n📊 Datenspeicherung: {csv_path} (Spalten: Zeitstempel; Gerät; Befehl; Rohantwort; Dekodiert; Latenz)")
    print(LINE)


def interactive_menu(laser_interval: float, lockin_interval: float):
    print("\n⌨️  Interaktive Befehle:")
    print("   • 'scan' / 's'  - Verfügbare Ports neu scannen")
    print("   • 'test' / 't'  - Alle bekannten Befehle an Geräte senden")
    print("   • 'connect'     - Verbindung zu Laser und Lock-In öffnen")
    print("   • 'disconnect'  - Verbindung sauber schließen")
    print("   • 'laser gs'    - Laser-Status abfragen")
    print("   • 'laser gt'    - Laser-Temperatur abfragen")
    print("   • 'laser on'    - Laser einschalten")
    print("   • 'laser off'   - Laser ausschalten")
    print("   • 'lockin phas' - Lock-In-Phase abfragen")
    print("   • 'lockin freq' - Lock-In-Frequenz abfragen")
    print("   • 'lockin snap' - Lock-In-X/Y-Werte abfragen")
    print("   • 'help' / '/help' / '?'  - Diese Hilfe anzeigen")
    print("   • 'quit' / 'q'  - Programm beenden")
    print(f"\n⏱️  Autom. Abfragen (jede {laser_interval:.1f}s Laser, jede {lockin_interval:.1f}s LockIn)")
    print(LINE + "\n")


def show_help():
    header("HILFE - VERFÜGBARE BEFEHLE")
    print("Allgemein:")
    print("  /help, help, ?      - Zeigt diese Hilfe an")
    print("  scan, s             - Ports neu scannen")
    print("  test, t             - bekannte Befehle an die Geräte senden")
    print("  connect             - Verbindung zu Laser und Lock-In öffnen")
    print("  disconnect          - Verbindung sauber schließen")
    print("  quit, q, exit       - Programm beenden")
    print("")
    print("Gerätebefehle im interaktiven Modus:")
    print("  laser gs            - Status des Lasers abfragen")
    print("  laser gt            - Temperatur abfragen")
    print("  laser on            - Laser einschalten")
    print("  laser off           - Laser ausschalten")
    print("  lockin phas         - Phase abfragen")
    print("  lockin freq         - Frequenz abfragen")
    print("  lockin snap         - X/Y-Werte abfragen")
    print("  gs, gt, phas, freq, snap - Kurzformen für die gleichen Befehle")
    print("")
    print("Hinweis: Die Verbindung wird beim Start aufgebaut; danach können die Gerätebefehle direkt verwendet werden.")
    print(LINE)


def waiting_for_responses(seconds: int):
    print(f"\n⏳ Warte auf Antworten ({seconds} Sekunden)...\n")


def interactive_header():
    header("INTERAKTIVER MODUS - EINGABE ERWARTET")


def unknown_command(command=None):
    print("  ❌ Unbekannter Befehl.")
    if command:
        print(f"     Eingabe: {command}")
    print("     Nutze: scan, test, help oder quit")


def scan_started():
    print("\n🔍 Scanne Ports...\n")


def test_started():
    print()


def exit_message():
    print("✓ Beende Programm...")


def interrupted_message():
    print("\n✓ Beende Programm (Strg+C)...")


def shutdown_summary(csv_filename: str):
    header("SHUTDOWN")
    print("✓ Worker beendet")
    print(f"✓ Logdatei: {csv_filename}")
    print(LINE)

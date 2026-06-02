"""
Dieses Modul enthält alle Ausgaben für die Konsole: Header, Statustexte und
Benutzerhinweise für den interaktiven Modus.
"""

import time

from Komunikation import scan_ports_with_spinner, print_available_ports

LINE = "=" * 80


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
    print("   • 'scan'  - Verfügbare Ports neu scannen")
    print("   • 'test'  - Alle bekannten Befehle an Geräte senden")
    print("   • 'quit'  - Programm beenden")
    print(f"\n⏱️  Autom. Abfragen (jede {laser_interval:.1f}s Laser, jede {lockin_interval:.1f}s LockIn)")
    print(LINE + "\n")


def waiting_for_responses(seconds: int):
    print(f"\n⏳ Warte auf Antworten ({seconds} Sekunden)...\n")


def interactive_header():
    header("INTERAKTIVER MODUS - EINGABE ERWARTET")


def unknown_command():
    print("  ❌ Unbekannter Befehl. Nutze: scan, test oder quit")


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

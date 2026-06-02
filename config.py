"""
Hier stehen alle wichtigen Einstellungen für das RS232-Kommunikationssystem.
Die Datei enthält Ports, Baudraten, Logging-Optionen und den Simulationsmodus.
"""

# ============================================================================
# HARDWARE-KONFIGURATION
# ============================================================================

# Serielle Ports
PORT_LASER = None  # z.B. "COM3" oder "/dev/ttyUSB0"
PORT_LOCKIN = None  # z.B. "COM4" oder "/dev/ttyUSB1"

# Baudrates
BAUDRATE_LASER = 9600
BAUDRATE_LOCKIN = 19200

# Timeouts (Sekunden)
TIMEOUT_LASER = 1.0
TIMEOUT_LOCKIN = 1.0

# ============================================================================
# WORKER-KONFIGURATION
# ============================================================================

# Abfrage-Intervalle (Sekunden)
INTERVAL_LASER = 1.0  # Laser-Abfragen alle 1 Sekunde
INTERVAL_LOCKIN = 0.1  # LockIn-Abfragen alle 0.1 Sekunden

# ============================================================================
# LOGGING-KONFIGURATION
# ============================================================================

# Logging-Modus: "M" für Hardware-Messung, "T" für Test/Simulation
LOG_PREFIX = "M"

# Capture Input in Terminal-Logging
CAPTURE_INPUT = True

# Inset Session Separator in CSV
INSERT_SEPARATOR = True

# ============================================================================
# SIMULATION-KONFIGURATION
# ============================================================================

# Simulationsmodus aktivieren (ignoriert pyserial-Verfügbarkeit)
SIMULATE = False

# Simulator-Datei (für FileSimulator, falls vorhanden)
SIMULATOR_FILE = "20190701_181338_MP1_QC19C.txt"

# ============================================================================
# INTERAKTIVE BEFEHLE
# ============================================================================

# Verfügbare Befehle für interaktiven Modus
KNOWN_COMMANDS = [
    ("OsTech", "GS", "Status abfragen"),
    ("OsTech", "GT", "Temperatur abfragen"),
    ("OsTech", "GMS 0x4000", "Laser Current ON"),
    ("OsTech", "GMS 0x0000", "Laser Current OFF"),
    ("SR830", "PHAS?", "Phase abfragen"),
    ("SR830", "SNAP? 1,2", "Lock-In X/Y Daten"),
    ("SR830", "FREQ?", "Frequenz abfragen"),
    ("SR830", "HARM?", "Harmonische abfragen"),
]

# ============================================================================
# TIMING-KONFIGURATION
# ============================================================================

# Startup-Warte-Zeit (Sekunden)
STARTUP_WAIT = 2.0

# Initiale Antwort-Warte-Zeit nach Startup (Sekunden)
INITIAL_WAIT = 30

# Interaktive Abfrage-Warte-Zeit (Sekunden)
INTERACTIVE_WAIT = 20

# Port-Scan-Timeout (Sekunden)
PORT_SCAN_TIMEOUT = 8

# Worker-Join-Timeout (Sekunden)
WORKER_JOIN_TIMEOUT = 5.0

# ============================================================================
# FEHLERBEHANDLUNG
# ============================================================================

# Automatisch in Simulationsmodus bei fehlendem pyserial
AUTO_SIMULATE_ON_NO_SERIAL = True

# ============================================================================
# AUSGABE-KONFIGURATION
# ============================================================================

# Debug-Ausgaben aktivieren
DEBUG = False

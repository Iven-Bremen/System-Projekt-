"""
Test/Simulation-Einstiegspunkt für das RS232-Kommunikationssystem.
Konfigurationsparameter werden aus config.py geladen.
Ausführung delegiert an helper.py im Simulationsmodus.
"""

import config
from helper import run_simulation


def main():
    """Hauptprogramm für Simulation."""
    # Konfiguriere für Simulationsmodus
    config.LOG_PREFIX = "T"
    config.SIMULATE = True

    # Starte Simulation über helper
    run_simulation(interactive=False)


if __name__ == '__main__':
    main()
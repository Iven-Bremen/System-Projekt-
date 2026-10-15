"""
Einstieg für die Simulation des RS232-Kommunikationssystems.
Hier werden die Einstellungen aus config.py geladen und dann die
Simulationsfunktion aus helper.py gestartet.
"""

import config
from helper import run_simulation
from Sim import FileSimulator


def main():
    """Starte den Testlauf mit simulierten Gerätedaten."""
    # Wir setzen das Programm bewusst in den Testmodus,
    # damit es keine echte Hardware erwartet.
    config.LOG_PREFIX = "T"
    config.SIMULATE = True

    # Der Simulator liest die Testdaten aus der angegebenen Datei.
    simulator = FileSimulator(config.SIMULATOR_FILE)

    # Simulation starten und dabei den geladenen Simulator verwenden.
    run_simulation(interactive=False, simulator=simulator)


if __name__ == '__main__':
    main()
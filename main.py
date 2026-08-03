"""
Hauptprogramm für den Hardware-Modus des RS232-Kommunikationssystems.
Hier werden Kommandozeilen-Argumente gelesen und das Programm gestartet.
"""

import sys
import config
from helper import run_hardware, run_custom, run_simulation
from Komunikation import print_available_ports


def parse_args(args):
    """Liest die Eingabeparameter von der Kommandozeile aus."""
    port_laser = None
    port_lockin = None
    did_list = False
    use_hardware = False
    use_simulation = False
    interactive = True

    for idx, arg in enumerate(args):
        if arg in ("--laser-port", "-l") and idx + 1 < len(args):
            port_laser = args[idx + 1]
        elif arg in ("--lockin-port", "-k") and idx + 1 < len(args):
            port_lockin = args[idx + 1]
        elif arg == "--list":
            print_available_ports()
            did_list = True
        elif arg in {"--hardware", "-h"}:
            use_hardware = True
        elif arg in {"--simulate", "-s"}:
            use_simulation = True
        elif arg in {"--no-interactive", "-ni"}:
            interactive = False

    return port_laser, port_lockin, did_list, use_hardware, use_simulation, interactive


def main():
    """Startet das Programm und übernimmt gegebenenfalls benutzerdefinierte Ports."""
    parsed = parse_args(sys.argv[1:])
    port_laser, port_lockin, did_list, use_hardware, use_simulation, interactive = parsed

    if did_list:
        return

    # Überschreibe config-Parameter mit Kommandozeilen-Argumenten
    if port_laser:
        config.PORT_LASER = port_laser
    if port_lockin:
        config.PORT_LOCKIN = port_lockin

    if use_simulation:
        run_simulation(interactive=interactive)
    elif use_hardware or port_laser or port_lockin:
        run_custom(port_laser=config.PORT_LASER, port_lockin=config.PORT_LOCKIN, interactive=interactive)
    else:
        run_hardware(interactive=interactive)


if __name__ == '__main__':
    main()

#
#
#
#
#
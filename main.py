"""
Haupteinstiegspunkt für das RS232-Kommunikationssystem im Hardware-Modus.
Konfigurationsparameter werden aus config.py geladen.
Ausführung delegiert an helper.py.
"""

import sys
import config
from helper import run_hardware, run_custom
from Komunikation import print_available_ports


def parse_args(args):
    """Parse Kommandozeilen-Argumente."""
    port_laser = None
    port_lockin = None
    for idx, arg in enumerate(args):
        if arg in ("--laser-port", "-l") and idx + 1 < len(args):
            port_laser = args[idx + 1]
        if arg in ("--lockin-port", "-k") and idx + 1 < len(args):
            port_lockin = args[idx + 1]
        if arg == "--list":
            print_available_ports()
            return None, None, True
    return port_laser, port_lockin, False


def main():
    """Hauptprogramm."""
    port_laser, port_lockin, did_list = parse_args(sys.argv[1:])
    
    if did_list:
        return

    # Überschreibe config-Parameter mit Kommandozeilen-Argumenten
    if port_laser:
        config.PORT_LASER = port_laser
    if port_lockin:
        config.PORT_LOCKIN = port_lockin

    # Starte Programm über helper
    if port_laser or port_lockin:
        run_custom(port_laser=config.PORT_LASER, port_lockin=config.PORT_LOCKIN)
    else:
        run_hardware(interactive=True)


if __name__ == '__main__':
    main()

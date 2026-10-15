"""
Dieses Modul organisiert den Programmablauf für die RS232-Kommunikation.
Es kümmert sich um Logging, die Simulationsentscheidung und den Hintergrund-Worker.
"""

import sys
import time
import queue

import config
from Komunikation import (
    SerialWorker,
    send_all_commands,
    drain_result_queue,
    scan_ports_with_spinner,
    print_available_ports,
    resolve_port,
    SERIAL_AVAILABLE,
    auto_detect_device_ports,
    print_auto_detected_ports,
    OsTechStatusDecoder,
)
from Log import make_log_path, start_terminal_logging, append_csv_row
from Terminal import (
    header,
    mode_status,
    port_search_header,
    no_ports_found,
    prompt_for_port,
    startup_info,
    interactive_menu,
    waiting_for_responses,
    interactive_header,
    unknown_command,
    scan_started,
    test_started,
    exit_message,
    interrupted_message,
    shutdown_summary,
    parse_interactive_command,
    show_help,
)


class ProgramRunner:
    """Dieser Runner hält das Programm zusammen: Ports, Simulation und Menü."""

    def __init__(self, port_laser=None, port_lockin=None, simulate=None, simulator=None, interactive=True):
        """
        Bereitet die Ausführung mit den richtigen Parametern vor.

        Args:
            port_laser: Port für den OsTech-Laser
            port_lockin: Port für den SR830-LockIn
            simulate: Wenn True, läuft das Programm im Simulationsmodus
            simulator: Ein Simulatorobjekt für die virtuellen Antworten
            interactive: Wenn True, zeigt das Programm das interaktive Menü
        """
        self.port_laser = port_laser or config.PORT_LASER
        self.port_lockin = port_lockin or config.PORT_LOCKIN
        self.simulate = simulate if simulate is not None else config.SIMULATE
        self.simulator = simulator
        self.interactive = interactive

        self.csv_path = None
        self.worker = None
        self.gui_to_device = queue.Queue()
        self.device_to_gui = queue.Queue()

    def initialize(self):
        """Bereitet das Logging vor und schreibt die Startkonfiguration ins Log."""
        # Wir legen die CSV-Datei an und starten die Terminal-Logaufzeichnung.
        self.csv_path = make_log_path(config.LOG_PREFIX)
        try:
            start_terminal_logging(
                prefix=config.LOG_PREFIX,
                csv_path=self.csv_path,
                capture_input=config.CAPTURE_INPUT,
                insert_separator=config.INSERT_SEPARATOR,
            )
        except Exception as e:
            print(f"[WARNUNG] Logging konnte nicht vollständig aktiviert werden: {e}")

        # Logging: Konfiguration
        self._log_configuration()

    def _log_configuration(self):
        """Speichert die aktuellen Einstellungen im Log, damit man später nachvollziehen kann, wie gestartet wurde."""
        config_items = [
            ("PORT_LASER", str(self.port_laser)),
            ("PORT_LOCKIN", str(self.port_lockin)),
            ("BAUDRATE_LASER", str(config.BAUDRATE_LASER)),
            ("BAUDRATE_LOCKIN", str(config.BAUDRATE_LOCKIN)),
            ("INTERVAL_LASER", str(config.INTERVAL_LASER)),
            ("INTERVAL_LOCKIN", str(config.INTERVAL_LOCKIN)),
            ("LOG_PREFIX", config.LOG_PREFIX),
            ("SIMULATE", str(self.simulate)),
            ("CAPTURE_INPUT", str(config.CAPTURE_INPUT)),
            ("INSERT_SEPARATOR", str(config.INSERT_SEPARATOR)),
        ]
        for param, value in config_items:
            try:
                append_csv_row(
                    self.csv_path,
                    device="CONFIG",
                    command=param,
                    raw_response=value,
                    decoded_info="",
                    latency_ms=0,
                )
            except Exception:
                pass

    def run(self):
        """Hauptprogramm ausführen."""
        try:
            self.initialize()

            # Starte Kommunikationssystem
            self._startup()

        except KeyboardInterrupt:
            interrupted_message()
        except Exception as e:
            print(f"[FEHLER] {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Egal ob normal beendet oder durch einen Fehler: wir schalten sauber ab.
            self._shutdown()

    def run_interactive(self):
        """Hauptprogramm mit interaktivem Modus."""
        try:
            self.initialize()

            # Starte Kommunikationssystem
            self._startup()

            if self.interactive:
                self._interactive_loop()

        except KeyboardInterrupt:
            interrupted_message()
        except Exception as e:
            print(f"[FEHLER] {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Am Ende räumen wir immer auf und beenden den Worker korrekt.
            self._shutdown()

    def _startup(self):
        """Startet den Hintergrund-Worker und schickt die ersten Befehle ab."""
        # Hier entscheiden wir, ob wir echte Hardware nutzen oder simulieren.
        use_simulation = self.simulate or (config.AUTO_SIMULATE_ON_NO_SERIAL and not SERIAL_AVAILABLE)

        # Header ausgeben und den genutzten Modus anzeigen.
        header("HARDWARE RS232 / USB KOMMUNIKATIONSSYSTEM - AKTIVER MODUS")
        mode_status(use_simulation=use_simulation)

        # Port-Auflösung
        port_laser = self.port_laser
        port_lockin = self.port_lockin

        if not port_laser or not port_lockin:
            if use_simulation:
                # Im Simulationsmodus brauchen wir keinen echten Portnamen.
                port_laser = port_laser or "SIM_LASER"
                port_lockin = port_lockin or "SIM_LOCKIN"
            else:
                port_search_header()
                ports = scan_ports_with_spinner(timeout=config.PORT_SCAN_TIMEOUT)
                print_available_ports(ports)

                if not ports:
                    no_ports_found()

                detected_laser, detected_lockin, detection = auto_detect_device_ports(ports)
                print_auto_detected_ports(detection)
                if detected_laser or detected_lockin:
                    if detected_laser:
                        print(f"\nAutomatisch als OsTech Laser erkannt: {detected_laser}")
                        port_laser = port_laser or detected_laser
                    if detected_lockin:
                        print(f"Automatisch als SR830 LockIn erkannt: {detected_lockin}")
                        port_lockin = port_lockin or detected_lockin

                if not port_laser:
                    port_laser = prompt_for_port(
                        "\n[OsTech-Laser] Gib den Port ein (z.B. COM3 oder /dev/serial/by-id/usb-...): "
                    )
                if not port_lockin:
                    port_lockin = prompt_for_port(
                        "\n[SR830-LockIn] Gib den Port ein (z.B. COM4 oder /dev/serial/by-id/usb-...): "
                    )

        port_laser = resolve_port(port_laser)
        port_lockin = resolve_port(port_lockin)

        # Worker erstellen und dabei den Simulator weiterreichen, wenn einer vorhanden ist.
        self.worker = SerialWorker(
            port_laser=port_laser,
            port_lockin=port_lockin,
            cmd_queue=self.gui_to_device,
            res_queue=self.device_to_gui,
            csv_filename=self.csv_path,
            simulate=use_simulation,
            simulator=self.simulator,
        )

        # Startup-Info
        startup_info(
            port_laser, port_lockin, self.csv_path, self.worker.INTERVAL_LASER, self.worker.INTERVAL_LOCKIN
        )
        interactive_menu(self.worker.INTERVAL_LASER, self.worker.INTERVAL_LOCKIN)

        # Worker starten
        self.worker.start()
        time.sleep(config.STARTUP_WAIT)
        send_all_commands(self.gui_to_device)

        waiting_for_responses(config.INITIAL_WAIT)
        for _ in range(config.INITIAL_WAIT):
            drain_result_queue(self.device_to_gui)
            time.sleep(0.5)

    def _interactive_loop(self):
        """Interaktive Eingabe-Schleife."""
        interactive_header()
        while True:
            try:
                raw_cmd = input("\n> Eingabe (scan/test/help/quit): ").strip()
                command, payload = parse_interactive_command(raw_cmd)

                if command == "quit":
                    exit_message()
                    break
                elif command == "scan":
                    scan_started()
                    ports = scan_ports_with_spinner(timeout=config.PORT_SCAN_TIMEOUT)
                    print_available_ports(ports)
                elif command == "test":
                    test_started()
                    send_all_commands(self.gui_to_device)
                    waiting_for_responses(config.INTERACTIVE_WAIT)
                    received_any = False
                    for _ in range(config.INTERACTIVE_WAIT):
                        while not self.device_to_gui.empty():
                            payload = self.device_to_gui.get_nowait()
                            received_any = True
                            print(
                                f"[TEST] {payload.get('device')} | {payload.get('command')} -> {payload.get('decoded') or payload.get('raw')}"
                            )
                        time.sleep(0.5)
                    if not received_any:
                        print("[INFO] Keine Nachrichten vom Laser oder Lock-In empfangen.")
                elif command == "help":
                    show_help()
                elif command == "connect":
                    if self.worker is None:
                        print("[INFO] Worker ist noch nicht initialisiert.")
                    else:
                        laser_ok = self.worker.laser.connect()
                        lockin_ok = self.worker.lockin.connect()
                        if laser_ok and lockin_ok:
                            print("[INFO] Verbindung zu Laser und Lock-In erfolgreich geöffnet.")
                        else:
                            print("[WARNUNG] Verbindung zu mindestens einem Gerät war nicht erfolgreich.")
                            if not laser_ok:
                                print("[WARNUNG] Laser: Verbindung fehlgeschlagen.")
                            if not lockin_ok:
                                print("[WARNUNG] Lock-In: Verbindung fehlgeschlagen.")
                elif command == "disconnect":
                    if self.worker is None:
                        print("[INFO] Worker ist noch nicht initialisiert.")
                    else:
                        self.worker.laser.close()
                        self.worker.lockin.close()
                        print("[INFO] Verbindung zu Laser und Lock-In geschlossen.")
                elif command == "device":
                    if self.worker is None:
                        print("[INFO] Worker ist noch nicht initialisiert.")
                    else:
                        device = payload.get("device")
                        action = payload.get("action")
                        value = payload.get("value")
                        if device == "laser":
                            if action == "gs":
                                res, lat = self.worker.laser.query("GS")
                                decoded = OsTechStatusDecoder.decode(res)
                                decoded_text = " | ".join(decoded["active_states"])
                                if res is None:
                                    print(f"[WARNUNG] Laser: keine Antwort empfangen (GS).")
                                else:
                                    print(f"[Laser] GS -> {decoded_text or res} ({lat:.1f}ms)")
                            elif action == "gt":
                                res, lat = self.worker.laser.query("GT")
                                if res is None:
                                    print(f"[WARNUNG] Laser: keine Antwort empfangen (GT).")
                                else:
                                    print(f"[Laser] GT -> {res} ({lat:.1f}ms)")
                            elif action == "on":
                                res, lat = self.worker.laser.query("GMS 0x4000")
                                if res is None:
                                    print(f"[WARNUNG] Laser: keine Antwort empfangen (GMS 0x4000).")
                                else:
                                    print(f"[Laser] GMS 0x4000 -> {res} ({lat:.1f}ms)")
                            elif action == "off":
                                res, lat = self.worker.laser.query("GMS 0x0000")
                                if res is None:
                                    print(f"[WARNUNG] Laser: keine Antwort empfangen (GMS 0x0000).")
                                else:
                                    print(f"[Laser] GMS 0x0000 -> {res} ({lat:.1f}ms)")
                            elif action == "gms":
                                if value is None:
                                    print("[INFO] Bitte einen Wert angeben, z. B. 0x0000 oder 0x4000.")
                                else:
                                    normalized_value = value.lower()
                                    if normalized_value not in {"0x0000", "0x4000", "0", "1", "off", "on"}:
                                        print("[WARNUNG] Ungültiger Laser-Wert. Erlaubt: 0x0000 (AUS), 0x4000 (EIN).")
                                    else:
                                        cmd = "GMS 0x4000" if normalized_value in {"0x4000", "1", "on"} else "GMS 0x0000"
                                        res, lat = self.worker.laser.query(cmd)
                                        if res is None:
                                            print(f"[WARNUNG] Laser: keine Antwort empfangen ({cmd}).")
                                        else:
                                            print(f"[Laser] {cmd} -> {res} ({lat:.1f}ms)")
                            else:
                                print(f"[INFO] Unbekannter Laser-Befehl: {action}")
                        elif device == "lockin":
                            if action == "phas":
                                res, lat = self.worker.lockin.query("PHAS?")
                                if res is None:
                                    print(f"[WARNUNG] Lock-In: keine Antwort empfangen (PHAS?).")
                                else:
                                    print(f"[LockIn] PHAS? -> {res} ({lat:.1f}ms)")
                            elif action == "freq":
                                res, lat = self.worker.lockin.query("FREQ?")
                                if res is None:
                                    print(f"[WARNUNG] Lock-In: keine Antwort empfangen (FREQ?).")
                                else:
                                    print(f"[LockIn] FREQ? -> {res} ({lat:.1f}ms)")
                            elif action == "snap":
                                res, lat = self.worker.lockin.query("SNAP? 1,2")
                                if res is None:
                                    print(f"[WARNUNG] Lock-In: keine Antwort empfangen (SNAP? 1,2).")
                                else:
                                    print(f"[LockIn] SNAP? 1,2 -> {res} ({lat:.1f}ms)")
                            else:
                                print(f"[INFO] Unbekannter LockIn-Befehl: {action}")
                        else:
                            print(f"[INFO] Unbekanntes Gerät: {device}")
                elif command == "noop":
                    continue
                else:
                    unknown_command(payload)

                drain_result_queue(self.device_to_gui)
            except KeyboardInterrupt:
                interrupted_message()
                break

    def _shutdown(self):
        """Beende den Worker und räume auf."""
        if self.worker:
            self.worker.stop()
            self.worker.join(timeout=config.WORKER_JOIN_TIMEOUT)
        drain_result_queue(self.device_to_gui)
        if self.worker:
            shutdown_summary(self.worker.csv_filename)


def run_hardware(interactive=True, simulator=None):
    """Starte das System im Hardware-Modus."""
    runner = ProgramRunner(simulate=False, interactive=interactive, simulator=simulator)
    runner.run_interactive()


def run_simulation(interactive=False, simulator=None):
    """Starte das System im Simulationsmodus."""
    runner = ProgramRunner(simulate=True, interactive=interactive, simulator=simulator)
    runner.run()


def run_custom(port_laser=None, port_lockin=None, simulate=None, simulator=None, interactive=True):
    """Starte das System mit benutzerdefinierten Parametern."""
    runner = ProgramRunner(port_laser=port_laser, port_lockin=port_lockin, simulate=simulate, simulator=simulator, interactive=interactive)
    runner.run_interactive()

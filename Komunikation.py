"""
Dieses Modul enthält die Gerätetreiber und den Hintergrund-Worker für die
RS232-/Serial-Kommunikation mit den beiden Geräten OsTech-Laser und SR830-LockIn.

Die Struktur folgt dem allgemeinen Muster eines seriellen Hosts:
- Port öffnen
- Befehl senden
- Antwort lesen
- Ergebnis weiterverarbeiten

Im Gegensatz zum externen Beispiel aus dem GitHub-Repo ist dieses Projekt auf
zwei konkrete Geräte und ein eigenes Protokoll ausgerichtet. Die Grundidee ist
aber dieselbe: ein einfacher, gut dokumentierter Serial-Loop mit sauberem
Fehlerhandling.
"""

import queue
import time
import os
import sys
import threading
from datetime import datetime

try:
    import serial
    from serial.tools import list_ports
    SERIAL_AVAILABLE = True
except Exception:
    serial = None
    list_ports = None
    SERIAL_AVAILABLE = False

from Log import make_log_path, ensure_log_file, insert_session_separator, append_csv_row
from lockin_amplifier import LAM


class OsTechStatusDecoder:
    """Dekodiere den Statusstring vom OsTech-Laser."""

    @staticmethod
    def decode(status_string):
        active_states = []
        status_int = 0
        if isinstance(status_string, str) and status_string.startswith("0x"):
            try:
                status_int = int(status_string, 16)
            except ValueError:
                return {"valid": False, "active_states": [], "laser_current_on": False}

        if status_int & 0x0001:
            active_states.append("Interlock OK")
        if status_int & 0x0002:
            active_states.append("Laser Ready")
        if status_int & 0x0004:
            active_states.append("Laser Current ON")
        if status_int & 0x0008:
            active_states.append("Low Power")
        if status_int & 0x0010:
            active_states.append("High Power")
        if status_int & 0x0020:
            active_states.append("Temp Alarm")

        return {
            "valid": isinstance(status_string, str) and status_string.startswith("0x"),
            "active_states": active_states,
            "laser_current_on": bool(status_int & 0x0004),
            "raw": status_string,
        }


class OsTechDriver:
    """Treiber für den OsTech-Laser über RS232/USB."""

    def __init__(self, port, baudrate=9600, timeout=1.0, simulate=False, simulator=None):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.simulate = simulate
        self.simulator = simulator
        self.ser = None

    def connect(self):
        if self.simulate:
            print(f"[OsTech] MOCK-MODUS: Virtuell verbunden mit {self.port}")
            return True
        if serial is None:
            print("[OsTech] pyserial ist nicht verfügbar.")
            return False
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            print(f"[OsTech] HARDWARE: Erfolgreich verbunden mit {self.port}")
            return True
        except Exception as e:
            print(f"[OsTech] Verbindungsfehler an {self.port}: {e}")
            self.ser = None
            return False

    def close(self):
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None

    def query(self, cmd):
        """Sende einen Befehl an das Gerät und liefere die Antwort zurück."""
        start_time = time.perf_counter()
        if not self.ser and not self.simulate:
            return None, (time.perf_counter() - start_time) * 1000

        if self.simulate:
            time.sleep(0.012)
            latency = (time.perf_counter() - start_time) * 1000
            if self.simulator:
                if cmd == "GT":
                    return self.simulator.get_GT(), latency
                if cmd == "GS":
                    return self.simulator.get_GS(), latency
                return "OK", latency
            if cmd == "GT":
                return "24.85", latency
            if cmd == "GS":
                return "0x4405", latency
            return "OK", latency

        try:
            self.ser.write(f"{cmd}\r\n".encode("utf-8"))
            response = self.ser.readline().decode("utf-8").strip()
            latency = (time.perf_counter() - start_time) * 1000
            return response, latency
        except Exception as e:
            return f"ERROR: {e}", (time.perf_counter() - start_time) * 1000


class SR830Driver(LAM):
    """Kompatibilitäts-Wrapper für die bestehende SR830-Schnittstelle."""

    def __init__(self, port, baudrate=19200, timeout=1.0, simulate=False, simulator=None, log_path=None):
        super().__init__(port=port, baudrate=baudrate, timeout=timeout, simulate=simulate, simulator=simulator, log_path=log_path)

    def query(self, cmd):
        return super().query(cmd)


def initialize_lockin(port=None, baudrate=19200, timeout=1.0, simulate=False, simulator=None, log_path=None):
    """Erzeugt und initialisiert einen SR830-Driver für den direkten Einsatz."""
    driver = SR830Driver(port=port, baudrate=baudrate, timeout=timeout, simulate=simulate, simulator=simulator, log_path=log_path)
    driver.connect()
    return driver


class SerialWorker(threading.Thread):
    """Hintergrund-Worker, der regelmäßig Daten abfragt und alles in die CSV schreibt."""

    def __init__(self, port_laser, port_lockin, cmd_queue, res_queue, csv_filename=None, simulate=False, simulator=None):
        super().__init__()
        self.cmd_queue = cmd_queue
        self.res_queue = res_queue
        self.csv_filename = csv_filename
        self.running = True
        self.simulate = simulate
        self.simulator = simulator

        self.laser = OsTechDriver(port=port_laser, simulate=self.simulate, simulator=self.simulator)
        self.lockin = SR830Driver(port=port_lockin, simulate=self.simulate, simulator=self.simulator)

        self.INTERVAL_LOCKIN = 0.1
        self.INTERVAL_LASER = 1.0

        self.init_csv()

    def init_csv(self):
        if not self.csv_filename:
            self.csv_filename = make_log_path('T' if self.simulate else 'M')
        ensure_log_file(self.csv_filename)
        insert_session_separator(self.csv_filename, mode='SIMULATION' if self.simulate else 'HARDWARE')
        print(f"[Worker] CSV-Logging initialisiert: {self.csv_filename}")

    def run(self):
        self.laser.connect()
        self.lockin.connect()

        last_lockin = time.perf_counter()
        last_laser = time.perf_counter()

        print("\n=== ASYNCHRONER DATEN-WORKER GESTARTET ===\n")

        while self.running:
            now = time.perf_counter()
            try:
                device, command = self.cmd_queue.get_nowait()
                self.process_gui_command(device, command)
                self.cmd_queue.task_done()
            except queue.Empty:
                pass

            if now - last_lockin >= self.INTERVAL_LOCKIN:
                res, lat = self.lockin.query("SNAP? 1,2")
                self.log_and_forward("SR830", "SNAP? 1,2", res, res, lat)
                last_lockin = now

            if now - last_laser >= self.INTERVAL_LASER:
                res, lat = self.laser.query("GS")
                decoded = OsTechStatusDecoder.decode(res)
                decoded_text = " | ".join(decoded["active_states"])
                self.log_and_forward("OsTech", "GS", res, decoded_text, lat, extra_data=decoded)

                temp_res, temp_lat = self.laser.query("GT")
                self.log_and_forward("OsTech", "GT", temp_res, f"{temp_res} °C", temp_lat)
                last_laser = now

            time.sleep(0.001)

    def process_gui_command(self, device, command):
        if device == "OsTech":
            res, lat = self.laser.query(command)
            decoded_text = res
            if command == "GS":
                decoded = OsTechStatusDecoder.decode(res)
                decoded_text = " | ".join(decoded["active_states"])
            self.log_and_forward("OsTech_Manual", command, res, decoded_text, lat)
        elif device == "SR830":
            res, lat = self.lockin.query(command)
            self.log_and_forward("SR830_Manual", command, res, res, lat)
        else:
            print(f"Unbekanntes Gerät für manuelle Anweisung: {device}")

    def log_and_forward(self, device, command, raw_res, decoded_txt, latency, extra_data=None):
        append_csv_row(self.csv_filename, device, command, raw_res, decoded_txt, latency)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] {device:20} Befehl: {command:15} │ Antwort: {decoded_txt:40} │ {latency:.1f}ms")

        payload = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "device": device,
            "command": command,
            "raw": raw_res,
            "decoded": decoded_txt,
            "latency": latency,
        }
        if extra_data:
            payload["structured_status"] = extra_data
        self.res_queue.put(payload)

    def stop(self):
        self.running = False
        self.laser.close()
        self.lockin.close()
        self.laser.close()
        self.lockin.close()


def scan_serial_ports():
    if list_ports is None:
        return []
    return [(p.device, p.description) for p in list_ports.comports()]


def resolve_port(port):
    if not port:
        return None
    if port.startswith("usb-") and not port.startswith("/dev/"):
        return f"/dev/serial/by-id/{port}"
    return port


def scan_ports_with_spinner(timeout=8):
    spinner = "|/-\\"
    start = time.time()
    idx = 0
    ports = []
    while time.time() - start < timeout:
        ports = scan_serial_ports()
        if ports:
            break
        sys.stdout.write(f"\rSuche serielle Ports... {spinner[idx % len(spinner)]}")
        sys.stdout.flush()
        idx += 1
        time.sleep(0.3)
    sys.stdout.write("\r" + " " * 40 + "\r")
    return ports


def print_available_ports(ports=None):
    if ports is None:
        ports = scan_serial_ports()
    if not ports:
        print("Keine seriellen Ports gefunden.")
        return
    print("Gefundene serielle Ports:")
    for idx, (device, description) in enumerate(ports, start=1):
        print(f"  {idx}. {device} - {description}")


def _is_float(value):
    try:
        float(value)
        return True
    except Exception:
        return False


def _query_serial_port(port, baudrate, command, timeout=0.7):
    if serial is None:
        return None
    try:
        with serial.Serial(port, baudrate, timeout=timeout) as ser:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            for ending in ("\r\n", "\n"):
                try:
                    ser.write(f"{command}{ending}".encode("utf-8"))
                    time.sleep(0.12)
                    response = ser.readline().decode("utf-8", errors="ignore").strip()
                    if response:
                        return response
                except Exception:
                    continue
    except Exception:
        return None
    return None


def _looks_like_os_tech_response(response, command):
    if not response:
        return False
    if command == "GS":
        return response.startswith("0x") or response.upper() == "OK"
    if command == "GT":
        return _is_float(response)
    return False


def _looks_like_sr830_response(response, command):
    if not response:
        return False
    if command == "PHAS?":
        return _is_float(response)
    if command == "SNAP? 1,2":
        parts = [p.strip() for p in response.split(",")]
        return len(parts) == 2 and all(_is_float(p) for p in parts)
    return False


def _probe_os_tech_port(port):
    gs = _query_serial_port(port, 9600, "GS")
    if _looks_like_os_tech_response(gs, "GS"):
        return True
    gt = _query_serial_port(port, 9600, "GT")
    return _looks_like_os_tech_response(gt, "GT")


def _probe_sr830_port(port):
    phas = _query_serial_port(port, 19200, "PHAS?")
    if _looks_like_sr830_response(phas, "PHAS?"):
        return True
    snap = _query_serial_port(port, 19200, "SNAP? 1,2")
    return _looks_like_sr830_response(snap, "SNAP? 1,2")


def auto_detect_device_ports(ports=None):
    if list_ports is None:
        return None, None, {}
    if ports is None:
        ports = scan_serial_ports()

    detection = {}
    for device, description in ports:
        detection[device] = {
            "description": description,
            "os_tech": _probe_os_tech_port(device),
            "sr830": _probe_sr830_port(device),
        }

    port_laser = None
    port_lockin = None
    os_tech_candidates = [p for p, info in detection.items() if info["os_tech"]]
    sr830_candidates = [p for p, info in detection.items() if info["sr830"]]

    if len(os_tech_candidates) == 1:
        port_laser = os_tech_candidates[0]
    if len(sr830_candidates) == 1:
        port_lockin = sr830_candidates[0]

    if port_laser is None and len(os_tech_candidates) == 2 and len(sr830_candidates) == 2:
        # Wenn zwei Ports gefunden und beide Geräte antworten jeweils eindeutig,
        # dann keinem Port zuordnen, da es zu unsicher ist.
        pass

    return port_laser, port_lockin, detection


def print_auto_detected_ports(detection):
    if not detection:
        return
    print("\nAuto-Erkennungsergebnisse:")
    for port, info in detection.items():
        labels = []
        if info.get("os_tech"):
            labels.append("OsTech Laser")
        if info.get("sr830"):
            labels.append("SR830 LockIn")
        if not labels:
            labels.append("unbekannt")
        description = info.get("description", "")
        print(f"  {port} - {description} -> {', '.join(labels)}")


def send_all_commands(cmd_queue, known_commands=None):
    if known_commands is None:
        import config
        known_commands = config.KNOWN_COMMANDS
    
    print("\n" + "=" * 80)
    print("SENDE BEKANNTE BEFEHLE AN GERÄTE")
    print("=" * 80)
    print(f"{'Gerät':<15} | {'Befehl':<20} | Beschreibung")
    print("-" * 80)
    for device, command, description in known_commands:
        print(f"{device:<15} | {command:<20} | {description}")
        cmd_queue.put((device, command))
        time.sleep(0.2)
    print("=" * 80)


def drain_result_queue(res_queue):
    while not res_queue.empty():
        payload = res_queue.get()
        print(f"[EINGANG] {payload['timestamp']} | {payload['device']} | {payload['command']} -> {payload['decoded']} ({payload['latency']:.1f}ms)")

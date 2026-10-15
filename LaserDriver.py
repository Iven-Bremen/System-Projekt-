"""Strukturierte API für den OsTech-Laserdriver.

Diese Klasse kapselt die serielle Kommunikation für den OsTech-Laser und
bietet eine einfache, testbare Schnittstelle ähnlich wie die LAM-Klasse für den
Lock-In-Verstärker.
"""

import csv
import os
import time
from datetime import datetime

try:
    import serial
except Exception:  # pragma: no cover - pyserial may be unavailable in tests
    serial = None


SUPPORTED_BAUDRATES = (9600, 19200, 38400, 57600, 115200)


class LaserDriver:
    """High-level API für den OsTech-Laser über RS232.

    Die Klasse übernimmt die im Handbuch beschriebenen Grenzen der Laserbefehle.
    Für Befehle ohne explizite Grenzen werden Platzhalter-Validierungen verwendet,
    damit die API konsistent bleibt und nur dokumentierte oder reservierte Werte
    akzeptiert.
    """

    def __init__(self, port=None, baudrate=9600, timeout=1.0, simulate=False, simulator=None, log_path=None, i_max=1000.0):
        self.port = port
        self.baudrate = self._validate_baudrate(baudrate)
        self.timeout = timeout
        self.simulate = simulate
        self.simulator = simulator
        self.log_path = log_path
        self.i_max = float(i_max)
        self.ser = None
        self._initialize_log_file()

    def _initialize_log_file(self):
        if not self.log_path:
            return
        directory = os.path.dirname(self.log_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(self.log_path) or os.path.getsize(self.log_path) == 0:
            with open(self.log_path, mode="w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle, delimiter=";")
                writer.writerow(["Timestamp", "Direction", "Command", "Value", "Latency_ms"])

    def _log_transaction(self, direction, command, value=None, latency_ms=None):
        if not self.log_path:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(self.log_path, mode="a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow([timestamp, direction, command, value if value is not None else "", f"{latency_ms:.2f}" if latency_ms is not None else ""])

    def _validate_baudrate(self, baudrate):
        if baudrate not in SUPPORTED_BAUDRATES:
            raise ValueError(f"Ungültige Baudrate {baudrate}. Unterstützt werden: {', '.join(str(v) for v in SUPPORTED_BAUDRATES)}")
        return baudrate

    def _validate_numeric_range(self, value, minimum, maximum, mnemonic):
        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Ungültiger Wert {value!r} für {mnemonic}.") from exc
        if not (minimum <= numeric_value <= maximum):
            raise ValueError(f"{mnemonic} muss zwischen {minimum} und {maximum} liegen.")
        return numeric_value

    def _validate_command_value(self, mnemonic, value):
        mnemonic = mnemonic.upper()

        if mnemonic == "GMS":
            if value is True:
                return "0x4000"
            if value is False:
                return "0x0000"
            if isinstance(value, str):
                try:
                    integer_value = int(value, 16)
                except ValueError as exc:
                    raise ValueError(f"Ungültiger Hex-Wert {value!r} für {mnemonic}.") from exc
                if 0 <= integer_value <= 0xFFFF:
                    return value
                raise ValueError(f"{mnemonic} muss zwischen 0x0000 und 0xFFFF liegen.")
            raise ValueError("GMS akzeptiert nur True/False oder einen Hex-String.")

        if mnemonic == "LCL":
            return self._validate_numeric_range(value, 0.0, self.i_max * 1.05, mnemonic)
        if mnemonic in {"LCT", "LCB"}:
            return self._validate_numeric_range(value, 0.0, self.i_max, mnemonic)
        if mnemonic == "LVC":
            return self._validate_numeric_range(value, 1.3, 6.0, mnemonic)
        if mnemonic == "LPCT":
            return self._validate_numeric_range(value, 0.0, 20.0, mnemonic)
        if mnemonic == "LMP":
            return self._validate_numeric_range(value, 2001.0, 48000.0, mnemonic)
        if mnemonic == "LMW":
            return self._validate_numeric_range(value, 1.0, 48000.0, mnemonic)
        if mnemonic == "LMDIC":
            return self._validate_numeric_range(value, 0.0, 65534.0, mnemonic)
        if mnemonic == "PP":
            return self._validate_numeric_range(value, 0.0, 16.0, mnemonic)
        if mnemonic == "LZTR":
            return self._validate_numeric_range(value, 300.0, 34000.0, mnemonic)
        if mnemonic in {"xTLU", "xTLL", "xTT"}:
            return self._validate_numeric_range(value, -99.0, 200.0, mnemonic)
        if mnemonic == "xTCL":
            return self._validate_numeric_range(value, 0.0, self.i_max, mnemonic)
        if mnemonic in {"xTCCK", "xTCCN"}:
            return self._validate_numeric_range(value, 0.0, 255.0, mnemonic)
        if mnemonic == "xTCCV":
            return self._validate_numeric_range(value, 0.0, 99.0, mnemonic)
        if mnemonic in {"GF", "GFD"}:
            return self._validate_numeric_range(value, 1.2, 24.0, mnemonic)
        if mnemonic == "LTM":
            return self._validate_numeric_range(value, -99.0, 200.0, mnemonic)

        if mnemonic in {"L", "LG", "LPCC", "LPA", "LPT", "LPF", "LMDI", "LMDX", "LMAX", "LMDXN", "PL", "LZR", "LZP", "LZPT", "LZPC", "xTC", "xTA", "xTCA", "xTVA", "GD", "GX", "GVS", "GVN", "GS", "GT", "GM", "GMC", "GMT", "GMS", "GM"}:
            return value

        # Platzhalter für Befehle, für die in der Dokumentation keine expliziten
        # Mindest-/Maximalwerte angegeben sind. Sie bleiben reserviert und werden
        # nur durch den Aufrufer weitergereicht.
        if value is None:
            return value
        return value

    def _reset_serial_buffers(self):
        if self.ser is None:
            return
        for method_name in ("reset_input_buffer", "reset_output_buffer"):
            method = getattr(self.ser, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception:
                    pass

    def _ensure_connection(self):
        if self.simulate:
            return True
        if self.ser is not None:
            try:
                if self.ser.is_open:
                    return True
            except Exception:
                pass
        return self.connect()

    def connect(self):
        if self.simulate:
            print(f"[Laser] MOCK-MODUS: Virtuell verbunden mit {self.port}")
            return True
        if serial is None:
            print("[Laser] pyserial ist nicht verfügbar.")
            return False

        for attempt in range(2):
            try:
                self.ser = serial.Serial(
                    self.port,
                    self.baudrate,
                    timeout=self.timeout,
                    write_timeout=self.timeout,
                )
                self._reset_serial_buffers()
                time.sleep(0.05)
                print(f"[Laser] HARDWARE: Erfolgreich verbunden mit {self.port}")
                return True
            except Exception as exc:
                self.ser = None
                if attempt == 0:
                    time.sleep(0.2)
                    continue
                print(f"[Laser] Verbindungsfehler an {self.port}: {exc}")
                return False

        return False

    def disconnect(self):
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None

    def close(self):
        self.disconnect()

    def build_command(self, mnemonic, *params):
        mnemonic = mnemonic.upper()
        if params:
            return f"{mnemonic} " + " ".join(str(p) for p in params)
        return mnemonic

    def write(self, mnemonic, *params):
        validated_params = []
        for param in params:
            validated_params.append(self._validate_command_value(mnemonic, param))
        params = tuple(validated_params)

        command = self.build_command(mnemonic, *params)
        self._send_command(command)
        self._log_transaction("TX", command)
        return command

    def send_command(self, mnemonic, *params):
        return self.write(mnemonic, *params)

    def _send_command(self, command):
        if self.simulate:
            time.sleep(0.008)
            return True

        if not self._ensure_connection():
            return False

        for attempt in range(2):
            try:
                self._reset_serial_buffers()
                self.ser.write(f"{command}\r\n".encode("utf-8"))
                return True
            except Exception:
                self.disconnect()
                if attempt == 0 and self._ensure_connection():
                    continue
                return False

    def query(self, mnemonic, *params):
        start_time = time.perf_counter()
        if not self.ser and not self.simulate:
            latency = (time.perf_counter() - start_time) * 1000
            self._log_transaction("RX", self.build_command(mnemonic, *params), value="<not connected>", latency_ms=latency)
            return None, latency

        if self.simulate:
            time.sleep(0.008)
            latency = (time.perf_counter() - start_time) * 1000
            if mnemonic == "GS":
                reply = "0x4405"
            elif mnemonic == "GT":
                reply = "24.85"
            elif mnemonic == "GMS":
                reply = "OK"
            else:
                reply = "OK"
            self._log_transaction("RX", self.build_command(mnemonic, *params), value=reply, latency_ms=latency)
            return reply, latency

        if not self._ensure_connection():
            response = "ERROR: not connected"
            latency = (time.perf_counter() - start_time) * 1000
            self._log_transaction("RX", self.build_command(mnemonic, *params), value=response, latency_ms=latency)
            return response, latency

        for attempt in range(2):
            try:
                self._reset_serial_buffers()
                self.ser.write(f"{self.build_command(mnemonic, *params)}\r\n".encode("utf-8"))
                response = self.ser.readline().decode("utf-8", errors="ignore").strip()
                latency = (time.perf_counter() - start_time) * 1000
                self._log_transaction("RX", self.build_command(mnemonic, *params), value=response, latency_ms=latency)
                return response, latency
            except Exception as exc:
                self.disconnect()
                if attempt == 0 and self._ensure_connection():
                    continue
                response = f"ERROR: {exc}"
                latency = (time.perf_counter() - start_time) * 1000
                self._log_transaction("RX", self.build_command(mnemonic, *params), value=response, latency_ms=latency)
                return response, latency

    def GS(self):
        """Fragt den aktuellen Status des Lasers ab."""
        return self.build_command("GS")

    def GT(self):
        """Fragt die Temperatur ab."""
        return self.build_command("GT")

    def GMS(self, value=None):
        """Schaltet den Laser ein oder aus.

        Args:
            value: True -> EIN, False -> AUS, oder ein Hex-String.
        """
        if value is None:
            return self.build_command("GMS")
        payload = self._validate_command_value("GMS", value)
        self.write("GMS", payload)
        return self.build_command("GMS", payload)

    def status(self):
        """Alias für den Statusbefehl."""
        return self.query("GS")[0]

    def temperature(self):
        """Alias für die Temperaturabfrage."""
        return self.query("GT")[0]

    def laser_on(self):
        """Schaltet den Laser ein."""
        return self.GMS(True)

    def laser_off(self):
        """Schaltet den Laser aus."""
        return self.GMS(False)

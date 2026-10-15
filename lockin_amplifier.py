"""
Strukturierter Treiber für den SR830 Lock-In-Verstärker über RS232.

Die Klasse kapselt die wichtigsten SR830-Befehle aus der RS232-Dokumentation und
macht die Kommunikation über einfache, gut lesbare Methoden zugänglich.

Typischer Ablauf:
    LAM = LAM(port="COM4")
    LAM.connect()
    LAM.set_output_interface(0)
    LAM.set_reference_frequency(1000)
    print(LAM.get_phase())
    print(LAM.snapshot_xy())
    LAM.disconnect()
"""

import csv
import os
import time
from datetime import datetime

try:
    import serial
except Exception:  # pragma: no cover - pyserial kann in Testumgebungen fehlen
    serial = None


SUPPORTED_BAUDRATES = (9600, 19200, 38400, 57600, 115200)


class LAM:
    """High-level API für den Stanford Research SR830 über RS232.

    Diese Klasse kapselt die Rohkommunikation in einer LAM-spezifischen Oberfläche.
    Sie bietet Einzelbefehle, Kurzformen wie PHAS(45) und zusammengesetzte
    Konfigurationsmethoden wie init() oder configure_reference().

    Die Klasse stellt eine einfache API für die Kommunikation mit dem Lock-In bereit.
    Jeder Befehl ist entweder ein Schreibbefehl (setzt einen Wert) oder ein
    Query-Befehl (liest einen Wert aus). Die Methoden bauen die korrekten SR830-
    Kommandos automatisch zusammen und kapseln die eigentliche Serielle Übertragung.
    """

    def __init__(self, port=None, baudrate=19200, timeout=1.0, simulate=False, simulator=None, log_path=None):
        """Initialisiert den Treiber mit Port, Baudrate und Simulationsoptionen.

        Args:
            port: Serielle Port-Adresse, z. B. "COM4" oder "/dev/ttyUSB0".
            baudrate: Baudrate für die RS232-Kommunikation. Standard: 19200.
            timeout: Lese-Timeout in Sekunden.
            simulate: Wenn True, arbeitet der Treiber im Simulationsmodus ohne echte Hardware.
            simulator: Optionales Objekt mit Testantworten für Simulationen.
            log_path: Optionaler Pfad zu einer CSV-Datei für das Logging.
        """
        self.port = port
        self.baudrate = self._validate_baudrate(baudrate)
        self.timeout = timeout
        self.simulate = simulate
        self.simulator = simulator
        self.log_path = log_path
        self.ser = None
        self._initialize_log_file()

    def _initialize_log_file(self):
        """Erstellt die Logdatei mit Header, falls ein Pfad angegeben wurde."""
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
        """Schreibt einen Befehl oder eine Antwort in die CSV-Logdatei."""
        if not self.log_path:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(self.log_path, mode="a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow([timestamp, direction, command, value if value is not None else "", f"{latency_ms:.2f}" if latency_ms is not None else ""])

    def _validate_baudrate(self, baudrate):
        """Prüft, ob die Baudrate vom SR830 unterstützt wird."""
        if baudrate not in SUPPORTED_BAUDRATES:
            raise ValueError(
                f"Ungültige Baudrate {baudrate}. Unterstützt werden: {', '.join(str(v) for v in SUPPORTED_BAUDRATES)}"
            )
        return baudrate

    def _validate_value(self, mnemonic, value):
        """Prüft, ob ein Schreibwert für einen SR830-Befehl zulässig ist."""
        if value is None:
            return None

        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Ungültiger Wert {value!r} für {mnemonic}.") from exc

        if mnemonic == "PHAS":
            if not (-360.0 <= numeric_value <= 729.99):
                raise ValueError("PHAS muss zwischen -360.00 und 729.99 liegen.")
        elif mnemonic == "FMOD":
            if int(numeric_value) not in (0, 1):
                raise ValueError("FMOD muss 0 oder 1 sein.")
        elif mnemonic == "FREQ":
            if not (0.001 <= numeric_value <= 102000.0): 
                raise ValueError("FREQ muss zwischen 0.001 und 102000 liegen.")
        elif mnemonic == "RSLP":
            if int(numeric_value) not in (0, 1, 2):
                raise ValueError("RSLP muss 0, 1 oder 2 sein.")
        elif mnemonic == "HARM":
            if int(numeric_value) < 1 or int(numeric_value) > 19999:
                raise ValueError("HARM muss zwischen 1 und 19999 liegen.")
        elif mnemonic == "SLVL":
            if not (0.004 <= numeric_value <= 5.000):
                raise ValueError("SLVL muss zwischen 0.004 und 5.000 liegen.")
        elif mnemonic == "ISRC":
            if int(numeric_value) not in (0, 1, 2, 3):
                raise ValueError("ISRC muss 0, 1, 2 oder 3 sein.")
        elif mnemonic == "IGND":
            if int(numeric_value) not in (0, 1):
                raise ValueError("IGND muss 0 oder 1 sein.")
        elif mnemonic == "ICPL":
            if int(numeric_value) not in (0, 1):
                raise ValueError("ICPL muss 0 oder 1 sein.")
        elif mnemonic == "ILIN":
            if int(numeric_value) not in (0, 1, 2, 3):
                raise ValueError("ILIN muss 0, 1, 2 oder 3 sein.")
        elif mnemonic == "SENS":
            if int(numeric_value) < 0 or int(numeric_value) > 26:
                raise ValueError("SENS muss zwischen 0 und 26 liegen.")
        elif mnemonic == "RMOD":
            if int(numeric_value) not in (0, 1, 2):
                raise ValueError("RMOD muss 0, 1 oder 2 sein.")
        elif mnemonic == "OFLT":
            if int(numeric_value) < 0 or int(numeric_value) > 19:
                raise ValueError("OFLT muss zwischen 0 und 19 liegen.")
        elif mnemonic == "OFSL":
            if int(numeric_value) not in (0, 1, 2, 3):
                raise ValueError("OFSL muss 0, 1, 2 oder 3 sein.")
        elif mnemonic == "SYNC":
            if int(numeric_value) not in (0, 1):
                raise ValueError("SYNC muss 0 oder 1 sein.")

        return value

    def _reset_serial_buffers(self):
        """Leert eingehende und ausgehende Puffer, falls die Bibliothek das unterstützt."""
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
        """Stellt sicher, dass eine aktive serielle Verbindung besteht."""
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
        """Öffnet die serielle Verbindung zum SR830.

        Returns:
            bool: True bei Erfolg, False bei fehlender Library oder Verbindungsfehler.
        """
        if self.simulate:
            print(f"[SR830] MOCK-MODUS: Virtuell verbunden mit {self.port}")
            return True
        if serial is None:
            print("[SR830] pyserial ist nicht verfügbar.")
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
                print(f"[SR830] HARDWARE: Erfolgreich verbunden mit {self.port}")
                return True
            except Exception as exc:
                self.ser = None
                if attempt == 0:
                    time.sleep(0.2)
                    continue
                print(f"[SR830] Verbindungsfehler an {self.port}: {exc}")
                return False

        return False

    def disconnect(self):
        """Schließt die aktive serielle Verbindung sauber."""
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None

    def close(self):
        """Alias für disconnect()."""
        self.disconnect()

    def build_command(self, mnemonic, *params, query=False):
        """Erzeugt aus Mnemonic und Parametern den finalen SR830-Befehl.

        Args:
            mnemonic: Vierbuchstaben-Befehl wie PHAS, FREQ oder SNAP.
            *params: Optionale Parameter, z. B. 12.34 oder 1,2.
            query: Wenn True, wird ein Fragezeichen an den Befehl angehängt.

        Returns:
            str: Formatierter Befehl wie "PHAS 12.34" oder "SNAP? 1,2".
        """
        mnemonic = mnemonic.upper()
        if query:
            if params:
                return f"{mnemonic}? " + ",".join(str(p) for p in params)
            return f"{mnemonic}?"
        if params:
            return f"{mnemonic} " + ",".join(str(p) for p in params)
        return mnemonic

    def write(self, mnemonic, *params, query=False):
        """Sendet einen SR830-Befehl, ohne auf eine Antwort zu warten.

        Diese Methode ist ideal für Schreibbefehle wie PHAS, FREQ oder SENS.

        Args:
            mnemonic: Befehlsname, z. B. "PHAS".
            *params: Parameter für den Befehl.
            query: Falls True, wird ein Query-Befehl erzeugt.

        Returns:
            str: Der gesendete Befehl als String.
        """
        if not query and params:
            validated_params = []
            for param in params:
                if isinstance(param, (int, float)):
                    validated_params.append(self._validate_value(mnemonic, param))
                else:
                    validated_params.append(param)
            params = tuple(validated_params)

        command = self.build_command(mnemonic, *params, query=query)
        self._send_command(command)
        self._log_transaction("TX", command)
        return command

    def send_command(self, mnemonic, *params, query=False):
        """Praktische Alias-Methode für write().

        Verwendung: LAM.send_command("PHAS", 12.34)
        """
        return self.write(mnemonic, *params, query=query)

    def query_value(self, mnemonic, *params):
        """Sendet einen Query-Befehl und gibt nur den Wert zurück.

        Args:
            mnemonic: Befehl wie PHAS, FREQ oder SENS.
            *params: Optionale Query-Parameter.

        Returns:
            str: Antwortwert des Geräts.
        """
        return self.query(self.build_command(mnemonic, *params, query=True))[0]

    def _generic_setter(self, mnemonic, value=None):
        """Hilfsfunktion für kurze Setter-Aufrufe wie FREQ(589)."""
        if value is None:
            return self.query_value(mnemonic)
        self.write(mnemonic, value)
        return self.build_command(mnemonic, value)

    def _generic_query(self, mnemonic):
        """Hilfsfunktion für kurze Query-Aufrufe wie PHAS()."""
        return self.query_value(mnemonic)

    def PHAS(self, value=None):
        """Kurzform für PHAS-Setzen oder -Abfragen.

        Beispiele:
            LAM.PHAS(45.0)   -> sendet PHAS 45.0
            LAM.PHAS()       -> fragt PHAS? ab
        """
        return self._generic_setter("PHAS", value)

    def FMOD(self, value=None):
        """Kurzform für FMOD-Setzen oder -Abfragen."""
        return self._generic_setter("FMOD", value)

    def FREQ(self, value=None):
        """Kurzform für FREQ-Setzen oder -Abfragen."""
        return self._generic_setter("FREQ", value)

    def RSLP(self, value=None):
        """Kurzform für RSLP-Setzen oder -Abfragen."""
        return self._generic_setter("RSLP", value)

    def HARM(self, value=None):
        """Kurzform für HARM-Setzen oder -Abfragen."""
        return self._generic_setter("HARM", value)

    def SLVL(self, value=None):
        """Kurzform für SLVL-Setzen oder -Abfragen."""
        return self._generic_setter("SLVL", value)

    def ISRC(self, value=None):
        """Kurzform für ISRC-Setzen oder -Abfragen."""
        return self._generic_setter("ISRC", value)

    def IGND(self, value=None):
        """Kurzform für IGND-Setzen oder -Abfragen."""
        return self._generic_setter("IGND", value)

    def ICPL(self, value=None):
        """Kurzform für ICPL-Setzen oder -Abfragen."""
        return self._generic_setter("ICPL", value)

    def ILIN(self, value=None):
        """Kurzform für ILIN-Setzen oder -Abfragen."""
        return self._generic_setter("ILIN", value)

    def SENS(self, value=None):
        """Kurzform für SENS-Setzen oder -Abfragen."""
        return self._generic_setter("SENS", value)

    def RMOD(self, value=None):
        """Kurzform für RMOD-Setzen oder -Abfragen."""
        return self._generic_setter("RMOD", value)

    def OFLT(self, value=None):
        """Kurzform für OFLT-Setzen oder -Abfragen."""
        return self._generic_setter("OFLT", value)

    def OFSL(self, value=None):
        """Kurzform für OFSL-Setzen oder -Abfragen."""
        return self._generic_setter("OFSL", value)

    def SYNC(self, value=None):
        """Kurzform für SYNC-Setzen oder -Abfragen."""
        return self._generic_setter("SYNC", value)

    def DDEF(self, channel=None, value=None, ratio=None):
        """Kurzform für DDEF-Setzen oder -Abfragen."""
        if channel is None:
            return None
        if value is None and ratio is None:
            return self.query_value("DDEF", channel)
        if ratio is None:
            self.write("DDEF", channel, value)
            return self.build_command("DDEF", channel, value)
        self.write("DDEF", channel, value, ratio)
        return self.build_command("DDEF", channel, value, ratio)

    def FPOP(self, channel=None, value=None):
        """Kurzform für FPOP-Setzen oder -Abfragen."""
        if channel is None:
            return None
        if value is None:
            return self.query_value("FPOP", channel)
        self.write("FPOP", channel, value)
        return self.build_command("FPOP", channel, value)

    def OEXP(self, quantity=None, offset=None, expand=None):
        """Kurzform für OEXP-Setzen oder -Abfragen."""
        if quantity is None:
            return None
        if offset is None and expand is None:
            return self.query_value("OEXP", quantity)
        self.write("OEXP", quantity, offset, expand)
        return self.build_command("OEXP", quantity, offset, expand)

    def OUTX(self, value=None):
        """Kurzform für OUTX-Setzen oder -Abfragen."""
        return self._generic_setter("OUTX", value)

    def query(self, command):
        """Sendet einen Befehl und liest die Antwort ein.

        Args:
            command: Vollständiger SR830-Befehl, z. B. "PHAS?" oder "SNAP? 1,2".

        Returns:
            tuple: (antwort, dauer_in_ms)
        """
        start_time = time.perf_counter()
        if not self.ser and not self.simulate:
            latency = (time.perf_counter() - start_time) * 1000
            self._log_transaction("RX", "<not connected>", latency_ms=latency)
            return None, latency

        if self.simulate:
            time.sleep(0.008)
            latency = (time.perf_counter() - start_time) * 1000
            if self.simulator:
                if command == "SNAP? 1,2":
                    reply = self.simulator.get_SR830_SNAP()
                elif command == "PHAS?":
                    reply = self.simulator.get_SR830_PHAS()
                elif command.startswith("PHAS "):
                    reply = "OK"
                elif command.startswith("FREQ "):
                    reply = "OK"
                else:
                    reply = "0"
            else:
                if command == "SNAP? 1,2":
                    reply = "0.00231, -0.00145"
                elif command == "PHAS?":
                    reply = "14.52"
                elif command.startswith("PHAS ") or command.startswith("FREQ "):
                    reply = "OK"
                else:
                    reply = "0"
            self._log_transaction("RX", command, value=reply, latency_ms=latency)
            return reply, latency

        if not self._ensure_connection():
            response = "ERROR: not connected"
            latency = (time.perf_counter() - start_time) * 1000
            self._log_transaction("RX", command, value=response, latency_ms=latency)
            return response, latency

        for attempt in range(2):
            try:
                self._reset_serial_buffers()
                self.ser.write(f"{command}\r\n".encode("utf-8"))
                response = self.ser.readline().decode("utf-8", errors="ignore").strip()
                latency = (time.perf_counter() - start_time) * 1000
                self._log_transaction("RX", command, value=response, latency_ms=latency)
                return response, latency
            except Exception as exc:
                self.disconnect()
                if attempt == 0 and self._ensure_connection():
                    continue
                response = f"ERROR: {exc}"
                latency = (time.perf_counter() - start_time) * 1000
                self._log_transaction("RX", command, value=response, latency_ms=latency)
                return response, latency

    def _send_command(self, command):
        """Interne Hilfsfunktion zum Senden eines Kommandos über die serielle Verbindung."""
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

    # ------------------------------------------------------------------
    # Referenz- und Phasenbefehle
    # ------------------------------------------------------------------

    def set_phase(self, value):
        """Setzt die Referenzphase des SR830.

        Args:
            value: Phase in Grad, z. B. 12.34.

        Example:
            LAM.set_phase(45.0)
        """
        return self.write("PHAS", value)

    def get_phase(self):
        """Fragt die aktuelle Referenzphase ab."""
        return self.query(self.build_command("PHAS", query=True))[0]

    def set_reference_source(self, value):
        """Wählt die Referenzquelle aus: intern oder extern.

        Args:
            value: 1 für intern, 0 für extern.
        """
        return self.write("FMOD", value)

    def get_reference_source(self):
        """Fragt die aktuell verwendete Referenzquelle ab."""
        return self.query(self.build_command("FMOD", query=True))[0]

    def set_reference_frequency(self, value):
        """Setzt die interne Referenzfrequenz in Hertz.

        Args:
            value: Frequenzwert, z. B. 1000 für 1000 Hz.
        """
        return self.write("FREQ", value)

    def get_reference_frequency(self):
        """Fragt die Referenzfrequenz ab."""
        return self.query(self.build_command("FREQ", query=True))[0]

    def set_reference_slope(self, value):
        """Wählt den Trigger-Übergang für externe Referenz ein.

        Args:
            value: 0 = Sinus-Nullstelle, 1 = TTL ansteigend, 2 = TTL fallend.
        """
        return self.write("RSLP", value)

    def get_reference_slope(self):
        """Fragt den Referenz-Triggermodus ab."""
        return self.query(self.build_command("RSLP", query=True))[0]

    def set_harmonic(self, value):
        """Wählt die zu detektierende Harmonische aus."""
        return self.write("HARM", value)

    def get_harmonic(self):
        """Fragt die aktive Harmonische ab."""
        return self.query(self.build_command("HARM", query=True))[0]

    def set_sine_output_level(self, value):
        """Setzt die Amplitude des Referenzsignals."""
        return self.write("SLVL", value)

    def get_sine_output_level(self):
        """Fragt die Referenzamplitude ab."""
        return self.query(self.build_command("SLVL", query=True))[0]

    # ------------------------------------------------------------------
    # Eingang und Filter
    # ------------------------------------------------------------------

    def set_input_source(self, value):
        """Wählt die Signalquelle am Eingang aus.

        Args:
            value: 0=A, 1=A-B, 2=I(1M), 3=I(100M).
        """
        return self.write("ISRC", value)

    def get_input_source(self):
        """Fragt die aktuelle Eingangskonfiguration ab."""
        return self.query(self.build_command("ISRC", query=True))[0]

    def set_input_grounding(self, value):
        """Schaltet die Shield-Grounding-Funktion ein oder aus."""
        return self.write("IGND", value)

    def get_input_grounding(self):
        """Fragt den Shield-Grounding-Status ab."""
        return self.query(self.build_command("IGND", query=True))[0]

    def set_input_coupling(self, value):
        """Wählt AC- oder DC-Kopplung des Eingangs."""
        return self.write("ICPL", value)

    def get_input_coupling(self):
        """Fragt die Eingangskopplung ab."""
        return self.query(self.build_command("ICPL", query=True))[0]

    def set_line_notch(self, value):
        """Aktiviert oder deaktiviert die Netznotch-Filter."""
        return self.write("ILIN", value)

    def get_line_notch(self):
        """Fragt den Zustand der Netznotch-Filter ab."""
        return self.query(self.build_command("ILIN", query=True))[0]

    # ------------------------------------------------------------------
    # Verstärkung und Zeitkonstante
    # ------------------------------------------------------------------

    def set_sensitivity(self, value):
        """Setzt die Empfindlichkeit des Lock-Ins.

        Args:
            value: Integer-Wert aus der SR830-Sensitivitätstabelle.
        """
        return self.write("SENS", value)

    def get_sensitivity(self):
        """Fragt die aktuelle Empfindlichkeit ab."""
        return self.query(self.build_command("SENS", query=True))[0]

    def set_reserve_mode(self, value):
        """Wählt den Reserve-Modus des Verstärkers."""
        return self.write("RMOD", value)

    def get_reserve_mode(self):
        """Fragt den Reserve-Modus ab."""
        return self.query(self.build_command("RMOD", query=True))[0]

    def set_time_constant(self, value):
        """Setzt die Zeitkonstante des Filters."""
        return self.write("OFLT", value)

    def get_time_constant(self):
        """Fragt die aktive Zeitkonstante ab."""
        return self.query(self.build_command("OFLT", query=True))[0]

    def set_filter_slope(self, value):
        """Setzt die Filtersteigung in dB/Oktave."""
        return self.write("OFSL", value)

    def get_filter_slope(self):
        """Fragt die Filtersteigung ab."""
        return self.query(self.build_command("OFSL", query=True))[0]

    def set_synchronous_filter(self, value):
        """Schaltet den synchronen Filter ein oder aus."""
        return self.write("SYNC", value)

    def get_synchronous_filter(self):
        """Fragt den Zustand des synchronen Filters ab."""
        return self.query(self.build_command("SYNC", query=True))[0]

    # ------------------------------------------------------------------
    # Anzeige und Ausgänge
    # ------------------------------------------------------------------

    def set_display(self, channel, value, ratio=None):
        """Wählt die anzeigten Größen auf CH1 oder CH2.

        Args:
            channel: 1 für CH1, 2 für CH2.
            value: Anzeigegröße, z. B. 0 für X, 1 für R.
            ratio: Optionales Verhältnis, z. B. Aux-In 1 oder 2.
        """
        if ratio is None:
            return self.write("DDEF", channel, value)
        return self.write("DDEF", channel, value, ratio)

    def get_display(self, channel):
        """Fragt die aktuell konfigurierte Anzeige für CH1 oder CH2 ab."""
        return self.query(self.build_command("DDEF", channel, query=True))[0]

    def set_front_panel_output(self, channel, value):
        """Wählt die Quelle für den Frontpanel-Ausgang."""
        return self.write("FPOP", channel, value)

    def get_front_panel_output(self, channel):
        """Fragt die Quelle des Frontpanel-Ausgangs ab."""
        return self.query(self.build_command("FPOP", channel, query=True))[0]

    def set_output_offset_expand(self, quantity, offset, expand):
        """Setzt Offset und Expand für X, Y oder R."""
        return self.write("OEXP", quantity, offset, expand)

    def get_output_offset_expand(self, quantity):
        """Fragt Offset und Expand für X, Y oder R ab."""
        return self.query(self.build_command("OEXP", quantity, query=True))[0]

    def auto_offset(self, quantity):
        """Führt den Auto-Offset für X, Y oder R aus."""
        return self.write("AOFF", quantity)

    def get_aux_input(self, channel):
        """Fragt einen Aux-Eingang ab."""
        return self.query(self.build_command("OAUX", channel, query=True))[0]

    def set_aux_output(self, channel, value):
        """Setzt die Spannung eines Aux-Ausgangs."""
        return self.write("AUXV", channel, value)

    # ------------------------------------------------------------------
    # Remote und Status
    # ------------------------------------------------------------------

    def set_output_interface(self, value):
        """Wählt die Ausgabeschnittstelle für Antworten: RS232 oder GPIB."""
        return self.write("OUTX", value)

    def get_output_interface(self):
        """Fragt die aktive Ausgabeschnittstelle ab."""
        return self.query(self.build_command("OUTX", query=True))[0]

    def set_remote_override(self, value):
        """Überschreibt das Remote-Verhalten für den Frontpanel-Zugriff."""
        return self.write("OVRM", value)

    def set_key_click(self, value):
        """Schaltet den Tastenton ein oder aus."""
        return self.write("KCLK", value)

    def get_key_click(self):
        """Fragt den Zustand des Tastentons ab."""
        return self.query(self.build_command("KCLK", query=True))[0]

    def set_alarm(self, value):
        """Schaltet den Alarm ein oder aus."""
        return self.write("ALRM", value)

    def get_alarm(self):
        """Fragt den Alarmzustand ab."""
        return self.query(self.build_command("ALRM", query=True))[0]

    def save_setup(self, buffer_id):
        """Speichert den aktuellen Aufbau in einem internen Setup-Speicher."""
        return self.write("SSET", buffer_id)

    def recall_setup(self, buffer_id):
        """Lädt einen gespeicherten Setup-Speicher wieder."""
        return self.write("RSET", buffer_id)

    def auto_gain(self):
        """Führt die automatische Verstärkungsanpassung aus."""
        return self.write("AGAN")

    def auto_reserve(self):
        """Führt die automatische Reserve-Anpassung aus."""
        return self.write("ARSV")

    def auto_phase(self):
        """Führt die automatische Phasenanpassung aus."""
        return self.write("APHS")

    def reset(self):
        """Setzt das Gerät auf die Standardkonfiguration zurück."""
        return self.write("*RST")

    def identify(self):
        """Fragt die Geräteidentifikation ab."""
        return self.query(self.build_command("*IDN", query=True))[0]

    def local(self, value=0):
        """Schaltet das Gerät zwischen lokal und remote um."""
        return self.write("LOCL", value)

    def status_byte(self):
        """Fragt das Statusbyte des Geräts ab."""
        return self.query(self.build_command("*STB", query=True))[0]

    def event_status(self):
        """Fragt den Event-Status-Register ab."""
        return self.query(self.build_command("*ESR", query=True))[0]

    def error_status(self):
        """Fragt den Fehlerstatus ab."""
        return self.query(self.build_command("ERRS", query=True))[0]

    def lia_status(self):
        """Fragt den Lock-In-Status ab."""
        return self.query(self.build_command("LIAS", query=True))[0]

    # ------------------------------------------------------------------
    # Datenabfrage / Snapshot
    # ------------------------------------------------------------------

    def snapshot(self, *channels):
        """Nimmt einen Snapshot von einem oder mehreren Messwerten.

        Args:
            *channels: Ein oder mehrere Kanalnummern, z. B. 1, 2 oder 1,2,9.

        Example:
            LAM.snapshot(1, 2)
        """
        if not channels:
            channels = (1, 2)
        return self.query(self.build_command("SNAP", *channels, query=True))[0]

    def snapshot_xy(self):
        """Liest die Standardwerte X und Y als Snapshot aus."""
        return self.snapshot(1, 2)


    # ------------------------------------------------------------------
    # LAM-ähnliche High-Level Methoden
    # ------------------------------------------------------------------

    def init(self, phase=None, frequency=None, sensitivity=None, time_constant=None):
        """Führt eine Standard-Initialisierung mit mehreren Basisparametern aus.

        Returns:
            dict: Wörterbuch mit den gesendeten Kommandos und Werten.
        """
        result = {}
        if phase is not None:
            result["phase"] = self.PHAS(phase)
        if frequency is not None:
            result["frequency"] = self.FREQ(frequency)
        if sensitivity is not None:
            result["sensitivity"] = self.SENS(sensitivity)
        if time_constant is not None:
            result["time_constant"] = self.OFLT(time_constant)
        return result

    def configure_reference(self, reference_source=None, frequency=None, phase=None):
        """Konfiguriert Referenzquelle, Frequenz und Phase in einem Schritt."""
        result = {}
        if reference_source is not None:
            result["reference_source"] = self.FMOD(reference_source)
        if frequency is not None:
            result["frequency"] = self.FREQ(frequency)
        if phase is not None:
            result["phase"] = self.PHAS(phase)
        return result

    def configure_input(self, input_source=None, grounding=None, coupling=None, notch=None):
        """Konfiguriert Eingangskanal, Grounding, Kopplung und Notch-Filter."""
        result = {}
        if input_source is not None:
            result["input_source"] = self.ISRC(input_source)
        if grounding is not None:
            result["grounding"] = self.IGND(grounding)
        if coupling is not None:
            result["coupling"] = self.ICPL(coupling)
        if notch is not None:
            result["notch"] = self.ILIN(notch)
        return result

    def configure_filter(self, sensitivity=None, reserve_mode=None, time_constant=None, slope=None, sync_filter=None):
        """Konfiguriert Empfindlichkeit, Reserve, Zeitkonstante und Filter."""
        result = {}
        if sensitivity is not None:
            result["sensitivity"] = self.SENS(sensitivity)
        if reserve_mode is not None:
            result["reserve_mode"] = self.RMOD(reserve_mode)
        if time_constant is not None:
            result["time_constant"] = self.OFLT(time_constant)
        if slope is not None:
            result["filter_slope"] = self.OFSL(slope)
        if sync_filter is not None:
            result["sync_filter"] = self.SYNC(sync_filter)
        return result

    def configure_output(self, display_channel=None, display_value=None, display_ratio=None, frontpanel_channel=None, frontpanel_value=None):
        """Konfiguriert Anzeige und Frontpanel-Ausgänge."""
        result = {}
        if display_channel is not None and display_value is not None:
            result["display"] = self.DDEF(display_channel, display_value, display_ratio)
        if frontpanel_channel is not None and frontpanel_value is not None:
            result["frontpanel_output"] = self.FPOP(frontpanel_channel, frontpanel_value)
        return result

    def configure_custom(self, **kwargs):
        """Freier Platzhalter für eigene Konfigurationen.

        Beispiele:
            LAM.configure_custom(PHAS=45, FREQ=589)
        """
        result = {}
        for name, value in kwargs.items():
            if value is None:
                continue
            if name in {"PHAS", "FMOD", "FREQ", "RSLP", "HARM", "SLVL", "ISRC", "IGND", "ICPL", "ILIN", "SENS", "RMOD", "OFLT", "OFSL", "SYNC", "OUTX"}:
                result[name] = getattr(self, name)(value)
            else:
                result[name] = self.send_command(name, value)
        return result

    def apply_setup(self, **kwargs):
        """Alias für configure_custom()."""
        return self.configure_custom(**kwargs)


__all__ = ["LAM"]

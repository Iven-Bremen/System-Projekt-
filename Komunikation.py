"""Low-level communication layer for SR830 and OSTECH instruments.

This module owns only the protocol-level hardware concerns:
- serial-port opening/closing (each instrument independently)
- lock-protected device access
- wire encoding / decoding
- command execution against the actual instrument
- thread-driven polling and status handling

User-facing command metadata and convenience wrappers live in ``Send.py``.

Wichtige Protokoll-Fakten (aus den Handbuechern), die hier umgesetzt sind:

SR830
  * Vor JEDER Abfrage muss ``OUTX 0`` gesendet werden, sonst antwortet das
    Geraet nicht ueber RS232 (sondern ueber GPIB).
  * Antworten enden mit <CR>, es gibt kein Echo.
  * Reihenfolge der Antworten ist strikt -> vor jeder Abfrage Eingangspuffer leeren.

OSTECH
  * 9600 Baud 8N1, Befehle enden mit <CR>, Zeile max. 14 Zeichen.
  * Das Geraet muss auf "external control" stehen (GXR).
  * Jedes gesendete Zeichen wird als Echo (Grossbuchstaben) zurueckgegeben.
  * Im Binaermodus (GMS8) liefert JEDER Befehl - auch ein Setter - nach dem Echo
    eine binaere Antwort (bool: 1 Byte 0xAA/0x55, word: 2 Byte + Summe,
    float: 4 Byte + Summe).  Diese Antwort MUSS gelesen werden, sonst
    verschiebt sie spaeter alle folgenden Antworten.
  * Der Platzhalter ``x`` in ``xTA`` etc. ist durch die TEC-Nummer zu ersetzen
    (hier: 1).
  * Bool-Befehle werden mit Suffix R (run) bzw. S (stop) gesendet: ``LR``, ``LS``.
"""

import numbers
import struct
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable

import serial
from serial.tools import list_ports

import Log
import State
from Threads import CommunicationThreads, ThreadMessage


DEFAULT_SR830_PORT = "COM3"
DEFAULT_OSTECH_PORT = "COM4"
SR830_PORT = None
OSTECH_PORT = None
BAUDRATE = 9600
TIMEOUT = 2
PROBE_TIMEOUT = 1.5
# Etwas groesser als 1 ms, damit Setter (GUI) zwischen den Poll-Schritten
# zuverlaessig an die Reihe kommen.
DEFAULT_TICK_MS = 20
DEFAULT_CYCLES = None
GUI_INTERVAL_MS = 12
MAX_CONSECUTIVE_ERRORS = 5
OSTECH_MAX_LINE = 14
# Das OSTECH muss fuer RS232-Steuerung auf "external control" stehen.
OSTECH_FORCE_EXTERNAL_CONTROL = True
OSTECH_RELEASE_EXTERNAL_ON_CLOSE = False

# --- Digitaler Zwilling: lesbare Einstellungen ------------------------------
# (Schluessel im Zwilling, Abfrage-Befehl, Datentyp, optionaler State-Name)
# Die Schluessel entsprechen den Befehlsnamen in Send.py (info.command).
SR830_SETTING_QUERIES = (
    ("FMOD", "FMOD?", int, None), ("RSLP", "RSLP?", int, None),
    ("HARM", "HARM?", int, None), ("SLVL", "SLVL?", float, None),
    ("ISRC", "ISRC?", int, None), ("IGND", "IGND?", int, None),
    ("ICPL", "ICPL?", int, None), ("ILIN", "ILIN?", int, None),
    ("SENS", "SENS?", int, None), ("RMOD", "RMOD?", int, None),
    ("OFLT", "OFLT?", int, None), ("OFSL", "OFSL?", int, None),
    ("SYNC", "SYNC?", int, None),
)
OSTECH_SETTING_QUERIES = (
    ("LCL", "LCL", float, None), ("LVC", "LVC", float, None),
    ("LCLM", "LCLM", float, None), ("LCB", "LCB", float, None),
    ("LMW", "LMW", float, None), ("LMP", "LMP", float, None),
    ("LMDIC", "LMDIC", int, None), ("LZTR", "LZTR", float, None),
    ("LTM", "LTM", float, "LTM"),
    ("1TT", "1TT", float, "XTT"), ("1TLU", "1TLU", float, None),
    ("1TLL", "1TLL", float, None), ("1TCL", "1TCL", float, None),
    ("1TCCK", "1TCCK", float, None), ("1TCCN", "1TCCN", float, None),
    ("1TCCV", "1TCCV", float, None),
    ("PP", "PP", int, None), ("GFD", "GFD", float, None),
)
# Schalter, die aus GS/GM (Bits) abgeleitet werden, plus Werte aus dem Dauer-Polling.
SR830_STATE_KEYS = ("PHAS", "FREQ")
OSTECH_STATE_KEYS = ("LCT", "L", "LMDI", "LMDX", "LMAX", "LG", "1TC", "PL")
# Nach einem Setter oder per Knopfdruck: alle Einstellungen sofort neu lesen.
_SETTINGS_REFRESH = {"SR830": threading.Event(), "OSTECH": threading.Event()}

SR830 = None
SR830_ID = None
OSTECH = None
OSTECH_SERIAL_NUMBER = None
LAST_CONNECT_ERROR = {"SR830": "", "OSTECH": ""}
SR830_LOCK = threading.RLock()
OSTECH_LOCK = threading.RLock()
_ACTIVE_COMMUNICATION_THREADS = None


class DeviceNotConnected(RuntimeError):
    """Raised when a worker or caller uses an instrument that is not open."""


def readable_settings(device: str):
    """Names of all settings of ``device`` that the twin can read back."""
    if str(device).upper() == "SR830":
        return {key for key, *_ in SR830_SETTING_QUERIES} | set(SR830_STATE_KEYS)
    return {key for key, *_ in OSTECH_SETTING_QUERIES} | set(OSTECH_STATE_KEYS)


def request_settings_refresh(device=None):
    """Ask the polling loop to read ALL settings of one/both devices at the next opportunity."""
    names = _SETTINGS_REFRESH if device is None else {str(device).upper(): None}
    for name in names:
        if name in _SETTINGS_REFRESH:
            _SETTINGS_REFRESH[name].set()


def get_twin():
    """Consistent copy of the digital twin (measured / settings / desired / compare)."""
    return State.twin_snapshot()


@dataclass(frozen=True)
class OSTECHCommandInfo:
    """Protocol metadata for one OSTECH command."""

    command: str
    data_type: type
    unit: str = ""


@dataclass(frozen=True)
class OSTECHResult:
    """Decoded OSTECH value together with its protocol metadata."""

    value: object
    info: OSTECHCommandInfo

    @property
    def command(self):
        return self.info.command

    @property
    def data_type(self):
        return self.info.data_type

    @property
    def unit(self):
        return self.info.unit

    def __str__(self):
        return str(self.value)


class OSTECHCommand(Enum):
    """Supported OSTECH measurement commands (binary-mode reads).

    ``x`` aus dem Handbuch ist durch ``1`` (erster TEC / Laser-TEC) ersetzt.
    Die Namen (XTA, XTCA ...) bleiben bewusst gleich, weil ``State`` und GUI
    diese Namen verwenden.
    """

    # Regelmaessige Messwerte
    LCT = OSTECHCommandInfo("LCT", float, "mA")
    XTA = OSTECHCommandInfo("1TA", float, "C")
    LVA = OSTECHCommandInfo("LVA", float, "V")
    XTCA = OSTECHCommandInfo("1TCA", float, "mA")
    XTVA = OSTECHCommandInfo("1TVA", float, "V")
    LCA = OSTECHCommandInfo("LCA", float, "mA")
    GT = OSTECHCommandInfo("GT", float, "C")
    GS = OSTECHCommandInfo("GS", int)
    GM = OSTECHCommandInfo("GM", int)
    # Einmalige Startabfragen
    XTT = OSTECHCommandInfo("1TT", float, "C")
    LTM = OSTECHCommandInfo("LTM", float, "C")
    GVN = OSTECHCommandInfo("GVN", int)


# =============================================================================
# Allgemeine Hilfsfunktionen
# =============================================================================

def _fmt_value(value):
    """Format a value compactly (no exponent, no float noise like 0.30000000000000004)."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, numbers.Integral):
        return str(int(value))
    if isinstance(value, numbers.Real):
        text = f"{float(value):.6f}".rstrip("0").rstrip(".")
        return "0" if text in ("", "-0") else text
    return str(value).strip()


def _format_command(command: str, value=None, separator=" "):
    """Build one ASCII command line."""
    command = str(command)
    return command if value is None else f"{command}{separator}{_fmt_value(value)}"


def _convert_response(response: str, return_type):
    """Convert a decoded text response into the requested type."""
    if return_type is None or return_type is str:
        return response
    if return_type is bool:
        normalized = response.strip().lower()
        if normalized in ("1", "true", "on"):
            return True
        if normalized in ("0", "false", "off"):
            return False
        raise ValueError(f"Keine boolesche Antwort: {response!r}")
    if return_type is int:
        try:
            return int(response)
        except ValueError:
            return int(float(response))
    return return_type(response)


def _available_ports():
    """Return current COM ports (fresh scan, startup scan as fallback)."""
    try:
        ports = [port.device for port in list_ports.comports()]
    except Exception:
        ports = []
    ports = ports or list(State.AVAILABLE_COM_PORTS or [])
    return list(dict.fromkeys(port for port in ports if port))


def _port_name(port_obj):
    return getattr(port_obj, "port", None) if port_obj is not None else None


def _candidate_ports(preferred, exclude):
    """Preferred port first, then all other visible ports, without excluded ones."""
    exclude = {str(item).upper() for item in exclude if item}
    result = []
    for port in [preferred] + _available_ports():
        if port and str(port).upper() not in exclude and port not in result:
            result.append(port)
    return result


def _safe_close(port):
    try:
        if port is not None and port.is_open:
            port.close()
    except Exception:
        pass


# =============================================================================
# SR830
# =============================================================================

def _open_sr830(port_name):
    """Open one port, select RS232 output and verify that an SR830 answers."""
    port = serial.Serial(port_name, BAUDRATE, timeout=PROBE_TIMEOUT)
    try:
        time.sleep(0.3)
        port.reset_input_buffer()
        # WICHTIG: ohne OUTX 0 antwortet der SR830 nicht ueber RS232.
        port.write(b"OUTX 0\r")
        port.flush()
        time.sleep(0.1)
        idn = ""
        for _ in range(2):
            port.reset_input_buffer()
            port.write(b"*IDN?\r")
            port.flush()
            idn = port.read_until(b"\r").decode("ascii", errors="replace").strip()
            if idn:
                break
        if "sr830" not in idn.lower():
            raise RuntimeError(f"Keine SR830-Antwort auf *IDN? (erhalten: {idn!r})")
        port.timeout = TIMEOUT
        return port, idn
    except Exception:
        _safe_close(port)
        raise


def connect_sr830(port=None, autodetect=True):
    """Connect the SR830 only (the OSTECH connection is not touched).

    ``port`` is tried first; if it fails and ``autodetect`` is true, all other
    visible ports not used by the OSTECH are probed. Returns the open
    ``serial.Serial`` or ``None`` (reason in ``LAST_CONNECT_ERROR['SR830']``).
    """
    global SR830, SR830_ID, SR830_PORT
    close_device("SR830", stop_loop=False)
    candidates = _candidate_ports(port, [_port_name(OSTECH)])
    if not autodetect:
        candidates = candidates[:1]
    errors = []
    for candidate in candidates:
        try:
            serial_port, idn = _open_sr830(candidate)
        except (serial.SerialException, OSError, RuntimeError) as error:
            errors.append(f"{candidate}: {error}")
            Log.Log("Comm", str(candidate), "Warning", "Try connect", "FAILED", str(error), "SR830")
            continue
        with SR830_LOCK:
            SR830, SR830_ID, SR830_PORT = serial_port, idn, candidate
        State.twin_set_connected("SR830", True)
        LAST_CONNECT_ERROR["SR830"] = ""
        Log.Log("Comm", "SR830", "Info", "Device assigned", idn, candidate)
        return SR830
    LAST_CONNECT_ERROR["SR830"] = "; ".join(errors) or "Keine COM-Ports gefunden."
    return None


def ask_SR830(command, value=None, return_type=None):
    """Send an SR830 command and return the typed response."""
    resolved_command = command.command if hasattr(command, "command") else str(command)
    if return_type is None:
        return_type = getattr(command, "type", None) or str
    line = _format_command(resolved_command, value)
    with SR830_LOCK:
        port = SR830
        if port is None:
            raise DeviceNotConnected("SR830 ist nicht verbunden.")
        port.reset_input_buffer()          # keine alten Antworten mitlesen
        port.write(f"{line}\r".encode("ascii"))
        port.flush()
        raw = port.read_until(b"\r")
    if not raw.endswith(b"\r"):
        raise TimeoutError(f"SR830 antwortet nicht auf {line!r} (Baudrate/Kabel pruefen).")
    return _convert_response(raw.decode("ascii", errors="replace").strip(), return_type)


def send_SR830(command, value=None):
    """Send an SR830 setting/action command (no response expected)."""
    resolved_command = command.command if hasattr(command, "command") else str(command)
    line = _format_command(resolved_command, value)
    with SR830_LOCK:
        port = SR830
        if port is None:
            raise DeviceNotConnected("SR830 ist nicht verbunden.")
        port.write(f"{line}\r".encode("ascii"))
        port.flush()


# =============================================================================
# OSTECH
# =============================================================================

def _ostech_line(command, value=None):
    """Build an OSTECH line (no space, <= 14 characters as required by the manual)."""
    line = _format_command(command, value, separator="")
    if len(line) > OSTECH_MAX_LINE:
        raise ValueError(f"OSTECH-Befehl zu lang ({len(line)} > {OSTECH_MAX_LINE}): {line!r}")
    return line


def _ostech_reply_type(command, return_type=None):
    """Binary reply type of a command (bool for run/stop commands)."""
    if return_type in (bool, int, float, str):
        return return_type
    meta_type = getattr(command, "type", None)
    if meta_type in (bool, int, float, str):
        return meta_type
    meta_type = getattr(command, "data_type", None)
    if meta_type in (bool, int, float, str):
        return meta_type
    return bool


def _ostech_enter_text_mode(port):
    """Bring a possibly still-binary OSTECH back to text mode and enable RS232 control."""
    port.write(b"\x1b")                     # Esc: angefangene Eingabe verwerfen
    port.flush()
    time.sleep(0.05)
    if OSTECH_FORCE_EXTERNAL_CONTROL:
        port.write(b"GXR\r")
        port.flush()
        time.sleep(0.3)
    port.write(b"GMC8\r")                   # Binaermodus aus (ggf. noch von frueher aktiv)
    port.flush()
    time.sleep(0.3)
    port.reset_input_buffer()


def _ostech_exchange(port, command: str, data_type: type, strict=True):
    """Send one command in binary mode and decode echo + payload.

    Caller must hold ``OSTECH_LOCK``. With ``strict=False`` (setters) a
    missing/short payload is tolerated, only a wrong echo raises.
    """
    port.reset_input_buffer()
    port.write(f"{command}\r".encode("ascii"))
    port.flush()
    echo = port.read_until(b"\r")
    expected_echo = f"{command.upper()}\r".encode("ascii")
    if echo != expected_echo:
        port.reset_input_buffer()
        raise RuntimeError(f"Unerwartetes Echo: erwartet {expected_echo!r}, erhalten {echo!r}")

    if data_type is str:
        payload = port.read_until(b"\x00")
        if not payload.endswith(b"\x00"):
            if strict:
                raise RuntimeError("OSTECH-String-Antwort unvollstaendig.")
            return None
        return payload[:-1].decode("ascii", errors="replace")

    if data_type is bool:
        response = port.read(1)
        if response not in (b"\xAA", b"\x55"):
            if strict:
                raise RuntimeError(f"Ungueltige bool-Antwort: {response!r}")
            return None
        return response == b"\xAA"

    payload_length = 2 if data_type is int else 4 if data_type is float else 0
    if not payload_length:
        raise TypeError("data_type muss bool, int, float oder str sein.")
    response = port.read(payload_length + 1)
    if len(response) != payload_length + 1:
        if strict:
            raise RuntimeError("OSTECH-Antwort ist zu kurz.")
        return None
    checksum = (0x55 + sum(response[:payload_length])) % 256
    if response[payload_length] != checksum:
        if strict:
            raise RuntimeError("Ungueltige OSTECH-Pruefsumme.")
        return None
    return struct.unpack(">H" if data_type is int else ">f", response[:payload_length])[0]


def _open_ostech(port_name):
    """Open one port, run the text-mode handshake and switch to binary mode."""
    port = serial.Serial(port_name, BAUDRATE, timeout=PROBE_TIMEOUT)
    try:
        time.sleep(0.3)
        _ostech_enter_text_mode(port)
        port.write(b"GVN\r")
        port.flush()
        echo = port.read_until(b"\r")
        if echo.strip().upper() != b"GVN":
            raise RuntimeError(f"Kein OSTECH-Echo auf GVN (erhalten: {echo!r})")
        serial_number = port.read_until(b"\r").decode("ascii", errors="replace").strip()
        if not serial_number:
            raise RuntimeError("Keine Antwort auf GVN erhalten.")
        # Binaermodus einschalten. GMS8 ist ein Setter ohne Rueckgabewert im Textmodus:
        # nur das Echo wird erwartet, Rest wird verworfen.
        port.write(b"GMS8\r")
        port.flush()
        echo = port.read_until(b"\r")
        if echo.strip().upper() != b"GMS8":
            raise RuntimeError(f"Unerwartetes GMS8-Echo: {echo!r}")
        time.sleep(0.3)
        port.reset_input_buffer()
        port.timeout = TIMEOUT
        # Pruefen, dass der Binaermodus wirklich aktiv ist (Status-Wort + Pruefsumme).
        _ostech_exchange(port, "GS", int)
        return port, serial_number
    except Exception:
        _safe_close(port)
        raise


def connect_ostech(port=None, autodetect=True):
    """Connect the OSTECH only (the SR830 connection is not touched)."""
    global OSTECH, OSTECH_SERIAL_NUMBER, OSTECH_PORT
    close_device("OSTECH", stop_loop=False)
    candidates = _candidate_ports(port, [_port_name(SR830)])
    if not autodetect:
        candidates = candidates[:1]
    errors = []
    for candidate in candidates:
        try:
            serial_port, serial_number = _open_ostech(candidate)
        except (serial.SerialException, OSError, RuntimeError) as error:
            errors.append(f"{candidate}: {error}")
            Log.Log("Comm", str(candidate), "Warning", "Try connect", "FAILED", str(error), "OSTECH")
            continue
        with OSTECH_LOCK:
            OSTECH, OSTECH_SERIAL_NUMBER, OSTECH_PORT = serial_port, serial_number, candidate
        State.twin_set_connected("OSTECH", True)
        LAST_CONNECT_ERROR["OSTECH"] = ""
        Log.Log("Comm", "OSTECH", "Info", "Device assigned", serial_number, candidate)
        return OSTECH
    LAST_CONNECT_ERROR["OSTECH"] = "; ".join(errors) or "Keine COM-Ports gefunden."
    return None


def ask_OSTECH(command, value=None, return_type=None):
    """Read (or query a setting of) the OSTECH in binary mode and return a typed value."""
    resolved_command = command.command if hasattr(command, "command") else str(command)
    if return_type is None and not hasattr(command, "type"):
        for known in OSTECHCommand:
            if known.value.command.upper() == resolved_command.upper():
                return_type = known.value.data_type
                break
    reply_type = _ostech_reply_type(command, return_type)
    line = _ostech_line(resolved_command, value)
    with OSTECH_LOCK:
        port = OSTECH
        if port is None:
            raise DeviceNotConnected("OSTECH ist nicht verbunden.")
        return _ostech_exchange(port, line, reply_type, strict=True)


def ask_OSTech(command, value=None, return_type=None):
    """Compatibility alias."""
    return ask_OSTECH(command, value=value, return_type=return_type)


def send_OSTECH(command, value=None, return_type=None):
    """Send an OSTECH setter/action and consume its binary reply.

    ``command`` is the final wire command (for bool switches already with the
    R/S suffix, e.g. ``LR``). The reply is read and discarded (returned for
    logging), so it can never shift the answers of later queries.
    """
    resolved_command = command.command if hasattr(command, "command") else str(command)
    reply_type = _ostech_reply_type(command, return_type)
    line = _ostech_line(resolved_command, value)
    with OSTECH_LOCK:
        port = OSTECH
        if port is None:
            raise DeviceNotConnected("OSTECH ist nicht verbunden.")
        result = _ostech_exchange(port, line, reply_type, strict=False)
        time.sleep(0.02)
        port.reset_input_buffer()
    Log.Log("Comm", "OSTECH", "Info", line, "" if result is None else result, "setter reply")
    return result


def send_OSTech(command, value=None, return_type=None):
    """Compatibility alias."""
    return send_OSTECH(command, value=value, return_type=return_type)


def send_ostech_command(command: str):
    """Compatibility helper: send a raw OSTECH line and consume the reply."""
    return send_OSTECH(command, None)


def query_ostech_text(command: str):
    """Read one OSTECH command while the device is still in text mode."""
    with OSTECH_LOCK:
        port = OSTECH
        if port is None:
            raise DeviceNotConnected("OSTECH ist nicht verbunden.")
        port.reset_input_buffer()
        port.write(f"{command}\r".encode("ascii"))
        port.flush()
        echo = port.read_until(b"\r")
        if echo != f"{command.upper()}\r".encode("ascii"):
            raise RuntimeError(f"Unerwartetes {command}-Echo: {echo!r}")
        response = port.read_until(b"\r")
        if not response:
            raise RuntimeError(f"Keine Antwort auf {command} erhalten.")
        return response.decode("ascii", errors="replace").strip()


def set_ostech_binary_mode():
    """Switch an already open OSTECH to binary mode (GMS8) and verify it."""
    with OSTECH_LOCK:
        port = OSTECH
        if port is None:
            raise DeviceNotConnected("OSTECH ist nicht verbunden.")
        port.reset_input_buffer()
        port.write(b"GMS8\r")
        port.flush()
        echo = port.read_until(b"\r")
        if echo.strip().upper() != b"GMS8":
            raise RuntimeError(f"Unerwartetes GMS8-Echo: {echo!r}")
        time.sleep(0.3)
        port.reset_input_buffer()
        _ostech_exchange(port, "GS", int)


def LabOSTECH(port, command: str, data_type: type):
    """Execute one binary-mode OSTECH read command and validate its frame."""
    with OSTECH_LOCK:
        if port is None:
            raise DeviceNotConnected("OSTECH ist nicht verbunden.")
        return _ostech_exchange(port, command, data_type, strict=True)


def decode_ostech_status(status_word: int):
    """Translate the OSTECH ``GS`` bit field into named boolean conditions."""
    masks = {
        "interlock_ok": 0x0001,
        "driver_supply_ok": 0x0004,
        "driver_temperature_ok": 0x0008,
        "ltlu_not_ok": 0x0010,
        "ltll_not_ok": 0x0020,
        "ctlu_not_ok": 0x0040,
        "ctll_not_ok": 0x0080,
        "lt_sensor_ok": 0x0400,
        "ct_sensor_ok": 0x0800,
        "ltm_not_ok": 0x2000,
        "lc_on": 0x4000,
        "lc_error": 0x8000,
    }
    return {"status_word": status_word, **{name: bool(status_word & mask) for name, mask in masks.items()}}


def LabOSTECHCommand(port, command: OSTECHCommand):
    """Execute an enum command, decode it, and publish it to ``State``."""
    info = command.value
    value = LabOSTECH(port, info.command, info.data_type)
    if command is OSTECHCommand.GS:
        value = decode_ostech_status(value)
        State.update_values({"GS": value, "OSTECH_STATUS": value, "L": value["lc_on"]})
        State.twin_update_settings("OSTECH", {"L": value["lc_on"]})
    elif command is OSTECHCommand.GM:
        # Modus-Bits laut Handbuch 9.3.2
        State.update_values({"LMDX": bool(value & 0x0040)})
        State.twin_update_settings("OSTECH", {
            "LMDI": bool(value & 0x0020),
            "LMDX": bool(value & 0x0040),
            "LMAX": bool(value & 0x0080),
            "1TC": bool(value & 0x0100),
            "PL": bool(value & 0x0400),
            "LG": bool(value & 0x4000),
        })
    else:
        State.update_values({command.name: value})
        if command is OSTECHCommand.LCT:
            State.twin_update_settings("OSTECH", {"LCT": value})
    return OSTECHResult(value, info)


def close_device(device_name: str, stop_loop=True):
    """Close exactly one instrument (thread-safe)."""
    global SR830, OSTECH, SR830_ID, OSTECH_SERIAL_NUMBER, SR830_PORT, OSTECH_PORT
    device_name = str(device_name).upper()

    if device_name in {"SR830", "LOCKIN", "LOCK-IN"}:
        with SR830_LOCK:
            port, SR830, SR830_ID, SR830_PORT = SR830, None, None, None
        _safe_close(port)
        State.twin_set_connected("SR830", False)
    elif device_name in {"OSTECH", "LASER", "OSTECH LASER"}:
        with OSTECH_LOCK:
            port, OSTECH, OSTECH_SERIAL_NUMBER, OSTECH_PORT = OSTECH, None, None, None
            if port is not None and port.is_open:
                try:
                    # Geraet wieder in den Textmodus, damit ein Neustart / Terminal funktioniert.
                    port.write(b"GMC8\r")
                    port.flush()
                    time.sleep(0.2)
                    if OSTECH_RELEASE_EXTERNAL_ON_CLOSE:
                        port.write(b"GXS\r")
                        port.flush()
                        time.sleep(0.2)
                except Exception:
                    pass
        _safe_close(port)
        State.twin_set_connected("OSTECH", False)
    else:
        raise ValueError(f"Unbekanntes Geraet: {device_name}")

    if stop_loop and SR830 is None and OSTECH is None:
        stop_communication_loop()
    return True


def close_devices():
    """Close every currently open instrument without raising on missing ports."""
    for device_name in ("SR830", "OSTECH"):
        try:
            close_device(device_name, stop_loop=False)
        except ValueError:
            pass
    stop_communication_loop()


def open_devices(sr830_port=None, ostech_port=None):
    """Connect instruments (compatibility wrapper).

    * only ``sr830_port`` given -> only the SR830 is (re)connected
    * only ``ostech_port`` given -> only the OSTECH is (re)connected
    * both ``None`` -> both are auto-detected
    A connection that is not requested is left untouched.
    """
    if sr830_port is None and ostech_port is None:
        connect_sr830(None)
        connect_ostech(None)
    else:
        if sr830_port is not None:
            connect_sr830(sr830_port)
        if ostech_port is not None:
            connect_ostech(ostech_port)
    return SR830, OSTECH


def CheckCOM(COM, ID, Command, returnvalue):
    """Check one COM port for the given instrument; the port is closed afterwards."""
    if not COM:
        Log.Log("Comm", ID, "Warning", f"Try connect: {COM}", "FAILED", Command)
        return False
    try:
        port, response = _open_sr830(COM) if ID == "SR830" else _open_ostech(COM)
    except (serial.SerialException, OSError, RuntimeError, TypeError) as error:
        Log.Log("Comm", str(COM), "Warning", "Try connect", "FAILED", str(error), ID)
        return False
    try:
        if ID != "SR830":
            port.write(b"GMC8\r")
            port.flush()
            time.sleep(0.2)
    finally:
        _safe_close(port)
    valid = returnvalue is None or response == str(returnvalue)
    Log.Log("Comm", str(COM), "Info" if valid else "Warning", "Try connect",
            "SUCCESS" if valid else "FAILED", f"{Command} -> {response}", ID)
    return valid


# =============================================================================
# Kommunikations-Threads
# =============================================================================

def stop_communication_loop():
    """Stop the active communication pipeline if one is running."""
    global _ACTIVE_COMMUNICATION_THREADS
    threads = _ACTIVE_COMMUNICATION_THREADS
    _ACTIVE_COMMUNICATION_THREADS = None
    if threads is not None:
        threads.stop()
        return True
    return False


def start_communication_loop(*, tick_ms=DEFAULT_TICK_MS, cycles=DEFAULT_CYCLES, gui_handler=None, **kwargs):
    """Start or reuse the global communication pipeline for the currently open devices."""
    global _ACTIVE_COMMUNICATION_THREADS
    if _ACTIVE_COMMUNICATION_THREADS is not None:
        running = []
        if getattr(_ACTIVE_COMMUNICATION_THREADS, "sr830", None) is not None:
            running.append(_ACTIVE_COMMUNICATION_THREADS.sr830.thread.is_alive())
        if getattr(_ACTIVE_COMMUNICATION_THREADS, "ostech", None) is not None:
            running.append(_ACTIVE_COMMUNICATION_THREADS.ostech.thread.is_alive())
        if any(running):
            return _ACTIVE_COMMUNICATION_THREADS
        stop_communication_loop()

    if SR830 is None and OSTECH is None:
        raise RuntimeError("Es gibt keine verbundenen Geraete fuer die Kommunikation.")

    _ACTIVE_COMMUNICATION_THREADS = start_threaded_measurement(
        tick_ms=tick_ms,
        cycles=cycles,
        gui_handler=gui_handler,
        sr830_enabled=SR830 is not None,
        ostech_enabled=OSTECH is not None,
        **kwargs,
    )
    return _ACTIVE_COMMUNICATION_THREADS


def _device_steps():
    """Build the polling actions for SR830 and OSTECH workers."""
    def read_snap(commands, names):
        response = ask_SR830(f"SNAP? {commands}", return_type=str)
        values = [float(value.strip()) for value in response.split(",")]
        if len(values) != len(names):
            raise ValueError(f"Unerwartete SNAP-Antwort fuer {commands}: {response!r}")
        State.update_values(dict(zip(names, values)))
        return response

    def read_value(command, name):
        value = float(ask_SR830(command, return_type=str))
        State.update_values({name: value})
        State.twin_update_settings("SR830", {name: value})
        return value

    def sr830_setting(key, query, data_type):
        def action():
            value = ask_SR830(query, return_type=data_type)
            State.twin_update_settings("SR830", {key: value})
            return value
        return action

    def ostech_setting(key, query, data_type, state_name):
        def action():
            value = ask_OSTECH(query, return_type=data_type)
            State.twin_update_settings("OSTECH", {key: value})
            if state_name:
                State.update_values({state_name: value})
            return value
        return action

    sr830_steps = (
        ("SNAP 1,2,3,4,10,11", lambda: read_snap(
            "1,2,3,4,10,11",
            ("OUTP1", "OUTP2", "OUTP3", "OUTP4", "CH1_DISPLAY", "CH2_DISPLAY"),
        )),
        ("SNAP 5,6,7,8,9", lambda: read_snap(
            "5,6,7,8,9",
            ("OAUX1", "OAUX2", "OAUX3", "OAUX4", "REFERENCE_FREQUENCY"),
        )),
        ("PHAS", lambda: read_value("PHAS?", "PHAS")),
        ("FREQ", lambda: read_value("FREQ?", "FREQ")),
    )

    def ostech_steps(commands):
        return tuple(
            (command.name, lambda command=command: LabOSTECHCommand(OSTECH, command))
            for command in commands
        )

    ostech_periodic_steps = ostech_steps((
        OSTECHCommand.LCT,
        OSTECHCommand.XTA,
        OSTECHCommand.LVA,
        OSTECHCommand.XTCA,
        OSTECHCommand.XTVA,
        OSTECHCommand.LCA,
        OSTECHCommand.GT,
        OSTECHCommand.GS,
        OSTECHCommand.GM,
    ))
    ostech_startup_steps = ostech_steps((
        OSTECHCommand.GVN,
    ))
    sr830_settings_steps = tuple(
        (f"set {key}", sr830_setting(key, query, data_type))
        for key, query, data_type, _ in SR830_SETTING_QUERIES
    )
    ostech_settings_steps = tuple(
        (f"set {key}", ostech_setting(key, query, data_type, state_name))
        for key, query, data_type, state_name in OSTECH_SETTING_QUERIES
    )
    return (sr830_steps, ostech_periodic_steps, ostech_startup_steps,
            sr830_settings_steps, ostech_settings_steps)


def _resync(source):
    """Throw away stale bytes after a failed exchange."""
    try:
        if source == "SR830":
            with SR830_LOCK:
                if SR830 is not None:
                    SR830.reset_input_buffer()
        else:
            with OSTECH_LOCK:
                if OSTECH is not None:
                    OSTECH.reset_input_buffer()
    except Exception:
        pass


def _is_connected(source):
    return SR830 is not None if source == "SR830" else OSTECH is not None


def _run_device(source, steps, tick_ms, cycles, stop_requested, publish,
                startup_steps=(), settings_steps=()):
    """Execute one device's polling sequence until completion or stop.

    A single failed exchange no longer ends the loop: the input buffer is
    flushed and polling continues. Only a lost port or
    ``MAX_CONSECUTIVE_ERRORS`` failures in a row stop this device's loop.
    """
    if not _is_connected(source):
        publish({"step": "startup", "value": f"{source} ist nicht verbunden."})
        return

    errors = 0

    def run_step(name, action):
        """Return False when the loop must end."""
        nonlocal errors
        try:
            publish({"step": name, "value": action()})
            errors = 0
            return True
        except DeviceNotConnected:
            return False
        except (serial.SerialException, OSError) as error:
            publish({"step": "error", "value": f"{name}: Port verloren: {error}"})
            return False
        except Exception as error:
            errors += 1
            publish({"step": "error", "value": f"{name}: {type(error).__name__}: {error}"})
            _resync(source)
            if errors >= MAX_CONSECUTIVE_ERRORS:
                publish({"step": "error", "value": f"{source}: {errors} Fehler in Folge, Abfrage gestoppt."})
                return False
            return True

    for name, action in startup_steps:
        if stop_requested.is_set() or not run_step(name, action):
            if stop_requested.is_set():
                return
            break
        if stop_requested.wait(tick_ms / 1000):
            return

    refresh_event = _SETTINGS_REFRESH[source]
    unreadable = {}            # Einstellung -> Anzahl Fehlversuche
    round_robin = 0

    def run_settings(batch):
        """Read settings for the twin. Unsupported ones are disabled after 2 failures."""
        for name, action in batch:
            if stop_requested.is_set():
                return True
            if unreadable.get(name, 0) >= 2:
                continue
            try:
                publish({"step": name, "value": action()})
                unreadable[name] = 0
            except DeviceNotConnected:
                return False
            except (serial.SerialException, OSError) as error:
                publish({"step": "error", "value": f"{name}: Port verloren: {error}"})
                return False
            except Exception as error:
                unreadable[name] = unreadable.get(name, 0) + 1
                _resync(source)
                if unreadable[name] >= 2:
                    publish({"step": "error", "value":
                             f"{source} {name}: nicht lesbar, wird nicht mehr abgefragt ({error})"})
            if stop_requested.wait(tick_ms / 1000):
                return True
        return True

    cycle = 0
    while cycles is None or cycle < cycles:
        for name, action in steps:
            if stop_requested.is_set():
                return
            if not run_step(name, action):
                return
            if stop_requested.wait(tick_ms / 1000):
                return
        if settings_steps:
            if refresh_event.is_set():
                refresh_event.clear()
                batch = settings_steps                          # alles sofort neu lesen
            else:
                batch = (settings_steps[round_robin % len(settings_steps)],)
                round_robin += 1                                # sonst: reihum eine Einstellung
            if not run_settings(batch):
                return
        cycle += 1


def _device_status_is_ready(publish):
    """Query the connected instruments and report whether command execution may start."""
    if SR830 is None and OSTECH is None:
        return False
    try:
        ready = True
        if SR830 is not None:
            sr830_id = SR830_ID or ask_SR830("*IDN?", return_type=str)
            publish({"tag": "SR830", "command": "*IDN?", "value": sr830_id, "info": "readiness check"})
            ready = ready and bool(sr830_id)
        if OSTECH is not None:
            status = LabOSTECHCommand(OSTECH, OSTECHCommand.GS).value
            publish({"tag": "OSTECH", "command": OSTECHCommand.GS.value.command,
                     "value": status, "info": "readiness check"})
            serial_number = LabOSTECHCommand(OSTECH, OSTECHCommand.GVN).value
            publish({"tag": "OSTECH", "command": OSTECHCommand.GVN.value.command,
                     "value": serial_number, "info": "readiness check; serial number"})
            ready = ready and not status.get("lc_error", False)
        return ready
    except Exception as error:
        publish({"step": "error", "value": f"{type(error).__name__}: {error}", "info": "readiness check"})
        return False


def _run_commands(command_queries, command_steps, stop_commands, interval_seconds, stop_requested, publish):
    """Run readiness checks, user commands, and shutdown commands in order."""
    if not (command_queries or command_steps or stop_commands):
        # Nichts zu tun: keine zusaetzlichen Seriell-Abfragen neben dem Polling.
        stop_requested.wait()
        return
    while not stop_requested.is_set() and not _device_status_is_ready(publish):
        stop_requested.wait(interval_seconds)
    if stop_requested.is_set():
        return

    for name, action in command_queries:
        if stop_requested.is_set():
            return
        try:
            publish({"step": f"query {name}", "value": action()})
        except Exception as error:
            publish({"step": "error", "value": f"query {name}: {type(error).__name__}: {error}"})

    for name, action in command_steps:
        if stop_requested.is_set():
            return
        try:
            publish({"step": name, "value": action()})
        except Exception as error:
            publish({"step": "error", "value": f"{name}: {type(error).__name__}: {error}"})

    stop_requested.wait()
    for name, action in stop_commands:
        try:
            publish({"step": f"stop {name}", "value": action()})
        except Exception as error:
            publish({"step": "error", "value": f"stop {name}: {type(error).__name__}: {error}"})


def start_threaded_measurement(
    tick_ms=DEFAULT_TICK_MS,
    cycles=DEFAULT_CYCLES,
    gui_handler: Callable[[ThreadMessage], None] | None = None,
    sr830_tick_ms=None,
    ostech_tick_ms=None,
    sr830_cycles=None,
    ostech_cycles=None,
    command_interval_seconds=1,
    command_queries=None,
    command_steps=None,
    stop_commands=None,
    sr830_enabled=None,
    ostech_enabled=None,
):
    """Create and start the communication pipeline.

    ``sr830_enabled`` / ``ostech_enabled`` default to ``None`` = automatically
    "enabled if the instrument is currently connected".
    """
    if sr830_enabled is None:
        sr830_enabled = SR830 is not None
    if ostech_enabled is None:
        ostech_enabled = OSTECH is not None
    sr830_tick_ms = tick_ms if sr830_tick_ms is None else sr830_tick_ms
    ostech_tick_ms = tick_ms if ostech_tick_ms is None else ostech_tick_ms
    sr830_cycles = cycles if sr830_cycles is None else sr830_cycles
    ostech_cycles = cycles if ostech_cycles is None else ostech_cycles
    if sr830_tick_ms <= 0 or ostech_tick_ms <= 0:
        raise ValueError("Die Geraete-Takte muessen groesser als 0 sein.")
    if sr830_cycles is not None and sr830_cycles <= 0:
        raise ValueError("sr830_cycles muss groesser als 0 oder None sein.")
    if ostech_cycles is not None and ostech_cycles <= 0:
        raise ValueError("ostech_cycles muss groesser als 0 oder None sein.")
    if command_interval_seconds <= 0:
        raise ValueError("command_interval_seconds muss groesser als 0 sein.")
    (sr830_steps, ostech_periodic_steps, ostech_startup_steps,
     sr830_settings_steps, ostech_settings_steps) = _device_steps()
    request_settings_refresh()          # beim Start einmal alle Einstellungen einlesen
    command_queries = () if command_queries is None else tuple(command_queries)
    command_steps = () if command_steps is None else tuple(command_steps)
    stop_commands = () if stop_commands is None else tuple(stop_commands)

    def log_handler(message: ThreadMessage):
        payload = message.value if isinstance(message.value, dict) else {"value": message.value}
        if message.kind == "error" or payload.get("step") == "error":
            Log.Log(
                "Comm",
                payload.get("tag", message.source),
                "Error",
                payload.get("command", "error"),
                payload.get("value", ""),
                payload.get("info", "communication error"),
            )
            return

        value = payload.get("value", "")
        command = payload.get("command", payload.get("step", message.kind))
        tag = payload.get("tag", message.source)
        info = payload.get("info", "periodic query")
        if isinstance(value, OSTECHResult):
            command = value.command
            info = value.unit or info
            value = value.value
        Log.Log("Comm", tag, "Running", command, value, info)

    def default_gui_handler(message: ThreadMessage):
        return

    threads = CommunicationThreads(
        lambda stop, publish: _run_device(
            "SR830", sr830_steps, sr830_tick_ms, sr830_cycles, stop, publish,
            settings_steps=sr830_settings_steps,
        ) if sr830_enabled else None,
        lambda stop, publish: _run_device(
            "OSTECH", ostech_periodic_steps, ostech_tick_ms, ostech_cycles, stop, publish,
            startup_steps=ostech_startup_steps, settings_steps=ostech_settings_steps,
        ) if ostech_enabled else None,
        log_handler,
        gui_handler or default_gui_handler,
        # Ohne echten Handler darf der GUI-Thread nicht 12 ms pro Nachricht warten,
        # sonst waechst die Queue bei ~80+ Nachrichten/s unbegrenzt.
        gui_interval_ms=GUI_INTERVAL_MS if gui_handler else 0,
        command_runner=lambda stop, publish: _run_commands(
            command_queries, command_steps, stop_commands,
            command_interval_seconds, stop, publish,
        ),
        sr830_enabled=sr830_enabled,
        ostech_enabled=ostech_enabled,
    )
    threads.start()
    return threads


def run_threaded_measurement(tick_ms=DEFAULT_TICK_MS, cycles=DEFAULT_CYCLES, **options):
    """Run a measurement synchronously while its internal work is threaded."""
    threads = start_threaded_measurement(tick_ms, cycles, **options)

    def alive():
        return any(
            getattr(getattr(threads, name, None), "thread", None) is not None
            and getattr(threads, name).thread.is_alive()
            for name in ("sr830", "ostech")
        )

    try:
        while alive():
            time.sleep(0.05)
    finally:
        threads.stop()


if __name__ == "__main__":
    try:
        open_devices()
        run_threaded_measurement()
    finally:
        close_devices()

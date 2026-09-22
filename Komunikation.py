"""Low-level communication layer for SR830 and OSTECH instruments.

This module owns only the protocol-neutral hardware concerns:
- serial-port opening/closing
- lock-protected device access
- wire encoding / decoding
- command execution against the actual instrument
- thread-driven polling and status handling

User-facing command metadata, convenience wrappers, and command selection live
in ``Send.py``. The point of this split is that the rest of the application
works with typed commands and metadata, while the communication layer stays
responsible for the actual byte-level interaction with the hardware.
"""

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
SR830_PORT = DEFAULT_SR830_PORT
OSTECH_PORT = DEFAULT_OSTECH_PORT
BAUDRATE = 9600
TIMEOUT = 2
DEFAULT_TICK_MS = 1
DEFAULT_CYCLES = None
GUI_INTERVAL_MS = 12
TEST_TAG = "Kommunikations-Test fuer SR830 und OSTECH"

SR830 = None
SR830_ID = None
OSTECH = None
OSTECH_SERIAL_NUMBER = None
SR830_LOCK = threading.Lock()
OSTECH_LOCK = threading.Lock()


@dataclass(frozen=True)
class OSTECHCommandInfo:
    """Protocol metadata for one OSTECH command.

    ``command`` is the wire-level command, ``data_type`` selects the binary
    decoder, and ``unit`` describes the engineering unit for displays and
    logs. Keeping this metadata beside the enum avoids duplicated command
    strings and conversion rules.
    """

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
    """Complete set of supported OSTECH measurement and control commands.

    Periodic measurements are polled by the OSTECH device thread. Startup and
    user-intent commands are executed by the command workflow. The enum value
    is an ``OSTECHCommandInfo`` object, not the decoded measurement itself.
    """

    # Regelmaessige Messwerte
    LCT = OSTECHCommandInfo("LCT", float, "mA")
    XTA = OSTECHCommandInfo("xTA", float, "C")
    LVA = OSTECHCommandInfo("LVA", float, "V")
    XTCA = OSTECHCommandInfo("xTCA", float, "mA")
    XTVA = OSTECHCommandInfo("xTVA", float, "V")
    LCA = OSTECHCommandInfo("LCA", float, "mA")
    # Einmalige Startabfragen
   
    XTT = OSTECHCommandInfo("xTT", float, "C")
    LTM = OSTECHCommandInfo("LTM", float, "C")
    GT = OSTECHCommandInfo("GT", float, "C")
    GS = OSTECHCommandInfo("GS", int)
    GVN = OSTECHCommandInfo("GVN", int)


def CheckCOM(COM, ID, Command, returnvalue):
    """Prueft einen COM-Port und gibt bei jedem Fehler ``False`` zurueck.

    ``ID`` beschreibt das erwartete Geraet fuer die Diagnose. Wenn
    ``returnvalue`` nicht ``None`` ist, muss die Antwort genau diesem Wert
    entsprechen. Der Port wird nur fuer die Pruefung geoeffnet und danach
    wieder geschlossen.
    """
    port = None
    if not COM:
        Log.Log("Comm", ID, "Warning", f"Try connect: {COM}", "FAILED", Command)
        return False
    try:
        port = serial.Serial(COM, BAUDRATE, timeout=TIMEOUT)
        port.write(f"{Command}\r".encode("ascii"))
        port.flush()
        response = port.read_until(b"\r").decode("ascii", errors="replace").strip()
        if response.upper() == str(Command).upper():
            response = port.read_until(b"\r").decode("ascii", errors="replace").strip()
        normalized = response.lower()
        if ID == "SR830":
            identified = "sr830" in normalized or "stanford" in normalized
        else:
            identified = bool(response) and normalized not in {"?", "error", "err", "-1"}
        valid = identified and (returnvalue is None or response == str(returnvalue))
        Log.Log(
            "Comm", str(COM), "Info" if valid else "Warning", "Try connect",
            "SUCCESS" if valid else "FAILED", f"{Command} -> {response}", ID,
        )
        return valid
    except (serial.SerialException, OSError, UnicodeError, TypeError) as error:
        Log.Log("Comm", str(COM), "Warning", "Try connect", "FAILED", str(error), ID)
        return False
    finally:
        if port is not None and port.is_open:
            port.close()


def _available_ports():
    """Return current COM ports, preferring the startup scan when available."""
    ports = State.AVAILABLE_COM_PORTS or [
        port.device for port in list_ports.comports()
    ]
    return list(dict.fromkeys(port for port in ports if port))


def _find_device_ports(ports):
    """Identify both instruments by their protocol responses."""
    found = {}
    for port in ports:
        if len(found) == 2:
            break
        if "SR830" not in found and CheckCOM(port, "SR830", "*IDN?", None):
            found["SR830"] = port
            continue
        if "OSTECH" not in found and CheckCOM(port, "OSTECH", "GVN", None):
            found["OSTECH"] = port
    return found


def open_devices(sr830_port=None, ostech_port=None):
    """Probe and open both instruments independently.

    Each port is checked separately. A failed SR830 connection therefore does
    not prevent an available OSTECH from being opened, and vice versa. OSTECH is
    left in binary mode after its text-mode startup handshake; the returned
    objects are later consumed by the dedicated communication threads.
    """
    global SR830, SR830_ID, OSTECH, OSTECH_SERIAL_NUMBER, SR830_PORT, OSTECH_PORT
    SR830 = None
    SR830_ID = None
    OSTECH = None
    OSTECH_SERIAL_NUMBER = None

    scan_ports = _available_ports()
    fallback_ports = [
        port for port in (sr830_port, ostech_port, DEFAULT_SR830_PORT, DEFAULT_OSTECH_PORT)
        if port
    ]
    candidates = list(dict.fromkeys(scan_ports + fallback_ports))
    detected = _find_device_ports(candidates)
    sr830_port = detected.get("SR830")
    ostech_port = detected.get("OSTECH")
    SR830_PORT = sr830_port
    OSTECH_PORT = ostech_port

    if sr830_port:
        Log.Log("Comm", "SR830", "Info", "Device assigned", sr830_port, "*IDN? scan")
    if ostech_port:
        Log.Log("Comm", "OSTECH", "Info", "Device assigned", ostech_port, "GVN scan")

    if sr830_port:
        try:
            SR830 = serial.Serial(sr830_port, BAUDRATE, timeout=TIMEOUT)
            SR830_ID = ask_SR830("*IDN?")
            Log.Log("Comm", "SR830", "Info", "Device assigned", SR830_ID, SR830_PORT)
        except (serial.SerialException, OSError, RuntimeError) as error:
            SR830 = None
            Log.Log("Comm", str(sr830_port), "Warning", "Open identified device", "FAILED", str(error), "SR830")

    if ostech_port:
        try:
            OSTECH = serial.Serial(ostech_port, BAUDRATE, timeout=TIMEOUT)
            OSTECH_SERIAL_NUMBER = query_ostech_text("GVN")
            set_ostech_binary_mode()
            Log.Log("Comm", "OSTECH", "Info", "Device assigned", OSTECH_SERIAL_NUMBER, OSTECH_PORT)
        except (serial.SerialException, OSError, RuntimeError) as error:
            if OSTECH is not None and OSTECH.is_open:
                OSTECH.close()
            OSTECH = None
            Log.Log("Comm", str(ostech_port), "Warning", "Open identified device", "FAILED", str(error), "OSTECH")

    return SR830, OSTECH


def close_devices():
    """Close every currently open instrument without raising on missing ports."""
    for port in (SR830, OSTECH):
        if port is not None and getattr(port, "is_open", True):
            port.close()


def _format_command(command: str, value=None):
    """Build the ASCII command line shared by SR830 and OSTECH setters."""
    return str(command) if value is None else f"{command} {value}"


def _convert_response(response: str, return_type):
    """Convert a decoded text response into the caller's requested type.

    Strings are returned unchanged, booleans accept the protocol's common
    textual forms, and all other types are called as conversion functions.
    Conversion failures deliberately propagate so the worker can publish a
    precise communication error instead of storing invalid state.
    """
    if return_type is str:
        return response
    if return_type is bool:
        normalized = response.strip().lower()
        if normalized in ("1", "true", "on"):
            return True
        if normalized in ("0", "false", "off"):
            return False
        raise ValueError(f"Keine boolesche Antwort: {response!r}")
    return return_type(response)


def _resolve_sr830_command(command):
    """Accept either a raw command string or a metadata object from Send.py."""
    if hasattr(command, "command"):
        return command.command
    return str(command)


def _resolve_sr830_return_type(command, return_type):
    """Pick a return type from metadata when the caller did not provide one."""
    if return_type is not None:
        return return_type
    if hasattr(command, "type"):
        return command.type
    return str


def ask_SR830(command, value=None, return_type=None):
    """Send a line-oriented SR830 command and return a typed response.

    ``command`` may be either a raw command string such as ``"FREQ?"`` or a
    metadata object from ``Send.py`` (for example ``SR830G.FREQ``). This module
    is responsible for the actual wire-level encoding and decoding. The public
    command API in ``Send.py`` decides which command to use.
    """
    if SR830 is None:
        raise RuntimeError("SR830 ist nicht verbunden.")
    resolved_command = _resolve_sr830_command(command)
    resolved_type = _resolve_sr830_return_type(command, return_type)
    with SR830_LOCK:
        SR830.write(f"{_format_command(resolved_command, value)}\r".encode("ascii"))
        SR830.flush()
        response = SR830.read_until(b"\r").decode("ascii", errors="replace").strip()
        return _convert_response(response, resolved_type)


def send_SR830(command, value=None):
    """Send an SR830 setting command without waiting for a response.

    The communication layer handles the actual serial write. Public code should
    reach this function through the command API in ``Send.py`` so all outgoing
    commands follow the same structure and logging flow.
    """
    if SR830 is None:
        raise RuntimeError("SR830 ist nicht verbunden.")
    resolved_command = _resolve_sr830_command(command)
    with SR830_LOCK:
        SR830.write(f"{_format_command(resolved_command, value)}\r".encode("ascii"))
        SR830.flush()


def _resolve_ostech_command(command):
    """Accept either a raw command string or metadata from Send.py."""
    if hasattr(command, "command"):
        return command.command
    return str(command)


def ask_OSTECH(command: str, value=None, return_type=str):
    """Send a text-mode OSTECH command and convert its response type."""
    if OSTECH is None:
        raise RuntimeError("OSTECH ist nicht verbunden.")
    resolved_command = _resolve_ostech_command(command)
    with OSTECH_LOCK:
        OSTECH.write(f"{_format_command(resolved_command, value)}\r".encode("ascii"))
        OSTECH.flush()
        response = OSTECH.read_until(b"\r").decode("ascii", errors="replace").strip()
        return _convert_response(response, return_type)


def ask_OSTech(command: str, value=None, return_type=str):
    """Compatibility alias kept for the Send-layer metadata API."""
    return ask_OSTECH(command, value=value, return_type=return_type)


def send_ostech_command(command: str):
    """Send a raw OSTECH text command without reading a response.

    This low-level compatibility helper is useful for commands whose response
    is intentionally ignored. Typed reads should use ``LabOSTECHCommand`` so
    echo, payload length, and checksum validation are not skipped.
    """
    if OSTECH is None:
        raise RuntimeError("OSTECH ist nicht verbunden.")
    resolved_command = _resolve_ostech_command(command)
    with OSTECH_LOCK:
        OSTECH.write(f"{resolved_command}\r".encode("ascii"))
        OSTECH.flush()


def send_OSTECH(command: str, value=None):
    """Send an OSTECH text-mode setter without waiting for a response."""
    if OSTECH is None:
        raise RuntimeError("OSTECH ist nicht verbunden.")
    resolved_command = _resolve_ostech_command(command)
    with OSTECH_LOCK:
        OSTECH.write(f"{_format_command(resolved_command, value)}\r".encode("ascii"))
        OSTECH.flush()


def send_OSTech(command: str, value=None):
    """Compatibility alias kept for the Send-layer metadata API."""
    return send_OSTECH(command, value=value)


def query_ostech_text(command: str):
    """Read one OSTECH command while the device is still in text mode.

    Startup commands use an ASCII echo followed by a line response. The echo
    check is important because it proves that the response belongs to this
    request rather than to a stale command left in the serial buffer.
    """
    if OSTECH is None:
        raise RuntimeError("OSTECH ist nicht verbunden.")
    with OSTECH_LOCK:
        OSTECH.reset_input_buffer()
        OSTECH.write(f"{command}\r".encode("ascii"))
        OSTECH.flush()
        echo = OSTECH.read_until(b"\r")
        expected_echo = f"{command.upper()}\r".encode("ascii")
        if echo != expected_echo:
            raise RuntimeError(f"Unerwartetes {command}-Echo: {echo!r}")
        response = OSTECH.read_until(b"\r")
        if not response:
            raise RuntimeError(f"Keine Antwort auf {command} erhalten.")
        return response.decode("ascii", errors="replace").strip()


def set_ostech_binary_mode():
    """Switch OSTECH from startup text mode to binary response mode.

    ``GMS8`` is the protocol boundary. It is issued only after the startup
    identification handshake and its echo/response are verified. Subsequent
    calls to ``LabOSTECH`` therefore expect binary payload frames.
    """
    if OSTECH is None:
        raise RuntimeError("OSTECH ist nicht verbunden.")
    with OSTECH_LOCK:
        OSTECH.reset_input_buffer()
        OSTECH.write(b"GMS8\r")
        OSTECH.flush()
        echo = OSTECH.read_until(b"\r")
        if echo != b"GMS8\r":
            raise RuntimeError(f"Unerwartetes GMS8-Echo: {echo!r}")
        response = OSTECH.read_until(b"\r")
        if not response:
            raise RuntimeError("Keine Antwort auf GMS8 erhalten.")


def LabOSTECH(port, command: str, data_type: type):
    """Execute one binary-mode OSTECH command and validate its frame.

    The expected frame is an ASCII echo followed by a typed payload and one
    checksum byte. The function rejects wrong echoes, short payloads, unknown
    types, and checksum mismatches so corrupted hardware responses become
    explicit communication errors instead of plausible-looking measurements.
    """
    with OSTECH_LOCK:
        port.reset_input_buffer()
        port.write(f"{command}\r".encode("ascii"))
        port.flush()
        echo = port.read_until(b"\r")
        expected_echo = f"{command.upper()}\r".encode("ascii")
        if echo != expected_echo:
            raise RuntimeError(f"Unerwartetes Echo: erwartet {expected_echo!r}, erhalten {echo!r}")

        if data_type is bool:
            response = port.read(1)
            if response not in (b"\xAA", b"\x55"):
                raise RuntimeError(f"Ungueltige bool-Antwort: {response!r}")
            return response == b"\xAA"

        payload_length = 2 if data_type is int else 4 if data_type is float else 0
        if not payload_length:
            raise TypeError("data_type muss bool, int oder float sein.")
        response = port.read(payload_length + 1)
        if len(response) != payload_length + 1:
            raise RuntimeError("OSTECH-Antwort ist zu kurz.")
        checksum = (0x55 + sum(response[:payload_length])) % 256
        if response[payload_length] != checksum:
            raise RuntimeError("Ungueltige OSTECH-Pruefsumme.")
        return struct.unpack(">H" if data_type is int else ">f", response[:payload_length])[0]


def decode_ostech_status(status_word: int):
    """Translate the OSTECH ``GS`` bit field into named boolean conditions."""
    masks = {
        "interlock_ok": 0x0001,
        "driver_supply_ok": 0x0004,
        "driver_temperature_ok": 0x0008,
        "lt_sensor_ok": 0x0400,
        "ct_sensor_ok": 0x0800,
        "lc_on": 0x4000,
        "lc_error": 0x8000,
    }
    return {"status_word": status_word, **{name: bool(status_word & mask) for name, mask in masks.items()}}


def LabOSTECHCommand(port, command: OSTECHCommand):
    """Execute an enum command, decode it, and publish it to ``State``.

    ``GS`` is special because its integer bit field becomes a status dictionary.
    All other commands are stored under their enum name, so the GUI and logging
    layers can use one consistent naming scheme independent of the wire format.
    """
    info = command.value
    value = LabOSTECH(port, info.command, info.data_type)
    if command is OSTECHCommand.GS:
        value = decode_ostech_status(value)
        State.update_values({"GS": value, "OSTECH_STATUS": value})
    else:
        State.update_values({command.name: value})
    return OSTECHResult(value, info)


def _device_steps():
    """Build the polling actions for SR830 and OSTECH workers.

    The two SR830 SNAP requests remain separate because they represent different
    manual parameter groups. Each action parses its response before publishing
    the corresponding State fields. Lambdas capture their command values safely
    so the generated OSTECH steps do not all reference the final loop item.
    """
    def read_snap(commands, names):
        response = ask_SR830(f"SNAP? {commands}")
        values = [float(value.strip()) for value in response.split(",")]
        if len(values) != len(names):
            raise ValueError(f"Unerwartete SNAP-Antwort fuer {commands}: {response!r}")
        State.update_values(dict(zip(names, values)))
        return response

    def read_value(command, name):
        value = float(ask_SR830(command))
        State.update_values({name: value})
        return value

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
    ostech_periodic_steps = tuple(
        (command.name, lambda command=command: LabOSTECHCommand(OSTECH, command))
        for command in (
            OSTECHCommand.LCT,
            OSTECHCommand.XTA,
            OSTECHCommand.LVA,
            OSTECHCommand.XTCA,
            OSTECHCommand.XTVA,
            OSTECHCommand.LCA,
        )
    )
    ostech_startup_steps = tuple(
        (command.name, lambda command=command: LabOSTECHCommand(OSTECH, command))
        for command in (
            OSTECHCommand.XTT,
            OSTECHCommand.LTM,
            OSTECHCommand.GT,
            OSTECHCommand.GS,
            OSTECHCommand.GVN,
        )
    )
    return sr830_steps, ostech_periodic_steps, ostech_startup_steps


def _run_device(source, steps, tick_ms, cycles, stop_requested, publish):
    """Execute one device's polling sequence until completion or stop.

    One invocation owns one serial device, so SR830 and OSTECH sequences run
    concurrently in separate ``DeviceThread`` instances. Within one device,
    steps remain sequential because a device's serial protocol is ordered.
    A failed step publishes one structured error and ends only that device
    loop; the other device and the GUI can continue running.
    """
    connected = SR830 is not None if source == "SR830" else OSTECH is not None
    if not connected:
        publish({"step": "startup", "value": f"{source} ist nicht verbunden."})
        return
    cycle = 0
    while cycles is None or cycle < cycles:
        for name, action in steps:
            if stop_requested.is_set():
                return
            try:
                publish({"step": name, "value": action()})
            except Exception as error:
                publish({"step": "error", "value": f"{name}: {type(error).__name__}: {error}"})
                return
            if stop_requested.wait(tick_ms / 1000):
                return
        cycle += 1


def _device_status_is_ready(publish):
    """Query both instruments and report whether command execution may start."""
    if SR830 is None or OSTECH is None:
        return False
    try:
        sr830_id = SR830_ID or ask_SR830("*IDN?")
        publish({
            "tag": "SR830",
            "command": "*IDN?",
            "value": sr830_id,
            "info": "readiness check",
        })
        status = LabOSTECHCommand(OSTECH, OSTECHCommand.GS).value
        publish({
            "tag": "OSTECH",
            "command": OSTECHCommand.GS.value.command,
            "value": status,
            "info": "readiness check",
        })
        serial_number = LabOSTECHCommand(OSTECH, OSTECHCommand.GVN).value
        publish({
            "tag": "OSTECH",
            "command": OSTECHCommand.GVN.value.command,
            "value": serial_number,
            "info": "readiness check; serial number",
        })
        return bool(sr830_id) and not status.get("lc_error", False)
    except Exception as error:
        publish({
            "step": "error",
            "value": f"{type(error).__name__}: {error}",
            "info": "readiness check",
        })
        return False


def _run_commands(command_queries, command_steps, stop_commands, interval_seconds, stop_requested, publish):
    """Run readiness checks, user commands, and shutdown commands in order.

    Readiness is retried until both devices are usable or cancellation is
    requested. Every action is isolated in its own ``try`` block so one failed
    optional command is reported without hiding the remaining workflow.
    """
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
):
    """Create and start the complete communication pipeline.

    The function validates timing and cycle parameters, builds the SR830 and
    OSTECH action lists, creates independent logging and GUI consumers, and
    starts the communication workers through ``CommunicationThreads``. The
    calculation worker is deliberately owned by ``Starter.py`` and is not
    started here. It returns the coordinator so callers can monitor or stop
    the communication workers explicitly.

    ``gui_handler`` receives data messages, not Tkinter widget calls. A real
    GUI integration should transfer those messages into the Tkinter main
    thread, while the default handler prints a diagnostic representation.
    """
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
    sr830_steps, ostech_periodic_steps, _ = _device_steps()
    if command_queries is None:
        command_queries = ()
    else:
        command_queries = tuple(command_queries)
    if command_steps is None:
        command_steps = ()
    else:
        command_steps = tuple(command_steps)
    if stop_commands is None:
        stop_commands = ()
    else:
        stop_commands = tuple(stop_commands)

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
        ),
        lambda stop, publish: _run_device(
            "OSTECH", ostech_periodic_steps, ostech_tick_ms, ostech_cycles, stop, publish,
        ),
        log_handler,
        gui_handler or default_gui_handler,
        gui_interval_ms=GUI_INTERVAL_MS,
        command_runner=lambda stop, publish: _run_commands(
            command_queries, command_steps, stop_commands,
            command_interval_seconds, stop, publish,
        ),
    )
    threads.start()
    return threads


def run_threaded_measurement(tick_ms=DEFAULT_TICK_MS, cycles=DEFAULT_CYCLES, **options):
    """Run a measurement synchronously while its internal work is threaded.

    The caller blocks while SR830 or OSTECH workers are alive. The ``finally``
    block guarantees that all owned threads are joined, including when a
    device raises an exception or the caller interrupts the wait.
    """
    threads = start_threaded_measurement(tick_ms, cycles, **options)
    try:
        while threads.sr830.thread.is_alive() or threads.ostech.thread.is_alive():
            time.sleep(0.05)
    finally:
        threads.stop()


if __name__ == "__main__":
    try:
        open_devices()
        run_threaded_measurement()
    finally:
        close_devices()
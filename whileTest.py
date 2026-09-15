import struct
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable

import serial

import TestingLog
from Threads import CommunicationThreads, ThreadMessage


SR830_PORT = "COM3"
OSTECH_PORT = "COM4"
BAUDRATE = 9600
TIMEOUT = 2
DEFAULT_TICK_MS = 1
DEFAULT_CYCLES = 5
GUI_INTERVAL_MS = 12
TEST_TAG = "Kommunikations-Test fuer SR830 und OSTECH"

SR830 = None
OSTECH = None
SR830_LOCK = threading.Lock()
OSTECH_LOCK = threading.Lock()


@dataclass(frozen=True)
class OSTECHCommandInfo:
    command: str
    data_type: type
    unit: str = ""


@dataclass(frozen=True)
class OSTECHResult:
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


    # send ones after Usere Intent 
    LMDX = OSTECHCommandInfo("LMDX", bool)
    L = OSTECHCommandInfo ("L", bool)

def open_devices(sr830_port=SR830_PORT, ostech_port=OSTECH_PORT):
    global SR830, OSTECH
    SR830 = serial.Serial(sr830_port, BAUDRATE, timeout=TIMEOUT)
    OSTECH = serial.Serial(ostech_port, BAUDRATE, timeout=TIMEOUT)
    return SR830, OSTECH


def close_devices():
    for port in (SR830, OSTECH):
        if port is not None and getattr(port, "is_open", True):
            port.close()


def ask_SR830(command: str):
    if SR830 is None:
        raise RuntimeError("SR830 ist nicht verbunden.")
    with SR830_LOCK:
        SR830.write(f"{command}\r".encode("ascii"))
        SR830.flush()
        return SR830.read_until(b"\r").decode("ascii", errors="replace").strip()


def ask_OSTECH(command: str):
    if OSTECH is None:
        raise RuntimeError("OSTECH ist nicht verbunden.")
    with OSTECH_LOCK:
        OSTECH.write(f"{command}\r".encode("ascii"))
        OSTECH.flush()
        return OSTECH.read_until(b"\r").decode("ascii", errors="replace").strip()


def send_ostech_command(command: str):
    if OSTECH is None:
        raise RuntimeError("OSTECH ist nicht verbunden.")
    with OSTECH_LOCK:
        OSTECH.write(f"{command}\r".encode("ascii"))
        OSTECH.flush()


def LabOSTECH(port, command: str, data_type: type):
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
    info = command.value
    value = LabOSTECH(port, info.command, info.data_type)
    if command is OSTECHCommand.GS:
        value = decode_ostech_status(value)
    return OSTECHResult(value, info)


def _device_steps():
    sr830_steps = (
        ("SNAP 1,2,3,4,10,11", lambda: ask_SR830("SNAP? 1,2,3,4,10,11")),
        ("SNAP 5,6,7,8,9", lambda: ask_SR830("SNAP? 5,6,7,8,9")),
        ("PHAS", lambda: ask_SR830("PHAS?")),
        ("FREQ", lambda: ask_SR830("FREQ?")),
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
    if SR830 is None or OSTECH is None:
        return False
    try:
        sr830_id = ask_SR830("*IDN?")
        status = LabOSTECHCommand(OSTECH, OSTECHCommand.GS).value
        serial_number = LabOSTECHCommand(OSTECH, OSTECHCommand.GVN).value
        publish({"step": "status SR830", "value": sr830_id})
        publish({"step": "status OSTECH", "value": {"status": status, "serial": serial_number}})
        return bool(sr830_id) and not status.get("lc_error", False)
    except Exception as error:
        publish({"step": "status error", "value": f"{type(error).__name__}: {error}"})
        return False


def _run_commands(command_queries, command_steps, stop_commands, interval_seconds, stop_requested, publish):
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
        command_queries = (
            ("OSTECH LMDX", lambda: LabOSTECHCommand(OSTECH, OSTECHCommand.LMDX)),
            ("OSTECH L", lambda: LabOSTECHCommand(OSTECH, OSTECHCommand.L)),
        )
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
        level = {"result": "T", "status": "I", "error": "E"}[message.kind]
        TestingLog.Log("KOM_Test", message.source, level, str(payload.get("step", message.kind)),
                       str(payload.get("value", "")), message.kind, TEST_TAG)

    def default_gui_handler(message: ThreadMessage):
        payload = message.value if isinstance(message.value, dict) else {"value": message.value}
        print(f"[{message.source}] {payload.get('step', message.kind)}: {payload.get('value', '')}")

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

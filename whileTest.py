import struct
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable

import serial
import time
import TestingLog
from Threads import CommunicationThreads, ThreadMessage


# run_threaded_measurement(tick_ms=50)
# run_threaded_measurement(tick_ms=10, cycles=100)


EXPECTED_SR830_ID = "Stanford_Research_Systems,SR830,s/n46328,ver1.07"
EXPECTED_OSTECH_SERIAL_NUMBER = 8661

TAKT_SR830 = 100
TAKT_OSTTECH = 100
TAKT_GUI = 100
CYCLES = None

Test_Tag = "Komunkiations Test für SR830 und OSTECH"





try:
    SR830 = serial.Serial("COM3", 9600, timeout=2)
    time.sleep(0.5)
    TestingLog.Log("KOM_Test", "SR830", "T", "SR830 Kom Test Start", "Ask", Test_Tag)
    SR830.write(b"*IDN?\r")
    ValueIDN = SR830.read_until(b"\r")
    TestingLog.Log("KOM_Test", "SR830", "T", "*IDN?", str(ValueIDN), "Raw", Test_Tag)
    ValueIDN = ValueIDN.decode("ascii", errors="replace").strip()
    TestingLog.Log("KOM_Test", "SR830", "T", "*IDN?", ValueIDN, "Decoded", Test_Tag)
except serial.SerialException as error:
    SR830 = None
    TestingLog.Log(
        "KOM_Test", "SR830", "E", "SR830 Verbindung fehlgeschlagen",
        f"{type(error).__name__}: {error}", "Connection error", Test_Tag,
    )

time.sleep(2)

try:
    OSTECH = serial.Serial("COM4", 9600, timeout=2)
    time.sleep(0.5)
    TestingLog.Log("KOM_Test", "OSTECH", "T", "OSTECH Kom Test Start", "Ask", Test_Tag)
    OSTECH.write(b"GMS8\r")
    OSTECH.flush()
    ValueGVN = OSTECH.read_until(b"\r")
    TestingLog.Log("KOM_Test", "OSTECH", "T", "OSTECH Kom Test Start", str(ValueGVN), "Raw", Test_Tag)
    ValueGVN = ValueGVN.decode("ascii", errors="replace").strip()
    TestingLog.Log("KOM_Test", "OSTECH", "T", "OSTECH Kom Test Start", ValueGVN, "Decoded", Test_Tag)
except serial.SerialException as error:
    OSTECH = None
    TestingLog.Log(
        "KOM_Test", "OSTECH", "E", "OSTECH Verbindung fehlgeschlagen",
        f"{type(error).__name__}: {error}", "Connection error", Test_Tag,
    )

time.sleep(2)




class CommunicationState(Enum):
    IDLE = "idle"
    WAITING = "waiting"
    EXECUTING = "executing"
    RUNNING = "running"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class CommunicationStep:
    name: str
    action: Callable[[], object]
    delay_ms: int = 0
    processor: Callable[[object], object] | None = None


class CommunicationStateMachine:
    def __init__(self, steps: list[CommunicationStep]):
        self.steps = steps
        self.state = CommunicationState.IDLE
        self.current_step: str | None = None
        self.results: dict[str, object] = {}
        self.errors: dict[str, Exception] = {}
        self.events: list[str] = []
        self._run_lock = threading.Lock()
        self._stop_requested = threading.Event()
        self._active = False

    def _log_event(self, message: str):
        self.events.append(message)
        TestingLog.Log("KOM_Test", "STATE_MACHINE", "I", message, "Info", Test_Tag)

    def run(self) -> dict[str, object]:
        self.state = CommunicationState.IDLE
        self.current_step = None
        self.results.clear()
        self.errors.clear()

        for step in self.steps:
            if step.delay_ms < 0:
                raise ValueError(f"Die Wartezeit für {step.name} darf nicht negativ sein.")

            self.current_step = step.name
            self.state = CommunicationState.WAITING
            testStat(step.delay_ms)
            self.state = CommunicationState.EXECUTING

            try:
                self.results[step.name] = step.action()
            except Exception as error:
                self.errors[step.name] = error
                self.state = CommunicationState.FAILED
                raise

        self.current_step = None
        self.state = CommunicationState.COMPLETED
        return dict(self.results)

    def run_periodic(self, tick_ms: int, cycles: int | None = None) -> dict[str, object]:
        if tick_ms <= 0:
            raise ValueError("Der Takt muss größer als 0 ms sein.")
        if cycles is not None and cycles <= 0:
            raise ValueError("Die Anzahl der Zyklen muss größer als 0 sein.")

        with self._run_lock:
            if self._active:
                self._stop_requested.set()
                self._log_event("Neuer Lauf ignoriert: der alte Task wird beendet.")
                return dict(self.results)
            self._active = True
            self._stop_requested.clear()

        try:
            self.results.clear()
            self.errors.clear()
            cycle_number = 0
            next_tick = time.monotonic()

            while cycles is None or cycle_number < cycles:
                if self._stop_requested.is_set():
                    self.state = CommunicationState.CANCELLED
                    self._log_event("Lauf beendet: ein neuer Start wurde ignoriert.")
                    break

                self.state = CommunicationState.RUNNING
                for step in self.steps:
                    self.current_step = step.name
                    try:
                        value = step.action()
                        self.results[step.name] = (
                            step.processor(value) if step.processor is not None else value
                        )
                    except Exception as error:
                        self.errors[step.name] = error
                        self.state = CommunicationState.FAILED
                        raise

                cycle_number += 1
                next_tick += tick_ms / 1000
                remaining = next_tick - time.monotonic()
                if remaining > 0 and (cycles is None or cycle_number < cycles):
                    self.state = CommunicationState.WAITING
                    self._stop_requested.wait(remaining)

            if self.state is not CommunicationState.CANCELLED:
                self.state = CommunicationState.COMPLETED
            self.current_step = None
            return dict(self.results)
        finally:
            with self._run_lock:
                self._active = False


@dataclass(frozen=True)
class OSTECHCommandInfo:
    command: str
    data_type: type
    unit: str = ""
    description: str = ""
    minimum: float | int | None = None
    maximum: float | int | None = None


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

    @property
    def description(self):
        return self.info.description

    def __str__(self):
        return str(self.value)


class OSTECHCommand(Enum):
    L = OSTECHCommandInfo("L", bool, description="laser stop/run")
    LTM = OSTECHCommandInfo("LTM", float, "°C", "laser temperature maximum", -99, 200)
    LG = OSTECHCommandInfo("LG", bool, description="gate option")
    LCL = OSTECHCommandInfo("LCL", float, "mA", "current limit", 0)
    LCT = OSTECHCommandInfo("LCT", float, "mA", "current target", 0)
    LCA = OSTECHCommandInfo("LCA", float, "mA", "actual current")
    LCB = OSTECHCommandInfo("LCB", float, "mA", "base or bias current", 0)
    LVA = OSTECHCommandInfo("LVA", float, "V", "actual laser voltage")
    LVC = OSTECHCommandInfo("LVC", float, "V", "compliance voltage", 1.3, 6)
    LPCA = OSTECHCommandInfo("LPCA", float, "µA", "laser photo current actual")
    LPCT = OSTECHCommandInfo("LPCT", float, "µA", "laser photo current target", 0, 20)
    LPCC = OSTECHCommandInfo("LPCC", bool, description="laser photo current control")
    LPA = OSTECHCommandInfo("LPA", float, "W", "laser power actual")
    LPT = OSTECHCommandInfo("LPT", float, "W", "laser power target", 0)
    LPF = OSTECHCommandInfo("LPF", bool, description="laser power fix procedure")
    LMDI = OSTECHCommandInfo("LMDI", bool, description="internal digital modulation")
    LMDX = OSTECHCommandInfo("LMDX", bool, description="external digital modulation")
    LMAX = OSTECHCommandInfo("LMAX", bool, description="external analog modulation")
    LMW = OSTECHCommandInfo("LMW", float, "µs", "pulse width", 1)
    LMP = OSTECHCommandInfo("LMP", float, "µs", "pulse period")
    LMDIC = OSTECHCommandInfo("LMDIC", int, "", "number of pulses", 0, 65534)
    LMDXN = OSTECHCommandInfo("LMDXN", bool, description="negate modulation input")
    LZTR = OSTECHCommandInfo("LZTR", float, "ms", "ramp time", 300, 34000)
    LZR = OSTECHCommandInfo("LZR", bool, "ms", "sequencer run")
    LZP = OSTECHCommandInfo("LZP", int, "ms", "sequencer point select")
    LZPT = OSTECHCommandInfo("LZPT", int, "ms", "subsequence time")
    LZPC = OSTECHCommandInfo("LZPC", float, "mA", "subsequence current")
    PL = OSTECHCommandInfo("PL", bool, description="pilot laser stop/run")
    PP = OSTECHCommandInfo("PP", int, "", "pilot laser modulation", 0, 16)
    XTA = OSTECHCommandInfo("xTA", float, "°C", "actual temperature")
    XTLU = OSTECHCommandInfo("xTLU", float, "°C", "upper temperature limit", -99, 200)
    XTLL = OSTECHCommandInfo("xTLL", float, "°C", "lower temperature limit", -99, 200)
    XTSC = OSTECHCommandInfo("xTSC", float, description="sensor coefficient")
    XTSM = OSTECHCommandInfo("xTSM", int, "", "sensor approximation model", 0, 1)
    XTC = OSTECHCommandInfo("xTC", bool, description="temperature controller stop/run")
    XTT = OSTECHCommandInfo("xTT", float, "°C", "temperature target", -99, 200)
    XTCA = OSTECHCommandInfo("xTCA", float, "mA", "actual current")
    XTCL = OSTECHCommandInfo("xTCL", float, "mA", "current limit", 0)
    XTVA = OSTECHCommandInfo("xTVA", float, "V", "actual voltage")
    XTCCK = OSTECHCommandInfo("xTCCK", float, "", "PID gain factor", 0, 255)
    XTCCN = OSTECHCommandInfo("xTCCN", float, "s", "PID reset time", 0, 255)
    XTCCV = OSTECHCommandInfo("xTCCV", float, "s", "PID rate time", 0, 99)
    GD = OSTECHCommandInfo("GD", bool, description="set defaults")
    GF = OSTECHCommandInfo("GF", float, "V", "fan voltage", 1.2, 24)
    GFD = OSTECHCommandInfo("GFD", float, "V", "default fan voltage", 1.2, 24)
    GX = OSTECHCommandInfo("GX", bool, description="external control stop/run")
    GT = OSTECHCommandInfo("GT", float, "°C", "device temperature")
    GVS = OSTECHCommandInfo("GVS", int, description="software version")
    GVN = OSTECHCommandInfo("GVN", int, description="serial number")
    GS = OSTECHCommandInfo("GS", int, description="get status")
    GM = OSTECHCommandInfo("GM", int, description="get mode")
    GMC = OSTECHCommandInfo("GMC", int, description="clear mode bits")
    GMS = OSTECHCommandInfo("GMS", int, description="set mode bits")
    GMT = OSTECHCommandInfo("GMT", int, description="toggle mode bits")

    def for_sensor(self, number: int) -> OSTECHCommandInfo:
        if not 1 <= number <= 9 or not self.value.command.startswith("x"):
            raise ValueError("Nur xT-Befehle können für einen Sensor nummeriert werden.")
        return OSTECHCommandInfo(
            f"{number}{self.value.command[1:]}", self.value.data_type,
            self.value.unit, self.value.description,
            self.value.minimum, self.value.maximum,
        )











def LabOSTECH(Port, Command: str, Data_Type, Decoder=None):
    Port.reset_input_buffer()
    Sending_Command = Command + "\r"
    Port.write(Sending_Command.encode("ascii"))
    Port.flush()

    Echo = Port.read_until(b"\r")
    Expected_Echo = (Command.upper() + "\r").encode("ascii")
    if Echo != Expected_Echo:
        raise RuntimeError(f"Unexpected echo: expected {Expected_Echo!r}, received {Echo!r}")

    if Decoder is not None:
        if not isinstance(Data_Type, int):
            raise TypeError("Data_Type muss die Anzahl der Antwortbytes sein.")
        response = Port.read(Data_Type)
        if len(response) != Data_Type:
            raise RuntimeError(
                f"Expected {Data_Type} response bytes, but received {len(response)} bytes."
            )
        return Decoder(response)

    if Data_Type is bool:
        response = Port.read(1)
        if len(response) != 1:
            raise RuntimeError(f"Expected 1 response byte, but received {len(response)} bytes.")
        if response == b"\xAA":
            return True
        if response == b"\x55":
            return False
        raise RuntimeError(f"Invalid boolean response: {response!r}")

    if Data_Type is int:
        response = Port.read(3)
        Payload_Length = 2
    elif Data_Type is float:
        response = Port.read(5)
        Payload_Length = 4
    else:
        raise TypeError("Data_Type muss bool, int, float oder ein eigener Decoder sein.")

    if len(response) != Payload_Length + 1:
        raise RuntimeError(
            f"Expected {Payload_Length + 1} response bytes, but received {len(response)} bytes."
        )

    Expected_Checksum = (0x55 + sum(response[:Payload_Length])) % 256
    if response[Payload_Length] != Expected_Checksum:
        raise RuntimeError(
            f"Invalid checksum: expected {Expected_Checksum:02X}, "
            f"received {response[Payload_Length]:02X}"
        )

    if Data_Type is int:
        return struct.unpack(">H", response[:Payload_Length])[0]
    return struct.unpack(">f", response[:Payload_Length])[0]


def decode_ostech_status(Status_Word: int):
    Status_Bits = {
        "interlock_ok": 0x0001,
        "driver_supply_ok": 0x0004,
        "driver_temperature_ok": 0x0008,
        "ltu_not_ok": 0x0010,
        "ltl_not_ok": 0x0020,
        "ctu_not_ok": 0x0040,
        "ctl_not_ok": 0x0080,
        "lt_sensor_ok": 0x0400,
        "ct_sensor_ok": 0x0800,
        "ltm_not_ok": 0x2000,
        "lc_on": 0x4000,
        "lc_error": 0x8000,
    }
    return {
        "status_word": Status_Word,
        **{Name: bool(Status_Word & Mask) for Name, Mask in Status_Bits.items()},
    }


def LabOSTECHCommand(Port, Command: OSTECHCommand, Sensor_Number=1):
    if Command.value.command.startswith("x"):
        Info = Command.for_sensor(Sensor_Number)
    else:
        if Sensor_Number != 1:
            raise ValueError("Sensor_Number ist nur für xT-Befehle erlaubt.")
        Info = Command.value

    Result = LabOSTECH(Port, Info.command, Info.data_type)
    if Command is OSTECHCommand.GS:
        Result = decode_ostech_status(Result)
    return OSTECHResult(Result, Info)


def set_ostech_binary_mode(Port):
    LabOSTECH(Port, "GMS8", int)

def set_ostech_ascii_mode():
# testing all relevant commands for OSTECH
    TestingLog.Log("KOM_Test","OSTECH","T","Test all relevant commands for OSTECH","Ask",str(Test_Tag))
    time.sleep(1)

    TestingLog.Log("KOM_Test","OSTECH","T","Set binary mode","GMS8","Ask",str(Test_Tag))
    set_ostech_binary_mode(OSTECH)

    TestingLog.Log("KOM_Test","OSTECH","T","GVS","","Ask",str(Test_Tag))
    Res = LabOSTECHCommand(OSTECH, OSTECHCommand.GVS)
    TestingLog.Log("KOM_Test","OSTECH","T","GVS",str(Res),"software version",str(Test_Tag))

    TestingLog.Log("KOM_Test","OSTECH","T","GVN","","Ask",str(Test_Tag))
    Res = LabOSTECHCommand(OSTECH, OSTECHCommand.GVN)
    TestingLog.Log("KOM_Test","OSTECH","T","GVN",str(Res),"serial number",str(Test_Tag))

    TestingLog.Log("KOM_Test","OSTECH","T","GS","","Ask",str(Test_Tag))
    Status = LabOSTECHCommand(OSTECH, OSTECHCommand.GS)
    TestingLog.Log("KOM_Test","OSTECH","T","GS",str(Status),"get status",str(Test_Tag))

    TestingLog.Log("KOM_Test","OSTECH","T","LTM","","Ask",str(Test_Tag))
    Res = LabOSTECHCommand(OSTECH, OSTECHCommand.LTM)
    TestingLog.Log("KOM_Test","OSTECH","T","LTM",str(Res),"laser temperature maximum",str(Test_Tag))

    TestingLog.Log("KOM_Test","OSTECH","T","LCA","","Ask",str(Test_Tag))
    Res = LabOSTECHCommand(OSTECH, OSTECHCommand.LCA)
    TestingLog.Log("KOM_Test","OSTECH","T","LCA",str(Res),"actual current",str(Test_Tag))

    TestingLog.Log("KOM_Test","OSTECH","T","LVA","","Ask",str(Test_Tag))
    Res = LabOSTECHCommand(OSTECH, OSTECHCommand.LVA)
    TestingLog.Log("KOM_Test","OSTECH","T","LVA",str(Res),"laser voltage actual",str(Test_Tag))

    TestingLog.Log("KOM_Test","OSTECH","T","LTA","","Ask",str(Test_Tag))
    Res = LabOSTECHCommand(OSTECH, OSTECHCommand.XTA)
    TestingLog.Log("KOM_Test","OSTECH","T","LTA",str(Res),"temperature actual",str(Test_Tag))

    TestingLog.Log("KOM_Test","OSTECH","T","GT","","Ask",str(Test_Tag))
    Res = LabOSTECHCommand(OSTECH, OSTECHCommand.GT)
    TestingLog.Log("KOM_Test","OSTECH","T","GT",str(Res),"device temperature (head)",str(Test_Tag))

    TestingLog.Log("KOM_Test","OSTECH","T","LVC","","Ask",str(Test_Tag))
    Res = LabOSTECHCommand(OSTECH, OSTECHCommand.LVC)
    TestingLog.Log("KOM_Test","OSTECH","T","LVC",str(Res),"compliance voltage",str(Test_Tag))

    TestingLog.Log("KOM_Test","OSTECH","T","xTC","","Ask",str(Test_Tag))
    Res = LabOSTECHCommand(OSTECH, OSTECHCommand.XTC)
    TestingLog.Log("KOM_Test","OSTECH","T","xTC",str(Res),"temperature controller stop/run ",str(Test_Tag))





def testStat(ms: int):
    if ms < 0:
        raise ValueError("Die Wartezeit darf nicht negativ sein.")
    time.sleep(ms / 1000)


def run_communication_sequence(steps: list[CommunicationStep]):
    return CommunicationStateMachine(steps).run()


def run_communication_loop(
    steps: list[CommunicationStep], tick_ms: int, cycles: int | None = None
):
    return CommunicationStateMachine(steps).run_periodic(tick_ms, cycles)





def _result_value(result):
    return result.value if isinstance(result, OSTECHResult) else result


def check_sr830():
    if SR830 is None:
        return False, "COM3 konnte nicht geöffnet werden; SR830 ist nicht angeschlossen."
    try:
        sr830_id = ask_SR830("*IDN?")
    except Exception as error:
        return False, f"Abfrage *IDN? fehlgeschlagen: {type(error).__name__}: {error}"
    if sr830_id != EXPECTED_SR830_ID:
        return False, (
            f"Falsche Geräte-ID. Erwartet: {EXPECTED_SR830_ID!r}; "
            f"erhalten: {sr830_id!r}."
        )
    return True, f"Gerät erkannt: {sr830_id}"


def check_ostech():
    if OSTECH is None:
        return False, "COM4 konnte nicht geöffnet werden; OSTECH ist nicht angeschlossen."
    try:
        serial_number = _result_value(
            LabOSTECHCommand(OSTECH, OSTECHCommand.GVN)
        )
    except Exception as error:
        return False, f"Abfrage GVN fehlgeschlagen: {type(error).__name__}: {error}"
    if serial_number != EXPECTED_OSTECH_SERIAL_NUMBER:
        return False, (
            f"Falsche Seriennummer. Erwartet: {EXPECTED_OSTECH_SERIAL_NUMBER}; "
            f"erhalten: {serial_number!r}."
        )
    return True, f"Gerät erkannt: Seriennummer {serial_number}"


def check_devices_before_measurement():
    sr830_ready, _ = check_sr830()
    ostech_ready, _ = check_ostech()
    TestingLog.Log(
        "KOM_Test", "STATE_MACHINE", "I",
        "Geräteprüfung erfolgreich; Messablauf wird gestartet.",
        "Startup check", Test_Tag,
    ) if sr830_ready and ostech_ready else None
    return sr830_ready and ostech_ready


def create_measurement_steps(delay_ms: int = 100):
    return [
        CommunicationStep("SR830 SNAP 1,2,3,4,10,11", lambda: ask_SR830("SNAP? 1,2,3,4,10,11"), delay_ms),
        CommunicationStep("SR830 SNAP 5,6,7,8,9", lambda: ask_SR830("SNAP? 5,6,7,8,9"), delay_ms),
        CommunicationStep("SR830 PHAS", lambda: ask_SR830("PHAS"), delay_ms),
        CommunicationStep("SR830 FREQ", lambda: ask_SR830("FREQ"), delay_ms),
        CommunicationStep("OSTECH LTM", lambda: LabOSTECHCommand(OSTECH, OSTECHCommand.LTM), delay_ms),
        CommunicationStep("OSTECH LCA", lambda: LabOSTECHCommand(OSTECH, OSTECHCommand.LCA), delay_ms),
        CommunicationStep("OSTECH LVA", lambda: LabOSTECHCommand(OSTECH, OSTECHCommand.LVA), delay_ms),
        CommunicationStep("OSTECH LTA", lambda: LabOSTECHCommand(OSTECH, OSTECHCommand.XTA), delay_ms),
        CommunicationStep("OSTECH GT", lambda: LabOSTECHCommand(OSTECH, OSTECHCommand.GT), delay_ms),
        CommunicationStep("OSTECH GS", lambda: LabOSTECHCommand(OSTECH, OSTECHCommand.GS), delay_ms),
    ]


def start_measurement(tick_ms: int = 100, cycles: int | None = None):
    check_devices_before_measurement()
    return run_communication_loop(create_measurement_steps(tick_ms), tick_ms, cycles)


def _run_device_steps(
    source: str,
    steps: list[CommunicationStep],
    tick_ms: int,
    cycles: int | None,
    stop_requested: threading.Event,
    publish: Callable[[object], None],
):
    if source == "SR830":
        ready, detail = check_sr830()
    else:
        ready, detail = check_ostech()
    if not ready:
        publish({"step": "startup", "value": f"{source} nicht bereit: {detail}"})
        return

    cycle_number = 0
    while cycles is None or cycle_number < cycles:
        for step in steps:
            if stop_requested.is_set():
                return
            try:
                value = step.action()
                value = step.processor(value) if step.processor is not None else value
                publish({"step": step.name, "value": value})
            except Exception as error:
                publish({
                    "step": "error",
                    "value": (
                        f"Befehl {step.name!r} fehlgeschlagen: "
                        f"{type(error).__name__}: {error}"
                    ),
                })
                return

            if stop_requested.wait(step.delay_ms / 1000):
                return

        cycle_number += 1
        if stop_requested.wait(max(0, tick_ms / 1000)):
            return


def _create_sr830_thread_steps(delay_ms: int):
    return [
        CommunicationStep("SNAP 1,2,3,4,10,11", lambda: ask_SR830("SNAP? 1,2,3,4,10,11"), delay_ms),
        CommunicationStep("SNAP 5,6,7,8,9", lambda: ask_SR830("SNAP? 5,6,7,8,9"), delay_ms),
        CommunicationStep("PHAS", lambda: ask_SR830("PHAS"), delay_ms),
        CommunicationStep("FREQ", lambda: ask_SR830("FREQ"), delay_ms),
    ]


def _create_ostech_thread_steps(delay_ms: int):
    return [
        CommunicationStep("LTM", lambda: LabOSTECHCommand(OSTECH, OSTECHCommand.LTM), delay_ms),
        CommunicationStep("LCA", lambda: LabOSTECHCommand(OSTECH, OSTECHCommand.LCA), delay_ms),
        CommunicationStep("LVA", lambda: LabOSTECHCommand(OSTECH, OSTECHCommand.LVA), delay_ms),
        CommunicationStep("LTA", lambda: LabOSTECHCommand(OSTECH, OSTECHCommand.XTA), delay_ms),
        CommunicationStep("GT", lambda: LabOSTECHCommand(OSTECH, OSTECHCommand.GT), delay_ms),
        CommunicationStep("GS", lambda: LabOSTECHCommand(OSTECH, OSTECHCommand.GS), delay_ms),
    ]


def start_threaded_measurement(
    tick_ms: int | None = None,
    cycles: int | None = None,
    gui_handler: Callable[[ThreadMessage], None] | None = None,
):
    sr830_tick_ms = TAKT_SR830 if tick_ms is None else tick_ms
    ostech_tick_ms = TAKT_OSTTECH if tick_ms is None else tick_ms
    cycle_limit = CYCLES if cycles is None else cycles

    def log_handler(message: ThreadMessage):
        payload = message.value if isinstance(message.value, dict) else {"value": message.value}
        level = {"result": "T", "status": "I", "error": "E"}[message.kind]
        action = payload.get("step", message.kind)
        value = payload.get("value", "")
        TestingLog.Log(
            "KOM_Test", message.source, level, str(action),
            str(value), f"{message.kind} im {message.source}-Thread", Test_Tag,
        )

    def default_gui_handler(message: ThreadMessage):
        payload = message.value if isinstance(message.value, dict) else {"value": message.value}
        print(f"[{message.source}] {payload.get('step', message.kind)}: {payload.get('value', '')}")

    threads = CommunicationThreads(
        lambda stop, publish: _run_device_steps(
            "SR830", _create_sr830_thread_steps(sr830_tick_ms), sr830_tick_ms,
            cycle_limit, stop, publish
        ),
        lambda stop, publish: _run_device_steps(
            "OSTECH", _create_ostech_thread_steps(ostech_tick_ms), ostech_tick_ms,
            cycle_limit, stop, publish
        ),
        log_handler,
        gui_handler or default_gui_handler,
        gui_interval_ms=TAKT_GUI,
    )
    threads.start()
    threads.publish("SYSTEM", "status", "whileTest gestartet; Geräte-Threads laufen parallel.")
    return threads


def run_threaded_measurement(tick_ms: int | None = None, cycles: int | None = None):
    threads = start_threaded_measurement(tick_ms, cycles)
    try:
        while threads.sr830.thread.is_alive() or threads.ostech.thread.is_alive():
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        threads.stop()


def ask_SR830(Command: str):
    SR830.write((str(Command) + "\r").encode("ascii"))
    SR830.flush()
    ValueSR830 = SR830.read_until(b"\r").decode("ascii", errors="replace").strip()
    return ValueSR830



def ask_OSTECH(Command: str):
    OSTECH.write((str(Command) + "\r").encode("ascii"))
    OSTECH.flush()
    ValueOSTECH = OSTECH.read_until(b"\r").decode("ascii", errors="replace").strip()
    return ValueOSTECH




def Test_SR830():
    ask_SR830("*IDN?")
    ask_SR830("SRAT 0")
    ask_SR830("SRAT 0")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 1")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 2")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 3")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 4")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 5")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 6")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 7")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 8")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 9")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 10")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 11")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 12")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 13")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 14")

    ask_SR830("SEND?")
    ask_SR830("SEND 1")
    ask_SR830("SEND?")
    ask_SR830("SEND 2")
    ask_SR830("SEND?")

    ask_SR830("TRIG")

    ask_SR830("TSTR ?")
    ask_SR830("TSTR 1")
    ask_SR830("TSTR ?")
    ask_SR830("TSTR 2")
    ask_SR830("TSTR ?")

    ask_SR830("STRT")

    ask_SR830("PAUS")

    ask_SR830("REST")

    ask_SR830("OAUX? 1")
    ask_SR830("OAUX? 2")
    ask_SR830("OAUX? 3")
    ask_SR830("OAUX? 4")

    ask_SR830("OUTP? 1")
    ask_SR830("OUTP? 2")
    ask_SR830("OUTP? 3")
    ask_SR830("OUTP? 4")

    ask_SR830("SNAP? 1,2")
    ask_SR830("SNAP? 3,2")
    ask_SR830("SNAP? 5,6")
    ask_SR830("SNAP? 7,8")
    ask_SR830("SNAP? 9,10")
    ask_SR830("SNAP? 10,11")

    ask_SR830("SNAP? 1,2,3,4")
    ask_SR830("SNAP? 5,6,7,8")
    ask_SR830("SNAP? 9,10,11")

    ask_SR830("SNAP? 1,2,3,4,10,11")
    ask_SR830("SNAP? 5,6,7,8,9")
    ask_SR830("PHAS")
    ask_SR830("FREQ")

    ask_SR830("SPTS?")

    ask_SR830("TRCA? 1,2,1")
    ask_SR830("TRCA? 2,2,1")

    ask_SR830("TRCB? 1,2,1")
    ask_SR830("TRCB? 2,2,1")

    ask_SR830("TRCL? 2,2,1")
    ask_SR830("TRCL? 2,2,1")

    ask_SR830("FAST? 1")
    ask_SR830("FAST?")

    ask_SR830("STRD")

    ask_SR830("FAST? 2")
    ask_SR830("FAST?")

    ask_SR830("STRD")

    ask_SR830("FAST? 3")
    ask_SR830("FAST?")

    ask_SR830("STRD")

    ask_SR830("FAST 1")
    ask_SR830("FAST?")

    ask_SR830("STRD")

    ask_SR830("FAST 2")
    ask_SR830("FAST?")

    ask_SR830("STRD")

    ask_SR830("FAST 3")
    ask_SR830("FAST?")

    ask_SR830("STRD")

    ask_SR830("*RST")

    ask_SR830("*IDN?")

    ask_SR830("LOCL? 1")

    ask_SR830("LOCL?")

    ask_SR830("*RST")

    ask_SR830("LOCL 1")

    ask_SR830("LOCL?")

    ask_SR830("*RST")

    ask_SR830("LOCL? 2")

    ask_SR830("LOCL?")

    ask_SR830("*RST")

    ask_SR830("OVRM? 0")

    ask_SR830("OVRM?")

    ask_SR830("OVRM? 1")

    ask_SR830("OVRM?")

    ask_SR830("*RST")

    ask_SR830("TRIG")

    ask_SR830("*ESE?")
    ask_SR830("*ESR?")
    ask_SR830("*SRE?")
    ask_SR830("*STB?")
    ask_SR830("*PSC?")
    ask_SR830("ERRE?")
    ask_SR830("ERRS?")
    ask_SR830("LIAE?")
    ask_SR830("LIAS?")

    ask_SR830("*STB?")

    ask_SR830("*CLS")




    print("Kom Test for ST830 Done")
    SR830.close()


def Test_OSTech():

    ask_OSTECH("LCA")
    ask_OSTECH("LVA")
    ask_OSTECH("LTA")
    ask_OSTECH("GT")


    ask_OSTECH("GE")

    ask_OSTECH("GF")

    ask_OSTECH("GFD")

    ask_OSTECH("GX")

    ask_OSTECH("GT")

    ask_OSTECH("GVS")

    ask_OSTECH("GVN")

    ask_OSTECH("GS")

    ask_OSTECH("GM")

    ask_OSTECH("GSP")

    ask_OSTECH("GSR")




    print("Kom Test for ST830 Done")
    OSTECH.close()

# Test_SR830()
#Test_OSTech()


if __name__ == "__main__":
    run_threaded_measurement()


"""Public SR830 command catalog and high-level command API.

This module owns the user-facing command metadata and the application-side API:
- command definitions (what can be sent)
- convenience helpers (send/read helpers)
- structured logging through ``Log.Log``

The actual serial-port traffic and the binary/text encoding decisions stay in
``Komunikation.py``. This keeps the hardware protocol isolated from user-level
command usage.
"""

from collections import namedtuple


SR830CommandInfo = namedtuple("SR830CommandInfo", ["command", "type", "unit", "description"])


class SR830G:
    """Query-only SR830 commands: read-only / monitoring commands."""

    OUTP_X = SR830CommandInfo("OUTP? 1", float, "V", "Liest X-Wert")
    OUTP_Y = SR830CommandInfo("OUTP? 2", float, "V", "Liest Y-Wert")
    OUTP_R = SR830CommandInfo("OUTP? 3", float, "V", "Liest R-Wert (Magnitude)")
    OUTP_THETA = SR830CommandInfo("OUTP? 4", float, "deg", "Liest Theta (Phase)")

    OUTR_CH1 = SR830CommandInfo("OUTR? 1", float, "", "Liest CH1 Display")
    OUTR_CH2 = SR830CommandInfo("OUTR? 2", float, "", "Liest CH2 Display")

    OAUX_IN1 = SR830CommandInfo("OAUX? 1", float, "V", "Liest Aux Input 1")
    OAUX_IN2 = SR830CommandInfo("OAUX? 2", float, "V", "Liest Aux Input 2")
    OAUX_IN3 = SR830CommandInfo("OAUX? 3", float, "V", "Liest Aux Input 3")
    OAUX_IN4 = SR830CommandInfo("OAUX? 4", float, "V", "Liest Aux Input 4")

    SNAP_XY = SR830CommandInfo("SNAP? 1,2", str, "V, V", "Gleichzeitiges Lesen von X und Y")
    SNAP_R_THETA = SR830CommandInfo("SNAP? 3,4", str, "V, deg", "Gleichzeitiges Lesen von R und Theta")
    SNAP_XY_R_TH = SR830CommandInfo("SNAP? 1,2,3,4", str, "V, V, V, deg", "Liest X, Y, R und Theta")
    SNAP_ALL_MAIN = SR830CommandInfo("SNAP? 1,2,3,4,10,11", str, "V, V, V, deg, V, V", "Liest X, Y, R, Theta, CH1 und CH2")
    SNAP_AUX_FREQ = SR830CommandInfo("SNAP? 5,6,7,8,9", str, "V, V, V, V, Hz", "Liest Aux1, Aux2, Aux3, Aux4 und RefFreq")

    SPTS = SR830CommandInfo("SPTS?", int, "points", "Liest Anzahl der gespeicherten Datenpunkte")
    IDN = SR830CommandInfo("*IDN?", str, "", "Liest die Geräte-Identifikation")
    ERRS = SR830CommandInfo("ERRS?", int, "", "Liest das Error Status Byte")
    LIAS = SR830CommandInfo("LIAS?", int, "", "Liest das LIA Status Byte")

    @staticmethod
    def read(command_info, return_type=None):
        """Read from the SR830 using command metadata from this class."""
        import Komunikation
        import Log

        actual_type = command_info.type if return_type is None else return_type
        command_name = getattr(command_info, "command", str(command_info))
        Log.Log("Send", "SR830", "Running", command_name, "read request", "query")
        return Komunikation.ask_SR830(command_info, return_type=actual_type)

    @classmethod
    def all(cls):
        """Return all query commands as a list of (name, command_info)."""
        return [
            (name, value)
            for name, value in cls.__dict__.items()
            if not name.startswith("__") and isinstance(value, SR830CommandInfo)
        ]


class SR830S:
    """Set-only SR830 commands: configuration and action commands."""

    PHAS = SR830CommandInfo("PHAS", float, "deg", "Setzt Phasenverschiebung (-360.00 bis 729.99)")
    FMOD = SR830CommandInfo("FMOD", int, "", "Referenzquelle: 0=External, 1=Internal")
    FREQ = SR830CommandInfo("FREQ", float, "Hz", "Interne Oszillatorfrequenz (0.001 bis 102000)")
    RSLP = SR830CommandInfo("RSLP", int, "", "Ext. Trigger Flanke: 0=Sine, 1=TTL Rising, 2=TTL Falling")
    HARM = SR830CommandInfo("HARM", int, "", "Detektions-Harmonische (1 bis 19999)")
    SLVL = SR830CommandInfo("SLVL", float, "V", "Sinus-Ausgangsamplitude (0.004 bis 5.000 Vrms)")

    ISRC = SR830CommandInfo("ISRC", int, "", "Eingang: 0=A, 1=A-B, 2=I(1MOhm), 3=I(100MOhm)")
    IGND = SR830CommandInfo("IGND", int, "", "Shield Erdung: 0=Float, 1=Ground")
    ICPL = SR830CommandInfo("ICPL", int, "", "Kopplung: 0=AC, 1=DC")
    ILIN = SR830CommandInfo("ILIN", int, "", "Netzfilter: 0=Out, 1=Line, 2=2xLine, 3=Both")

    SENS = SR830CommandInfo("SENS", int, "", "Sensitivität (0=2nV/fA bis 26=1V/uA)")
    RMOD = SR830CommandInfo("RMOD", int, "", "Reserve Mode: 0=High, 1=Normal, 2=Low Noise")
    OFLT = SR830CommandInfo("OFLT", int, "", "Zeitkonstante (0=10us bis 19=30ks)")
    OFSL = SR830CommandInfo("OFSL", int, "", "Low Pass Filter Slope: 0=6, 1=12, 2=18, 3=24 dB/oct")
    SYNC = SR830CommandInfo("SYNC", int, "", "Synchronous Filter: 0=Off, 1=On (<200Hz)")

    AGAN = SR830CommandInfo("AGAN", None, "", "Führt Auto Gain aus")
    ARSV = SR830CommandInfo("ARSV", None, "", "Führt Auto Reserve aus")
    APHS = SR830CommandInfo("APHS", None, "", "Führt Auto Phase aus")

    SRAT = SR830CommandInfo("SRAT", int, "Hz", "Data Sample Rate (0=62.5mHz bis 14=Trigger)")
    SEND = SR830CommandInfo("SEND", int, "", "Scan Mode: 0=1 Shot, 1=Loop")
    STRT = SR830CommandInfo("STRT", None, "", "Startet/Setzt den Scan fort")
    PAUS = SR830CommandInfo("PAUS", None, "", "Pausiert den Scan")
    REST = SR830CommandInfo("REST", None, "", "Setzt den Datenpuffer zurück (Reset)")


SENSITIVITY_VALUES = {
    "2 nV/fA": 0,
    "5 nV/fA": 1,
    "10 nV/fA": 2,
    "20 nV/fA": 3,
    "50 nV/fA": 4,
    "100 nV/fA": 5,
    "200 nV/fA": 6,
    "500 nV/fA": 7,
    "1 uV/pA": 8,
    "2 uV/pA": 9,
    "5 uV/pA": 10,
    "10 uV/pA": 11,
    "20 uV/pA": 12,
    "50 uV/pA": 13,
    "100 uV/pA": 14,
    "200 uV/pA": 15,
    "500 uV/pA": 16,
    "1 mV/nA": 17,
    "2 mV/nA": 18,
    "5 mV/nA": 19,
    "10 mV/nA": 20,
    "20 mV/nA": 21,
    "50 mV/nA": 22,
    "100 mV/nA": 23,
    "200 mV/nA": 24,
    "500 mV/nA": 25,
    "1 V/uA": 26,
}

TIME_CONSTANT_VALUES = {
    "10 us": 0,
    "30 us": 1,
    "100 us": 2,
    "300 us": 3,
    "1 ms": 4,
    "3 ms": 5,
    "10 ms": 6,
    "30 ms": 7,
    "100 ms": 8,
    "300 ms": 9,
    "1 s": 10,
    "3 s": 11,
    "10 s": 12,
    "30 s": 13,
    "100 s": 14,
    "300 s": 15,
    "1 ks": 16,
    "3 ks": 17,
    "10 ks": 18,
    "30 ks": 19,
}

RESERVE_VALUES = {"High Reserve": 0, "Normal": 1, "Low Noise": 2}
FILTER_SLOPE_VALUES = {"6 dB/oct": 0, "12 dB/oct": 1, "18 dB/oct": 2, "24 dB/oct": 3}
INPUT_CONFIG_VALUES = {"A": 0, "A-B": 1, "I (1M)": 2, "I (100M)": 3}
GROUNDING_VALUES = {"Float": 0, "Ground": 1}
COUPLING_VALUES = {"AC": 0, "DC": 1}
LINE_NOTCH_VALUES = {"Out": 0, "Line (50/60Hz)": 1, "2x Line": 2, "Both": 3}
SYNCHRONOUS_FILTER_VALUES = {"Off": 0, "On": 1}


def resolve_sr830_setting(command_name, value_name_or_index):
    """Translate a human-readable SR830 setting into the numeric index expected by the instrument."""
    mapping = {
        "SENS": SENSITIVITY_VALUES,
        "RMOD": RESERVE_VALUES,
        "OFLT": TIME_CONSTANT_VALUES,
        "OFSL": FILTER_SLOPE_VALUES,
        "ISRC": INPUT_CONFIG_VALUES,
        "IGND": GROUNDING_VALUES,
        "ICPL": COUPLING_VALUES,
        "ILIN": LINE_NOTCH_VALUES,
        "SYNC": SYNCHRONOUS_FILTER_VALUES,
    }.get(command_name.upper())
    if mapping is None:
        return value_name_or_index
    if isinstance(value_name_or_index, (int, float)):
        return int(value_name_or_index)
    if value_name_or_index in mapping:
        return mapping[value_name_or_index]
    for label, index in mapping.items():
        if str(value_name_or_index).strip().lower() == label.lower():
            return index
    raise ValueError(f"Unbekannter Wert für {command_name}: {value_name_or_index!r}")

    @staticmethod
    def write(command_info, value):
        """Write a value to the SR830 using the command metadata."""
        import Komunikation
        import Log

        command_name = getattr(command_info, "command", str(command_info))
        Log.Log("Send", "SR830", "Running", command_name, value, "set value")
        return Komunikation.send_SR830(command_info, value)

    @staticmethod
    def run(command_info):
        """Execute an action command without value."""
        import Komunikation
        import Log

        command_name = getattr(command_info, "command", str(command_info))
        Log.Log("Send", "SR830", "Running", command_name, "execute", "action command")
        return Komunikation.send_SR830(command_info, None)

    @classmethod
    def all(cls):
        """Return all set commands as a list of (name, command_info)."""
        return [
            (name, value)
            for name, value in cls.__dict__.items()
            if not name.startswith("__") and isinstance(value, SR830CommandInfo)
        ]


def _normalize_command(command):
    """Accept either metadata or a raw command string and return the command metadata."""
    if hasattr(command, "command"):
        return command
    if isinstance(command, str):
        for category in (SR830G, SR830S):
            for _, info in category.all():
                if info.command == command:
                    return info
        return command
    raise TypeError(f"Unbekannter SR830-Befehl: {command!r}")


def send(command, value=None):
    """Public API: send any SR830 command via the Send layer."""
    import Komunikation

    command_info = _normalize_command(command)
    if hasattr(command_info, "command"):
        return Komunikation.send_SR830(command_info, value)
    return Komunikation.send_SR830(command, value)


def read(command, return_type=None):
    """Public API: query any SR830 command via the Send layer."""
    import Komunikation

    command_info = _normalize_command(command)
    if hasattr(command_info, "command"):
        actual_type = command_info.type if return_type is None else return_type
        return Komunikation.ask_SR830(command_info, return_type=actual_type)
    return Komunikation.ask_SR830(command, return_type=return_type)


def set(command, value):
    """Public API: set a value on the SR830 via the Send layer."""
    return send(command, value)


def run(command):
    """Public API: execute an action command without a value."""
    return send(command, None)


def list_sr830_commands(kind=None):
    """Return all SR830 command metadata with optional filtering by get/set."""
    if kind is None:
        return SR830G.all() + SR830S.all()
    if kind.lower() in {"get", "g", "read", "query"}:
        return SR830G.all()
    if kind.lower() in {"set", "s", "write", "command"}:
        return SR830S.all()
    raise ValueError("kind muss 'get' oder 'set' sein.")


SR830GetCommands = SR830G
SR830SetCommands = SR830S
__all__ = [
    "SR830CommandInfo",
    "SR830G",
    "SR830S",
    "SR830GetCommands",
    "SR830SetCommands",
    "send",
    "read",
    "set",
    "run",
    "list_sr830_commands",
]
 
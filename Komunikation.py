"""Zentrale Kommunikation mit SR830 und OSTech."""

from __future__ import annotations

import time
from typing import Any, Optional

import serial

import Log


import numpy as np
from SWP_Calculation_PhaseVsFrequenz_v3 import process_live_measurement as prayForItToWork


SR830: Optional[Any] = None
OSTech: Optional[Any] = None
SR830_PORT: Optional[str] = None
OSTECH_PORT: Optional[str] = None
KOMMUNIKATIONSSTATUS = {"SR830": False, "OSTech": False}

SR830_READ_COMMANDS = {
    "SNAP", "SPTS", "IDN", "OAUX1", "OAUX2", "OAUX3", "OAUX4",
    "OUTP1", "OUTP2", "OUTP3", "OUTP4", "OUTR1", "OUTR2",
    "TRCA1", "TRCA2", "TRCB1", "TRCB2", "TRCL1", "TRCL2",
}
OSTECH_READ_COMMANDS = {
    "LCA", "LVA", "LPCA", "LPA", "LPF", "LZR", "xTCA", "xTVA",
    "GD", "GT", "GVS", "GVN", "GS", "GM",
}

SR830_SET_ARGUMENTS = {
    "PHAS": ("x",), "FMOD": ("i",), "FREQ": ("i",), "RSLP": ("i",),
    "HARM": ("i",), "SLVL": ("x",), "ISRC": ("i",), "IGND": ("i",),
    "LCPL": ("i",), "ILN": ("i",), "SENS": ("i",), "RMOD": ("i",),
    "OFLT": ("i",), "OFSL": ("i",), "SYNC": ("i",),
    "DDEF": ("i", "j", "k"), "FPOP": ("i", "j"),
    "OEXP": ("i", "x", "j"), "AOFF": ("i",), "AUXV": ("i", "x"),
    "OUTX": ("i",), "OVRM": ("i",), "AOXV": ("i", "x"),
    "KCLK": ("i",), "ALRM": ("i",), "SSET": ("i",), "RSET": ("i",),
    "AGAN": (), "ARSV": (), "APHS": (),
}


def _open_port(port: str, baudrate: int, timeout: float, device_name: str):
    try:
        device = serial.Serial(port, baudrate, timeout=timeout)
        time.sleep(0.5)
        Log.LogMassage(port, "Info", "Communication", "OpenPort", device_name)
        return device
    except serial.SerialException as error:
        Log.LogMassage(port, "Warning", "Communication", str(error), device_name)
        return None


def _verfuegbare_ports(*bevorzugte_ports: str) -> list[str]:
    """Liefert bevorzugte Ports und danach alle aktuell sichtbaren COM-Ports."""
    from serial.tools import list_ports

    ports = list(bevorzugte_ports)
    ports.extend(info.device for info in list_ports.comports())
    return list(dict.fromkeys(port for port in ports if port))


def _probe(device: Any, command: str) -> str:
    """Sendet einen kurzen Identifikationsbefehl ohne zusaetzliches Logging."""
    try:
        device.reset_input_buffer()
        device.write(f"{command}\r".encode("ascii"))
        return device.read_until(b"\r").decode("ascii", errors="replace").strip()
    except (serial.SerialException, OSError):
        return ""


def _gueltige_antwort(response: str) -> bool:
    """Filtert leere Antworten und typische Fehlerantworten der Geraete."""
    normalized = response.strip().lower()
    return bool(normalized) and normalized not in {"?", "error", "err", "-1"}


def _sr830_antwort(response: str) -> bool:
    normalized = response.lower()
    return _gueltige_antwort(response) and ("sr830" in normalized or "stanford" in normalized)


def _konfiguriere_port(device: Any, baudrate: int, timeout: float) -> Any:
    """Setzt die verbindungsweiten Parameter nach erfolgreicher Pruefung."""
    device.baudrate = baudrate
    device.timeout = timeout
    device.bytesize = serial.EIGHTBITS
    device.parity = serial.PARITY_NONE
    device.stopbits = serial.STOPBITS_ONE
    return device


def _suche_geraete(
    sr830_port: str,
    ostech_port: str,
    baudrate: int,
    timeout: float,
) -> tuple[Optional[Any], Optional[Any], Optional[str], Optional[str]]:
    """Prueft jeden sichtbaren Port einmal und ordnet die Geraete Antworten zu."""
    sr830 = None
    ostech = None
    found_sr830_port = None
    found_ostech_port = None

    for port in _verfuegbare_ports(sr830_port, ostech_port):
        if sr830 is not None and ostech is not None:
            break
        device = _open_port(port, baudrate, 0.5, "Port-Scan")
        if device is None:
            continue

        sr_response = _probe(device, "*IDN?")
        if sr830 is None and _sr830_antwort(sr_response):
            sr830 = _konfiguriere_port(device, baudrate, timeout)
            found_sr830_port = port
            Log.LogMassage(port, "Info", "Communication", "SR830 erkannt", sr_response)
            continue

        ostech_response = _probe(device, "GVN")
        if ostech is None and _gueltige_antwort(ostech_response):
            ostech = _konfiguriere_port(device, baudrate, timeout)
            found_ostech_port = port
            Log.LogMassage(port, "Info", "Communication", "OSTech erkannt", ostech_response)
            continue

        device.close()
        Log.LogMassage(port, "Info", "Communication", "Keine passende Hardwareantwort", "Port-Scan")

    return sr830, ostech, found_sr830_port, found_ostech_port


def initialisiere_kommunikation(
    sr830_port: str = "COM3",
    ostech_port: str = "COM5",
    baudrate: int = 9600,
    timeout: float = 2.0,
) -> tuple[Optional[Any], Optional[Any]]:
    """Scannt die COM-Ports einmal, prueft die Kommunikation und konfiguriert sie."""
    global SR830, OSTech, SR830_PORT, OSTECH_PORT, KOMMUNIKATIONSSTATUS
    if SR830 is None or OSTech is None:
        SR830, OSTech, SR830_PORT, OSTECH_PORT = _suche_geraete(
            sr830_port, ostech_port, baudrate, timeout
        )
    KOMMUNIKATIONSSTATUS = {"SR830": SR830 is not None, "OSTech": OSTech is not None}
    return SR830, OSTech


def schliesse_kommunikation() -> None:
    """Schliesst beide Schnittstellen, sofern sie geoeffnet sind."""
    global SR830, OSTech, SR830_PORT, OSTECH_PORT, KOMMUNIKATIONSSTATUS
    for device in (SR830, OSTech):
        if device is not None and getattr(device, "is_open", True):
            device.close()
    SR830 = None
    OSTech = None
    SR830_PORT = None
    OSTECH_PORT = None
    KOMMUNIKATIONSSTATUS = {"SR830": False, "OSTech": False}


def frequenz_sweep_durchfuehren(
        f_start: float = 0.1,
        f_end: float = 500.0,
        schritte: int = 100
) -> tuple[np.ndarray, np.ndarray]:

    # Frequenzband von f_start bis f_end logarithmisch erzeugen
    f_sweep = np.logspace(np.log10(f_start), np.log10(f_end), schritte)
    phi_gemessen = []

    for f in f_sweep:
        # Frequenz am SR830 setzen
        setValue(Command="FREQ", x=f)

        # Dynamische Einschwingzeit: Mind. 0.3s oder 3 Periodenlängen (3/f)
        wartezeit = max(0.3, 3.0 / f)
        time.sleep(wartezeit)

        # SNAP liest Magnitude (i=9) und Phase (j=10) aus
        antwort = getValue(Command="SNAP", i=9, j=10)

        try:
            _, phase_val = antwort.split(",")
            phi_gemessen.append(float(phase_val))
        except (ValueError, IndexError):
            Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"), "Warning", "Sweep", f"Fehler bei {f} Hz", "SR830")

    f_array = np.array(f_sweep)
    phi_array = np.array(phi_gemessen)

    # Direkt an den Evaluator zur Schichtdickenberechnung übergeben
    d_fit, d_err, r2, _ = prayForItToWork(f_array, phi_array)

    return f_array, phi_array


def _send_and_read(device: Any, command: str, device_name: str) -> str:
    if device is None:
        Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"), "Communication", "Read", f"Keine Hardware fuer {command} verbunden!", device_name)
        return "N/A"
    Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"), "Communication", "Send", command, device_name)
    device.write(f"{command}\r".encode("ascii"))
    value = device.read_until(b"\r").decode("ascii", errors="replace").strip()
    Log.LogMassage(time.strftime("%Y-%m-%d %H:%M:%S"), "Communication", "Receive", value, device_name)
    return value


def _sr830_command(command: str, i: int, j: int, k: int) -> str:
    query_templates = {
        "IDN": "*IDN?",
        "SNAP": f"SNAP? {i},{j}",
        "SPTS": "SPTS?",
    }
    if command in query_templates:
        return query_templates[command]
    if command[:4] in {"OAUX", "OUTP", "OUTR"}:
        return f"{command[:4]}? {command[-1]}"
    return f"{command[:4]}? {command[-1]},{j},{k}"


def getValue(Init=None, Command: str = "", i: int = 0, j: int = 0, k: int = 0) -> str:
    """Liest einen bekannten SR830- oder OSTech-Befehl."""
    if Command in SR830_READ_COMMANDS:
        return _send_and_read(Init if Init is not None else SR830, _sr830_command(Command, i, j, k), "SR830")
    if Command in OSTECH_READ_COMMANDS:
        return _send_and_read(Init if Init is not None else OSTech, Command, "OSTech")
    raise ValueError(f"Unbekannter Kommunikationsbefehl: {Command}")


def setValue(
    Init=None,
    Command: str = "",
    i: int = 0,
    j: int = 0,
    k: int = 0,
    l: int = 0,
    m: int = 0,
    f: int = 0,
    x: Any = 0,
    y: int = 0,
    z: int = 0,
    s: int = 0,
    **kwargs,
) -> str:
    """Setzt einen SR830-Parameter ueber eine zentrale Befehlsdefinition."""
    if Command not in SR830_SET_ARGUMENTS:
        raise ValueError(f"Unbekannter SR830-Setzbefehl: {Command}")

    arguments = {"i": i, "j": j, "k": k, "l": l, "m": m, "f": f, "x": x, "y": y, "z": z, "s": s}
    values = tuple(arguments[name] for name in SR830_SET_ARGUMENTS[Command])
    command_text = Command + (" " + " ".join(map(str, values)) if values else "")
    return _send_and_read(Init if Init is not None else SR830, command_text, "SR830")


def sr830_get(command: str, i: int = 0, j: int = 0, k: int = 0) -> str:
    """Liest gezielt vom SR830."""
    if command not in SR830_READ_COMMANDS:
        raise ValueError(f"Unbekannter SR830-Lesebefehl: {command}")
    return getValue(SR830, command, i, j, k)


def ostech_get(command: str) -> str:
    """Liest gezielt vom OSTech-Controller."""
    if command not in OSTECH_READ_COMMANDS:
        raise ValueError(f"Unbekannter OSTech-Lesebefehl: {command}")
    return getValue(OSTech, command)


initialize_communication = initialisiere_kommunikation
close_communication = schliesse_kommunikation
get_value = getValue
set_value = setValue
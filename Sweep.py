"""Frequenzsweep am SR830 mit zwei Datenwegen.

Ablauf pro Frequenzstufe:
    1. FREQ am SR830 setzen (interne Referenz)
    2. warten, bis der Lock-in eingeschwungen ist
    3. SNAP? 4,9 lesen -> Theta (Phase) und Referenzfrequenz
    4. Messpunkt auf zwei Wegen ausgeben:
         a) Strang 1: eigene CSV-Datei (Format wie parse_lockin_csv es erwartet)
         b) Strang 2: State.live_sweep_data (Live-Variable fuer die Berechnung)

Die Hardware-Zugriffe laufen ueber Send.py bzw. Komunikation.py und teilen sich
damit den SR830_LOCK mit den Polling-Threads. Der Runner selbst fasst keine
Tkinter-Widgets an; die GUI fragt ``status`` und ``State.live_sweep_data`` per
Timer ab.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime

import numpy as np

import Komunikation
import Log
import Send
import State

F_MIN_HZ = 0.001
F_MAX_HZ = 102000.0

# Zeitkonstanten des SR830 in Sekunden, Index = Wert des OFLT-Befehls.
TIME_CONSTANT_SECONDS = (
    10e-6, 30e-6, 100e-6, 300e-6, 1e-3, 3e-3, 10e-3, 30e-3, 100e-3, 300e-3,
    1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1e3, 3e3, 10e3, 30e3,
)


class NoDeviceError(RuntimeError):
    """Kein SR830 verbunden bzw. kein passender COM-Port gefunden."""


class SweepConfigError(ValueError):
    """Ungueltige Sweep-Parameter."""


class SweepError(RuntimeError):
    """Fehler waehrend des laufenden Sweeps."""


@dataclass(frozen=True)
class SweepConfig:
    """Parameter eines Frequenzsweeps."""

    f_start: float = 10.0
    f_end: float = 10000.0
    n_points: int = 25
    log_spacing: bool = True
    settle_factor: float = 5.0   # Wartezeit = settle_factor * Zeitkonstante
    min_wait_s: float = 0.2      # absolute Untergrenze pro Stufe

    def validate(self) -> "SweepConfig":
        for name, value in (("Start", self.f_start), ("Ende", self.f_end)):
            if not (F_MIN_HZ <= value <= F_MAX_HZ):
                raise SweepConfigError(
                    f"{name}-Frequenz {value} Hz liegt ausserhalb von "
                    f"{F_MIN_HZ}-{F_MAX_HZ:.0f} Hz.")
        if self.f_start >= self.f_end:
            raise SweepConfigError("Die Startfrequenz muss kleiner als die Endfrequenz sein.")
        if int(self.n_points) < 2:
            raise SweepConfigError("Ein Sweep braucht mindestens 2 Punkte.")
        if self.settle_factor <= 0 or self.min_wait_s < 0:
            raise SweepConfigError("Wartezeit-Parameter muessen positiv sein.")
        return self

    def frequencies(self) -> np.ndarray:
        """Frequenzliste (aufsteigend), logarithmisch oder linear verteilt."""
        self.validate()
        n = int(self.n_points)
        if self.log_spacing:
            return np.logspace(np.log10(self.f_start), np.log10(self.f_end), n)
        return np.linspace(self.f_start, self.f_end, n)


def ensure_device_available() -> None:
    """Wirft ``NoDeviceError``, wenn kein SR830 fuer einen Sweep nutzbar ist."""
    port = Komunikation.SR830
    # close_devices() schliesst den Port, setzt Komunikation.SR830 aber nicht auf None.
    if port is None or not getattr(port, "is_open", True):
        ports = State.AVAILABLE_COM_PORTS
        hint = "kein COM-Port gefunden" if not ports else f"COM-Ports {ports} ohne SR830"
        raise NoDeviceError(f"Es ist kein SR830 verbunden ({hint}).")


# ---------------------------------------------------------------------------
# Standard-Hardwarezugriffe (austauschbar, z.B. fuer Tests)
# ---------------------------------------------------------------------------
def _hw_check_reference_internal() -> None:
    if int(Send.read("FMOD?", return_type=int)) == 0:
        raise SweepError(
            "Der SR830 steht auf externer Referenz (FMOD=0); FREQ hat dann keine "
            "Wirkung. Bitte auf interne Referenz stellen.")


def _hw_set_frequency(freq_hz: float) -> None:
    Send.set(Send.SR830S.FREQ, float(f"{freq_hz:.7g}"))


def _hw_time_constant_s() -> float:
    index = int(Send.read("OFLT?", return_type=int))
    return TIME_CONSTANT_SECONDS[index]


def _hw_read_point() -> tuple[float, float]:
    """Liefert (Referenzfrequenz in Hz, Theta in Grad) aus einem SNAP-Aufruf."""
    response = Send.read("SNAP? 4,9", return_type=str)
    theta, freq = (float(v) for v in response.split(","))
    return freq, theta


def make_sweep_csv_path() -> str:
    """Pfad der Sweep-CSV im Tagesordner der Logs."""
    name = datetime.now().strftime("%H-%M-%S") + "_sweep_probe.csv"
    return Log.make_log_path("M", base_name=name)


def _port_open(port) -> bool:
    return port is not None and getattr(port, "is_open", True)


def _raise_if_not_connected(missing: list[str]) -> None:
    if missing:
        ports = State.AVAILABLE_COM_PORTS
        hint = "kein COM-Port gefunden" if not ports else f"gefundene COM-Ports: {ports}"
        raise NoDeviceError(f"Nicht verbunden: {', '.join(missing)} ({hint}).")


def check_lockin_ready() -> None:
    """Prueft, ob der SR830 fuer einen Sweep nutzbar ist (unabhaengig vom Laser).

    :raises NoDeviceError: SR830 nicht verbunden bzw. Port nicht offen
    :raises SweepError: SR830 antwortet nicht oder steht auf externer Referenz
    """
    _raise_if_not_connected([] if _port_open(Komunikation.SR830) else ["SR830 (Lock-in)"])
    try:
        _hw_check_reference_internal()
        _hw_time_constant_s()
    except SweepError:
        raise
    except Exception as error:
        raise SweepError(f"Der SR830 antwortet nicht korrekt: {type(error).__name__}: {error}")


def check_laser_connected() -> None:
    """Prueft, ob der OSTECH-Laser-Controller verbunden ist (unabhaengig vom Lock-in).

    :raises NoDeviceError: OSTECH nicht verbunden bzw. Port nicht offen
    """
    _raise_if_not_connected([] if _port_open(Komunikation.OSTECH) else ["OSTECH (Laser)"])


def preflight(require_laser: bool = True) -> None:
    """Prueft, ob ein Sweep wirklich moeglich ist.

    Setzt sich aus den unabhaengig nutzbaren Einzelpruefungen
    ``check_lockin_ready()`` und (bei ``require_laser``) ``check_laser_connected()``
    zusammen. Beide Geraete koennen auch ohne Sweep benutzt werden; diese Funktion
    wird nur vor einem Sweep aufgerufen.

    :raises NoDeviceError: Geraet fehlt bzw. Port nicht offen
    :raises SweepError: Geraet vorhanden, aber nicht nutzbar (keine Antwort, externe Referenz)
    """
    missing = []
    if not _port_open(Komunikation.SR830):
        missing.append("SR830 (Lock-in)")
    if require_laser and not _port_open(Komunikation.OSTECH):
        missing.append("OSTECH (Laser)")
    _raise_if_not_connected(missing)
    check_lockin_ready()


# ---------------------------------------------------------------------------
# Externe Modulation des Lasers (LMAX analog / LMDX digital)
# ---------------------------------------------------------------------------
# Der OSTECH kann nicht erkennen, ob an AMOD/DMOD ein Kabel steckt; er meldet
# nur im Statuswort (GS), ob der Modus aktiv ist (0x0080 = LMAX ON, 0x0040 = LMDX ON).
# "Nutzbar/angeschlossen" wird daher so geprueft:
#   1. Laser-Controller verbunden,
#   2. LMAX: die Signalquelle (SR830 Sine Out -> AMOD) ist verbunden und liefert Spannung,
#   3. nach dem Senden: das Geraet bestaetigt den Modus im Statuswort (Readback).
# Der SR830 kann Sine Out nicht auf exakt 0 V setzen (Minimum 4 mV), deshalb eine Schwelle.
SINE_OUT_MIN_ACTIVE_V = 0.01

EXTERNAL_MODULATION_MODES = {
    "LMAX": "External Modulation (analog, AMOD)",
    "LMDX": "External Modulation (digital, DMOD)",
}
# Moegliche Schluessel des dekodierten Statusworts (State.OSTECH_STATUS / State.GS).
# Falls Komunikation.py die Bits anders benennt, hier die Namen ergaenzen.
_MODULATION_STATUS_KEYS = {
    "LMAX": ("lmax_on", "LMAX_ON", "LMAX", "lmax"),
    "LMDX": ("lmdx_on", "LMDX_ON", "LMDX", "lmdx"),
}


class ModulationUnavailableError(RuntimeError):
    """Externer Modulationsmodus (LMAX/LMDX) ist nicht nutzbar bzw. nicht angeschlossen."""


def _normalize_modulation_mode(mode: str) -> str:
    key = str(mode).strip().upper()
    if key not in EXTERNAL_MODULATION_MODES:
        raise ValueError(f"Unbekannter externer Modulationsmodus '{mode}' (erlaubt: LMAX, LMDX).")
    return key


def check_external_modulation(mode: str) -> None:
    """Prueft VOR dem Senden, ob ein externer Modulationsmodus nutzbar ist.

    :param mode: ``"LMAX"`` (analog) oder ``"LMDX"`` (digital)
    :raises ModulationUnavailableError: Laser nicht verbunden, bei LMAX zusaetzlich
        Signalquelle (SR830) nicht verbunden bzw. Sine Out aus
    """
    key = _normalize_modulation_mode(mode)
    label = EXTERNAL_MODULATION_MODES[key]
    if not _port_open(Komunikation.OSTECH):
        raise ModulationUnavailableError(
            f"{label} ({key}) nicht nutzbar: Der OSTECH-Laser-Controller ist nicht verbunden.")
    if key == "LMAX":
        if not _port_open(Komunikation.SR830):
            raise ModulationUnavailableError(
                f"{label} (LMAX) nicht nutzbar: Die Signalquelle (SR830 Sine Out -> AMOD) "
                "ist nicht verbunden.")
        try:
            level = float(Send.read("SLVL?", return_type=str).strip())
        except Exception as error:
            raise ModulationUnavailableError(
                f"{label} (LMAX) nicht nutzbar: Der SR830 antwortet nicht auf SLVL? "
                f"({type(error).__name__}: {error}).")
        if level < SINE_OUT_MIN_ACTIVE_V:
            raise ModulationUnavailableError(
                f"{label} (LMAX) nicht nutzbar: Sine Out des SR830 steht auf {level:.3f} V (AUS), "
                "am AMOD-Eingang liegt kein Modulationssignal an. "
                "Zuerst 'Start Sine Out' bzw. 'Apply Reference' ausfuehren.")


def modulation_mode_confirmed(mode: str):
    """Liest aus dem dekodierten Geraetestatus, ob der Modus aktiv ist.

    :return: True/False, oder None, wenn der Status keinen passenden Schluessel enthaelt
        (dann kann das Geraet den Modus nicht bestaetigen - kein Fehler).
    """
    key = _normalize_modulation_mode(mode)
    for source in (getattr(State, "OSTECH_STATUS", None), getattr(State, "GS", None)):
        if not isinstance(source, dict):
            continue
        for name in _MODULATION_STATUS_KEYS[key]:
            if name in source:
                return bool(source[name])
    return None


def verify_external_modulation(mode: str) -> None:
    """Prueft NACH dem Senden, ob der Laser-Controller den Modus bestaetigt.

    :raises ModulationUnavailableError: Geraet meldet den Modus nicht als aktiv
    """
    key = _normalize_modulation_mode(mode)
    confirmed = modulation_mode_confirmed(key)
    if confirmed is None:
        Log.Log("Calc", "Laser", "Warning", "Modulation",
                f"{key}: Statuswort enthaelt kein Bit fuer diesen Modus - nicht bestaetigt")
        return
    if not confirmed:
        raise ModulationUnavailableError(
            f"{EXTERNAL_MODULATION_MODES[key]} ({key}): Der Laser-Controller meldet den Modus "
            "nicht als aktiv (Status GS). Modus nicht verfuegbar oder Befehl nicht angenommen.")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
class SweepRunner:
    """Fuehrt einen Sweep in einem eigenen Thread aus.

    ``status``: idle | running | finished | stopped | error
    """

    def __init__(self, config: SweepConfig, csv_path: str | None = None, *,
                 set_frequency=None, read_point=None, time_constant=None,
                 check_reference=None, sleep=None):
        self.config = config.validate()
        self.csv_path = csv_path
        self._set_frequency = set_frequency or _hw_set_frequency
        self._read_point = read_point or _hw_read_point
        self._time_constant = time_constant or _hw_time_constant_s
        self._check_reference = check_reference or _hw_check_reference_internal
        self._stop = threading.Event()
        # Event.wait als unterbrechbares Warten; Tests koennen es ersetzen.
        self._sleep = sleep or (lambda s: self._stop.wait(s))
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._status = "idle"
        self._error: Exception | None = None
        self._f: list[float] = []
        self._phase: list[float] = []
        self.n_planned = int(config.n_points)

    # -- Zustand -----------------------------------------------------------
    @property
    def status(self) -> str:
        with self._lock:
            return self._status

    @property
    def error(self) -> Exception | None:
        with self._lock:
            return self._error

    @property
    def is_running(self) -> bool:
        return self.status == "running"

    @property
    def n_done(self) -> int:
        with self._lock:
            return len(self._f)

    def _set_status(self, status, error=None):
        with self._lock:
            self._status = status
            if error is not None:
                self._error = error

    # -- Steuerung ---------------------------------------------------------
    def start(self) -> None:
        if self.is_running:
            raise SweepError("Der Sweep laeuft bereits.")
        if self.csv_path is None:
            self.csv_path = make_sweep_csv_path()
        Log.ensure_log_file(self.csv_path)
        self._stop.clear()
        self._set_status("running")
        self._publish(finished=False)  # leere Live-Variable fuer diesen Sweep
        self._thread = threading.Thread(target=self._run, name="SweepRunner", daemon=True)
        self._thread.start()

    def stop(self, join_timeout: float | None = 2.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive() and join_timeout:
            thread.join(join_timeout)

    # -- Datenwege ---------------------------------------------------------
    def _publish(self, finished: bool) -> None:
        """Strang 2: komplette Momentaufnahme in die Live-Variable schreiben."""
        with self._lock:
            f, ph = list(self._f), list(self._phase)
        State.update_values({"live_sweep_data": {
            "f_probe": f,
            "phase_probe": ph,
            "n_planned": self.n_planned,
            "finished": finished,
            "csv_path": self.csv_path,
        }})

    def _write_csv_row(self, state, message, value, info=""):
        """Strang 1: eine Zeile im Log-Schema (Message/Value wie SNAP-Log)."""
        now = datetime.now()
        row = [now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), now.strftime("%f")[:3],
               "Comm", "SR830", state, message, value, info, "", "", "", ""]
        Log._append_row(self.csv_path, row)

    def _wait_for_settling(self, freq_hz: float) -> bool:
        """True, wenn vollstaendig gewartet wurde, False bei Stopp."""
        tau = self._time_constant()
        wait = max(self.config.settle_factor * tau, 3.0 / freq_hz, self.config.min_wait_s)
        self._sleep(wait)
        return not self._stop.is_set()

    # -- Thread ------------------------------------------------------------
    def _run(self) -> None:
        cfg = self.config
        freqs = cfg.frequencies()
        try:
            self._check_reference()
            self._write_csv_row("Start", "SWEEP START",
                                f"{cfg.f_start}-{cfg.f_end} Hz",
                                f"{len(freqs)} points, log={cfg.log_spacing}")
            Log.Log("Calc", "Sweep", "Start", "Sweep", f"{cfg.f_start}-{cfg.f_end} Hz",
                    f"{len(freqs)} points")
            for i, target in enumerate(freqs, start=1):
                if self._stop.is_set():
                    break
                self._set_frequency(float(target))
                if not self._wait_for_settling(float(target)):
                    break
                freq, theta = self._read_point()
                with self._lock:
                    self._f.append(freq)
                    self._phase.append(theta)
                # "SNAP 4,9" -> parse_lockin_csv liest Parameter 4 (Theta) + 9 (Freq)
                self._write_csv_row("Running", "SNAP 4,9", f"{theta},{freq}",
                                    f"sweep step {i}/{len(freqs)}")
                Log.Log("Calc", "Sweep", "Info", "Sweep step",
                        f"{i}/{len(freqs)} f={freq:.4g} Hz theta={theta:.3f} deg")
                self._publish(finished=False)
            final = "stopped" if self._stop.is_set() else "finished"
            self._write_csv_row("End", "SWEEP END", final, f"{self.n_done} points")
            Log.Log("Calc", "Sweep", "End", "Sweep", final, f"{self.n_done} points")
            self._publish(finished=True)
            self._set_status(final)
        except Exception as error:  # Hardwarefehler duerfen den Thread nicht still beenden
            try:
                self._write_csv_row("Error", "SWEEP ERROR", f"{type(error).__name__}: {error}")
                Log.Log("Calc", "Sweep", "Error", "Sweep", f"{type(error).__name__}: {error}")
            except Exception:
                pass
            self._publish(finished=True)
            self._set_status("error", error)

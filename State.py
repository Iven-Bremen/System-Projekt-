"""Shared application state and serial-port discovery.

This module is the small data hub between communication workers, simulation,
and the GUI. Device code writes decoded measurements with ``update_values``;
the GUI reads the latest values during its Tkinter refresh callback. No module
in this file performs serial I/O or changes widgets, which keeps the state
layer independent from both hardware and presentation.

The names follow the instrument manuals. SR830 values use names such as
``OUTP1`` and ``OAUX1``. OSTECH values use command names such as ``LCT`` and
``XTA``. ``GS`` and ``OSTECH_STATUS`` contain the decoded status-bit mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
import threading

from serial.tools import list_ports

# Shared display values used by the GUI and communication modules.
Experiment = "Test"
OUTP1 = 0.0
OUTP2 = 0.0
OUTP3 = 0.0
OUTP4 = 0.0
OUTR1 = 0.0
OUTR2 = 0.0
OAUX1 = 0.0
OAUX2 = 0.0
OAUX3 = 0.0
OAUX4 = 0.0
REFERENCE_FREQUENCY = 0.0
CH1_DISPLAY = 0.0
CH2_DISPLAY = 0.0
PHAS = 0.0
FREQ = 0.0
LCT = 0.0
XTA = 0.0
LVA = 0.0
XTCA = 0.0
XTVA = 0.0
LCA = 0.0
XTT = 0.0
LTM = 0.0
GT = 0.0
GS = {}
GVN = 0
LMDX = False
L = False
OSTECH_STATUS = {}
AVAILABLE_COM_PORTS = []
SIGNAL_MAGNITUDE = 0.0
SIGNAL_PHASE = 0.0
CALCULATION_STATUS = "IDLE"
_values_lock = threading.Lock()

def update_values(values: dict[str, object]) -> None:
	"""Atomically publish one or more decoded device values.

	Unknown names are ignored so a diagnostic payload cannot accidentally create
	arbitrary module globals. The lock protects the short assignment block when
	an SR830 worker, an OSTECH worker, or the emergency simulation updates the
	state while the GUI is reading it. Readers should treat values as a current
	snapshot rather than as a historical queue of measurements.
	"""
	global OUTP1, OUTP2, OUTP3, OUTP4, OUTR1, OUTR2
	global OAUX1, OAUX2, OAUX3, OAUX4
	global REFERENCE_FREQUENCY, CH1_DISPLAY, CH2_DISPLAY, PHAS, FREQ
	global LCT, XTA, LVA, XTCA, XTVA, LCA, XTT, LTM, GT, GS, GVN, LMDX, L
	global OSTECH_STATUS, AVAILABLE_COM_PORTS
	global SIGNAL_MAGNITUDE, SIGNAL_PHASE, CALCULATION_STATUS
	with _values_lock:
		for name, value in values.items():
			if name in globals():
				globals()[name] = value


def get_display_value_for_selection(channel: str, selection: str):
	"""Resolve the live value and unit for a selected lock-in display source.

	The phase display does not read the raw channel output. It must use the
	actual ``State.PHAS`` value instead of ``State.OUTP4`` so the GUI stays in
	sync with the instrument state.
	"""
	if channel == "CH1":
		cmd_map = {
			"X": ("OUTP1", "V"),
			"R": ("OUTP3", "V"),
			"X Noise": ("OUTR1", "V"),
			"Aux In 1": ("OAUX1", "V"),
			"Aux In 2": ("OAUX2", "V"),
		}
	else:
		cmd_map = {
			"Y": ("OUTP2", "V"),
			"Phase (θ)": ("PHAS", "°"),
			"Y Noise": ("OUTR2", "V"),
			"Aux In 3": ("OAUX3", "V"),
			"Aux In 4": ("OAUX4", "V"),
		}
	cmd, unit = cmd_map.get(selection, next(iter(cmd_map.values())))
	return globals().get(cmd, 0.0), unit


@dataclass(frozen=True)
class COMPort:
	"""Immutable description of one serial port visible to the OS.

	``device`` is the usable identifier, for example ``COM3``. The optional
	description and hardware ID are retained for port-selection UIs and
	diagnostics without coupling callers to pyserial's port-info object.
	"""

	device: str
	description: str = ""
	hwid: str = ""

	def __str__(self):
		return self.device


class COMScanner:
	"""Converts pyserial port discovery into application-owned data.

	Every scan creates fresh ``COMPort`` values, so callers do not retain a
	pyserial object whose state may change after the scan has completed.
	"""

	def scan(self) -> list[COMPort]:
		return [
			COMPort(port.device, port.description or "", port.hwid or "")
			for port in list_ports.comports()
		]

	def devices(self) -> list[str]:
		return [port.device for port in self.scan()]


def scan_com_ports() -> list[str]:
	"""Returns the device names of all available COM ports."""
	return COMScanner().devices()


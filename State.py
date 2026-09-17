"""Shared application state and serial-port discovery."""

from __future__ import annotations

from dataclasses import dataclass
import threading

from serial.tools import list_ports

from enum import Enum, global_enum


@global_enum
class Disp1val(Enum):
	OUTP1 = 0
	OUTP3 = 0
	OUTR1 = 0
	OAUX1 = 0
	OAUX2 = 0

@global_enum
class Disp2val(Enum):
	OUTP2 = 0
	OUTP4 = 0
	OUTR2 = 0
	OAUX3 = 0
	OAUX4 = 0

# Shared display values used by the GUI and other modules.
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
_values_lock = threading.Lock()

def update_values(values: dict[str, object]) -> None:
	"""Updates shared measurement values received from the devices."""
	global OUTP1, OUTP2, OUTP3, OUTP4, OUTR1, OUTR2
	global OAUX1, OAUX2, OAUX3, OAUX4
	global REFERENCE_FREQUENCY, CH1_DISPLAY, CH2_DISPLAY, PHAS, FREQ
	global LCT, XTA, LVA, XTCA, XTVA, LCA, XTT, LTM, GT, GS, GVN, LMDX, L
	global OSTECH_STATUS
	with _values_lock:
		for name, value in values.items():
			if name in globals():
				globals()[name] = value


# Compatibility aliases for older callers that imported these names.
disp1val = Disp1val
disp2val = Disp2val


@dataclass(frozen=True)
class COMPort:
	"""Describes one serial port visible to the operating system."""

	device: str
	description: str = ""
	hwid: str = ""

	def __str__(self):
		return self.device


class COMScanner:
	"""Scans and returns all currently available serial COM ports."""

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


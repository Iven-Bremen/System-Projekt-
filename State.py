"""Shared application state and serial-port discovery."""

from __future__ import annotations

from dataclasses import dataclass

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


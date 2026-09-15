"""Shared application state and serial-port discovery."""

from __future__ import annotations

from dataclasses import dataclass

from serial.tools import list_ports


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


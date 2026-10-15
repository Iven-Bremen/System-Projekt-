"""Python 3 wrapper for the Pyramid Technologies RS-232 bill acceptor example.

This module adapts the original Python 2 sample from the PyramidTechnologies
Python-RS-232 repository to Python 3 so it can be reused in the current project.
"""

from __future__ import annotations

import binascii
import time
from threading import Thread

try:
    import serial
except Exception:  # pragma: no cover - pyserial may be unavailable in tests
    serial = None


POLL_RATE = 0.1


class Host(object):
    """Minimal Python 3 port of the Pyramid Technologies RS-232 host example."""

    state_dict = {
        1: "Idling ",
        2: "Accepting ",
        4: "Escrowed ",
        8: "Stacking ",
        16: "Stacked ",
        32: "Returning",
        64: "Returned",
        17: "Stacked Idling ",
        65: "Returned Idling ",
    }
    event_dict = {0: "", 1: "Cheated ", 2: "Rejected ", 4: "Jammed ", 8: "Full "}

    def __init__(self):
        self.running = True
        self.bill_count = bytearray([0, 0, 0, 0, 0, 0, 0, 0])

        self.ack = 0
        self.credit = 0
        self.last_state = ""
        self.escrowed = False
        self.verbose = False
        self._serial_thread = None

    def start(self, portname):
        """Start the host in a non-daemon thread."""
        self._serial_thread = Thread(target=self._serial_runner, args=(portname,))
        self._serial_thread.daemon = False
        self._serial_thread.start()

    def stop(self):
        """Stop the host thread and wait for it to finish."""
        self.running = False
        if self._serial_thread is not None:
            self._serial_thread.join(timeout=2)

    def parse_cmd(self, cmd):
        """Apply simple commands like Q, ?, H or V."""
        if cmd == "Q":
            return 1
        if cmd in {"?", "H"}:
            return 2
        if cmd == "V":
            self.verbose = not self.verbose
        return 0

    def _serial_runner(self, portname):
        """Poll a bill acceptor over serial and decode the reply."""
        if serial is None:
            print("pyserial is not available")
            return

        try:
            ser = serial.Serial(
                port=portname,
                baudrate=9600,
                bytesize=serial.SEVENBITS,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.2,
            )
        except Exception as exc:
            print(f"Unable to open serial port {portname}: {exc}")
            return

        try:
            while ser.is_open and self.running:
                msg = bytearray([0x02, 0x08, 0x10, 0x7F, 0x00, 0x00, 0x03, 0x00])
                msg[2] = 0x10 | self.ack
                self.ack ^= 1

                if self.escrowed:
                    msg[4] |= 0x20

                for byte_idx in range(1, 6):
                    msg[7] ^= msg[byte_idx]

                ser.write(msg)
                time.sleep(0.1)

                out = b""
                while ser.in_waiting > 0:
                    out += ser.read(1)

                if not out:
                    continue

                try:
                    status = self.state_dict[ord(out[3:4])]
                except KeyError:
                    status = ""
                    print(f"unknown state dict key {ord(out[3:4])}")

                self.escrowed = bool(ord(out[3:4]) & 4)

                try:
                    status += self.event_dict[ord(out[4:5]) & 1]
                    status += self.event_dict[ord(out[4:5]) & 2]
                    status += self.event_dict[ord(out[4:5]) & 4]
                    status += self.event_dict[ord(out[4:5]) & 8]
                except KeyError:
                    print(f"unknown state dict key {ord(out[4:5])}")

                if (ord(out[4:5]) & 0x10) != 0x10:
                    status += " CASSETTE MISSING"

                if self.last_state != status:
                    print("Acceptor status:", status)
                    self.last_state = status

                if self.verbose:
                    print(", ".join(f"0x{c:02x}" for c in out))

                credit = (ord(out[5:6]) & 0x38) >> 3
                if credit != 0 and (ord(out[3:4]) & 0x10):
                    print("Bill credited: Bill#", credit)
                    self.bill_count[credit] += 1
                    print("Acceptor now holds:", binascii.hexlify(self.bill_count).decode("ascii"))

                time.sleep(POLL_RATE)
        finally:
            try:
                ser.close()
            except Exception:
                pass

            print("port closed")

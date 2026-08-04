import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from LaserDriver import LaserDriver


def test_laser_driver_supports_short_commands_and_validation():
    driver = LaserDriver(port="COM1", simulate=True)

    assert driver.GS() == "GS"
    assert driver.GT() == "GT"
    assert driver.GMS(True) == "GMS 0x4000"
    assert driver.GMS(False) == "GMS 0x0000"

    with pytest.raises(ValueError):
        driver.GMS(2)


def test_laser_driver_retries_after_transient_serial_error(monkeypatch):
    class FakeSerialPort:
        def __init__(self, fail_once=False):
            self.write_calls = 0
            self.closed = False
            self.fail_once = fail_once

        def write(self, data):
            self.write_calls += 1
            if self.fail_once and self.write_calls == 1:
                raise RuntimeError("temporary write failure")
            return len(data)

        def readline(self):
            return b"0x4405\n"

        def close(self):
            self.closed = True

    class FakeSerialModule:
        def __init__(self):
            self.created_ports = []
            self.fail_next_port = True

        def Serial(self, *args, **kwargs):
            port = FakeSerialPort(fail_once=self.fail_next_port)
            self.created_ports.append(port)
            self.fail_next_port = False
            return port

    fake_serial_module = FakeSerialModule()
    monkeypatch.setattr("LaserDriver.serial", fake_serial_module)

    driver = LaserDriver(port="COM1", simulate=False, timeout=0.1)
    assert driver.connect() is True

    response, latency = driver.query("GS")

    assert response == "0x4405"
    assert latency >= 0
    assert len(fake_serial_module.created_ports) >= 2

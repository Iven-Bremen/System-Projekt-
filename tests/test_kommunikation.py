import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lockin_amplifier
import Komunikation
from Komunikation import OsTechStatusDecoder, _looks_like_os_tech_response, _looks_like_sr830_response
from lockin_amplifier import LAM as LAMClass


def test_os_tech_status_decoder():
    decoded = OsTechStatusDecoder.decode("0x4405")
    assert decoded["laser_current_on"] is True
    assert "Interlock OK" in decoded["active_states"]
    assert "Laser Current ON" in decoded["active_states"]


def test_response_detection():
    assert _looks_like_os_tech_response("0x4405", "GS") is True
    assert _looks_like_os_tech_response("24.85", "GT") is True
    assert _looks_like_sr830_response("14.52", "PHAS?") is True
    assert _looks_like_sr830_response("0.00231, -0.00145", "SNAP? 1,2") is True


def test_driver_does_not_return_fake_data_when_not_connected(monkeypatch):
    monkeypatch.setattr(Komunikation, "SERIAL_AVAILABLE", False)
    driver = Komunikation.OsTechDriver(port="COM1", simulate=False)

    assert driver.connect() is False
    response, _ = driver.query("GS")
    assert response is None


def test_sr830_command_builder_formats_common_commands():
    lam = LAMClass(port="COM1", simulate=True)

    assert lam.build_command("PHAS", 12.34) == "PHAS 12.34"
    assert lam.build_command("PHAS", query=True) == "PHAS?"
    assert lam.build_command("SNAP", 1, 2, query=True) == "SNAP? 1,2"


def test_generic_command_wrapper_supports_short_call_style():
    lam = LAMClass(port="COM1", simulate=True)

    assert lam.PHAS(45) == "PHAS 45"
    assert lam.PHAS() == "14.52"
    assert lam.FREQ(589) == "FREQ 589"


def test_lam_composite_methods_run_multiple_commands():
    lam = LAMClass(port="COM1", simulate=True)

    result = lam.init(phase=45.0, frequency=589.0)

    assert result["phase"] == "PHAS 45.0"
    assert result["frequency"] == "FREQ 589.0"
    assert lam.configure_reference(1, 1000.0)["reference_source"] == "FMOD 1"


def test_lam_rejects_invalid_values_and_baudrates():
    lam = LAMClass(port="COM1", simulate=True)

    with pytest.raises(ValueError):
        lam.PHAS(1000)

    with pytest.raises(ValueError):
        lam.FREQ(0)

    with pytest.raises(ValueError):
        lam.SENS(99)

    with pytest.raises(ValueError):
        lam.OFLT(20)

    with pytest.raises(ValueError):
        lam.FMOD(2)

    with pytest.raises(ValueError):
        LAMClass(port="COM1", simulate=True, baudrate=1234)


def test_lam_logs_sent_and_received_commands(tmp_path):
    log_path = tmp_path / "sr830_log.csv"
    lam = LAMClass(port="COM1", simulate=True, log_path=str(log_path))

    lam.PHAS(45)
    lam.PHAS()

    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "TX" in content
    assert "RX" in content
    assert "PHAS" in content


def test_lam_retries_after_transient_serial_error(monkeypatch):
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
            return b"14.52\n"

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
    monkeypatch.setattr(lockin_amplifier, "serial", fake_serial_module)

    lam = LAMClass(port="COM1", simulate=False, timeout=0.1)
    assert lam.connect() is True

    response, latency = lam.query("PHAS?")

    assert response == "14.52"
    assert latency >= 0
    assert len(fake_serial_module.created_ports) >= 2
    assert fake_serial_module.created_ports[-1].closed is False

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

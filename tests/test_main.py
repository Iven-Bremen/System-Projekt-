import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import parse_args


def test_parse_args_supports_hardware_and_simulation_modes():
    assert parse_args(["--laser-port", "COM3", "--lockin-port", "COM4", "--hardware"]) == (
        "COM3",
        "COM4",
        False,
        True,
        False,
        True,
    )

    assert parse_args(["--simulate", "--no-interactive"]) == (
        None,
        None,
        False,
        False,
        True,
        False,
    )

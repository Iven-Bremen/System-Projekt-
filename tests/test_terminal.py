import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Terminal import parse_interactive_command


def test_parse_interactive_command_supports_help_and_shortcuts():
    assert parse_interactive_command("/help") == ("help", None)
    assert parse_interactive_command("HELP") == ("help", None)
    assert parse_interactive_command("s") == ("scan", None)
    assert parse_interactive_command("t") == ("test", None)
    assert parse_interactive_command("q") == ("quit", None)
    assert parse_interactive_command("unknown") == ("unknown", "unknown")


def test_parse_interactive_command_supports_device_commands():
    assert parse_interactive_command("laser gs") == ("device", {"device": "laser", "action": "gs"})
    assert parse_interactive_command("laser on") == ("device", {"device": "laser", "action": "on"})
    assert parse_interactive_command("lockin snap") == ("device", {"device": "lockin", "action": "snap"})
    assert parse_interactive_command("connect") == ("connect", None)
    assert parse_interactive_command("disconnect") == ("disconnect", None)

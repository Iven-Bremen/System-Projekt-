import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pti_bill_acceptor import Host


def test_host_parse_cmd_supports_basic_controls():
    host = Host()

    assert host.parse_cmd("Q") == 1
    assert host.parse_cmd("?") == 2
    assert host.parse_cmd("H") == 2

    assert host.parse_cmd("V") == 0
    assert host.verbose is True
    assert host.parse_cmd("V") == 0
    assert host.verbose is False

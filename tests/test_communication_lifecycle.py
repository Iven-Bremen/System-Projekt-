import Komunikation
from Threads import CommunicationThreads


def test_close_selected_device_only_closes_requested_port():
    Komunikation.SR830 = object()
    Komunikation.OSTECH = object()
    Komunikation.SR830_PORT = "COM3"
    Komunikation.OSTECH_PORT = "COM4"

    result = Komunikation.close_device("SR830")

    assert result is True
    assert Komunikation.SR830 is None
    assert Komunikation.OSTECH is not None

    Komunikation.OSTECH = None


def test_communication_starts_only_for_connected_devices():
    def runner(stop, publish):
        stop.wait(0.5)

    threads = CommunicationThreads(
        runner,
        runner,
        lambda message: None,
        lambda message: None,
        sr830_enabled=False,
        ostech_enabled=True,
    )

    assert threads.sr830 is None
    assert threads.ostech is not None

    threads.start()
    try:
        assert threads.ostech.thread.is_alive() is True
    finally:
        threads.stop()
        assert threads.ostech.thread.is_alive() is False

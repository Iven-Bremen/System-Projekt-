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
        assert threads.logging.thread.is_alive() is False
        assert threads.gui.thread.is_alive() is False


def test_communication_loop_restarts_when_second_device_connects(monkeypatch):
    class Worker:
        def is_alive(self):
            return True

    class Pipeline:
        def __init__(self, sr830_enabled, ostech_enabled):
            self.sr830 = type("Device", (), {"thread": Worker()})() if sr830_enabled else None
            self.ostech = type("Device", (), {"thread": Worker()})() if ostech_enabled else None
            self.stopped = False

        def stop(self):
            self.stopped = True

    started = []

    def fake_start(**options):
        pipeline = Pipeline(options["sr830_enabled"], options["ostech_enabled"])
        started.append(pipeline)
        return pipeline

    monkeypatch.setattr(Komunikation, "SR830", object())
    monkeypatch.setattr(Komunikation, "OSTECH", None)
    monkeypatch.setattr(Komunikation, "_ACTIVE_COMMUNICATION_THREADS", None)
    monkeypatch.setattr(Komunikation, "start_threaded_measurement", fake_start)

    first = Komunikation.start_communication_loop()
    monkeypatch.setattr(Komunikation, "OSTECH", object())
    second = Komunikation.start_communication_loop()

    assert first.stopped is True
    assert second is started[1]
    assert second.sr830 is not None
    assert second.ostech is not None

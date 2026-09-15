import queue
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class ThreadMessage:
    source: str
    kind: str
    value: object


class DeviceThread:
    def __init__(self, name, runner, publish):
        self.stop_requested = threading.Event()
        self._runner = runner
        self._publish = publish
        self.thread = threading.Thread(target=self._run, name=name)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_requested.set()
        if self.thread.is_alive():
            self.thread.join()

    def _run(self):
        try:
            self._runner(self.stop_requested, self.publish)
        except Exception as error:
            self.publish({"step": "error", "value": f"{type(error).__name__}: {error}"})

    def publish(self, value):
        self._publish(self.thread.name.removesuffix("Thread"), value)


class MessageThread:
    def __init__(self, name, handler, interval_ms=0):
        self._messages = queue.Queue()
        self._handler = handler
        self._interval_ms = interval_ms
        self._stop_requested = threading.Event()
        self.thread = threading.Thread(target=self._run, name=name)

    def publish(self, message):
        self._messages.put(message)

    def start(self):
        self.thread.start()

    def stop(self):
        self._stop_requested.set()
        self._messages.put(None)
        if self.thread.is_alive():
            self.thread.join()

    def _run(self):
        while True:
            message = self._messages.get()
            if message is None:
                return
            self._handler(message)
            if self._interval_ms > 0:
                self._stop_requested.wait(self._interval_ms / 1000)


class CommandThread:
    def __init__(self, runner, publish):
        self.stop_requested = threading.Event()
        self._runner = runner
        self._publish = publish
        self.thread = threading.Thread(target=self._run, name="CommandThread")

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_requested.set()
        if self.thread.is_alive():
            self.thread.join()

    def _run(self):
        try:
            self._runner(self.stop_requested, self.publish)
        except Exception as error:
            self.publish({"step": "error", "value": f"{type(error).__name__}: {error}"})

    def publish(self, value):
        self._publish("COMMAND", value)


class CommunicationThreads:
    def __init__(
        self,
        sr830_runner,
        ostech_runner,
        log_handler,
        gui_handler,
        gui_interval_ms=0,
        command_runner=None,
    ):
        self.logging = MessageThread("LoggingThread", log_handler)
        self.gui = MessageThread("GuiThread", gui_handler, gui_interval_ms)
        self.sr830 = DeviceThread("SR830Thread", sr830_runner, self._publish)
        self.ostech = DeviceThread("OSTECHThread", ostech_runner, self._publish)
        self.commands = CommandThread(command_runner, self._publish) if command_runner else None

    def _publish(self, source, value):
        kind = "result"
        if isinstance(value, dict):
            step = value.get("step")
            if step == "startup":
                kind = "error" if "nicht bereit" in str(value.get("value", "")) else "status"
            elif step == "error":
                kind = "error"
        message = ThreadMessage(source, kind, value)
        self.logging.publish(message)
        self.gui.publish(message)

    def publish(self, source, kind, value):
        message = ThreadMessage(source, kind, value)
        self.logging.publish(message)
        self.gui.publish(message)

    def start(self):
        self.logging.start()
        self.gui.start()
        if self.commands:
            self.commands.start()
        self.sr830.start()
        self.ostech.start()

    def stop(self):
        self.sr830.stop()
        self.ostech.stop()
        if self.commands:
            self.commands.stop()
        self.logging.stop()
        self.gui.stop()
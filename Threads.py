"""Threading infrastructure for device communication, logging, and GUI data.

The module deliberately separates work from presentation. Device threads do
blocking serial I/O and publish plain Python messages. Message threads consume
those messages and call their handlers in order. This keeps CSV logging and
GUI message handling independent from the timing of either hardware device.

Tkinter widgets must still be changed only by the Tkinter main thread. The
``gui`` message queue is therefore a transport boundary for application data;
it must not be used to call widget methods directly from a worker thread.
"""

import queue
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class ThreadMessage:
    """Immutable message passed from a worker to logging or GUI consumers.

    ``source`` identifies the producer, for example ``SR830`` or ``OSTECH``.
    ``kind`` is the normalized severity/category used by the consumers.
    ``value`` contains the original result or an error/status dictionary.
    Keeping this object immutable prevents one consumer from changing what a
    different consumer receives.
    """

    source: str
    kind: str
    value: object


class DeviceThread:
    """Runs one blocking device loop in a dedicated daemon-independent thread.

    The runner receives a stop event and a publish callback. It should check
    the event between hardware operations and publish values instead of
    touching logging or GUI objects directly. Exceptions are converted into a
    final error message so a device failure cannot silently kill the process.
    """

    def __init__(self, name, runner, publish):
        self.stop_requested = threading.Event()
        self._runner = runner
        self._publish = publish
        self.thread = threading.Thread(target=self._run, name=name)

    def start(self):
        """Start the worker exactly once.

        The thread object cannot be started a second time. The coordinator
        therefore owns the lifecycle and calls this method only during startup.
        """
        self.thread.start()

    def stop(self):
        """Request cancellation and wait until the device loop has returned."""
        self.stop_requested.set()
        if self.thread.is_alive():
            self.thread.join()

    def _run(self):
        try:
            self._runner(self.stop_requested, self.publish)
        except Exception as error:
            self.publish({"step": "error", "value": f"{type(error).__name__}: {error}"})

    def publish(self, value):
        """Attach this worker's name and forward a result to the coordinator."""
        self._publish(self.thread.name.removesuffix("Thread"), value)


class MessageThread:
    """Serializes queued messages for one handler.

    A queue is used instead of shared mutable state. ``stop()`` inserts a
    sentinel after setting the stop event, allowing the consumer to leave its
    blocking ``Queue.get`` call deterministically.
    """

    def __init__(self, name, handler, interval_ms=0):
        self._messages = queue.Queue()
        self._handler = handler
        self._interval_ms = interval_ms
        self._stop_requested = threading.Event()
        self.thread = threading.Thread(target=self._run, name=name)

    def publish(self, message):
        """Queue one message without blocking the producer on the handler."""
        self._messages.put(message)

    def start(self):
        """Start the queue consumer exactly once."""
        self.thread.start()

    def stop(self):
        """Wake the consumer with a sentinel and wait for clean termination."""
        self._stop_requested.set()
        self._messages.put(None)
        if self.thread.is_alive():
            self.thread.join()

    def _run(self):
        """Consume messages in FIFO order until the sentinel is received."""
        while True:
            message = self._messages.get()
            if message is None:
                return
            self._handler(message)
            if self._interval_ms > 0:
                self._stop_requested.wait(self._interval_ms / 1000)


class CommandThread:
    """Runs command/status workflows independently from periodic polling.

    Commands may wait for a device to become ready or block until shutdown.
    This class keeps those workflows from delaying the regular SR830 and
    OSTECH polling loops.
    """

    def __init__(self, runner, publish):
        self.stop_requested = threading.Event()
        self._runner = runner
        self._publish = publish
        self.thread = threading.Thread(target=self._run, name="CommandThread")

    def start(self):
        """Start the command workflow exactly once."""
        self.thread.start()

    def stop(self):
        """Request command cancellation and wait for its runner to finish."""
        self.stop_requested.set()
        if self.thread.is_alive():
            self.thread.join()

    def _run(self):
        """Run the command callback and convert failures into messages."""
        try:
            self._runner(self.stop_requested, self.publish)
        except Exception as error:
            self.publish({"step": "error", "value": f"{type(error).__name__}: {error}"})

    def publish(self, value):
        """Publish a command result under the stable ``COMMAND`` source tag."""
        self._publish("COMMAND", value)


class CalculationThread:
    """Run application calculations independently from device polling.

    The calculation runner receives the same stop event and publish callback
    as a device runner. It may read values from ``State`` and publish derived
    results, but it must not update Tkinter widgets directly. Keeping this
    work in its own thread prevents longer calculations, fits, or conversions
    from delaying serial communication.
    """

    def __init__(self, runner, publish):
        self.stop_requested = threading.Event()
        self._runner = runner
        self._publish = publish
        self.thread = threading.Thread(target=self._run, name="CalculationThread")

    def start(self):
        """Start the calculation runner exactly once."""
        self.thread.start()

    def stop(self):
        """Request calculation cancellation and wait for completion."""
        self.stop_requested.set()
        if self.thread.is_alive():
            self.thread.join()

    def _run(self):
        """Run calculations and convert failures into error messages."""
        try:
            self._runner(self.stop_requested, self.publish)
        except Exception as error:
            self.publish({"step": "error", "value": f"{type(error).__name__}: {error}"})

    def publish(self, value):
        """Publish a calculation result under the ``CALCULATION`` source."""
        self._publish("CALCULATION", value)


class CommunicationThreads:
    """Owns and coordinates every background communication worker.

    The coordinator starts logging and GUI message consumers before producers,
    then starts optional command processing and only the device loops that are
    actually enabled. A device that is not connected must not leak a worker
    thread or a stale status update into the communication pipeline.
    """

    def __init__(
        self,
        sr830_runner,
        ostech_runner,
        log_handler,
        gui_handler,
        gui_interval_ms=0,
        command_runner=None,
        calculation_runner=None,
        sr830_enabled=True,
        ostech_enabled=True,
    ):
        self.logging = MessageThread("LoggingThread", log_handler)
        self.gui = MessageThread("GuiThread", gui_handler, gui_interval_ms)
        self.sr830 = DeviceThread("SR830Thread", sr830_runner, self._publish) if sr830_enabled else None
        self.ostech = DeviceThread("OSTECHThread", ostech_runner, self._publish) if ostech_enabled else None
        self.commands = CommandThread(command_runner, self._publish) if command_runner else None
        self.calculations = (
            CalculationThread(calculation_runner, self._publish)
            if calculation_runner else None
        )

    def _publish(self, source, value):
        """Normalize a raw worker payload and fan it out to both consumers."""
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
        """Publish an already classified message to both consumer queues."""
        message = ThreadMessage(source, kind, value)
        self.logging.publish(message)
        self.gui.publish(message)

    def start(self):
        """Start consumers first, then commands, calculations, and enabled devices."""
        self.logging.start()
        self.gui.start()
        if self.commands:
            self.commands.start()
        if self.calculations:
            self.calculations.start()
        if self.sr830 is not None:
            self.sr830.start()
        if self.ostech is not None:
            self.ostech.start()

    def stop(self):
        """Stop producers before consumers and join every owned thread."""
        if self.sr830 is not None:
            self.sr830.stop()
        if self.ostech is not None:
            self.ostech.stop()
        if self.commands:
            self.commands.stop()
        if self.calculations:
            self.calculations.stop()
        self.logging.stop()
        self.gui.stop()
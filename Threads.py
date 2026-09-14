import queue
import threading
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ThreadMessage:
	source: str
	kind: str
	value: object


class LoggingThread:
	def __init__(self, log_handler: Callable[[ThreadMessage], None]):
		self.messages = queue.Queue()
		self._stop_requested = threading.Event()
		self._thread = threading.Thread(target=self._run, name="LoggingThread")
		self._log_handler = log_handler

	def publish(self, message: ThreadMessage):
		self.messages.put(message)

	def start(self):
		self._thread.start()

	def stop(self):
		self._stop_requested.set()
		self.messages.put(None)
		self._thread.join()

	def _run(self):
		while True:
			message = self.messages.get()
			if message is None:
				break
			self._log_handler(message)


class GuiThread:
	def __init__(self, update_handler: Callable[[ThreadMessage], None], interval_ms: int = 0):
		self.messages = queue.Queue()
		self._stop_requested = threading.Event()
		self._thread = threading.Thread(target=self._run, name="GuiThread")
		self._update_handler = update_handler
		self._interval_ms = interval_ms

	def publish(self, message: ThreadMessage):
		self.messages.put(message)

	def start(self):
		self._thread.start()

	def stop(self):
		self._stop_requested.set()
		self.messages.put(None)
		self._thread.join()

	def _run(self):
		while True:
			message = self.messages.get()
			if message is None:
				break
			self._update_handler(message)
			if self._interval_ms > 0:
				self._stop_requested.wait(self._interval_ms / 1000)


class DeviceThread:
	def __init__(self, name: str, runner: Callable[[threading.Event, Callable[[object], None]], None]):
		self.name = name
		self._runner = runner
		self.stop_requested = threading.Event()
		self.thread = threading.Thread(target=self._run, name=name)

	def start(self):
		self.thread.start()

	def stop(self):
		self.stop_requested.set()
		self.thread.join()

	def _run(self):
		self._runner(self.stop_requested, self.publish)

	def publish(self, value: object):
		raise NotImplementedError


class CommunicationThreads:
	def __init__(
		self,
		sr830_runner: Callable[[threading.Event, Callable[[object], None]], None],
		ostech_runner: Callable[[threading.Event, Callable[[object], None]], None],
		log_handler: Callable[[ThreadMessage], None],
		gui_handler: Callable[[ThreadMessage], None],
		gui_interval_ms: int = 0,
	):
		self.logging = LoggingThread(log_handler)
		self.gui = GuiThread(gui_handler, gui_interval_ms)
		self.sr830 = DeviceThread("SR830Thread", sr830_runner)
		self.ostech = DeviceThread("OSTECHThread", ostech_runner)
		self.sr830.publish = lambda value: self._publish("SR830", value)
		self.ostech.publish = lambda value: self._publish("OSTECH", value)

	def _publish(self, source: str, value: object):
		kind = "result"
		if isinstance(value, dict):
			if value.get("step") == "startup":
				kind = "error" if "nicht bereit" in str(value.get("value", "")) else "status"
			elif value.get("step") == "error":
				kind = "error"
		message = ThreadMessage(source, kind, value)
		self.logging.publish(message)
		self.gui.publish(message)

	def publish(self, source: str, kind: str, value: object):
		message = ThreadMessage(source, kind, value)
		self.logging.publish(message)
		self.gui.publish(message)

	def start(self):
		self.logging.start()
		self.gui.start()
		self.sr830.start()
		self.ostech.start()

	def stop(self):
		self.sr830.stop()
		self.ostech.stop()
		self.logging.stop()
		self.gui.stop()

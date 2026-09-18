"""Deterministic, time-varying values for the GUI emergency simulation.

The emergency bypass must make the interface usable without connected
hardware, but it must not pretend that simulated values came from a device.
This module therefore writes only clearly synthetic values into ``State`` and
does so through Tkinter's ``after`` scheduler. The scheduler runs in the GUI
thread, which is safe for Tkinter and keeps the update frequency below 60 Hz.

``start(root)`` and ``stop(root)`` own the callback lifecycle. In particular,
``stop`` cancels the pending callback before the root window is destroyed.
"""

import math
import time

import State


UPDATE_INTERVAL_MS = 17
_simulation_active = False
_simulation_job = None


def _update(root):
	"""Write one simulation snapshot and schedule the next one.

	The function intentionally updates SR830-like and OSTECH-like values in one
	state transaction. Consumers never need to know whether a value originated
	from serial hardware or emergency simulation; both paths use ``State``.
	"""
	global _simulation_job
	if not _simulation_active:
		# The callback may still be invoked once after stop() has changed the flag.
		# Returning without scheduling another callback makes shutdown idempotent.
		_simulation_job = None
		return

	phase = time.monotonic()
	ostech_status = {
		# This dictionary mirrors the result of decode_ostech_status(). Keeping
		# the same keys lets safety indicators use real and simulated data alike.
		"status_word": 0x4C0D,
		"interlock_ok": True,
		"driver_supply_ok": True,
		"driver_temperature_ok": True,
		"lt_sensor_ok": True,
		"ct_sensor_ok": True,
		"lc_on": True,
		"lc_error": False,
	}
	State.update_values({
		# SR830 SNAP channels and auxiliary inputs.
		"OUTP1": 0.5 + 0.2 * math.sin(phase),
		"OUTP2": 0.4 + 0.15 * math.cos(phase * 0.8),
		"OUTP3": 0.7 + 0.1 * math.sin(phase * 1.2),
		"OUTP4": 45.0 + 10.0 * math.sin(phase * 0.5),
		"OUTR1": 0.01 + 0.005 * abs(math.sin(phase * 1.5)),
		"OUTR2": 0.02 + 0.005 * abs(math.cos(phase * 1.3)),
		"OAUX1": 20.0 + 2.0 * math.sin(phase * 0.4),
		"OAUX2": 21.0 + 2.0 * math.cos(phase * 0.4),
		"OAUX3": 22.0 + 2.0 * math.sin(phase * 0.3),
		"OAUX4": 23.0 + 2.0 * math.cos(phase * 0.3),
		"REFERENCE_FREQUENCY": 1000.0,
		"CH1_DISPLAY": 0.5,
		"CH2_DISPLAY": 0.4,
		"PHAS": 45.0,
		"FREQ": 1000.0,
		# OSTECH periodic and startup values.
		"LCT": 0.0 + 0.05 * math.sin(phase * 0.7),
		"XTA": 25.0 + 0.3 * math.sin(phase * 0.2),
		"LVA": 0.0,
		"XTCA": 0.0 + 0.02 * math.cos(phase * 0.6),
		"XTVA": 0.0,
		"LCA": 0.0 + 0.01 * math.sin(phase * 0.9),
		"XTT": 25.0 + 0.2 * math.sin(phase * 0.2),
		"LTM": 25.0 + 0.2 * math.cos(phase * 0.2),
		"GT": 25.0,
		"GS": ostech_status,
		"GVN": 264981,
		"LMDX": True,
		"L": True,
		"OSTECH_STATUS": ostech_status,
	})
	_simulation_job = root.after(UPDATE_INTERVAL_MS, _update, root)


def start(root):
	"""Start the simulation once at a maximum rate of 60 Hz.

	Calling this function repeatedly is safe: an active simulation is not
	duplicated and therefore cannot create multiple competing callbacks.
	"""
	global _simulation_active, _simulation_job
	if _simulation_active:
		return
	_simulation_active = True
	_simulation_job = root.after(0, _update, root)


def stop(root):
	"""Stop the simulation and cancel its pending Tkinter callback.

	Cancellation is best effort because shutdown may already have destroyed the
	Tk interpreter. Such a late cancellation is harmless and is intentionally
	suppressed here during application shutdown.
	"""
	global _simulation_active, _simulation_job
	_simulation_active = False
	if _simulation_job is not None:
		try:
			root.after_cancel(_simulation_job)
		except Exception:
			pass
		_simulation_job = None

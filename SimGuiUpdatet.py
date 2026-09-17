"""Simulation values for the GUI emergency mode."""

import math
import time

import State


UPDATE_INTERVAL_MS = 17
_simulation_active = False
_simulation_job = None


def _update(root):
	global _simulation_job
	if not _simulation_active:
		_simulation_job = None
		return

	phase = time.monotonic()
	State.update_values({
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
	})
	_simulation_job = root.after(UPDATE_INTERVAL_MS, _update, root)


def start(root):
	"""Starts the GUI simulation once at a maximum rate of 60 Hz."""
	global _simulation_active, _simulation_job
	if _simulation_active:
		return
	_simulation_active = True
	_simulation_job = root.after(0, _update, root)


def stop(root):
	"""Stops the GUI simulation if it is active."""
	global _simulation_active, _simulation_job
	_simulation_active = False
	if _simulation_job is not None:
		root.after_cancel(_simulation_job)
		_simulation_job = None

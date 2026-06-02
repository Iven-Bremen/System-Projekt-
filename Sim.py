"""
Sim.py

Datei-Simulator: Liest das bereitgestellte Messprotokoll und liefert
plausible Antworten für GT, GS, PHAS und SNAP-Befehle.
"""
import re


class FileSimulator:
    """Simple simulator that reads a measurement log TXT and produces
    plausible responses for GT (temperature), GS (status flags), and
    SR830 SNAP/PHAS responses.

    It cycles through values parsed from the file so tests are deterministic.
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.amp_values = []
        self.phase_values = []
        self._index = 0
        self._load_file()
        # A simple set of status codes to cycle through
        self.status_codes = ["0x4405", "0x4005", "0x0000", "0x4000"]

    def _load_file(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                data = f.read()
        except Exception:
            # Fallback to a few hardcoded values
            self.amp_values = [1.0071, 0.9766, 0.9460, 0.9155]
            self.phase_values = [234.246, 232.374, 237.678, 241.146]
            return

        # Try to find the "Amplitude in mV" table and extract the first column floats
        match = re.search(r"Amplitude in mV\s*Phase in Grad(.*?)\n\s*2", data, re.S)
        section = match.group(1) if match else data

        nums = re.findall(r"([0-9]*\.?[0-9]+)", section)
        floats = [float(x) for x in nums]

        # Heuristic: alternate amplitude and phase: amplitude, phase, amplitude, phase...
        amps = floats[0::2]
        phases = floats[1::2]

        if amps:
            self.amp_values = amps
        else:
            self.amp_values = [1.0, 0.9, 1.1]

        if phases:
            self.phase_values = phases
        else:
            self.phase_values = [180.0, 200.0, 220.0]

    def _next(self):
        i = self._index
        self._index = (self._index + 1) % max(1, len(self.amp_values))
        return i

    def get_GT(self):
        # Return a temperature-like value derived from amplitude (scaled)
        i = self._next()
        amp = self.amp_values[i % len(self.amp_values)]
        temp = 20.0 + (amp - 0.9) * 10.0
        return f"{temp:.2f}"

    def get_GS(self):
        i = self._next()
        return self.status_codes[i % len(self.status_codes)]

    def get_SR830_PHAS(self):
        i = self._next()
        return f"{self.phase_values[i % len(self.phase_values)]:.2f}"

    def get_SR830_SNAP(self):
        i = self._next()
        # produce small X,Y values derived from amplitude
        amp = self.amp_values[i % len(self.amp_values)]
        x = amp * 0.001 + 0.0005
        y = -amp * 0.0009 - 0.0003
        return f"{x:.5f}, {y:.5f}"

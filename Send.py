"""Public SR830 and OSTech command catalog and high-level command API.

This module owns the user-facing command metadata and the application-side API:
- command definitions (what can be sent)
- convenience helpers (send/read helpers)
- structured logging through ``Log.Log``

The actual serial-port traffic and the binary/text encoding decisions stay in
``Komunikation.py``. This keeps the hardware protocol isolated from user-level
command usage.
"""

from collections import namedtuple

# =============================================================================
# ARCHITEKTURERKLÄRUNG
# =============================================================================
# Diese Datei ist die öffentliche Befehls-Schnittstelle für die Geräte.
# Sie enthält keine reale seriellen IO-Operationen.
# Die eigentliche Kommunikation mit dem Hardware-Gerät passiert in Komunikation.py.
#
# Aufbau:
# - SR830G: nur Lesebefehle
# - SR830S: nur Schreibbefehle
# - OSTechG: nur Lesebefehle für das OSTech-Gerät
# - OSTechS: nur Schreibbefehle für das OSTech-Gerät
# - send(), read(), set(), run(): allgemeine API für GUI, Threads und andere Module
# - resolve_sr830_setting(): wandelt verständliche Werte wie "Normal" oder "1 s" in
#   die Zahlenwerte um, die das SR830-Gerät erwartet.
#
# Warum diese Trennung wichtig ist:
# - Das GUI oder die Threads sollen keine Kommandostring-Logik selbst bauen.
# - Die Logik der Befehlsdefinition gehört in diese Datei.
# - Die Logik des tatsächlichen Sendens an das Gerät gehört in Komunikation.py.
# - Dadurch bleibt der Code klarer, testbarer und sauberer von der Hardware getrennt.

# --- Data Structures ---
# Jede Befehlsdefinition besteht aus vier Informationen:
# 1. command: der genaue Befehlscode, z.B. "SENS" oder "OUTP? 1"
# 2. type: Datentyp des Rückgabewerts oder erwarteten Werts
# 3. unit: Einheit, z.B. "V", "Hz", "deg"
# 4. description: verständliche Beschreibung für Menschen
SR830CommandInfo = namedtuple("SR830CommandInfo", ["command", "type", "unit", "description"])
OSTechCommandInfo = namedtuple("OSTechCommandInfo", ["command", "type", "unit", "description"])

# =============================================================================
# SR830 COMMANDS
# =============================================================================

# SR830G = Lesebefehle.
# Diese Befehle fragen das Gerät nach Messwerten oder Statusinformationen.
# Beispiele: X, Y, R, Theta, Statusbytes, Geräte-ID und Snapshot-Werte.
# Mit diesen Befehlen liest man Informationen aus dem SR830 aus, aber man setzt nichts.
# SR830G enthält alle Lesebefehle des SR830.
# Man nutzt diese Befehle, wenn man Werte oder Zustände vom Lock-In Verstärker lesen will.
# Beispiele: X-Wert, Y-Wert, R-Wert, Theta, Statusbytes, Geräte-ID und Snapshot-Messungen.
# Diese Befehle ändern nichts am Gerät, sondern fragen nur Informationen ab.
class SR830G:
    """Query-only SR830 commands: read-only / monitoring commands."""

    OUTP_X = SR830CommandInfo("OUTP? 1", float, "V", "Reads X-value")
    OUTP_Y = SR830CommandInfo("OUTP? 2", float, "V", "Reads Y-value")
    OUTP_R = SR830CommandInfo("OUTP? 3", float, "V", "Reads R-value (Magnitude)")
    OUTP_THETA = SR830CommandInfo("OUTP? 4", float, "deg", "Reads Theta (Phase)")

    OUTR_CH1 = SR830CommandInfo("OUTR? 1", float, "", "Reads CH1 Display")
    OUTR_CH2 = SR830CommandInfo("OUTR? 2", float, "", "Reads CH2 Display")

    OAUX_IN1 = SR830CommandInfo("OAUX? 1", float, "V", "Reads Aux Input 1")
    OAUX_IN2 = SR830CommandInfo("OAUX? 2", float, "V", "Reads Aux Input 2")
    OAUX_IN3 = SR830CommandInfo("OAUX? 3", float, "V", "Reads Aux Input 3")
    OAUX_IN4 = SR830CommandInfo("OAUX? 4", float, "V", "Reads Aux Input 4")

    SNAP_XY = SR830CommandInfo("SNAP? 1,2", str, "V, V", "Reads X-value and Y-value")
    SNAP_R_THETA = SR830CommandInfo("SNAP? 3,4", str, "V, deg", "Reads R-value and Theta")
    SNAP_XY_R_TH = SR830CommandInfo("SNAP? 1,2,3,4", str, "V, V, V, deg", "Reads X, Y, R and Theta")
    SNAP_ALL_MAIN = SR830CommandInfo("SNAP? 1,2,3,4,10,11", str, "V, V, V, deg, V, V", "Reads X, Y, R, Theta, CH1 and CH2")
    SNAP_AUX_FREQ = SR830CommandInfo("SNAP? 5,6,7,8,9", str, "V, V, V, V, Hz", "Reads Aux1, Aux2, Aux3, Aux4 and RefFreq")

    SPTS = SR830CommandInfo("SPTS?", int, "points", "Reads number of stored data points")
    IDN = SR830CommandInfo("*IDN?", str, "", "Reads device identification")

    # ERRS? und LIAS? sind keine Konfigurationsbefehle, sondern reine Statusabfragen.
    # Sie liefern interne Zustandsbytes des SR830 und werden daher in der API als
    # Lesebefehle modelliert. Das ist wichtig, weil der Code den Unterschied sauber
    # zwischen „Messwert lesen“ und „Gerätestatus lesen“ aufrechterhalten will.
    #
    # Der eigentliche serielle Austausch passiert in Komunikation.ask_SR830().
    # Diese Klasse hier beschreibt nur die Bedeutung des Befehls und dessen Typ.
    ERRS = SR830CommandInfo("ERRS?", int, "", "Reads das Error Status Byte")
    LIAS = SR830CommandInfo("LIAS?", int, "", "Reads das LIA Status Byte")

    @staticmethod
    def read(command_info, return_type=None):
        """Read from the SR830 using command metadata from this class."""
        return read(command_info, return_type)

    @classmethod
    def all(cls):
        """Return all query commands as a list of (name, command_info)."""
        return [
            (name, value)
            for name, value in cls.__dict__.items()
            if not name.startswith("__") and isinstance(value, SR830CommandInfo)
        ]


# SR830S = Schreibbefehle.
# Diese Befehle verändern das Verhalten des SR830.
# Beispiele: Sensitivität, Reserve, Zeitkonstante, Filter, Eingang, Phase, Frequenz und Auto-Commands.
# Wenn im GUI ein Wert gesetzt wird, ist das meist ein Befehl aus dieser Klasse.
# SR830S enthält alle Schreibbefehle des SR830.
# Das sind die Befehle, mit denen der Nutzer Einstellungen am Gerät verändert.
# Beispiele: Sensitivität, Reserve, Zeitkonstante, Filter, Eingangskonfiguration, Phase,
# Frequenz, interne Referenz und automatische Anpassungsfunktionen.
# Die GUI und andere Module sollten in der Regel genau diese Befehle verwenden, wenn sie
# Einstellungen an das SR830 senden wollen.
class SR830S:
    """Set-only SR830 commands: configuration and action commands."""

    PHAS = SR830CommandInfo("PHAS", float, "deg", "Setzt Phasenverschiebung (-360.00 bis 729.99)")
    FMOD = SR830CommandInfo("FMOD", int, "", "Referenzquelle: 0=External, 1=Internal")
    FREQ = SR830CommandInfo("FREQ", float, "Hz", "Interne Oszillatorfrequenz (0.001 bis 102000)")
    RSLP = SR830CommandInfo("RSLP", int, "", "Ext. Trigger Flanke: 0=Sine, 1=TTL Rising, 2=TTL Falling")
    HARM = SR830CommandInfo("HARM", int, "", "Detektions-Harmonische (1 bis 19999)")
    SLVL = SR830CommandInfo("SLVL", float, "V", "Sinus-Ausgangsamplitude (0.004 bis 5.000 Vrms)")

    ISRC = SR830CommandInfo("ISRC", int, "", "Eingang: 0=A, 1=A-B, 2=I(1MOhm), 3=I(100MOhm)")
    IGND = SR830CommandInfo("IGND", int, "", "Shield Erdung: 0=Float, 1=Ground")
    ICPL = SR830CommandInfo("ICPL", int, "", "Kopplung: 0=AC, 1=DC")
    ILIN = SR830CommandInfo("ILIN", int, "", "Netzfilter: 0=Out, 1=Line, 2=2xLine, 3=Both")

    SENS = SR830CommandInfo("SENS", int, "", "Sensitivität (0=2nV/fA bis 26=1V/uA)")
    RMOD = SR830CommandInfo("RMOD", int, "", "Reserve Mode: 0=High, 1=Normal, 2=Low Noise")
    OFLT = SR830CommandInfo("OFLT", int, "", "Zeitkonstante (0=10us bis 19=30ks)")
    OFSL = SR830CommandInfo("OFSL", int, "", "Low Pass Filter Slope: 0=6, 1=12, 2=18, 3=24 dB/oct")
    SYNC = SR830CommandInfo("SYNC", int, "", "Synchronous Filter: 0=Off, 1=On (<200Hz)")

    AGAN = SR830CommandInfo("AGAN", None, "", "Führt Auto Gain aus")
    ARSV = SR830CommandInfo("ARSV", None, "", "Führt Auto Reserve aus")
    APHS = SR830CommandInfo("APHS", None, "", "Führt Auto Phase aus")

    SRAT = SR830CommandInfo("SRAT", int, "Hz", "Data Sample Rate (0=62.5mHz bis 14=Trigger)")
    SEND = SR830CommandInfo("SEND", int, "", "Scan Mode: 0=1 Shot, 1=Loop")
    STRT = SR830CommandInfo("STRT", None, "", "Startet/Setzt den Scan fort")
    PAUS = SR830CommandInfo("PAUS", None, "", "Pausiert den Scan")
    REST = SR830CommandInfo("REST", None, "", "Setzt den Datenpuffer zurück (Reset)")

    @staticmethod
    def write(command_info, value):
        """Write a value to the SR830 (value translation happens in send())."""
        return send(command_info, value)

    @staticmethod
    def run(command_info):
        """Execute an action command without value."""
        return send(command_info, None)

    @classmethod
    def all(cls):
        """Return all set commands as a list of (name, command_info)."""
        return [
            (name, value)
            for name, value in cls.__dict__.items()
            if not name.startswith("__") and isinstance(value, SR830CommandInfo)
        ]


# =============================================================================
# WERT-ÜBERSETZUNG FÜR SR830
# =============================================================================
# Das SR830-Gerät arbeitet intern oft mit numerischen Indizes.
# Der Mensch verwendet aber Bezeichnungen wie "1 s", "Normal" oder "A-B".
# Diese Mapping-Tabellen übersetzen verständliche Texte in die Gerätewerte.
#
# Beispiel:
#   "SENS" erwartet einen Numerischen Index, z.B. 10.
#   Der Benutzer wählt aber vielleicht "100 nV/fA".
#   Diese Tabelle macht daraus genau den richtigen Index.
#
# So bleibt die GUI benutzerfreundlich, während das Gerät trotzdem die erwarteten Zahlenwerte
# erhält.
# --- Mapping Constants for SR830 ---
SENSITIVITY_VALUES = {
    "2 nV/fA": 0, "5 nV/fA": 1, "10 nV/fA": 2, "20 nV/fA": 3,
    "50 nV/fA": 4, "100 nV/fA": 5, "200 nV/fA": 6, "500 nV/fA": 7,
    "1 uV/pA": 8, "2 uV/pA": 9, "5 uV/pA": 10, "10 uV/pA": 11,
    "20 uV/pA": 12, "50 uV/pA": 13, "100 uV/pA": 14, "200 uV/pA": 15,
    "500 uV/pA": 16, "1 mV/nA": 17, "2 mV/nA": 18, "5 mV/nA": 19,
    "10 mV/nA": 20, "20 mV/nA": 21, "50 mV/nA": 22, "100 mV/nA": 23,
    "200 mV/nA": 24, "500 mV/nA": 25, "1 V/uA": 26,
}
TIME_CONSTANT_VALUES = {
    "10 us": 0, "30 us": 1, "100 us": 2, "300 us": 3,
    "1 ms": 4, "3 ms": 5, "10 ms": 6, "30 ms": 7,
    "100 ms": 8, "300 ms": 9, "1 s": 10, "3 s": 11,
    "10 s": 12, "30 s": 13, "100 s": 14, "300 s": 15,
    "1 ks": 16, "3 ks": 17, "10 ks": 18, "30 ks": 19,
}
RESERVE_VALUES = {"High Reserve": 0, "Normal": 1, "Low Noise": 2}
FILTER_SLOPE_VALUES = {"6 dB/oct": 0, "12 dB/oct": 1, "18 dB/oct": 2, "24 dB/oct": 3}
INPUT_CONFIG_VALUES = {"A": 0, "A-B": 1, "I (1M)": 2, "I (100M)": 3}
GROUNDING_VALUES = {"Float": 0, "Ground": 1}
COUPLING_VALUES = {"AC": 0, "DC": 1}
LINE_NOTCH_VALUES = {"Out": 0, "Line (50/60Hz)": 1, "2x Line": 2, "Both": 3}
SYNCHRONOUS_FILTER_VALUES = {"Off": 0, "On": 1}

# Diese Funktion übernimmt die Übersetzung von Benutzereingaben in das Format, das das
# SR830 tatsächlich verstehen kann.
#
# Eingaben können sein:
# - ein bereits numerischer Index, z.B. 5
# - ein String wie "Normal"
# - ein String wie "1 s"
#
# Die Funktion prüft, zu welchem Befehl die Einstellung gehört und holt dann die passende
# Zuordnungstabelle. Danach liefert sie den gültigen Gerätwert zurück.
#
# Beispiel:
#   resolve_sr830_setting("RMOD", "Normal") -> 1
#   resolve_sr830_setting("OFLT", "1 s") -> 10
#
def resolve_sr830_setting(command_name, value_name_or_index):
    """Translate a human-readable SR830 setting into the numeric index expected by the instrument."""
    mapping = {
        "SENS": SENSITIVITY_VALUES,
        "RMOD": RESERVE_VALUES,
        "OFLT": TIME_CONSTANT_VALUES,
        "OFSL": FILTER_SLOPE_VALUES,
        "ISRC": INPUT_CONFIG_VALUES,
        "IGND": GROUNDING_VALUES,
        "ICPL": COUPLING_VALUES,
        "ILIN": LINE_NOTCH_VALUES,
        "SYNC": SYNCHRONOUS_FILTER_VALUES,
    }.get(command_name.upper())
    if mapping is None:
        return value_name_or_index
    if isinstance(value_name_or_index, (int, float)):
        return int(value_name_or_index)
    if value_name_or_index in mapping:
        return mapping[value_name_or_index]
    try:
        return int(str(value_name_or_index).strip())
    except ValueError:
        pass
    for label, index in mapping.items():
        if str(value_name_or_index).strip().lower() == label.lower():
            return index
    raise ValueError(f"Unbekannter Wert für {command_name}: {value_name_or_index!r}")


# =============================================================================
# OSTECH COMMANDS
# =============================================================================

# OSTechG enthält die Lesebefehle des OSTECH-Geräts.
# Man verwendet diese Befehle, wenn man Messwerte oder Zustände auslesen möchte,
# zum Beispiel Strom, Spannung, Temperatur, Status oder Firmware-Informationen.
# Diese Befehle verändern das Gerät nicht, sondern lesen nur Daten.
class OSTechG:
    """Query-only OSTech commands: read-only / monitoring commands[cite: 2]."""

    LCA = OSTechCommandInfo("LCA", float, "mA", "actual current")
    LVA = OSTechCommandInfo("LVA", float, "V", "actual laser voltage")
    LPCA = OSTechCommandInfo("LPCA", float, "uA", "laser photo current actual")
    LPA  = OSTechCommandInfo("LPA", float, "W", "laser power actual")

    # --- Temperature and TEC 1 Actuals (Präfix 1 für Sensor/TEC 1)[cite: 2] ---
    T1A  = OSTechCommandInfo("1TA", float, "°C", "actual temperature (TEC 1)")
    T1CA = OSTechCommandInfo("1TCA", float, "mA", "actual current (TEC 1)")
    T1VA = OSTechCommandInfo("1TVA", float, "V", "actual voltage (TEC 1)")

    GT   = OSTechCommandInfo("GT", float, "°C", "device temperature (head)")
    GS   = OSTechCommandInfo("GS", int, "", "get status (Bitmask)")
    GM   = OSTechCommandInfo("GM", int, "", "get mode (Bitmask)")
    GVS  = OSTechCommandInfo("GVS", int, "", "software version")
    GVN  = OSTechCommandInfo("GVN", int, "", "serial number")
    GE   = OSTechCommandInfo("GE", int, "", "get error code (see manual chapter 8)")

    @staticmethod
    def read(command_info, return_type=None):
        """Read from the OSTech using command metadata from this class."""
        return read(command_info, return_type)

    @classmethod
    def all(cls):
        """Return all query commands as a list of (name, command_info)."""
        return [
            (name, value)
            for name, value in cls.__dict__.items()
            if not name.startswith("__") and isinstance(value, OSTechCommandInfo)
        ]


# OSTechS enthält die Schreibbefehle des OSTECH-Geräts.
# Diese Befehle aktivieren oder konfigurieren Funktionen wie Laserbetrieb,
# Temperatursteuerung, Stromgrenzen, Betriebspunkte und Modulationsparameter.
# Einige Befehle brauchen einen Wert, andere sind reine Aktionsbefehle wie Start/Stop.
# Das Muster entspricht dem SR830: Definition der Befehle hier, reale Serial-Kommunikation in Komunikation.py.
class OSTechS:
    """Set-only OSTech commands: configuration and action commands[cite: 2]."""

    # type=bool  -> Schalter: send(cmd, 1) sendet "<cmd>R", send(cmd, 0) sendet "<cmd>S"
    #               (run(cmd) ohne Wert = Run).  Beispiel: L -> "LR" / "LS".
    # type=None  -> feste Aktion, wird genau so gesendet (z.B. "LR", "LS", "LGR").
    L = OSTechCommandInfo("L", bool, "", "laser stop/run (LS / LR)")
    LR = OSTechCommandInfo("LR", None, "", "laser run")
    LS = OSTechCommandInfo("LS", None, "", "laser stop")
    LTM = OSTechCommandInfo("LTM", float, "°C", "laser temperature maximum (-99 to 200)")
    LG = OSTechCommandInfo("LG", bool, "", "gate option (LGR / LGS)")
    LGR = OSTechCommandInfo("LGR", None, "", "gate option run/enable")
    LGS = OSTechCommandInfo("LGS", None, "", "gate option stop/disable")

    LCL = OSTechCommandInfo("LCL", float, "mA", "current limit")
    LCT = OSTechCommandInfo("LCT", float, "mA", "current target")
    LCB = OSTechCommandInfo("LCB", float, "mA", "base or bias current")
    LVC = OSTechCommandInfo("LVC", float, "V", "compliance voltage (1.3 to 6)")
    LCLM = OSTechCommandInfo("LCLM", float, "mA", "limit for average laser current")

    LPCT = OSTechCommandInfo("LPCT", float, "uA", "laser photo current target (0 to 20)")
    LPT  = OSTechCommandInfo("LPT", float, "W", "laser power target")
    LPCC = OSTechCommandInfo("LPCC", bool, "", "laser photo current control (S/R)")
    LPCCR = OSTechCommandInfo("LPCCR", None, "", "laser photo current control run")
    LPCCS = OSTechCommandInfo("LPCCS", None, "", "laser photo current control stop")
    LPF   = OSTechCommandInfo("LPF", None, "", "laser power fix procedure")

    LMDI = OSTechCommandInfo("LMDI", bool, "", "internal digital modulation (S/R)")
    LMDX = OSTechCommandInfo("LMDX", bool, "", "external digital modulation (S/R)")
    LMAX = OSTechCommandInfo("LMAX", bool, "", "external analog modulation (S/R)")
    LMDXN = OSTechCommandInfo("LMDXN", bool, "", "negate modulation input (R = negate)")
    LMDIR = OSTechCommandInfo("LMDIR", None, "", "internal digital modulation run")
    LMDIS = OSTechCommandInfo("LMDIS", None, "", "internal digital modulation stop")
    LMW = OSTechCommandInfo("LMW", float, "us", "pulse width")
    LMP = OSTechCommandInfo("LMP", float, "us", "pulse period")
    LMDIC = OSTechCommandInfo("LMDIC", int, "", "number of pulses (0 = continuous, 1 = single)")
    PC = LMDIC  # Alias: "pulse count" im Laser-Menue

    PL = OSTechCommandInfo("PL", bool, "", "pilot laser stop/run (S/R)")
    PLR = OSTechCommandInfo("PLR", None, "", "pilot laser run")
    PLS = OSTechCommandInfo("PLS", None, "", "pilot laser stop")
    PP  = OSTechCommandInfo("PP", int, "", "pilot laser modulation (0 to 16)")

    # --- Temperature Controller TEC 1 (Präfix 1)[cite: 2] ---
    T1C = OSTechCommandInfo("1TC", bool, "", "temperature controller 1 stop/run (S/R)")
    T1CR = OSTechCommandInfo("1TCR", None, "", "temperature controller 1 run")
    T1CS = OSTechCommandInfo("1TCS", None, "", "temperature controller 1 stop")
    T1TT = OSTechCommandInfo("1TT", float, "°C", "temperature target TEC 1")
    T1TLU = OSTechCommandInfo("1TLU", float, "°C", "upper temperature limit TEC 1")
    T1TLL = OSTechCommandInfo("1TLL", float, "°C", "lower temperature limit TEC 1")
    T1CL = OSTechCommandInfo("1TCL", float, "mA", "current limit TEC 1")
    
    T1CCK = OSTechCommandInfo("1TCCK", float, "", "PID parameter: gain factor TEC 1")
    T1CCN = OSTechCommandInfo("1TCCN", float, "s", "PID parameter: reset time TEC 1")
    T1CCV = OSTechCommandInfo("1TCCV", float, "s", "PID parameter: rate time TEC 1")

    GF  = OSTechCommandInfo("GF", float, "V", "fan voltage (1.2 to 24)")
    GFD = OSTechCommandInfo("GFD", float, "V", "default fan voltage")
    GXR = OSTechCommandInfo("GXR", None, "", "switch to external (RS232) control")
    GXS = OSTechCommandInfo("GXS", None, "", "release external control")
    # Achtung: GMS8/GMC8 schalten den Binaermodus. Komunikation.py verwaltet das selbst.
    GMS8 = OSTechCommandInfo("GMS8", int, "", "set mode bit for binary mode")
    GMC8 = OSTechCommandInfo("GMC8", int, "", "clear mode bit for standard mode")

    @staticmethod
    def write(command_info, value):
        """Write a value to the OSTech (wire formatting happens in send())."""
        return send(command_info, value)

    @staticmethod
    def run(command_info):
        """Execute an action command without value (bool switches: Run)."""
        return send(command_info, None)

    @classmethod
    def all(cls):
        """Return all set commands as a list of (name, command_info)."""
        return [
            (name, value)
            for name, value in cls.__dict__.items()
            if not name.startswith("__") and isinstance(value, OSTechCommandInfo)
        ]


# =============================================================================
# UNIFIED HIGH-LEVEL API
# =============================================================================

# _normalize_command macht die öffentliche API robust.
# Man kann einer Funktion entweder:
# - ein Command-Objekt übergeben, z.B. SR830S.SENS
# - oder einen reinen String, z.B. "SENS"
#
# Die Funktion erkennt dann, welcher Befehl gemeint ist und gibt das passende Metadatenobjekt zurück.
# Wenn der String nicht gefunden wird, bleibt er unverändert und kann später als Fehler behandelt werden.
def _normalize_command(command):
    """Accept either metadata or a raw command string and return the command metadata."""
    if hasattr(command, "command"):
        return command
    if isinstance(command, str):
        # Check all available classes to find the matching command string
        for category in (SR830G, SR830S, OSTechG, OSTechS):
            for _, info in category.all():
                if info.command == command:
                    return info
        return command
    raise TypeError(f"Unbekannter Befehl: {command!r}")


# Allgemeine API-Funktionen:
# send()  = etwas an das Gerät senden, meistens mit einem Wert
# read()  = etwas vom Gerät lesen, ohne es zu verändern
# set()   = kurze Schreibversion, praktisch wie send()
# run()   = Aktion ausführen, ohne Zahlenwert, z.B. Auto Gain oder Laser starten
# Diese Funktionen bilden die „sprechende“ Oberfläche für GUI, Threads und andere Module.
# =============================================================================
# ÖFFENTLICHE HIGH-LEVEL API-FUNKTIONEN
# =============================================================================
# Diese Funktionen sind die benutzerfreundliche Oberfläche für alle anderen Module.
# GUI, Threads und andere Komponenten sollten nicht direkt mit den Hardware-Funktionen aus
# Komunikation.py arbeiten, sondern über diese Funktionen.
#
# Dadurch bleibt die Anwendung sauber organisiert:
# - GUI fragt: "Was soll ich setzen?"
# - Send.py entscheidet: "Welcher Befehl passt dazu?"
# - Komunikation.py schickt den tatsächlichen Text an das Gerät.
#
# So sind Befehlsdefinition und Übertragung sauber voneinander getrennt.

def _ostech_wire(info, value):
    """Return ``(wire_command, wire_value, reply_type)`` for an OSTech command."""
    command = info.command
    if info.type is bool:                       # Schalter -> Suffix R / S
        if value is None:
            value = True
        if isinstance(value, str):
            value = value.strip().lower() in ("1", "true", "on", "run", "r", "yes")
        return command + ("R" if value else "S"), None, bool
    if value is None:
        reply = info.type if info.type in (int, float, str) else bool
        return command, None, reply
    if info.type is int:
        value = int(round(float(value)))
    elif info.type is float:
        value = float(value)
    return command, value, info.type


def _sr830_value(info, value):
    """Translate GUI text (e.g. "1 s", "Normal") and coerce to the command's type."""
    if value is None or not hasattr(info, "command"):
        return value
    resolved = resolve_sr830_setting(info.command, value)
    if info.type is int:
        return int(round(float(resolved)))
    if info.type is float:
        return float(resolved)
    return resolved


def _sr830_query_form(info):
    """Settings are queried by appending '?' (e.g. FREQ -> FREQ?)."""
    if hasattr(info, "command") and not info.command.endswith("?"):
        base = info.command.split(" ")[0]
        return SR830CommandInfo(base + "?", info.type, info.unit, info.description)
    return info


# Feste Aktionsbefehle -> (Zwillings-Schluessel, Sollwert)
_OSTECH_ACTION_DESIRED = {
    "LR": ("L", True), "LS": ("L", False),
    "LGR": ("LG", True), "LGS": ("LG", False),
    "LMDIR": ("LMDI", True), "LMDIS": ("LMDI", False),
    "PLR": ("PL", True), "PLS": ("PL", False),
    "1TCR": ("1TC", True), "1TCS": ("1TC", False),
}


def _record_desired(device, info, wire_command, wire_value):
    """Tell the digital twin which value was just commanded (Soll) and request a readback (Ist).

    Never raises: a twin problem must not break command sending.
    """
    try:
        import Komunikation
        import State

        key, desired = None, None
        if device == "OSTECH":
            if wire_command in _OSTECH_ACTION_DESIRED:
                key, desired = _OSTECH_ACTION_DESIRED[wire_command]
            elif info.type is bool:
                key, desired = info.command, wire_command.endswith("R")
            elif wire_value is not None:
                key, desired = info.command, wire_value
        elif wire_value is not None:
            key, desired = info.command, wire_value

        if key is not None and key in Komunikation.readable_settings(device):
            State.twin_set_desired(device, key, desired)
            Komunikation.request_settings_refresh(device)
    except Exception:
        pass


def send(command, value=None):
    """Public API: send any SR830 or OSTech command via the Send layer."""
    import Komunikation
    import Log

    command_info = _normalize_command(command)
    command_name = getattr(command_info, "command", str(command_info))

    if isinstance(command_info, OSTechCommandInfo):
        wire_command, wire_value, reply_type = _ostech_wire(command_info, value)
        Log.Log("Send", "OSTech", "Running", wire_command, wire_value if wire_value is not None else "", "set value")
        result = Komunikation.send_OSTECH(wire_command, wire_value, return_type=reply_type)
        _record_desired("OSTECH", command_info, wire_command, wire_value)
        return result

    sr_value = _sr830_value(command_info, value)
    Log.Log("Send", "SR830", "Running", command_name, sr_value, "set value")
    result = Komunikation.send_SR830(command_info, sr_value)
    _record_desired("SR830", command_info, command_name, sr_value)
    return result


def read(command, return_type=None):
    """Public API: query any SR830 or OSTech command via the Send layer."""
    import Komunikation
    import Log

    command_info = _normalize_command(command)
    command_name = getattr(command_info, "command", str(command_info))

    if isinstance(command_info, OSTechCommandInfo):
        Log.Log("Send", "OSTech", "Running", command_name, "read request", "query")
        actual_type = command_info.type if return_type is None else return_type
        if actual_type is None:
            actual_type = bool
        return Komunikation.ask_OSTECH(command_info.command, return_type=actual_type)

    if hasattr(command_info, "command"):
        if command_info in dict(SR830S.all()).values():
            command_info = _sr830_query_form(command_info)
        Log.Log("Send", "SR830", "Running", command_info.command, "read request", "query")
        actual_type = command_info.type if return_type is None else return_type
        return Komunikation.ask_SR830(command_info, return_type=actual_type)
    Log.Log("Send", "SR830", "Running", command_name, "read request", "query")
    return Komunikation.ask_SR830(command, return_type=return_type)


# set() ist die kurze Form für "einen Wert setzen".
# Praktisch ist sie ein Alias für send().
# Das ist bequem für ein einheitliches API, wenn der Code nur "setzen" und nicht "send" sagen will.
def set(command, value):
    """Public API: set a value via the Send layer."""
    return send(command, value)


# run() dient für Befehle, die keinen numerischen Wert benötigen.
# Typische Beispiele: Start/Stop, Auto-Funktionen, Aktivieren/Deaktivieren.
# Diese Befehle sind in der Regel reine Aktionen, keine Konfigurationswerte.
def run(command):
    """Public API: execute an action command without a value (bool switches: Run)."""
    return send(command, None)


# list_commands sammelt alle verfügbaren Befehle in einer übersichtlichen Menge.
# Dabei kann man gezielt filtern:
# - nur Lesen oder nur Schreiben
# - nur SR830 oder nur OSTECH
# - oder einfach alles zusammen
#
# Das ist sehr praktisch für GUI-Listen, Debug-Ausgaben oder automatische Kommandolisten.
def list_commands(kind=None, device=None):
    """Return command metadata with optional filtering by get/set and device (sr830/ostech)."""
    commands = []
    
    # Filter by Device
    if device is None or device.lower() == "sr830":
        if kind is None or kind.lower() in {"get", "g", "read", "query"}:
            commands.extend(SR830G.all())
        if kind is None or kind.lower() in {"set", "s", "write", "command"}:
            commands.extend(SR830S.all())
            
    if device is None or device.lower() == "ostech":
        if kind is None or kind.lower() in {"get", "g", "read", "query"}:
            commands.extend(OSTechG.all())
        if kind is None or kind.lower() in {"set", "s", "write", "command"}:
            commands.extend(OSTechS.all())
            
    return commands

# Backwards compatibility names
list_sr830_commands = lambda kind=None: list_commands(kind, device="sr830")
list_ostech_commands = lambda kind=None: list_commands(kind, device="ostech")

SR830GetCommands = SR830G
SR830SetCommands = SR830S
OSTechGetCommands = OSTechG
OSTechSetCommands = OSTechS

__all__ = [
    "SR830CommandInfo",
    "OSTechCommandInfo",
    "SR830G",
    "SR830S",
    "OSTechG",
    "OSTechS",
    "SR830GetCommands",
    "SR830SetCommands",
    "OSTechGetCommands",
    "OSTechSetCommands",
    "send",
    "read",
    "set",
    "run",
    "list_commands",
    "list_sr830_commands",
    "list_ostech_commands",
]
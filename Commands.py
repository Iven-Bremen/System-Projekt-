from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class OSTECHCommandInfo:
    """Complete command description based on the OSTECH command reference."""
    
    command: str
    data_type: type
    minimum: str | float | None = None
    maximum: str | float | None = None
    default: str | float | None = None
    unit: str = ""
    description: str = ""

    @property
    def type_name(self) -> str:
        return {bool: "bool", float: "float", int: "word"}.get(self.data_type, self.data_type.__name__)

    @property
    def type(self) -> str:
        return self.type_name


@dataclass(frozen=True)
class OSTECHResult:
    value: object
    info: OSTECHCommandInfo

    @property
    def command(self):
        return self.info.command

    @property
    def data_type(self):
        return self.info.data_type

    @property
    def minimum(self):
        return self.info.minimum

    @property
    def maximum(self):
        return self.info.maximum

    @property
    def default(self):
        return self.info.default

    @property
    def type_name(self):
        return self.info.type_name

    @property
    def unit(self):
        return self.info.unit

    @property
    def description(self):
        return self.info.description

    def __str__(self):
        return str(self.value)


class OSTECHCommand(Enum):
    #   Aufbau der OsTechEnum  (    cmd     ,   type    ,   min         ,   max         ,   default     ,   unit    ,   description                         )

    L       = OSTECHCommandInfo(    "L"     ,   bool    ,   "S"         ,   "R"         ,   "S"         ,   ""      ,   "laser stop/run"                    )#
    LTM     = OSTECHCommandInfo(    "LTM"   ,   float   ,   -99.0       ,   200.0       ,   35.0        ,   "°C"    ,   "laser temperature maximum"         )#
    LG      = OSTECHCommandInfo(    "LG"    ,   bool    ,   "S"         ,   "R"         ,   "S"         ,   ""      ,   "gate option"                       )#
    LCL     = OSTECHCommandInfo(    "LCL"   ,   float   ,   0.0         ,   "Imax + 5%" ,   "Imax + 5%" ,   "mA"    ,   "current limit"                     )#
    LCT     = OSTECHCommandInfo(    "LCT"   ,   float   ,   0.0         ,   "Imax"      ,   0.0         ,   "mA"    ,   "current target"                    )#
    LCA     = OSTECHCommandInfo(    "LCA"   ,   float   ,   None        ,   None        ,   None        ,   "mA"    ,   "actual current"                    )#
    LCB     = OSTECHCommandInfo(    "LCB"   ,   float   ,   0.0         ,   "Imax"      ,   0.0         ,   "mA"    ,   "base or bias current"              )#
    LVA     = OSTECHCommandInfo(    "LVA"   ,   float   ,   None        ,   None        ,   None        ,   "V"     ,   "actual laser voltage"              )#
    LVC     = OSTECHCommandInfo(    "LVC"   ,   float   ,   1.3         ,   6.0         ,   3.0         ,   "V"     ,   "compliance voltage"                )#
    LPCA    = OSTECHCommandInfo(    "LPCA"  ,   float   ,   None        ,   None        ,   None        ,   "µA"    ,   "laser photo current actual"        )#
    LPCT    = OSTECHCommandInfo(    "LPCT"  ,   float   ,   0.0         ,   20.0        ,   0.0         ,   "µA"    ,   "laser photo current target"        )#
    LPCC    = OSTECHCommandInfo(    "LPCC"  ,   bool    ,   "S"         ,   "R"         ,   "S"         ,   ""      ,   "laser photo current control"       )#
    LPA     = OSTECHCommandInfo(    "LPA"   ,   float   ,   None        ,   None        ,   None        ,   "W"     ,   "laser power actual"                )#
    LPT     = OSTECHCommandInfo(    "LPT"   ,   float   ,   0.0         ,   None        ,   0.0         ,   "W"     ,   "laser power target"                )#
    LPF     = OSTECHCommandInfo(    "LPF"   ,   bool    ,   "S"         ,   "R"         ,   "S"         ,   ""      ,   "laser power fix procedure"         )#
    LMDI    = OSTECHCommandInfo(    "LMDI"  ,   bool    ,   "S"         ,   "R"         ,   "S"         ,   ""      ,   "internal digital modulation"       )#
    LMDX    = OSTECHCommandInfo(    "LMDX"  ,   bool    ,   "S"         ,   "R"         ,   "S"         ,   ""      ,   "external digital modulation"       )#
    LMAX    = OSTECHCommandInfo(    "LMAX"  ,   bool    ,   "S"         ,   "R"         ,   "S"         ,   ""      ,   "external analog modulation"        )#
    LMW     = OSTECHCommandInfo(    "LMW"   ,   float   ,   1.0         ,   "> 48 h"    ,   1000.0      ,   "µs"    ,   "pulse width"                       )#
    LMP     = OSTECHCommandInfo(    "LMP"   ,   float   ,   "LMW + 1"   ,   "> 48 h"    ,   2000.0      ,   "µs"    ,   "pulse period"                      )#
    LMDIC   = OSTECHCommandInfo(    "LMDIC" ,   int     ,   0.0         ,   65534.0     ,   0.0         ,   ""      ,   "number of pulses"                  )#
    LMDXN   = OSTECHCommandInfo(    "LMDXN" ,   bool    ,   "S"         ,   "R"         ,   "S"         ,   ""      ,   "negate modulation input"           )#
    LZTR    = OSTECHCommandInfo(    "LZTR"  ,   float   ,   300.0       ,   34000.0     ,   300.0       ,   "ms"    ,   "ramp time"                         )#
    LZR     = OSTECHCommandInfo(    "LZR"   ,   bool    ,   None        ,   None        ,   None        ,   ""      ,   "sequencer run (stop with IS)"      )#
    LZP     = OSTECHCommandInfo(    "LZP"   ,   int     ,   None        ,   None        ,   None        ,   "ms"    ,   "sequencer point select"            )#
    LZPT    = OSTECHCommandInfo(    "LZPT"  ,   int     ,   None        ,   None        ,   None        ,   "ms"    ,   "subsequence time (duration)"       )#
    LZPC    = OSTECHCommandInfo(    "LZPC"  ,   float   ,   None        ,   None        ,   None        ,   "mA"    ,   "subsequence current (end)"         )#
    PL      = OSTECHCommandInfo(    "PL"    ,   bool    ,   "S"         ,   "R"         ,   "S"         ,   ""      ,   "pilot laser stop/run"              )#
    PP      = OSTECHCommandInfo(    "PP"    ,   int     ,   0.0         ,   16.0        ,   0.0         ,   ""      ,   "pilot laser modulation"            )#
    XTA     = OSTECHCommandInfo(    "xTA"   ,   float   ,   None        ,   None        ,   None        ,   "°C"    ,   "actual temperature"                )#
    XTLU    = OSTECHCommandInfo(    "xTLU"  ,   float   ,   -99.0       ,   200.0       ,   40.0        ,   "°C"    ,   "upper temperature limit"           )#
    XTLL    = OSTECHCommandInfo(    "xTLL"  ,   float   ,   -99.0       ,   200.0       ,   0.0         ,   "°C"    ,   "lower temperature limit"           )#
    XTSC    = OSTECHCommandInfo(    "xTSC"  ,   float   ,   None        ,   None        ,   "NTC B3980" ,   ""      ,   "sensor coefficients"               )#
    XTSM    = OSTECHCommandInfo(    "xTSM"  ,   int     ,   0.0         ,   1.0         ,   0.0         ,   ""      ,   "sensor approximation model"        )#
    XTC     = OSTECHCommandInfo(    "xTC"   ,   bool    ,   "S"         ,   "R"         ,   "S"         ,   ""      ,   "temperature controller stop/run"   )#
    XTT     = OSTECHCommandInfo(    "xTT"   ,   float   ,   -99.0       ,   200.0       ,   20.0        ,   "°C"    ,   "temperature target"                )#
    XTCA    = OSTECHCommandInfo(    "xTCA"  ,   float   ,   None        ,   None        ,   None        ,   "mA"    ,   "actual current"                    )#
    XTCL    = OSTECHCommandInfo(    "xTCL"  ,   float   ,   0.0         ,   "Imax"      ,   "Imax"      ,   "mA"    ,   "current limit"                     )#
    XTVA    = OSTECHCommandInfo(    "xTVA"  ,   float   ,   None        ,   None        ,   None        ,   "V"     ,   "actual voltage"                    )#
    XTCCK   = OSTECHCommandInfo(    "xTCCK" ,   float   ,   0.0         ,   255.0       ,   2.0         ,   ""      ,   "PID parameter: gain factor"        )#
    XTCCN   = OSTECHCommandInfo(    "xTCCN" ,   float   ,   0.0         ,   255.0       ,   60.0        ,   "s"     ,   "PID parameter: reset time"         )#
    XTCCV   = OSTECHCommandInfo(    "xTCCV" ,   float   ,   0.0         ,   99.0        ,   1.0         ,   "s"     ,   "PID parameter: rate time"          )#
    GD      = OSTECHCommandInfo(    "GD"    ,   bool    ,   None        ,   None        ,   None        ,   ""      ,   "set defaults"                      )#
    GF      = OSTECHCommandInfo(    "GF"    ,   float   ,   1.2         ,   24.0        ,   5.0         ,   "V"     ,   "fan voltage (max. 300 mA)"         )#
    GFD     = OSTECHCommandInfo(    "GFD"   ,   float   ,   1.2         ,   24.0        ,   5.0         ,   "V"     ,   "default fan voltage"               )#
    GX      = OSTECHCommandInfo(    "GX"    ,   bool    ,   "S"         ,   "R"         ,   "S"         ,   ""      ,   "external control stop/run"         )#
    GT      = OSTECHCommandInfo(    "GT"    ,   float   ,   None        ,   None        ,   None        ,   "°C"    ,   "device temperature (head)"         )#
    GVS     = OSTECHCommandInfo(    "GVS"   ,   int     ,   None        ,   None        ,   None        ,   ""      ,   "software version"                  )#
    GVN     = OSTECHCommandInfo(    "GVN"   ,   int     ,   None        ,   None        ,   None        ,   ""      ,   "serial number"                     )#
    GS      = OSTECHCommandInfo(    "GS"    ,   int     ,   None        ,   None        ,   None        ,   ""      ,   "get status"                        )#
    GM      = OSTECHCommandInfo(    "GM"    ,   int     ,   None        ,   None        ,   None        ,   ""      ,   "get mode"                          )#
    GMC     = OSTECHCommandInfo(    "GMC"   ,   int     ,   None        ,   None        ,   None        ,   ""      ,   "clear mode bits"                   )#
    GMS     = OSTECHCommandInfo(    "GMS"   ,   int     ,   None        ,   None        ,   None        ,   ""      ,   "set mode bits"                     )#
    GMT     = OSTECHCommandInfo(    "GMT"   ,   int     ,   None        ,   None        ,   None        ,   ""      ,   "toggle mode bits"                  )#











@dataclass(frozen=True)
class SR830CommandInfo:
    """Complete command description based on the SR830 command reference."""
    
    command: str
    data_type: type
    minimum: str | float | None = None
    maximum: str | float | None = None
    default: str | float | None = None
    unit: str = ""
    description: str = ""
    queryable: bool = True

    @property
    def type_name(self) -> str:
        return {bool: "bool", float: "float", int: "word"}.get(self.data_type, self.data_type.__name__)

    @property
    def type(self) -> str:
        return self.type_name

    def build(self, *parameters, query: bool | None = None) -> str:
        """Build an SR830 command with optional query and parameters.

        Examples: ``SRAT.value.build(4)``, ``OUTP.value.build(1)`` and
        ``SNAP.value.build(1, 2)``.
        """
        base_command = self.command.rstrip("?")
        is_query_only = self.command.endswith("?")
        if query is None:
            query = is_query_only
        if query and not self.queryable:
            raise ValueError(f"{base_command} does not support queries")
        if is_query_only and query is False:
            query = True

        command = f"{base_command}{'?' if query else ''}"
        if parameters:
            values = ",".join(str(parameter) for parameter in parameters)
            command = f"{command} {values}"
        return command


@dataclass(frozen=True)
class SR830Result:
    value: object
    info: SR830CommandInfo

    @property
    def command(self):
        return self.info.command

    @property
    def data_type(self):
        return self.info.data_type

    @property
    def minimum(self):
        return self.info.minimum

    @property
    def maximum(self):
        return self.info.maximum

    @property
    def default(self):
        return self.info.default

    @property
    def type_name(self):
        return self.info.type_name

    @property
    def unit(self):
        return self.info.unit

    @property
    def description(self):
        return self.info.description

    def __str__(self):
        return str(self.value)


class SR830Command(Enum):
    #   Aufbau der SR830Enum  ( cmd    , type   , min  , max  , default , unit , description )

    PHAS = SR830CommandInfo("PHAS", float, -360.0, 729.99, 0.0, "deg", "reference phase shift")
    FMOD = SR830CommandInfo("FMOD", int, 0, 1, 1, "", "reference source: external or internal")
    FREQ = SR830CommandInfo("FREQ", float, 0.001, 102000.0, 1000.0, "Hz", "reference frequency")
    RSLP = SR830CommandInfo("RSLP", int, 0, 2, 0, "", "external reference trigger slope")
    HARM = SR830CommandInfo("HARM", int, 1, 19999, 1, "", "detection harmonic")
    SLVL = SR830CommandInfo("SLVL", float, 0.004, 5.0, 1.0, "V", "sine output amplitude")

    ISRC = SR830CommandInfo("ISRC", int, 0, 3, 0, "", "input configuration")
    IGND = SR830CommandInfo("IGND", int, 0, 1, 0, "", "input shield grounding")
    ICPL = SR830CommandInfo("ICPL", int, 0, 1, 0, "", "input coupling")
    ILIN = SR830CommandInfo("ILIN", int, 0, 3, 0, "", "input line notch filters")

    SENS = SR830CommandInfo("SENS", int, 0, 26, 26, "", "sensitivity")
    RMOD = SR830CommandInfo("RMOD", int, 0, 2, 1, "", "dynamic reserve mode")
    OFLT = SR830CommandInfo("OFLT", int, 0, 18, 10, "", "time constant")
    OFSL = SR830CommandInfo("OFSL", int, 0, 3, 0, "", "low-pass filter slope")
    SYNC = SR830CommandInfo("SYNC", int, 0, 1, 0, "", "synchronous filter")

    DDEF = SR830CommandInfo("DDEF", int, 1, 2, description="CH1 or CH2 display selection")
    FPOP = SR830CommandInfo("FPOP", int, 1, 2, description="front-panel output source")
    OEXP = SR830CommandInfo("OEXP", int, 1, 3, description="output offset and expand")
    AOFF = SR830CommandInfo("AOFF", int, 1, 3, description="automatic output offset", queryable=False)

    OAUX = SR830CommandInfo("OAUX?", float, 1, 4, unit="V", description="auxiliary input voltage")
    AUXV = SR830CommandInfo("AUXV", float, -10.5, 10.5, 0.0, "V", "auxiliary output voltage")

    OUTX = SR830CommandInfo("OUTX", int, 0, 1, 0, "", "output interface selection")
    OVRM = SR830CommandInfo("OVRM", int, 0, 1, 1, "", "GPIB override remote")
    KCLK = SR830CommandInfo("KCLK", int, 0, 1, 1, "", "key click")
    ALRM = SR830CommandInfo("ALRM", int, 0, 1, 0, "", "alarm")
    SSET = SR830CommandInfo("SSET", int, 1, 9, description="save current setup")
    RSET = SR830CommandInfo("RSET", int, 1, 9, description="recall saved setup")

    AGAN = SR830CommandInfo("AGAN", bool, description="automatic gain", queryable=False)
    ARSV = SR830CommandInfo("ARSV", bool, description="automatic reserve", queryable=False)
    APHS = SR830CommandInfo("APHS", bool, description="automatic phase", queryable=False)

    SRAT = SR830CommandInfo("SRAT", int, 0, 14, description="data sample rate")
    SEND = SR830CommandInfo("SEND", int, 0, 1, 1, description="end-of-buffer mode")
    TRIG = SR830CommandInfo("TRIG", bool, description="software trigger", queryable=False)
    TSTR = SR830CommandInfo("TSTR", int, 0, 1, 0, description="trigger starts scan")
    STRT = SR830CommandInfo("STRT", bool, description="start or continue a scan", queryable=False)
    PAUS = SR830CommandInfo("PAUS", bool, description="pause a scan", queryable=False)
    REST = SR830CommandInfo("REST", bool, description="reset the scan and erase stored data", queryable=False)

    OUTP = SR830CommandInfo("OUTP?", float, 1, 4, unit="V/deg", description="X, Y, R or theta output")
    OUTR = SR830CommandInfo("OUTR?", float, 1, 2, unit="display units", description="CH1 or CH2 display output")
    SNAP = SR830CommandInfo("SNAP?", float, 1, 11, description="simultaneous output snapshot")
    SPTS = SR830CommandInfo("SPTS?", int, 0, 16383, unit="points", description="stored data point count")
    TRCA = SR830CommandInfo("TRCA?", float, unit="display units", description="ASCII trace data")
    TRCB = SR830CommandInfo("TRCB?", bytes, unit="display units", description="IEEE binary trace data")
    TRCL = SR830CommandInfo("TRCL?", bytes, unit="display units", description="SR830 binary trace data")
    FAST = SR830CommandInfo("FAST", int, 0, 2, 0, description="fast binary X/Y data transfer")
    STRD = SR830CommandInfo("STRD", bool, description="start scan after fast-transfer delay", queryable=False)

    RST = SR830CommandInfo("*RST", bool, description="reset to default configuration", queryable=False)
    IDN = SR830CommandInfo("*IDN?", str, description="device identification")
    LOCL = SR830CommandInfo("LOCL", int, 0, 2, 0, description="local, remote or local-lockout state")

    CLS = SR830CommandInfo("*CLS", bool, description="clear all status registers", queryable=False)
    ESE = SR830CommandInfo("*ESE", int, 0, 255, 0, description="standard event status enable register")
    ESR = SR830CommandInfo("*ESR?", int, 0, 255, description="standard event status byte")
    SRE = SR830CommandInfo("*SRE", int, 0, 255, 0, description="serial poll enable register")
    STB = SR830CommandInfo("*STB?", int, 0, 255, description="serial poll status byte")
    PSC = SR830CommandInfo("*PSC", int, 0, 1, 0, description="power-on status clear")
    ERRE = SR830CommandInfo("ERRE", int, 0, 255, 0, description="error status enable register")
    ERRS = SR830CommandInfo("ERRS?", int, 0, 255, description="error status byte")
    LIAE = SR830CommandInfo("LIAE", int, 0, 255, 0, description="lock-in status enable register")
    LIAS = SR830CommandInfo("LIAS?", int, 0, 255, description="lock-in status byte")

    def build(self, *parameters, query: bool | None = None) -> str:
        """Build this SR830 command, optionally adding query parameters."""
        return self.value.build(*parameters, query=query)



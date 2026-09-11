import struct
from dataclasses import dataclass
from enum import Enum

import serial
import time
import TestingLog


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
    L = OSTECHCommandInfo("L", bool, "S", "R", "S", "", "laser stop/run")
    LTM = OSTECHCommandInfo("LTM", float, -99.0, 200.0, 35.0, "°C", "laser temperature maximum")
    LG = OSTECHCommandInfo("LG", bool, "S", "R", "S", "", "gate option")
    LCL = OSTECHCommandInfo("LCL", float, 0.0, "Imax + 5%", "Imax + 5%", "mA", "current limit")
    LCT = OSTECHCommandInfo("LCT", float, 0.0, "Imax", 0.0, "mA", "current target")
    LCA = OSTECHCommandInfo("LCA", float, None, None, None, "mA", "actual current")
    LCB = OSTECHCommandInfo("LCB", float, 0.0, "Imax", 0.0, "mA", "base or bias current")
    LVA = OSTECHCommandInfo("LVA", float, None, None, None, "V", "actual laser voltage")
    LVC = OSTECHCommandInfo("LVC", float, 1.3, 6.0, 3.0, "V", "compliance voltage")
    LPCA = OSTECHCommandInfo("LPCA", float, None, None, None, "µA", "laser photo current actual")
    LPCT = OSTECHCommandInfo("LPCT", float, 0.0, 20.0, 0.0, "µA", "laser photo current target")
    LPCC = OSTECHCommandInfo("LPCC", bool, "S", "R", "S", "", "laser photo current control")
    LPA = OSTECHCommandInfo("LPA", float, None, None, None, "W", "laser power actual")
    LPT = OSTECHCommandInfo("LPT", float, 0.0, None, 0.0, "W", "laser power target")
    LPF = OSTECHCommandInfo("LPF", bool, "S", "R", "S", "", "laser power fix procedure")
    LMDI = OSTECHCommandInfo("LMDI", bool, "S", "R", "S", "", "internal digital modulation")
    LMDX = OSTECHCommandInfo("LMDX", bool, "S", "R", "S", "", "external digital modulation")
    LMAX = OSTECHCommandInfo("LMAX", bool, "S", "R", "S", "", "external analog modulation")
    LMW = OSTECHCommandInfo("LMW", float, 1.0, "> 48 h", 1000.0, "µs", "pulse width")
    LMP = OSTECHCommandInfo("LMP", float, "LMW + 1", "> 48 h", 2000.0, "µs", "pulse period")
    LMDIC = OSTECHCommandInfo("LMDIC", int, 0.0, 65534.0, 0.0, "", "number of pulses")
    LMDXN = OSTECHCommandInfo("LMDXN", bool, "S", "R", "S", "", "negate modulation input")
    LZTR = OSTECHCommandInfo("LZTR", float, 300.0, 34000.0, 300.0, "ms", "ramp time")
    LZR = OSTECHCommandInfo("LZR", bool, None, None, None, "", "sequencer run (stop with IS)")
    LZP = OSTECHCommandInfo("LZP", int, None, None, None, "ms", "sequencer point select")
    LZPT = OSTECHCommandInfo("LZPT", int, None, None, None, "ms", "subsequence time (duration)")
    LZPC = OSTECHCommandInfo("LZPC", float, None, None, None, "mA", "subsequence current (end)")
    PL = OSTECHCommandInfo("PL", bool, "S", "R", "S", "", "pilot laser stop/run")
    PP = OSTECHCommandInfo("PP", int, 0.0, 16.0, 0.0, "", "pilot laser modulation")
    XTA = OSTECHCommandInfo("xTA", float, None, None, None, "°C", "actual temperature")
    XTLU = OSTECHCommandInfo("xTLU", float, -99.0, 200.0, 40.0, "°C", "upper temperature limit")
    XTLL = OSTECHCommandInfo("xTLL", float, -99.0, 200.0, 0.0, "°C", "lower temperature limit")
    XTSC = OSTECHCommandInfo("xTSC", float, None, None, "NTC B3980", "", "sensor coefficients")
    XTSM = OSTECHCommandInfo("xTSM", int, 0.0, 1.0, 0.0, "", "sensor approximation model")
    XTC = OSTECHCommandInfo("xTC", bool, "S", "R", "S", "", "temperature controller stop/run")
    XTT = OSTECHCommandInfo("xTT", float, -99.0, 200.0, 20.0, "°C", "temperature target")
    XTCA = OSTECHCommandInfo("xTCA", float, None, None, None, "mA", "actual current")
    XTCL = OSTECHCommandInfo("xTCL", float, 0.0, "Imax", "Imax", "mA", "current limit")
    XTVA = OSTECHCommandInfo("xTVA", float, None, None, None, "V", "actual voltage")
    XTCCK = OSTECHCommandInfo("xTCCK", float, 0.0, 255.0, 2.0, "", "PID parameter: gain factor")
    XTCCN = OSTECHCommandInfo("xTCCN", float, 0.0, 255.0, 60.0, "s", "PID parameter: reset time")
    XTCCV = OSTECHCommandInfo("xTCCV", float, 0.0, 99.0, 1.0, "s", "PID parameter: rate time")
    GD = OSTECHCommandInfo("GD", bool, None, None, None, "", "set defaults")
    GF = OSTECHCommandInfo("GF", float, 1.2, 24.0, 5.0, "V", "fan voltage (max. 300 mA)")
    GFD = OSTECHCommandInfo("GFD", float, 1.2, 24.0, 5.0, "V", "default fan voltage")
    GX = OSTECHCommandInfo("GX", bool, "S", "R", "S", "", "external control stop/run")
    GT = OSTECHCommandInfo("GT", float, None, None, None, "°C", "device temperature (head)")
    GVS = OSTECHCommandInfo("GVS", int, None, None, None, "", "software version")
    GVN = OSTECHCommandInfo("GVN", int, None, None, None, "", "serial number")
    GS = OSTECHCommandInfo("GS", int, None, None, None, "", "get status")
    GM = OSTECHCommandInfo("GM", int, None, None, None, "", "get mode")
    GMC = OSTECHCommandInfo("GMC", int, None, None, None, "", "clear mode bits")
    GMS = OSTECHCommandInfo("GMS", int, None, None, None, "", "set mode bits")
    GMT = OSTECHCommandInfo("GMT", int, None, None, None, "", "toggle mode bits")

    def for_sensor(self, number: int) -> OSTECHCommandInfo:
        if not 1 <= number <= 9 or not self.value.command.startswith("x"):
            raise ValueError("Nur xT-Befehle können für einen Sensor nummeriert werden.")
        return OSTECHCommandInfo(
            f"{number}{self.value.command[1:]}", self.value.data_type,
            self.value.minimum, self.value.maximum, self.value.default,
            self.value.unit, self.value.description,
        )

Test_Tag = "Komunkiations Test für SR830 und OSTECH"

TestingLog.Log("KOM_Test", "SR830", "T", "Proramm start", "Ask", Test_Tag)

try:
    SR830 = serial.Serial("COM3", 9600, timeout=2)
    time.sleep(0.5)
    TestingLog.Log("KOM_Test", "SR830", "T", "SR830 Kom Test Start", "Ask", Test_Tag)
    SR830.write(b"*IDN?\r")
    ValueIDN = SR830.read_until(b"\r")
    TestingLog.Log("KOM_Test", "SR830", "T", "SR830 Kom Test Start", str(ValueIDN), "Raw", Test_Tag)
    ValueIDN = ValueIDN.decode("ascii", errors="replace").strip()
    TestingLog.Log("KOM_Test", "SR830", "T", "SR830 Kom Test Start", ValueIDN, "Decoded", Test_Tag)
except serial.SerialException as error:
    SR830 = None
    print(f"SR830 auf COM3 nicht erreichbar: {error}")

#try:
 #   OSTECH = serial.Serial("COM4", 9600, timeout=2)
 #   time.sleep(0.5)
 #   TestingLog.Log("KOM_Test", "OSTECH", "T", "OSTECH Kom Test Start", "Ask", Test_Tag)
 #   OSTECH.write(b"GMS8\r")
  #  OSTECH.flush()
 #   ValueGVN = OSTECH.read_until(b"\r")
#    TestingLog.Log("KOM_Test", "OSTECH", "T", "OSTECH Kom Test Start", str(ValueGVN), "Raw", Test_Tag)
#    ValueGVN = ValueGVN.decode("ascii", errors="replace").strip()
#    TestingLog.Log("KOM_Test", "OSTECH", "T", "OSTECH Kom Test Start", ValueGVN, "Decoded", Test_Tag)
#except serial.SerialException as error:
 #   OSTECH = None
 #   print(f"OSTECH auf COM4 nicht erreichbar: {error}")
try:
    OSTECH = serial.Serial("COM4", 9600, timeout=1)
    time.sleep(0.5)
    TestingLog.Log("KOM_Test", "OSTECH", "T", "OSTECH auf COM4 erreichbar", "Ask", Test_Tag )

except serial.SerialException as error:
    OSTECH = None
    TestingLog.Log("KOM_Test", "OSTECH", "E", "OSTECH auf COM4 nicht erreichbar", f"Error: {error}", "Decoded", Test_Tag)

def LabOSTECH(Port, Command: str, Data_Type, Decoder=None):
    Port.reset_input_buffer()
    Sending_Command = Command + "\r"
    Port.write(Sending_Command.encode("ascii"))
    Port.flush()

    Echo = Port.read_until(b"\r")
    Expected_Echo = (Command.upper() + "\r").encode("ascii")
    if Echo != Expected_Echo:
        raise RuntimeError(f"Unexpected echo: expected {Expected_Echo!r}, received {Echo!r}")

    if Decoder is not None:
        if not isinstance(Data_Type, int):
            raise TypeError("Data_Type muss die Anzahl der Antwortbytes sein.")
        response = Port.read(Data_Type)
        if len(response) != Data_Type:
            raise RuntimeError(
                f"Expected {Data_Type} response bytes, but received {len(response)} bytes."
            )
        return Decoder(response)

    if Data_Type is bool:
        response = Port.read(1)
        if len(response) != 1:
            raise RuntimeError(f"Expected 1 response byte, but received {len(response)} bytes.")
        if response == b"\xAA":
            return True
        if response == b"\x55":
            return False
        raise RuntimeError(f"Invalid boolean response: {response!r}")

    if Data_Type is int:
        response = Port.read(3)
        Payload_Length = 2
    elif Data_Type is float:
        response = Port.read(5)
        Payload_Length = 4
    else:
        raise TypeError("Data_Type muss bool, int, float oder ein eigener Decoder sein.")

    if len(response) != Payload_Length + 1:
        raise RuntimeError(
            f"Expected {Payload_Length + 1} response bytes, but received {len(response)} bytes."
        )

    Expected_Checksum = (0x55 + sum(response[:Payload_Length])) % 256
    if response[Payload_Length] != Expected_Checksum:
        raise RuntimeError(
            f"Invalid checksum: expected {Expected_Checksum:02X}, "
            f"received {response[Payload_Length]:02X}"
        )

    if Data_Type is int:
        return struct.unpack(">H", response[:Payload_Length])[0]
    return struct.unpack(">f", response[:Payload_Length])[0]


def decode_ostech_status(Status_Word: int):
    Status_Bits = {
        "interlock_ok": 0x0001,
        "driver_supply_ok": 0x0004,
        "driver_temperature_ok": 0x0008,
        "ltu_not_ok": 0x0010,
        "ltl_not_ok": 0x0020,
        "ctu_not_ok": 0x0040,
        "ctl_not_ok": 0x0080,
        "lt_sensor_ok": 0x0400,
        "ct_sensor_ok": 0x0800,
        "ltm_not_ok": 0x2000,
        "lc_on": 0x4000,
        "lc_error": 0x8000,
    }
    return {
        "status_word": Status_Word,
        **{Name: bool(Status_Word & Mask) for Name, Mask in Status_Bits.items()},
    }


def LabOSTECHCommand(Port, Command: OSTECHCommand, Sensor_Number=1):
    if Command.value.command.startswith("x"):
        Info = Command.for_sensor(Sensor_Number)
    else:
        if Sensor_Number != 1:
            raise ValueError("Sensor_Number ist nur für xT-Befehle erlaubt.")
        Info = Command.value

    Result = LabOSTECH(Port, Info.command, Info.data_type)
    if Command is OSTECHCommand.GS:
        Result = decode_ostech_status(Result)
    return OSTECHResult(Result, Info)


def set_ostech_binary_mode(Port):
    LabOSTECH(Port, "GMS8", int)


# testing all relevant commands for OSTECH
TestingLog.Log("KOM_Test","OSTECH","T","Test all relevant commands for OSTECH","Ask",str(Test_Tag))
time.sleep(1)

TestingLog.Log("KOM_Test","OSTECH","T","Set binary mode","GMS8","Ask",str(Test_Tag))
set_ostech_binary_mode(OSTECH)

TestingLog.Log("KOM_Test","OSTECH","T","GVS","","Ask",str(Test_Tag))
Res = LabOSTECHCommand(OSTECH, OSTECHCommand.GVS)
TestingLog.Log("KOM_Test","OSTECH","T","GVS",str(Res),"software version",str(Test_Tag))

TestingLog.Log("KOM_Test","OSTECH","T","GVN","","Ask",str(Test_Tag))
Res = LabOSTECHCommand(OSTECH, OSTECHCommand.GVN)
TestingLog.Log("KOM_Test","OSTECH","T","GVN",str(Res),"serial number",str(Test_Tag))

TestingLog.Log("KOM_Test","OSTECH","T","GS","","Ask",str(Test_Tag))
Status = LabOSTECHCommand(OSTECH, OSTECHCommand.GS)
TestingLog.Log("KOM_Test","OSTECH","T","GS",str(Status),"get status",str(Test_Tag))

TestingLog.Log("KOM_Test","OSTECH","T","LTM","","Ask",str(Test_Tag))
Res = LabOSTECHCommand(OSTECH, OSTECHCommand.LTM)
TestingLog.Log("KOM_Test","OSTECH","T","LTM",str(Res),"laser temperature maximum",str(Test_Tag))

TestingLog.Log("KOM_Test","OSTECH","T","LCA","","Ask",str(Test_Tag))
Res = LabOSTECHCommand(OSTECH, OSTECHCommand.LCA)
TestingLog.Log("KOM_Test","OSTECH","T","LCA",str(Res),"actual current",str(Test_Tag))

TestingLog.Log("KOM_Test","OSTECH","T","LVA","","Ask",str(Test_Tag))
Res = LabOSTECHCommand(OSTECH, OSTECHCommand.LVA)
TestingLog.Log("KOM_Test","OSTECH","T","LVA",str(Res),"laser voltage actual",str(Test_Tag))

TestingLog.Log("KOM_Test","OSTECH","T","LTA","","Ask",str(Test_Tag))
Res = LabOSTECHCommand(OSTECH, OSTECHCommand.XTA)
TestingLog.Log("KOM_Test","OSTECH","T","LTA",str(Res),"temperature actual",str(Test_Tag))

TestingLog.Log("KOM_Test","OSTECH","T","GT","","Ask",str(Test_Tag))
Res = LabOSTECHCommand(OSTECH, OSTECHCommand.GT)
TestingLog.Log("KOM_Test","OSTECH","T","GT",str(Res),"device temperature (head)",str(Test_Tag))

TestingLog.Log("KOM_Test","OSTECH","T","LVC","","Ask",str(Test_Tag))
Res = LabOSTECHCommand(OSTECH, OSTECHCommand.LVC)
TestingLog.Log("KOM_Test","OSTECH","T","LVC",str(Res),"compliance voltage",str(Test_Tag))

TestingLog.Log("KOM_Test","OSTECH","T","xTC","","Ask",str(Test_Tag))
Res = LabOSTECHCommand(OSTECH, OSTECHCommand.XTC)
TestingLog.Log("KOM_Test","OSTECH","T","xTC",str(Res),"temperature controller stop/run ",str(Test_Tag))







def ask_SR830(Command: str):
    TestingLog.Log("KOM_Test","SR830","T",str(Command),"Ask",str(Test_Tag))
    SR830.write((str(Command) + "\r").encode("ascii"))
    SR830.flush()
    ValueSR830 = SR830.read_until(b"\r").decode("ascii", errors="replace").strip()
    TestingLog.Log("KOM_Test","SR830","T",str(Command),str(ValueSR830),"Decoded",str(Test_Tag))



def ask_OSTECH(Command: str):
    TestingLog.Log("KOM_Test","OSTECH","T",str(Command),"Ask",str(Test_Tag))
    OSTECH.write((str(Command) + "\r").encode("ascii"))
    OSTECH.flush()
    ValueOSTECH = OSTECH.read_until(b"\r").decode("ascii", errors="replace").strip()
    TestingLog.Log("KOM_Test","OSTECH","T",str(Command),str(ValueOSTECH),"Decoded",str(Test_Tag))




def Test_SR830():
    ask_SR830("*IDN?")
    ask_SR830("SRAT 0")
    ask_SR830("SRAT 0")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 1")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 2")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 3")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 4")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 5")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 6")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 7")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 8")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 9")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 10")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 11")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 12")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 13")
    ask_SR830("SRAT?")
    ask_SR830("SRAT 14")

    ask_SR830("SEND?")
    ask_SR830("SEND 1")
    ask_SR830("SEND?")
    ask_SR830("SEND 2")
    ask_SR830("SEND?")

    ask_SR830("TRIG")

    ask_SR830("TSTR ?")
    ask_SR830("TSTR 1")
    ask_SR830("TSTR ?")
    ask_SR830("TSTR 2")
    ask_SR830("TSTR ?")

    ask_SR830("STRT")

    ask_SR830("PAUS")

    ask_SR830("REST")

    ask_SR830("OAUX? 1")
    ask_SR830("OAUX? 2")
    ask_SR830("OAUX? 3")
    ask_SR830("OAUX? 4")

    ask_SR830("OUTP? 1")
    ask_SR830("OUTP? 2")
    ask_SR830("OUTP? 3")
    ask_SR830("OUTP? 4")

    ask_SR830("SNAP? 1,2")
    ask_SR830("SNAP? 3,2")
    ask_SR830("SNAP? 5,6")
    ask_SR830("SNAP? 7,8")
    ask_SR830("SNAP? 9,10")
    ask_SR830("SNAP? 10,11")

    ask_SR830("SNAP? 1,2,3,4")
    ask_SR830("SNAP? 5,6,7,8")
    ask_SR830("SNAP? 9,10,11")

    ask_SR830("SNAP? 1,2,3,4,10,11")
    ask_SR830("SNAP? 5,6,7,8,9")

    ask_SR830("SPTS?")

    ask_SR830("TRCA? 1,2,1")
    ask_SR830("TRCA? 2,2,1")

    ask_SR830("TRCB? 1,2,1")
    ask_SR830("TRCB? 2,2,1")

    ask_SR830("TRCL? 2,2,1")
    ask_SR830("TRCL? 2,2,1")

    ask_SR830("FAST? 1")
    ask_SR830("FAST?")

    ask_SR830("STRD")

    ask_SR830("FAST? 2")
    ask_SR830("FAST?")

    ask_SR830("STRD")

    ask_SR830("FAST? 3")
    ask_SR830("FAST?")

    ask_SR830("STRD")

    ask_SR830("FAST 1")
    ask_SR830("FAST?")

    ask_SR830("STRD")

    ask_SR830("FAST 2")
    ask_SR830("FAST?")

    ask_SR830("STRD")

    ask_SR830("FAST 3")
    ask_SR830("FAST?")

    ask_SR830("STRD")

    ask_SR830("*RST")

    ask_SR830("*IDN?")

    ask_SR830("LOCL? 1")

    ask_SR830("LOCL?")

    ask_SR830("*RST")

    ask_SR830("LOCL 1")

    ask_SR830("LOCL?")

    ask_SR830("*RST")

    ask_SR830("LOCL? 2")

    ask_SR830("LOCL?")

    ask_SR830("*RST")

    ask_SR830("OVRM? 0")

    ask_SR830("OVRM?")

    ask_SR830("OVRM? 1")

    ask_SR830("OVRM?")

    ask_SR830("*RST")

    ask_SR830("TRIG")

    ask_SR830("*ESE?")
    ask_SR830("*ESR?")
    ask_SR830("*SRE?")
    ask_SR830("*STB?")
    ask_SR830("*PSC?")
    ask_SR830("ERRE?")
    ask_SR830("ERRS?")
    ask_SR830("LIAE?")
    ask_SR830("LIAS?")

    ask_SR830("*STB?")

    ask_SR830("*CLS")




    print("Kom Test for ST830 Done")
    SR830.close()


def Test_OSTech():

    ask_OSTECH("LCA")
    ask_OSTECH("LVA")
    ask_OSTECH("LTA")
    ask_OSTECH("GT")


    ask_OSTECH("GE")

    ask_OSTECH("GF")

    ask_OSTECH("GFD")

    ask_OSTECH("GX")

    ask_OSTECH("GT")

    ask_OSTECH("GVS")

    ask_OSTECH("GVN")

    ask_OSTECH("GS")

    ask_OSTECH("GM")

    ask_OSTECH("GSP")

    ask_OSTECH("GSR")




    print("Kom Test for ST830 Done")
    OSTECH.close()

# Test_SR830()
#Test_OSTech()


import serial
import time
import TestingLog

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

try:
    OSTECH = serial.Serial("COM4", 9600, timeout=2)
    time.sleep(0.5)
    TestingLog.Log("KOM_Test", "OSTECH", "T", "OSTECH Kom Test Start", "Ask", Test_Tag)
    OSTECH.write(b"GMS8\r")
    ValueGVN = OSTECH.read_until(b"\r")
    TestingLog.Log("KOM_Test", "OSTECH", "T", "OSTECH Kom Test Start", str(ValueGVN), "Raw", Test_Tag)
    ValueGVN = ValueGVN.decode("ascii", errors="replace").strip()
    TestingLog.Log("KOM_Test", "OSTECH", "T", "OSTECH Kom Test Start", ValueGVN, "Decoded", Test_Tag)
except serial.SerialException as error:
    OSTECH = None
    print(f"OSTECH auf COM4 nicht erreichbar: {error}")


def ask_SR830(Command: str):
    time.sleep (1)
    TestingLog.Log("KOM_Test","SR830","T",str(Command),"Ask",str(Test_Tag))
    SR830.write(b"" + Command +"\r")
    ValueSR830 = SR830.read_until(b"\r")
    time.sleep (0.5)
    TestingLog.Log("KOM_Test","SR830","T",str(Command),str(ValueSR830),"Raw",str(Test_Tag))
    ValueSR830 = ValueSR830.decode("ascii", errors="replace").strip()
    time.sleep (0.5)
    TestingLog.Log("KOM_Test","SR830","T",str(Command),str(ValueSR830),"Decoded",str(Test_Tag))

def ask_OSTECH(Command: str):
    time.sleep (1)
    TestingLog.Log("KOM_Test","OSTECH","T",str(Command),"Ask",str(Test_Tag))
    OSTECH.write(b"" + Command + b"\r")
    ValueOSTECH = OSTECH.read_until(b"\r")
    time.sleep (0.5)
    TestingLog.Log("KOM_Test","OSTECH","T",str(Command),str(ValueOSTECH),"Raw",str(Test_Tag))
    ValueOSTECH = ValueOSTECH.decode("ascii", errors="replace").strip()
    time.sleep (0.5)
    TestingLog.Log("KOM_Test","OSTECH","T",str(Command),str(ValueOSTECH),"Decoded",str(Test_Tag))

def Test_SR830():

    ask_SR830("SRAT?")
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

    #ask_SR830("REST")

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



    print("Kom Test for ST830 Done")
    OSTECH.close()
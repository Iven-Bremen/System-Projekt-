import serial
import time

SR830 = serial.Serial("COM3", 9600, timeout= 2)
time.sleep (0.5)
print("Write IDN")
SR830.write(b"*IDN?\r")
ValueIDN = SR830.read_until(b"\r")
print("Raw: " ,repr(ValueIDN))
ValueIDN = ValueIDN.decode("ascii", errors="replace").strip()
print("Decoded: ", ValueIDN)

ask_SR830("OUTP? 1")
ask_SR830("OUTP? 2")
ask_SR830("OUTP? 3")
ask_SR830("OUTP? 4")
ask_SR830("OAUX? 1")
ask_SR830("OAUX? 2")
ask_SR830("OAUX? 3")
ask_SR830("OAUX? 4")

ask_SR830("SNAP? 1")
ask_SR830("SNAP? 2")


print("Kom Test for ST830 Done")
SR830.close()



OSTECH = serial.Serial("COM4", 9600, timeout= 2)
time.sleep (0.5)
print("Write GVN")
OSTECH.write(b"GMS8\r")
ValueGVN = OSTECH.read_until(b"\r")
print("Raw: " ,repr(ValueGVN))
ValueGVN = ValueGVN.decode("ascii", errors="replace").strip()
print("Decoded: ", ValueGVN)







OSTECH.close()


def ask_SR830(Command: str):
    print("Write "+str(Command))
    SR830.write(b"" + Command +"\r")
    ValueSR830 = SR830.read_until(b"\r")
    print("Raw: " ,repr(ValueSR830))
    ValueSR830 = ValueSR830.decode("ascii", errors="replace").strip()
    print("Decoded: ", ValueSR830)

def ask_OSTECH(Command: str):
    print("Write "+str(Command))
    OSTECH.write(b"" + Command + b"\r")
    ValueOSTECH = OSTECH.read_until(b"\r")
    print("Raw: " ,repr(ValueOSTECH))
    ValueOSTECH = ValueOSTECH.decode("ascii", errors="replace").strip()
    print("Decoded: ", ValueOSTECH)
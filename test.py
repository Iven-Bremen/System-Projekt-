import serial
import time

SR830 = serial.Serial("COM4", 9600, timeout= 2)
time.sleep (0.5)
print("Write IDN")
SR830.write(b"*IDN?\r")
ValueIDN = SR830.read_until(b"\r")
print("Raw: " ,repr(ValueIDN))
ValueIDN = ValueIDN.decode("ascii", errors="replace").strip()
print("Decoded: ", ValueIDN)
SR830.close()

GVN


OSTECH = serial.Serial("COM5", 9600, timeout= 2)
time.sleep (0.5)
print("Write GVN")
OSTECH.write(b"GVN")
ValueGVN = OSTECH.read_until(b"\r")
print("Raw: " ,repr(ValueGVN))
ValueGVN = ValueGVN.decode("ascii", errors="replace").strip()
print("Decoded: ", ValueGVN)
OSTECH.close()



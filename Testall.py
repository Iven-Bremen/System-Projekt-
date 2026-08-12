import serial
import time

ser = serial.Serial("COM4", 9600, timeout = 2.0)
time.sleep (0.5)
ser.write(b"*IDN?\r")
reply = ser.read_until(b"\r")
print("Raw: " ,repr(reply))
print("Decoded: ", reply.decode("ascii", errors="replace").strip())
time.sleep (1)

while True:
    ser.write(b"OUTP? 1\r")
    OUTP1 = ser.read_until(b"\r")
    print("RawP1: " ,repr(OUTP1))
    print("DecodedP1: ", OUTP1.decode("ascii", errors="replace").strip())
    time.sleep (0.1)

    ser.write(b"OUTP? 2\r")
    OUTP2 = ser.read_until(b"\r")
    print("RawP2: " ,repr(OUTP2))
    print("DecodedP2: ", OUTP2.decode("ascii", errors="replace").strip())
    time.sleep (0.1)

    ser.write(b"OUTP? 3\r")
    OUTP3 = ser.read_until(b"\r")
    print("RawP3: " ,repr(OUTP3))
    print("DecodedP3: ", OUTP3.decode("ascii", errors="replace").strip())
    time.sleep (0.1)

    ser.write(b"OUTP? 4\r")
    OUTP4 = ser.read_until(b"\r")
    print("RawP4: " ,repr(OUTP4))
    print("DecodedP4: ", OUTP4.decode("ascii", errors="replace").strip())
    time.sleep (0.1)

ser.close()



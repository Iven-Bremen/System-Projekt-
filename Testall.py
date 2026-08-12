import serial
import time


ser = serial.Serial("COM4", 9600, timeout = 2.0)
time.sleep (0.5)
ser.write(b"*IDN?\r")
reply = ser.read_until(b"\r")
print("Raw: " ,repr(reply))
print("Decoded: ", reply.decode("ascii", errors="replace").strip())
time.sleep (1)

ser.write(b"OUTP? 3\r")
reply = ser.read_until(b"\r")
print("Raw: " ,repr(reply))
print("Decoded: ", reply.decode("ascii", errors="replace").strip())
time.sleep (1)


ser.close()

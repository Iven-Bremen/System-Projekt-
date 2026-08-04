import serial
import time

ser = serial.Serial("COM3", 9600, timeout= 2)
time.sleep (0.5)
ser.write(b"*IDN?\r")
reply = ser.read_until(b"\r")
print("Raw: " ,repr(reply))
print("Decoded: ", reply.decode(errors="ignore").strip())
ser.close()

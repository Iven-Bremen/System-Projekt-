import serial
import time

 def decode64(
 encoding: str = "utf-8",
 errors: str = "strict"
)

ser = serial.Serial("COM4", 9600, timeout = 2.0)
time.sleep (0.5)
ser.write(b"*IDN?\r")
reply = ser.read_until(b"\r")
print("Raw: " ,repr(reply))
print("Decoded: ", reply.decode(errors="ignore").strip())
time.sleep (1)

ser.write(b"OUTP? 3\r")
reply = ser.read_until(b"\r")
print("Raw: " ,repr(reply))
print("Decoded: ", reply.decode(errors="ignore").strip())
time.sleep (1)

ser.write(b"FREQ\r")
reply = ser.read_until(b"\r")
print("Raw: " ,repr(reply))
print("Decoded: ", reply.decode(errors="ignore").strip())
time.sleep (1)

ser.write(b"SENS\r")
reply = ser.read_until(b"\r")
print("Raw: " ,repr(reply))
print("Decoded: ", reply.decode(errors="ignore").strip())
time.sleep (1)

ser.close()

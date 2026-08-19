import serial
import time
import Commands
import Log

Log.LogMassage("Check Ports","Info","Test","Check","Check")
SR830 = serial.Serial("COM4", 9600, timeout = 2.0)
time.sleep (0.5)
Log.LogMassage("COM4","Info","Test","OpenPort","9600")

SR830.write(b"*IDN?\r")
reply = SR830.read_until(b"\r")
print("Raw: " ,repr(reply))
print("Decoded: ", reply.decode("ascii", errors="replace").strip())
time.sleep (1)


Commands.getValue(SR830,"IDN",0,0,0)



Commands.getValue(SR830,"OUTP1",0,0,0)



Commands.getValue(SR830,"OUTP2",0,0,0)



Commands.getValue(SR830,"OUTP3",0,0,0)



Commands.getValue(SR830,"OUTP4",0,0,0)



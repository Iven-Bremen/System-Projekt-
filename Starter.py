import Log
import serial
import time
import GUI

def init_hardware():
    """Prüft und initialisiert alle seriellen Schnittstellen als allererstes."""
    Log.start_terminal_logging()
    Log.LogMassage("SYSTEM", "START", "Programm gestartet", "Version 1.0")
   

    # --- SR830 Ansteuerung ---
    Log.LogMassage("Check Ports vor SR830", "Info", "Test", "Check", "SR830")
    try:
        #ConficPortsSR830("COM5",9600, 2.0) 
        SR830 = serial.Serial("COM3", 9600, timeout=2.0)
        time.sleep(0.5)
        Log.LogMassage("COM3", "Info", "Test", "OpenPort", "9600")
    except serial.SerialException:
        SR830 = None
        Log.LogMassage("COM3", "Warning", "Port konnte nicht geöffnet werden (Hardware fehlt)", "Fail", "COM3")

    # --- OSTech Laser Ansteuerung ---
    Log.LogMassage("Check Ports vor OSTech", "Info", "Test", "Check", "OSTech")
    try:
        #ConficPortsOSTech("COM5",9600, 2.0) 
        global OSTech
        OSTech = serial.Serial("COM5", 9600, timeout=2.0)
        time.sleep(0.5)  
    except serial.SerialException:
        OSTech = None
        Log.LogMassage("COM4", "Warning", "Port konnte nicht geöffnet werden (Hardware fehlt)", "Fail", "COM4")


def StartGui():
    """Startet erst die GUI, wenn die Hardware-Prüfung komplett abgeschlossen ist."""
    Log.LogMassage("Gui", "Info", "Starting Gui", " ", " ")

    GUI.update_ch1_display()
    GUI.update_ch2_display()
    GUI.update_laser_display_mode()
    GUI.root.after(2000, GUI.live_update_loop)

    GUI.root.mainloop()


def ConficPortsSR830(NameOfPort : str, BaudRate : int, Timeout : float):
    global SR830
    SR830 = serial.Serial(NameOfPort, BaudRate, timeout = Timeout)
    time.sleep (0.5)
    Log.LogMassage(NameOfPort,"Info","Test","OpenPort",str(BaudRate))
    ValidatedPort(NameOfPort,BaudRate,Timeout)

def ConficPortsOSTech(NameOfPort : str, BaudRate : int, Timeout : float):
    global OSTech
    OSTech = serial.Serial(NameOfPort, BaudRate, timeout = Timeout)
    time.sleep (0.5)
    Log.LogMassage(NameOfPort,"Info","Test","OpenPort",str(BaudRate))
    ValidatedPort(NameOfPort,BaudRate,Timeout)

def ValidatedPort(NameOfPort : str, BaudRate : int, Timeout : float):
    if(NameOfPort == GUI.getPortOf(OSTech)):
        OSTech = serial.Serial(NameOfPort, BaudRate, timeout = Timeout)
        time.sleep (1)
        Log.LogMassage("StartKom", "OSTECH", "Try to open Port with BaudRate of "+ str(BaudRate), "Check OpenPort", "validation needed" )
        OSTech.write(b"GVN")
        OSTechID = OSTech.read_until(b"\r")
        OSTechID = OSTechID.decode("ascii", errors="replace").strip()
        if(OSTechID != "264981"):
            Log.LogMassage("Startkom","OSTech","OSTech ID is False", "validation failed", "Port will be closed")
            OSTech.close()
            return False
        Log.LogMassage("Startkom","OSTech","OSTech ID is Right", "validation passed", "Port will be open at OSTech with Port" +str(NameOfPort))
        return True
    if(NameOfPort == GUI.getPortOf(SR830)):
        SR830 = serial.Serial(NameOfPort, BaudRate, timeout = Timeout)
        time.sleep (1)
        Log.LogMassage("StartKom", "SR830", "Try to open Port with BaudRate of "+ str(BaudRate), "Check OpenPort", "validation needed" )
        SR830.write(b"*IDN?\r")
        SR830ID = SR830.read_until(b"\r")
        SR830ID = SR830ID.decode("ascii", errors="replace").strip()
        if(SR830ID != "264981"):
            Log.LogMassage("Startkom","SR830","SR830 ID is False", "validation failed", "Port will be closed")
            OSTech.close()
            return False
        Log.LogMassage("Startkom","SR830","SR830 ID is Right", "validation passed", "Port will be open at OSTech with Port" +str(NameOfPort))
        return True


if __name__ == "__main__":
    init_hardware()
    StartGui()
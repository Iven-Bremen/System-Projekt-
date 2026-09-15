import Log
import serial
import time
from Komunikation import (
    ask_OSTECH,
    ask_SR830,
    close_devices,
    open_devices,
    send_OSTECH,
    send_SR830,
)
from State import COMScanner, scan_com_ports


SR830 = None
OSTech = None


def get_available_com_ports():
    """Returns all COM ports currently available to the Starter/GUI."""
    return scan_com_ports()

def init_hardware():
    """Prüft und initialisiert alle seriellen Schnittstellen als allererstes."""
    global SR830, OSTech
    Log.start_terminal_logging()
    Log.LogMassage("SYSTEM", "START", "Programm gestartet", "Version 1.0")
    SR830, OSTech = open_devices()
    Log.LogMassage("COM3", "Info" if SR830 is not None else "Warning",
                   "OpenPort" if SR830 is not None else "Port nicht verbunden",
                   "OK" if SR830 is not None else "Fail", "SR830")
    Log.LogMassage("COM4", "Info" if OSTech is not None else "Warning",
                   "OpenPort" if OSTech is not None else "Port nicht verbunden",
                   "OK" if OSTech is not None else "Fail", "OSTech")


def StartGui():
    """Startet erst die GUI, wenn die Hardware-Prüfung komplett abgeschlossen ist."""
    import GUI

    Log.LogMassage("Gui", "Info", "Starting Gui", " ", " ")

    GUI.update_ch1_display()
    GUI.update_ch2_display()
    GUI.update_laser_display_mode()
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
    import GUI

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

    '''-Abgleich gleich zu true checkport apply +check
    -Apply mit lockin +check
    -laser menu deaktiv
    -apply
    -pop up für import data#
    -ordner struktur und speichern
    -alte datein öffenen
    -log ordner
    -scrollen bei logs und export
    -port is fitting
    -coms von 0-100 als textfeld
    -overview
    .guide'''
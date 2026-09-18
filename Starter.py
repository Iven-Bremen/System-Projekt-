"""Application entry point and startup/shutdown orchestration.

``Starter`` deliberately stays thin. It performs the initial COM-port scan,
starts the logging session, owns the idle calculation thread, opens the GUI
in the Tkinter main thread, and closes serial resources at the end. The actual
protocol implementation belongs to
``Komunikation.py``; shared measurements belong to ``State.py``; and worker
thread coordination belongs to ``Threads.py``.

The GUI is intentionally started in the main thread because both Tkinter and
Matplotlib create native GUI resources that are not safe in a background
thread. Device communication can run independently once its communication
entry point is used, but widget creation and ``mainloop`` remain here.
"""

import Log
import serial
import threading
import time
import State
from Komunikation import (
    ask_OSTECH,
    ask_SR830,
    close_devices,
    open_devices,
    send_OSTECH,
    send_SR830,
)
from State import COMScanner, scan_com_ports
from Threads import CalculationThread


SR830 = None
OSTech = None
calculation_thread = None


def _calculation_runner(stop_requested, publish):
    """Keep the calculation worker ready without performing calculations yet.

    The worker is intentionally started during application startup so the
    calculation lifecycle already exists. The actual formulas can be added
    here later without moving thread ownership into the communication layer.
    """
    State.update_values({"CALCULATION_STATUS": "READY"})
    publish({"step": "calculation ready", "value": "No calculations configured"})
    stop_requested.wait()
    State.update_values({"CALCULATION_STATUS": "STOPPED"})


def start_calculation_thread():
    """Create and start the idle calculation worker from the application starter."""
    global calculation_thread
    if calculation_thread is None:
        calculation_thread = CalculationThread(
            _calculation_runner,
            lambda source, value: Log.Log(
                "CALCULATION", source, "I", str(value.get("step", "status")),
                str(value.get("value", "")), "STARTER",
            ),
        )
        calculation_thread.start()
    return calculation_thread


def stop_calculation_thread():
    """Stop and release the calculation worker during application shutdown."""
    global calculation_thread
    if calculation_thread is not None:
        calculation_thread.stop()
        calculation_thread = None


def get_available_com_ports():
    """Return all currently visible COM ports and print a short status.

    The GUI uses this function for its Refresh action. Port discovery is
    delegated to ``State.scan_com_ports`` so the starter and GUI use exactly
    the same representation. No port is opened by this function.
    """
    ports = scan_com_ports()
    if not ports:
        print("No COM ports available")
    else:
        print(ports)
    return ports

def init_hardware():
    """Start logging and perform the initial non-invasive port scan.

    Device opening is intentionally deferred until the user presses Connect
    in the GUI. This allows the user to edit the dynamically discovered port
    names first and prevents an incorrect default port from being opened.
    """
    Log.start_terminal_logging()
    Log.LogMassage("SYSTEM", "START", "Programm gestartet", "Version 1.0")
    ports = get_available_com_ports()
    State.update_values({"AVAILABLE_COM_PORTS": ports})
    Log.LogMassage("SYSTEM", "Info", "COM-Port Scan", str(ports), "Startup")


def _run_gui():
    """Import, initialize, and run the GUI in the process main thread.

    Importing ``GUI`` constructs the Tkinter widgets and the Matplotlib figure,
    so the import itself must happen in this thread as well. A failure during
    construction or ``mainloop`` is converted into a structured ``Error`` log
    instead of leaking an unhandled traceback to the terminal.
    """
    try:
        import GUI

        Log.LogMassage("Gui", "Info", "Starting Gui", " ", " ")

        GUI.update_ch1_display()
        GUI.update_ch2_display()
        GUI.update_laser_display_mode()
        # Start the idle calculation worker after Tk has created the window.
        # This keeps the first visible GUI frame independent of worker setup.
        GUI.root.after(0, start_calculation_thread)
        GUI.root.mainloop()
    except Exception as error:
        Log.LogMassage(
            "SYSTEM", "Error", "GUI konnte nicht gestartet werden",
            f"{type(error).__name__}: {error}", "GUI",
        )


def StartGui():
    """Run the GUI synchronously until its window is closed."""
    _run_gui()


def ConficPortsSR830(NameOfPort : str, BaudRate : int, Timeout : float):
    """Open and validate a manually selected SR830 serial configuration."""
    global SR830
    SR830 = serial.Serial(NameOfPort, BaudRate, timeout = Timeout)
    time.sleep (0.5)
    Log.LogMassage(NameOfPort,"Info","Test","OpenPort",str(BaudRate))
    ValidatedPort(NameOfPort,BaudRate,Timeout)

def ConficPortsOSTech(NameOfPort : str, BaudRate : int, Timeout : float):
    """Open and validate a manually selected OSTECH serial configuration."""
    global OSTech
    OSTech = serial.Serial(NameOfPort, BaudRate, timeout = Timeout)
    time.sleep (0.5)
    Log.LogMassage(NameOfPort,"Info","Test","OpenPort",str(BaudRate))
    ValidatedPort(NameOfPort,BaudRate,Timeout)


def ValidatedPort(NameOfPort : str, BaudRate : int, Timeout : float, SR830=None):
    """Perform the legacy identification handshake for one selected port.

    This helper is retained for older GUI workflows. New startup code should
    prefer ``Komunikation.open_devices`` because it owns the complete protocol
    transition, locking, and typed response handling.
    """
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
    try:
        init_hardware()
        start_calculation_thread()
        StartGui()
    except KeyboardInterrupt:
        Log.LogMassage("SYSTEM", "Info", "Programm beendet", "Benutzerabbruch", " ")
    except Exception as error:
        Log.LogMassage(
            "SYSTEM", "Error", "Unerwarteter Programmfehler",
            f"{type(error).__name__}: {error}", "Starter",
        )
    finally:
        stop_calculation_thread()
        close_devices()

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
import time
import serial

try:
    from serial.tools import list_ports
except Exception:
    serial = None
    list_ports = None


def list_serial_ports():
    """Gibt alle verfügbaren seriellen Ports zurück."""
    if list_ports is None:
        return []
    return [port.device for port in list_ports.comports()]


def print_serial_ports():
    ports = list_serial_ports()
    if not ports:
        print("Keine seriellen Ports gefunden.")
        return

    print("Gefundene serielle Ports:")
    for port in ports:
        print(f"- {port}")


if __name__ == "__main__":
    if serial is None or list_ports is None:
        print("pyserial ist nicht installiert. Installiere es mit: pip install pyserial")
    else:
        print_serial_ports()



def ConnectSerial(port, baudrate=9600, timeout=2.0):
    """Stellt eine Verbindung zu einem seriellen Port her."""
    try:
        Port = serial.Serial(port, baudrate, timeout=timeout)
        time.sleep(0.25)  # Kurze Pause, um die Verbindung zu stabilisieren
        print ("Try communication with port: ", port)
        Port.write(b"*IDN?\r")
        answer = Port.read_until(b"\r")
        print("ID", answer.decode("ascii", errors="replace").strip())

        return Port
    except serial.SerialException as e:
        print(f"Fehler beim Verbinden mit {port}: {e}")
        return None

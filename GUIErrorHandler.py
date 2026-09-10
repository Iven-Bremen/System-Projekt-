import traceback
import tkinter as tk
from tkinter import messagebox


class GUIErrorHandler:
    """Zentrale Klasse zur Abwicklung von Fehlern und Edge-Cases in der GUI."""

    @staticmethod
    def handle_exception(exception: Exception, context: str = "Operation") -> None:
        """
        Analysiert Ausnahmen und zeigt spezifische, benutzerfreundliche Fehlermeldungen.
        """
        err_msg = str(exception)

        # Edge Case 1: Eingabefehler (z.B. Buchstaben statt Zahlen bei Frequenz/Spannung)
        if isinstance(exception, ValueError):
            messagebox.showerror(
                "Eingabefehler",
                f"Fehler in '{context}':\nBitte überprüfen Sie Ihre Eingaben auf ungültige Zeichen oder Formate.\n\nDetails: {err_msg}"
            )

        # Edge Case 2: Port- / Serien-Schnittstellen-Fehler (COM-Port besetzt oder nicht vorhanden)
        elif "serial" in type(exception).__name__.lower() or "port" in err_msg.lower():
            messagebox.showerror(
                "Schnittstellenfehler (COM)",
                f"Fehler bei Schnittstelle in '{context}':\nDer ausgewählte COM-Port ist ungültig, getrennt oder wird von einem anderen Programm blockiert."
            )

        # Edge Case 3: VISA / Hardware Timeout oder Verbindungsabbruch
        elif "visa" in type(exception).__module__.lower() or "timeout" in err_msg.lower():
            messagebox.showwarning(
                "Hardware Timeout",
                f"Hardware-Antwort fehlt ({context}):\nDas Gerät hat nicht rechtzeitig geantwortet. Überprüfen Sie die Kabelverbindung und das Gerät."
            )

        # Edge Case 4: Datei- und Pfadfehler (z. B. Datei gelöscht/gesperrt)
        elif isinstance(exception, (FileNotFoundError, PermissionError)):
            messagebox.showerror(
                "Datei- / Zugriffsfehler",
                f"Fehler beim Dateizugriff ({context}):\nDie Datei konnte nicht geöffnet oder geschrieben werden."
            )

        # Edge Case 5: Unbekannter / Unerwarteter Systemfehler
        else:
            messagebox.showerror(
                "Unerwarteter Fehler",
                f"Ein unerwarteter Fehler ist aufgetreten ({context}):\n{type(exception).__name__}: {err_msg}"
            )
            print(f"[ERROR LOG - {context}]:", traceback.format_exc())

    @staticmethod
    def safely_execute(func, context: str = "Aktion", *args, **kwargs):
        """
        Hilfsmethode, um eine Funktion sicher auszuführen, ohne die GUI abstürzen zu lassen.
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            GUIErrorHandler.handle_exception(e, context=context)
            return None
import os
import sys
import json
import random
import time
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from tkinter.constants import DISABLED
import datetime
import shutil
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Lokale Projektmodule
import Log
import Komunikation
import Send
import Starter
import State
import SimGuiUpdatet
from State import scan_com_ports
import GUIErrorHandler


# Imports: für Calculations im Reiter "Experiment"
import SWP_Calculation_PhaseVsFrequenz_v8 as PhasFreq_v8
import SWP_Streuung_Messunsicherheit_TypA_v6 as SWP_SM_v6



# Externe Bibliotheken mit Fallback-Mechanismus
try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

try:
    import pyvisa
except ImportError:
    pyvisa = None

try:
    import serial.tools.list_ports
except ImportError:
    serial = None

# ==========================================
# ORDNER INITIALISIERUNG
# ==========================================
# Erstellt Verzeichnisse für Log-Dateien und generierte Plots, falls nicht vorhanden.
LOG_DIR = os.path.join(os.getcwd(), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

PLOT_DIR = os.path.join(os.getcwd(), "plots")
if not os.path.exists(PLOT_DIR):
    os.makedirs(PLOT_DIR)

# ==========================================
# KONFIGURATION
# ==========================================

def read_numeric_entry(entry_widget, field_name, minimum=None, maximum=None):
    """Liest einen numerischen Wert aus einem Tkinter-Entry-Widget.

    Entfernt Einheiten (z.B. V, mA, Hz, °C) und prüft Min/Max-Grenzen.
    """
    raw_value = entry_widget.get().strip()
    normalized_value = raw_value.replace(",", ".")
    for unit in ("°C", "degC", "mA", "V", "A", "ms", "Hz"):
        if normalized_value.lower().endswith(unit.lower()):
            normalized_value = normalized_value[:-len(unit)].strip()
            break
    try:
        value = float(normalized_value)
    except (TypeError, ValueError):
        message = f"Ungültige Eingabe für {field_name}: {raw_value!r}"
        Log.Log("Gui", field_name, "Error", "Input Error", message, field_name)
        messagebox.showerror("Input Error", message)
        entry_widget.focus_set()
        return None
    if ((minimum is not None and value < minimum)
            or (maximum is not None and value > maximum)):
        message = f"Wert für {field_name} muss zwischen {minimum} und {maximum} liegen."
        Log.Log("Gui", field_name, "Error", "Input Error", message, field_name)
        messagebox.showerror("Input Error", message)
        entry_widget.focus_set()
        return None
    return value


def read_integer_entry(entry_widget, field_name, minimum=None, maximum=None):
    """Liest eine Ganzzahl (Integer) aus einem Entry-Widget und validiert diese."""
    value = read_numeric_entry(entry_widget, field_name, minimum, maximum)
    if value is None or value.is_integer():
        return None if value is None else int(value)
    message = f"Für {field_name} wird eine ganze Zahl erwartet."
    Log.Log("Gui", field_name, "Error", "Input Error", message, field_name)
    messagebox.showerror("Input Error", message)
    entry_widget.focus_set()
    return None


# ==========================================
# AUTOMATISIERTES ÜBERSETZUNGS-SYSTEM
# ==========================================
# Pfad zum lokalen Übersetzungs-Cache
CACHE_FILE = "translation_cache.json"
# Globale Variable für die aktuelle Sprache (Standard: Englisch "en")
current_lang = "en"


def load_cache():
    """Lädt den Übersetzungscache aus einer lokalen JSON-Datei."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Fehler beim Laden des Caches: {e}")
    return {"de": {}, "es": {}, "fr": {}}


def save_cache():
    """Speichert den Übersetzungscache lokal."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(TRANSLATION_CACHE, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Fehler beim Speichern des Caches: {e}")


# Globaler Übersetzungs-Cache
TRANSLATION_CACHE = load_cache()

# Manuelle Übersetzungs-Korrekturen
MANUAL_OVERRIDES = {
    "de": {
        "Sine Out": "Sine-Out Signal",
        "Data Cleansing & Fit": "Datenbereinigung & Fit",
        "Phase vs. Frequency Analysis": "Phase-vs-Frequenz Analyse",
        "Logs": "Protokolle / Logs",
        "Overview": "Übersicht",
        "Lock-In Amplifier": "Lock-In Verstärker",
        "Laser / TEC Controller": "Laser / TEC Regler",
        "Experiment": "Experiment",
        "Help": "Hilfe",
        "Guide": "Handbuch / Anleitung",
        "Settings": "Einstellungen"
    }
}

# Liste aller registrierten UI-Elemente für den Sprachwechsel
registered_widgets = []


def auto_tr(english_text):
    """Übersetzt englischen Text in die aktuell eingestellte Sprache."""
    if current_lang == "en":
        return english_text

    if current_lang in MANUAL_OVERRIDES and english_text in MANUAL_OVERRIDES[current_lang]:
        return MANUAL_OVERRIDES[current_lang][english_text]

    if current_lang not in TRANSLATION_CACHE:
        TRANSLATION_CACHE[current_lang] = {}

    if english_text in TRANSLATION_CACHE[current_lang]:
        return TRANSLATION_CACHE[current_lang][english_text]

    if GoogleTranslator:
        try:
            translated = GoogleTranslator(source='en', target=current_lang).translate(english_text)
            TRANSLATION_CACHE[current_lang][english_text] = translated
            save_cache()
            return translated
        except Exception:
            return english_text
    return english_text


def reg_ui(widget, english_text, prop="text"):
    """Registriert ein UI-Widget zur dynamischen Übersetzung."""
    registered_widgets.append((widget, prop, english_text))
    update_single_widget(widget, prop, english_text)


def update_single_widget(widget, prop, english_text):
    """Aktualisiert die Beschriftung eines einzelnen registrierten Widgets."""
    translated_val = auto_tr(english_text)
    try:
        if prop == "text":
            widget.config(text=translated_val)
        elif prop == "tab_text":
            nb, tab = widget
            nb.tab(tab, text=f" {translated_val} ")
    except Exception:
        pass


def change_language(lang_code):
    """Wechselt die globale Sprache der Benutzeroberfläche."""
    global current_lang
    current_lang = lang_code
    for widget, prop, english_text in registered_widgets:
        update_single_widget(widget, prop, english_text)


# ==========================================
# HARDWARE VARIABLEN & STEUERUNG
# ==========================================
# COM-Ports für Hardware
LOCK_IN_AMPLIFIER_PORT = Komunikation.DEFAULT_SR830_PORT
LASER_PORT = Komunikation.DEFAULT_OSTECH_PORT

# Status- und Sitzungsvariablen
lockin_device = None
current_file_path = None

is_lockin_connected = False
is_laser_connected = False
is_emergency_bypass = False
communication_threads = None


def stop_communication_threads():
    """Stoppt alle aktiven Hintergrund-Kommunikations-Threads."""
    global communication_threads
    if communication_threads is not None:
        communication_threads.stop()
        communication_threads = None


def check_real_com_port(port_name):
    """Prüft, ob der angegebene COM-Port physikalisch verfügbar ist."""
    if serial:
        return port_name in scan_com_ports()
    if pyvisa:
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources()
            return port_name in resources
        except Exception:
            return False
    return False


def get_available_com_ports():
    """Liest alle verfügbaren COM-Ports des Systems aus."""
    return scan_com_ports()


def open_file_dialog():
    """Öffnet einen Dateiauswahldialog zum Importieren von Messdaten."""
    global current_file_path
    file_path = filedialog.askopenfilename(
        title=auto_tr("Import Data File"),
        filetypes=[("Text Files", "*.txt *.csv"), ("All files", "*.*")]
    )
    if file_path:
        current_file_path = file_path
        #Iclbl_file_status.config(text=os.path.basename(current_file_path))


# GUI-Refresh Job Referenz
refresh_job = None
is_closing = False


def on_closing():
    """Beendet die GUI und trennt alle Verbindungen und Threads sicher."""
    global refresh_job, is_closing
    if is_closing:
        return
    is_closing = True

    stop_communication_threads()

    if refresh_job is not None:
        try:
            root.after_cancel(refresh_job)
        except tk.TclError:
            pass
        refresh_job = None

    SimGuiUpdatet.stop(root)
    Log.Log("Sys", "GUI", "Info", "Foreground Shutdown", "GUI closed")
    root.quit()
    root.destroy()


# ==========================================
# GUI ANWENDUNG INITIALISIERUNG
# ==========================================
root = tk.Tk()
root.title('PAMO - Photothermal Analysis & Monitoring Overview')
root.state("zoomed")
root.configure(bg="#2b2b2b")
root.protocol("WM_DELETE_WINDOW", on_closing)

# Styling-Konfiguration
style = ttk.Style()
style.theme_use('default')
style.configure("TNotebook", background="#2b2b2b", borderwidth=0)
style.configure("TNotebook.Tab", background="#3c3f41", foreground="#ffffff", padding=[10, 6],
                font=('Consolas', 10, 'bold'))
style.map("TNotebook.Tab", background=[("selected", "#007acc")], foreground=[("selected", "#ffffff")])

# Status-Anzeige-Listen
status_labels_lockin = []
status_labels_laser = []


def update_status_indicators():
    """Aktualisiert alle visuellen Verbindungs-Labels im Interface."""
    for lbl in status_labels_lockin:
        lbl.config(text="🟢 Connected" if is_lockin_connected else "🔴 Disconnected",
                   fg="#00ff00" if is_lockin_connected else "#ff4444")
    for lbl in status_labels_laser:
        lbl.config(text="🟢 Connected" if is_laser_connected else "🔴 Disconnected",
                   fg="#00ff00" if is_laser_connected else "#ff4444")


# ==========================================
# HARDWARE SAMMLUNGSFUNKTIONEN
# ==========================================
def connect_all_hardware():
    """Initiert die Verbindung zu Lock-In Verstaerker und Laser Controller."""
    global is_lockin_connected, is_laser_connected
    global LOCK_IN_AMPLIFIER_PORT, LASER_PORT
    global communication_threads
    SimGuiUpdatet.stop(root)
    stop_communication_threads()

    Komunikation.close_devices()
    connected_sr830, connected_ostech = Komunikation.open_devices(
        sr830_port=LOCK_IN_AMPLIFIER_PORT or None,
        ostech_port=LASER_PORT or None,
    )
    LOCK_IN_AMPLIFIER_PORT = Komunikation.SR830_PORT
    LASER_PORT = Komunikation.OSTECH_PORT

    is_lockin_connected = connected_sr830 is not None or is_emergency_bypass
    is_laser_connected = connected_ostech is not None or is_emergency_bypass

    update_status_indicators()

    if is_lockin_connected or is_laser_connected:
        communication_threads = Komunikation.start_threaded_measurement(cycles=None)

    lockin_result = "SUCCESS" if is_lockin_connected else "FAILED"
    laser_result = "SUCCESS" if is_laser_connected else "FAILED"
    update_overview_log(f"Connect SR830 on {LOCK_IN_AMPLIFIER_PORT}: {lockin_result}")
    update_overview_log(f"Connect OSTECH on {LASER_PORT}: {laser_result}")


def disconnect_all_hardware():
    """Trennt die Verbindung zu allen angeschlossenen Geräten."""
    global is_lockin_connected, is_laser_connected, is_emergency_bypass, lockin_device
    is_lockin_connected = False
    is_laser_connected = False
    is_emergency_bypass = False
    SimGuiUpdatet.stop(root)
    stop_communication_threads()
    Komunikation.close_devices()
    lockin_device = None

    update_status_indicators()
    update_overview_log("Hardware connections disconnected.")


# ------------------------------------------
# HARDWARE STEUERUNGSLEISTEN (Anpassung: Textfeld statt Combobox)
# ------------------------------------------
def create_lockin_control_bar(parent):
    """Erzeugt die Verbindungskontrollleiste für den Lock-In Amplifier mit Textfeld für COM-Port."""
    frame = tk.LabelFrame(parent, text=" Lock-In Connection Control ", font=("Consolas", 10, "bold"),
                          bg="#1e1e1e", fg="#00ffcc", padx=10, pady=8)
    frame.pack(fill="x", padx=10, pady=5)

    tk.Label(frame, text="COM Port:", bg="#1e1e1e", fg="#ffffff", font=("Consolas", 9, "bold")).pack(side="left",
                                                                                                     padx=5)

    # Textfeld statt Combobox
    entry_com = ttk.Entry(frame, width=12)
    if LOCK_IN_AMPLIFIER_PORT:
        entry_com.insert(0, LOCK_IN_AMPLIFIER_PORT)
    else:
        entry_com.insert(0, "COM1")
    entry_com.pack(side="left", padx=5)

    def do_connect():
        global LOCK_IN_AMPLIFIER_PORT
        LOCK_IN_AMPLIFIER_PORT = entry_com.get().strip()
        connect_all_hardware()

    btn_connect = tk.Button(frame, text="🔌 Connect", font=("Consolas", 8, "bold"), bg="#2e7d32", fg="white",
                            command=do_connect)
    btn_connect.pack(side="left", padx=5)

    btn_disconnect = tk.Button(frame, text="❌ Disconnect", font=("Consolas", 8, "bold"), bg="#c62828", fg="white",
                               command=disconnect_all_hardware)
    btn_disconnect.pack(side="left", padx=5)

    lbl_status = tk.Label(frame, text="🔴 Disconnected", font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#ff4444")
    lbl_status.pack(side="right", padx=10)
    status_labels_lockin.append(lbl_status)
    return frame


def create_laser_control_bar(parent):
    """Erzeugt die Verbindungskontrollleiste für den Laser Controller mit Textfeld für COM-Port."""
    frame = tk.LabelFrame(parent, text=" Laser Connection Control ", font=("Consolas", 10, "bold"),
                          bg="#1e1e1e", fg="#00ffcc", padx=10, pady=8)
    frame.pack(fill="x", padx=10, pady=5)

    tk.Label(frame, text="COM Port:", bg="#1e1e1e", fg="#ffffff", font=("Consolas", 9, "bold")).pack(side="left",
                                                                                                     padx=5)

    # Textfeld statt Combobox
    entry_com = ttk.Entry(frame, width=12)
    if LASER_PORT:
        entry_com.insert(0, LASER_PORT)
    else:
        entry_com.insert(0, "COM2")
    entry_com.pack(side="left", padx=5)

    def do_connect():
        global LASER_PORT
        LASER_PORT = entry_com.get().strip()
        connect_all_hardware()

    btn_connect = tk.Button(frame, text="🔌 Connect", font=("Consolas", 8, "bold"), bg="#2e7d32", fg="white",
                            command=do_connect)
    btn_connect.pack(side="left", padx=5)

    btn_disconnect = tk.Button(frame, text="❌ Disconnect", font=("Consolas", 8, "bold"), bg="#c62828", fg="white",
                               command=disconnect_all_hardware)
    btn_disconnect.pack(side="left", padx=5)

    lbl_status = tk.Label(frame, text="🔴 Disconnected", font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#ff4444")
    lbl_status.pack(side="right", padx=10)
    status_labels_laser.append(lbl_status)
    return frame

def toggle_laser():
    """Schaltet den Laser ein oder aus und sendet den passenden OStech-Befehl."""
    current_state = bool(getattr(State, "L", False))
    new_state = not current_state

    try:
        if not is_emergency_bypass:
            if not is_laser_connected or Komunikation.OSTECH is None:
                raise RuntimeError("OStech Laser Controller ist nicht verbunden.")

            # Beim Starten wird die Laser-Ausgabe aktiviert, beim Ausschalten gestoppt.
            if new_state:
                Send.run(Send.OSTechS.LGR)
            else:
                Send.run(Send.OSTechS.L)

        # Lokalen Status aktualisieren & Button-Design anpassen
        State.L = 1 if new_state else 0
        update_laser_toggle_button(new_state)

        status_text = "EINGESCHALTET" if new_state else "AUSGESCHALTET"
        messagebox.showinfo("Laser Controller", f"Laser wurde {status_text}.")
        Log.Log("Gui", "Laser", "Info", "Laser Power", f"Laser set to {status_text}")

    except Exception as e:
        messagebox.showerror("Laser Fehler", f"Fehler beim Umschalten des Lasers:\n{e}")

def update_laser_toggle_button(is_on):
    """Aktualisiert Text und Farbe des Laser-Start/Stopp-Knopfs."""
    if is_on:
        btn_laser_toggle.config(
            text="⚡ LASER STOPPEN ⚡",
            bg="#d32f2f",        # Auffälliges Rot
            activebackground="#b71c1c",
            fg="#ffffff"
        )
    else:
        btn_laser_toggle.config(
            text="⚡ LASER STARTEN ⚡",
            bg="#388e3c",        # Auffälliges Grün
            activebackground="#2e7d32",
            fg="#ffffff"
        )


# ==========================================
# REGISTERKARTEN / TABS INITIALISIERUNG
# ==========================================
# Haupt-Notebook für alle primären Tabs
main_notebook = ttk.Notebook(root)
main_notebook.pack(fill="both", expand=True, padx=10, pady=10)

# ------------------------------------------
# 0. TAB: HOME
# ------------------------------------------
tab_home = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_home, text="")
reg_ui((main_notebook, tab_home), "Home", "tab_text")

lbl_welcome = tk.Label(tab_home, font=("Consolas", 12, "bold"), bg="#1e1e1e", fg="#00ffcc")
lbl_welcome.pack(pady=(40, 10))
reg_ui(lbl_welcome, "WELCOME TO PAMO - THE PHOTOTHERMAL ANALYSIS & MONITORING OVERVIEW")

lbl_info = tk.Label(tab_home, font=("Segoe UI", 10), bg="#1e1e1e", fg="#aaaaaa", justify="center")
lbl_info.pack(pady=10)
reg_ui(lbl_info, "Select a tab above to control hardware or run data analysis.")

# ------------------------------------------
# 1. TAB: OVERVIEW
# ------------------------------------------
tab_overview = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_overview, text="")
reg_ui((main_notebook, tab_overview), "Overview", "tab_text")

frame_overview_status = tk.LabelFrame(tab_overview, text=" Hardware Connection Status ",
                                      font=("Consolas", 10, "bold"),
                                      bg="#1e1e1e", fg="#00ffcc", padx=15, pady=5)
frame_overview_status.pack(fill="x", padx=10, pady=5)

tk.Label(frame_overview_status, text="Lock-in-Amplifier:", bg="#1e1e1e", fg="#aaaaaa",
         font=("Consolas", 10, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)
lbl_status_ov_lockin = tk.Label(frame_overview_status, text="🔴 Disconnected", font=("Consolas", 10, "bold"),
                                bg="#1e1e1e", fg="#ff4444")
lbl_status_ov_lockin.grid(row=0, column=1, sticky="w", padx=10, pady=5)
status_labels_lockin.append(lbl_status_ov_lockin)

tk.Label(frame_overview_status, text="Laser Controller:", bg="#1e1e1e", fg="#aaaaaa",
         font=("Consolas", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(30, 10), pady=5)
lbl_status_ov_laser = tk.Label(frame_overview_status, text="🔴 Disconnected", font=("Consolas", 10, "bold"),
                               bg="#1e1e1e", fg="#ff4444")
lbl_status_ov_laser.grid(row=0, column=3, sticky="w", padx=10, pady=5)
status_labels_laser.append(lbl_status_ov_laser)

# --- Vorschau der Displays ---
frame_previews = tk.Frame(tab_overview, bg="#1e1e1e")
frame_previews.pack(fill="x", padx=10, pady=5)

# Lock-In Vorschau
frame_ov_lockin = tk.LabelFrame(frame_previews, text=" Lock-In Display Preview (Read-Only) ",
                                font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=10, pady=5)
frame_ov_lockin.pack(side="left", fill="both", expand=True, padx=(0, 5))

frame_ov_ch1 = tk.Frame(frame_ov_lockin, bg="#000000", bd=2, relief="sunken")
frame_ov_ch1.pack(fill="x", pady=2, padx=2)
lbl_ov_ch1_title = tk.Label(frame_ov_ch1, text="CH1 Display [X]", font=("Consolas", 8, "bold"), bg="#000000",
                            fg="#00ffcc")
lbl_ov_ch1_title.pack(anchor="w", padx=5, pady=2)
lbl_ov_ch1_val = tk.Label(frame_ov_ch1, text="0.0000 V", font=("Consolas", 16, "bold"), bg="#000000", fg="#00ff00")
lbl_ov_ch1_val.pack(padx=5, pady=2)

frame_ov_ch2 = tk.Frame(frame_ov_lockin, bg="#000000", bd=2, relief="sunken")
frame_ov_ch2.pack(fill="x", pady=2, padx=2)
lbl_ov_ch2_title = tk.Label(frame_ov_ch2, text="CH2 Display [Phase (θ)]", font=("Consolas", 8, "bold"), bg="#000000",
                            fg="#00ffcc")
lbl_ov_ch2_title.pack(anchor="w", padx=5, pady=2)
lbl_ov_ch2_val = tk.Label(frame_ov_ch2, text="0.00 °", font=("Consolas", 16, "bold"), bg="#000000", fg="#00ff00")
lbl_ov_ch2_val.pack(padx=5, pady=2)

# Laser Vorschau
frame_ov_laser = tk.LabelFrame(frame_previews, text=" Laser Layout Preview (Read-Only) ", font=("Consolas", 9, "bold"),
                               bg="#1e1e1e", fg="#00ffcc", padx=10, pady=5)
frame_ov_laser.pack(side="right", fill="both", expand=True, padx=(5, 0))

lbl_ov_laser_layout_title = tk.Label(frame_ov_laser, text="Hardware Layout:", font=("Consolas", 8, "bold"),
                                     bg="#1e1e1e", fg="#aaaaaa")
lbl_ov_laser_layout_title.pack(anchor="w", pady=(2, 0))
lbl_ov_laser_layout_val = tk.Label(frame_ov_laser, text="(b) Laser driver with one TEC controller",
                                   font=("Consolas", 9, "bold"), bg="#000000", fg="#00ffcc", anchor="w", padx=5, pady=3,
                                   relief="sunken")
lbl_ov_laser_layout_val.pack(fill="x", pady=2)

lbl_ov_laser_main_val = tk.Label(frame_ov_laser, text="0.0 mA", font=("Consolas", 18, "bold"), bg="#000000",
                                 fg="#00ff00", bd=2, relief="sunken")
lbl_ov_laser_main_val.pack(fill="x", pady=5)

# Live-Log
frame_overview_log = tk.LabelFrame(tab_overview, text=" Live Log Terminal ", font=("Consolas", 10, "bold"),
                                   bg="#1e1e1e", fg="#00ffcc", padx=10, pady=5)
frame_overview_log.pack(fill="both", expand=True, padx=10, pady=5)

txt_overview_log = tk.Text(frame_overview_log, bg="#000000", fg="#00ff00", font=("Consolas", 9), state="disabled",
                           wrap="word")
txt_overview_log.pack(fill="both", expand=True, padx=5, pady=5)


def update_overview_log(message):
    """Schreibt System- und Statusnachrichten in das Overview Log Terminal."""
    txt_overview_log.config(state="normal")
    txt_overview_log.insert("end", f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}\n")
    txt_overview_log.see("end")
    txt_overview_log.config(state="disabled")


update_overview_log("System initialized. Monitoring active...")

# ------------------------------------------
# 2. TAB: EXPERIMENT (Anpassung: ehemals Analysis, jetzt an 3. Stelle)
# ------------------------------------------
tab_experiment = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_experiment, text="")
reg_ui((main_notebook, tab_experiment), "Experiment", "tab_text")

# Untertabs für Experiment
exp_notebook = ttk.Notebook(tab_experiment)
exp_notebook.pack(fill="both", expand=True, padx=10, pady=10)

# Untertab 2.1: Experiment Settings
tab_exp_settings = tk.Frame(exp_notebook, bg="#1e1e1e")
exp_notebook.add(tab_exp_settings, text="")
reg_ui((exp_notebook, tab_exp_settings), "Experiment Settings", "tab_text")

frame_sweep = tk.LabelFrame(tab_exp_settings, text=" Frequency Parameter Sweep ", font=("Consolas", 10, "bold"),
                            bg="#1e1e1e", fg="#00ffcc", padx=15, pady=15)
frame_sweep.pack(fill="x", padx=10, pady=10)

tk.Label(frame_sweep, text="Start Frequency (Hz):", font=("Consolas", 9), bg="#1e1e1e", fg="#ffffff").grid(row=0,
                                                                                                           column=0,
                                                                                                           sticky="w",
                                                                                                           padx=5,
                                                                                                           pady=5)
entry_sweep_start = ttk.Entry(frame_sweep, width=15)
entry_sweep_start.insert(0, "10.0")
entry_sweep_start.grid(row=0, column=1, sticky="w", padx=5, pady=5)

tk.Label(frame_sweep, text="End Frequency (Hz):", font=("Consolas", 9), bg="#1e1e1e", fg="#ffffff").grid(row=1,
                                                                                                         column=0,
                                                                                                         sticky="w",
                                                                                                         padx=5, pady=5)
entry_sweep_end = ttk.Entry(frame_sweep, width=15)
entry_sweep_end.insert(0, "100000.0")
entry_sweep_end.grid(row=1, column=1, sticky="w", padx=5, pady=5)





def starte_pvf_analyse():
    """Run Calculations: Berechnet die Schichtdicke / Phase vs. Frequenz."""
    global fig_pvf, canvas_pvf

    # 1. Nutzer nach der Referenzdatei fragen
    path_to_ref = filedialog.askopenfilename(
        title="Referenzmessung auswählen (unnitriert)",
        filetypes=[("Text/CSV Files", "*.txt *.csv"), ("All files", "*.*")]
    )
    if not path_to_ref:
        return  # Abbruch durch Nutzer

    # 2. Live-Daten beziehen (oder Datei als Fallback)
    probe_data = get_live_or_fallback_probe_data()
    if probe_data is None:
        return

    if isinstance(probe_data, dict):
        State.update_values({
            "live_sweep_data": {
                "f_probe": probe_data.get("f_probe") or probe_data.get("frequency"),
                "phase_probe": probe_data.get("phase_probe") or probe_data.get("phase")
            }
        })

    # 3. Berechnung über PhasFreq_v8 starten
    try:
        results = PhasFreq_v8.start_PhaseFreq(path_to_ref, probe_data)
        # print("GESAMTE KEYS IN RESULTS:", results.keys())
        pdata = results.get("plot_data", {})

        # 1. Figure & Axes initialisieren bzw. bestehende säubern
        # --- FIGURE INITIALISIEREN & VORBEREITEN ---
        if fig_pvf is None:
            fig_pvf = plt.Figure(figsize=(6, 5), dpi=100)
        else:
            fig_pvf.clf()

        ax_raw = fig_pvf.add_subplot(211)
        ax_fit = fig_pvf.add_subplot(212)

        # --- OBERER PLOT: Rohdaten (Log-Skala) ---
        if "f_ref" in pdata and "phase_ref_unwr" in pdata:
            ref_label = pdata.get("ref_filename", "Referenz (unnitriert)")
            ax_raw.plot(pdata["f_ref"], pdata["phase_ref_unwr"], "o-", label=f"Reference: File One (Untreated)", markersize=4)

        if "f_probe" in pdata and "phase_probe_unwr" in pdata:
            probe_label = pdata.get("probe_filename", "Probe (nitriert)")
            ax_raw.plot(pdata["f_probe"], pdata["phase_probe_unwr"], "s--", label=f"Sample: File Two (Treated)", markersize=4)

        ax_raw.set_xscale("log")
        ax_raw.set_xlabel("Frequency in Hz")
        ax_raw.set_ylabel("Phase in °")
        ax_raw.set_title("Unwrapped Raw Phase Data")
        ax_raw.grid(True, which="both", linestyle="--", alpha=0.5)
        ax_raw.legend(loc="best")

        # --- UNTERER PLOT: Phasendifferenz vs. sqrt(omega) ---
        if "freq_common" in pdata and "Phi" in pdata:
            sqrt_omega_common = np.sqrt(2 * np.pi * np.array(pdata["freq_common"]))
            ax_fit.plot(sqrt_omega_common, pdata["Phi"], "o",
                        label=r"Messdaten $\Phi(\omega) = \Phi_{ref} - \Phi_{probe}$", alpha=0.8, markersize=4)

        if "freq_fine" in pdata and "Phi_fit_curve" in pdata:
            sqrt_omega_fine = np.sqrt(2 * np.pi * np.array(pdata["freq_fine"]))
            ax_fit.plot(sqrt_omega_fine, pdata["Phi_fit_curve"], "--", color="orange",
                        label="angepasste Modellfunktion", linewidth=1.5)

        ax_fit.set_xscale("linear")
        ax_fit.set_xlabel(r"$\sqrt{\omega}$ in $\sqrt{Hz}$")
        ax_fit.set_ylabel(r"Phase difference $\Phi$ in °")

        # Werte direkt aus results auslesen
        d_um = results.get("d_fit_um")
        kL_fit = results.get("kL_fit")

        # Falls sie als Arrays/Listen vorliegen, das erste Element nehmen
        if hasattr(d_um, "__len__") and len(d_um) > 0:
            d_um = d_um[0]
        if hasattr(kL_fit, "__len__") and len(kL_fit) > 0:
            kL_fit = kL_fit[0]

        # Titel setzen
        if d_um is not None and kL_fit is not None:
            ax_fit.set_title(
                rf"$\text{{Layer thickness}} = {float(d_um):.2f}\ \mu\mathrm{{m}},\quad \text{{Thermal conductivity of the Layer}} = {float(kL_fit):.2f}\ \mathrm{{\frac{{W}}{{m\cdot K}}}}$"
            )
        else:
            ax_fit.set_title("Fit-Ergebnisse")

        ax_fit.grid(True, linestyle="--", alpha=0.5)
        ax_fit.legend(loc="best")

        fig_pvf.tight_layout()


        # --- CANVAS AKTUALISIEREN ---
        if canvas_pvf is None:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            canvas_pvf = FigureCanvasTkAgg(fig_pvf, master=frame_plot_pvf)
            canvas_pvf.get_tk_widget().pack(fill="both", expand=True)

        canvas_pvf.draw()

    except Exception as e:
        print(f"Fehler beim Plottem: {e}")


def parse_ptr_log_csv(filepath):
    """
    Liest PTR-Log-CSVs mit 'Message' und 'Value' Spalten ein und extrahiert
    ein Numpy-Array mit Spalte 0 = Frequenz, Spalte 1 = Phase.
    """
    df = pd.read_csv(filepath)

    # Prüfen, ob das Log-Format vorliegt
    if 'Message' in df.columns and 'Value' in df.columns:
        # Frequenzen und Phasen filtern und in Floats umwandeln
        freqs = df[df['Message'] == 'FREQ']['Value'].astype(float).values
        phases = df[df['Message'] == 'PHAS']['Value'].astype(float).values

        if len(freqs) == len(phases) and len(freqs) > 0:
            # Zusammenfügen zu N x 2 Array [[f1, p1], [f2, p2], ...]
            return np.column_stack((freqs, phases))
        else:
            raise ValueError(
                f"Anzahl Frequenzwerte ({len(freqs)}) und Phasenwerte ({len(phases)}) stimmt nicht überein.")

    # Fallback für normale 2-Spalten-CSVs ohne 'Message'/'Value' Header
    else:
        df_numeric = df.select_dtypes(include=['number'])
        return df_numeric.to_numpy(dtype=float)


def get_live_sweep_data():
    """
    Holt Live-Daten aus State.live_sweep_data.
    Wirft eine Exception, wenn keine Daten da sind.
    """
    live_data = getattr(State, "live_sweep_data", None)

    # Sicherstellen, dass wirklich valide Daten vorhanden sind
    if live_data is None:
        raise ConnectionError("Keine Live-Messdaten im Speicher (None).")

    # Falls live_data eine leere Liste oder ein leeres Array ist
    if hasattr(live_data, "__len__") and len(live_data) == 0:
        raise ConnectionError("Live-Messdaten-Puffer ist leer.")

    return live_data


def starte_messunsicherheit_analyse():
    """Button-Handler für 'Run Uncertainty'"""
    global canvas_pvf
    data_to_analyze = None

    # 1. VERSUCH: Live-Daten laden
    try:
        data_to_analyze = get_live_sweep_data()
    except Exception as live_err:
        print(f"[Info] Keinen Live-Puffer gefunden ({live_err}). Fallback zur Dateiauswahl.")

    # 2. FALLBACK: Wenn keine Live-Daten im RAM vorliegen -> Dateiauswahl
    if data_to_analyze is None:
        data_to_analyze = filedialog.askopenfilename(
            title="Messdatei auswählen",
            filetypes=[("CSV Files", "*.csv"), ("Text Files", "*.txt"), ("All files", "*.*")]
        )
        if not data_to_analyze:
            return  # Nutzer hat abgebrochen

    # 3. BERECHNUNG UND PLOTTING MIT v6
    try:
        # v6 aufrufen
        res, fit = SWP_SM_v6.start_Messunsicherheit(data_to_analyze)
        fig = SWP_SM_v6.plot_results(res, fit, show=False)

        # Alten Canvas im Plot-Frame löschen
        if canvas_pvf is not None:
            canvas_pvf.get_tk_widget().destroy()

        # Canvas WICHTIG in 'frame_plot_pvf' platzieren!
        canvas_pvf = FigureCanvasTkAgg(fig, master=frame_plot_pvf)
        canvas_pvf.draw()
        canvas_pvf.get_tk_widget().pack(fill="both", expand=True)

        plt.close(fig)  # Speicher freigeben

    except (SWP_SM_v6.InvalidFileTypeError, SWP_SM_v6.InvalidFileContentError) as gate_err:
        messagebox.showerror("Ungültiges Dateiformat", f"SNAP-Format Fehler:\n{gate_err}")
    except Exception as e:
        messagebox.showerror("Fehler bei Messunsicherheit", f"Berechnung fehlgeschlagen:\n{e}")


def apply_sweep_settings():
    """Liest und überprüft die Parameter für den Frequenz-Sweep."""
    f_start = read_numeric_entry(entry_sweep_start, "Start Frequency", 0.001, 102000)
    f_end = read_numeric_entry(entry_sweep_end, "End Frequency", 0.001, 102000)
    if f_start is not None and f_end is not None:
        messagebox.showinfo("Sweep Settings", f"Frequency Sweep gesetzt von {f_start} Hz bis {f_end} Hz.")


btn_apply_sweep = tk.Button(frame_sweep, text="✔ Set Sweep Parameters", font=("Consolas", 9, "bold"), bg="#007acc",
                            fg="white", command=apply_sweep_settings)
btn_apply_sweep.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")


# --- Untertab 2.2: Results (Calculations & Fit) ---
tab_exp_results = tk.Frame(exp_notebook, bg="#252526")
exp_notebook.add(tab_exp_results, text="Results")
reg_ui(tab_exp_results, "Ergebnisse", "Results")


def import_data_file_callback():
    from tkinter import filedialog, messagebox
    import os, shutil

    file_path = filedialog.askopenfilename(
        title="Import CSV Log File",
        filetypes=[("CSV Files", "*.csv"), ("All files", "*.*")]
    )
    if file_path:
        try:
            dest_path = os.path.join(LOG_DIR, os.path.basename(file_path))
            shutil.copy(file_path, dest_path)
            messagebox.showinfo("Import", f"CSV file successfully imported: {os.path.basename(file_path)}")
            #lbl_file_status.config(text=os.path.basename(file_path), fg="white")
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import CSV: {e}")


# --- Obere Steuerungsleiste im Subtab ---
frame_top_bar = tk.Frame(tab_exp_results, bg="#1e1e1e")
frame_top_bar.pack(side="top", fill="x", padx=10, pady=5)


paned_stats = ttk.PanedWindow(tab_exp_results, orient="horizontal")
paned_stats.pack(fill="both", expand=True, padx=5, pady=5)

frame_tree_stats = tk.Frame(paned_stats, bg="#1e1e1e", width=260)
paned_stats.add(frame_tree_stats, weight=1)

lbl_tree_stats_title = tk.Label(frame_tree_stats, text="PROJECT EXPLORER", font=("Consolas", 9, "bold"), bg="#3c3f41",
                                fg="#ffffff", anchor="w", padx=5)
lbl_tree_stats_title.pack(fill="x")

tree_stats = ttk.Treeview(frame_tree_stats, show="tree")
tree_stats.pack(fill="both", expand=True)

frame_stats_work = tk.Frame(paned_stats, bg="#252526")
paned_stats.add(frame_stats_work, weight=4)

frame_stats_top = tk.Frame(frame_stats_work, bg="#252526")
frame_stats_top.pack(fill="x", pady=10)

btn_run_calc = tk.Button(
    frame_stats_top,
    text="Run Calculations",
    font=("Consolas", 9, "bold"),
    bg="#007acc",
    fg="white",
    command=starte_pvf_analyse
)
btn_run_calc.pack(side="left", padx=10)

btn_run_uncertainty = tk.Button(
    frame_stats_top,
    text="Run Uncertainty",
    font=("Consolas", 9, "bold"),
    bg="#007acc",
    fg="white",
    command=starte_messunsicherheit_analyse
)
btn_run_uncertainty.pack(side="left", padx=10)


frame_plot_pvf = tk.Frame(frame_stats_work, bg="#1e1e1e", bd=2, relief="sunken")
frame_plot_pvf.pack(fill="both", expand=True, padx=10, pady=5)

fig_pvf = None
ax_pvf = None
canvas_pvf = None


def get_live_or_fallback_probe_data():
    """
    Sucht nach Live-Daten im Speicher (State.live_sweep_data).
    Gibt die Live-Daten zurück oder öffnet als Fallback den Datei-Explorer.
    """
    live_data = getattr(State, "live_sweep_data", None)

    if live_data is not None:
        return live_data

    # Fallback: Keine Live-Daten vorhanden
    messagebox.showwarning(
        "Keine Live-Messdaten",
        "Es wurden keine aktuellen Sweep-Messdaten im Speicher gefunden.\n"
        "Bitte wähle manuell die Messdatei der Nitrierschicht (Probe) aus."
    )
    path_to_probe = filedialog.askopenfilename(
        title="Messdatei der Nitrierschicht (Probe) auswählen",
        filetypes=[("Text/CSV Files", "*.txt *.csv"), ("All files", "*.*")]
    )
    return path_to_probe if path_to_probe else None

'''
btn_calc = tk.Button(frame_stats_top, text="⚡ Run Calculations", font=("Consolas", 9, "bold"), bg="#2e7d32", fg="white",
                     padx=10, pady=5, command=starte_pvf_analyse)
btn_calc.pack(side="left", padx=10)
'''
# ------------------------------------------
# 3. TAB: LOGS
# ------------------------------------------
tab_logs = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_logs, text="")
reg_ui((main_notebook, tab_logs), "Logs", "tab_text")

paned_logs_main = ttk.PanedWindow(tab_logs, orient="horizontal")
paned_logs_main.pack(fill="both", expand=True, padx=10, pady=10)

frame_tree_logs_main = tk.Frame(paned_logs_main, bg="#1e1e1e", width=280)
paned_logs_main.add(frame_tree_logs_main, weight=1)

lbl_tree_logs_title = tk.Label(frame_tree_logs_main, text="LOG EXPLORER", font=("Consolas", 9, "bold"), bg="#3c3f41",
                               fg="#ffffff", anchor="w", padx=5)
lbl_tree_logs_title.pack(fill="x")

tree_logs_main = ttk.Treeview(frame_tree_logs_main, show="tree")
tree_logs_main.pack(fill="both", expand=True)

frame_logs_work_main = tk.Frame(paned_logs_main, bg="#252526")
paned_logs_main.add(frame_logs_work_main, weight=4)

frame_log_ctrl_main = tk.Frame(frame_logs_work_main, bg="#252526")
frame_log_ctrl_main.pack(fill="x", pady=5, padx=5)

lbl_log_name = tk.Label(frame_log_ctrl_main, text="Log File Name:", font=("Consolas", 8, "bold"), bg="#252526",
                        fg="#ffffff")
lbl_log_name.pack(side="left", padx=5)

default_log_filename = f"{datetime.date.today().strftime('%Y-%m-%d')}_Experiment_01"
entry_log_name = ttk.Entry(frame_log_ctrl_main, width=30)
entry_log_name.insert(0, default_log_filename)
entry_log_name.pack(side="left", padx=5)

entry_manual_note = ttk.Entry(frame_log_ctrl_main, width=40)
entry_manual_note.insert(0, "Insert message...")
entry_manual_note.pack(side="left", padx=5)


def add_manual_log_note():
    """Fügt einen manuellen Benutzereintrag in das Logsystem ein."""
    note = entry_manual_note.get().strip()
    if not note or note == "Nachricht eingeben...":
        messagebox.showwarning("Hinweis", "Bitte zuerst eine Nachricht eingeben.")
        return

    Log.Log("Gui", "USER", "Info", "Manual note", note, "GUI input")
    entry_manual_note.delete(0, "end")
    entry_manual_note.insert(0, "Nachricht eingeben...")


btn_add_note = tk.Button(frame_log_ctrl_main, text="📝 Note", font=("Consolas", 8, "bold"), bg="#388e3c",
                         fg="white", padx=8, pady=3, command=add_manual_log_note)
btn_add_note.pack(side="left", padx=5)


def save_current_log():
    """Speichert das aktuelle Log-Terminal als CSV-/Textdatei ab."""
    filename = entry_log_name.get().strip()
    if not filename:
        messagebox.showerror("Error", "Please enter a valid log file name.")
        return
    if not filename.endswith(".csv") and not filename.endswith(".log") and not filename.endswith(".txt"):
        filename += ".csv"

    filepath = os.path.join(LOG_DIR, filename)
    try:
        content = txt_log_terminal_main.get("1.0", "end-1c")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        messagebox.showinfo("Success", f"Log saved successfully as:\n{filename}")
        build_file_tree(tree_logs_main, LOG_DIR)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save log: {e}")


btn_save_log = tk.Button(frame_log_ctrl_main, text="💾 Save Log", font=("Consolas", 8, "bold"), bg="#007acc", fg="white",
                         padx=8, pady=3, command=save_current_log)
btn_save_log.pack(side="left", padx=5)


def import_external_csv():
    """Kopiert eine externe Logdatei in den zentralen 'logs'-Ordner."""
    file_path = filedialog.askopenfilename(
        title="Import CSV Log File",
        filetypes=[("CSV Files", "*.csv"), ("All files", "*.*")]
    )
    if file_path:
        dest_path = os.path.join(LOG_DIR, os.path.basename(file_path))
        try:
            shutil.copy(file_path, dest_path)
            messagebox.showinfo("Import",
                                f"CSV file successfully imported into Log Directory:\n{os.path.basename(file_path)}")
            build_file_tree(tree_logs_main, LOG_DIR)
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import CSV: {e}")


btn_import_csv = tk.Button(frame_log_ctrl_main, text="📥 Import CSV", font=("Consolas", 8, "bold"), bg="#f57c00",
                           fg="white", padx=8, pady=3, command=import_external_csv)
btn_import_csv.pack(side="left", padx=5)

btn_clear_logs_main = tk.Button(frame_log_ctrl_main, text="Clear Terminal", font=("Consolas", 8), bg="#3c3f41",
                                fg="white", padx=8, pady=3,
                                command=lambda: (txt_log_terminal_main.config(state="normal"),
                                                 txt_log_terminal_main.delete("1.0", "end"),
                                                 txt_log_terminal_main.config(state="disabled")))
btn_clear_logs_main.pack(side="right", padx=5)

txt_log_terminal_main = tk.Text(frame_logs_work_main, bg="#000000", fg="#00ff00", font=("Consolas", 9),
                                state="disabled", wrap="word")
txt_log_terminal_main.pack(fill="both", expand=True, padx=5, pady=5)


def append_gui_log_text(message):
    """Callback-Funktion für das Haupt-Log-Terminal."""
    if not root.winfo_exists():
        return

    def _append_to_widget():
        txt_log_terminal_main.config(state="normal")
        txt_log_terminal_main.insert("end", message)
        txt_log_terminal_main.see("end")
        txt_log_terminal_main.config(state="disabled")

    try:
        root.after(0, _append_to_widget)
    except Exception:
        _append_to_widget()


Log.register_gui_callback(append_gui_log_text, filter_func=Log.gui_live_log_filter)


def on_tree_logs_main_select(event):
    """Zeigt den Inhalt der im Explorer ausgewählten Datei im Terminal an."""
    selected = tree_logs_main.selection()
    if selected:
        val = tree_logs_main.item(selected[0], "values")
        if val and os.path.isfile(val[0]):
            try:
                with open(val[0], "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                txt_log_terminal_main.config(state="normal")
                txt_log_terminal_main.delete("1.0", "end")
                txt_log_terminal_main.insert("end", f"=== FILE DISPLAY: {os.path.basename(val[0])} ===\n\n")
                txt_log_terminal_main.insert("end", content)
                txt_log_terminal_main.config(state="disabled")
            except Exception:
                pass


tree_logs_main.bind("<<TreeviewSelect>>", on_tree_logs_main_select)

# ------------------------------------------
# 4. TAB: LOCK-IN AMPLIFIER
# ------------------------------------------
tab_lockin = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_lockin, text="")
reg_ui((main_notebook, tab_lockin), "Lock-In Amplifier", "tab_text")

create_lockin_control_bar(tab_lockin)

frame_lockin_content = tk.Frame(tab_lockin, bg="#1e1e1e")
frame_lockin_content.pack(fill="both", expand=True)

frame_lockin_content.columnconfigure((0, 1, 2, 3), weight=1, pad=5)
frame_lockin_content.rowconfigure(0, weight=1)

frame_input = tk.LabelFrame(frame_lockin_content, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=8,
                            pady=5)
frame_input.grid(row=0, column=0, sticky="nsew", padx=4, pady=5)
reg_ui(frame_input, " Signal Inputs & Filters ")

lbl_in_cfg = tk.Label(frame_input, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_in_cfg.pack(anchor="w", pady=(2, 0))
reg_ui(lbl_in_cfg, "Input Configuration:")
combo_in_cfg = ttk.Combobox(frame_input, values=["A", "A-B", "I (1M)", "I (100M)"], state="readonly")
combo_in_cfg.current(0)
combo_in_cfg.pack(fill="x", pady=2)

lbl_coupling = tk.Label(frame_input, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_coupling.pack(anchor="w", pady=(5, 0))
reg_ui(lbl_coupling, "Coupling:")
combo_coupling = ttk.Combobox(frame_input, values=["AC", "DC"], state="readonly")
combo_coupling.current(0)
combo_coupling.pack(fill="x", pady=2)

lbl_grounding = tk.Label(frame_input, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_grounding.pack(anchor="w", pady=(5, 0))
reg_ui(lbl_grounding, "Grounding:")
combo_grounding = ttk.Combobox(frame_input, values=["Float", "Ground"], state="readonly")
combo_grounding.current(1)
combo_grounding.pack(fill="x", pady=2)

lbl_notch = tk.Label(frame_input, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_notch.pack(anchor="w", pady=(5, 0))
reg_ui(lbl_notch, "Line Notch Filter:")
combo_notch = ttk.Combobox(frame_input, values=["Out", "Line (50/60Hz)", "2x Line", "Both"], state="readonly")
combo_notch.current(0)
combo_notch.pack(fill="x", pady=2)

lbl_sens = tk.Label(frame_input, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_sens.pack(anchor="w", pady=(5, 0))
reg_ui(lbl_sens, "Sensitivity:")
combo_sens_values = [
    "2 nV/fA", "5 nV/fA", "10 nV/fA", "20 nV/fA", "50 nV/fA", "100 nV/fA", "200 nV/fA", "500 nV/fA",
    "1 uV/pA", "2 uV/pA", "5 uV/pA", "10 uV/pA", "20 uV/pA", "50 uV/pA", "100 uV/pA", "200 uV/pA",
    "500 uV/pA", "1 mV/nA", "2 mV/nA", "5 mV/nA", "10 mV/nA", "20 mV/nA", "50 mV/nA", "100 mV/nA",
    "200 mV/nA", "500 mV/nA", "1 V/uA",
]
combo_sens = ttk.Combobox(frame_input, values=combo_sens_values, state="readonly")
combo_sens.current(len(combo_sens_values) - 1)
combo_sens.pack(fill="x", pady=2)

lbl_res = tk.Label(frame_input, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_res.pack(anchor="w", pady=(5, 0))
reg_ui(lbl_res, "Dynamic Reserve:")
combo_res = ttk.Combobox(frame_input, values=["High Reserve", "Normal", "Low Noise"], state="readonly")
combo_res.current(1)
combo_res.pack(fill="x", pady=2)

lbl_tc = tk.Label(frame_input, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_tc.pack(anchor="w", pady=(5, 0))
reg_ui(lbl_tc, "Time Constant:")
combo_tc_values = [
    "10 us", "30 us", "100 us", "300 us", "1 ms", "3 ms", "10 ms", "30 ms", "100 ms", "300 ms",
    "1 s", "3 s", "10 s", "30 s", "100 s", "300 s", "1 ks", "3 ks", "10 ks", "30 ks",
]
combo_tc = ttk.Combobox(frame_input, values=combo_tc_values, state="readonly")
combo_tc.current(9)
combo_tc.pack(fill="x", pady=2)

lbl_slope = tk.Label(frame_input, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_slope.pack(anchor="w", pady=(5, 0))
reg_ui(lbl_slope, "Filter Slope:")
combo_slope = ttk.Combobox(frame_input, values=["6 dB/oct", "12 dB/oct", "18 dB/oct", "24 dB/oct"], state="readonly")
combo_slope.current(3)
combo_slope.pack(fill="x", pady=2)


def apply_lockin_filter_settings():
    """Überträgt die eingegebenen Filter- und Signal-Einstellungen an den SR830."""
    if not messagebox.askyesno("Bestätigung",
                               "Filter- und Eingangs-Einstellungen an den Lock-In Amplifier übermitteln?"):
        return

    try:
        sensitivity_map = {
            "2 nV/fA": 0, "5 nV/fA": 1, "10 nV/fA": 2, "20 nV/fA": 3, "50 nV/fA": 4, "100 nV/fA": 5,
            "200 nV/fA": 6, "500 nV/fA": 7, "1 uV/pA": 8, "2 uV/pA": 9, "5 uV/pA": 10, "10 uV/pA": 11,
            "20 uV/pA": 12, "50 uV/pA": 13, "100 uV/pA": 14, "200 uV/pA": 15, "500 uV/pA": 16,
            "1 mV/nA": 17, "2 mV/nA": 18, "5 mV/nA": 19, "10 mV/nA": 20, "20 mV/nA": 21, "50 mV/nA": 22,
            "100 mV/nA": 23, "200 mV/nA": 24, "500 mV/nA": 25, "1 V/uA": 26,
        }

        mapping = {
            "ISRC": {"A": 0, "A-B": 1, "I (1M)": 2, "I (100M)": 3},
            "ICPL": {"AC": 0, "DC": 1},
            "IGND": {"Float": 0, "Ground": 1},
            "ILIN": {"Out": 0, "Line (50/60Hz)": 1, "2x Line": 2, "Both": 3},
            "SENS": sensitivity_map,
            "RMOD": {"High Reserve": 0, "Normal": 1, "Low Noise": 2},
            "OFLT": {
                "10 us": 0, "30 us": 1, "100 us": 2, "300 us": 3, "1 ms": 4, "3 ms": 5,
                "10 ms": 6, "30 ms": 7, "100 ms": 8, "300 ms": 9, "1 s": 10, "3 s": 11,
                "10 s": 12, "30 s": 13, "100 s": 14, "300 s": 15, "1 ks": 16, "3 ks": 17,
                "10 ks": 18, "30 ks": 19,
            },
            "OFSL": {"6 dB/oct": 0, "12 dB/oct": 1, "18 dB/oct": 2, "24 dB/oct": 3},
        }

        selected = {
            "ISRC": combo_in_cfg.get(),
            "ICPL": combo_coupling.get(),
            "IGND": combo_grounding.get(),
            "ILIN": combo_notch.get(),
            "SENS": combo_sens.get(),
            "RMOD": combo_res.get(),
            "OFLT": combo_tc.get(),
            "OFSL": combo_slope.get(),
        }

        for command, value in selected.items():
            if value not in mapping[command]:
                raise ValueError(f"Unbekannte Auswahl für {command}: {value!r}")
            send_lockin_command(command, mapping[command][value])

        messagebox.showinfo("Lock-In Amplifier", "Signal- und Filter-Parameter erfolgreich angewendet.")
    except Exception as error:
        messagebox.showerror("Lock-In Fehler", str(error))


btn_apply_input = tk.Button(frame_input, text="✔ Apply Input Settings", font=("Consolas", 8, "bold"), bg="#007acc",
                            fg="white", command=apply_lockin_filter_settings)
btn_apply_input.pack(fill="x", pady=(10, 2))


# --- Hilfsfunktion für Display-Geräteansicht ---
def create_hardware_display_box(parent, status_left=("AUTO", "SYNC")):
    """Baut eine realistische Hardware-Messwert-Anzeige mit skalierten Einheiten auf."""
    disp_frame = tk.Frame(parent, bg="#000000", bd=2, relief="sunken")
    disp_frame.pack(fill="x", pady=2)

    top_bar = tk.Frame(disp_frame, bg="#000000")
    top_bar.pack(fill="x", padx=2, pady=2)

    status_box = tk.Frame(top_bar, bg="#000000")
    status_box.pack(side="left", anchor="n", padx=2, pady=2)
    tk.Label(status_box, text="OVLD", font=("Consolas", 7, "bold"), bg="#000000", fg="#444444").pack(anchor="w")
    tk.Label(status_box, text=status_left[0], font=("Consolas", 7, "bold"), bg="#000000", fg="#00ff00").pack(anchor="w")
    tk.Label(status_box, text=status_left[1], font=("Consolas", 7, "bold"), bg="#000000", fg="#00ff00").pack(anchor="w")

    val_container = tk.Frame(top_bar, bg="#000000")
    val_container.pack(side="left", expand=True, padx=2)

    val_label = tk.Label(val_container, text="+0.0000", font=("Consolas", 22, "bold"), bg="#000000", fg="#00ff00")
    val_label.pack(side="left")

    unit_label = tk.Label(val_container, text="V", font=("Consolas", 14, "bold"), bg="#000000", fg="#00ff00")
    unit_label.pack(side="left", padx=(4, 0))

    # Skalierte, kleinere Einheiten-Matrix am Bildschirmrand (Anpassung 2)
    units_box = tk.Frame(top_bar, bg="#000000")
    units_box.pack(side="right", anchor="n", padx=2)
    units = [
        ("%", "μA", "V"),
        ("DEG", "nA", "mV"),
        ("pA", "μV", "nV"),
        ("fA", "pV", "aA")
    ]
    for r, row in enumerate(units):
        for c, u in enumerate(row):
            tk.Label(units_box, text=u, font=("Consolas", 5, "bold"), bg="#000000", fg="#666666").grid(row=r, column=c,
                                                                                                       padx=1)

    bot_bar = tk.Frame(disp_frame, bg="#000000")
    bot_bar.pack(fill="x", padx=5, pady=(0, 2))

    canvas_bar = tk.Canvas(bot_bar, height=12, bg="#000000", highlightthickness=0)
    canvas_bar.pack(fill="x")

    labels_frame = tk.Frame(bot_bar, bg="#000000")
    labels_frame.pack(fill="x")
    tk.Label(labels_frame, text="Offset", font=("Consolas", 6), bg="#000000", fg="#aaaaaa").pack(side="left",
                                                                                                 expand=True)
    tk.Label(labels_frame, text="Ratio", font=("Consolas", 6), bg="#000000", fg="#aaaaaa").pack(side="left",
                                                                                                expand=True)
    tk.Label(labels_frame, text="Expand", font=("Consolas", 6), bg="#000000", fg="#aaaaaa").pack(side="left",
                                                                                                 expand=True)

    return disp_frame, val_label, unit_label, canvas_bar


# CH1 Display
frame_ch1 = tk.LabelFrame(frame_lockin_content, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=8,
                          pady=5)
frame_ch1.grid(row=0, column=1, sticky="nsew", padx=4, pady=5)
reg_ui(frame_ch1, " CH1 Display ")

lbl_ch1_src = tk.Label(frame_ch1, text="DISPLAY SOURCE:", font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_ch1_src.pack(anchor="w")
combo_ch1_src = ttk.Combobox(frame_ch1, values=["X", "R", "X Noise", "Aux In 1", "Aux In 2"], state="readonly")
combo_ch1_src.current(0)
combo_ch1_src.pack(fill="x", pady=2)

disp_ch1_box, val_ch1_label, val_ch1_unit_label, canvas_bar1 = create_hardware_display_box(frame_ch1, ("AUTO", "SYNC"))

lbl_overload_ch1 = tk.Label(frame_ch1, text="OVERLOAD: OK", font=("Consolas", 8, "bold"), bg="#2e7d32", fg="#ffffff")
lbl_overload_ch1.pack(fill="x", pady=2)

frame_re1 = tk.Frame(frame_ch1, bg="#1e1e1e")
frame_re1.pack(fill="x", pady=4)

frame_ratio1 = tk.Frame(frame_re1, bg="#1e1e1e")
frame_ratio1.pack(side="left", expand=True, fill="x", padx=(0, 2))
tk.Label(frame_ratio1, text="Ratio:", font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa").pack(side="left")
combo_ratio1 = ttk.Combobox(frame_ratio1, values=["None", "AUX IN 1", "AUX IN 2"], state="readonly", width=8)
combo_ratio1.current(0)
combo_ratio1.pack(side="right", expand=True, fill="x")

frame_expand1 = tk.Frame(frame_re1, bg="#1e1e1e")
frame_expand1.pack(side="left", expand=True, fill="x", padx=(2, 0))
tk.Label(frame_expand1, text="Expand:", font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa").pack(side="left")
combo_expand1 = ttk.Combobox(frame_expand1, values=["x1", "x10", "x100"], state="readonly", width=6)
combo_expand1.current(0)
combo_expand1.pack(side="right", expand=True, fill="x")


def update_ch1_display(event=None):
    """Liest die Werte von CH1 aus State.py und aktualisiert das UI."""
    selection = combo_ch1_src.get()
    cmd_map = {
        "X": ("OUTP1", "V"),
        "R": ("OUTP3", "V"),
        "X Noise": ("OUTR1", "V"),
        "Aux In 1": ("OAUX1", "V"),
        "Aux In 2": ("OAUX2", "V")
    }
    cmd, unit = cmd_map.get(selection, ("OUTP1", "V"))
    val = getattr(State, cmd, 0.0)

    val_ch1_label.config(text=f"{val:+.4f}")
    val_ch1_unit_label.config(text=unit)
    lbl_ov_ch1_title.config(text=f"CH1 Display [{selection}]")
    lbl_ov_ch1_val.config(text=f"{val:+.4f} {unit}")

    if abs(val) > 10.0:
        lbl_overload_ch1.config(text="OVERLOAD: DETECTED", bg="#c62828")
    else:
        lbl_overload_ch1.config(text="OVERLOAD: OK", bg="#2e7d32")


combo_ch1_src.bind("<<ComboboxSelected>>", update_ch1_display)


def draw_bargraph(canvas, percent):
    """Zeigt den Signalpegel visuell als Balkendiagramm an."""
    canvas.delete("all")
    width = canvas.winfo_width()
    if width <= 1:
        width = 180
    fill_width = int(width * (percent / 100.0))
    for x in range(0, fill_width, 5):
        color = "#00ff00" if x < width * 0.8 else "#ff3333"
        canvas.create_rectangle(x, 1, x + 3, 11, fill=color, outline="")
    for i in range(1, 8):
        x_pos = int(width * (i / 8.0))
        canvas.create_line(x_pos, 11, x_pos, 14, fill="#ffffff")


canvas_bar1.bind("<Configure>", lambda e: draw_bargraph(canvas_bar1, 68))

frame_off1 = tk.LabelFrame(frame_ch1, text=" OFFSET ", font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#00ffcc")
frame_off1.pack(fill="x", pady=(5, 2))
frame_off1_btns = tk.Frame(frame_off1, bg="#1e1e1e")
frame_off1_btns.pack(fill="x", pady=2)
btn_onoff1 = tk.Button(frame_off1_btns, text="On/Off", font=("Consolas", 7), bg="#3c3f41", fg="white")
btn_onoff1.pack(side="left", expand=True, padx=1)
btn_auto_off1 = tk.Button(frame_off1_btns, text="Auto", font=("Consolas", 7), bg="#3c3f41", fg="white")
btn_auto_off1.pack(side="left", expand=True, padx=1)
btn_mod1 = tk.Button(frame_off1_btns, text="Modify", font=("Consolas", 7), bg="#3c3f41", fg="white")
btn_mod1.pack(side="left", expand=True, padx=1)

# CH2 Display
frame_ch2 = tk.LabelFrame(frame_lockin_content, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=8,
                          pady=5)
frame_ch2.grid(row=0, column=2, sticky="nsew", padx=4, pady=5)
reg_ui(frame_ch2, " CH2 Display ")

lbl_ch2_src = tk.Label(frame_ch2, text="DISPLAY SOURCE:", font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_ch2_src.pack(anchor="w")
combo_ch2_src = ttk.Combobox(frame_ch2, values=["Y", "Phase (θ)", "Y Noise", "Aux In 3", "Aux In 4"], state="readonly")
combo_ch2_src.current(1)
combo_ch2_src.pack(fill="x", pady=2)

disp_ch2_box, val_ch2_label, val_ch2_unit_label, canvas_bar2 = create_hardware_display_box(frame_ch2, ("AUTO", "TRIG"))

lbl_overload_ch2 = tk.Label(frame_ch2, text="OVERLOAD: OK", font=("Consolas", 8, "bold"), bg="#2e7d32", fg="#ffffff")
lbl_overload_ch2.pack(fill="x", pady=2)

frame_re2 = tk.Frame(frame_ch2, bg="#1e1e1e")
frame_re2.pack(fill="x", pady=4)

frame_ratio2 = tk.Frame(frame_re2, bg="#1e1e1e")
frame_ratio2.pack(side="left", expand=True, fill="x", padx=(0, 2))
tk.Label(frame_ratio2, text="Ratio:", font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa").pack(side="left")
combo_ratio2 = ttk.Combobox(frame_ratio2, values=["None", "AUX IN 3", "AUX IN 4"], state="readonly", width=8)
combo_ratio2.current(0)
combo_ratio2.pack(side="right", expand=True, fill="x")

frame_expand2 = tk.Frame(frame_re2, bg="#1e1e1e")
frame_expand2.pack(side="left", expand=True, fill="x", padx=(2, 0))
tk.Label(frame_expand2, text="Expand:", font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa").pack(side="left")
combo_expand2 = ttk.Combobox(frame_expand2, values=["x1", "x10", "x100"], state="readonly", width=6)
combo_expand2.current(0)
combo_expand2.pack(side="right", expand=True, fill="x")


def update_ch2_display(event=None):
    """Liest die Werte von CH2 aus State.py und aktualisiert das UI."""
    selection = combo_ch2_src.get()
    cmd_map = {
        "Y": ("OUTP2", "V"),
        "Phase (θ)": ("OUTP4", "°"),
        "Y Noise": ("OUTR2", "V"),
        "Aux In 3": ("OAUX3", "V"),
        "Aux In 4": ("OAUX4", "V")
    }
    cmd, unit = cmd_map.get(selection, ("OUTP4", "°"))
    val = getattr(State, cmd, 0.0)

    val_ch2_label.config(text=f"{val:+.2f}")
    val_ch2_unit_label.config(text=unit)
    lbl_ov_ch2_title.config(text=f"CH2 Display [{selection}]")
    lbl_ov_ch2_val.config(text=f"{val:+.2f} {unit}")

    if abs(val) > 180.0 if unit == "°" else abs(val) > 10.0:
        lbl_overload_ch2.config(text="OVERLOAD: DETECTED", bg="#c62828")
    else:
        lbl_overload_ch2.config(text="OVERLOAD: OK", bg="#2e7d32")


combo_ch2_src.bind("<<ComboboxSelected>>", update_ch2_display)


def refresh_shared_values():
    """Periodischer GUI-Refresh für kontinuierliche Messwert-Anzeigen."""
    global refresh_job
    if is_closing:
        refresh_job = None
        return
    update_ch1_display()
    update_ch2_display()
    update_laser_display_mode()
    refresh_job = root.after(17, refresh_shared_values)


refresh_job = root.after(17, refresh_shared_values)

canvas_bar2.bind("<Configure>", lambda e: draw_bargraph(canvas_bar2, 42))

frame_off2 = tk.LabelFrame(frame_ch2, text=" OFFSET ", font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#00ffcc")
frame_off2.pack(fill="x", pady=(5, 2))
frame_off2_btns = tk.Frame(frame_off2, bg="#1e1e1e")
frame_off2_btns.pack(fill="x", pady=2)
btn_onoff2 = tk.Button(frame_off2_btns, text="On/Off", font=("Consolas", 7), bg="#3c3f41", fg="white")
btn_onoff2.pack(side="left", expand=True, padx=1)
btn_auto_off2 = tk.Button(frame_off2_btns, text="Auto", font=("Consolas", 7), bg="#3c3f41", fg="white")
btn_auto_off2.pack(side="left", expand=True, padx=1)
btn_mod2 = tk.Button(frame_off2_btns, text="Modify", font=("Consolas", 7), bg="#3c3f41", fg="white")
btn_mod2.pack(side="left", expand=True, padx=1)

# Ref Display & Controls
frame_ref = tk.LabelFrame(frame_lockin_content, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=8,
                          pady=5)
frame_ref.grid(row=0, column=3, sticky="nsew", padx=4, pady=5)
reg_ui(frame_ref, " Ref Display & Controls ")

val_ref_display = tk.Label(frame_ref, text="1000.00 Hz", font=("Consolas", 20, "bold"), bg="#000000", fg="#00ff00",
                           relief="sunken", bd=3)
val_ref_display.pack(fill="x", pady=(2, 6))

frame_auto = tk.LabelFrame(frame_ref, text=" Auto Functions ", font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#ffaa00",
                           padx=5, pady=5)
frame_auto.pack(fill="x", pady=5)
frame_auto.columnconfigure((0, 1), weight=1)


def send_lockin_command(command, value=None):
    """Hilfsfunktion zum Senden von GPIB/Befehlen an den SR830."""
    if is_emergency_bypass:
        return
    if not is_lockin_connected or Komunikation.SR830 is None:
        raise RuntimeError("SR830 ist nicht verbunden.")
    Komunikation.send_SR830(command, value)


def run_auto_command(command, values=None):
    """Führt Automatikfunktionen des Lock-Ins aus."""
    try:
        if values is None:
            send_lockin_command(command)
        else:
            for value in values:
                send_lockin_command(command, value)
    except Exception as error:
        messagebox.showerror("Lock-In Fehler", f"{command}: {error}")


btn_auto_phase = tk.Button(frame_auto, text="Auto Phase", font=("Consolas", 8, "bold"), bg="#3c3f41", fg="white",
                           command=lambda: run_auto_command("APHS"))
btn_auto_phase.grid(row=0, column=0, padx=2, pady=2, sticky="ew")

btn_auto_gain = tk.Button(frame_auto, text="Auto Gain", font=("Consolas", 8, "bold"), bg="#3c3f41", fg="white",
                          command=lambda: run_auto_command("AGAN"))
btn_auto_gain.grid(row=0, column=1, padx=2, pady=2, sticky="ew")

btn_auto_reserve = tk.Button(frame_auto, text="Auto Reserve", font=("Consolas", 8, "bold"), bg="#3c3f41", fg="white",
                             command=lambda: run_auto_command("ARSV"))
btn_auto_reserve.grid(row=1, column=0, padx=2, pady=2, sticky="ew")

btn_auto_offset = tk.Button(frame_auto, text="Auto Offset", font=("Consolas", 8, "bold"), bg="#3c3f41", fg="white",
                            command=lambda: run_auto_command("AOFF", (1, 2, 3)))
btn_auto_offset.grid(row=1, column=1, padx=2, pady=2, sticky="ew")

lbl_freq = tk.Label(frame_ref, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_freq.pack(anchor="w", pady=(4, 0))
reg_ui(lbl_freq, "Ref Frequency (Hz):")
entry_freq = tk.Entry(frame_ref, font=("Consolas", 9), justify="center")
entry_freq.insert(0, "1000.0")
entry_freq.pack(fill="x", pady=1)

lbl_ref_phase = tk.Label(frame_ref, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_ref_phase.pack(anchor="w", pady=(4, 0))
reg_ui(lbl_ref_phase, "Ref Phase (°):")
entry_ref_phase = tk.Entry(frame_ref, font=("Consolas", 9), justify="center")
entry_ref_phase.insert(0, "0.0")
entry_ref_phase.pack(fill="x", pady=1)

lbl_ampl = tk.Label(frame_ref, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_ampl.pack(anchor="w", pady=(4, 0))
reg_ui(lbl_ampl, "Sine Output Amplitude (V):")
entry_ampl = tk.Entry(frame_ref, font=("Consolas", 9), justify="center")
entry_ampl.insert(0, "1.000")
entry_ampl.pack(fill="x", pady=1)


def lockin_start():
    """Startet das Sine Out Signal am Lock-In Amplifier."""
    try:
        send_lockin_command("SLVL", 1.0)
        messagebox.showinfo(auto_tr("Lock-In Amplifier"), auto_tr("Sine Out set to 1.0 V (ON)."))
    except Exception as e:
        messagebox.showerror("Fehler", f"{e}")


def lockin_stop():
    """Stoppt das Sine Out Signal am Lock-In Amplifier."""
    try:
        send_lockin_command("SLVL", 0.0)
        messagebox.showinfo(auto_tr("Lock-In Amplifier"), auto_tr("Sine Out set to 0.0 V (OFF)."))
    except Exception as e:
        messagebox.showerror("Fehler", f"{e}")


def apply_ref_settings():
    """Wendet Frequenz, Phase und Amplitude des Referenzsignals an."""
    new_freq = read_numeric_entry(entry_freq, "Ref Frequency", 0.001, 102000)
    new_phase = read_numeric_entry(entry_ref_phase, "Ref Phase", -360, 729.99)
    new_ampl = read_numeric_entry(entry_ampl, "Sine Output Amplitude", 0, 5)
    if None in (new_freq, new_phase, new_ampl):
        return

    if messagebox.askyesno("Bestätigung",
                           f"Referenz-Parameter wirklich anpassen?\n\nFrequenz: {new_freq} Hz\nPhase: {new_phase}°\nAmplitude: {new_ampl} V"):
        val_ref_display.config(text=f"{new_freq} Hz")
        if not is_emergency_bypass:
            try:
                send_lockin_command("FREQ", new_freq)
                send_lockin_command("PHAS", new_phase)
                send_lockin_command("SLVL", new_ampl)
            except Exception as e:
                messagebox.showerror("Hardware Fehler", f"Fehler beim Senden: {e}")
                return
        messagebox.showinfo("Lock-In Amplifier", "Referenz-Signal erfolgreich angewendet!")


btn_apply_ref = tk.Button(frame_ref, text="✔ Apply Reference", font=("Consolas", 8, "bold"), bg="#007acc", fg="white",
                          command=apply_ref_settings)
btn_apply_ref.pack(fill="x", pady=(6, 2))

btn_start_lockin = tk.Button(frame_ref, font=("Consolas", 8, "bold"), bg="#2e7d32", fg="white", pady=3,
                             command=lockin_start)
btn_start_lockin.pack(fill="x", pady=(6, 2))
reg_ui(btn_start_lockin, "▶ Start Sine Out")

btn_stop_lockin = tk.Button(frame_ref, font=("Consolas", 8, "bold"), bg="#c62828", fg="white", pady=3,
                            command=lockin_stop)
btn_stop_lockin.pack(fill="x", pady=2)
reg_ui(btn_stop_lockin, "⏹ Stop Sine Out")

# ------------------------------------------
# 5. TAB: OSTECH LASER / TEC CONTROLLER
# ------------------------------------------
tab_laser = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_laser, text="")
reg_ui((main_notebook, tab_laser), "Laser / TEC Controller", "tab_text")

create_laser_control_bar(tab_laser)

lbl_laser_com = tk.Label(tab_laser, text="", bg="#1e1e1e")

ostech_notebook = ttk.Notebook(tab_laser)
ostech_notebook.pack(fill="both", expand=True, padx=5, pady=5)

tab_ostech_main = tk.Frame(ostech_notebook, bg="#1e1e1e")
ostech_notebook.add(tab_ostech_main, text=" Main Display ")

frame_layout_sel = tk.Frame(tab_ostech_main, bg="#1e1e1e")
frame_layout_sel.pack(fill="x", padx=10, pady=5)

lbl_layout_cfg = tk.Label(frame_layout_sel, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc")
lbl_layout_cfg.pack(side="left", padx=5)
reg_ui(lbl_layout_cfg, "Hardware Module Layout:")

combo_layout = ttk.Combobox(frame_layout_sel, values=[
    "(a) Laser driver without TEC controller",
    "(b) Laser driver with one TEC controller",
    "(c) Laser driver with two TEC controllers",
    "(d) Controller for one TEC",
    "(e) Controller for two TECs"
], state="readonly", width=42)
combo_layout.current(1)
combo_layout.pack(side="left", padx=5)

frame_lcd = tk.Frame(tab_ostech_main, bg="#000000", bd=3, relief="sunken")
frame_lcd.pack(fill="x", padx=10, pady=5)

lbl_lcd_main = tk.Label(frame_lcd, text="0.0 mA", font=("Consolas", 26, "bold"), bg="#000000", fg="#00ff00")
lbl_lcd_main.pack(pady=(5, 0))

frame_lcd_grid = tk.Frame(frame_lcd, bg="#000000")
frame_lcd_grid.pack(fill="x", padx=20, pady=10)
frame_lcd_grid.columnconfigure((0, 1, 2, 3), weight=1)

lcd_vars = {}
params_list = [
    "Laser Status", "Mode", "TEC1 Status", "TEC2 Status",
    "LCT", "LCB", "LVA", "TA", "TT", "TCA", "TVA", "TCL",
    "LTA", "CTA", "LTT", "LTCA", "CTT", "CTCA", "Error#", "Interlock"
]

for idx, p in enumerate(params_list):
    r = idx // 4
    c = idx % 4
    lbl_p = tk.Label(frame_lcd_grid, text=f"{p}: --", font=("Consolas", 9, "bold"), bg="#000000", fg="#00ff00",
                     anchor="w")
    lbl_p.grid(row=r, column=c, sticky="ew", padx=5, pady=2)
    lcd_vars[p] = lbl_p


def update_laser_display_mode(event=None):
    """Aktualisiert die angezeigten Parameter anhand des Hardware-Layouts."""
    try:
        mode_str = combo_layout.get()
        if lbl_ov_laser_layout_val.winfo_exists():
            lbl_ov_laser_layout_val.config(text=mode_str)
    except Exception:
        mode_str = ""

    # 1. Entferne vorherige Grid-Zuordnungen
    for k in lcd_vars:
        try:
            if lcd_vars[k].winfo_exists():
                lcd_vars[k].grid_remove()
        except Exception:
            pass

    status = getattr(State, "OSTECH_STATUS", {})
    laser_is_on = bool(getattr(State, "L", False))

    display_values = {
        "Laser Status": "ON" if laser_is_on else "OFF",
        "Mode": "LMDX" if getattr(State, "LMDX", False) else "Local",
        "TEC1 Status": "OK" if status.get("lt_sensor_ok", False) else "ERROR",
        "TEC2 Status": "OK" if status.get("ct_sensor_ok", False) else "ERROR",
        "LCT": f"{getattr(State, 'LCT', 0):.3f} mA",
        "LCB": f"{getattr(State, 'LCA', 0):.3f} mA",
        "LVA": f"{getattr(State, 'LVA', 0):.3f} V",
        "TA": f"{getattr(State, 'XTA', 0):.2f} °C",
        "TT": f"{getattr(State, 'XTT', 0):.2f} °C",
        "TCA": f"{getattr(State, 'XTCA', 0):.3f} mA",
        "TVA": f"{getattr(State, 'XTVA', 0):.3f} V",
        "TCL": f"{getattr(State, 'LTM', 0):.2f} °C",
        "LTA": f"{getattr(State, 'XTA', 0):.2f} °C",
        "CTA": f"{getattr(State, 'XTCA', 0):.3f} mA",
        "LTT": f"{getattr(State, 'XTT', 0):.2f} °C",
        "LTCA": f"{getattr(State, 'XTCA', 0):.3f} mA",
        "CTT": f"{getattr(State, 'GT', 0):.2f} °C",
        "CTCA": f"{getattr(State, 'XTCA', 0):.3f} mA",
        "Error#": "ERROR" if status.get("lc_error", False) else "--",
        "Interlock": "OK" if status.get("interlock_ok", False) else "OPEN",
    }

    # 2. Werte auf LCD-Labels schreiben (abgesichert)
    for name, value in display_values.items():
        if name in lcd_vars:
            try:
                widget = lcd_vars[name]
                if widget.winfo_exists():
                    widget.config(text=f"{name}: {value}")
            except Exception:
                pass

    # 3. Layout-Modus bestimmen
    lca_val = f"{getattr(State, 'LCA', 0):.3f} mA"
    gt_val = f"{getattr(State, 'GT', 0):.2f} °C"

    try:
        if "(a)" in mode_str:
            if lbl_lcd_main.winfo_exists(): lbl_lcd_main.config(text=lca_val)
            if lbl_ov_laser_main_val.winfo_exists(): lbl_ov_laser_main_val.config(text=lca_val)
            active = ["Laser Status", "Mode", "LCT", "LCB", "LVA", "TA", "Error#", "Interlock"]
        elif "(b)" in mode_str:
            if lbl_lcd_main.winfo_exists(): lbl_lcd_main.config(text=lca_val)
            if lbl_ov_laser_main_val.winfo_exists(): lbl_ov_laser_main_val.config(text=lca_val)
            active = ["Laser Status", "TEC1 Status", "LCT", "TA", "LVA", "TT", "Mode", "TCA", "Error#", "Interlock"]
        elif "(c)" in mode_str:
            if lbl_lcd_main.winfo_exists(): lbl_lcd_main.config(text=lca_val)
            if lbl_ov_laser_main_val.winfo_exists(): lbl_ov_laser_main_val.config(text=lca_val)
            active = ["Laser Status", "TEC1 Status", "TEC2 Status", "LCT", "LTA", "LVA", "CTA", "Mode", "Error#",
                      "Interlock"]
        elif "(d)" in mode_str:
            if lbl_lcd_main.winfo_exists(): lbl_lcd_main.config(text=gt_val)
            if lbl_ov_laser_main_val.winfo_exists(): lbl_ov_laser_main_val.config(text=gt_val)
            active = ["TEC1 Status", "TT", "TVA", "TCA", "TCL", "Error#", "Interlock"]
        elif "(e)" in mode_str:
            double_gt = f"{gt_val}   {gt_val}"
            if lbl_lcd_main.winfo_exists(): lbl_lcd_main.config(text=double_gt)
            if lbl_ov_laser_main_val.winfo_exists(): lbl_ov_laser_main_val.config(text=double_gt)
            active = ["TEC1 Status", "TEC2 Status", "LTT", "CTT", "LTCA", "CTCA", "Error#", "Interlock"]
        else:
            active = []
    except Exception:
        active = []

    # 4. Aktive Labels neu anordnen
    for idx, p in enumerate(active):
        if p in lcd_vars:
            try:
                widget = lcd_vars[p]
                if widget.winfo_exists():
                    r = idx // 4
                    c = idx % 4
                    widget.grid(row=r, column=c, sticky="ew", padx=5, pady=2)
            except Exception:
                pass


def check_laser_safety():
    """Entsperrt das Lasermenü nur, wenn alle Sicherheitsabfragen erfüllt sind."""
    if var_goggles.get() and var_interlock.get() and var_beampath.get() and var_warning.get():
        ostech_notebook.tab(tab_ostech_laser, state="normal")
        reg_ui((ostech_notebook, tab_ostech_laser), "Laser Menu", "tab_text")
        lbl_disabled_banner.pack_forget()
        frame_lmenu.pack(fill="both", expand=True, padx=10, pady=10)
        lbl_safety_status.config(text=" SAFE TO OPERATE \nLaser-Menu Unlocked", bg="#2e7d32", fg="#ffffff")
        messagebox.showinfo(auto_tr("Laser Security"),
                            auto_tr("All safety measurements complied. The Laser-Menu is now unlocked."))
    else:
        ostech_notebook.tab(tab_ostech_laser, state=DISABLED)
        reg_ui((ostech_notebook, tab_ostech_laser), "🔒 Laser Menu (Locked)", "tab_text")
        frame_lmenu.pack_forget()
        lbl_disabled_banner.pack(fill="both", expand=True, padx=20, pady=40)
        lbl_safety_status.config(text=" ⚠️ INTERLOCKED ⚠️ \nChecklist Incomplete", bg="#c62828", fg="#ffffff")


# Laser Sicherheitskontrolle
var_goggles = tk.BooleanVar(value=False)
var_interlock = tk.BooleanVar(value=False)
var_beampath = tk.BooleanVar(value=False)
var_warning = tk.BooleanVar(value=False)


frame_safety = tk.LabelFrame(tab_ostech_main, text=" Laser Security Checklist ", font=("Consolas", 9, "bold"),
                             bg="#1e1e1e", fg="#ffaa00", padx=10, pady=8)
frame_safety.pack(fill="x", padx=10, pady=10)

chk_goggles = tk.Checkbutton(frame_safety, text=" Protective googles on?", variable=var_goggles,
                             command=check_laser_safety, bg="#1e1e1e", fg="#ffffff", selectcolor="#2b2b2b",
                             activebackground="#1e1e1e")
chk_goggles.pack(anchor="w", pady=2)

chk_interlock = tk.Checkbutton(frame_safety, text=" Door-Interlock / Hardware-Interlock closed", variable=var_interlock,
                               command=check_laser_safety, bg="#1e1e1e", fg="#ffffff", selectcolor="#2b2b2b",
                               activebackground="#1e1e1e")
chk_interlock.pack(anchor="w", pady=2)

chk_beampath = tk.Checkbutton(frame_safety, text=" Beam path secured", variable=var_beampath,
                              command=check_laser_safety, bg="#1e1e1e", fg="#ffffff", selectcolor="#2b2b2b",
                              activebackground="#1e1e1e")
chk_beampath.pack(anchor="w", pady=2)

chk_warning = tk.Checkbutton(frame_safety, text=" Laser warning light active & emergency shutdown in reach",
                             variable=var_warning, command=check_laser_safety, bg="#1e1e1e", fg="#ffffff",
                             selectcolor="#2b2b2b", activebackground="#1e1e1e")
chk_warning.pack(anchor="w", pady=2)

lbl_safety_status = tk.Label(frame_safety, text=" ⚠️ INTERLOCKED ⚠️ \nChecklist Incomplete",
                             font=("Consolas", 11, "bold"), bg="#c62828", fg="#ffffff", bd=3, relief="ridge", padx=15,
                             pady=8)
lbl_safety_status.pack(fill="x", pady=(10, 0))

# Laser Menü Untertab
tab_ostech_laser = tk.Frame(ostech_notebook, bg="#1e1e1e")
ostech_notebook.add(tab_ostech_laser, text="")
reg_ui((ostech_notebook, tab_ostech_laser), "🔒 Laser Menu (Locked)", "tab_text")
ostech_notebook.tab(tab_ostech_laser, state=DISABLED)

lbl_disabled_banner = tk.Label(tab_ostech_laser,
                               text="🔒 LASER MENU DEACTIVATED\n\nPlease complete the Laser Security Checklist in the 'Main Display' tab to unlock hardware controls.",
                               font=("Consolas", 12, "bold"), bg="#2b2b2b", fg="#ff4444", relief="ridge", bd=2, padx=20,
                               pady=30)
lbl_disabled_banner.pack(fill="both", expand=True, padx=20, pady=40)

frame_lmenu = tk.LabelFrame(tab_ostech_laser, text=" Laser Menu Parameters ", font=("Consolas", 9, "bold"),
                            bg="#1e1e1e", fg="#00ffcc", padx=10, pady=10)
frame_lmenu.columnconfigure((0, 1, 2), weight=1)

tk.Label(frame_lmenu, text="LCT (Laser Current Target - A):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).grid(
    row=0, column=0, sticky="w", pady=2)
entry_lct = tk.Entry(frame_lmenu, font=("Consolas", 9))
entry_lct.insert(0, "3.0")
lct_value = entry_lct.get()
entry_lct.grid(row=1, column=0, sticky="ew", padx=5)

tk.Label(frame_lmenu, text="LCL (Laser Current Limit - A):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).grid(
    row=2, column=0, sticky="w", pady=2)
entry_lcl = tk.Entry(frame_lmenu, font=("Consolas", 9))
entry_lcl.insert(0, "6.300")
lcl_value = float(entry_lcl.get())
entry_lcl.grid(row=3, column=0, sticky="ew", padx=5)

tk.Label(frame_lmenu, text="LVC (Compliance Voltage - V):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).grid(
    row=2, column=1, sticky="w", pady=2)
entry_lvc = tk.Entry(frame_lmenu, font=("Consolas", 9))
entry_lvc.insert(0, "3.00")
lvc_value = float(entry_lvc.get())
entry_lvc.grid(row=3, column=1, sticky="ew", padx=5)

tk.Label(frame_lmenu, text="LCLM (Avg Current Limit - A):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).grid(
    row=4, column=0, sticky="w", pady=2)
entry_lclm = tk.Entry(frame_lmenu, font=("Consolas", 9))
entry_lclm.insert(0, "6.300")
lclm_value = float(entry_lclm.get())
entry_lclm.grid(row=5, column=0, sticky="ew", padx=5)

tk.Label(frame_lmenu, text="LTM (Max Temp Limit - °C):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).grid(row=6,
                                                                                                                column=0,
                                                                                                                sticky="w",
                                                                                                                pady=2)
entry_ltm = tk.Entry(frame_lmenu, font=("Consolas", 9))
entry_ltm.insert(0, "33.0")
ltm_value = float(entry_ltm.get())
entry_ltm.grid(row=7, column=0, sticky="ew", padx=5)

tk.Label(frame_lmenu, text="Modulation Mode:", bg="#1e1e1e", fg="#00ffcc", font=("Consolas", 9, "bold")).grid(row=0,
                                                                                                              column=1,
                                                                                                              sticky="w",
                                                                                                              pady=2)
combo_mod_mode = ttk.Combobox(frame_lmenu, values=["CW Mode (No Mod)", "External Modulation (Analog - LMAX)",
                                                   "External Modulation (Digital - LMDX)",
                                                   "Internal Digital Modulation (LMDI)"], state="readonly")
combo_mod_mode.current(1)
combo_mod_mode.grid(row=1, column=1, sticky="ew", padx=5)

tk.Label(frame_lmenu, text="LMW (Modulation Width - ms):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).grid(row=2,
                                                                                                                  column=2,
                                                                                                                  sticky="w",
                                                                                                                  pady=2)
entry_lmw = tk.Entry(frame_lmenu, font=("Consolas", 9))
entry_lmw.insert(0, "1.000")
lmw_value = float(entry_lmw.get())
entry_lmw.grid(row=3, column=2, sticky="ew", padx=5)

tk.Label(frame_lmenu, text="LMP (Modulation Period - ms):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).grid(
    row=4, column=1, sticky="w", pady=2)
entry_lmp = tk.Entry(frame_lmenu, font=("Consolas", 9))
entry_lmp.insert(0, "2.000")
lmp_value = float(entry_lmp.get())
entry_lmp.grid(row=5, column=1, sticky="ew", padx=5)

tk.Label(frame_lmenu, text="PC (Pulse Count Mode):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).grid(row=0,
                                                                                                            column=2,
                                                                                                            sticky="w",
                                                                                                            pady=2)
combo_pc = ttk.Combobox(frame_lmenu, values=["PC = 0 (Continuous)", "PC = 1 (Single Pulse)", "PC = 2 (Burst of 2)"],
                        state="readonly")
combo_pc.current(0)
combo_pc.grid(row=1, column=2, sticky="ew", padx=5)

chk_lg = tk.Checkbutton(frame_lmenu, text="LG (Gate Option Enabled)", bg="#1e1e1e", fg="#ffffff", selectcolor="#2b2b2b",
                        activebackground="#1e1e1e", activeforeground="#ffffff")
chk_lg.grid(row=5, column=2, sticky="w", padx=5)


def apply_laser_settings():
    """Liest und speichert veränderte Laser-Parameter."""
    values = (
        read_numeric_entry(entry_lct, "LCT", 0, 100),
        Send.send(Send.OSTechS.LCT, lct_value),
        read_numeric_entry(entry_lcl, "LCL", 0, 100),
        Send.send(Send.OSTechS.LCL, lcl_value),
        read_numeric_entry(entry_lvc, "LVC", 0, 100),
        Send.send(Send.OSTechS.LVC, lvc_value),
        read_numeric_entry(entry_lclm, "LCLM", 0, 100),
        Send.send(Send.OSTechS.LCLM, lclm_value),
        read_numeric_entry(entry_ltm, "LTM", -273.15, 200),
        Send.send(Send.OSTechS.LTM, ltm_value),
        read_numeric_entry(entry_lmw, "LMW", 0, 100000),
        Send.send(Send.OSTechS.LMW, lmw_value),
        read_numeric_entry(entry_lmp, "LMP", 0, 100000),
        Send.send(Send.OSTechS.LMP, lmp_value)
    )
    if any(value is None for value in values):
        return
    if messagebox.askyesno("Bestätigung",
                           "Sollen die eingegebenen Laser-Parameter an den Controller übertragen werden?"):
        messagebox.showinfo("Laser Controller", "Laser-Einstellungen erfolgreich aktualisiert.")


def reset_laser_defaults():
    """Setzt alle Laser-Einstellungen auf Standardwerte zurück."""
    if messagebox.askyesno("Reset", "Laser-Parameter auf Werkseinstellungen zurücksetzen?"):
        entry_lct.delete(0, tk.END)
        entry_lct.insert(0, "5.00")
        entry_lcl.delete(0, tk.END)
        entry_lcl.insert(0, "6.300")
        entry_lvc.delete(0, tk.END)
        entry_lvc.insert(0, "3.00")
        entry_lclm.delete(0, tk.END)
        entry_lclm.insert(0, "6.300")
        entry_ltm.delete(0, tk.END)
        entry_ltm.insert(0, "33.0")
        entry_lmw.delete(0, tk.END)
        entry_lmw.insert(0, "1.000")
        entry_lmp.delete(0, tk.END)
        entry_lmp.insert(0, "2.000")
        combo_mod_mode.current(1)
        combo_pc.current(0)
        chk_lg.deselect()
        messagebox.showinfo("Reset", "Laser-Standardwerte wiederhergestellt.")

# Laser Start / Stop Button
btn_laser_toggle = tk.Button(
    frame_lmenu,
    text="⚡ START LASER ⚡",
    font=("Consolas", 12, "bold"),
    bg="#388e3c",
    fg="#ffffff",
    activebackground="#2e7d32",
    activeforeground="#ffffff",
    bd=3,
    relief="raised",
    command=toggle_laser
)
# Positioned across columns 1 and 2 in the laser menu grid
btn_laser_toggle.grid(row=7, column=1, columnspan=2, sticky="ew", padx=5, pady=(10, 5))

frame_laser_btns = tk.Frame(frame_lmenu, bg="#1e1e1e")
frame_laser_btns.grid(row=8, column=0, columnspan=3, pady=15, sticky="ew")

btn_apply_laser = tk.Button(frame_laser_btns, text="✔ Apply Laser Settings", font=("Consolas", 9, "bold"), bg="#007acc",
                            fg="white", command=apply_laser_settings)
btn_apply_laser.pack(side="left", fill="x", expand=True, padx=5)

btn_reset_laser = tk.Button(frame_laser_btns, text="Restore Default Settings", font=("Consolas", 8, "bold"),
                            bg="#c62828", fg="white", command=reset_laser_defaults)
btn_reset_laser.pack(side="right", padx=5)

# TEC Menü
tab_ostech_tec = tk.Frame(ostech_notebook, bg="#1e1e1e")
ostech_notebook.add(tab_ostech_tec, text=" TEC Menu & PID ")

frame_tmenu = tk.LabelFrame(tab_ostech_tec, text=" TEC Settings, PID & Sensor Setup ", font=("Consolas", 9, "bold"),
                            bg="#1e1e1e", fg="#00ffcc", padx=10, pady=10)
frame_tmenu.pack(fill="both", expand=True, padx=10, pady=10)
frame_tmenu.columnconfigure((0, 1, 2), weight=1)

tk.Label(frame_tmenu, text="TLU (Upper Temp Limit - °C):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).grid(row=0,
                                                                                                                  column=0,
                                                                                                                  sticky="w")
entry_tlu = tk.Entry(frame_tmenu, font=("Consolas", 9))
entry_tlu.insert(0, "40.00")
entry_tlu.grid(row=1, column=0, sticky="ew", padx=5)

tk.Label(frame_tmenu, text="TLL (Lower Temp Limit - °C):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).grid(row=2,
                                                                                                                  column=0,
                                                                                                                  sticky="w")
entry_tll = tk.Entry(frame_tmenu, font=("Consolas", 9))
entry_tll.insert(0, "5.00")
entry_tll.grid(row=3, column=0, sticky="ew", padx=5)

chk_tc_auto = tk.Checkbutton(frame_tmenu, text="TC Auto On (Activate within limits)", bg="#1e1e1e", fg="#ffffff",
                             selectcolor="#2b2b2b")
chk_tc_auto.grid(row=4, column=0, sticky="w", pady=5)

frame_pid = tk.LabelFrame(frame_tmenu, text=" PID Parameters ", font=("Consolas", 8, "bold"), bg="#1e1e1e",
                          fg="#ffaa00", padx=5, pady=5)
frame_pid.grid(row=0, column=1, rowspan=5, sticky="nsew", padx=5)

tk.Label(frame_pid, text="Tk (Proportional):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).pack(anchor="w")
entry_tk = tk.Entry(frame_pid, font=("Consolas", 9))
entry_tk.insert(0, "2.000")
entry_tk.pack(fill="x", pady=2)

tk.Label(frame_pid, text="Tn (Integral - s):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).pack(anchor="w")
entry_tn = tk.Entry(frame_pid, font=("Consolas", 9))
entry_tn.insert(0, "50.000")
entry_tn.pack(fill="x", pady=2)

tk.Label(frame_pid, text="Tv (Derivative - s):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).pack(anchor="w")
entry_tv = tk.Entry(frame_pid, font=("Consolas", 9))
entry_tv.insert(0, "1.000")
entry_tv.pack(fill="x", pady=2)

frame_sens = tk.LabelFrame(frame_tmenu, text=" Sensor Selection ", font=("Consolas", 8, "bold"), bg="#1e1e1e",
                           fg="#ffaa00", padx=5, pady=5)
frame_sens.grid(row=0, column=2, rowspan=5, sticky="nsew", padx=5)

tk.Label(frame_sens, text="Select Sensor:", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).pack(anchor="w")
combo_sensor = ttk.Combobox(frame_sens, values=["NTC 10k", "Pt100", "Pt1000", "Custom"], state="readonly")
combo_sensor.current(0)
combo_sensor.pack(fill="x", pady=2)

tk.Label(frame_sens, text="Model Type:", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).pack(anchor="w", pady=(5, 0))
combo_sens_model = ttk.Combobox(frame_sens, values=["Steinhart-Hart", "Polynomial"], state="readonly")
combo_sens_model.current(0)
combo_sens_model.pack(fill="x", pady=2)


def apply_tec_settings():
    """Wendet die veränderten TEC- und PID-Einstellungswerte an."""
    values = (
        read_numeric_entry(entry_tlu, "TLU", -273.15, 500),
        read_numeric_entry(entry_tll, "TLL", -273.15, 500),
        read_numeric_entry(entry_tk, "Tk", 0, 100000),
        read_numeric_entry(entry_tn, "Tn", 0, 100000),
        read_numeric_entry(entry_tv, "Tv", 0, 100000),
    )
    if any(value is None for value in values):
        return
    if values[1] >= values[0]:
        message = "TLL muss kleiner als TLU sein."
        Log.Log("Gui", "TEC", "Error", "Input Error", message, "TEC limits")
        messagebox.showerror("Input Error", message)
        return
    if messagebox.askyesno("Bestätigung", "Neue TEC-Limits, PID-Werte und Sensorparameter anwenden?"):
        messagebox.showinfo("TEC Controller", "TEC-Parameter wurden übernommen.")


def reset_tec_defaults():
    """Setzt TEC-Parameter zurück."""
    if messagebox.askyesno("Reset", "TEC-Parameter auf Werkseinstellungen zurücksetzen?"):
        entry_tlu.delete(0, tk.END)
        entry_tlu.insert(0, "40.00")
        entry_tll.delete(0, tk.END)
        entry_tll.insert(0, "5.00")
        entry_tk.delete(0, tk.END)
        entry_tk.insert(0, "2.000")
        entry_tn.delete(0, tk.END)
        entry_tn.insert(0, "50.000")
        entry_tv.delete(0, tk.END)
        entry_tv.insert(0, "1.000")
        combo_sensor.current(0)
        combo_sens_model.current(0)
        chk_tc_auto.deselect()
        messagebox.showinfo("Reset", "TEC-Standardwerte wiederhergestellt.")


frame_tec_btns = tk.Frame(frame_tmenu, bg="#1e1e1e")
frame_tec_btns.grid(row=5, column=0, columnspan=3, pady=10, sticky="ew")

btn_apply_tec = tk.Button(frame_tec_btns, text="✔ Apply TEC & PID Settings", font=("Consolas", 9, "bold"), bg="#007acc",
                          fg="white", command=apply_tec_settings)
btn_apply_tec.pack(side="left", fill="x", expand=True, padx=5)

btn_reset_tec = tk.Button(frame_tec_btns, text="Restore Default Settings", font=("Consolas", 8, "bold"), bg="#c62828",
                          fg="white", command=reset_tec_defaults)
btn_reset_tec.pack(side="right", padx=5)

# Device Menu Untertab
tab_ostech_dev = tk.Frame(ostech_notebook, bg="#1e1e1e")
ostech_notebook.add(tab_ostech_dev, text=" Device Menu ")

frame_dmenu = tk.LabelFrame(tab_ostech_dev, text=" Device System Menu ", font=("Consolas", 9, "bold"), bg="#1e1e1e",
                            fg="#00ffcc", padx=10, pady=10)
frame_dmenu.pack(fill="both", expand=True, padx=10, pady=10)

chk_ext_start = tk.Checkbutton(frame_dmenu, text="External Control on Start", bg="#1e1e1e", fg="#ffffff",
                               selectcolor="#2b2b2b")
chk_ext_start.pack(anchor="w", pady=3)

chk_pilot = tk.Checkbutton(frame_dmenu, text="Pilot Laser Active", bg="#1e1e1e", fg="#ffffff", selectcolor="#2b2b2b")
chk_pilot.pack(anchor="w", pady=3)

frame_pilot_int = tk.Frame(frame_dmenu, bg="#1e1e1e")
frame_pilot_int.pack(fill="x", pady=5)
tk.Label(frame_pilot_int, text="Pilot Laser Intensity (0...16):", bg="#1e1e1e", fg="#aaaaaa",
         font=("Consolas", 8)).pack(side="left")
spin_pilot = tk.Spinbox(frame_pilot_int, from_=0, to=16, width=5, font=("Consolas", 9))
spin_pilot.pack(side="left", padx=10)

frame_gfd = tk.Frame(frame_dmenu, bg="#1e1e1e")
frame_gfd.pack(fill="x", pady=5)
tk.Label(frame_gfd, text="GFD (Default Fan Voltage - V):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).pack(
    side="left")
entry_gfd = tk.Entry(frame_gfd, font=("Consolas", 9), width=8)
entry_gfd.insert(0, "12.0 V")
entry_gfd.pack(side="left", padx=10)


def apply_device_settings():
    """Wendet System- und Geräte-Optionen an."""
    pilot_intensity = read_integer_entry(spin_pilot, "Pilot Laser Intensity", 0, 16)
    fan_voltage = read_numeric_entry(entry_gfd, "GFD", 0, 100)
    if pilot_intensity is None or fan_voltage is None:
        return
    if messagebox.askyesno("Bestätigung", "Gerätesystem-Einstellungen anwenden?"):
        messagebox.showinfo("System Settings", "System-Einstellungen übernommen.")


def reset_device_defaults():
    """Setzt Geräteeinstellungen zurück."""
    if messagebox.askyesno("Reset", "Gerätesystem-Einstellungen zurücksetzen?"):
        chk_ext_start.deselect()
        chk_pilot.deselect()
        spin_pilot.delete(0, tk.END)
        spin_pilot.insert(0, "0")
        entry_gfd.delete(0, tk.END)
        entry_gfd.insert(0, "12.0 V")
        messagebox.showinfo("Reset", "System-Standardwerte wiederhergestellt.")


frame_dev_btns = tk.Frame(frame_dmenu, bg="#1e1e1e")
frame_dev_btns.pack(fill="x", pady=15)

btn_apply_dev = tk.Button(frame_dev_btns, text="✔ Apply Device Settings", font=("Consolas", 9, "bold"), bg="#007acc",
                          fg="white", command=apply_device_settings)
btn_apply_dev.pack(side="left", padx=5)

btn_reset_def = tk.Button(frame_dev_btns, text="Restore Default Settings", font=("Consolas", 8, "bold"), bg="#c62828",
                          fg="white", command=reset_device_defaults)
btn_reset_def.pack(side="left", padx=5)


# ------------------------------------------
# HELPER FOR EXPLORER TREEVIEW
# ------------------------------------------
def build_file_tree(tree_widget, root_dir):
    """Baut eine Ordnerstruktur im Baumdiagramm für Datei-Explorer auf."""
    tree_widget.delete(*tree_widget.get_children())
    root_node = tree_widget.insert("", "end", text=f" 📂 {os.path.basename(os.path.abspath(root_dir))}", open=True,
                                   values=[os.path.abspath(root_dir)])

    def populate(parent_node, path):
        try:
            entries = sorted(os.listdir(path))
            for entry in entries:
                if entry.startswith('.'):
                    continue
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    node = tree_widget.insert(parent_node, "end", text=f" 📁 {entry}", open=False, values=[full_path])
                    populate(node, full_path)
                else:
                    ext = os.path.splitext(entry)[1].lower()
                    icon = "📄"
                    if ext in ['.py', '.pyw']:
                        icon = "🐍"
                    elif ext in ['.txt', '.log', '.csv']:
                        icon = "📝"
                    elif ext in ['.json']:
                        icon = "⚙️"
                    tree_widget.insert(parent_node, "end", text=f" {icon} {entry}", values=[full_path])
        except PermissionError:
            pass

    populate(root_node, os.path.abspath(root_dir))


build_file_tree(tree_logs_main, LOG_DIR)
build_file_tree(tree_stats, LOG_DIR)

# ------------------------------------------
# 6. TAB: HELP
# ------------------------------------------
tab_help = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_help, text="")
reg_ui((main_notebook, tab_help), "Help", "tab_text")

lbl_help_title = tk.Label(tab_help, font=("Consolas", 12, "bold"), bg="#1e1e1e", fg="#00ffcc")
lbl_help_title.pack(pady=20)
reg_ui(lbl_help_title, "Help & User Guide")

txt_help = tk.Text(tab_help, bg="#252526", fg="#ffffff", font=("Segoe UI", 10), wrap="word", padx=15, pady=15)
txt_help.pack(fill="both", expand=True, padx=20, pady=10)

help_content = """PAMO System Documentation & Instructions:

1. Overview Tab:
   - Live hardware status indicators and previews for Lock-in Amplifier and Laser Controller.

2. Experiment Tab:
   - Configure parameter sweeps for frequency (Start and End Frequency).
   - View results, process raw measurement data and run delta phase calculations.

3. Logs Tab:
   - Monitor real-time logs, insert manual user notes, and import/export CSV measurement records.

4. Lock-In Amplifier Tab:
   - Configure input channels, sensitivities, filter slopes, and reference oscillator parameters.

5. Laser / TEC Controller Tab:
   - Requires safety checklist verification before unlocking control parameters.
   - Adjust PID loop settings, sensor types, and current limits.

6. Settings Tab:
   - Manage application language and the layout.
"""
txt_help.insert("1.0", help_content)
txt_help.config(state="disabled")

# ------------------------------------------
# 7. TAB: SETTINGS & THEME ENGINE
# ------------------------------------------
# Hier können Sprache und Erscheinungsbild der Anwendung angepasst werden.
# Das verbessert Benutzerkomfort und Lesbarkeit bei längerem Betrieb.
tab_settings = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_settings, text="")
reg_ui((main_notebook, tab_settings), "Settings", "tab_text")

settings_notebook = ttk.Notebook(tab_settings)
settings_notebook.pack(fill="both", expand=True, padx=10, pady=10)

sub_tab_lang = tk.Frame(settings_notebook, bg="#252526")
settings_notebook.add(sub_tab_lang, text="")
reg_ui((settings_notebook, sub_tab_lang), "Language", "tab_text")

lbl_lang_sel = tk.Label(sub_tab_lang, font=("Consolas", 10, "bold"), bg="#252526", fg="#ffffff")
lbl_lang_sel.pack(pady=15)
reg_ui(lbl_lang_sel, "Select Application Language:")

lang_frame = tk.Frame(sub_tab_lang, bg="#252526")
lang_frame.pack()

languages = [("English", "en"), ("Deutsch", "de"), ("Español", "es"), ("Français", "fr")]
for name, code in languages:
    b = tk.Button(lang_frame, text=name, width=12, bg="#3c3f41", fg="white", command=lambda c=code: change_language(c))
    b.pack(pady=3)

sub_tab_theme = tk.Frame(settings_notebook, bg="#252526")
settings_notebook.add(sub_tab_theme, text="")
reg_ui((settings_notebook, sub_tab_theme), "Theme / Layout", "tab_text")


def apply_theme(theme_name):
    # Schaltet zwischen Dark- und Light-Theme um und passt die Farben aller Widgets an.
    try:
        if theme_name == "light":
            bg_main = "#f0f0f0"
            bg_card = "#ffffff"
            fg_text = "#000000"
            btn_bg = "#e0e0e0"
            tab_bg = "#d6d6d6"
            display_bg = "#e8f5e9"
            display_fg = "#1b5e20"
            canvas_bg = "#e0e0e0"
            lf_title_fg = "#005588"

            style.configure("TNotebook", background=bg_main, borderwidth=0)
            style.configure("TNotebook.Tab", background=tab_bg, foreground=fg_text, padding=[10, 6],
                            font=('Consolas', 10, 'bold'))
            style.map("TNotebook.Tab", background=[("selected", "#007acc")], foreground=[("selected", "#ffffff")])
            style.configure("TCombobox", fieldbackground="#ffffff", background="#e0e0e0", foreground="#000000")
            style.map("TCombobox", fieldbackground=[("readonly", "#ffffff")], foreground=[("readonly", "#000000")])
            style.configure("TEntry", fieldbackground="#ffffff", foreground="#000000")
            style.configure("TLabelframe", background=bg_main, borderwidth=1)
            style.configure("TLabelframe.Label", background=bg_main, foreground=lf_title_fg,
                            font=('Consolas', 10, 'bold'))

        else:
            bg_main = "#1e1e1e"
            bg_card = "#2b2b2b"
            fg_text = "#ffffff"
            btn_bg = "#3c3f41"
            tab_bg = "#3c3f41"
            display_bg = "#000000"
            display_fg = "#00ff00"
            canvas_bg = "#000000"
            lf_title_fg = "#00ffcc"

            style.configure("TNotebook", background="#2b2b2b", borderwidth=0)
            style.configure("TNotebook.Tab", background=tab_bg, foreground=fg_text, padding=[10, 6],
                            font=('Consolas', 10, 'bold'))
            style.map("TNotebook.Tab", background=[("selected", "#007acc")], foreground=[("selected", "#ffffff")])
            style.configure("TCombobox", fieldbackground="#2b2b2b", background="#3c3f41", foreground="#ffffff")
            style.map("TCombobox", fieldbackground=[("readonly", "#2b2b2b")], foreground=[("readonly", "#ffffff")])
            style.configure("TEntry", fieldbackground="#2b2b2b", foreground="#ffffff")
            style.configure("TLabelframe", background="#1e1e1e", borderwidth=1)
            style.configure("TLabelframe.Label", background="#1e1e1e", foreground=lf_title_fg,
                            font=('Consolas', 10, 'bold'))

        root.configure(bg=bg_card)

        def force_widget_colors(widget):
            is_display = False
            is_protected_signal = False

            try:
                if widget in (val_ch1_label, val_ch1_unit_label, val_ch2_label, val_ch2_unit_label, val_ref_display,
                              lbl_lcd_main) or widget in lcd_vars.values():
                    is_display = True
                elif widget in (btn_start_lockin, btn_stop_lockin, btn_reset_def, btn_reset_laser, btn_reset_tec,
                                lbl_safety_status, lbl_disabled_banner, lbl_overload_ch1, lbl_overload_ch2):
                    is_protected_signal = True
                elif any(keyword in str(widget).lower() for keyword in
                         ("start", "stop", "interlock", "laser_on", "laser_off")):
                    is_protected_signal = True
            except Exception:
                pass

            if is_protected_signal:
                try:
                    for child in widget.winfo_children():
                        force_widget_colors(child)
                except Exception:
                    pass
                return

            if is_display:
                target_bg = display_bg
                target_fg = display_fg
            else:
                target_bg = bg_main
                target_fg = fg_text

            for bg_attr in ("bg", "background", "activebackground", "highlightbackground", "readonlybackground",
                            "selectcolor"):
                try:
                    widget[bg_attr] = target_bg
                except Exception:
                    pass

            for fg_attr in ("fg", "foreground", "activeforeground", "disabledforeground"):
                try:
                    widget[fg_attr] = target_fg
                except Exception:
                    pass

            try:
                if widget.winfo_class() == "Button":
                    widget.configure(bg=btn_bg)
            except Exception:
                pass

            try:
                if widget.winfo_class() in ("Entry", "Spinbox"):
                    widget.configure(fg="#000000" if theme_name == "light" else "#ffffff",
                                     bg="#ffffff" if theme_name == "light" else "#2b2b2b",
                                     insertbackground="#000000" if theme_name == "light" else "#ffffff")
            except Exception:
                pass

            try:
                if widget.winfo_class() == "Canvas":
                    widget.configure(bg=canvas_bg)
            except Exception:
                pass

            try:
                for child in widget.winfo_children():
                    force_widget_colors(child)
            except Exception:
                pass

        force_widget_colors(root)
    except Exception as e:
        GUIErrorHandler.handle_exception(e, context="Theme Umschalten")


lbl_theme_sel = tk.Label(sub_tab_theme, text="Select Layout Theme:", font=("Consolas", 10, "bold"), bg="#252526",
                         fg="#ffffff")
lbl_theme_sel.pack(pady=15)

btn_dark = tk.Button(sub_tab_theme, text="Dark Mode", width=15, bg="#3c3f41", fg="white",
                     command=lambda: apply_theme("dark"))
btn_dark.pack(pady=4)

btn_light = tk.Button(sub_tab_theme, text="Light Mode", width=15, bg="#e0e0e0", fg="black",
                      command=lambda: apply_theme("light"))
btn_light.pack(pady=4)


def log_gui_click(event):
    # Protokolliert jeden Button- oder Checkbutton-Klick in das Log-System.
    widget = event.widget
    try:
        label = widget.cget("text").strip()
    except tk.TclError:
        label = widget.winfo_class()
    if not label:
        label = widget.winfo_class()
    Log.Log("Gui", "Button", "Info", "Button clicked", label)


def register_button_logging(widget):
    # Durchläuft rekursiv alle Widgets und registriert Klick-Handler für Buttons.
    for child in widget.winfo_children():
        if child.winfo_class() in ("Button", "Checkbutton"):
            child.bind("<ButtonRelease-1>", log_gui_click, add="+")
        register_button_logging(child)


register_button_logging(root)

check_laser_safety()
if __name__ == "__main__":
    root.mainloop()




#ValueOfLCA = Send.read(Send.OSTechG.LCA)
# actual current
#Send.set(Send.OSTechS.GFD, 12.0)
#   Fan voltage

#   Beispiele wie man Abfagen machen


#   SR830

#   Werte Lesen

#import Send

#x_value = Send.read(Send.SR830G.OUTP_X)
#y_value = Send.read(Send.SR830G.OUTP_Y)
#theta = Send.read(Send.SR830G.OUTP_THETA)

#   Werte Setzen

#import Send

#Send.set(Send.SR830S.FREQ, 1000.0)   # Frequenz
#Send.set(Send.SR830S.PHAS, 30.0)     # Phase
#Send.set(Send.SR830S.SLVL, 1.5)      # Amplitude





#   OSTECH

#   Werte lesen

#import Send

#current = Send.read(Send.OSTechG.LCA)
#voltage = Send.read(Send.OSTechG.LVA)
#status = Send.read(Send.OSTechG.GS)


#   Werte Setzen

#import Send

#Send.set(Send.OSTechS.LCL, 6.3)   # Laser Current Limit
#Send.set(Send.OSTechS.LTM, 33.0) # Max Temperature
#Send.set(Send.OSTechS.GFD, 12.0) # Fan voltage
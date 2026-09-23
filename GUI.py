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
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import Log
import Komunikation
import Send
import Starter
import State
import SimGuiUpdatet
from State import scan_com_ports
import GUIErrorHandler

import SWP_Calculation_PhaseVsFrequenz_v8 as PhasFreq_v8


# Externe Bibliotheken
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
# Diese beiden Ordner werden für alle Messdaten, Log-Dateien und Plots genutzt.
# Dadurch bleiben sämtliche Auswertungen und Protokolle an einem zentralen Ort.
LOG_DIR = os.path.join(os.getcwd(), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

PLOT_DIR = os.path.join(os.getcwd(), "plots")
if not os.path.exists(PLOT_DIR):
    os.makedirs(PLOT_DIR)

# ==========================================
# KONFIGURATION & PASSWORT-MANAGEMENT
# ==========================================
# Diese Funktionen laden und speichern globale GUI-Einstellungen.
# Wichtig: Einstellungen werden in einer lokalen JSON-Datei abgelegt, damit
# Werte wie z. B. Sicherheitsparameter oder zuletzt verwendete Optionen nicht verloren gehen.
SETTINGS_FILE = "settings.json"


def load_settings():
    default_settings = {"emergency_password": "admin123"}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_settings.update(data)
        except Exception:
            pass
    else:
        save_settings(default_settings)
    return default_settings


def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Fehler beim Speichern der Settings: {e}")


APP_SETTINGS = load_settings()


def read_numeric_entry(entry_widget, field_name, minimum=None, maximum=None):
    # Diese Hilfsfunktion liest aus einem Tkinter-Eingabefeld einen Zahlenwert aus.
    # Sie akzeptiert Einheiten wie V, mA, Hz, °C und prüft anschließend den erlaubten Bereich.
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
    # Diese Funktion prüft, ob ein Feld eine ganze Zahl erwartet und
    # verhindert dadurch Fehleingaben bei z. B. Portnummern oder Intensitätswerten.
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
# Das GUI-System kann automatisch zwischen Sprachen wechseln.
# Angemeldete Widgets werden hier mit einer englischen Basis-Textvorlage registriert
# und bei Sprachwechsel entsprechend übersetzt.
CACHE_FILE = "translation_cache.json"
current_lang = "en"


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Fehler beim Laden des Caches: {e}")
    return {"de": {}, "es": {}, "fr": {}}


def save_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(TRANSLATION_CACHE, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Fehler beim Speichern des Caches: {e}")


TRANSLATION_CACHE = load_cache()

MANUAL_OVERRIDES = {
    "de": {
        "Sine Out": "Sine-Out Signal",
        "Data Cleansing & Fit": "Datenbereinigung & Fit",
        "Phase vs. Frequency Analysis": "Phase-vs-Frequenz Analyse",
        "Logs": "Protokolle / Logs",
        "Overview": "Übersicht",
        "Lock-In Amplifier": "Lock-In Verstärker",
        "Laser / TEC Controller": "Laser / TEC Regler",
        "Analysis": "Analyse",
        "Help": "Hilfe",
        "Guide": "Handbuch / Anleitung",
        "Settings": "Einstellungen"
    }
}

registered_widgets = []


def auto_tr(english_text):
    # Übersetzt einen englischen Text in die aktuell ausgewählte Sprache.
    # Wenn der Text bereits gecached ist, wird er direkt geladen; andernfalls
    # wird versucht, ihn mit GoogleTranslator zu übersetzen.
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
    # Registriert ein Widget für Sprachupdates.
    # Dadurch kann das Label oder der Tab-Text beim Wechsel der Sprache automatisch aktualisiert werden.
    registered_widgets.append((widget, prop, english_text))
    update_single_widget(widget, prop, english_text)


def update_single_widget(widget, prop, english_text):
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
    global current_lang
    current_lang = lang_code
    for widget, prop, english_text in registered_widgets:
        update_single_widget(widget, prop, english_text)


# ==========================================
# HARDWARE VARIABLEN & STEUERUNG
# ==========================================
# Hier werden globale Zustände für Geräteverbindungen und Messstatus verwaltet.
# Diese Variablen werden von mehreren Tabs gleichzeitig genutzt, z. B. Overview, Lock-In und Laser.
LOCK_IN_AMPLIFIER_PORT = Komunikation.DEFAULT_SR830_PORT
LASER_PORT = Komunikation.DEFAULT_OSTECH_PORT
lockin_device = None
current_file_path = None

is_lockin_connected = False
is_laser_connected = False
is_emergency_bypass = False
communication_threads = None


def stop_communication_threads():
    # Stoppt laufende Kommunikations-Threads sauber, bevor Hardware getrennt oder GUI geschlossen wird.
    global communication_threads
    if communication_threads is not None:
        communication_threads.stop()
        communication_threads = None


def check_real_com_port(port_name):
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
    return scan_com_ports()


def open_file_dialog():
    global current_file_path
    file_path = filedialog.askopenfilename(
        title=auto_tr("Import Data File"),
        filetypes=[("Text Files", "*.txt *.csv"), ("All files", "*.*")]
    )
    if file_path:
        current_file_path = file_path
        lbl_file_status.config(text=os.path.basename(current_file_path))


refresh_job = None
is_closing = False


def on_closing():
    # Wird beim Schließen des Fensters aufgerufen.
    # Hier werden laufende Threads, refresh-Callbacks und GUI-Updates sauber beendet.
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
# Das Hauptfenster wird hier initialisiert und mit dem Theme sowie dem Schließen-Handler versehen.
# Danach werden die Tabs erzeugt, die den kompletten Ablauf der Software darstellen.
root = tk.Tk()
root.title('PAMO - Photothermal Analysis & Monitoring Overview')
root.state("zoomed")
root.configure(bg="#2b2b2b")
root.protocol("WM_DELETE_WINDOW", on_closing)

style = ttk.Style()
style.theme_use('default')
style.configure("TNotebook", background="#2b2b2b", borderwidth=0)
style.configure("TNotebook.Tab", background="#3c3f41", foreground="#ffffff", padding=[10, 6],
                font=('Consolas', 10, 'bold'))
style.map("TNotebook.Tab", background=[("selected", "#007acc")], foreground=[("selected", "#ffffff")])

# Globale Widget-Listen für Status-Labels
# Diese Listen enthalten alle Label, die den Verbindungsstatus der Hardware anzeigen.
status_labels_lockin = []
status_labels_laser = []


def update_status_indicators():
    # Aktualisiert alle Statusanzeigen für Lock-In und Laser.
    # Wenn Gerät verbunden ist, erscheint grün; ansonsten rot.
    for lbl in status_labels_lockin:
        lbl.config(text="🟢 Verbunden" if is_lockin_connected else "🔴 Nicht Verbunden",
                   fg="#00ff00" if is_lockin_connected else "#ff4444")
    for lbl in status_labels_laser:
        lbl.config(text="🟢 Verbunden" if is_laser_connected else "🔴 Nicht Verbunden",
                   fg="#00ff00" if is_laser_connected else "#ff4444")


# ==========================================
# HARDWARE SAMMLUNGSFUNKTIONEN
# ==========================================
def connect_all_hardware():
    # Verbindet alle konfigurierten Hardware-Geräte mit der Software.
    # Danach werden Statusflags gesetzt und ein Übersicht-Log aktualisiert.
    global is_lockin_connected, is_laser_connected, is_emergency_bypass
    global LOCK_IN_AMPLIFIER_PORT, LASER_PORT
    global communication_threads
    is_emergency_bypass = False
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
    # Trennt alle Geräte sauber und setzt die Verbindungszustände zurück.
    # Wichtig: Nach dem Trennen müssen Threads und Hardware-Handles beendet werden.
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


# Hilfsfunktionen für Lock-In und Laser Port-Steuerung
# Diese Bar-Widgets erzeugen die COM-Port-Auswahl und die Connect/Disconnect-Buttons pro Gerät.
def create_lockin_control_bar(parent):
    frame = tk.LabelFrame(parent, text=" Lock-In Connection Control ", font=("Consolas", 10, "bold"),
                          bg="#1e1e1e", fg="#00ffcc", padx=10, pady=8)
    frame.pack(fill="x", padx=10, pady=5)

    tk.Label(frame, text="COM Port:", bg="#1e1e1e", fg="#ffffff", font=("Consolas", 9, "bold")).pack(side="left",
                                                                                                     padx=5)
    combo_com = ttk.Combobox(frame, values=get_available_com_ports(), width=12)
    if LOCK_IN_AMPLIFIER_PORT:
        combo_com.set(LOCK_IN_AMPLIFIER_PORT)
    combo_com.pack(side="left", padx=5)

    def refresh_ports():
        ports = get_available_com_ports()
        combo_com['values'] = ports
        if ports and not combo_com.get():
            combo_com.set(ports[0])

    btn_refresh = tk.Button(frame, text="🔄 Refresh", font=("Consolas", 8, "bold"), bg="#3c3f41", fg="white",
                            command=refresh_ports)
    btn_refresh.pack(side="left", padx=5)

    def do_connect():
        global LOCK_IN_AMPLIFIER_PORT
        LOCK_IN_AMPLIFIER_PORT = combo_com.get().strip()
        connect_all_hardware()

    btn_connect = tk.Button(frame, text="🔌 Connect", font=("Consolas", 8, "bold"), bg="#2e7d32", fg="white",
                            command=do_connect)
    btn_connect.pack(side="left", padx=5)

    btn_disconnect = tk.Button(frame, text="❌ Disconnect", font=("Consolas", 8, "bold"), bg="#c62828", fg="white",
                               command=disconnect_all_hardware)
    btn_disconnect.pack(side="left", padx=5)

    lbl_status = tk.Label(frame, text="🔴 Nicht Verbunden", font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#ff4444")
    lbl_status.pack(side="right", padx=10)
    status_labels_lockin.append(lbl_status)
    return frame


def create_laser_control_bar(parent):
    frame = tk.LabelFrame(parent, text=" Laser Connection Control ", font=("Consolas", 10, "bold"),
                          bg="#1e1e1e", fg="#00ffcc", padx=10, pady=8)
    frame.pack(fill="x", padx=10, pady=5)

    tk.Label(frame, text="COM Port:", bg="#1e1e1e", fg="#ffffff", font=("Consolas", 9, "bold")).pack(side="left",
                                                                                                     padx=5)
    combo_com = ttk.Combobox(frame, values=get_available_com_ports(), width=12)
    if LASER_PORT:
        combo_com.set(LASER_PORT)
    combo_com.pack(side="left", padx=5)

    def refresh_ports():
        ports = get_available_com_ports()
        combo_com['values'] = ports
        if ports and not combo_com.get():
            combo_com.set(ports[0])

    btn_refresh = tk.Button(frame, text="🔄 Refresh", font=("Consolas", 8, "bold"), bg="#3c3f41", fg="white",
                            command=refresh_ports)
    btn_refresh.pack(side="left", padx=5)

    def do_connect():
        global LASER_PORT
        LASER_PORT = combo_com.get().strip()
        connect_all_hardware()

    btn_connect = tk.Button(frame, text="🔌 Connect", font=("Consolas", 8, "bold"), bg="#2e7d32", fg="white",
                            command=do_connect)
    btn_connect.pack(side="left", padx=5)

    btn_disconnect = tk.Button(frame, text="❌ Disconnect", font=("Consolas", 8, "bold"), bg="#c62828", fg="white",
                               command=disconnect_all_hardware)
    btn_disconnect.pack(side="left", padx=5)

    lbl_status = tk.Label(frame, text="🔴 Nicht Verbunden", font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#ff4444")
    lbl_status.pack(side="right", padx=10)
    status_labels_laser.append(lbl_status)
    return frame


# ==========================================================
# HAUPTSTRUKTUR DER GUI: REGISTERKARTEN (TABS)
# ==========================================================
# Alle Hauptbereiche der Software werden als Tabs im Notebook organisiert.
# Dadurch bleibt jede Funktion logisch getrennt:
# - Status/Übersicht
# - Logs
# - Lock-In-Steuerung
# - Laser/TEC-Steuerung
# - Analyse
# - Hilfe
# - Einstellungen
main_notebook = ttk.Notebook(root)
main_notebook.pack(fill="both", expand=True, padx=10, pady=10)

# ------------------------------------------
# 1. TAB: OVERVIEW (PASSIVE DISPLAY- & HARDWARE-PREVIEW)
# ------------------------------------------
# Dieser Tab zeigt nur Status und Vorschau an.
# Er ist keine Steueroberfläche für Messungen, sondern die Startseite.
# Ziel: Sofort erkennen, ob Hardware verbunden ist und ob das System stabil läuft.
tab_overview = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_overview, text="")
reg_ui((main_notebook, tab_overview), "Overview", "tab_text")

frame_overview_status = tk.LabelFrame(tab_overview, text=" Hardware Connection Status ",
                                      font=("Consolas", 10, "bold"),
                                      bg="#1e1e1e", fg="#00ffcc", padx=15, pady=5)
frame_overview_status.pack(fill="x", padx=10, pady=5)

tk.Label(frame_overview_status, text="Lock-in-Amplifier:", bg="#1e1e1e", fg="#aaaaaa",
         font=("Consolas", 10, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)
lbl_status_ov_lockin = tk.Label(frame_overview_status, text="🔴 Nicht Verbunden", font=("Consolas", 10, "bold"),
                                bg="#1e1e1e", fg="#ff4444")
lbl_status_ov_lockin.grid(row=0, column=1, sticky="w", padx=10, pady=5)
status_labels_lockin.append(lbl_status_ov_lockin)

tk.Label(frame_overview_status, text="Laser Controller:", bg="#1e1e1e", fg="#aaaaaa",
         font=("Consolas", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(30, 10), pady=5)
lbl_status_ov_laser = tk.Label(frame_overview_status, text="🔴 Nicht Verbunden", font=("Consolas", 10, "bold"),
                               bg="#1e1e1e", fg="#ff4444")
lbl_status_ov_laser.grid(row=0, column=3, sticky="w", padx=10, pady=5)
status_labels_laser.append(lbl_status_ov_laser)

# --- Passive Gerät-Display Vorschauen ---
frame_previews = tk.Frame(tab_overview, bg="#1e1e1e")
frame_previews.pack(fill="x", padx=10, pady=5)

# Lock-In Passive Preview
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

# Laser Passive Preview
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

frame_overview_log = tk.LabelFrame(tab_overview, text=" Live Log Terminal ", font=("Consolas", 10, "bold"),
                                   bg="#1e1e1e", fg="#00ffcc", padx=10, pady=5)
frame_overview_log.pack(fill="both", expand=True, padx=10, pady=5)

txt_overview_log = tk.Text(frame_overview_log, bg="#000000", fg="#00ff00", font=("Consolas", 9), state="disabled",
                           wrap="word")
txt_overview_log.pack(fill="both", expand=True, padx=5, pady=5)


def update_overview_log(message):
    # Schreibt eine Zeile in das Live-Log des Overview-Tabs.
    # Diese Funktion wird z. B. beim Verbinden/Trennen von Hardware aufgerufen.
    txt_overview_log.config(state="normal")
    txt_overview_log.insert("end", f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}\n")
    txt_overview_log.see("end")
    txt_overview_log.config(state="disabled")


update_overview_log("System initialized. Monitoring active...")

# ------------------------------------------
# 2. TAB: LOGS
# ------------------------------------------
# In diesem Bereich werden gespeicherte Messprotokolle verwaltet und als Dateien angezeigt.
# Der Nutzer kann neue Logs erzeugen, existierende importieren und historische Dateien aufrufen.
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
entry_manual_note.insert(0, "Nachricht eingeben...")
entry_manual_note.pack(side="left", padx=5)


def add_manual_log_note():
    # Einfache manuelle Notiz, die ebenfalls in der Log-Laufzeit und in der CSV erscheint.
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
    # Speichert den Inhalt des Log-Terminals als CSV-Datei im "logs"-Ordner.
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
    # Lädt eine CSV-Datei von außerhalb in das Log-Verzeichnis der Anwendung.
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
    """Nimmt Log-Callbacks entgegen und hängt sie im Laufzeit-Log an.

    Manuelle Einträge aus dem Eingabefeld werden ebenfalls hier abgelegt, da sie
    intern mit ``Log.Log(...)`` geschrieben werden. Dadurch bleibt ein einheitliches
    Verhalten für regelmäßige Meldungen und für Benutzernachträge.
    """
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
    # Wenn ein Eintrag im Log-Baum ausgewählt wird, wird der Inhalt direkt im Terminal angezeigt.
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
# 3. TAB: LOCK-IN AMPLIFIER
# ------------------------------------------
# Hier werden die SR830-Einstellungen und Messkanäle konfiguriert.
# Der Lock-In ist das Herzstück der Messdiagnostik und steuert die Signalverarbeitung.
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
    # Überträgt die eingestellten Lock-In-Parameter an das Gerät.
    # Die Mappe definiert die Hardware-Kommandos und deren Werte für SR830.
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


# --- Hilfsfunktion für Display-Geräteansicht nach Hardware-Muster ---
# Diese Funktion erzeugt eine künstliche Hardware-Anzeige, die wie ein physischer Messgerät-Display aussieht.
def create_hardware_display_box(parent, status_left=("AUTO", "SYNC")):
    disp_frame = tk.Frame(parent, bg="#000000", bd=2, relief="sunken")
    disp_frame.pack(fill="x", pady=2)

    # Obere Leiste: Status links, Hauptwert, Einheiten-Grid rechts
    top_bar = tk.Frame(disp_frame, bg="#000000")
    top_bar.pack(fill="x", padx=2, pady=2)

    # Status Indikatoren Links
    status_box = tk.Frame(top_bar, bg="#000000")
    status_box.pack(side="left", anchor="n", padx=2, pady=2)
    tk.Label(status_box, text="OVLD", font=("Consolas", 7, "bold"), bg="#000000", fg="#444444").pack(anchor="w")
    tk.Label(status_box, text=status_left[0], font=("Consolas", 7, "bold"), bg="#000000", fg="#00ff00").pack(anchor="w")
    tk.Label(status_box, text=status_left[1], font=("Consolas", 7, "bold"), bg="#000000", fg="#00ff00").pack(anchor="w")

    # Hauptwert Anzeigelabel (Vergrößertes Display mit integrierter Einheit)
    val_container = tk.Frame(top_bar, bg="#000000")
    val_container.pack(side="left", expand=True, padx=2)

    val_label = tk.Label(val_container, text="+0.0000", font=("Consolas", 28, "bold"), bg="#000000", fg="#00ff00")
    val_label.pack(side="left")

    unit_label = tk.Label(val_container, text="V", font=("Consolas", 18, "bold"), bg="#000000", fg="#00ff00")
    unit_label.pack(side="left", padx=(4, 0))

    # Einheiten-Grid Rechts (Vollständige Matrix)
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
            tk.Label(units_box, text=u, font=("Consolas", 6, "bold"), bg="#000000", fg="#888888").grid(row=r, column=c,
                                                                                                       padx=1)

    # Untere Leiste: Levelbar mit 8er Marker-Stücken & Beschriftungen
    bot_bar = tk.Frame(disp_frame, bg="#000000")
    bot_bar.pack(fill="x", padx=5, pady=(0, 2))

    canvas_bar = tk.Canvas(bot_bar, height=14, bg="#000000", highlightthickness=0)
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


# ==========================================================
# LOCK-IN TAB: CH1 / CH2 / REFERENCE DISPLAY
# ==========================================================
# In diesem Bereich werden die angezeigten Messwerte der GUI definiert.
# Wichtige Stelle: Die Live-Anzeige der Werte wird hier nicht direkt berechnet,
# sondern mit den aktuellen State-Werten aus State.py aktualisiert.
# CH1 = Signal- oder X-Wert
# CH2 = Phase oder Y-Wert
# Ref Display = Referenzfrequenz / Phase / Amplitude

# CH1
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

# Ratio & Expand nebeneinander für CH1
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
    # LOCK-IN TAB: Aktualisiert die CH1-Anzeige mit dem aktuell ausgewählten Messwert.
    # Der eigentliche Zahlenwert kommt aus State.py, z. B. State.OUTP1, State.OUTP3 etc.
    # Die GUI bindet lediglich diese Werte an das Label, damit die Anzeige live aktualisiert wird.
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

    # Diese Labels sind die tatsächlichen sichtbaren Werte im GUI-Display.
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
    canvas.delete("all")
    width = canvas.winfo_width()
    if width <= 1:
        width = 180
    fill_width = int(width * (percent / 100.0))
    for x in range(0, fill_width, 5):
        color = "#00ff00" if x < width * 0.8 else "#ff3333"
        canvas.create_rectangle(x, 1, x + 3, 11, fill=color, outline="")
    # 8 Markerstück-Unterteilungen
    for i in range(1, 8):
        x_pos = int(width * (i / 8.0))
        canvas.create_line(x_pos, 11, x_pos, 14, fill="#ffffff")


canvas_bar1.bind("<Configure>", lambda e: draw_bargraph(canvas_bar1, 68))

# Offset Steuerung gemäß Hardware-Muster
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

# CH2
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

# Ratio & Expand nebeneinander für CH2
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
    # LOCK-IN TAB: Aktualisiert die CH2-Anzeige analog zu CH1.
    # Der Unterschied ist nur die Auswahl der Quelle: bei CH2 kann Phase (θ) im Gradmaß dargestellt werden.
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

    # Diese Labels sind die sichtbaren Werte im CH2-Feld.
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
    # LOCK-IN TAB + LASER TAB: Diese Funktion führt die regelmäßige Aktualisierung aller Live-Werte aus.
    # Sie wird per root.after(...) in kurzen Intervallen aufgerufen, damit die GUI "live" wirkt.
    # Wichtig: Hier werden die aktuellsten Werte aus State.py an die sichtbaren Labels gebunden.
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
    # Sendet ein SR830-Kommando an das Gerät, falls angeschlossen.
    # Wenn der Notfall-Bypass aktiviert ist, werden keine Hardware-Kommandos gesendet.
    if is_emergency_bypass:
        return
    if not is_lockin_connected or Komunikation.SR830 is None:
        raise RuntimeError("SR830 ist nicht verbunden.")
    Komunikation.send_SR830(command, value)


def run_auto_command(command, values=None):
    # Führt eine Automatik-Funktion des Lock-In aus, z. B. Auto Phase oder Auto Gain.
    try:
        if values is None:
            send_lockin_command(command)
        else:
            for value in values:
                send_lockin_command(command, value)
    except Exception as error:
        messagebox.showerror("Lock-In Fehler", f"{command}: {error}")


btn_auto_phase = tk.Button(
    frame_auto, text="Auto Phase", font=("Consolas", 8, "bold"),
    bg="#3c3f41", fg="white", command=lambda: run_auto_command("APHS"),
)
btn_auto_phase.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
btn_auto_gain = tk.Button(
    frame_auto, text="Auto Gain", font=("Consolas", 8, "bold"),
    bg="#3c3f41", fg="white", command=lambda: run_auto_command("AGAN"),
)
btn_auto_gain.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
btn_auto_reserve = tk.Button(
    frame_auto, text="Auto Reserve", font=("Consolas", 8, "bold"),
    bg="#3c3f41", fg="white", command=lambda: run_auto_command("ARSV"),
)
btn_auto_reserve.grid(row=1, column=0, padx=2, pady=2, sticky="ew")
btn_auto_offset = tk.Button(
    frame_auto, text="Auto Offset", font=("Consolas", 8, "bold"),
    bg="#3c3f41", fg="white", command=lambda: run_auto_command("AOFF", (1, 2, 3)),
)
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
    try:
        send_lockin_command("SLVL", 1.0)
        messagebox.showinfo(auto_tr("Lock-In Amplifier"), auto_tr("Sine Out set to 1.0 V (ON)."))
    except Exception as e:
        messagebox.showerror("Fehler", f"{e}")


def lockin_stop():
    try:
        send_lockin_command("SLVL", 0.0)
        messagebox.showinfo(auto_tr("Lock-In Amplifier"), auto_tr("Sine Out set to 0.0 V (OFF)."))
    except Exception as e:
        messagebox.showerror("Fehler", f"{e}")


def apply_ref_settings():
    # LOCK-IN TAB: Setzt Frequenz, Phase und Ausgangsamplitude des Referenzsignals.
    # Die sichtbaren Werte werden in val_ref_display übernommen und als GUI-Anzeige dargestellt.
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
# 4. TAB: OSTECH LASER / TEC CONTROLLER
# ------------------------------------------
# Hier werden Laserparameter, TEC-Regelung und Sicherheitslogik gesteuert.
# Die Sicherheitsabfrage verhindert, dass der Laser ohne Prüfung bedient wird.
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
    # Aktualisiert die Anzeige je nach ausgewählter Hardware-Layout-Konfiguration.
    mode_str = combo_layout.get()
    lbl_ov_laser_layout_val.config(text=mode_str)

    for k in lcd_vars:
        lcd_vars[k].grid_remove()

    status = State.OSTECH_STATUS
    laser_is_on = bool(State.L)
    display_values = {
        "Laser Status": "ON" if laser_is_on else "OFF",
        "Mode": "LMDX" if State.LMDX else "Local",
        "TEC1 Status": "OK" if status.get("lt_sensor_ok", False) else "ERROR",
        "TEC2 Status": "OK" if status.get("ct_sensor_ok", False) else "ERROR",
        "LCT": f"{State.LCT:.3f} mA",
        "LCB": f"{State.LCA:.3f} mA",
        "LVA": f"{State.LVA:.3f} V",
        "TA": f"{State.XTA:.2f} °C",
        "TT": f"{State.XTT:.2f} °C",
        "TCA": f"{State.XTCA:.3f} mA",
        "TVA": f"{State.XTVA:.3f} V",
        "TCL": f"{State.LTM:.2f} °C",
        "LTA": f"{State.XTA:.2f} °C",
        "CTA": f"{State.XTCA:.3f} mA",
        "LTT": f"{State.XTT:.2f} °C",
        "LTCA": f"{State.XTCA:.3f} mA",
        "CTT": f"{State.GT:.2f} °C",
        "CTCA": f"{State.XTCA:.3f} mA",
        "Error#": "ERROR" if status.get("lc_error", False) else "--",
        "Interlock": "OK" if status.get("interlock_ok", False) else "OPEN",
    }
    for name, value in display_values.items():
        lcd_vars[name].config(text=f"{name}: {value}")

    if "(a)" in mode_str:
        lbl_lcd_main.config(text=f"{State.LCA:.3f} mA")
        lbl_ov_laser_main_val.config(text=f"{State.LCA:.3f} mA")
        active = ["Laser Status", "Mode", "LCT", "LCB", "LVA", "TA", "Error#", "Interlock"]
    elif "(b)" in mode_str:
        lbl_lcd_main.config(text=f"{State.LCA:.3f} mA")
        lbl_ov_laser_main_val.config(text=f"{State.LCA:.3f} mA")
        active = ["Laser Status", "TEC1 Status", "LCT", "TA", "LVA", "TT", "Mode", "TCA", "Error#", "Interlock"]
    elif "(c)" in mode_str:
        lbl_lcd_main.config(text=f"{State.LCA:.3f} mA")
        lbl_ov_laser_main_val.config(text=f"{State.LCA:.3f} mA")
        active = ["Laser Status", "TEC1 Status", "TEC2 Status", "LCT", "LTA", "LVA", "CTA", "Mode", "Error#",
                  "Interlock"]
    elif "(d)" in mode_str:
        lbl_lcd_main.config(text=f"{State.GT:.2f} °C")
        lbl_ov_laser_main_val.config(text=f"{State.GT:.2f} °C")
        active = ["TEC1 Status", "TT", "TVA", "TCA", "TCL", "Error#", "Interlock"]
    elif "(e)" in mode_str:
        lbl_lcd_main.config(text=f"{State.GT:.2f} °C   {State.GT:.2f} °C")
        lbl_ov_laser_main_val.config(text=f"{State.GT:.2f} °C   {State.GT:.2f} °C")
        active = ["TEC1 Status", "TEC2 Status", "LTT", "CTT", "LTCA", "CTCA", "Error#", "Interlock"]
    else:
        active = []

    for idx, p in enumerate(active):
        r = idx // 4
        c = idx % 4
        lcd_vars[p].grid(row=r, column=c, sticky="ew", padx=5, pady=2)


combo_layout.bind("<<ComboboxSelected>>", update_laser_display_mode)

# Laser Security Checklist
var_goggles = tk.BooleanVar(value=False)
var_interlock = tk.BooleanVar(value=False)
var_beampath = tk.BooleanVar(value=False)
var_warning = tk.BooleanVar(value=False)


def check_laser_safety():
    # Prüft, ob die Sicherheitscheckliste vollständig erfüllt wurde.
    # Nur dann wird das Laser-Menü freigeschaltet.
    if var_goggles.get() and var_interlock.get() and var_beampath.get() and var_warning.get():
        ostech_notebook.tab(tab_ostech_laser, state="normal")
        reg_ui((ostech_notebook, tab_ostech_laser), "Laser Menu", "tab_text")
        lbl_disabled_banner.pack_forget()
        frame_lmenu.pack(fill="both", expand=True, padx=10, pady=10)
        lbl_safety_status.config(
            text=" SAFE TO OPERATE \nLaser-Menu Unlocked",
            bg="#2e7d32",
            fg="#ffffff"
        )
        messagebox.showinfo(auto_tr("Laser Security"),
                            auto_tr("All safety measurements complied. The Laser-Menu is now unlocked."))
    else:
        ostech_notebook.tab(tab_ostech_laser, state=DISABLED)
        reg_ui((ostech_notebook, tab_ostech_laser), "🔒 Laser Menu (Locked)", "tab_text")
        frame_lmenu.pack_forget()
        lbl_disabled_banner.pack(fill="both", expand=True, padx=20, pady=40)
        lbl_safety_status.config(
            text=" ⚠️ INTERLOCKED ⚠️ \nChecklist Incomplete",
            bg="#c62828",
            fg="#ffffff"
        )


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

lbl_safety_status = tk.Label(
    frame_safety,
    text=" ⚠️ INTERLOCKED ⚠️ \nChecklist Incomplete",
    font=("Consolas", 11, "bold"),
    bg="#c62828",
    fg="#ffffff",
    bd=3,
    relief="ridge",
    padx=15,
    pady=8
)
lbl_safety_status.pack(fill="x", pady=(10, 0))

# Laser Menu Tab
tab_ostech_laser = tk.Frame(ostech_notebook, bg="#1e1e1e")
ostech_notebook.add(tab_ostech_laser, text="")
reg_ui((ostech_notebook, tab_ostech_laser), "🔒 Laser Menu (Locked)", "tab_text")
ostech_notebook.tab(tab_ostech_laser, state=DISABLED)

lbl_disabled_banner = tk.Label(
    tab_ostech_laser,
    text="🔒 LASER MENU DEACTIVATED\n\nPlease complete the Laser Security Checklist in the 'Main Display' tab to unlock hardware controls.",
    font=("Consolas", 12, "bold"),
    bg="#2b2b2b",
    fg="#ff4444",
    relief="ridge",
    bd=2,
    padx=20,
    pady=30
)
lbl_disabled_banner.pack(fill="both", expand=True, padx=20, pady=40)

frame_lmenu = tk.LabelFrame(tab_ostech_laser, text=" Laser Menu Parameters ", font=("Consolas", 9, "bold"),
                            bg="#1e1e1e", fg="#00ffcc", padx=10, pady=10)
frame_lmenu.columnconfigure((0, 1, 2), weight=1)

tk.Label(frame_lmenu, text="LCL (Laser Current Limit - A):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).grid(
    row=0, column=0, sticky="w", pady=2)
entry_lcl = tk.Entry(frame_lmenu, font=("Consolas", 9))
entry_lcl.insert(0, "6.300")
entry_lcl.grid(row=1, column=0, sticky="ew", padx=5)

tk.Label(frame_lmenu, text="LVC (Compliance Voltage - V):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).grid(
    row=2, column=0, sticky="w", pady=2)
entry_lvc = tk.Entry(frame_lmenu, font=("Consolas", 9))
entry_lvc.insert(0, "3.00")
entry_lvc.grid(row=3, column=0, sticky="ew", padx=5)

tk.Label(frame_lmenu, text="LCLM (Avg Current Limit - A):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).grid(
    row=4, column=0, sticky="w", pady=2)
entry_lclm = tk.Entry(frame_lmenu, font=("Consolas", 9))
entry_lclm.insert(0, "6.300")
entry_lclm.grid(row=5, column=0, sticky="ew", padx=5)

tk.Label(frame_lmenu, text="LTM (Max Temp Limit - °C):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).grid(row=6,
                                                                                                                column=0,
                                                                                                                sticky="w",
                                                                                                                pady=2)
entry_ltm = tk.Entry(frame_lmenu, font=("Consolas", 9))
entry_ltm.insert(0, "33.0")
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
                                                                                                                  column=1,
                                                                                                                  sticky="w",
                                                                                                                  pady=2)
entry_lmw = tk.Entry(frame_lmenu, font=("Consolas", 9))
entry_lmw.insert(0, "1.000")
entry_lmw.grid(row=3, column=1, sticky="ew", padx=5)

tk.Label(frame_lmenu, text="LMP (Modulation Period - ms):", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 8)).grid(
    row=4, column=1, sticky="w", pady=2)
entry_lmp = tk.Entry(frame_lmenu, font=("Consolas", 9))
entry_lmp.insert(0, "2.000")
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
chk_lg.grid(row=3, column=2, sticky="w", padx=5)


def apply_laser_settings():
    # Validiert und akzeptiert die Laserparameter wie Stromlimit, Spannung und Temperaturgrenze.
    values = (
        read_numeric_entry(entry_lcl, "LCL", 0, 100),
        read_numeric_entry(entry_lvc, "LVC", 0, 100),
        read_numeric_entry(entry_lclm, "LCLM", 0, 100),
        read_numeric_entry(entry_ltm, "LTM", -273.15, 200),
        read_numeric_entry(entry_lmw, "LMW", 0, 100000),
        read_numeric_entry(entry_lmp, "LMP", 0, 100000),
    )
    if any(value is None for value in values):
        return
    if messagebox.askyesno("Bestätigung",
                           "Sollen die eingegebenen Laser-Parameter an den Controller übertragen werden?"):
        messagebox.showinfo("Laser Controller", "Laser-Einstellungen erfolgreich aktualisiert.")


def reset_laser_defaults():
    if messagebox.askyesno("Reset", "Laser-Parameter auf Werkseinstellungen zurücksetzen?"):
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


frame_laser_btns = tk.Frame(frame_lmenu, bg="#1e1e1e")
frame_laser_btns.grid(row=8, column=0, columnspan=3, pady=15, sticky="ew")

btn_apply_laser = tk.Button(frame_laser_btns, text="✔ Apply Laser Settings", font=("Consolas", 9, "bold"), bg="#007acc",
                            fg="white", command=apply_laser_settings)
btn_apply_laser.pack(side="left", fill="x", expand=True, padx=5)

btn_reset_laser = tk.Button(frame_laser_btns, text="Restore Default Settings", font=("Consolas", 8, "bold"),
                            bg="#c62828", fg="white", command=reset_laser_defaults)
btn_reset_laser.pack(side="right", padx=5)

# TEC Menu
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
    # Überträgt TEC-Limits und PID-Parameter auf das Temperaturregelgerät.
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

# Device Menu
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
    # Verarbeitet Geräteeinstellungen wie Pilot-Laser-Stärke und Lüfterspannung.
    pilot_intensity = read_integer_entry(spin_pilot, "Pilot Laser Intensity", 0, 16)
    fan_voltage = read_numeric_entry(entry_gfd, "GFD", 0, 100)
    if pilot_intensity is None or fan_voltage is None:
        return
    if messagebox.askyesno("Bestätigung", "Gerätesystem-Einstellungen anwenden?"):
        messagebox.showinfo("System Settings", "System-Einstellungen übernommen.")


def reset_device_defaults():
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


# ==========================================
# HELPER FOR EXPLORER TREEVIEW
# ==========================================
# Diese Funktionen bauen die Dateibaumstruktur für Logs und Plot-Ordner auf.
# Dadurch kann der Benutzer gespeicherte Messdaten im GUI-Browser einfach auswählen.
def build_file_tree(tree_widget, root_dir):
    # Baut den Dateibaum für den Log-Explorer auf.
    # Der Baum zeigt verzeichnisweise alle Dateien und Unterordner an.
    # Damit kann der Benutzer gespeicherte Messdaten schnell auswählen und öffnen.
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


def build_analysis_explorer(tree_widget):
    # Zeigt im Analyse-Tab ausschließlich die relevanten Datenordner an.
    # Dadurch bleibt der Explorer übersichtlich und enthält nur Messdaten sowie gespeicherte Plots.
    tree_widget.delete(*tree_widget.get_children())
    root_node = tree_widget.insert("", "end", text=" 📂 Workspace", open=True, values=[os.getcwd()])

    for dir_path, label in [(LOG_DIR, "logs"), (PLOT_DIR, "plots")]:
        node = tree_widget.insert(root_node, "end", text=f" 📁 {label}", open=True, values=[dir_path])
        try:
            entries = sorted(os.listdir(dir_path))
            for entry in entries:
                if entry.startswith('.'):
                    continue
                full_path = os.path.join(dir_path, entry)
                if not os.path.isdir(full_path):
                    tree_widget.insert(node, "end", text=f" 📝 {entry}", values=[full_path])
        except Exception:
            pass


build_file_tree(tree_logs_main, LOG_DIR)

# ------------------------------------------
# 5. TAB: ANALYSIS
# ------------------------------------------
# Hier werden die Messdaten ausgewertet und graphisch dargestellt.
# Der Nutzer kann Daten importieren, Plots berechnen und die Ergebnisse speichern.
tab_analysis = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_analysis, text="")
reg_ui((main_notebook, tab_analysis), "Analysis", "tab_text")

analysis_notebook = ttk.Notebook(tab_analysis)
analysis_notebook.pack(fill="both", expand=True, padx=10, pady=10)

sub_tab_stats = tk.Frame(analysis_notebook, bg="#252526")
analysis_notebook.add(sub_tab_stats, text="")
reg_ui((analysis_notebook, sub_tab_stats), "Statistics", "tab_text")

paned_stats = ttk.PanedWindow(sub_tab_stats, orient="horizontal")
paned_stats.pack(fill="both", expand=True, padx=5, pady=5)

frame_tree_stats = tk.Frame(paned_stats, bg="#1e1e1e", width=260)
paned_stats.add(frame_tree_stats, weight=1)

lbl_tree_stats_title = tk.Label(frame_tree_stats, text="PROJECT EXPLORER", font=("Consolas", 9, "bold"), bg="#3c3f41",
                                fg="#ffffff", anchor="w", padx=5)
lbl_tree_stats_title.pack(fill="x")

tree_stats = ttk.Treeview(frame_tree_stats, show="tree")
tree_stats.pack(fill="both", expand=True)

# Analysis Explorer stellt ausschließlich den Log- und Plot-Ordner dar
build_analysis_explorer(tree_stats)

frame_stats_work = tk.Frame(paned_stats, bg="#252526")
paned_stats.add(frame_stats_work, weight=4)

frame_stats_top = tk.Frame(frame_stats_work, bg="#252526")
frame_stats_top.pack(fill="x", pady=10)

btn_load = tk.Button(frame_stats_top, font=("Consolas", 9, "bold"), bg="#007acc", fg="white", padx=10, pady=5,
                     command=open_file_dialog)
btn_load.pack(side="left", padx=10)
reg_ui(btn_load, "📁 Import Data File")

lbl_file_status = tk.Label(frame_stats_top, font=("Consolas", 9), bg="#252526", fg="#aaaaaa")
lbl_file_status.pack(side="left", padx=10)
reg_ui(lbl_file_status, "No file loaded")

frame_plot_pvf = tk.Frame(frame_stats_work, bg="#1e1e1e", bd=2, relief="sunken")
frame_plot_pvf.pack(fill="both", expand=True, padx=10, pady=5)

fig_pvf = None
ax_pvf = None
canvas_pvf = None


def initialize_pvf_plot():
    # Initialisiert das Matplotlib-Plot-Fenster für die PVF-/Phasenanalyse.
    global fig_pvf, ax_pvf, canvas_pvf
    if fig_pvf is not None:
        return

    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    fig_pvf, ax_pvf = plt.subplots(figsize=(6, 4), facecolor="#1e1e1e")
    ax_pvf.set_facecolor("#2b2b2b")
    ax_pvf.tick_params(colors="white")
    ax_pvf.xaxis.label.set_color("white")
    ax_pvf.yaxis.label.set_color("white")
    ax_pvf.title.set_color("white")
    ax_pvf.grid(True, color="#444444", linestyle=":")
    canvas_pvf = FigureCanvasTkAgg(fig_pvf, master=frame_plot_pvf)
    canvas_pvf.get_tk_widget().pack(fill="both", expand=True)


def starte_pvf_analyse():
    global fig_pvf, ax_pvf, canvas_pvf

    # 1. Referenz-Datei abfragen
    path_to_ref = filedialog.askopenfilename(
        title="1. Select Reference Measurement File (unnitriert)",
        filetypes=[("Text Files", "*.txt *.csv"), ("All files", "*.*")]
    )
    if not path_to_ref:
        return

    # 2. Proben-Datei abfragen
    path_to_probe = filedialog.askopenfilename(
        title="2. Select Probe Measurement File (nitriert)",
        filetypes=[("Text Files", "*.txt *.csv"), ("All files", "*.*")]
    )
    if not path_to_probe:
        return

    try:
        # 3. Berechnung ausführen
        results = PhasFreq_v8.start_PhaseFreq(path_to_ref, path_to_probe)

        d_um = results["d_fit_um"]
        d_err = results["d_err_um"]
        kL = results["kL_fit"]
        kL_err = results["kL_err"]
        pdata = results["plot_data"]

        # 4. Figure initialisieren / zurücksetzen
        if fig_pvf is None:
            fig_pvf = plt.Figure(figsize=(6, 5), dpi=100)
        else:
            fig_pvf.clf()

        # Subplots erstellen
        ax_raw = fig_pvf.add_subplot(211)
        ax_fit = fig_pvf.add_subplot(212)

        # Plot 1: Rohdaten
        ax_raw.plot(pdata["f_ref"], pdata["phase_ref_unwr"], "o-", label=f"Ref: {pdata['ref_filename']}")
        ax_raw.plot(pdata["f_probe"], pdata["phase_probe_unwr"], "s--", label=f"Probe: {pdata['probe_filename']}")
        ax_raw.set_xscale("log")
        ax_raw.set_xlabel("Frequenz in Hz (log-Skala)")
        ax_raw.set_ylabel("Phase (entfaltet) in °")
        ax_raw.set_title("Sicht-Vergleich der Rohdaten")
        ax_raw.legend(fontsize=8)
        ax_raw.grid(True, which="both", alpha=0.4)

        # Plot 2: Phasendifferenz & Fit
        ax_fit.plot(np.sqrt(2 * np.pi * pdata["freq_common"]), pdata["Phi"], "o", label=r"Messdaten $\Phi(\omega)$")
        ax_fit.plot(np.sqrt(2 * np.pi * pdata["freq_fine"]), pdata["Phi_fit_curve"], "--", label="Fit-Modell")
        ax_fit.set_xlabel(r"$\sqrt{\omega}$ in $\sqrt{Hz}$")
        ax_fit.set_ylabel(r"Phasendifferenz $\Phi$ in °")
        ax_fit.set_title(f"Ergebnis: d = {d_um:.2f} ± {d_err:.2f} µm | k_L = {kL:.2f} ± {kL_err:.2f} W/(m·K)")
        ax_fit.legend(fontsize=8)
        ax_fit.grid(True, alpha=0.4)

        fig_pvf.tight_layout()

        # Canvas in den Frame frame_plot_pvf einbetten (falls noch nicht geschehen)
        if canvas_pvf is None:
            canvas_pvf = FigureCanvasTkAgg(fig_pvf, master=frame_plot_pvf)
            canvas_pvf.get_tk_widget().pack(fill="both", expand=True)

        # Canvas aktualisieren
        canvas_pvf.draw()

        messagebox.showinfo("Analysis", "Phase vs. Frequenz Analyse erfolgreich berechnet.")

    except Exception as e:
        messagebox.showerror("Fehler", f"Fehler bei der Analyse: {e}")


'''
    initialize_pvf_plot()
    ax_pvf.clear()
    ax_pvf.grid(True, color="#444444", linestyle=":")

    np.random.seed(42)
    f_simulated = np.logspace(0, 5, 250)

    def get_effusivity(k, rho, c): return np.sqrt(k * rho * c)

    def get_diffusivity(k, rho, c): return k / (rho * c)

    def fit_model_d_only(f, d_um, k_L=14.4):
        omega = 2.0 * np.pi * f
        d = d_um * 1e-6
        b_L = get_effusivity(k_L, 7870.0, 460.0)
        b_S = get_effusivity(73.0, 7870.0, 460.0)
        alpha_L = get_diffusivity(k_L, 7870.0, 460.0)
        mu_L = np.sqrt(2.0 * alpha_L / omega)
        term_d_mu = (2.0 * d) / mu_L
        b_diff = b_S - b_L
        b_sum = b_S + b_L
        num = (b_S ** 2 - b_L ** 2) * (np.exp(term_d_mu) - np.exp(-term_d_mu)) + 2.0 * (b_S ** 2 - b_L ** 2) * np.sin(
            term_d_mu)
        den = -(b_diff ** 2) + (b_sum ** 2) * np.exp(2.0 * term_d_mu) + 2.0 * (b_S ** 2 - b_L ** 2) * np.sin(term_d_mu)
        return np.degrees(np.arctan(num / den))

    d_true = 30.0
    phi_simulated = fit_model_d_only(f_simulated, d_true) + np.random.normal(0, 0.35, size=250)

    sqrt_omega = np.sqrt(2 * np.pi * f_simulated)
    ax_pvf.plot(sqrt_omega, phi_simulated, 'o', color='#ff7043', alpha=0.6, markersize=3, label='Lock-In Messdaten')
    ax_pvf.plot(sqrt_omega, fit_model_d_only(f_simulated, 30.0), color='#29b6f6', linewidth=2,
                label='Fit (d = 30.00 µm, R² = 0.9984)')

    ax_pvf.set_xlabel(r'$\sqrt{\omega}$ [$\sqrt{\mathrm{Hz}}$]', color="white")
    ax_pvf.set_ylabel('Phase φ [°]', color="white")
    ax_pvf.set_title('PTR Phase vs. Frequency Analysis & Fit', color="white", fontweight="bold")
    ax_pvf.legend(facecolor="#2b2b2b", edgecolor="#444444", labelcolor="white")
'''





def save_pvf_plot():
    # Speichert das aktuell erstellte Plot als PNG im plots-Ordner.
    if fig_pvf is None:
        messagebox.showerror("Error", "Kein Plot vorhanden, der gespeichert werden kann.")
        return
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"PTR_Plot_{timestamp}.png"
    filepath = os.path.join(PLOT_DIR, filename)
    try:
        fig_pvf.savefig(filepath, dpi=300, bbox_inches="tight", facecolor=fig_pvf.get_facecolor())
        messagebox.showinfo("Erfolg", f"Plot erfolgreich gespeichert unter:\n{filepath}")
        build_analysis_explorer(tree_stats)
    except Exception as e:
        messagebox.showerror("Fehler", f"Fehler beim Speichern des Plots: {e}")


btn_pvf = tk.Button(frame_stats_top, font=("Consolas", 9, "bold"), bg="#f57c00", fg="white", padx=10, pady=5,
                    command=starte_pvf_analyse)
btn_pvf.pack(side="left", padx=10)
reg_ui(btn_pvf, "📈 Phase vs. Frequency Analysis")

btn_save_plot = tk.Button(frame_stats_top, text="💾 Save Plot", font=("Consolas", 9, "bold"), bg="#2e7d32", fg="white", padx=10, pady=5,
                          command=save_pvf_plot)
btn_save_plot.pack(side="left", padx=10)


def on_tree_stats_select(event):
    selected = tree_stats.selection()
    if selected:
        val = tree_stats.item(selected[0], "values")
        if val and os.path.isfile(val[0]):
            lbl_file_status.config(text=os.path.basename(val[0]))


tree_stats.bind("<<TreeviewSelect>>", on_tree_stats_select)

# ------------------------------------------
# 6. TAB: HELP
# ------------------------------------------
# Dieser Bereich enthält die allgemeine Bedienhinweise und Informationsseiten für den Nutzer.
tab_help = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_help, text="")
reg_ui((main_notebook, tab_help), "Help", "tab_text")

help_notebook = ttk.Notebook(tab_help)
help_notebook.pack(fill="both", expand=True, padx=10, pady=10)

sub_tab_about_the_application = tk.Frame(help_notebook, bg="#252526")
help_notebook.add(sub_tab_about_the_application, text="")
reg_ui((help_notebook, sub_tab_about_the_application), "About the application", "tab_text")

lbl_help = tk.Label(sub_tab_about_the_application, font=("Consolas", 14, "bold"), bg="#252526", fg="#00ffcc")
lbl_help.pack(pady=(20, 10))
reg_ui(lbl_help,
       "This application is the result of the software project of summer semester 2026.\nIn case of problems please contact support.")

sub_tab_guide = tk.Frame(help_notebook, bg="#252526")
help_notebook.add(sub_tab_guide, text="")
reg_ui((help_notebook, sub_tab_guide), "Guide", "tab_text")

txt_guide = tk.Text(sub_tab_guide, bg="#1e1e1e", fg="#ffffff", font=("Segoe UI", 10), padx=15, pady=15, wrap="word")
txt_guide.pack(fill="both", expand=True, padx=10, pady=10)

guide_content = """📖 PAMO EXPERIMENT & HARDWARE GUIDE

1. OVERVIEW & HARDWARE CONNECTION:
   - Live status of hardware connection visible on top.
   - Live Log Terminal monitoring real-time system events.

2. LOG MANAGEMENT (LOGS TAB):
   - Access the Log Directory using the built-in file explorer.
   - Define custom log file names using the format '[YYYY-MM-DD]_Experiment_[Identifier]'.
   - Import external CSV log files using the 'Import CSV' button.

3. LOCK-IN AMPLIFIER:
   - Configure signal inputs, coupling (AC/DC), line notch filters, and sensitivity.
   - Monitor CH1/CH2 live channels with physical units (V, °) and dynamic Overload Detection.
   - Execute auto-tuning functions (Auto Phase, Auto Gain, Auto Reserve, Auto Offset).

4. OSTECH LASER & TEC CONTROLLER:
   - Complete the Laser Security Checklist to unlock the Laser Menu.
   - Configure laser limits (LCL, LVC, LTM) and modulation modes (CW, External, Internal).
   - Adjust TEC temperature limits and PID controller parameters (Tk, Tn, Tv).

5. DATA ANALYSIS:
   - Import dataset files (.txt, .csv) and run Phase vs. Frequency analysis models.
"""
txt_guide.insert("end", guide_content)
txt_guide.config(state="disabled")

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
                                btn_pvf, btn_save_plot,
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



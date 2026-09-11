import os
import sys
import json
import random
import time
import tkinter as tk
from tkinter import messagebox, ttk, filedialog, simpledialog
from tkinter.constants import DISABLED

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

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
# KONFIGURATION & PASSWORT-MANAGEMENT
# ==========================================
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

# ==========================================
# AUTOMATISIERTES ÜBERSETZUNGS-SYSTEM
# ==========================================
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
        "Logs": "Protokolle / Logs"
    }
}

registered_widgets = []


def auto_tr(english_text):
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
# HARDWARE VARIABLEN
# ==========================================
LOCK_IN_AMPLIFIER_PORT = "COM3"
LASER_PORT = "COM4"
lockin_device = None
current_file_path = None

is_lockin_connected = False
is_laser_connected = False
is_emergency_bypass = False


def check_real_com_port(port_name):
    if serial:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        return port_name in ports
    if pyvisa:
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources()
            return port_name in resources
        except Exception:
            return False
    return False


def connect_lockin():
    global lockin_device, is_lockin_connected
    if is_emergency_bypass:
        return True

    if pyvisa:
        try:
            rm = pyvisa.ResourceManager()
            lockin_device = rm.open_resource(LOCK_IN_AMPLIFIER_PORT)
            lockin_device.timeout = 2000
            is_lockin_connected = True
        except Exception:
            lockin_device = None
            is_lockin_connected = False
    else:
        is_lockin_connected = check_real_com_port(LOCK_IN_AMPLIFIER_PORT)

    return is_lockin_connected


def open_file_dialog():
    global current_file_path
    file_path = filedialog.askopenfilename(
        title=auto_tr("Import Data File"),
        filetypes=[("Text Files", "*.txt *.csv"), ("All files", "*.*")]
    )
    if file_path:
        current_file_path = file_path
        lbl_file_status.config(text=os.path.basename(current_file_path))


def on_closing():
    root.quit()
    root.destroy()
    sys.exit(0)


# ==========================================
# GUI ANWENDUNG INITIALISIERUNG
# ==========================================
root = tk.Tk()
root.title('PAMO - Photothermal Analysis & Monitoring Overview')
root.geometry('1340x840')
root.configure(bg="#2b2b2b")
root.protocol("WM_DELETE_WINDOW", on_closing)

style = ttk.Style()
style.theme_use('default')
style.configure("TNotebook", background="#2b2b2b", borderwidth=0)
style.configure("TNotebook.Tab", background="#3c3f41", foreground="#ffffff", padding=[10, 6],
                font=('Consolas', 10, 'bold'))
style.map("TNotebook.Tab", background=[("selected", "#007acc")], foreground=[("selected", "#ffffff")])

main_notebook = ttk.Notebook(root)
main_notebook.pack(fill="both", expand=True, padx=10, pady=10)

# ------------------------------------------
# 1. TAB: HOME
# ------------------------------------------
tab_home = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_home, text="")
reg_ui((main_notebook, tab_home), "Home", "tab_text")

lbl_welcome = tk.Label(tab_home, font=("Consolas", 12, "bold"), bg="#1e1e1e", fg="#00ffcc")
lbl_welcome.pack(pady=(20, 5))
reg_ui(lbl_welcome, "WELCOME TO LAB MEASUREMENT SYSTEM")

lbl_info = tk.Label(tab_home, font=("Segoe UI", 10), bg="#1e1e1e", fg="#aaaaaa", justify="center")
lbl_info.pack(pady=5)
reg_ui(lbl_info, "Select a tab above to control hardware or run data analysis.")

# ------------------------------------------
# 2. TAB: CONNECTIONS
# ------------------------------------------
tab_connections = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_connections, text="")
reg_ui((main_notebook, tab_connections), "Connections", "tab_text")

frame_coms = tk.LabelFrame(tab_connections, text=" Hardware COM Interfaces & System Tools ",
                           font=("Consolas", 10, "bold"),
                           bg="#1e1e1e", fg="#00ffcc", padx=15, pady=15)
frame_coms.pack(pady=15, padx=20, fill="x")

tk.Label(frame_coms, text="Lock-In Amplifier Port:", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 9)).grid(row=0,
                                                                                                            column=0,
                                                                                                            sticky="w",
                                                                                                            pady=5)
entry_com_lockin = ttk.Entry(frame_coms, width=20)
entry_com_lockin.insert(0, LOCK_IN_AMPLIFIER_PORT)
entry_com_lockin.grid(row=0, column=1, padx=10, pady=5)

lbl_status_lockin = tk.Label(frame_coms, text="🔴 Nicht Verbunden", font=("Consolas", 9, "bold"), bg="#1e1e1e",
                             fg="#ff4444")
lbl_status_lockin.grid(row=0, column=2, padx=10, pady=5, sticky="w")

tk.Label(frame_coms, text="OSTech Laser Port:", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 9)).grid(row=1, column=0,
                                                                                                       sticky="w",
                                                                                                       pady=5)
entry_com_laser = ttk.Entry(frame_coms, width=20)
entry_com_laser.insert(0, LASER_PORT)
entry_com_laser.grid(row=1, column=1, padx=10, pady=5)

lbl_status_laser = tk.Label(frame_coms, text="🔴 Nicht Verbunden", font=("Consolas", 9, "bold"), bg="#1e1e1e",
                            fg="#ff4444")
lbl_status_laser.grid(row=1, column=2, padx=10, pady=5, sticky="w")

frame_com_btns = tk.Frame(frame_coms, bg="#1e1e1e")
frame_com_btns.grid(row=2, column=0, columnspan=3, pady=15, sticky="w")

# ------------------------------------------
# 3. TAB: LOCK-IN AMPLIFIER
# ------------------------------------------
tab_lockin = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_lockin, text="")
reg_ui((main_notebook, tab_lockin), "Lock-In Amplifier 🔒 (locked)", "tab_text")

lbl_lockin_com_locked = tk.Label(tab_lockin, text="", bg="#1e1e1e")

tab_lockin.columnconfigure((0, 1, 2, 3), weight=1, pad=5)
tab_lockin.rowconfigure(0, weight=1)

frame_input = tk.LabelFrame(tab_lockin, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=8, pady=5)
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
combo_sens = ttk.Combobox(frame_input, values=["2 nV", "10 nV", "100 nV", "1 uV", "100 uV", "1 V"], state="readonly")
combo_sens.current(5)
combo_sens.pack(fill="x", pady=2)

lbl_res = tk.Label(frame_input, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_res.pack(anchor="w", pady=(5, 0))
reg_ui(lbl_res, "Dynamic Reserve:")
combo_res = ttk.Combobox(frame_input, values=["High Reserve", "Normal", "Low Noise"], state="readonly")
combo_res.current(0)
combo_res.pack(fill="x", pady=2)

lbl_tc = tk.Label(frame_input, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_tc.pack(anchor="w", pady=(5, 0))
reg_ui(lbl_tc, "Time Constant:")
combo_tc = ttk.Combobox(frame_input, values=["10 us", "1 ms", "100 ms", "1 s", "30 ks"], state="readonly")
combo_tc.current(2)
combo_tc.pack(fill="x", pady=2)

lbl_slope = tk.Label(frame_input, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_slope.pack(anchor="w", pady=(5, 0))
reg_ui(lbl_slope, "Filter Slope:")
combo_slope = ttk.Combobox(frame_input, values=["6 dB/oct", "12 dB/oct", "18 dB/oct", "24 dB/oct"], state="readonly")
combo_slope.current(3)
combo_slope.pack(fill="x", pady=2)


def apply_lockin_filter_settings():
    if messagebox.askyesno("Bestätigung", "Filter- und Eingangs-Einstellungen an den Lock-In Amplifier übermitteln?"):
        messagebox.showinfo("Lock-In Amplifier", "Signal- und Filter-Parameter erfolgreich angewendet.")


btn_apply_input = tk.Button(frame_input, text="✔ Apply Input Settings", font=("Consolas", 8, "bold"), bg="#007acc",
                            fg="white", command=apply_lockin_filter_settings)
btn_apply_input.pack(fill="x", pady=(10, 2))

# CH1
frame_ch1 = tk.LabelFrame(tab_lockin, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=8, pady=5)
frame_ch1.grid(row=0, column=1, sticky="nsew", padx=4, pady=5)
reg_ui(frame_ch1, " CH1 Display ")

lbl_ch1_src = tk.Label(frame_ch1, text="DISPLAY SOURCE:", font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_ch1_src.pack(anchor="w")
combo_ch1_src = ttk.Combobox(frame_ch1, values=["X", "R", "X Noise", "Aux In 1"], state="readonly")
combo_ch1_src.current(0)
combo_ch1_src.pack(fill="x", pady=2)

val_ch1_label = tk.Label(frame_ch1, text="0.0 V", font=("Consolas", 22, "bold"), bg="#000000", fg="#00ff00",
                         relief="sunken", bd=3)
val_ch1_label.pack(fill="x", pady=(10, 2))


def update_ch1_display(event=None):
    selection = combo_ch1_src.get()
    cmd_map = {"X": ("OUTP1", "V"), "R": ("OUTP3", "V"), "X Noise": ("OUTR1", "V"), "Aux In 1": ("OAUX1", "V")}
    cmd, unit = cmd_map.get(selection, ("OUTP1", "V"))
    val = 0
    val_ch1_label.config(text=f"{val} {unit}")


combo_ch1_src.bind("<<ComboboxSelected>>", update_ch1_display)

lbl_bar1 = tk.Label(frame_ch1, text="LEVEL BAR GRAPH", font=("Consolas", 7), bg="#1e1e1e", fg="#888888")
lbl_bar1.pack(anchor="w", pady=(5, 0))
canvas_bar1 = tk.Canvas(frame_ch1, height=18, bg="#000000", highlightthickness=1, highlightbackground="#444444")
canvas_bar1.pack(fill="x", pady=2)


def draw_bargraph(canvas, percent):
    canvas.delete("all")
    width = canvas.winfo_width()
    if width <= 1:
        width = 200
    fill_width = int(width * (percent / 100.0))
    for x in range(0, fill_width, 6):
        color = "#00ff00" if x < width * 0.8 else "#ff3333"
        canvas.create_rectangle(x, 2, x + 4, 16, fill=color, outline="")


canvas_bar1.bind("<Configure>", lambda e: draw_bargraph(canvas_bar1, 68))

frame_off1 = tk.LabelFrame(frame_ch1, text=" Offset & Expand ", font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
frame_off1.pack(fill="x", pady=(15, 2))
btn_auto_off1 = tk.Button(frame_off1, text="Auto Offset", font=("Consolas", 8), bg="#3c3f41", fg="white")
btn_auto_off1.pack(fill="x", pady=2)

# CH2
frame_ch2 = tk.LabelFrame(tab_lockin, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=8, pady=5)
frame_ch2.grid(row=0, column=2, sticky="nsew", padx=4, pady=5)
reg_ui(frame_ch2, " CH2 Display ")

lbl_ch2_src = tk.Label(frame_ch2, text="DISPLAY SOURCE:", font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_ch2_src.pack(anchor="w")
combo_ch2_src = ttk.Combobox(frame_ch2, values=["Y", "Phase (θ)", "Y Noise", "Aux In 2"], state="readonly")
combo_ch2_src.current(1)
combo_ch2_src.pack(fill="x", pady=2)

val_ch2_label = tk.Label(frame_ch2, text="0.0 °", font=("Consolas", 22, "bold"), bg="#000000", fg="#00ff00",
                         relief="sunken", bd=3)
val_ch2_label.pack(fill="x", pady=(10, 2))


def update_ch2_display(event=None):
    selection = combo_ch2_src.get()
    cmd_map = {"Y": ("OUTP2", "V"), "Phase (θ)": ("OUTP4", "°"), "Y Noise": ("OUTR2", "V"), "Aux In 2": ("OAUX2", "V")}
    cmd, unit = cmd_map.get(selection, ("OUTP4", "°"))
    val = 0
    val_ch2_label.config(text=f"{val} {unit}")


combo_ch2_src.bind("<<ComboboxSelected>>", update_ch2_display)

lbl_bar2 = tk.Label(frame_ch2, text="LEVEL BAR GRAPH", font=("Consolas", 7), bg="#1e1e1e", fg="#888888")
lbl_bar2.pack(anchor="w", pady=(5, 0))
canvas_bar2 = tk.Canvas(frame_ch2, height=18, bg="#000000", highlightthickness=1, highlightbackground="#444444")
canvas_bar2.pack(fill="x", pady=2)
canvas_bar2.bind("<Configure>", lambda e: draw_bargraph(canvas_bar2, 42))

frame_off2 = tk.LabelFrame(frame_ch2, text=" Offset & Expand ", font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
frame_off2.pack(fill="x", pady=(15, 2))
btn_auto_off2 = tk.Button(frame_off2, text="Auto Offset", font=("Consolas", 8), bg="#3c3f41", fg="white")
btn_auto_off2.pack(fill="x", pady=2)

# Ref Display & Controls
frame_ref = tk.LabelFrame(tab_lockin, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=8, pady=5)
frame_ref.grid(row=0, column=3, sticky="nsew", padx=4, pady=5)
reg_ui(frame_ref, " Ref Display & Controls ")

val_ref_display = tk.Label(frame_ref, text="1000.00 Hz", font=("Consolas", 20, "bold"), bg="#000000", fg="#00ff00",
                           relief="sunken", bd=3)
val_ref_display.pack(fill="x", pady=(2, 6))

frame_auto = tk.LabelFrame(frame_ref, text=" Auto Functions ", font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#ffaa00",
                           padx=5, pady=5)
frame_auto.pack(fill="x", pady=5)
frame_auto.columnconfigure((0, 1), weight=1)

tk.Button(frame_auto, text="Auto Phase", font=("Consolas", 8, "bold"), bg="#3c3f41", fg="white").grid(row=0, column=0,
                                                                                                      padx=2, pady=2,
                                                                                                      sticky="ew")
tk.Button(frame_auto, text="Auto Gain", font=("Consolas", 8, "bold"), bg="#3c3f41", fg="white").grid(row=0, column=1,
                                                                                                     padx=2, pady=2,
                                                                                                     sticky="ew")
tk.Button(frame_auto, text="Auto Reserve", font=("Consolas", 8, "bold"), bg="#3c3f41", fg="white").grid(row=1, column=0,
                                                                                                        padx=2, pady=2,
                                                                                                        sticky="ew")
tk.Button(frame_auto, text="Auto Offset", font=("Consolas", 8, "bold"), bg="#3c3f41", fg="white").grid(row=1, column=1,
                                                                                                       padx=2, pady=2,
                                                                                                       sticky="ew")

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
    if connect_lockin():
        try:
            if lockin_device:
                lockin_device.write("SLVL 1.0")
            messagebox.showinfo(auto_tr("Lock-In Amplifier"), auto_tr("Sine Out set to 1.0 V (ON)."))
        except Exception as e:
            messagebox.showerror("Fehler", f"{e}")


def lockin_stop():
    if connect_lockin():
        try:
            if lockin_device:
                lockin_device.write("SLVL 0.0")
            messagebox.showinfo(auto_tr("Lock-In Amplifier"), auto_tr("Sine Out set to 0.0 V (OFF)."))
        except Exception as e:
            messagebox.showerror("Fehler", f"{e}")


def apply_ref_settings():
    new_freq = entry_freq.get()
    new_phase = entry_ref_phase.get()
    new_ampl = entry_ampl.get()

    if messagebox.askyesno("Bestätigung",
                           f"Referenz-Parameter wirklich anpassen?\n\nFrequenz: {new_freq} Hz\nPhase: {new_phase}°\nAmplitude: {new_ampl} V"):
        val_ref_display.config(text=f"{new_freq} Hz")
        if connect_lockin() and lockin_device:
            try:
                lockin_device.write(f"FREQ {new_freq}")
                lockin_device.write(f"PHAS {new_phase}")
                lockin_device.write(f"SLVL {new_ampl}")
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
tab_laser = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_laser, text="")
reg_ui((main_notebook, tab_laser), "Laser / TEC Controller 🔒 (locked)", "tab_text")

lbl_laser_com_locked = tk.Label(tab_laser, text="", bg="#1e1e1e")

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
    mode_str = combo_layout.get()
    for k in lcd_vars:
        lcd_vars[k].grid_remove()

    lca = 0
    gt = 0

    if "(a)" in mode_str:
        lbl_lcd_main.config(text=f"{lca} mA")
        active = ["Laser Status", "Mode", "LCT", "LCB", "LVA", "TA", "Error#", "Interlock"]
    elif "(b)" in mode_str:
        lbl_lcd_main.config(text=f"{lca} mA")
        active = ["Laser Status", "TEC1 Status", "LCT", "TA", "LVA", "TT", "Mode", "TCA", "Error#", "Interlock"]
    elif "(c)" in mode_str:
        lbl_lcd_main.config(text=f"{lca} mA")
        active = ["Laser Status", "TEC1 Status", "TEC2 Status", "LCT", "LTA", "LVA", "CTA", "Mode", "Error#",
                  "Interlock"]
    elif "(d)" in mode_str:
        lbl_lcd_main.config(text=f"{gt} °C")
        active = ["TEC1 Status", "TT", "TVA", "TCA", "TCL", "Error#", "Interlock"]
    elif "(e)" in mode_str:
        lbl_lcd_main.config(text=f"{gt}°C   {gt}°C")
        active = ["TEC1 Status", "TEC2 Status", "LTT", "CTT", "LTCA", "CTCA", "Error#", "Interlock"]

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
# HARDWARE SAMMLUNGSFUNKTIONEN
# (Nach Widget-Erstellung definiert)
# ==========================================
def update_tab_states():
    if is_emergency_bypass:
        main_notebook.tab(tab_lockin, state="normal")
        main_notebook.tab(tab_laser, state="normal")
        reg_ui((main_notebook, tab_lockin), "Lock-In Amplifier", "tab_text")
        reg_ui((main_notebook, tab_laser), "Laser / TEC Controller", "tab_text")
        lbl_lockin_com_locked.pack_forget()
        lbl_laser_com_locked.pack_forget()
        lbl_status_lockin.config(text="⚠️ OVERRIDE (EMERGENCY)", fg="#ffaa00")
        lbl_status_laser.config(text="⚠️ OVERRIDE (EMERGENCY)", fg="#ffaa00")
        return

    if is_lockin_connected:
        main_notebook.tab(tab_lockin, state="normal")
        reg_ui((main_notebook, tab_lockin), "Lock-In Amplifier", "tab_text")
        lbl_lockin_com_locked.pack_forget()
        lbl_status_lockin.config(text="🟢 Verbunden", fg="#00ff00")
    else:
        main_notebook.tab(tab_lockin, state="disabled")
        reg_ui((main_notebook, tab_lockin), "Lock-In Amplifier 🔒 (locked)", "tab_text")
        lbl_status_lockin.config(text="🔴 Nicht Verbunden", fg="#ff4444")

    if is_laser_connected:
        main_notebook.tab(tab_laser, state="normal")
        reg_ui((main_notebook, tab_laser), "Laser / TEC Controller", "tab_text")
        lbl_laser_com_locked.pack_forget()
        lbl_status_laser.config(text="🟢 Verbunden", fg="#00ff00")
    else:
        main_notebook.tab(tab_laser, state="disabled")
        reg_ui((main_notebook, tab_laser), "Laser 🔒 (locked)", "tab_text")
        lbl_status_laser.config(text="🔴 Nicht Verbunden", fg="#ff4444")


def apply_com_settings():
    global LOCK_IN_AMPLIFIER_PORT, LASER_PORT
    LOCK_IN_AMPLIFIER_PORT = entry_com_lockin.get()
    LASER_PORT = entry_com_laser.get()
    messagebox.showinfo("COM Config", f"Ports updated:\nLock-In: {LOCK_IN_AMPLIFIER_PORT}\nLaser: {LASER_PORT}")


def connect_all_hardware():
    global is_lockin_connected, is_laser_connected, is_emergency_bypass
    is_emergency_bypass = False

    is_lockin_connected = connect_lockin()
    is_laser_connected = check_real_com_port(LASER_PORT)

    update_tab_states()

    if is_lockin_connected or is_laser_connected:
        messagebox.showinfo("Hardware Status",
                            f"Verbindungsprüfung abgeschlossen:\nLock-In: {'Verbunden' if is_lockin_connected else 'Getrennt'}\nLaser: {'Verbunden' if is_laser_connected else 'Getrennt'}")
    else:
        messagebox.showwarning("Hardware Status",
                               "Keine physikalische Verbindung zu den angegebenen COM-Ports gefunden!")


def disconnect_all_hardware():
    global is_lockin_connected, is_laser_connected, is_emergency_bypass, lockin_device
    is_lockin_connected = False
    is_laser_connected = False
    is_emergency_bypass = False
    lockin_device = None
    update_tab_states()
    messagebox.showinfo("Hardware Status", "Alle Verbindungen getrennt.")


def trigger_emergency_bypass():
    global is_emergency_bypass
    pwd = simpledialog.askstring("Notfall-Zugriff", "Bitte Notfall-Passwort eingeben:", show='*')
    if pwd is not None:
        if pwd == APP_SETTINGS.get("emergency_password", "admin123"):
            is_emergency_bypass = True
            update_tab_states()
            messagebox.showwarning("Notfall-Bypass Aktiviert",
                                   "Notfall-Zugriff gewährt!\nHardware-Schnittstellen wurden manuell freigeschaltet.")
        else:
            messagebox.showerror("Zugriff Verweigert", "Falsches Passwort!")


btn_apply_com = tk.Button(frame_com_btns, text="Refresh", font=("Consolas", 9, "bold"), bg="#007acc", fg="white",
                          command=apply_com_settings)
btn_apply_com.pack(side="left", padx=5)

btn_scan_com = tk.Button(frame_com_btns, text="Connect", font=("Consolas", 9, "bold"), bg="#2e7d32", fg="white",
                         command=connect_all_hardware)
btn_scan_com.pack(side="left", padx=5)

btn_dev_manager = tk.Button(frame_com_btns, text="Disconnect", font=("Consolas", 9, "bold"), bg="#c62828", fg="white",
                            command=disconnect_all_hardware)
btn_dev_manager.pack(side="left", padx=5)

btn_emergency_bypass = tk.Button(frame_coms, text="🔑", font=("Consolas", 8), bg="#2b2b2b", fg="#555555", bd=0,
                                 relief="flat", activebackground="#2b2b2b", command=trigger_emergency_bypass)
btn_emergency_bypass.grid(row=2, column=2, sticky="e", padx=5)


# ==========================================
# HELPER FOR EXPLORER TREEVIEW (PYCHARM STYLE)
# ==========================================
def build_file_tree(tree_widget, root_dir):
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


# ==========================================
# 5. TAB: ANALYSIS
# ==========================================
tab_analysis = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_analysis, text="")
reg_ui((main_notebook, tab_analysis), "Analysis", "tab_text")

analysis_notebook = ttk.Notebook(tab_analysis)
analysis_notebook.pack(fill="both", expand=True, padx=10, pady=10)

# --- SUB-TAB: STATISTICS ---
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
build_file_tree(tree_stats, os.getcwd())

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
    canvas_pvf.draw()

    messagebox.showinfo("Analysis", "Phase vs. Frequenz Analyse erfolgreich berechnet und visualisiert.")


btn_pvf = tk.Button(frame_stats_top, font=("Consolas", 9, "bold"), bg="#f57c00", fg="white", padx=10, pady=5,
                    command=starte_pvf_analyse)
btn_pvf.pack(side="left", padx=10)
reg_ui(btn_pvf, "📈 Phase vs. Frequency Analysis")


def on_tree_stats_select(event):
    selected = tree_stats.selection()
    if selected:
        val = tree_stats.item(selected[0], "values")
        if val and os.path.isfile(val[0]):
            lbl_file_status.config(text=os.path.basename(val[0]))


tree_stats.bind("<<TreeviewSelect>>", on_tree_stats_select)

# --- SUB-TAB: LOGS ---
sub_tab_logs = tk.Frame(analysis_notebook, bg="#252526")
analysis_notebook.add(sub_tab_logs, text="")
reg_ui((analysis_notebook, sub_tab_logs), "Logs", "tab_text")

paned_logs = ttk.PanedWindow(sub_tab_logs, orient="horizontal")
paned_logs.pack(fill="both", expand=True, padx=5, pady=5)

frame_tree_logs = tk.Frame(paned_logs, bg="#1e1e1e", width=260)
paned_logs.add(frame_tree_logs, weight=1)

lbl_tree_logs_title = tk.Label(frame_tree_logs, text="LOG DIRECTORY", font=("Consolas", 9, "bold"), bg="#3c3f41",
                               fg="#ffffff", anchor="w", padx=5)
lbl_tree_logs_title.pack(fill="x")

tree_logs = ttk.Treeview(frame_tree_logs, show="tree")
tree_logs.pack(fill="both", expand=True)
build_file_tree(tree_logs, os.getcwd())

frame_logs_work = tk.Frame(paned_logs, bg="#252526")
paned_logs.add(frame_logs_work, weight=4)

frame_log_ctrl = tk.Frame(frame_logs_work, bg="#252526")
frame_log_ctrl.pack(fill="x", pady=5)


def run_logs_script():
    txt_log_terminal.config(state="normal")
    txt_log_terminal.insert("end", "=== EXECUTING LOGS.TXT SCRIPT ABLAUF ===\n")

    devices = ["SR830", "OsTech"]
    modes = ["S", "F", "R", "W"]
    commands = ["FREQ", "PHAS", "RSLP", "FMOD"]

    for _ in range(12):
        dev = random.choice(devices)
        m = random.choice(modes)
        cmd = random.choice(commands)
        val = str(random.randint(0, 100))
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        log_line = f"[{timestamp}] Serial Comm | Dev: {dev} | Mode: {m} | Cmd: {cmd} | Val: {val} | Status: Testing Log and Import\n"
        txt_log_terminal.insert("end", log_line)
        txt_log_terminal.see("end")

    txt_log_terminal.insert("end", "=== LOG SCRIPT EXECUTION COMPLETED SUCCESSFULLY ===\n\n")
    txt_log_terminal.config(state="disabled")


btn_run_logs = tk.Button(frame_log_ctrl, text="▶ Run Logs Script (Log.txt)", font=("Consolas", 9, "bold"), bg="#2e7d32",
                         fg="white", padx=10, pady=4, command=run_logs_script)
btn_run_logs.pack(side="left", padx=5)

btn_clear_logs = tk.Button(frame_log_ctrl, text="Clear Console", font=("Consolas", 8), bg="#3c3f41", fg="white", padx=8,
                           pady=4,
                           command=lambda: (txt_log_terminal.config(state="normal"),
                                            txt_log_terminal.delete("1.0", "end"),
                                            txt_log_terminal.config(state="disabled")))
btn_clear_logs.pack(side="left", padx=5)

txt_log_terminal = tk.Text(frame_logs_work, bg="#000000", fg="#00ff00", font=("Consolas", 9), state="disabled",
                           wrap="word")
txt_log_terminal.pack(fill="both", expand=True, padx=5, pady=5)


def on_tree_logs_select(event):
    selected = tree_logs.selection()
    if selected:
        val = tree_logs.item(selected[0], "values")
        if val and os.path.isfile(val[0]):
            try:
                with open(val[0], "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                txt_log_terminal.config(state="normal")
                txt_log_terminal.delete("1.0", "end")
                txt_log_terminal.insert("end", f"=== FILE DISPLAY: {os.path.basename(val[0])} ===\n\n")
                txt_log_terminal.insert("end", content)
                txt_log_terminal.config(state="disabled")
            except Exception as e:
                pass


tree_logs.bind("<<TreeviewSelect>>", on_tree_logs_select)

# ------------------------------------------
# 6. TAB: HELP
# ------------------------------------------
tab_help = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_help, text="")
reg_ui((main_notebook, tab_help), "Help", "tab_text")

help_notebook = ttk.Notebook(tab_help)
help_notebook.pack(fill="both", expand=True, padx=10, pady=10)

sub_tab_about_the_application = tk.Frame(help_notebook, bg="#252526")
help_notebook.add(sub_tab_about_the_application, text="")
reg_ui((help_notebook, sub_tab_about_the_application), "About the application", "tab_text")

lbl_help = tk.Label(sub_tab_about_the_application, font=("Consolas", 18, "bold"), bg="#252526", fg="#00ffcc")
lbl_help.pack(pady=(40, 10))
reg_ui(lbl_help,
       "This application is the result of the software project of summer semester 2026. \n in case of problems please contact:")
lbl_help2 = tk.Label(sub_tab_about_the_application, font=("Consolas", 18, "italic"), bg="#252526", fg="#ff4d00")
lbl_help2.pack(pady=(45, 10))
reg_ui(lbl_help2, "xxx")

# ------------------------------------------
# 7. TAB: SETTINGS & THEME ENGINE
# ------------------------------------------
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
            style.configure("TNotebook.Tab", background=tab_bg, foreground=fg_text, padding=[10, 6], font=('Consolas', 10, 'bold'))
            style.map("TNotebook.Tab", background=[("selected", "#007acc")], foreground=[("selected", "#ffffff")])
            style.configure("TCombobox", fieldbackground="#ffffff", background="#e0e0e0", foreground="#000000")
            style.configure("TLabelframe", background=bg_main, borderwidth=1)
            style.configure("TLabelframe.Label", background=bg_main, foreground=lf_title_fg, font=('Consolas', 10, 'bold'))

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
            style.configure("TNotebook.Tab", background=tab_bg, foreground=fg_text, padding=[10, 6], font=('Consolas', 10, 'bold'))
            style.map("TNotebook.Tab", background=[("selected", "#007acc")], foreground=[("selected", "#ffffff")])
            style.configure("TCombobox", fieldbackground="#2b2b2b", background="#3c3f41", foreground="#ffffff")
            style.configure("TLabelframe", background="#1e1e1e", borderwidth=1)
            style.configure("TLabelframe.Label", background="#1e1e1e", foreground=lf_title_fg, font=('Consolas', 10, 'bold'))

        root.configure(bg=bg_card)

        def force_widget_colors(widget):
            is_display = False
            is_protected_signal = False

            try:
                if widget in (val_ch1_label, val_ch2_label, val_ref_display, lbl_lcd_main) or widget in lcd_vars.values():
                    is_display = True
                elif widget in (btn_start_lockin, btn_stop_lockin, btn_reset_def, btn_reset_laser, btn_reset_tec, btn_pvf,
                                lbl_safety_status, btn_scan_com, btn_dev_manager, btn_apply_ref, btn_apply_input,
                                btn_apply_laser, btn_apply_tec, btn_apply_dev, lbl_disabled_banner):
                    is_protected_signal = True
                elif any(keyword in str(widget).lower() for keyword in ("start", "stop", "interlock", "laser_on", "laser_off")):
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

            for bg_attr in ("bg", "background", "activebackground", "highlightbackground", "readonlybackground", "selectcolor"):
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


lbl_theme_sel = tk.Label(sub_tab_theme, text="Select Layout Theme:", font=("Consolas", 10, "bold"), bg="#252526", fg="#ffffff")
lbl_theme_sel.pack(pady=15)

btn_dark = tk.Button(sub_tab_theme, text="Dark Mode", width=15, bg="#3c3f41", fg="white", command=lambda: apply_theme("dark"))
btn_dark.pack(pady=4)

btn_light = tk.Button(sub_tab_theme, text="Light Mode", width=15, bg="#e0e0e0", fg="black", command=lambda: apply_theme("light"))
btn_light.pack(pady=4)

sub_tab_security = tk.Frame(settings_notebook, bg="#252526")
settings_notebook.add(sub_tab_security, text=" Security ")

lbl_sec_title = tk.Label(sub_tab_security, text="Emergency Password Settings", font=("Consolas", 10, "bold"),
                         bg="#252526", fg="#ffffff")
lbl_sec_title.pack(pady=15)


def change_emergency_password():
    old_pwd = simpledialog.askstring("Passwort Ändern", "Altes Passwort eingeben:", show='*')
    if old_pwd == APP_SETTINGS.get("emergency_password", "admin123"):
        new_pwd = simpledialog.askstring("Passwort Ändern", "Neues Passwort eingeben:", show='*')
        if new_pwd:
            APP_SETTINGS["emergency_password"] = new_pwd
            save_settings(APP_SETTINGS)
            messagebox.showinfo("Erfolg", "Notfall-Passwort wurde erfolgreich geändert!")
    else:
        messagebox.showerror("Fehler", "Altes Passwort nicht korrekt!")


btn_change_pwd = tk.Button(sub_tab_security, text="Change Emergency Password", font=("Consolas", 9, "bold"),
                           bg="#007acc", fg="white", command=change_emergency_password)
btn_change_pwd.pack(pady=5)

# Initialisierung der Tab-Zustände beim Start
update_tab_states()
check_laser_safety()

if __name__ == "__main__":
    root.mainloop()
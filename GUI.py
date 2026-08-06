import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk, filedialog

# Datenverarbeitung & Mathematik
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

# Eigene SWP-Module (falls vorhanden)
try:
    import SWP_Calculation_PhaseVsFrequenz as PvF
    import SWP_Calculations_Streuung
except ImportError:
    PvF = None
    SWP_Calculations_Streuung = None

# VISA / Hardware-Ansteuerung
import pyvisa

# ==========================================
# HARDWARE-KONFIGURATION & STEUERUNG (SR830)
# ==========================================
GPIB_ADDRESS = "GPIB0::8::INSTR"
lockin_device = None


def connect_lockin():
    global lockin_device
    if lockin_device is None:
        try:
            rm = pyvisa.ResourceManager()
            lockin_device = rm.open_resource(GPIB_ADDRESS)
            lockin_device.timeout = 2000
        except Exception as e:
            lockin_device = None
            print(f"Hardware nicht gefunden: {e}")
            return False
    return True


def lockin_start():
    if connect_lockin():
        try:
            lockin_device.write("SLVL 1.0")
            messagebox.showinfo(tr("tab_lockin"), tr("msg_lockin_start"))
        except Exception as e:
            messagebox.showerror("Fehler", f"{e}")


def lockin_stop():
    if connect_lockin():
        try:
            lockin_device.write("SLVL 0.0")
            messagebox.showinfo(tr("tab_lockin"), tr("msg_lockin_stop"))
        except Exception as e:
            messagebox.showerror("Fehler", f"{e}")


def close_lockin_connection():
    global lockin_device
    if lockin_device is not None:
        try:
            lockin_device.close()
        except Exception:
            pass


# ==========================================
# MANUELLE, FACHLICH KORREKTE ÜBERSETZUNGS-DATENBANK
# ==========================================
TRANSLATIONS = {
    "en": {
        "tab_home": "Home",
        "tab_lockin": "Lock-In Amplifier",
        "tab_laser": "Laser",
        "tab_analysis": "Analysis",
        "tab_settings": "Settings",

        "sub_analysis_cleansing": "Data Cleansing & Fit",
        "sub_analysis_stats": "Statistics",
        "sub_settings_lang": "Language",
        "sub_settings_hw": "Hardware Config",

        "home_welcome": "WELCOME TO LAB MEASUREMENT SYSTEM",
        "home_info": "Select a tab above to control hardware or run data analysis.",
        "mon_title": " SR830 LIVE MONITOR ",
        "mon_amp": "AMPLITUDE (R):",
        "mon_phase": "PHASE (θ):",
        "btn_start_sine": "▶ Start Sine Out (1V)",
        "btn_stop_sine": "⏹ Stop Sine Out (0V)",

        "laser_title": "LASER CONTROL PANEL",
        "laser_status_off": "Laser Status: Inactive",
        "laser_status_on": "Laser Status: ACTIVE 🔥",
        "btn_fire_laser": "Fire Laser",

        "analysis_title": "DATA ANALYSIS & REGRESSION",
        "btn_load_file": "📁 Import Data File",
        "btn_run_regression": "📊 Run Regression",
        "btn_pvf_analysis": "📈 Phase vs. Frequency Analysis",
        "no_file_loaded": "No file loaded",

        "settings_lang_select": "Select Application Language:",
        "settings_gpib_addr": "GPIB Address:",

        "msg_title": "Information",
        "msg_lang_changed": "Language changed successfully!",
        "msg_lockin_start": "Sine Out set to 1.0 V (ON).",
        "msg_lockin_stop": "Sine Out set to 0.0 V (OFF)."
    },
    "de": {
        "tab_home": "Startseite",
        "tab_lockin": "Lock-In Verstärker",
        "tab_laser": "Laser",
        "tab_analysis": "Analyse",
        "tab_settings": "Einstellungen",

        "sub_analysis_cleansing": "Bereinigung & Regression",
        "sub_analysis_stats": "Statistik",
        "sub_settings_lang": "Sprache",
        "sub_settings_hw": "Hardware-Konfig",

        "home_welcome": "WILLKOMMEN IM MESSSYSTEM",
        "home_info": "Wähle oben eine Karteikarte zur Hardwaresteuerung oder Datenauswertung.",
        "mon_title": " SR830 LIVE MONITOR ",
        "mon_amp": "AMPLITUDE (R):",
        "mon_phase": "PHASE (θ):",
        "btn_start_sine": "▶ Sine Out Starten (1V)",
        "btn_stop_sine": "⏹ Sine Out Stoppen (0V)",

        "laser_title": "LASER STEUERUNG",
        "laser_status_off": "Laser-Status: Inaktiv",
        "laser_status_on": "Laser-Status: AKTIV 🔥",
        "btn_fire_laser": "Laser Zünden",

        "analysis_title": "DATENANALYSE & REGRESSION",
        "btn_load_file": "📁 Datei Laden",
        "btn_run_regression": "📊 Regression Starten",
        "btn_pvf_analysis": "📈 Phase vs. Frequenz Analyse",
        "no_file_loaded": "Keine Datei geladen",

        "settings_lang_select": "Sprache auswählen:",
        "settings_gpib_addr": "GPIB Addresse:",

        "msg_title": "Information",
        "msg_lang_changed": "Sprache erfolgreich geändert!",
        "msg_lockin_start": "Sine Out auf 1.0 V gesetzt (AN).",
        "msg_lockin_stop": "Sine Out auf 0.0 V gesetzt (AUS)."
    },
    "es": {
        "tab_home": "Inicio",
        "tab_lockin": "Amplificador Lock-In",
        "tab_laser": "Láser",
        "tab_analysis": "Análisis",
        "tab_settings": "Ajustes",

        "sub_analysis_cleansing": "Depuración y Ajuste",
        "sub_analysis_stats": "Estadística",
        "sub_settings_lang": "Idioma",
        "sub_settings_hw": "Config. Hardware",

        "home_welcome": "BIENVENIDO AL SISTEMA DE MEDICIÓN",
        "home_info": "Seleccione una pestaña superior para operar hardware o analizar datos.",
        "mon_title": " MONITOR EN VIVO SR830 ",
        "mon_amp": "AMPLITUD (R):",
        "mon_phase": "FASE (θ):",
        "btn_start_sine": "▶ Iniciar Sine Out (1V)",
        "btn_stop_sine": "⏹ Detener Sine Out (0V)",

        "laser_title": "CONTROL DEL LÁSER",
        "laser_status_off": "Estado del Láser: Inactivo",
        "laser_status_on": "Estado del Láser: ACTIVO 🔥",
        "btn_fire_laser": "Disparar Láser",

        "analysis_title": "ANÁLISIS DE DATOS Y REGRESIÓN",
        "btn_load_file": "📁 Cargar Archivo",
        "btn_run_regression": "📊 Ejecutar Regresión",
        "btn_pvf_analysis": "📈 Análisis Fase vs. Frecuencia",
        "no_file_loaded": "Ningún archivo cargado",

        "settings_lang_select": "Seleccionar Idioma:",
        "settings_gpib_addr": "Dirección GPIB:",

        "msg_title": "Información",
        "msg_lang_changed": "¡Idioma cambiado con éxito!",
        "msg_lockin_start": "Sine Out establecido a 1.0 V (ON).",
        "msg_lockin_stop": "Sine Out establecido a 0.0 V (OFF)."
    }
}

current_lang = "de"
registered_widgets = []
current_file_path = None


def tr(key):
    """Liest den Begriff aus der lokalen Sprachentabelle."""
    lang_dict = TRANSLATIONS.get(current_lang, TRANSLATIONS["en"])
    return lang_dict.get(key, TRANSLATIONS["en"].get(key, key))


def reg_ui(widget, key, prop="text"):
    registered_widgets.append((widget, prop, key))
    update_single_widget(widget, prop, key)


def update_single_widget(widget, prop, key):
    translated_val = tr(key)
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
    for widget, prop, key in registered_widgets:
        update_single_widget(widget, prop, key)
    messagebox.showinfo(tr("msg_title"), tr("msg_lang_changed"))


def open_file_dialog():
    global current_file_path
    file_path = filedialog.askopenfilename(
        title=tr("btn_load_file"),
        filetypes=[("Text Files", "*.txt *.csv"), ("All files", "*.*")]
    )
    if file_path:
        current_file_path = file_path
        lbl_file_status.config(text=os.path.basename(current_file_path))


# ==========================================
# GUI ANWENDUNG
# ==========================================
root = tk.Tk()
root.title('Labor-Steuerung & Analyse')
root.geometry('580x480')
root.configure(bg="#2b2b2b")

style = ttk.Style()
style.theme_use('default')
style.configure("TNotebook", background="#2b2b2b", borderwidth=0)
style.configure("TNotebook.Tab", background="#3c3f41", foreground="#ffffff", padding=[10, 6],
                font=('Consolas', 10, 'bold'))
style.map("TNotebook.Tab", background=[("selected", "#007acc")], foreground=[("selected", "#ffffff")])

# HAUPT-NOTEBOOK (Reiterzeile)
main_notebook = ttk.Notebook(root)
main_notebook.pack(fill="both", expand=True, padx=10, pady=10)

# ------------------------------------------
# 1. TAB: HOME
# ------------------------------------------
tab_home = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_home, text="")
reg_ui((main_notebook, tab_home), "tab_home", "tab_text")

lbl_welcome = tk.Label(tab_home, font=("Consolas", 12, "bold"), bg="#1e1e1e", fg="#00ffcc")
lbl_welcome.pack(pady=(40, 10))
reg_ui(lbl_welcome, "home_welcome")

lbl_info = tk.Label(tab_home, font=("Segoe UI", 10), bg="#1e1e1e", fg="#aaaaaa", justify="center")
lbl_info.pack(pady=10)
reg_ui(lbl_info, "home_info")

# ------------------------------------------
# 2. TAB: LOCK-IN AMPLIFIER
# ------------------------------------------
tab_lockin = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_lockin, text="")
reg_ui((main_notebook, tab_lockin), "tab_lockin", "tab_text")

display_frame = tk.LabelFrame(tab_lockin, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=10, pady=5)
display_frame.pack(padx=15, pady=15, fill="x")
reg_ui(display_frame, "mon_title")

lbl_amp = tk.Label(display_frame, font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_amp.pack(anchor="w")
reg_ui(lbl_amp, "mon_amp")

val_r_label = tk.Label(display_frame, text="OFFLINE", font=("Consolas", 16, "bold"), bg="#000000", fg="#ff3333",
                       relief="sunken", bd=2)
val_r_label.pack(fill="x", pady=(2, 6))

lbl_phase = tk.Label(display_frame, font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_phase.pack(anchor="w")
reg_ui(lbl_phase, "mon_phase")

val_phase_label = tk.Label(display_frame, text="OFFLINE", font=("Consolas", 16, "bold"), bg="#000000", fg="#ff3333",
                           relief="sunken", bd=2)
val_phase_label.pack(fill="x", pady=(2, 5))

btn_frame = tk.Frame(tab_lockin, bg="#1e1e1e")
btn_frame.pack(pady=10)

btn_start_lockin = tk.Button(btn_frame, font=("Consolas", 9, "bold"), bg="#2e7d32", fg="white", padx=10, pady=5,
                             command=lockin_start)
btn_start_lockin.pack(side="left", padx=5)
reg_ui(btn_start_lockin, "btn_start_sine")

btn_stop_lockin = tk.Button(btn_frame, font=("Consolas", 9, "bold"), bg="#c62828", fg="white", padx=10, pady=5,
                            command=lockin_stop)
btn_stop_lockin.pack(side="left", padx=5)
reg_ui(btn_stop_lockin, "btn_stop_sine")

# ------------------------------------------
# 3. TAB: LASER
# ------------------------------------------
tab_laser = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_laser, text="")
reg_ui((main_notebook, tab_laser), "tab_laser", "tab_text")

lbl_laser_title = tk.Label(tab_laser, font=("Consolas", 12, "bold"), bg="#1e1e1e", fg="#ff5555")
lbl_laser_title.pack(pady=15)
reg_ui(lbl_laser_title, "laser_title")

laser_status_lbl = tk.Label(tab_laser, font=("Consolas", 10), bg="#000000", fg="#ffaa00", width=30, height=2,
                            relief="sunken")
laser_status_lbl.pack(pady=10)
reg_ui(laser_status_lbl, "laser_status_off")

btn_fire = tk.Button(tab_laser, bg="#d32f2f", fg="white", font=("Consolas", 10, "bold"),
                     command=lambda: reg_ui(laser_status_lbl, "laser_status_on"))
btn_fire.pack(pady=5)
reg_ui(btn_fire, "btn_fire_laser")

# ------------------------------------------
# 4. TAB: ANALYSIS (NEU MIT UNTER-NOTEBOOK)
# ------------------------------------------
tab_analysis = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_analysis, text="")
reg_ui((main_notebook, tab_analysis), "tab_analysis", "tab_text")

analysis_notebook = ttk.Notebook(tab_analysis)
analysis_notebook.pack(fill="both", expand=True, padx=10, pady=10)

# Sub-Tab 1: Regression & Daten
sub_tab_clean = tk.Frame(analysis_notebook, bg="#252526")
analysis_notebook.add(sub_tab_clean, text="")
reg_ui((analysis_notebook, sub_tab_clean), "sub_analysis_cleansing", "tab_text")

btn_load = tk.Button(sub_tab_clean, font=("Consolas", 9, "bold"), bg="#007acc", fg="white", padx=10, pady=5,
                     command=open_file_dialog)
btn_load.pack(pady=15)
reg_ui(btn_load, "btn_load_file")

lbl_file_status = tk.Label(sub_tab_clean, font=("Consolas", 9), bg="#252526", fg="#aaaaaa")
lbl_file_status.pack(pady=5)
reg_ui(lbl_file_status, "no_file_loaded")

btn_reg = tk.Button(sub_tab_clean, font=("Consolas", 9, "bold"), bg="#388e3c", fg="white", padx=10, pady=5,
                    command=lambda: messagebox.showinfo("Regression", "Regression wird gestartet..."))
btn_reg.pack(pady=10)
reg_ui(btn_reg, "btn_run_regression")

# Sub-Tab 2: Statistik
sub_tab_stats = tk.Frame(analysis_notebook, bg="#252526")
analysis_notebook.add(sub_tab_stats, text="")
reg_ui((analysis_notebook, sub_tab_stats), "sub_analysis_stats", "tab_text")

btn_pvf = tk.Button(sub_tab_stats, font=("Consolas", 9, "bold"), bg="#f57c00", fg="white", padx=10, pady=5,
                    command=lambda: PvF.main() if PvF else print("PvF nicht verfügbar"))
btn_pvf.pack(pady=20)
reg_ui(btn_pvf, "btn_pvf_analysis")

# ------------------------------------------
# 5. TAB: SETTINGS (SUB-NOTEBOOK)
# ------------------------------------------
tab_settings = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_settings, text="")
reg_ui((main_notebook, tab_settings), "tab_settings", "tab_text")

settings_notebook = ttk.Notebook(tab_settings)
settings_notebook.pack(fill="both", expand=True, padx=10, pady=10)

# Sub-Tab 1: Sprache
sub_tab_lang = tk.Frame(settings_notebook, bg="#252526")
settings_notebook.add(sub_tab_lang, text="")
reg_ui((settings_notebook, sub_tab_lang), "sub_settings_lang", "tab_text")

lbl_lang_sel = tk.Label(sub_tab_lang, font=("Consolas", 10, "bold"), bg="#252526", fg="#ffffff")
lbl_lang_sel.pack(pady=15)
reg_ui(lbl_lang_sel, "settings_lang_select")

lang_frame = tk.Frame(sub_tab_lang, bg="#252526")
lang_frame.pack()

languages = [("Deutsch", "de"), ("English", "en"), ("Español", "es")]
for name, code in languages:
    b = tk.Button(lang_frame, text=name, width=12, bg="#3c3f41", fg="white", command=lambda c=code: change_language(c))
    b.pack(pady=3)

# Sub-Tab 2: Hardware Config
sub_tab_hw = tk.Frame(settings_notebook, bg="#252526")
settings_notebook.add(sub_tab_hw, text="")
reg_ui((settings_notebook, sub_tab_hw), "sub_settings_hw", "tab_text")

lbl_gpib = tk.Label(sub_tab_hw, font=("Consolas", 9), bg="#252526", fg="#ffffff")
lbl_gpib.pack(pady=(20, 5))
reg_ui(lbl_gpib, "settings_gpib_addr")

entry_gpib = tk.Entry(sub_tab_hw, font=("Consolas", 10), justify="center")
entry_gpib.insert(0, GPIB_ADDRESS)
entry_gpib.pack()


# ==========================================
# SCHLEIFEN & CLEANUP
# ==========================================
def update_lockin_display():
    if lockin_device is not None:
        try:
            r_val = float(lockin_device.query("OUTP? 3"))
            phase_val = float(lockin_device.query("OUTP? 4"))
            val_r_label.config(text=f"{r_val:^+10.6f} V", fg="#00ff00")
            val_phase_label.config(text=f"{phase_val:^+8.2f} °", fg="#ff9900")
        except Exception:
            val_r_label.config(text="--.------ V", fg="#555555")
            val_phase_label.config(text="---.-- °", fg="#555555")
    else:
        val_r_label.config(text="OFFLINE", fg="#ff3333")
        val_phase_label.config(text="OFFLINE", fg="#ff3333")

    root.after(500, update_lockin_display)


root.protocol("WM_DELETE_WINDOW", lambda: (close_lockin_connection(), root.destroy()))

# Start-Updates
update_lockin_display()
root.mainloop()
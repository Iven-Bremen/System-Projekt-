import os
import sys
import platform
import re
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk, filedialog

# Übersetzungs-Bibliothek
from deep_translator import GoogleTranslator

# Datenverarbeitung & Mathematik
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.optimize import curve_fit
from scipy.stats import norm

# Eigene SWP-Module
import SWP_Calculation_PhaseVsFrequenz as PvF
import SWP_Calculation_TimeVsNitrierschicht as TvN
import SWP_Calculations_Streuung

# VISA / Hardware-Ansteuerung
import pyvisa

# ==========================================
# HARDWARE-KONFIGURATION (LOCK-IN SR830)
# ==========================================
GPIB_ADDRESS = "GPIB0::8::INSTR"  # Adresse ggf. anpassen
lockin_device = None


def connect_lockin():
    """Stellt die VISA-Verbindung zum SR830 her, falls noch nicht geschehen."""
    global lockin_device
    if lockin_device is None:
        try:
            rm = pyvisa.ResourceManager()
            lockin_device = rm.open_resource(GPIB_ADDRESS)
            lockin_device.timeout = 2000  # Kurz gehalten, damit die GUI nicht blockiert
            idn = lockin_device.query("*IDN?")
            print(f"Verbunden mit: {idn.strip()}")
        except Exception as e:
            lockin_device = None
            # Hinweis: Fehlermeldung nur im Terminal ausgeben, um die GUI-Schleife nicht dauerhaft zu stoppen
            print(f"Hardware-Verbindung fehlgeschlagen: {e}")
            return False
    return True


def lockin_start():
    """Schaltet den Sine Out des SR830 an (1.0 V)."""
    if connect_lockin():
        try:
            lockin_device.write("SLVL 1.0")
            messagebox.showinfo("Lock-In Amplifier", "Sine Out wurde auf 1.0 V gesetzt (AN).")
        except Exception as e:
            messagebox.showerror("Fehler", f"Befehl konnte nicht gesendet werden:\n{e}")


def lockin_stop():
    """Schaltet den Sine Out des SR830 aus (0.0 V)."""
    if connect_lockin():
        try:
            lockin_device.write("SLVL 0.0")
            messagebox.showinfo("Lock-In Amplifier", "Sine Out wurde auf 0.0 V gesetzt (AUS).")
        except Exception as e:
            messagebox.showerror("Fehler", f"Befehl konnte nicht gesendet werden:\n{e}")


def close_lockin_connection():
    """Trennt die VISA-Verbindung sauber beim Beenden."""
    global lockin_device
    if lockin_device is not None:
        try:
            lockin_device.close()
            print("Lock-In Verbindung geschlossen.")
        except Exception:
            pass


# ==========================================
# LIVE-ANZEIGE LOGIK (SR830 MONITOR)
# ==========================================
def update_lockin_display():
    """Liest regelmäßig Messwerte vom SR830 aus und aktualisiert die Digitalanzeige."""
    if lockin_device is not None:
        try:
            # OUTP? 3 = Amplitude R, OUTP? 4 = Phase
            x_val = float(lockin_device.query("OUTP? 1"))
            y_val = float(lockin_device.query("OUTP? 2"))
            r_val = float(lockin_device.query("OUTP? 3"))
            phase_val = float(lockin_device.query("OUTP? 4"))

            # Formatierung im Digital-Stil
            val_x_label.config(text=f"{x_val:^+10.6f} V", fg="#00ff00")
            val_y_label.config(text=f"{y_val:^+10.6f} V", fg="#00ff00")
            val_r_label.config(text=f"{r_val:^+10.6f} V", fg="#00ff00")
            val_phase_label.config(text=f"{phase_val:^+8.2f} °", fg="#ff9900")
        except Exception:
            val_x_label.config(text="--.------ V", fg="#555555")
            val_y_label.config(text="--.------ V", fg="#555555")
            val_r_label.config(text="--.------ V", fg="#555555")
            val_phase_label.config(text="---.-- °", fg="#555555")
    else:
        val_r_label.config(text="OFFLINE", fg="#ff3333")
        val_phase_label.config(text="OFFLINE", fg="#ff3333")

    # Aktualisierung alle 500 ms (0,5 Sekunden)
    root.after(500, update_lockin_display)


# ==========================================
# ANWENDUNGS-LOGIK & DATEI-MANAGEMENT
# ==========================================
current_file_path = None


def open_file_dialog():
    global current_file_path
    file_path = filedialog.askopenfilename(
        title="Datei auswählen",
        filetypes=[
            ("All supported Files", "*.txt *.csv *.xlsx *.json"),
            ("Text Files", "*.txt"),
            ("CSV Files", "*.csv"),
            ("XLSX Files", "*.xlsx"),
            ("JSON Files", "*.json"),
            ("All files", "*.*")
        ]
    )
    if file_path:
        current_file_path = file_path
        print(f"Geladene Datei: {current_file_path}")
        messagebox.showinfo("Import erfolgreich", f"Datei geladen:\n{os.path.basename(current_file_path)}")


def remove_file_from_app():
    global current_file_path
    if current_file_path is None:
        messagebox.showwarning("Hinweis", "Es ist derzeit keine Datei geladen!")
        return

    filename = os.path.basename(current_file_path)
    current_file_path = None
    print("Datei aus dem Speicher entfernt.")
    messagebox.showinfo("Entfernt", f"Die Datei '{filename}' wurde aus dem Programm entladen.")


def starte_regression(dateipfad):
    try:
        frequenzen, sweeps = SWP_Calculations_Streuung.lade_ptr_datei(dateipfad)
        f, phase, sigma = SWP_Calculations_Streuung.bereite_daten_auf(frequenzen, sweeps)
        popt, perr = SWP_Calculations_Streuung.fitte_regression(f, phase, sigma)
        fit, residuen = SWP_Calculations_Streuung.berechne_residuen(f, phase, popt)

        SWP_Calculations_Streuung.statistik(f, residuen)
        SWP_Calculations_Streuung.plot_ergebnis(f, phase, sigma, fit, residuen, popt, sweeps)
    except Exception as e:
        messagebox.showerror("Berechnungsfehler", f"Fehler bei der Regression:\n{e}")


# ==========================================
# ÜBERSETZUNGS-DATENBANK & AUTOMATISIERUNG
# ==========================================
BASE_MENU_EN = {
    "menu_data": "Data", "menu_data_new": "New", "menu_data_open": "Open", "menu_data_save": "Save",
    "menu_data_saveas": "Save as", "menu_data_import": "Import", "menu_data_export": "Export",
    "menu_data_removefile": "Remove file", "menu_data_quit": "Quit",
    "menu_analysis": "Analysis", "menu_analysis_clean": "Data cleansing",
    "menu_analysis_stats": "Calculating Statistics", "menu_analysis_chart": "Plot Chart Type",
    "menu_analysis_outliers": "Detect Outliers",
    "menu_view": "View", "menu_view_chart": "Change Chart Type", "menu_view_colour": "Colour Assignment",
    "menu_view_fullscreen": "Full Screen", "menu_view_zoom": "Zoom",
    "menu_settings": "Settings", "menu_settings_units": "Units", "menu_language": "Languages",
    "menu_settings_schemes": "Colour Schemes", "menu_settings_thresholds": "Defining Thresholds",
    "menu_help": "Help", "menu_help_doc": "Documentation", "menu_help_about": "About The Application",
    "menu_help_version": "Version Number",
    "menu_laser": "Laser", "menu_laser_start": "Start Laser", "menu_laser_stop": "Stop Laser",
    "menu_lock_in_amplifier": "Lock-In Amplifier", "menu_lock_in_amplifier_start": "Start Lock-In Amplifier",
    "menu_lock_in_amplifier_stop": "Stop Lock-In Amplifier",
    "msg_title": "Info", "msg_text": "Language changed successfully!"
}

current_lang = "en"
menu_registry = []
translation_cache = {"en": BASE_MENU_EN.copy()}


def get_translation(key, lang):
    if lang not in translation_cache:
        translation_cache[lang] = {}
    if key in translation_cache[lang]:
        return translation_cache[lang][key]
    if lang == "en":
        return BASE_MENU_EN.get(key, key)
    try:
        english_text = BASE_MENU_EN.get(key, key)
        translated_text = GoogleTranslator(source='en', target=lang).translate(english_text)
        translation_cache[lang][key] = translated_text
        return translated_text
    except Exception as e:
        print(f"Übersetzungsfehler ({key}): {e}")
        return BASE_MENU_EN.get(key, key)


def change_language(lang_code):
    global current_lang
    current_lang = lang_code
    update_all_menus()
    messagebox.showinfo(get_translation("msg_title", current_lang), get_translation("msg_text", current_lang))


def update_all_menus():
    for i, (menu_obj, current_label, json_key) in enumerate(menu_registry):
        new_label = get_translation(json_key, current_lang)
        try:
            menu_obj.entryconfigure(current_label, label=new_label)
            menu_registry[i] = (menu_obj, new_label, json_key)
        except tk.TclError:
            pass


# ==========================================
# MENÜ-STRUKTUR DEFINITION
# ==========================================
MENU_STRUCTURE = [
    ("main", "menu_laser", "submenu_laser"),
    ("main", "menu_lock_in_amplifier", "submenu_lock_in_amplifier"),
    ("main", "menu_data", "submenu_data"),
    ("main", "menu_analysis", "submenu_analysis"),
    ("main", "menu_view", "submenu_view"),
    ("main", "menu_settings", "submenu_settings"),
    ("main", "menu_help", "submenu_help"),

    ("submenu_laser", "menu_laser_start", lambda: print("laser_start")),
    ("submenu_laser", "sep", None),
    ("submenu_laser", "menu_laser_stop", lambda: print("laser_stop")),

    ("submenu_lock_in_amplifier", "menu_lock_in_amplifier_start", lockin_start),
    ("submenu_lock_in_amplifier", "sep", None),
    ("submenu_lock_in_amplifier", "menu_lock_in_amplifier_stop", lockin_stop),

    ("submenu_data", "menu_data_new", lambda: print("new")),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_open", lambda: print("open")),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_save", lambda: print("save")),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_saveas", lambda: print("save_as")),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_import", open_file_dialog),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_export", lambda: print("export")),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_removefile", remove_file_from_app),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_quit", "DESTROY_APP"),

    ("submenu_analysis", "menu_analysis_clean", lambda: print("clean")),
    ("submenu_analysis", "sep", None),
    ("submenu_analysis", "menu_analysis_stats", lambda: starte_regression(
        dateipfad=current_file_path or r"C:\Users\aouch\PycharmProjects\PythonProject\20190701_181338_MP1_QC19C(1).txt")),
    ("submenu_analysis", "sep", None),
    ("submenu_analysis", "menu_analysis_stats", lambda: PvF.main()),
    ("submenu_analysis", "sep", None),
    ("submenu_analysis", "menu_analysis_outliers", lambda: print("outliers")),

    ("submenu_view", "menu_view_chart", lambda: print("chart")),
    ("submenu_view", "sep", None),
    ("submenu_view", "menu_view_colour", lambda: print("colour")),
    ("submenu_view", "sep", None),
    ("submenu_view", "menu_view_fullscreen", lambda: print("fullscreen")),
    ("submenu_view", "sep", None),
    ("submenu_view", "menu_view_zoom", lambda: print("zoom")),

    ("submenu_settings", "menu_settings_units", lambda: print("units")),
    ("submenu_settings", "sep", None),
    ("submenu_settings", "menu_language", "subsetting_languages"),
    ("submenu_settings", "sep", None),
    ("submenu_settings", "menu_settings_schemes", lambda: print("scheme")),
    ("submenu_settings", "sep", None),
    ("submenu_settings", "menu_settings_thresholds", lambda: print("threshold")),

    ("submenu_help", "menu_help_doc", lambda: print("doc")),
    ("submenu_help", "sep", None),
    ("submenu_help", "menu_help_about", lambda: print("about")),
    ("submenu_help", "sep", None),
    ("submenu_help", "menu_help_version", lambda: print("version"))
]

# ==========================================
# GUI AUFBAU
# ==========================================
root = tk.Tk()
root.title('GUI for processing nightriding')
root.geometry('500x400')
root.configure(bg="#2b2b2b")  # Dunkler Hintergrund für das Hauptfenster

# ------------------------------------------
# HIER IST DIE DIGITALUHR-ANZEIGE IM FENSTER
# ------------------------------------------
display_frame = tk.LabelFrame(
    root,
    text=" SR830 LIVE MONITOR ",
    font=("Consolas", 10, "bold"),
    bg="#1e1e1e",
    fg="#00ffcc",
    padx=15,
    pady=10
)
display_frame.pack(padx=15, pady=15, fill="both", expand=True)

# Spannung X-Anteil: X=R*cos(theta) (X)
lbl_x_title = tk.Label(display_frame, text="VOLTAGE (X=R*cos(θ)):", font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_x_title.pack(anchor="w")

val_x_label = tk.Label(
    display_frame,
    text="OFFLINE",
    font=("Consolas", 20, "bold"),
    bg="#000000",
    fg="#ff3333",
    relief="sunken",
    bd=3,
    padx=10,
    pady=2
)
val_x_label.pack(fill="x", pady=(2, 20))

# Spannung Y-Anteil: R*sin(theta) (Y)
lbl_y_title = tk.Label(display_frame, text="VOLTAGE (Y=R*sin(θ)):", font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_y_title.pack(anchor="w")
val_y_label = tk.Label(
    display_frame,
    text="OFFLINE",
    font=("Consolas", 20, "bold"),
    bg="#000000",
    fg="#ff3333",
    relief="sunken",
    bd=3,
    padx=10,
    pady=2
)
val_y_label.pack(fill="x", pady=(2, 30))

# Amplitude (R)
lbl_r_title = tk.Label(display_frame, text="AMPLITUDE (R):", font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_r_title.pack(anchor="w")
val_r_label = tk.Label(
    display_frame,
    text="OFFLINE",
    font=("Consolas", 20, "bold"),
    bg="#000000",
    fg="#ff3333",
    relief="sunken",
    bd=3,
    padx=10,
    pady=2
)
val_r_label.pack(fill="x", pady=(2, 10))

# Phase (θ)
lbl_phase_title = tk.Label(display_frame, text="PHASE (θ):", font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_phase_title.pack(anchor="w")

val_phase_label = tk.Label(
    display_frame,
    text="OFFLINE",
    font=("Consolas", 20, "bold"),
    bg="#000000",
    fg="#ff3333",
    relief="sunken",
    bd=3,
    padx=10,
    pady=2
)
val_phase_label.pack(fill="x", pady=(2, 0))

# ------------------------------------------
# MENÜS AUFBAUEN
# ------------------------------------------
menus = {
    "main": tk.Menu(root),
    "submenu_laser": tk.Menu(root, tearoff=0),
    "submenu_lock_in_amplifier": tk.Menu(root, tearoff=0),
    "submenu_data": tk.Menu(root, tearoff=0),
    "submenu_analysis": tk.Menu(root, tearoff=0),
    "submenu_view": tk.Menu(root, tearoff=0),
    "submenu_settings": tk.Menu(root, tearoff=0),
    "submenu_help": tk.Menu(root, tearoff=0),
    "subsetting_languages": tk.Menu(root, tearoff=0)
}

menus["subsetting_languages"].add_command(label='English', command=lambda: change_language("en"))
menus["subsetting_languages"].add_separator()
menus["subsetting_languages"].add_command(label='Deutsch', command=lambda: change_language("de"))
menus["subsetting_languages"].add_separator()
menus["subsetting_languages"].add_command(label='Español', command=lambda: change_language("es"))
menus["subsetting_languages"].add_separator()
menus["subsetting_languages"].add_command(label='Français', command=lambda: change_language("fr"))
menus["subsetting_languages"].add_separator()
menus["subsetting_languages"].add_command(label='Italiano', command=lambda: change_language("it"))

for parent_name, item_key, action in MENU_STRUCTURE:
    parent_menu = menus[parent_name]
    if item_key == "sep":
        parent_menu.add_separator()
        continue

    start_text = get_translation(item_key, current_lang)

    if isinstance(action, str):
        target_sub = root.destroy if action == "DESTROY_APP" else menus[action]
        if action == "DESTROY_APP":
            parent_menu.add_command(label=start_text, command=target_sub)
        else:
            parent_menu.add_cascade(label=start_text, menu=target_sub)
    else:
        parent_menu.add_command(label=start_text, command=action)

    menu_registry.append((parent_menu, start_text, item_key))

root.config(menu=menus["main"])


# Ereignis beim Schließen des Fensters
def on_closing():
    close_lockin_connection()
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_closing)

# Startet die ständige Live-Aktualisierung der Messwerte
update_lockin_display()

# GUI-Schleife starten
root.mainloop()
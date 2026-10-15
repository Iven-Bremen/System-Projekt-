import os
import sys
import json
import tkinter as tk
from tkinter import messagebox, ttk, filedialog

# Übersetzungs-Bibliothek
from deep_translator import GoogleTranslator

# VISA / Hardware-Ansteuerung
import pyvisa

# Eigene SWP-Module
import SWP_Calculation_PhaseVsFrequenz as PvF
import SWP_Calculation_TimeVsNitrierschicht as TvN
import SWP_Calculations_Streuung

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
# AUTOMATISIERTES ÜBERSETZUNGS-SYSTEM (MIT JSON-CACHE)
# ==========================================
CACHE_FILE = "translation_cache.json"

# === 1. STARTSPRACHE AUF ENGLISCH GESETZT ===
current_lang = "en"  # Standard-Sprache beim Start ist nun Englisch

def load_cache():
    """Lädt den Cache aus der JSON-Datei, falls sie existiert."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Fehler beim Laden des Caches: {e}")
    return {"de": {}, "es": {}, "fr": {}}

def save_cache():
    """Speichert den aktuellen Cache in der JSON-Datei."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(TRANSLATION_CACHE, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Fehler beim Speichern des Caches: {e}")

# Cache beim Starten des Programms laden
TRANSLATION_CACHE = load_cache()

# Manuelle Korrekturen für Fachwörter
MANUAL_OVERRIDES = {
    "de": {
        "Sine Out": "Sine-Out Signal",
        "Data Cleansing & Fit": "Datenbereinigung & Fit",
        "Phase vs. Frequency Analysis": "Phase-vs-Frequenz Analyse"
    },
    "es": {
        "Sine Out": "Salida Senoidal"
    }
}

registered_widgets = []

def auto_tr(english_text):
    """
    Übersetzt englischen Klartext vollautomatisch.
    Prüft: 1. Sprache Englisch? 2. Manuelle Korrektur? 3. JSON-Cache? 4. Live-Übersetzung + Auto-Save
    """
    if current_lang == "en":
        return english_text

    # 1. Manuelle Spezial-Korrektur prüfen
    if current_lang in MANUAL_OVERRIDES and english_text in MANUAL_OVERRIDES[current_lang]:
        return MANUAL_OVERRIDES[current_lang][english_text]

    # Sicherstellen, dass die Sprache im Cache existiert
    if current_lang not in TRANSLATION_CACHE:
        TRANSLATION_CACHE[current_lang] = {}

    # 2. Im Cache suchen (schnell, offline)
    if english_text in TRANSLATION_CACHE[current_lang]:
        return TRANSLATION_CACHE[current_lang][english_text]

    # 3. Automatisch online übersetzen & im Cache/JSON speichern
    try:
        translated = GoogleTranslator(source='en', target=current_lang).translate(english_text)
        TRANSLATION_CACHE[current_lang][english_text] = translated
        save_cache()
        return translated
    except Exception as e:
        print(f"Übersetzungsfehler bei '{english_text}': {e}")
        return english_text

def reg_ui(widget, english_text, prop="text"):
    """Registriert ein UI-Element mit seinem ENGLISCHEN Originaltext."""
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
    # Alle registrierten UI-Elemente automatisch anpassen
    for widget, prop, english_text in registered_widgets:
        update_single_widget(widget, prop, english_text)

    msg_title = auto_tr("Information")
    msg_text = auto_tr("Language changed successfully!")
    messagebox.showinfo(msg_title, msg_text)

# ==========================================
# HARDWARE & FUNCTIONS
# ==========================================
LOCK_IN_AMPLIFIER_PORT = "GPIB0::8::INSTR"
lockin_device = None
current_file_path = None

def connect_lockin():
    global lockin_device
    if lockin_device is None:
        try:
            rm = pyvisa.ResourceManager()
            lockin_device = rm.open_resource(LOCK_IN_AMPLIFIER_PORT)
            lockin_device.timeout = 2000
        except Exception:
            lockin_device = None
            return False
    return True

def lockin_start():
    if connect_lockin():
        try:
            lockin_device.write("SLVL 1.0")
            messagebox.showinfo(auto_tr("Lock-In Amplifier"), auto_tr("Sine Out set to 1.0 V (ON)."))
        except Exception as e:
            messagebox.showerror("Fehler", f"{e}")

def lockin_stop():
    if connect_lockin():
        try:
            lockin_device.write("SLVL 0.0")
            messagebox.showinfo(auto_tr("Lock-In Amplifier"), auto_tr("Sine Out set to 0.0 V (OFF)."))
        except Exception as e:
            messagebox.showerror("Fehler", f"{e}")

def open_file_dialog():
    global current_file_path
    file_path = filedialog.askopenfilename(
        title=auto_tr("Import Data File"),
        filetypes=[("Text Files", "*.txt *.csv"), ("All files", "*.*")]
    )
    if file_path:
        current_file_path = file_path
        lbl_file_status.config(text=os.path.basename(current_file_path))

# ==========================================
# GUI ANWENDUNG
# ==========================================
root = tk.Tk()
root.title('Labor-Steuerung & Analyse (Auto-Translation)')
root.geometry('1100x620')  # Vergrößert für die detaillierten Frontpanels
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
reg_ui((main_notebook, tab_home), "Home", "tab_text")

lbl_welcome = tk.Label(tab_home, font=("Consolas", 12, "bold"), bg="#1e1e1e", fg="#00ffcc")
lbl_welcome.pack(pady=(40, 10))
reg_ui(lbl_welcome, "WELCOME TO LAB MEASUREMENT SYSTEM")

lbl_info = tk.Label(tab_home, font=("Segoe UI", 10), bg="#1e1e1e", fg="#aaaaaa", justify="center")
lbl_info.pack(pady=10)
reg_ui(lbl_info, "Select a tab above to control hardware or run data analysis.")

# ------------------------------------------
# 2. TAB: LOCK-IN AMPLIFIER (SR830 1:1 FRONTPANEL)
# ------------------------------------------
tab_lockin = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_lockin, text="")
reg_ui((main_notebook, tab_lockin), "Lock-In Amplifier", "tab_text")

# 4-Spalten-Layout
tab_lockin.columnconfigure((0, 1, 2, 3), weight=1, pad=5)
tab_lockin.rowconfigure(0, weight=1)

# --- Frame 1: Signal Input & Filters ---
frame_input = tk.LabelFrame(tab_lockin, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=8, pady=5)
frame_input.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
reg_ui(frame_input, " Signal Input & Filters ")

lbl_in_cfg = tk.Label(frame_input, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_in_cfg.pack(anchor="w", pady=(5, 0))
reg_ui(lbl_in_cfg, "Input Configuration:")
combo_in_cfg = ttk.Combobox(frame_input, values=["A", "A-B", "I (1M)", "I (100M)"], state="readonly")
combo_in_cfg.current(0)
combo_in_cfg.pack(fill="x", pady=2)

lbl_coupling = tk.Label(frame_input, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_coupling.pack(anchor="w", pady=(8, 0))
reg_ui(lbl_coupling, "Coupling:")
combo_coupling = ttk.Combobox(frame_input, values=["AC", "DC"], state="readonly")
combo_coupling.current(0)
combo_coupling.pack(fill="x", pady=2)

lbl_grounding = tk.Label(frame_input, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_grounding.pack(anchor="w", pady=(8, 0))
reg_ui(lbl_grounding, "Grounding:")
combo_grounding = ttk.Combobox(frame_input, values=["Float", "Ground"], state="readonly")
combo_grounding.current(1)
combo_grounding.pack(fill="x", pady=2)

lbl_notch = tk.Label(frame_input, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_notch.pack(anchor="w", pady=(8, 0))
reg_ui(lbl_notch, "Line Notch Filter:")
combo_notch = ttk.Combobox(frame_input, values=["Out", "Line (50/60Hz)", "2x Line", "Both"], state="readonly")
combo_notch.current(0)
combo_notch.pack(fill="x", pady=2)

# --- Frame 2: Gain & Time Constant ---
frame_gain = tk.LabelFrame(tab_lockin, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=8, pady=5)
frame_gain.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
reg_ui(frame_gain, " Gain & Time Constant ")

lbl_sens = tk.Label(frame_gain, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_sens.pack(anchor="w", pady=(5, 0))
reg_ui(lbl_sens, "Sensitivity:")
combo_sens = ttk.Combobox(frame_gain, values=["2 nV", "10 nV", "100 nV", "1 uV", "100 uV", "1 V"], state="readonly")
combo_sens.current(5)
combo_sens.pack(fill="x", pady=2)

lbl_res = tk.Label(frame_gain, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_res.pack(anchor="w", pady=(8, 0))
reg_ui(lbl_res, "Dynamic Reserve:")
combo_res = ttk.Combobox(frame_gain, values=["High Reserve", "Normal", "Low Noise"], state="readonly")
combo_res.current(0)
combo_res.pack(fill="x", pady=2)

lbl_tc = tk.Label(frame_gain, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_tc.pack(anchor="w", pady=(8, 0))
reg_ui(lbl_tc, "Time Constant:")
combo_tc = ttk.Combobox(frame_gain, values=["10 us", "1 ms", "100 ms", "1 s", "30 ks"], state="readonly")
combo_tc.current(2)
combo_tc.pack(fill="x", pady=2)

lbl_slope = tk.Label(frame_gain, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_slope.pack(anchor="w", pady=(8, 0))
reg_ui(lbl_slope, "Filter Slope:")
combo_slope = ttk.Combobox(frame_gain, values=["6 dB/oct", "12 dB/oct", "18 dB/oct", "24 dB/oct"], state="readonly")
combo_slope.current(3)
combo_slope.pack(fill="x", pady=2)

# --- Frame 3: Displays & Auto Functions ---
frame_disp = tk.LabelFrame(tab_lockin, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=8, pady=5)
frame_disp.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
reg_ui(frame_disp, " SR830 Live Monitor & Auto ")

lbl_amp = tk.Label(frame_disp, font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_amp.pack(anchor="w")
reg_ui(lbl_amp, "AMPLITUDE (R):")

val_r_label = tk.Label(frame_disp, text="OFFLINE", font=("Consolas", 14, "bold"), bg="#000000", fg="#ff3333", relief="sunken", bd=2)
val_r_label.pack(fill="x", pady=(2, 6))

lbl_phase = tk.Label(frame_disp, font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_phase.pack(anchor="w")
reg_ui(lbl_phase, "PHASE (θ):")

val_phase_label = tk.Label(frame_disp, text="OFFLINE", font=("Consolas", 14, "bold"), bg="#000000", fg="#ff3333", relief="sunken", bd=2)
val_phase_label.pack(fill="x", pady=(2, 10))

# Auto-Buttons Grid
auto_btn_frame = tk.Frame(frame_disp, bg="#1e1e1e")
auto_btn_frame.pack(fill="x", pady=5)
auto_btn_frame.columnconfigure((0, 1), weight=1)

btn_auto_phase = tk.Button(auto_btn_frame, font=("Consolas", 8, "bold"), bg="#3c3f41", fg="white")
btn_auto_phase.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
reg_ui(btn_auto_phase, "Auto Phase")

btn_auto_gain = tk.Button(auto_btn_frame, font=("Consolas", 8, "bold"), bg="#3c3f41", fg="white")
btn_auto_gain.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
reg_ui(btn_auto_gain, "Auto Gain")

btn_auto_res = tk.Button(auto_btn_frame, font=("Consolas", 8, "bold"), bg="#3c3f41", fg="white")
btn_auto_res.grid(row=1, column=0, padx=2, pady=2, sticky="ew")
reg_ui(btn_auto_res, "Auto Reserve")

btn_auto_off = tk.Button(auto_btn_frame, font=("Consolas", 8, "bold"), bg="#3c3f41", fg="white")
btn_auto_off.grid(row=1, column=1, padx=2, pady=2, sticky="ew")
reg_ui(btn_auto_off, "Auto Offset")

# --- Frame 4: Reference Channel & Hardware Control ---
frame_ref = tk.LabelFrame(tab_lockin, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=8, pady=5)
frame_ref.grid(row=0, column=3, sticky="nsew", padx=5, pady=5)
reg_ui(frame_ref, " Reference Channel ")

lbl_freq = tk.Label(frame_ref, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_freq.pack(anchor="w", pady=(3, 0))
reg_ui(lbl_freq, "Ref Frequency (Hz):")
entry_freq = tk.Entry(frame_ref, font=("Consolas", 9), justify="center")
entry_freq.insert(0, "1000.0")
entry_freq.pack(fill="x", pady=2)

lbl_ref_phase = tk.Label(frame_ref, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_ref_phase.pack(anchor="w", pady=(5, 0))
reg_ui(lbl_ref_phase, "Ref Phase (°):")
entry_ref_phase = tk.Entry(frame_ref, font=("Consolas", 9), justify="center")
entry_ref_phase.insert(0, "0.0")
entry_ref_phase.pack(fill="x", pady=2)

lbl_ampl = tk.Label(frame_ref, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_ampl.pack(anchor="w", pady=(5, 0))
reg_ui(lbl_ampl, "Sine Amplitude (Vrms):")
entry_ampl = tk.Entry(frame_ref, font=("Consolas", 9), justify="center")
entry_ampl.insert(0, "1.000")
entry_ampl.pack(fill="x", pady=2)

lbl_ref_src = tk.Label(frame_ref, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_ref_src.pack(anchor="w", pady=(5, 0))
reg_ui(lbl_ref_src, "Ref Source:")
combo_ref_src = ttk.Combobox(frame_ref, values=["Internal", "External Sine", "TTL Pos Edge", "TTL Neg Edge"], state="readonly")
combo_ref_src.current(0)
combo_ref_src.pack(fill="x", pady=2)

btn_start_lockin = tk.Button(frame_ref, font=("Consolas", 8, "bold"), bg="#2e7d32", fg="white", pady=4, command=lockin_start)
btn_start_lockin.pack(fill="x", pady=(10, 2))
reg_ui(btn_start_lockin, "▶ Start Sine Out")

btn_stop_lockin = tk.Button(frame_ref, font=("Consolas", 8, "bold"), bg="#c62828", fg="white", pady=4, command=lockin_stop)
btn_stop_lockin.pack(fill="x", pady=2)
reg_ui(btn_stop_lockin, "⏹ Stop Sine Out")

# ------------------------------------------
# 3. TAB: LASER (FRONTPANEL)
# ------------------------------------------
tab_laser = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_laser, text="")
reg_ui((main_notebook, tab_laser), "Laser", "tab_text")

tab_laser.columnconfigure((0, 1), weight=1, pad=10)
tab_laser.rowconfigure((0, 1), weight=1, pad=10)

# Safety & Interlock Frame
frame_laser_safety = tk.LabelFrame(tab_laser, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#ff5555", padx=10, pady=10)
frame_laser_safety.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
reg_ui(frame_laser_safety, " Safety & Interlock ")

laser_status_lbl = tk.Label(frame_laser_safety, font=("Consolas", 11, "bold"), bg="#000000", fg="#ffaa00", height=2, relief="sunken")
laser_status_lbl.pack(fill="x", pady=10)
reg_ui(laser_status_lbl, "Laser Status: INACTIVE")

def toggle_laser_fire():
    if laser_status_lbl.cget("text").endswith("ACTIVE 🔥") or "ACTIVE" in laser_status_lbl.cget("text"):
        reg_ui(laser_status_lbl, "Laser Status: INACTIVE")
        btn_fire.config(bg="#d32f2f")
    else:
        reg_ui(laser_status_lbl, "Laser Status: ACTIVE 🔥")
        btn_fire.config(bg="#ff1744")

btn_fire = tk.Button(frame_laser_safety, bg="#d32f2f", fg="white", font=("Consolas", 10, "bold"), pady=6, command=toggle_laser_fire)
btn_fire.pack(fill="x", pady=5)
reg_ui(btn_fire, "Fire / Toggle Laser")

# Power & Current Frame
frame_laser_power = tk.LabelFrame(tab_laser, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#ffaa00", padx=10, pady=10)
frame_laser_power.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
reg_ui(frame_laser_power, " Power & Current Control ")

lbl_curr = tk.Label(frame_laser_power, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_curr.pack(anchor="w")
reg_ui(lbl_curr, "Diode Current Setpoint (mA):")

slider_curr = tk.Scale(frame_laser_power, from_=0, to=500, orient="horizontal", bg="#1e1e1e", fg="#ffffff", highlightthickness=0)
slider_curr.pack(fill="x", pady=5)

lbl_pwr_readout = tk.Label(frame_laser_power, text="0.0 mW", font=("Consolas", 16, "bold"), bg="#000000", fg="#00ff00", relief="sunken")
lbl_pwr_readout.pack(fill="x", pady=10)

# Temperature TEC Frame
frame_laser_temp = tk.LabelFrame(tab_laser, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=10, pady=10)
frame_laser_temp.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
reg_ui(frame_laser_temp, " Temperature Control (TEC) ")

lbl_target_temp = tk.Label(frame_laser_temp, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_target_temp.pack(anchor="w")
reg_ui(lbl_target_temp, "Target Temperature (°C):")

entry_temp = tk.Entry(frame_laser_temp, font=("Consolas", 10), justify="center")
entry_temp.insert(0, "25.0")
entry_temp.pack(fill="x", pady=5)

lbl_act_temp = tk.Label(frame_laser_temp, text="Actual Temp: 25.00 °C", font=("Consolas", 12, "bold"), bg="#1e1e1e", fg="#00ffcc")
lbl_act_temp.pack(pady=5)

# ------------------------------------------
# 4. TAB: ANALYSIS
# ------------------------------------------
tab_analysis = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_analysis, text="")
reg_ui((main_notebook, tab_analysis), "Analysis", "tab_text")

analysis_notebook = ttk.Notebook(tab_analysis)
analysis_notebook.pack(fill="both", expand=True, padx=10, pady=10)

# Sub-Tab 1: Data Cleansing & Fit
sub_tab_clean = tk.Frame(analysis_notebook, bg="#252526")
analysis_notebook.add(sub_tab_clean, text="")
reg_ui((analysis_notebook, sub_tab_clean), "Data Cleansing & Fit", "tab_text")

btn_load = tk.Button(sub_tab_clean, font=("Consolas", 9, "bold"), bg="#007acc", fg="white", padx=10, pady=5,
                     command=open_file_dialog)
btn_load.pack(pady=15)
reg_ui(btn_load, "📁 Import Data File")

lbl_file_status = tk.Label(sub_tab_clean, font=("Consolas", 9), bg="#252526", fg="#aaaaaa")
lbl_file_status.pack(pady=5)
reg_ui(lbl_file_status, "No file loaded")

btn_reg = tk.Button(sub_tab_clean, font=("Consolas", 9, "bold"), bg="#388e3c", fg="white", padx=10, pady=5,
                    command=lambda: messagebox.showinfo(auto_tr("Regression"), TvN.main()))
btn_reg.pack(pady=10)
reg_ui(btn_reg, "📊 Run Regression")

# Sub-Tab 2: Statistics
sub_tab_stats = tk.Frame(analysis_notebook, bg="#252526")
analysis_notebook.add(sub_tab_stats, text="")
reg_ui((analysis_notebook, sub_tab_stats), "Statistics", "tab_text")

btn_pvf = tk.Button(sub_tab_stats, font=("Consolas", 9, "bold"), bg="#f57c00", fg="white", padx=10, pady=5,
                    command=lambda: starte_regression(current_file_path))
btn_pvf.pack(pady=20)
reg_ui(btn_pvf, "📈 Phase vs. Frequency Analysis")

# ------------------------------------------
# 5. TAB: SETTINGS
# ------------------------------------------
tab_settings = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_settings, text="")
reg_ui((main_notebook, tab_settings), "Settings", "tab_text")

settings_notebook = ttk.Notebook(tab_settings)
settings_notebook.pack(fill="both", expand=True, padx=10, pady=10)

# Sub-Tab 1: Language
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

# Sub-Tab 2: Hardware Config
sub_tab_hw = tk.Frame(settings_notebook, bg="#252526")
settings_notebook.add(sub_tab_hw, text="")
reg_ui((settings_notebook, sub_tab_hw), "Hardware Config", "tab_text")

lbl_gpib = tk.Label(sub_tab_hw, font=("Consolas", 9), bg="#252526", fg="#ffffff")
lbl_gpib.pack(pady=(20, 5))
reg_ui(lbl_gpib, "GPIB Address:")

entry_gpib = tk.Entry(sub_tab_hw, font=("Consolas", 10), justify="center")
entry_gpib.insert(0, LOCK_IN_AMPLIFIER_PORT)
entry_gpib.pack()

# ==========================================
# MONITOR LOOP & LAUNCH
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

update_lockin_display()
root.mainloop()
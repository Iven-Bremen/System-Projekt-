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
# AUTOMATISIERTES ÜBERSETZUNGS-SYSTEM
# ==========================================
CACHE_FILE = "translation_cache.json"
current_lang = "en"  # Standard-Startsprache: Englisch


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
        "Phase vs. Frequency Analysis": "Phase-vs-Frequenz Analyse"
    },
    "es": {
        "Sine Out": "Salida Senoidal"
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

    try:
        translated = GoogleTranslator(source='en', target=current_lang).translate(english_text)
        TRANSLATION_CACHE[current_lang][english_text] = translated
        save_cache()
        return translated
    except Exception as e:
        print(f"Übersetzungsfehler bei '{english_text}': {e}")
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

    msg_title = auto_tr("Information")
    msg_text = auto_tr("Language changed successfully!")
    messagebox.showinfo(msg_title, msg_text)


# ==========================================
# HARDWARE & FUNCTIONS
# ==========================================
GPIB_ADDRESS = "GPIB0::8::INSTR"
lockin_device = None
current_file_path = None


def connect_lockin():
    global lockin_device
    if lockin_device is None:
        try:
            rm = pyvisa.ResourceManager()
            lockin_device = rm.open_resource(GPIB_ADDRESS)
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
root.geometry('1260x700')
root.configure(bg="#2b2b2b")

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
lbl_welcome.pack(pady=(40, 10))
reg_ui(lbl_welcome, "WELCOME TO LAB MEASUREMENT SYSTEM")

lbl_info = tk.Label(tab_home, font=("Segoe UI", 10), bg="#1e1e1e", fg="#aaaaaa", justify="center")
lbl_info.pack(pady=10)
reg_ui(lbl_info, "Select a tab above to control hardware or run data analysis.")

# ------------------------------------------
# 2. TAB: LOCK-IN AMPLIFIER (SR830 COMPLETE PANEL)
# ------------------------------------------
tab_lockin = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_lockin, text="")
reg_ui((main_notebook, tab_lockin), "Lock-In Amplifier", "tab_text")

tab_lockin.columnconfigure((0, 1, 2, 3), weight=1, pad=5)
tab_lockin.rowconfigure(0, weight=1)

# --- 1. Signal Input & Filters ---
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

# --- 2. Gain & Time Constant ---
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

# --- 3. CH1 & CH2 Displays ---
frame_disp = tk.LabelFrame(tab_lockin, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=8, pady=5)
frame_disp.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
reg_ui(frame_disp, " CH1 & CH2 Displays ")

lbl_ch1_sel = tk.Label(frame_disp, font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_ch1_sel.pack(anchor="w")
reg_ui(lbl_ch1_sel, "CH1 DISPLAY SOURCE:")
combo_ch1_src = ttk.Combobox(frame_disp, values=["X", "R", "X Noise", "Aux In 1", "Aux In 2"], state="readonly")
combo_ch1_src.current(1)
combo_ch1_src.pack(fill="x", pady=2)

val_ch1_label = tk.Label(frame_disp, text="OFFLINE", font=("Consolas", 13, "bold"), bg="#000000", fg="#ff3333",
                         relief="sunken", bd=2)
val_ch1_label.pack(fill="x", pady=(2, 8))

lbl_ch2_sel = tk.Label(frame_disp, font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_ch2_sel.pack(anchor="w")
reg_ui(lbl_ch2_sel, "CH2 DISPLAY SOURCE:")
combo_ch2_src = ttk.Combobox(frame_disp, values=["Y", "Phase (θ)", "Y Noise", "Aux In 3", "Aux In 4"], state="readonly")
combo_ch2_src.current(1)
combo_ch2_src.pack(fill="x", pady=2)

val_ch2_label = tk.Label(frame_disp, text="OFFLINE", font=("Consolas", 13, "bold"), bg="#000000", fg="#ff3333",
                         relief="sunken", bd=2)
val_ch2_label.pack(fill="x", pady=(2, 8))

auto_btn_frame = tk.Frame(frame_disp, bg="#1e1e1e")
auto_btn_frame.pack(fill="x", pady=2)
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

# --- 4. Reference Channel & Display ---
frame_ref = tk.LabelFrame(tab_lockin, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=8, pady=5)
frame_ref.grid(row=0, column=3, sticky="nsew", padx=5, pady=5)
reg_ui(frame_ref, " Reference Channel & Display ")

lbl_ref_disp_title = tk.Label(frame_ref, font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_ref_disp_title.pack(anchor="w")
reg_ui(lbl_ref_disp_title, "REF DISPLAY (Freq / Phase / Amp):")

val_ref_display = tk.Label(frame_ref, text="1000.00 Hz | 0.0° | 1.000V", font=("Consolas", 9, "bold"), bg="#000000",
                           fg="#00ff00", relief="sunken", bd=2)
val_ref_display.pack(fill="x", pady=(2, 6))

lbl_freq = tk.Label(frame_ref, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_freq.pack(anchor="w")
reg_ui(lbl_freq, "Ref Frequency (Hz):")
entry_freq = tk.Entry(frame_ref, font=("Consolas", 9), justify="center")
entry_freq.insert(0, "1000.0")
entry_freq.pack(fill="x", pady=2)

lbl_ref_phase = tk.Label(frame_ref, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_ref_phase.pack(anchor="w")
reg_ui(lbl_ref_phase, "Ref Phase (°):")
entry_ref_phase = tk.Entry(frame_ref, font=("Consolas", 9), justify="center")
entry_ref_phase.insert(0, "0.0")
entry_ref_phase.pack(fill="x", pady=2)

lbl_ampl = tk.Label(frame_ref, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_ampl.pack(anchor="w")
reg_ui(lbl_ampl, "Sine Amplitude (Vrms):")
entry_ampl = tk.Entry(frame_ref, font=("Consolas", 9), justify="center")
entry_ampl.insert(0, "1.000")
entry_ampl.pack(fill="x", pady=2)

lbl_ref_src = tk.Label(frame_ref, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_ref_src.pack(anchor="w")
reg_ui(lbl_ref_src, "Ref Source:")
combo_ref_src = ttk.Combobox(frame_ref, values=["Internal", "External Sine", "TTL Pos Edge", "TTL Neg Edge"],
                             state="readonly")
combo_ref_src.current(0)
combo_ref_src.pack(fill="x", pady=2)

btn_start_lockin = tk.Button(frame_ref, font=("Consolas", 8, "bold"), bg="#2e7d32", fg="white", pady=3,
                             command=lockin_start)
btn_start_lockin.pack(fill="x", pady=(6, 2))
reg_ui(btn_start_lockin, "▶ Start Sine Out")

btn_stop_lockin = tk.Button(frame_ref, font=("Consolas", 8, "bold"), bg="#c62828", fg="white", pady=3,
                            command=lockin_stop)
btn_stop_lockin.pack(fill="x", pady=2)
reg_ui(btn_stop_lockin, "⏹ Stop Sine Out")

# ------------------------------------------
# 3. TAB: LASER (MIT ALLER PARAMETER-UNTERSTÜTZUNG FOR 1 OD. 2 CONTROLLER)
# ------------------------------------------
tab_laser = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_laser, text="")
reg_ui((main_notebook, tab_laser), "Laser", "tab_text")

# Layout: Zeile 0 = Safety & Mode Header, Zeile 1 = 3 Spalten (LD Params, Controller 1, Controller 2)
tab_laser.columnconfigure((0, 1, 2), weight=1, pad=5)
tab_laser.rowconfigure(1, weight=1)

# === TOP ROW: SAFETY, MODE, INTERLOCK & CONTROLLER SWITCH ===
frame_laser_top = tk.LabelFrame(tab_laser, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#ff5555", padx=8, pady=5)
frame_laser_top.grid(row=0, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
reg_ui(frame_laser_top, " Laser Safety, Interlock & Operating Mode ")

frame_top_inner = tk.Frame(frame_laser_top, bg="#1e1e1e")
frame_top_inner.pack(fill="x")

lbl_interlock = tk.Label(frame_top_inner, font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_interlock.pack(side="left", padx=(5, 2))
reg_ui(lbl_interlock, "Interlock:")

lbl_interlock_val = tk.Label(frame_top_inner, text="CLOSED (OK)", font=("Consolas", 9, "bold"), bg="#000000",
                             fg="#00ff00", relief="sunken", padx=5)
lbl_interlock_val.pack(side="left", padx=5)

lbl_mode = tk.Label(frame_top_inner, font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_mode.pack(side="left", padx=(15, 2))
reg_ui(lbl_mode, "Mode:")

combo_laser_mode = ttk.Combobox(frame_top_inner, values=["CW Mode", "Pulsed Mode", "Modulated"], state="readonly",
                                width=12)
combo_laser_mode.current(0)
combo_laser_mode.pack(side="left", padx=5)

lbl_err_title = tk.Label(frame_top_inner, font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_err_title.pack(side="left", padx=(15, 2))
reg_ui(lbl_err_title, "Error#:")

lbl_error_code = tk.Label(frame_top_inner, text="Error #00", font=("Consolas", 9, "bold"), bg="#000000", fg="#00ff00",
                          relief="sunken", padx=5)
lbl_error_code.pack(side="left", padx=5)

lbl_ctrl_mode = tk.Label(frame_top_inner, font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_ctrl_mode.pack(side="left", padx=(15, 2))
reg_ui(lbl_ctrl_mode, "Controllers:")


def update_controller_view(event=None):
    mode = combo_ctrl_select.get()
    if "1" in mode:
        frame_ctrl2.grid_remove()
    else:
        frame_ctrl2.grid()


combo_ctrl_select = ttk.Combobox(frame_top_inner, values=["1 Controller", "2 Controllers"], state="readonly", width=14)
combo_ctrl_select.current(1)  # Default: 2 Controllers aktiv
combo_ctrl_select.pack(side="left", padx=5)
combo_ctrl_select.bind("<<ComboboxSelected>>", update_controller_view)

laser_status_lbl = tk.Label(frame_top_inner, font=("Consolas", 9, "bold"), bg="#000000", fg="#ffaa00", relief="sunken",
                            padx=8)
laser_status_lbl.pack(side="right", padx=5)
reg_ui(laser_status_lbl, "Status: INACTIVE")


def toggle_laser_fire():
    if "ACTIVE" in laser_status_lbl.cget("text"):
        reg_ui(laser_status_lbl, "Status: INACTIVE")
        btn_fire.config(bg="#d32f2f")
    else:
        reg_ui(laser_status_lbl, "Status: ACTIVE 🔥")
        btn_fire.config(bg="#ff1744")


btn_fire = tk.Button(frame_top_inner, bg="#d32f2f", fg="white", font=("Consolas", 8, "bold"), padx=10,
                     command=toggle_laser_fire)
btn_fire.pack(side="right", padx=5)
reg_ui(btn_fire, "Fire Laser")

# === SPALTE 1: LASER DIODE PARAMETERS (LCB, LCT, LVA, CURRENT, POWER) ===
frame_laser_ld = tk.LabelFrame(tab_laser, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#ffaa00", padx=8, pady=5)
frame_laser_ld.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
reg_ui(frame_laser_ld, " Laser Diode Controls ")

lbl_lcb = tk.Label(frame_laser_ld, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_lcb.pack(anchor="w", pady=(2, 0))
reg_ui(lbl_lcb, "LCB (Laser Current Bias - mA):")
entry_lcb = tk.Entry(frame_laser_ld, font=("Consolas", 9), justify="center")
entry_lcb.insert(0, "12.5")
entry_lcb.pack(fill="x", pady=2)

lbl_lct = tk.Label(frame_laser_ld, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_lct.pack(anchor="w", pady=(6, 0))
reg_ui(lbl_lct, "LCT (Laser Current Threshold - mA):")
entry_lct = tk.Entry(frame_laser_ld, font=("Consolas", 9), justify="center")
entry_lct.insert(0, "45.0")
entry_lct.pack(fill="x", pady=2)

lbl_curr = tk.Label(frame_laser_ld, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_curr.pack(anchor="w", pady=(6, 0))
reg_ui(lbl_curr, "Diode Current Setpoint (mA):")
slider_curr = tk.Scale(frame_laser_ld, from_=0, to=500, orient="horizontal", bg="#1e1e1e", fg="#ffffff",
                       highlightthickness=0)
slider_curr.pack(fill="x", pady=2)

lbl_lva_title = tk.Label(frame_laser_ld, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_lva_title.pack(anchor="w", pady=(6, 0))
reg_ui(lbl_lva_title, "LVA (Laser Voltage Actual):")
lbl_lva_val = tk.Label(frame_laser_ld, text="2.18 V", font=("Consolas", 11, "bold"), bg="#000000", fg="#00ff00",
                       relief="sunken")
lbl_lva_val.pack(fill="x", pady=2)

lbl_pwr_readout = tk.Label(frame_laser_ld, text="Power: 0.0 mW", font=("Consolas", 11, "bold"), bg="#000000",
                           fg="#00ff00", relief="sunken")
lbl_pwr_readout.pack(fill="x", pady=(10, 2))

# === SPALTE 2: CONTROLLER 1 (LASER / LD TEC: LTA, LTT, LTAC, CTA) ===
frame_ctrl1 = tk.LabelFrame(tab_laser, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=8, pady=5)
frame_ctrl1.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
reg_ui(frame_ctrl1, " Controller 1 (Laser / LD TEC) ")

lbl_ltt = tk.Label(frame_ctrl1, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_ltt.pack(anchor="w", pady=(2, 0))
reg_ui(lbl_ltt, "LTT (Laser Target Temp - °C):")
entry_ltt = tk.Entry(frame_ctrl1, font=("Consolas", 9), justify="center")
entry_ltt.insert(0, "25.00")
entry_ltt.pack(fill="x", pady=2)

lbl_lta_title = tk.Label(frame_ctrl1, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_lta_title.pack(anchor="w", pady=(6, 0))
reg_ui(lbl_lta_title, "LTA (Laser Temp Actual):")
lbl_lta_val = tk.Label(frame_ctrl1, text="25.02 °C", font=("Consolas", 11, "bold"), bg="#000000", fg="#00ffcc",
                       relief="sunken")
lbl_lta_val.pack(fill="x", pady=2)

lbl_ltac_title = tk.Label(frame_ctrl1, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_ltac_title.pack(anchor="w", pady=(6, 0))
reg_ui(lbl_ltac_title, "LTAC (Laser Temp Controller Actual):")
lbl_ltac_val = tk.Label(frame_ctrl1, text="24.98 °C", font=("Consolas", 11, "bold"), bg="#000000", fg="#00ffcc",
                        relief="sunken")
lbl_ltac_val.pack(fill="x", pady=2)

lbl_cta_title = tk.Label(frame_ctrl1, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_cta_title.pack(anchor="w", pady=(6, 0))
reg_ui(lbl_cta_title, "CTA (Current Temp Actual):")
lbl_cta_val = tk.Label(frame_ctrl1, text="25.05 °C", font=("Consolas", 11, "bold"), bg="#000000", fg="#00ffcc",
                       relief="sunken")
lbl_cta_val.pack(fill="x", pady=2)

# === SPALTE 3: CONTROLLER 2 (SYSTEM / BOARD TEC: TA, TT, TAC, CTT, CTAC) ===
frame_ctrl2 = tk.LabelFrame(tab_laser, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#e040fb", padx=8, pady=5)
frame_ctrl2.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)
reg_ui(frame_ctrl2, " Controller 2 (System / Board TEC) ")

lbl_tt = tk.Label(frame_ctrl2, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_tt.pack(anchor="w", pady=(2, 0))
reg_ui(lbl_tt, "TT (Target Temp - °C):")
entry_tt = tk.Entry(frame_ctrl2, font=("Consolas", 9), justify="center")
entry_tt.insert(0, "22.50")
entry_tt.pack(fill="x", pady=2)

lbl_ctt = tk.Label(frame_ctrl2, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_ctt.pack(anchor="w", pady=(4, 0))
reg_ui(lbl_ctt, "CTT (Controller Target Temp - °C):")
entry_ctt = tk.Entry(frame_ctrl2, font=("Consolas", 9), justify="center")
entry_ctt.insert(0, "22.50")
entry_ctt.pack(fill="x", pady=2)

lbl_ta_title = tk.Label(frame_ctrl2, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_ta_title.pack(anchor="w", pady=(4, 0))
reg_ui(lbl_ta_title, "TA (Temp Actual):")
lbl_ta_val = tk.Label(frame_ctrl2, text="22.51 °C", font=("Consolas", 10, "bold"), bg="#000000", fg="#e040fb",
                      relief="sunken")
lbl_ta_val.pack(fill="x", pady=1)

lbl_tac_title = tk.Label(frame_ctrl2, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_tac_title.pack(anchor="w", pady=(4, 0))
reg_ui(lbl_tac_title, "TAC (Temp Actual Controller):")
lbl_tac_val = tk.Label(frame_ctrl2, text="22.49 °C", font=("Consolas", 10, "bold"), bg="#000000", fg="#e040fb",
                       relief="sunken")
lbl_tac_val.pack(fill="x", pady=1)

lbl_ctac_title = tk.Label(frame_ctrl2, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_ctac_title.pack(anchor="w", pady=(4, 0))
reg_ui(lbl_ctac_title, "CTAC (Controller Temp Actual Controller):")
lbl_ctac_val = tk.Label(frame_ctrl2, text="22.50 °C", font=("Consolas", 10, "bold"), bg="#000000", fg="#e040fb",
                        relief="sunken")
lbl_ctac_val.pack(fill="x", pady=1)

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
entry_gpib.insert(0, GPIB_ADDRESS)
entry_gpib.pack()


# ==========================================
# MONITOR LOOP & LAUNCH
# ==========================================
def update_lockin_display():
    if lockin_device is not None:
        try:
            r_val = float(lockin_device.query("OUTP? 3"))
            phase_val = float(lockin_device.query("OUTP? 4"))
            val_ch1_label.config(text=f"{r_val:^+10.6f} V", fg="#00ff00")
            val_ch2_label.config(text=f"{phase_val:^+8.2f} °", fg="#ff9900")

            freq_val = entry_freq.get()
            phase_set = entry_ref_phase.get()
            ampl_set = entry_ampl.get()
            val_ref_display.config(text=f"{freq_val} Hz | {phase_set}° | {ampl_set}V")
        except Exception:
            val_ch1_label.config(text="--.------ V", fg="#555555")
            val_ch2_label.config(text="---.-- °", fg="#555555")
    else:
        val_ch1_label.config(text="OFFLINE", fg="#ff3333")
        val_ch2_label.config(text="OFFLINE", fg="#ff3333")

    root.after(500, update_lockin_display)


update_lockin_display()
root.mainloop()
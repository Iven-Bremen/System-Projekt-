import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk, filedialog

# Übersetzungs-Bibliothek (installierbar via: pip install deep-translator)
from deep_translator import GoogleTranslator

# VISA / Hardware-Ansteuerung
import pyvisa

# ==========================================
# AUTOMATISIERTES ÜBERSETZUNGS-SYSTEM
# ==========================================
current_lang = "de"  # Startsprache

# Speicher für bereits übersetzte Begriffe (verhindert unnötige Internet-Anfragen)
TRANSLATION_CACHE = {
    "de": {},
    "es": {},
    "fr": {}
}

# OPTIONAL: Manuelle Korrekturen NUR für Fachwörter, die Google falsch übersetzt
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
    Prüft: 1. Ist Sprache Englisch? 2. Gibt es Korrektur? 3. War es im Cache? 4. Live-Übersetzung
    """
    if current_lang == "en":
        return english_text

    # 1. Manuelle Spezial-Korrektur prüfen
    if current_lang in MANUAL_OVERRIDES and english_text in MANUAL_OVERRIDES[current_lang]:
        return MANUAL_OVERRIDES[current_lang][english_text]

    # 2. Im Cache suchen (schnell, offline)
    if english_text in TRANSLATION_CACHE[current_lang]:
        return TRANSLATION_CACHE[current_lang][english_text]

    # 3. Automatisch online übersetzen & im Cache speichern
    try:
        translated = GoogleTranslator(source='en', target=current_lang).translate(english_text)
        TRANSLATION_CACHE[current_lang][english_text] = translated
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
root.title('GUI for Nitriding processing')
root.geometry('600x500')
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
# 2. TAB: LOCK-IN AMPLIFIER
# ------------------------------------------
tab_lockin = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_lockin, text="")
reg_ui((main_notebook, tab_lockin), "Lock-In Amplifier", "tab_text")

display_frame = tk.LabelFrame(tab_lockin, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=10, pady=5)
display_frame.pack(padx=15, pady=15, fill="x")
reg_ui(display_frame, " SR830 LIVE MONITOR ")

lbl_amp = tk.Label(display_frame, font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_amp.pack(anchor="w")
reg_ui(lbl_amp, "AMPLITUDE (R):")

val_r_label = tk.Label(display_frame, text="OFFLINE", font=("Consolas", 16, "bold"), bg="#000000", fg="#ff3333",
                       relief="sunken", bd=2)
val_r_label.pack(fill="x", pady=(2, 6))

lbl_phase = tk.Label(display_frame, font=("Consolas", 8, "bold"), bg="#1e1e1e", fg="#aaaaaa")
lbl_phase.pack(anchor="w")
reg_ui(lbl_phase, "PHASE (θ):")

val_phase_label = tk.Label(display_frame, text="OFFLINE", font=("Consolas", 16, "bold"), bg="#000000", fg="#ff3333",
                           relief="sunken", bd=2)
val_phase_label.pack(fill="x", pady=(2, 5))

btn_frame = tk.Frame(tab_lockin, bg="#1e1e1e")
btn_frame.pack(pady=10)

btn_start_lockin = tk.Button(btn_frame, font=("Consolas", 9, "bold"), bg="#2e7d32", fg="white", padx=10, pady=5,
                             command=lockin_start)
btn_start_lockin.pack(side="left", padx=5)
reg_ui(btn_start_lockin, "▶ Start Sine Out (1V)")

btn_stop_lockin = tk.Button(btn_frame, font=("Consolas", 9, "bold"), bg="#c62828", fg="white", padx=10, pady=5,
                            command=lockin_stop)
btn_stop_lockin.pack(side="left", padx=5)
reg_ui(btn_stop_lockin, "⏹ Stop Sine Out (0V)")

# ------------------------------------------
# 3. TAB: LASER
# ------------------------------------------
tab_laser = tk.Frame(main_notebook, bg="#1e1e1e")
main_notebook.add(tab_laser, text="")
reg_ui((main_notebook, tab_laser), "Laser", "tab_text")

lbl_laser_title = tk.Label(tab_laser, font=("Consolas", 12, "bold"), bg="#1e1e1e", fg="#ff5555")
lbl_laser_title.pack(pady=15)
reg_ui(lbl_laser_title, "LASER CONTROL PANEL")

laser_status_lbl = tk.Label(tab_laser, font=("Consolas", 10), bg="#000000", fg="#ffaa00", width=30, height=2,
                            relief="sunken")
laser_status_lbl.pack(pady=10)
reg_ui(laser_status_lbl, "Laser Status: Inactive")

btn_fire = tk.Button(tab_laser, bg="#d32f2f", fg="white", font=("Consolas", 10, "bold"),
                     command=lambda: reg_ui(laser_status_lbl, "Laser Status: ACTIVE 🔥"))
btn_fire.pack(pady=5)
reg_ui(btn_fire, "Fire Laser")

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
                    command=lambda: messagebox.showinfo(auto_tr("Regression"), auto_tr("Starting Regression...")))
btn_reg.pack(pady=10)
reg_ui(btn_reg, "📊 Run Regression")

# Sub-Tab 2: Statistics
sub_tab_stats = tk.Frame(analysis_notebook, bg="#252526")
analysis_notebook.add(sub_tab_stats, text="")
reg_ui((analysis_notebook, sub_tab_stats), "Statistics", "tab_text")

btn_pvf = tk.Button(sub_tab_stats, font=("Consolas", 9, "bold"), bg="#f57c00", fg="white", padx=10, pady=5)
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

languages = [("Deutsch", "de"), ("English", "en"), ("Español", "es"), ("Français", "fr")]
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
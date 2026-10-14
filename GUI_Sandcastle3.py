import os
import sys
import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import socket
import tkinter as tk
from tkinter import messagebox, ttk

# Plotting
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Übersetzungs-Bibliothek
from deep_translator import GoogleTranslator

# Hardware-Schnittstellen (GPIB & RS232)
import pyvisa

try:
    import serial

    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


# ==========================================
# DIGITAL TWIN STATE (SR830 & OSTech DSx1)
# ==========================================
class DigitalTwinState:
    def __init__(self):
        # SRS SR830 Lock-In State
        self.sr830_connected = False
        self.sr830_x = 0.000000  # Volts
        self.sr830_y = 0.000000  # Volts
        self.sr830_r = 0.000000  # Volts
        self.sr830_phase = 0.00  # Degrees
        self.sr830_freq = 1000.0  # Hz
        self.sr830_sine_out = 1.000  # Volts (0.004 to 5.000 V)
        self.sr830_time_const = "100 ms"
        self.sr830_sensitivity = "1 V/uA"

        # OSTech DSx1 Laser State
        self.ostech_connected = False
        self.laser_emission = False
        self.laser_interlock_ok = True
        self.laser_current_act = 0.0  # mA
        self.laser_current_set = 250.0  # mA
        self.laser_temp_act = 24.8  # °C
        self.laser_temp_set = 25.0  # °C


twin = DigitalTwinState()

# Hardware Configuration
LOCK_IN_AMPLIFIER_PORT = "GPIB0::8::INSTR"
RS232_PORT = "COM3"
RS232_BAUD = 19200

lockin_device = None
ostech_serial = None


def connect_sr830():
    global lockin_device
    if lockin_device is None:
        try:
            rm = pyvisa.ResourceManager()
            lockin_device = rm.open_resource(LOCK_IN_AMPLIFIER_PORT)
            lockin_device.timeout = 1000
            twin.sr830_connected = True
        except Exception:
            twin.sr830_connected = False
            return False
    return True


def connect_ostech():
    global ostech_serial
    if not HAS_SERIAL:
        return False
    if ostech_serial is None or not ostech_serial.is_open:
        try:
            ostech_serial = serial.Serial(RS232_PORT, RS232_BAUD, timeout=1)
            twin.ostech_connected = True
        except Exception:
            twin.ostech_connected = False
            return False
    return True


def send_ostech_cmd(cmd):
    if connect_ostech():
        try:
            ostech_serial.write(f"{cmd}\r\n".encode('ascii'))
            return ostech_serial.readline().decode('ascii').strip()
        except Exception:
            pass
    return None


# ==========================================
# MOBILE / TABLET WEB SERVER
# ==========================================
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class MobileTwinHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)

        # API Endpunkte
        if parsed_path.path == "/api/toggle_laser":
            twin.laser_emission = not twin.laser_emission
            send_ostech_cmd("la 1" if twin.laser_emission else "la 0")
        elif parsed_path.path == "/api/toggle_sine":
            twin.sr830_sine_out = 0.0 if twin.sr830_sine_out > 0 else 1.000
            if connect_sr830():
                try:
                    lockin_device.write(f"SLVL {twin.sr830_sine_out}")
                except Exception:
                    pass

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Digital Twin - SR830 & OSTech DSx1</title>
            <style>
                body {{ font-family: -apple-system, sans-serif; background: #121212; color: #e0e0e0; text-align: center; padding: 12px; margin: 0; }}
                .card {{ background: #1e1e1e; padding: 15px; margin: 12px auto; max-width: 420px; border-radius: 10px; border: 1px solid #333; text-align: left; }}
                .btn {{ display: block; width: 100%; box-sizing: border-box; padding: 12px; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; text-decoration: none; text-align: center; margin-top: 10px; font-size: 0.95em; }}
                .btn-green {{ background: #2e7d32; }} .btn-red {{ background: #c62828; }} .btn-blue {{ background: #007acc; }}
                .val {{ font-family: monospace; font-weight: bold; color: #00ffcc; float: right; }}
                .badge {{ padding: 3px 8px; border-radius: 4px; font-size: 0.75em; font-weight: bold; float: right; background: #333; color: #00ffcc; }}
            </style>
            <meta http-equiv="refresh" content="2">
        </head>
        <body>
            <h3>Digital Twin Lab Interface</h3>

            <!-- SR830 Card -->
            <div class="card">
                <h4>SRS SR830 Lock-In <span class="badge">{"ONLINE" if twin.sr830_connected else "SIMULATION"}</span></h4>
                <p>X (In-Phase): <span class="val">{twin.sr830_x:+.6f} V</span></p>
                <p>Y (Quadrature): <span class="val">{twin.sr830_y:+.6f} V</span></p>
                <p>Magnitude R: <span class="val">{twin.sr830_r:+.6f} V</span></p>
                <p>Phase &theta;: <span class="val">{twin.sr830_phase:+.2f} &deg;</span></p>
                <p>Frequency: <span class="val">{twin.sr830_freq:.1f} Hz</span></p>
                <p>Sine Out Level: <span class="val">{twin.sr830_sine_out:.3f} V</span></p>
                <a href="/api/toggle_sine" class="btn btn-blue">Toggle Sine Out</a>
            </div>

            <!-- OSTech DSx1 Card -->
            <div class="card">
                <h4>OSTech DSx1 Laser <span class="badge">{"ONLINE" if twin.ostech_connected else "SIMULATION"}</span></h4>
                <p>Current (Act/Set): <span class="val">{twin.laser_current_act:.1f} / {twin.laser_current_set:.1f} mA</span></p>
                <p>Temp (Act/Set): <span class="val">{twin.laser_temp_act:.2f} / {twin.laser_temp_set:.1f} &deg;C</span></p>
                <p>Interlock: <span class="val" style="color:{"#00ff00" if twin.laser_interlock_ok else "#ff3333"};">{"OK" if twin.laser_interlock_ok else "OPEN"}</span></p>
                <a href="/api/toggle_laser" class="btn {"btn-red" if twin.laser_emission else "btn-green"}">
                    {"EMISSION OFF" if twin.laser_emission else "EMISSION ON"}
                </a>
            </div>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        return


threading.Thread(target=lambda: HTTPServer(("0.0.0.0", 8080), MobileTwinHandler).serve_forever(), daemon=True).start()

# ==========================================
# TRANSLATION SYSTEM
# ==========================================
current_lang = "en"
registered_widgets = []


def auto_tr(text):
    if current_lang == "en": return text
    try:
        return GoogleTranslator(source='en', target=current_lang).translate(text)
    except Exception:
        return text


def reg_ui(widget, text, prop="text"):
    registered_widgets.append((widget, prop, text))
    try:
        widget.config(text=auto_tr(text))
    except Exception:
        pass


def change_lang(lang):
    global current_lang
    current_lang = lang
    for w, p, t in registered_widgets:
        try:
            if p == "text":
                w.config(text=auto_tr(t))
            elif p == "tab":
                notebook.tab(w, text=f" {auto_tr(t)} ")
        except Exception:
            pass


# ==========================================
# MAIN GUI (TKINTER)
# ==========================================
root = tk.Tk()
root.title('Digital Twin - SRS SR830 & OSTech DSx1 Controller')
root.geometry('740x640')
root.configure(bg="#2b2b2b")

style = ttk.Style()
style.theme_use('default')
style.configure("TNotebook", background="#2b2b2b", borderwidth=0)
style.configure("TNotebook.Tab", background="#3c3f41", foreground="#ffffff", padding=[10, 6],
                font=('Consolas', 10, 'bold'))
style.map("TNotebook.Tab", background=[("selected", "#007acc")], foreground=[("selected", "#ffffff")])

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=10, pady=10)

# ------------------------------------------
# TAB 1: OVERVIEW & MOBILE IP
# ------------------------------------------
tab_home = tk.Frame(notebook, bg="#1e1e1e")
notebook.add(tab_home, text="")
reg_ui(tab_home, "Overview", "tab")

lbl_h1 = tk.Label(tab_home, font=("Consolas", 12, "bold"), bg="#1e1e1e", fg="#00ffcc")
lbl_h1.pack(pady=(15, 5))
reg_ui(lbl_h1, "SYSTEM DIGITAL TWIN CONTROL CENTER")

lbl_info = tk.Label(tab_home, font=("Segoe UI", 9), bg="#1e1e1e", fg="#aaaaaa")
lbl_info.pack(pady=5)
reg_ui(lbl_info, "Real-time control twin for SRS SR830 Lock-In & OSTech DSx1 Diode Laser.")

ip_frame = tk.LabelFrame(tab_home, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=10, pady=10)
ip_frame.pack(padx=20, pady=15, fill="x")
reg_ui(ip_frame, " MOBILE / WEB ACCESS ")

lbl_ip_title = tk.Label(ip_frame, font=("Segoe UI", 9), bg="#1e1e1e", fg="#ffffff")
lbl_ip_title.pack()
reg_ui(lbl_ip_title, "Connect any Smartphone, Tablet, or PC browser to:")

lbl_ip_val = tk.Label(ip_frame, text=f"http://{get_local_ip()}:8080", font=("Consolas", 14, "bold"), bg="#000000",
                      fg="#00ff00", pady=5)
lbl_ip_val.pack(pady=5, fill="x")

# ------------------------------------------
# TAB 2: SRS SR830 LOCK-IN AMPLIFIER
# ------------------------------------------
tab_sr = tk.Frame(notebook, bg="#1e1e1e")
notebook.add(tab_sr, text="")
reg_ui(tab_sr, "SRS SR830 Lock-In", "tab")

sr_disp_frame = tk.LabelFrame(tab_sr, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#00ffcc", padx=10, pady=10)
sr_disp_frame.pack(padx=15, pady=10, fill="x")
reg_ui(sr_disp_frame, " FRONT PANEL MONITOR ")

grid_f = tk.Frame(sr_disp_frame, bg="#1e1e1e")
grid_f.pack(fill="x")

lbl_x_t = tk.Label(grid_f, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_x_t.grid(row=0, column=0, sticky="w")
reg_ui(lbl_x_t, "X (IN-PHASE):")
val_x_label = tk.Label(grid_f, text="+0.000000 V", font=("Consolas", 12, "bold"), bg="#000000", fg="#00ff00", width=16)
val_x_label.grid(row=1, column=0, padx=5, pady=2)

lbl_y_t = tk.Label(grid_f, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_y_t.grid(row=0, column=1, sticky="w")
reg_ui(lbl_y_t, "Y (QUADRATURE):")
val_y_label = tk.Label(grid_f, text="+0.000000 V", font=("Consolas", 12, "bold"), bg="#000000", fg="#00ff00", width=16)
val_y_label.grid(row=1, column=1, padx=5, pady=2)

lbl_r_t = tk.Label(grid_f, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_r_t.grid(row=2, column=0, sticky="w")
reg_ui(lbl_r_t, "MAGNITUDE (R):")
val_r_label = tk.Label(grid_f, text="+0.000000 V", font=("Consolas", 14, "bold"), bg="#000000", fg="#00ffcc", width=16)
val_r_label.grid(row=3, column=0, padx=5, pady=2)

lbl_ph_t = tk.Label(grid_f, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_ph_t.grid(row=2, column=1, sticky="w")
reg_ui(lbl_ph_t, "PHASE (θ):")
val_phase_label = tk.Label(grid_f, text="+0.00 °", font=("Consolas", 14, "bold"), bg="#000000", fg="#ff9900", width=16)
val_phase_label.grid(row=3, column=1, padx=5, pady=2)

# SR830 Controls
sr_ctrl_frame = tk.Frame(tab_sr, bg="#1e1e1e")
sr_ctrl_frame.pack(pady=10)

lbl_sine_out = tk.Label(sr_ctrl_frame, font=("Consolas", 9), bg="#1e1e1e", fg="#ffffff")
lbl_sine_out.grid(row=0, column=0, padx=5, pady=5)
reg_ui(lbl_sine_out, "Sine Out Level (V):")

entry_sine_out = tk.Entry(sr_ctrl_frame, font=("Consolas", 10), width=8, justify="center")
entry_sine_out.insert(0, "1.000")
entry_sine_out.grid(row=0, column=1, padx=5, pady=5)


def apply_sine():
    try:
        val = float(entry_sine_out.get())
        twin.sr830_sine_out = val
        if connect_sr830(): lockin_device.write(f"SLVL {val}")
    except ValueError:
        pass


btn_apply_sine = tk.Button(sr_ctrl_frame, font=("Consolas", 8, "bold"), bg="#007acc", fg="white", command=apply_sine)
btn_apply_sine.grid(row=0, column=2, padx=5, pady=5)
reg_ui(btn_apply_sine, "Set")

# ------------------------------------------
# TAB 3: OSTECH DSx1 LASER CONTROLLER
# ------------------------------------------
tab_os = tk.Frame(notebook, bg="#1e1e1e")
notebook.add(tab_os, text="")
reg_ui(tab_os, "OSTech DSx1 Laser", "tab")

ostech_frame = tk.LabelFrame(tab_os, font=("Consolas", 9, "bold"), bg="#1e1e1e", fg="#ff5555", padx=10, pady=10)
ostech_frame.pack(padx=15, pady=10, fill="x")
reg_ui(ostech_frame, " DIODE LASER STATUS & SETTINGS ")

lbl_c_act_t = tk.Label(ostech_frame, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_c_act_t.pack(anchor="w")
reg_ui(lbl_c_act_t, "DIODE CURRENT (ACTUAL / SET):")

val_laser_cur_label = tk.Label(ostech_frame, text="0.0 mA / 250.0 mA", font=("Consolas", 14, "bold"), bg="#000000",
                               fg="#ffaa00")
val_laser_cur_label.pack(fill="x", pady=2)

lbl_t_act_t = tk.Label(ostech_frame, font=("Consolas", 8), bg="#1e1e1e", fg="#aaaaaa")
lbl_t_act_t.pack(anchor="w")
reg_ui(lbl_t_act_t, "DIODE TEMPERATURE (ACTUAL / SET):")

val_laser_temp_label = tk.Label(ostech_frame, text="24.80 °C / 25.00 °C", font=("Consolas", 14, "bold"), bg="#000000",
                                fg="#00ffcc")
val_laser_temp_label.pack(fill="x", pady=2)

os_ctrl_frame = tk.Frame(tab_os, bg="#1e1e1e")
os_ctrl_frame.pack(pady=10)

lbl_set_cur = tk.Label(os_ctrl_frame, font=("Consolas", 9), bg="#1e1e1e", fg="#ffffff")
lbl_set_cur.grid(row=0, column=0, padx=5, pady=5)
reg_ui(lbl_set_cur, "Set Current (mA):")

entry_cur_set = tk.Entry(os_ctrl_frame, font=("Consolas", 10), width=8, justify="center")
entry_cur_set.insert(0, "250.0")
entry_cur_set.grid(row=0, column=1, padx=5, pady=5)


def apply_laser_cur():
    try:
        val = float(entry_cur_set.get())
        twin.laser_current_set = val
        send_ostech_cmd(f"sc {val}")
    except ValueError:
        pass


btn_apply_cur = tk.Button(os_ctrl_frame, font=("Consolas", 8, "bold"), bg="#007acc", fg="white",
                          command=apply_laser_cur)
btn_apply_cur.grid(row=0, column=2, padx=5, pady=5)
reg_ui(btn_apply_cur, "Set")


def toggle_laser():
    twin.laser_emission = not twin.laser_emission
    send_ostech_cmd("la 1" if twin.laser_emission else "la 0")


btn_laser_emission = tk.Button(tab_os, font=("Consolas", 10, "bold"), bg="#c62828", fg="white", padx=15, pady=8,
                               command=toggle_laser)
btn_laser_emission.pack(pady=10)
reg_ui(btn_laser_emission, "TOGGLE EMISSION")

# ------------------------------------------
# TAB 4: LIVE MONITOR / PLOTTING
# ------------------------------------------
tab_analysis = tk.Frame(notebook, bg="#1e1e1e")
notebook.add(tab_analysis, text="")
reg_ui(tab_analysis, "Live Plot", "tab")

fig = Figure(figsize=(5, 3), dpi=100)
ax = fig.add_subplot(111)
ax.set_title("SR830 Magnitude (R) vs Time", color="white", fontsize=9)
ax.set_facecolor("#1e1e1e")
fig.patch.set_facecolor("#2b2b2b")
ax.tick_params(colors='white', labelsize=8)
line, = ax.plot([], [], '#00ffcc', linewidth=1.5)

canvas = FigureCanvasTkAgg(fig, master=tab_analysis)
canvas.draw()
canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
plot_data = []

# ------------------------------------------
# TAB 5: SETTINGS & HARDWARE CONFIG
# ------------------------------------------
tab_settings = tk.Frame(notebook, bg="#1e1e1e")
notebook.add(tab_settings, text="")
reg_ui(tab_settings, "Settings", "tab")

sub_notebook = ttk.Notebook(tab_settings)
sub_notebook.pack(fill="both", expand=True, padx=10, pady=10)

# Language Subtab
sub_lang = tk.Frame(sub_notebook, bg="#252526")
sub_notebook.add(sub_lang, text="")
reg_ui(sub_lang, "Language", "tab")

for name, code in [("English", "en"), ("Deutsch", "de"), ("Español", "es"), ("Français", "fr")]:
    tk.Button(sub_lang, text=name, width=14, bg="#3c3f41", fg="white", command=lambda c=code: change_lang(c)).pack(
        pady=4)

# Hardware Ports Subtab
sub_hw = tk.Frame(sub_notebook, bg="#252526")
sub_notebook.add(sub_hw, text="")
reg_ui(sub_hw, "Interfaces", "tab")

lbl_gpib_cfg = tk.Label(sub_hw, text="SR830 GPIB Address:", font=("Consolas", 9), bg="#252526", fg="#fff")
lbl_gpib_cfg.pack(pady=(10, 2))
entry_gpib_cfg = tk.Entry(sub_hw, font=("Consolas", 10), justify="center")
entry_gpib_cfg.insert(0, LOCK_IN_AMPLIFIER_PORT)
entry_gpib_cfg.pack()

lbl_rs232_cfg = tk.Label(sub_hw, text="OSTech RS232 Port:", font=("Consolas", 9), bg="#252526", fg="#fff")
lbl_rs232_cfg.pack(pady=(10, 2))
entry_rs232_cfg = tk.Entry(sub_hw, font=("Consolas", 10), justify="center")
entry_rs232_cfg.insert(0, RS232_PORT)
entry_rs232_cfg.pack()


# ==========================================
# MONITOR LOOP
# ==========================================
def update_gui_loop():
    # 1. Update SR830 Data
    if connect_sr830():
        try:
            twin.sr830_x = float(lockin_device.query("OUTP? 1"))
            twin.sr830_y = float(lockin_device.query("OUTP? 2"))
            twin.sr830_r = float(lockin_device.query("OUTP? 3"))
            twin.sr830_phase = float(lockin_device.query("OUTP? 4"))
            twin.sr830_freq = float(lockin_device.query("FREQ?"))
        except Exception:
            pass
    else:
        # Simulation values for Twin
        twin.sr830_r = twin.sr830_sine_out * 0.8543
        twin.sr830_x = twin.sr830_r * 0.707
        twin.sr830_y = twin.sr830_r * 0.707

    val_x_label.config(text=f"{twin.sr830_x:^+10.6f} V")
    val_y_label.config(text=f"{twin.sr830_y:^+10.6f} V")
    val_r_label.config(text=f"{twin.sr830_r:^+10.6f} V")
    val_phase_label.config(text=f"{twin.sr830_phase:^+8.2f} °")

    # 2. Update OSTech Laser Data
    if twin.laser_emission:
        twin.laser_current_act = twin.laser_current_set
        val_laser_cur_label.config(text=f"{twin.laser_current_act:.1f} mA / {twin.laser_current_set:.1f} mA",
                                   fg="#00ff00")
        btn_laser_emission.config(bg="#c62828", text=auto_tr("STOP EMISSION 🔥"))
    else:
        twin.laser_current_act = 0.0
        val_laser_cur_label.config(text=f"0.0 mA / {twin.laser_current_set:.1f} mA", fg="#ffaa00")
        btn_laser_emission.config(bg="#2e7d32", text=auto_tr("START EMISSION"))

    val_laser_temp_label.config(text=f"{twin.laser_temp_act:.2f} °C / {twin.laser_temp_set:.1f} °C")

    # 3. Update Live Plot
    plot_data.append(twin.sr830_r)
    if len(plot_data) > 50: plot_data.pop(0)

    line.set_data(range(len(plot_data)), plot_data)
    ax.relim()
    ax.autoscale_view()
    canvas.draw_idle()

    root.after(500, update_gui_loop)


update_gui_loop()
root.mainloop()
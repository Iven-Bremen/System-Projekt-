import tkinter as tk
from tkinter import messagebox, ttk, filedialog
# Wir nutzen deep-translator für die Live-Übersetzung
from deep_translator import GoogleTranslator

import SWP_Calculation_PhaseVsFrequenz
import SWP_Calculation_TimeVsNitrierschicht as TvN
import SWP_Calculation_PhaseVsFrequenz as PvF
import SWP_Calculations_Streuung
import platform
import subprocess
import numpy as np
import os
import re
import sys
import matplotlib
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.stats import norm

def starte_regression(dateipfad):
    # 1. Daten einlesen und aufbereiten
    frequenzen, sweeps = SWP_Calculations_Streuung.lade_ptr_datei(dateipfad)
    f, phase, sigma = SWP_Calculations_Streuung.bereite_daten_auf(frequenzen, sweeps)

    # 2. Fit und Analyse
    popt, perr = SWP_Calculations_Streuung.fitte_regression(f, phase, sigma)
    fit, residuen = SWP_Calculations_Streuung.berechne_residuen(f, phase, popt)

    # 3. Statistik und Plot
    SWP_Calculations_Streuung.statistik(f, residuen)
    SWP_Calculations_Streuung.plot_ergebnis(f, phase, sigma, fit, residuen, popt, sweeps)

# ==========================================
# 1. ÜBERSETZUNGS-DATENBANK & GLOBALE VARIABLE
# ==========================================
BASE_MENU_EN = {
    "menu_data": "Data", "menu_data_new": "New", "menu_data_open": "Open",
    "menu_data_save": "Save", "menu_data_saveas": "Save as",
    "menu_data_import": "Import", "menu_data_export": "Export", "menu_data_removefile": "Remove file", "menu_data_quit": "Quit",
    "menu_analysis": "Analysis", "menu_analysis_clean": "Data cleansing",
    "menu_analysis_stats": "Calculating Statistics",
    "menu_settings": "Settings", "menu_language": "Languages",
    "menu_help": "Help", "menu_help_doc": "Documentation",
    "msg_title": "Info", "msg_text": "Language changed successfully!"
}

current_lang = "en"
menu_registry = []
translation_cache = {"en": BASE_MENU_EN.copy()}

# Speicher für die ausgelesenen Daten
imported_data = {}


# ==========================================
# 2. ÜBERSETZUNGS-LOGIK
# ==========================================
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
    except Exception:
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
# 3. DIE DEINE IMPORT-METHODE (FUNKTION)
# ==========================================
def open_folder_and_read_files(parent_window):
    """
    Öffnet den Import-Ordner, zeigt Popups für Benutzerführung / Fehler
    und liest nur gültige textbasierte Dateien als Inputwerte aus.
    """
    global imported_data

    # 1. Import-Ordner definieren und erstellen
    import_dir = os.path.abspath("import_data")
    if not os.path.exists(import_dir):
        os.makedirs(import_dir)

    # 2. Ordner im Betriebssystem öffnen
    try:
        if platform.system() == "Windows":
            os.startfile(import_dir)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", import_dir])
        else:  # Linux
            subprocess.run(["xdg-open", import_dir])
    except Exception as e:
        messagebox.showerror("Fehler", f"Ordner konnte nicht geöffnet werden:\n{e}", parent=parent_window)
        return

    # 3. Popup: Instruktion für den Nutzer
    messagebox.showinfo(
        title="Dateien hinzufügen",
        message=(
            "Der Import-Ordner wurde geöfnet.\n\n"
            "1. Bitte ziehe nun deine textbasierten Dateien (z. B. .txt, .csv, .json, .dat) in diesen Ordner.\n"
            "2. Klicke hier auf 'OK', sobald du alle Dateien abgelegt hast.\n\n"
            "Die Dateien werden danach automatisch eingelesen."
        ),
        parent=parent_window
    )

    # 4. Dateien einlesen und prüfen
    valid_extensions = {".txt", ".csv", ".json", ".dat"}
    read_data = {}
    errors = []

    for filename in os.listdir(import_dir):
        file_path = os.path.join(import_dir, filename)

        if os.path.isfile(file_path):
            ext = os.path.splitext(filename)[1].lower()

            # Prüfen auf erlaubte Endungen
            if ext not in valid_extensions:
                errors.append(f"'{filename}' (Keine unterstützte Textdatei / falsches Format)")
                continue

            # Auslesen der Datei
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    read_data[filename] = content
            except UnicodeDecodeError:
                errors.append(f"'{filename}' (Konnte nicht als Text decodiert werden - evtl. Binärdatei)")
            except Exception as e:
                errors.append(f"'{filename}' (Lesefehler: {e})")

    # 5. Popup bei Fehlern oder unlesbaren Dateien
    if errors:
        error_msg = "Einige Dateien konnten nicht eingelesen werden oder sind keine unterstützten Textdateien:\n\n"
        error_msg += "\n".join(errors)
        messagebox.showwarning(title="Warnung beim Einlesen", message=error_msg, parent=parent_window)

    # 6. Erfolgreich ausgelesene Daten global bereitstellen
    if read_data:
        imported_data = read_data
        print(f"\n[Erfolg] {len(imported_data)} Datei(en) eingelesen:")
        for name, inhalt in imported_data.items():
            print(f" -> {name}: {len(inhalt)} Zeichen geladen.")

        messagebox.showinfo(
            title="Import erfolgreich",
            message=f"{len(imported_data)} Datei(en) erfolgreich als Inputwerte geladen!",
            parent=parent_window
        )


# ==========================================
# 4. DIE REMOVE-METHODE (GESPIEGELT)
# ==========================================
def open_folder_and_remove_files(parent_window):
    """
    1. Öffnet den Import-Ordner im Dateimanager.
    2. Zeigt ein Info-Popup zur Lösch-Instruktion.
    3. Aktualisiert nach Bestätigung den Datenbestand in der App.
    4. Gibt Feedback / Warnungen aus.
    """
    global imported_data

    import_dir = os.path.abspath("import_data")
    if not os.path.exists(import_dir):
        os.makedirs(import_dir)

    # 1. Ordner im Betriebssystem öffnen
    try:
        if platform.system() == "Windows":
            os.startfile(import_dir)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", import_dir])
        else:  # Linux
            subprocess.run(["xdg-open", import_dir])
    except Exception as e:
        messagebox.showerror("Fehler", f"Ordner konnte nicht geöffnet werden:\n{e}", parent=parent_window)
        return

    # 2. Popup: Instruktion für den Nutzer
    messagebox.showinfo(
        title="Dateien entfernen",
        message=(
            "Der Daten-Ordner wurde geöffnet.\n\n"
            "1. Bitte lösche die Dateien, die du entfernen möchtest, oder ziehe sie aus dem Ordner heraus.\n"
            "2. Klicke hier auf 'OK', sobald du fertig bist.\n\n"
            "Der Datenbestand im Programm wird danach automatisch aktualisiert."
        ),
        parent=parent_window
    )

    # 3. Ordner-Inhalt neu scannen & vergleichen
    valid_extensions = {".txt", ".csv", ".json", ".dat"}
    new_imported_data = {}
    errors = []

    current_files = os.listdir(import_dir)

    for filename in current_files:
        file_path = os.path.join(import_dir, filename)

        if os.path.isfile(file_path):
            ext = os.path.splitext(filename)[1].lower()

            if ext not in valid_extensions:
                errors.append(f"'{filename}' (Keine unterstützte Textdatei)")
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    new_imported_data[filename] = file.read()
            except Exception as e:
                errors.append(f"'{filename}' (Fehler beim Lesen: {e})")

    # 4. Berechnen, wie viele Dateien entfernt wurden
    removed_count = len(imported_data) - len(new_imported_data)
    imported_data = new_imported_data  # Speicher in der App aktualisieren

    # 5. Warnung bei verbleibenden fehlerhaften Dateien
    if errors:
        error_msg = "Folgende im Ordner verbliebene Dateien sind ungültig oder konnten nicht eingelesen werden:\n\n"
        error_msg += "\n".join(errors)
        messagebox.showwarning(title="Warnung beim Aktualisieren", message=error_msg, parent=parent_window)

    # 6. Erfolgs-Feedback
    if removed_count > 0:
        messagebox.showinfo(
            title="Aktualisierung erfolgreich",
            message=f"{removed_count} Datei(en) wurden aus dem Programm entfernt.\nVerbleibend: {len(imported_data)} Datei(en).",
            parent=parent_window
        )
    else:
        messagebox.showinfo(
            title="Keine Änderungen",
            message=f"Es wurden keine geladenen Dateien entfernt. Aktuell geladen: {len(imported_data)} Datei(en).",
            parent=parent_window
        )


# ==========================================
# 5. MENÜ-STRUKTUR
# ==========================================
MENU_STRUCTURE = [
    ("main", "menu_data", "submenu_data"),
    ("main", "menu_analysis", "submenu_analysis"),
    ("main", "menu_settings", "submenu_settings"),
    ("main", "menu_help", "submenu_help"),

    ("submenu_data", "menu_data_new", lambda: print("New clicked")),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_open", lambda: print("Open clicked")),
    ("submenu_data", "sep", None),

    # HIER IST DER IMPORT-KNOPF, DER DIE NEUE METHODE AUFRUFT:
    ("submenu_data", "menu_data_import", lambda: open_folder_and_read_files(root)),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_removefile", lambda: open_folder_and_remove_files(root)),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_quit", "DESTROY_APP"),

    ("submenu_analysis", "menu_analysis_clean", lambda: print("Clean clicked")),
    ("submenu_analysis", "sep", None),
    ("submenu_analysis", "menu_analysis_stats", lambda: starte_regression(dateipfad=r"C:\Users\aouch\PycharmProjects\PythonProject\20190701_181338_MP1_QC19C(1).txt")),
    ("submenu_analysis", "sep", None),
    ("submenu_analysis", "menu_analysis_stats", lambda: SWP_Calculation_PhaseVsFrequenz.main()),
    ("submenu_analysis", "sep", None),

    ("submenu_settings", "menu_language", "subsetting_languages"),

    ("submenu_help", "menu_help_doc", lambda: print("Doc clicked")),
]

# ==========================================
# 6. GUI INITIALISIERUNG
# ==========================================
root = tk.Tk()
root.title('GUI mit automatischem Ordner-Import')
root.geometry('400x300')

# Menü-Objekte
menus = {
    "main": tk.Menu(root),
    "submenu_data": tk.Menu(root, tearoff=0),
    "submenu_analysis": tk.Menu(root, tearoff=0),
    "submenu_settings": tk.Menu(root, tearoff=0),
    "submenu_help": tk.Menu(root, tearoff=0),
    "subsetting_languages": tk.Menu(root, tearoff=0)
}

# Sprachauswahl
menus["subsetting_languages"].add_command(label='English', command=lambda: change_language("en"))
menus["subsetting_languages"].add_separator()
menus["subsetting_languages"].add_command(label='Deutsch', command=lambda: change_language("de"))
menus["subsetting_languages"].add_separator()
menus["subsetting_languages"].add_command(label='Español', command=lambda: change_language("es"))
menus["subsetting_languages"].add_separator()
menus["subsetting_languages"].add_command(label='Français', command=lambda: change_language("fr"))

# Automatischer Menü-Aufbau
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

# Kleine Beschriftung im Fenster
lbl = tk.Label(root, text="Klicke im Menü unter 'Data' -> 'Import',\num Dateien hinzuzufügen.", pady=20)
lbl.pack()

root.mainloop()
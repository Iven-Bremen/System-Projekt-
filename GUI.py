import tkinter as tk
from tkinter import messagebox, ttk
# Wir nutzen deep-translator für die Live-Übersetzung
from deep_translator import GoogleTranslator

# ==========================================
# 1. NUR NOCH EINE ENGLISCHE BASIS-DATENBANK
# ==========================================
BASE_MENU_EN = {
    "menu_data": "Data", "menu_data_new": "New", "menu_data_open": "Open", "menu_data_save": "Save",
    "menu_data_saveas": "Save as", "menu_data_import": "Import", "menu_data_export": "Export", "menu_data_quit": "Quit",
    "menu_analysis": "Analysis", "menu_analysis_clean": "Data cleansing",
    "menu_analysis_stats": "Calculating Statistics", "menu_analysis_chart": "Plot Chart Type",
    "menu_analysis_outliers": "Detect Outliers",
    "menu_view": "View", "menu_view_chart": "Change Chart Type", "menu_view_colour": "Colour Assignment", "menu_view_fullscreen": "Full Screen",
    "menu_view_zoom": "Zoom",
    "menu_settings": "Settings", "menu_settings_units": "Units", "menu_language": "Languages",
    "menu_settings_schemes": "Colour Schemes", "menu_settings_thresholds": "Defining Thresholds",
    "menu_help": "Help", "menu_help_doc": "Documentation", "menu_help_about": "About The Application",
    "menu_help_version": "Version Number",
    "msg_title": "Info", "msg_text": "Language changed successfully!"
}

current_lang = "en"
menu_registry = []  # Hält die Verbindung: (Menü-Objekt, aktueller_text, json_key)

# Caching-System, damit wir nicht bei jedem Klick das Internet abfragen müssen
translation_cache = {
    "en": BASE_MENU_EN.copy()
}


# ==========================================
# 2. KI / BIBLIOTHEK ÜBERSETZUNGS-LOGIK
# ==========================================
def get_translation(key, lang):
    """Holt die Übersetzung aus dem Cache oder übersetzt sie live via Bibliothek."""
    # 1. Wenn die Sprache noch nie geladen wurde, legen wir ein leeres Wörterbuch an
    if lang not in translation_cache:
        translation_cache[lang] = {}

    # 2. Wenn das Wort schon übersetzt wurde, nimm es aus dem Cache (spart Zeit und Internet)
    if key in translation_cache[lang]:
        return translation_cache[lang][key]

    # 3. Wenn es die englische Basis ist, einfach zurückgeben
    if lang == "en":
        return BASE_MENU_EN.get(key, key)

    # 4. Automatisches Übersetzen mit der Bibliothek!
    try:
        english_text = BASE_MENU_EN.get(key, key)
        # GoogleTranslator übersetzt von Englisch ("en") in die Zielsprache (z.B. "es", "de", "fr")
        translated_text = GoogleTranslator(source='en', target=lang).translate(english_text)

        # Im Cache speichern
        translation_cache[lang][key] = translated_text
        return translated_text
    except Exception as e:
        print(f"Übersetzungsfehler für {key}: {e}")
        return BASE_MENU_EN.get(key, key)  # Fallback auf Englisch bei Internetproblemen


def change_language(lang_code):
    global current_lang
    current_lang = lang_code
    update_all_menus()
    messagebox.showinfo(get_translation("msg_title", current_lang), get_translation("msg_text", current_lang))


def update_all_menus():
    """Rattert die Registry durch und holt die Übersetzungen vollautomatisch."""
    for i, (menu_obj, current_label, json_key) in enumerate(menu_registry):
        new_label = get_translation(json_key, current_lang)
        try:
            menu_obj.entryconfigure(current_label, label=new_label)
            menu_registry[i] = (menu_obj, new_label, json_key)
        except tk.TclError:
            pass


# ==========================================
# 3. DIE MENÜ-STRUKTUR
# ==========================================
MENU_STRUCTURE = [
    ("main", "menu_data", "submenu_data"),
    ("main", "menu_analysis", "submenu_analysis"),
    ("main", "menu_view", "submenu_view"),
    ("main", "menu_settings", "submenu_settings"),
    ("main", "menu_help", "submenu_help"),

    ("submenu_data", "menu_data_new", lambda: print("new")),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_open", lambda: print("open")),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_save", lambda: print("save")),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_saveas", lambda: print("save_as")),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_import", lambda: print("import")),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_export", lambda: print("export")),
    ("submenu_data", "sep", None),
    ("submenu_data", "menu_data_quit", "DESTROY_APP"),

    ("submenu_analysis", "menu_analysis_clean", lambda: print("clean")),
    ("submenu_analysis", "sep", None),
    ("submenu_analysis", "menu_analysis_stats", lambda: print("stats")),
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
# 4. GUI AUFBAU
# ==========================================
root = tk.Tk()
root.title('Vollautomatische GUI')
root.geometry('300x300')

menus = {
    "main": tk.Menu(root),
    "submenu_data": tk.Menu(root, tearoff=0),
    "submenu_analysis": tk.Menu(root, tearoff=0),
    "submenu_view": tk.Menu(root, tearoff=0),
    "submenu_settings": tk.Menu(root, tearoff=0),
    "submenu_help": tk.Menu(root, tearoff=0),
    "subsetting_languages": tk.Menu(root, tearoff=0)
}

# HIER KANNST DU JETZT JEDE BELIEBIGE SPRACHE DER WELT HINZUFÜGEN!
# Einfach den ISO-Code (es = Spanisch, it = Italienisch, ja = Japanisch etc.) übergeben.
menus["subsetting_languages"].add_command(label='English', command=lambda: change_language("en"))
menus["subsetting_languages"].add_separator()
menus["subsetting_languages"].add_command(label='Deutsch', command=lambda: change_language("de"))
menus["subsetting_languages"].add_separator()
menus["subsetting_languages"].add_command(label='Español', command=lambda: change_language("es"))
menus["subsetting_languages"].add_separator()
menus["subsetting_languages"].add_command(label='Français', command=lambda: change_language("fr"))
menus["subsetting_languages"].add_separator()
menus["subsetting_languages"].add_command(label='Italiano', command=lambda: change_language("it"))

# Schleife für den automatischen Aufbau
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
root.mainloop()
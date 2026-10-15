import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

#1. Globale Übersetzungs-Datenbank
LOCALES = {
    "en": {
        "menu_settings": "Settings",
        "menu_language": "Language",
        "welcome_title": "Welcome!",
        "welcome_text": "This UI updates automatically without restarting.",
        "btn_click": "Click me",
        "msg_title": "Info",
        "msg_text": "Language changed successfully!"
    },
    "de": {
        "menu_settings": "Einstellungen",
        "menu_language": "Sprache",
        "welcome_title": "Willkommen!",
        "welcome_text": "Diese Oberfläche aktualisiert sich automatisch ohne Neustart.",
        "btn_click": "Klick mich",
        "msg_title": "Info",
        "msg_text": "Sprache erfolgreich geändert!"
    },
    "fr": {
        "menu_settings": "Paramètres",
        "menu_language": "La langue",
        "welcome_title": "Bienvenue !",
        "welcome_text": "Cette interface se met à jour automatiquement sans redémarrer.",
        "btn_click": "Cliquez-ici",
        "msg_title": "Info",
        "msg_text": "Langue changée avec succès !"
    }
}

#Globale Variablen für den Zustand
current_lang = "de"
registered_vars = []  # Speichert Tupel: (StringVar-Objekt, Translation-Key)

#Diese Widgets müssen wir global halten, da wir ihre Labels im Menü manuell updaten müssen
main_menu = None
settings_menu = None

#Hilfsfunktionen für die Übersetzung
def get_translation(key):
    """Holt die Übersetzung für den aktuellen Key mit Fallback auf Englisch."""
    try:
        return LOCALES[current_lang][key]
    except KeyError:
        return LOCALES["en"].get(key, f"[{key}]")

def register_var(string_var, key):
    """Registriert eine StringVar und setzt ihren ersten Wert."""
    registered_vars.append((string_var, key))
    string_var.set(get_translation(key))

def change_language(lang_code):
    """Wechselt die globale Sprache und aktualisiert alle Variablen und Menüs."""
    global current_lang
    if lang_code in LOCALES:
        current_lang = lang_code
#Alle registrierten StringVars aktualisieren
        for var, key in registered_vars:
            var.set(get_translation(key))

#Menü-Einträge manuell aktualisieren
        update_menu_labels()

#Feedback-Box
        messagebox.showinfo(get_translation("msg_title"), get_translation("msg_text"))

def update_menu_labels():
    """Da Tkinter-Menüs keine StringVars direkt im Label unterstützen, updaten wir sie hier."""
    if main_menu and settings_menu:
        # Ändert den Text des ersten Eintrags im Hauptmenü ("Einstellungen")
        main_menu.entryconfigure(1, label=get_translation("menu_settings"))
        # Ändert den Text des ersten Eintrags im Einstellungsmenü ("Sprache")
        settings_menu.entryconfigure(1, label=get_translation("menu_language"))
#Hauptprogramm / GUI-Setup
root = tk.Tk()
root.title("Multi-Lang Tkinter (Funktional)")
root.geometry("450x250")

#StringVars erzeugen
title_var = tk.StringVar()
text_var = tk.StringVar()
btn_var = tk.StringVar()

#Variablen registrieren (dadurch erhalten sie sofort ihren deutschen Start-Text)
register_var(title_var, "welcome_title")
register_var(text_var, "welcome_text")
register_var(btn_var, "btn_click")


#--- MENÜ ERSTELLEN ---
main_menu = tk.Menu(root)

#Einstellungs-Menü
settings_menu = tk.Menu(main_menu, tearoff=0)

#Sprachen-Auswahl (Submenu)
lang_menu = tk.Menu(settings_menu, tearoff=0)
lang_menu.add_command(label="English", command=lambda: change_language("en"))
lang_menu.add_command(label="Deutsch", command=lambda: change_language("de"))
lang_menu.add_command(label="Français", command=lambda: change_language("fr"))

#Kaskaden verknüpfen (Labels sind hier erst Platzhalter)
settings_menu.add_cascade(menu=lang_menu, label="Sprache")
main_menu.add_cascade(menu=settings_menu, label="Einstellungen")

root.config(menu=main_menu)
update_menu_labels()  # Setzt die echten, übersetzten Menü-Labels beim Start


#--- WIDGETS ERSTELLEN ---
frame = tk.Frame(root)
frame.pack(expand=True, fill="both", padx=20, pady=20)

#Titel (Groß)
lbl_title = tk.Label(frame, textvariable=title_var, font=("Arial", 16, "bold"))
lbl_title.pack(pady=(0, 10))

#Fließtext
lbl_text = tk.Label(frame, textvariable=text_var, wraplength=400, justify="center")
lbl_text.pack(pady=(0, 20))

#Button
btn = tk.Button(frame, textvariable=btn_var, command=lambda: messagebox.showinfo("Action", "Klick!"))
btn.pack()

root.mainloop()
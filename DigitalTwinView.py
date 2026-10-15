"""Live view of the digital twin (SR830 + OSTECH).

Zeigt pro Geraet:
  * Messwerte    - laufend gelesen (Geraet -> Software)
  * Einstellungen - Soll (zuletzt gesendet) gegen Ist (vom Geraet zurueckgelesen)

Status einer Einstellung:
  OK            Ist stimmt mit Soll ueberein (oder wurde nie gesendet)
  ABWEICHUNG    Geraet hat einen anderen Wert zurueckgemeldet (Wert abgelehnt, begrenzt oder gerundet)
  ausstehend    gesendet, Readback laeuft noch

Das Fenster liest ausschliesslich ``State.twin_snapshot()`` und sendet nichts selbst,
ausser ueber den Knopf "Einstellungen jetzt auslesen".
"""

import json
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import State

REFRESH_MS = 500
_window = None

_COLUMNS = ("param", "desired", "actual", "age", "status")


def _fmt(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "ON" if value else "OFF"
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, dict):
        return ", ".join(f"{k}={'1' if v else '0'}" if isinstance(v, bool) else f"{k}={v}"
                         for k, v in value.items() if k != "status_word") or "{}"
    return str(value)


class DigitalTwinWindow:
    """Toplevel window that refreshes itself every ``REFRESH_MS`` milliseconds."""

    def __init__(self, root):
        self.root = root
        self.win = tk.Toplevel(root)
        self.win.title("Digital Twin - SR830 / OSTECH")
        self.win.geometry("900x620")
        self.win.configure(bg="#1e1e1e")
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self._items = set()
        self._job = None

        style = ttk.Style(self.win)
        style.configure("Twin.Treeview", background="#111111", foreground="#dddddd",
                        fieldbackground="#111111", rowheight=20, font=("Consolas", 9))
        style.configure("Twin.Treeview.Heading", font=("Consolas", 9, "bold"))
        style.map("Twin.Treeview", background=[("selected", "#37474f")])

        top = tk.Frame(self.win, bg="#1e1e1e")
        top.pack(fill="x", padx=8, pady=6)
        self.lbl_status = tk.Label(top, text="", bg="#1e1e1e", fg="#aaaaaa", font=("Consolas", 9), anchor="w")
        self.lbl_status.pack(side="left", fill="x", expand=True)
        tk.Button(top, text="Einstellungen jetzt auslesen", font=("Consolas", 8, "bold"),
                  command=self.refresh_settings).pack(side="right", padx=4)
        tk.Button(top, text="Export JSON", font=("Consolas", 8, "bold"),
                  command=self.export_json).pack(side="right", padx=4)

        frame = tk.Frame(self.win, bg="#1e1e1e")
        frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tree = ttk.Treeview(frame, columns=_COLUMNS, style="Twin.Treeview", show="tree headings")
        self.tree.heading("#0", text="Geraet / Bereich")
        self.tree.column("#0", width=190, stretch=False)
        for column, title, width in (("param", "Parameter", 150), ("desired", "Soll (gesendet)", 150),
                                     ("actual", "Ist (Geraet)", 190), ("age", "Alter", 60),
                                     ("status", "Status", 110)):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, anchor="w")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.tag_configure("ok", foreground="#66ff99")
        self.tree.tag_configure("bad", foreground="#ff5555")
        self.tree.tag_configure("pending", foreground="#ffcc00")
        self.tree.tag_configure("group", foreground="#00ffcc")
        self.tree.tag_configure("off", foreground="#777777")

        self.update_view()

    # ------------------------------------------------------------------ helpers
    def _upsert(self, iid, parent, text, values, tag):
        if iid in self._items:
            self.tree.item(iid, text=text, values=values, tags=(tag,))
        else:
            self.tree.insert(parent, "end", iid=iid, text=text, values=values, tags=(tag,), open=True)
            self._items.add(iid)

    def update_view(self):
        """Redraw from one consistent snapshot of the twin."""
        try:
            snapshot = State.twin_snapshot()
            now = snapshot["timestamp"]
            summary = []
            for device in State.TWIN_DEVICES:
                twin = snapshot[device]
                compare = twin["compare"]
                mismatch = {key: (desired, actual) for key, desired, actual in compare["mismatch"]}
                pending = set(compare["pending"])
                connected = twin["connected"]
                summary.append(f"{device}: {'verbunden' if connected else 'getrennt'}"
                               f"{f', {len(mismatch)} Abweichung(en)' if mismatch else ''}")

                self._upsert(f"{device}", "", f"{device} {'🟢' if connected else '🔴'}",
                             ("", "", "", "", "verbunden" if connected else "getrennt"),
                             "group" if connected else "off")
                self._upsert(f"{device}|m", device, "Messwerte", ("", "", "", "", ""), "group")
                self._upsert(f"{device}|s", device, "Einstellungen", ("", "", "", "", ""), "group")

                for name, value in sorted(twin["measured"].items()):
                    age = now - twin["measured_ts"].get(name, now)
                    self._upsert(f"{device}|m|{name}", f"{device}|m", "",
                                 (name, "", _fmt(value), f"{age:.1f}s", ""), "ok" if age < 5 else "off")

                for key in sorted(set(twin["settings"]) | set(twin["desired"])):
                    desired = twin["desired"].get(key)
                    actual = twin["settings"].get(key)
                    age = now - twin["settings_ts"][key] if key in twin["settings_ts"] else None
                    if key in mismatch:
                        status, tag = "ABWEICHUNG", "bad"
                    elif key in pending:
                        status, tag = "ausstehend", "pending"
                    else:
                        status, tag = "OK", "ok"
                    self._upsert(f"{device}|s|{key}", f"{device}|s", "",
                                 (key, _fmt(desired), _fmt(actual),
                                  "" if age is None else f"{age:.1f}s", status), tag)

                # Eintraege entfernen, die nach Trennen nicht mehr existieren
                valid = {f"{device}|m|{n}" for n in twin["measured"]} | \
                        {f"{device}|s|{k}" for k in set(twin["settings"]) | set(twin["desired"])}
                for iid in [i for i in self._items if i.startswith(f"{device}|") and i.count("|") == 2 and i not in valid]:
                    self.tree.delete(iid)
                    self._items.discard(iid)
            self.lbl_status.config(text="   |   ".join(summary))
        except Exception as error:   # die Anzeige darf nie die GUI blockieren
            self.lbl_status.config(text=f"Anzeige-Fehler: {type(error).__name__}: {error}")
        self._job = self.win.after(REFRESH_MS, self.update_view)

    # ------------------------------------------------------------------ actions
    def refresh_settings(self):
        try:
            import Komunikation
            Komunikation.request_settings_refresh()
        except Exception as error:
            messagebox.showerror("Digital Twin", f"Auslesen nicht moeglich:\n{error}", parent=self.win)

    def export_json(self):
        path = filedialog.asksaveasfilename(parent=self.win, defaultextension=".json",
                                            initialfile=f"digital_twin_{time.strftime('%Y%m%d_%H%M%S')}.json",
                                            filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(State.twin_snapshot(), handle, indent=2, default=str, ensure_ascii=False)
        except OSError as error:
            messagebox.showerror("Digital Twin", f"Export fehlgeschlagen:\n{error}", parent=self.win)

    def close(self):
        global _window
        if self._job is not None:
            try:
                self.win.after_cancel(self._job)
            except Exception:
                pass
        _window = None
        self.win.destroy()


def open_twin_window(root):
    """Open the twin window, or bring the existing one to the front."""
    global _window
    if _window is not None:
        try:
            _window.win.deiconify()
            _window.win.lift()
            return _window
        except tk.TclError:
            _window = None
    _window = DigitalTwinWindow(root)
    return _window

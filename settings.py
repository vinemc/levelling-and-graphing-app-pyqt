import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
import json
import logging
from pathlib import Path

# --- CONSTANTS ---
SETTINGS_FILE = "settings.json"
DEFAULT_AUTOSAVE_INTERVAL_MIN = 5

# --- SETTINGS STATE ---
settings = {
    "precision": 3,
    "theme": "Light",
    "graph_line_color": "royalblue",
    "graph_marker_color": "orange",
    "comparison_line_color": "green",
    "label_color": "darkred",
    "grade_slope_label_color": "blue",
    "autosave_interval": 5,
    "recent_files": [],
    "result_table_columns": [],
    "profile_table_columns": [],
    "onboarding_complete": False,
    "follow_system_theme": True,
}

STATUS_BAR_CLEAR_DELAY = 4000
INPUT_VALIDATION_HIGHLIGHT_DELAY = 3000

def load_settings():
    global settings
    try:
        with open(SETTINGS_FILE, 'r') as f:
            loaded = json.load(f)
            settings.update(loaded)
    except Exception as e:
        logging.info(f"Could not load settings: {e}")

def save_settings():
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logging.error(f"Could not save settings: {e}")

def detect_system_theme():
    """Detect system dark/light mode (Windows only). Returns 'Dark' or 'Light'."""
    try:
        import platform
        if platform.system() == 'Windows':
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize") as key:
                val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return "Light" if val == 1 else "Dark"
    except Exception:
        pass
    return "Light"

class SettingsDialog:
    def __init__(self, master, apply_theme_callback, update_graph_callback):
        self.master = master
        self.apply_theme_callback = apply_theme_callback
        self.update_graph_callback = update_graph_callback
        self._settings_win = None

    def open_settings(self):
        # Prevent multiple settings windows
        if self._settings_win is not None and self._settings_win.winfo_exists():
            self._settings_win.lift()
            self._settings_win.focus_force()
            return
        win = tk.Toplevel(self.master)
        self._settings_win = win
        win.title("⚙️ Settings & Support")
        win.geometry("350x500")
        win.resizable(False, False)

        def on_close():
            save_settings()
            self._settings_win = None
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", on_close)

        notebook = ttk.Notebook(win)
        notebook.pack(pady=10, padx=10, fill="both", expand=True)

        # --- General Tab ---
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")

        ttk.Label(general_frame, text="Decimal Places:", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(10, 0))
        precision_var = tk.IntVar(value=settings["precision"])
        precision_spin = ttk.Spinbox(general_frame, from_=1, to=6, textvariable=precision_var, width=5)
        precision_spin.pack(anchor="w", padx=40)

        ttk.Label(general_frame, text="Theme Mode:", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(10, 0))
        theme_var = tk.StringVar(value=settings["theme"])
        ttk.Radiobutton(general_frame, text="Light", variable=theme_var, value="Light").pack(anchor="w", padx=40)
        ttk.Radiobutton(general_frame, text="Dark", variable=theme_var, value="Dark").pack(anchor="w", padx=40)

        # Follow system theme
        follow_system_var = tk.BooleanVar(value=settings.get("follow_system_theme", True))
        ttk.Checkbutton(general_frame, text="Follow system theme (Windows)", variable=follow_system_var).pack(anchor="w", padx=40, pady=(5,0))

        # Autosave interval
        ttk.Label(general_frame, text="Autosave Interval (minutes):", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(10, 0))
        autosave_var = tk.IntVar(value=settings.get("autosave_interval", DEFAULT_AUTOSAVE_INTERVAL_MIN))
        autosave_spin = ttk.Spinbox(general_frame, from_=1, to=60, textvariable=autosave_var, width=5)
        autosave_spin.pack(anchor="w", padx=40)

        # --- Graph Tab ---
        graph_frame = ttk.Frame(notebook)
        notebook.add(graph_frame, text="Graph")

        line_color_var = tk.StringVar(value=settings.get("graph_line_color", "royalblue"))
        marker_color_var = tk.StringVar(value=settings.get("graph_marker_color", "orange"))

        def choose_color(var, title):
            color_code = colorchooser.askcolor(title=title)[1]
            if color_code:
                var.set(color_code)

        ttk.Label(graph_frame, text="Graph Colors:", font=("Arial", 11, "bold")).pack(anchor="w", padx=20, pady=(10,5))

        line_frame = ttk.Frame(graph_frame)
        line_frame.pack(fill="x", padx=20, pady=5)
        ttk.Label(line_frame, text="Line Color:").pack(side="left")
        line_color_btn = ttk.Button(line_frame, text="Choose...", command=lambda v=line_color_var, t="Choose Line Color": choose_color(v, t))
        line_color_btn.pack(side="right")
        line_color_label = ttk.Label(line_frame, textvariable=line_color_var, relief="sunken", width=10)
        line_color_label.pack(side="right", padx=5)

        marker_frame = ttk.Frame(graph_frame)
        marker_frame.pack(fill="x", padx=20, pady=5)
        ttk.Label(marker_frame, text="Marker Color:").pack(side="left")
        marker_color_btn = ttk.Button(marker_frame, text="Choose...", command=lambda v=marker_color_var, t="Choose Marker Color": choose_color(v, t))
        marker_color_btn.pack(side="right")
        marker_color_label = ttk.Label(marker_frame, textvariable=marker_color_var, relief="sunken", width=10)
        marker_color_label.pack(side="right", padx=5)

        # --- Auto-save settings on change ---
        def update_and_save_settings(*args):
            settings["precision"] = precision_var.get()
            settings["theme"] = theme_var.get()
            settings["graph_line_color"] = line_color_var.get()
            settings["graph_marker_color"] = marker_color_var.get()
            settings["autosave_interval"] = autosave_var.get()
            settings["follow_system_theme"] = follow_system_var.get()
            save_settings()
            self.apply_theme_callback()
            self.update_graph_callback()

        # Bind changes to auto-save
        precision_var.trace_add('write', update_and_save_settings)
        theme_var.trace_add('write', update_and_save_settings)
        line_color_var.trace_add('write', update_and_save_settings)
        marker_color_var.trace_add('write', update_and_save_settings)
        autosave_var.trace_add('write', update_and_save_settings)
        follow_system_var.trace_add('write', update_and_save_settings)

        ttk.Button(win, text="Close", command=on_close, style="Accent.TButton").pack(pady=15)
        ttk.Label(win, text="Support: levelingapp@example.com", font=("Arial", 9), style="Dim.TLabel").pack(side="bottom", pady=5)

        # Add import/export settings buttons
        def import_settings():
            file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
            if not file_path:
                return
            try:
                with open(file_path, "r") as f:
                    imported = json.load(f)
                settings.update(imported)
                save_settings()
                self.apply_theme_callback()
                self.update_graph_callback()
                messagebox.showinfo("Import Successful", "Settings imported.")
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import settings:\n{e}")
        def export_settings():
            file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
            if not file_path:
                return
            try:
                with open(file_path, "w") as f:
                    json.dump(settings, f, indent=2)
                messagebox.showinfo("Export Successful", "Settings exported.")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export settings:\n{e}")
        ttk.Button(win, text="Import Settings", command=import_settings).pack(pady=2)
        ttk.Button(win, text="Export Settings", command=export_settings).pack(pady=2) 
import json
import logging
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from .lang import LANG
from . import DEFAULT_ROW_COUNT

class SessionManager:
    def __init__(self, settings):
        self.settings = settings

    def save_session(self, data):
        """Save current session (data, settings, etc.)"""
        def get_value(var):
            return var.get() if hasattr(var, 'get') else var
        session = {
            "data": [[get_value(var) for var in row] for row in data],
            "settings": self.settings.copy(),
        }
        try:
            with Path("last_session.json").open("w") as f:
                json.dump(session, f)
            return True
        except Exception as e:
            logging.error(f"Could not save session: {e}")
            return False

    def load_session(self):
        """Load session data from file"""
        try:
            with Path("last_session.json").open("r") as f:
                session = json.load(f)
            return session
        except Exception as e:
            logging.error(f"Could not load session: {e}")
            return None

    def offer_session_restore(self, master):
        """Offer to restore session if one exists"""
        if Path("last_session.json").exists():
            if messagebox.askyesno(LANG["session_restore"], LANG["session_found"]):
                return self.load_session()
        return None

    def restore_session_data(self, session, data, redraw_callback, progress_bar=None, rl_fields=None, results_table=None, undo_stack=None, redo_stack=None, status_callback=None):
        """Restore session data to the application, with progress bar and no graph update."""
        if not session:
            return False
        try:
            # Show and start progress bar if provided
            if progress_bar is not None:
                progress_bar.pack(side="left", padx=20, pady=5)
                progress_bar.start()
                progress_bar.update_idletasks()

            # Restore data
            data.clear()
            restored_rows = session["data"]
            for idx, row_data in enumerate(restored_rows):
                row_vars = [tk.StringVar(value=val) for val in row_data]
                data.append(row_vars)
                if progress_bar is not None:
                    progress_bar.step(1)
                    progress_bar.update_idletasks()
            # Pad to DEFAULT_ROW_COUNT
            while len(data) < DEFAULT_ROW_COUNT:
                data.append([tk.StringVar() for _ in range(len(restored_rows[0]) if restored_rows else 4)])
                if progress_bar is not None:
                    progress_bar.step(1)
                    progress_bar.update_idletasks()
            redraw_callback()
            
            # Clear RL fields if provided
            if rl_fields is not None:
                for entry in rl_fields:
                    entry.delete(0, tk.END)

            # Clear results table if provided
            if results_table is not None:
                results_table.delete(*results_table.get_children())

            # Clear undo/redo stacks if provided
            if undo_stack is not None:
                undo_stack.clear()
            if redo_stack is not None:
                redo_stack.clear()

            # Restore settings (except theme, to avoid flicker)
            for k, v in session["settings"].items():
                if k != "theme":
                    self.settings[k] = v
            
            # Stop and hide progress bar
            if progress_bar is not None:
                progress_bar.stop()
                progress_bar.pack_forget()

            # Show status message if callback provided
            if status_callback is not None:
                status_callback("Session restored. Please recalculate to update results.")

            return True
        except Exception as e:
            if progress_bar is not None:
                progress_bar.stop()
                progress_bar.pack_forget()
            messagebox.showerror(LANG["session_restore_error"], f"{LANG['could_not_restore_session']}\n{e}")
            return False

    def check_unsaved_changes(self, dirty):
        """Check if there are unsaved changes before closing"""
        if dirty:
            return messagebox.askyesno(LANG["confirm"], LANG["unsaved_changes"])
        return True 
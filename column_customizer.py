import tkinter as tk
from tkinter import ttk, messagebox

class ColumnCustomizer:
    def __init__(self, master, settings, save_settings_callback, apply_column_settings_callback):
        self.master = master
        self.settings = settings
        self.save_settings_callback = save_settings_callback
        self.apply_column_settings_callback = apply_column_settings_callback

    def customize_columns_dialog(self, table_type):
        """Show dialog to customize columns for result/profile tables."""
        if table_type == 'result':
            default_cols = ['Point', 'BS', 'IS', 'FS', 'HI', 'RL', 'Adjustment', 'Adjusted RL']
            settings_key = "result_table_columns"
        else:
            default_cols = ['Point', 'Elevation', 'Distance']
            settings_key = "profile_table_columns"
        
        # Get current settings or default
        col_settings = self.settings.get(settings_key, [])
        if not col_settings or set(c[0] for c in col_settings) != set(default_cols):
            col_settings = [(col, True) for col in default_cols]
        
        # Dialog
        win = tk.Toplevel(self.master)
        win.title("Customize Columns")
        win.geometry("320x400")
        win.resizable(False, False)
        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # List of (col, shown) tuples
        vars = []
        for col, shown in col_settings:
            var = tk.BooleanVar(value=shown)
            vars.append((col, var))
        
        # Listbox for order
        listbox = tk.Listbox(frame, selectmode="single")
        for col, var in vars:
            listbox.insert("end", col)
        listbox.grid(row=0, column=0, rowspan=6, sticky="ns")
        
        # Checkboxes for show/hide
        checkboxes = []
        for i, (col, var) in enumerate(vars):
            cb = ttk.Checkbutton(frame, text=col, variable=var)
            cb.grid(row=i, column=1, sticky="w")
            checkboxes.append(cb)
        
        # Up/Down buttons
        def move(up):
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if up and idx == 0:
                return
            if not up and idx == len(vars) - 1:
                return
            vars[idx], vars[idx-1 if up else idx+1] = vars[idx-1 if up else idx+1], vars[idx]
            # Update listbox
            listbox.delete(0, "end")
            for col, _ in vars:
                listbox.insert("end", col)
            listbox.selection_set(idx-1 if up else idx+1)
        
        up_btn = ttk.Button(frame, text="↑", width=3, command=lambda: move(True))
        up_btn.grid(row=0, column=2, sticky="n")
        down_btn = ttk.Button(frame, text="↓", width=3, command=lambda: move(False))
        down_btn.grid(row=1, column=2, sticky="n")
        
        # Save/apply
        def apply():
            # Prevent hiding all columns
            if sum(var.get() for _, var in vars) == 0:
                messagebox.showerror("Column Error", "At least one column must be visible.")
                return
            new_settings = [(col, var.get()) for col, var in vars]
            self.settings[settings_key] = new_settings
            self.save_settings_callback()
            self.apply_column_settings_callback(table_type)
            win.destroy()
        
        ttk.Button(frame, text="Apply", command=apply).grid(row=7, column=1, pady=10)
        ttk.Button(frame, text="Cancel", command=win.destroy).grid(row=7, column=2, pady=10)

    def apply_column_settings(self, table_type, result_table=None, graph_tree=None):
        """Apply user column settings to result/profile tables."""
        if table_type == 'result':
            tree = result_table
            settings_key = "result_table_columns"
        else:
            tree = graph_tree
            settings_key = "profile_table_columns"
        
        if not tree:
            return
            
        col_settings = self.settings.get(settings_key, [])
        if not col_settings:
            return
        
        # Set columns and hide as needed
        cols = [col for col, shown in col_settings if shown]
        tree["displaycolumns"] = cols
        
        # Reorder columns
        tree["columns"] = [col for col, _ in col_settings]
        
        # Optionally, could also update headings here
        for col in tree["columns"]:
            tree.heading(col, text=col)
        
        tree.update() 
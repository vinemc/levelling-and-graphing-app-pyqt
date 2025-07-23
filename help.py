import tkinter as tk
from tkinter import ttk
from .lang import LANG

class HelpManager:
    def __init__(self, master):
        self.master = master

    def init_help_tab(self, notebook):
        """Initializes the Help/Guide tab with instructional text."""
        help_frame = ttk.Frame(notebook)
        notebook.add(help_frame, text="Help / Guide")

        help_text_widget = tk.Text(help_frame, wrap="word", font=("Arial", 10), relief="flat", background="#f0f0f0")
        help_text_widget.pack(padx=15, pady=15, fill="both", expand=True)

        # --- Help Content ---
        title_font = ("Arial", 14, "bold")
        heading_font = ("Arial", 12, "bold")
        
        help_text_widget.tag_configure("title", font=title_font, spacing3=10)
        help_text_widget.tag_configure("heading", font=heading_font, spacing3=5)
        help_text_widget.tag_configure("bullet", lmargin1=20, lmargin2=20)

        help_text_widget.insert("end", LANG["help_welcome"] + "\n", "title")
        
        help_text_widget.insert("end", "\n" + LANG["help_getting_started"] + "\n", "heading")
        help_text_widget.insert("end", " • ", "bullet")
        help_text_widget.insert("end", LANG["help_enter_first_rl"] + "\n")
        help_text_widget.insert("end", " • ", "bullet")
        help_text_widget.insert("end", LANG["help_input_readings"] + "\n")
        help_text_widget.insert("end", " • ", "bullet")
        help_text_widget.insert("end", LANG["help_change_point"] + "\n")
        help_text_widget.insert("end", " • ", "bullet")
        help_text_widget.insert("end", LANG["help_final_reading"] + "\n")

        help_text_widget.insert("end", "\n" + LANG["help_calculation"] + "\n", "heading")
        help_text_widget.insert("end", " • ", "bullet")
        help_text_widget.insert("end", LANG["help_choose_method"] + "\n")
        help_text_widget.insert("end", " • ", "bullet")
        help_text_widget.insert("end", LANG["help_enter_last_rl"] + "\n")
        help_text_widget.insert("end", " • ", "bullet")
        help_text_widget.insert("end", LANG["help_calculate_update"] + "\n")

        help_text_widget.insert("end", "\n" + LANG["help_profile_graph"] + "\n", "heading")
        help_text_widget.insert("end", " • ", "bullet")
        help_text_widget.insert("end", LANG["help_plot_rl"] + "\n")
        help_text_widget.insert("end", " • ", "bullet")
        help_text_widget.insert("end", LANG["help_graph_controls"] + "\n")
        help_text_widget.insert("end", " • ", "bullet")
        help_text_widget.insert("end", LANG["help_comparison_profile"] + "\n")
        help_text_widget.insert("end", " • ", "bullet")
        help_text_widget.insert("end", LANG["help_cut_fill"] + "\n")

        help_text_widget.insert("end", "\n" + LANG["help_data_management"] + "\n", "heading")
        help_text_widget.insert("end", " • ", "bullet")
        help_text_widget.insert("end", LANG["help_import_csv"] + "\n")
        help_text_widget.insert("end", " • ", "bullet")
        help_text_widget.insert("end", LANG["help_save_db"] + "\n")
        help_text_widget.insert("end", " • ", "bullet")
        help_text_widget.insert("end", LANG["help_right_click"] + "\n")

        help_text_widget.config(state="disabled") # Make text read-only 
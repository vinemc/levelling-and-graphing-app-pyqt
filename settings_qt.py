from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QWidget, QSpinBox, QRadioButton, QButtonGroup, QCheckBox, QColorDialog, QFileDialog, QLineEdit, QDialogButtonBox
)
from PyQt6.QtCore import Qt
import json
from .settings import settings, save_settings, DEFAULT_AUTOSAVE_INTERVAL_MIN

class SettingsDialog(QDialog):
    def __init__(self, parent, apply_theme_callback, update_graph_callback):
        super().__init__(parent)
        self.apply_theme_callback = apply_theme_callback
        self.update_graph_callback = update_graph_callback
        self.setWindowTitle("⚙️ Settings & Support")
        self.setMinimumSize(400, 500)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        # General Tab
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        # Decimal Places
        general_layout.addWidget(QLabel("Decimal Places:"))
        self.precision_spin = QSpinBox()
        self.precision_spin.setRange(1, 6)
        self.precision_spin.setValue(settings.get("precision", 3))
        general_layout.addWidget(self.precision_spin)
        # Theme
        general_layout.addWidget(QLabel("Theme Mode:"))
        self.theme_light_radio = QRadioButton("Light")
        self.theme_dark_radio = QRadioButton("Dark")
        theme_group = QButtonGroup(self)
        theme_group.addButton(self.theme_light_radio)
        theme_group.addButton(self.theme_dark_radio)
        if settings.get("theme", "Light") == "Dark":
            self.theme_dark_radio.setChecked(True)
        else:
            self.theme_light_radio.setChecked(True)
        general_layout.addWidget(self.theme_light_radio)
        general_layout.addWidget(self.theme_dark_radio)
        # Follow system theme
        self.follow_system_cb = QCheckBox("Follow system theme (Windows)")
        self.follow_system_cb.setChecked(settings.get("follow_system_theme", True))
        general_layout.addWidget(self.follow_system_cb)
        # Autosave interval
        general_layout.addWidget(QLabel("Autosave Interval (minutes):"))
        self.autosave_spin = QSpinBox()
        self.autosave_spin.setRange(1, 60)
        self.autosave_spin.setValue(settings.get("autosave_interval", DEFAULT_AUTOSAVE_INTERVAL_MIN))
        general_layout.addWidget(self.autosave_spin)
        tabs.addTab(general_tab, "General")
        # Graph Tab
        graph_tab = QWidget()
        graph_layout = QVBoxLayout(graph_tab)
        graph_layout.addWidget(QLabel("Graph Colors:"))
        # Line color
        line_color_layout = QHBoxLayout()
        line_color_layout.addWidget(QLabel("Line Color:"))
        self.line_color_btn = QPushButton(settings.get("graph_line_color", "royalblue"))
        self.line_color_btn.clicked.connect(self.choose_line_color)
        line_color_layout.addWidget(self.line_color_btn)
        graph_layout.addLayout(line_color_layout)
        # Marker color
        marker_color_layout = QHBoxLayout()
        marker_color_layout.addWidget(QLabel("Marker Color:"))
        self.marker_color_btn = QPushButton(settings.get("graph_marker_color", "orange"))
        self.marker_color_btn.clicked.connect(self.choose_marker_color)
        marker_color_layout.addWidget(self.marker_color_btn)
        graph_layout.addLayout(marker_color_layout)
        
        # Comparison line color
        comparison_color_layout = QHBoxLayout()
        comparison_color_layout.addWidget(QLabel("Comparison Line Color:"))
        self.comparison_color_btn = QPushButton(settings.get("comparison_line_color", "green"))
        self.comparison_color_btn.clicked.connect(self.choose_comparison_color)
        comparison_color_layout.addWidget(self.comparison_color_btn)
        graph_layout.addLayout(comparison_color_layout)
        
        # Label color
        label_color_layout = QHBoxLayout()
        label_color_layout.addWidget(QLabel("Label Color:"))
        self.label_color_btn = QPushButton(settings.get("label_color", "darkred"))
        self.label_color_btn.clicked.connect(self.choose_label_color)
        label_color_layout.addWidget(self.label_color_btn)
        graph_layout.addLayout(label_color_layout)
        
        # Grade slope label color
        slope_color_layout = QHBoxLayout()
        slope_color_layout.addWidget(QLabel("Grade Slope Label Color:"))
        self.slope_color_btn = QPushButton(settings.get("grade_slope_label_color", "blue"))
        self.slope_color_btn.clicked.connect(self.choose_slope_color)
        slope_color_layout.addWidget(self.slope_color_btn)
        graph_layout.addLayout(slope_color_layout)
        tabs.addTab(graph_tab, "Graph")
        # Tooltip toggle
        self.tooltips_checkbox = QCheckBox("Show tooltips (context help)")
        self.tooltips_checkbox.setChecked(settings.get('show_tooltips', True))
        self.tooltips_checkbox.stateChanged.connect(self.toggle_tooltips)
        layout.addWidget(self.tooltips_checkbox)
        # Support info
        layout.addWidget(QLabel("Support: levelingapp@example.com"))
        # Import/Export settings
        import_btn = QPushButton("Import Settings")
        import_btn.clicked.connect(self.import_settings)
        layout.addWidget(import_btn)
        export_btn = QPushButton("Export Settings")
        export_btn.clicked.connect(self.export_settings)
        layout.addWidget(export_btn)
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        # Connect signals for auto-save
        self.precision_spin.valueChanged.connect(self.update_and_save_settings)
        self.theme_light_radio.toggled.connect(self.update_and_save_settings)
        self.theme_dark_radio.toggled.connect(self.update_and_save_settings)
        self.follow_system_cb.toggled.connect(self.update_and_save_settings)
        self.autosave_spin.valueChanged.connect(self.update_and_save_settings)
    def choose_line_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.line_color_btn.setText(color.name())
            self.update_and_save_settings()
    def choose_marker_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.marker_color_btn.setText(color.name())
            self.update_and_save_settings()
            
    def choose_comparison_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.comparison_color_btn.setText(color.name())
            self.update_and_save_settings()
            
    def choose_label_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.label_color_btn.setText(color.name())
            self.update_and_save_settings()
            
    def choose_slope_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.slope_color_btn.setText(color.name())
            self.update_and_save_settings()
    def update_and_save_settings(self):
        settings["precision"] = self.precision_spin.value()
        settings["theme"] = "Dark" if self.theme_dark_radio.isChecked() else "Light"
        settings["graph_line_color"] = self.line_color_btn.text()
        settings["graph_marker_color"] = self.marker_color_btn.text()
        settings["comparison_line_color"] = self.comparison_color_btn.text()
        settings["label_color"] = self.label_color_btn.text()
        settings["grade_slope_label_color"] = self.slope_color_btn.text()
        settings["autosave_interval"] = self.autosave_spin.value()
        settings["follow_system_theme"] = self.follow_system_cb.isChecked()
        save_settings()
        self.apply_theme_callback()
        self.update_graph_callback()
    def toggle_tooltips(self, state):
        settings['show_tooltips'] = bool(state)
        save_settings()
    def import_settings(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Settings", "", "JSON Files (*.json)")
        if not file_path:
            return
        try:
            with open(file_path, "r") as f:
                imported = json.load(f)
            settings.update(imported)
            save_settings()
            self.apply_theme_callback()
            self.update_graph_callback()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Import Successful", "Settings imported.")
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Import Error", f"Failed to import settings:\n{e}")
    def export_settings(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Settings", "", "JSON Files (*.json)")
        if not file_path:
            return
        try:
            with open(file_path, "w") as f:
                json.dump(settings, f, indent=2)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Export Successful", "Settings exported.")
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Export Error", f"Failed to export settings:\n{e}") 
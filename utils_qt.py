from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QCheckBox, QComboBox, QHeaderView, QToolTip, QWidget, QApplication
)
from PyQt6.QtCore import Qt, QPoint, QObject
from pathlib import Path
import csv
import json
from PyQt6.QtGui import QPalette, QColor
from .settings import settings

class Tooltip(QObject):
    _tooltip_label = None

    def __init__(self, widget, text):
        super().__init__(widget)
        self.widget = widget
        self.text = text
        widget.installEventFilter(self)
        if Tooltip._tooltip_label is None:
            Tooltip._tooltip_label = QLabel()
            Tooltip._tooltip_label.setWindowFlags(Qt.WindowType.ToolTip)
            Tooltip._tooltip_label.setStyleSheet("""
                QLabel {
                    background-color: #ffffe0;
                    border: 1px solid black;
                    padding: 2px;
                    color: black;
                }
            """)

    def eventFilter(self, obj, event):
        if obj == self.widget:
            if not settings.get('show_tooltips', True):
                return False
            if event.type() == event.Type.Enter:
                Tooltip._tooltip_label.setText(self.text)
                Tooltip._tooltip_label.move(self.widget.mapToGlobal(QPoint(0, self.widget.height())))
                Tooltip._tooltip_label.show()
            elif event.type() == event.Type.Leave:
                Tooltip._tooltip_label.hide()
        return False

class ImportDialog(QDialog):
    def __init__(self, parent, file_path, target_columns):
        super().__init__(parent)
        self.setWindowTitle("Import Preview")
        self.setMinimumSize(800, 500)
        self.file_path = file_path
        self.target_columns = target_columns
        self.import_result = None  # Use this instead of self.result
        self.csv_header = []
        self.csv_preview_data = []
        self._read_csv_preview()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"File: {Path(self.file_path).name}"))
        # Mapping
        map_layout = QHBoxLayout()
        self.map_combos = []
        options = ["None"] + self.target_columns
        for col_name in self.csv_header:
            vbox = QVBoxLayout()
            vbox.addWidget(QLabel(f"'{col_name}':"))
            combo = QComboBox()
            combo.addItems(options)
            # Attempt to auto-map
            for i, target_col in enumerate(self.target_columns):
                if col_name.lower() == target_col.lower():
                    combo.setCurrentIndex(i+1)
                    break
            vbox.addWidget(combo)
            self.map_combos.append(combo)
            map_layout.addLayout(vbox)
        layout.addLayout(map_layout)
        # Preview
        preview_table = QTableWidget(len(self.csv_preview_data), len(self.csv_header))
        preview_table.setHorizontalHeaderLabels(self.csv_header)
        for row_idx, row_data in enumerate(self.csv_preview_data):
            for col_idx, value in enumerate(row_data):
                preview_table.setItem(row_idx, col_idx, QTableWidgetItem(value))
        header = preview_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(preview_table)
        # Options
        self.has_header_cb = QCheckBox("File has a header row (first row will be skipped)")
        self.has_header_cb.setChecked(True)
        layout.addWidget(self.has_header_cb)
        # Buttons
        btn_layout = QHBoxLayout()
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self._on_import)
        btn_layout.addWidget(import_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _read_csv_preview(self):
        try:
            with open(self.file_path, 'r', newline='') as f:
                reader = csv.reader(f)
                self.csv_header = next(reader, [])
                for i, row in enumerate(reader):
                    if i >= 10: break
                    self.csv_preview_data.append(row)
        except Exception as e:
            self.csv_header = []
            self.csv_preview_data = []

    def _on_import(self):
        mapping = {}
        for i, combo in enumerate(self.map_combos):
            col_name = combo.currentText()
            if col_name != "None":
                if col_name in mapping:
                    return  # Duplicate mapping, ignore
                mapping[col_name] = i
        self.import_result = {
            "mapping": mapping,
            "has_header": self.has_header_cb.isChecked()
        }
        self.accept()

def show_onboarding(parent, settings, save_settings_callback):
    dialog = QDialog(parent)
    dialog.setWindowTitle("Welcome to Leveling & Graphing App!")
    dialog.setMinimumSize(500, 400)
    layout = QVBoxLayout(dialog)
    title = QLabel("Welcome!")
    title.setStyleSheet("font-size: 16pt; font-weight: bold;")
    layout.addWidget(title)
    tips = (
        "• Enter your first RL and survey readings in the Leveling Calculator tab.\n"
        "• Use the 'Calculate & Update Graph' button to see results and plot the profile.\n"
        "• Right-click tables for options like Copy, Paste, Delete, and Customize Columns.\n"
        "• Drag and drop CSV or DB files onto the window to import data.\n"
        "• Use the Profile Graph tab for visualization, cut/fill analysis, and exporting.\n"
        "• Access settings (theme, autosave, colors) via the ⚙️ button or Ctrl+Shift+S.\n"
        "• Undo/Redo with Ctrl+Z / Ctrl+Y.\n"
        "• See the Help tab for a full guide.\n"
    )
    msg = QLabel(tips)
    msg.setStyleSheet("font-size: 11pt;")
    msg.setWordWrap(True)
    layout.addWidget(msg)
    btn = QPushButton("Get Started!")
    btn.clicked.connect(dialog.accept)
    layout.addWidget(btn)
    settings["onboarding_complete"] = True
    save_settings_callback()
    dialog.exec()

def show_about(parent=None):
    dialog = QDialog(parent)
    dialog.setWindowTitle("About")
    layout = QVBoxLayout(dialog)
    about_text = QLabel("<b>Leveling & Graphing App</b><br>Version 1.0.0<br>© 2024 Your Name")
    about_text.setTextFormat(Qt.TextFormat.RichText)
    layout.addWidget(about_text)
    btn = QPushButton("OK")
    btn.clicked.connect(dialog.accept)
    layout.addWidget(btn)
    dialog.exec()

def apply_theme_qt():
    """Load custom_theme.json and apply as QPalette to QApplication."""
    import os
    from PyQt6.QtWidgets import QApplication
    theme_path = os.path.join(os.path.dirname(__file__), 'custom_theme.json')
    try:
        with open(theme_path, 'r') as f:
            theme = json.load(f)
    except Exception:
        return  # Fail silently if theme file missing
    palette = QPalette()
    # Map theme keys to QPalette roles
    role_map = {
        'Window': QPalette.ColorRole.Window,
        'WindowText': QPalette.ColorRole.WindowText,
        'Base': QPalette.ColorRole.Base,
        'AlternateBase': QPalette.ColorRole.AlternateBase,
        'ToolTipBase': QPalette.ColorRole.ToolTipBase,
        'ToolTipText': QPalette.ColorRole.ToolTipText,
        'Text': QPalette.ColorRole.Text,
        'Button': QPalette.ColorRole.Button,
        'ButtonText': QPalette.ColorRole.ButtonText,
        'BrightText': QPalette.ColorRole.BrightText,
        'Highlight': QPalette.ColorRole.Highlight,
        'HighlightedText': QPalette.ColorRole.HighlightedText,
        'PlaceholderText': QPalette.ColorRole.PlaceholderText,
        'Light': QPalette.ColorRole.Light,
        'Midlight': QPalette.ColorRole.Midlight,
        'Dark': QPalette.ColorRole.Dark,
        'Mid': QPalette.ColorRole.Mid,
        'Shadow': QPalette.ColorRole.Shadow,
        'Link': QPalette.ColorRole.Link,
        'LinkVisited': QPalette.ColorRole.LinkVisited,
    }
    for key, role in role_map.items():
        if key in theme:
            rgba = theme[key]
            color = QColor(*rgba)
            palette.setColor(role, color)
    app = QApplication.instance()
    if app is not None:
        app.setPalette(palette)  # type: ignore[attr-defined]
 
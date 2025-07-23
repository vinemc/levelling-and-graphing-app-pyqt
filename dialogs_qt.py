from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QDialogButtonBox, QComboBox, QCheckBox, QTextEdit
import os
from PyQt6.QtGui import QIcon

ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Leveling & Graphing App")
        layout = QVBoxLayout(self)
        
        message = QLabel("Leveling & Graphing App\n\nVersion: 2.0 (PyQt)\nAuthor: [Your Name]")
        layout.addWidget(message)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, self)
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button and os.path.exists(os.path.join(ICON_DIR, 'exit.svg')):
            ok_button.setIcon(QIcon(os.path.join(ICON_DIR, 'exit.svg')))
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        layout = QVBoxLayout(self)
        
        # Add settings widgets here later
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button and os.path.exists(os.path.join(ICON_DIR, 'exit.svg')):
            ok_button.setIcon(QIcon(os.path.join(ICON_DIR, 'exit.svg')))
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button and os.path.exists(os.path.join(ICON_DIR, 'exit.svg')):
            cancel_button.setIcon(QIcon(os.path.join(ICON_DIR, 'exit.svg')))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

class ImportDialog(QDialog):
    def __init__(self, file_path, column_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import CSV")
        layout = QVBoxLayout(self)
        self.import_result = None

        self.has_header_checkbox = QCheckBox("File has header row")
        self.has_header_checkbox.setChecked(True)
        layout.addWidget(self.has_header_checkbox)

        self.mapping_combos = {}
        for name in column_names:
            label = QLabel(f"'{name}' column:")
            combo = QComboBox()
            self.mapping_combos[name] = combo
            layout.addWidget(label)
            layout.addWidget(combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.do_import)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.populate_combos(file_path)
        self.setLayout(layout)

    def populate_combos(self, file_path):
        import csv
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            for name, combo in self.mapping_combos.items():
                combo.addItems(header)
                if name in header:
                    combo.setCurrentText(name)

    def do_import(self):
        self.import_result = {
            "mapping": {name: combo.currentIndex() for name, combo in self.mapping_combos.items()},
            "has_header": self.has_header_checkbox.isChecked()
        }
        self.accept()

class AppLogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("App Log")
        self.resize(800, 500)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setFontFamily("Consolas")
        self.text_edit.setFontPointSize(10)
        layout.addWidget(self.text_edit)
        log_path = os.path.join(os.path.dirname(__file__), "app.log")
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                self.text_edit.setPlainText(f.read())
        except Exception as e:
            self.text_edit.setPlainText(f"Could not read log file: {e}")
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QMenu, QGroupBox, QRadioButton, QHeaderView, QAbstractItemView, QMessageBox, QApplication, QTableWidgetSelectionRange
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer
from .settings import settings
from leveling_app_modular.calculator import LevelingCalculator
from PyQt6.QtGui import QColor, QIcon
from .utils_qt import Tooltip
import time
import os
ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")

DEFAULT_ROW_COUNT = 30

class RestoreWorker(QObject):
    progress = pyqtSignal(int, list)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, data):
        super().__init__()
        self.data = data

    def run(self):
        try:
            for row, row_data in enumerate(self.data):
                self.progress.emit(row, row_data)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class LevelingApp(QWidget):
    def __init__(self, parent=None, on_results_ready=None, settings_dialog=None, column_customizer=None):
        super().__init__(parent)
        self.on_results_ready = on_results_ready
        self.settings_dialog = settings_dialog
        self.column_customizer = column_customizer
        self.COLUMN_NAMES = ["Point", "BS", "IS", "FS"]
        self.undo_stack = []
        self.redo_stack = []
        self.dirty = False
        self.context_menu_row = -1
        self.clipboard_row = None
        self._init_ui()
        self.push_undo()  # Initial state

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # Controls
        controls_layout = QHBoxLayout()
        method_group = QGroupBox()
        method_layout = QHBoxLayout(method_group)
        self.hi_radio = QRadioButton("Height of Instrument")
        self.hi_radio.setChecked(True)
        Tooltip(self.hi_radio, "Height of Instrument method: calculates RLs by adding BS to previous RL.")
        self.rf_radio = QRadioButton("Rise & Fall")
        Tooltip(self.rf_radio, "Rise & Fall method: calculates RLs by computing rises and falls between points.")
        method_layout.addWidget(QLabel("Method:"))
        method_layout.addWidget(self.hi_radio)
        method_layout.addWidget(self.rf_radio)
        controls_layout.addWidget(method_group)

        rl_layout = QHBoxLayout()
        rl_layout.addWidget(QLabel("First RL:"))
        self.first_rl_entry = QLineEdit()
        Tooltip(self.first_rl_entry, "Enter the first Reduced Level (RL) for your survey.")
        rl_layout.addWidget(self.first_rl_entry)
        rl_layout.addWidget(QLabel("Last RL (Check):"))
        self.last_rl_entry = QLineEdit()
        Tooltip(self.last_rl_entry, "Optionally enter the last RL for arithmetic check.")
        rl_layout.addWidget(self.last_rl_entry)
        controls_layout.addLayout(rl_layout)

        action_layout = QHBoxLayout()
        self.undo_button = QPushButton(QIcon(os.path.join(ICON_DIR, 'undo.svg')), "Undo")
        Tooltip(self.undo_button, "Undo the last change (Ctrl+Z).")
        self.undo_button.setEnabled(False)
        self.undo_button.clicked.connect(self.undo)
        action_layout.addWidget(self.undo_button)
        self.redo_button = QPushButton(QIcon(os.path.join(ICON_DIR, 'redo.svg')), "Redo")
        Tooltip(self.redo_button, "Redo the last undone change (Ctrl+Y).")
        self.redo_button.setEnabled(False)
        self.redo_button.clicked.connect(self.redo)
        action_layout.addWidget(self.redo_button)
        self.calculate_button = QPushButton(QIcon(os.path.join(ICON_DIR, 'calculate.svg')), "Calculate & Update Graph")
        Tooltip(self.calculate_button, "Calculate results and update the profile graph.")
        self.calculate_button.clicked.connect(self.calculate_and_update)
        action_layout.addWidget(self.calculate_button)
        if self.settings_dialog:
            self.settings_button = QPushButton(QIcon(os.path.join(ICON_DIR, 'settings.svg')), "")
            Tooltip(self.settings_button, "Open settings dialog.")
            self.settings_button.clicked.connect(self.settings_dialog.open_settings)
            action_layout.addWidget(self.settings_button)
        self.clear_button = QPushButton(QIcon(os.path.join(ICON_DIR, 'delete.svg')), "Clear All")
        Tooltip(self.clear_button, "Clear all data and results.")
        self.clear_button.clicked.connect(self.clear_all_data)
        action_layout.addWidget(self.clear_button)
        controls_layout.addLayout(action_layout)
        main_layout.addLayout(controls_layout)

        # Progress Bar
        self.progress_bar = QProgressBar()
        Tooltip(self.progress_bar, "Shows calculation progress.")
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Data Entry Table
        self.table = QTableWidget(DEFAULT_ROW_COUNT, len(self.COLUMN_NAMES))
        Tooltip(self.table, "Enter your survey readings here. Double-click to edit cells. Right-click for options.")
        self.table.setHorizontalHeaderLabels(self.COLUMN_NAMES)
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.SelectedClicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)
        main_layout.addWidget(self.table)

        # Add row button
        self.add_row_button = QPushButton(QIcon(os.path.join(ICON_DIR, 'add_row.svg')), "+")
        Tooltip(self.add_row_button, "Add a new row to the data entry table.")
        self.add_row_button.clicked.connect(self.add_row)
        main_layout.addWidget(self.add_row_button)

        # Stats
        stats_group = QGroupBox("Survey Stats & Arithmetic Check")
        stats_layout = QVBoxLayout(stats_group)
        self.stations_label = QLabel("Number of Stations (CP): 0")
        self.bs_label = QLabel("Backsights: 0")
        self.is_label = QLabel("Intersights: 0")
        self.fs_label = QLabel("Foresights: 0")
        self.arith_label = QLabel("Arithmetic Check: -")
        self.error_label = QLabel("")
        stats_layout.addWidget(self.arith_label)
        stats_layout.addWidget(self.stations_label)
        stats_layout.addWidget(self.bs_label)
        stats_layout.addWidget(self.is_label)
        stats_layout.addWidget(self.fs_label)
        stats_layout.addWidget(self.error_label)
        main_layout.addWidget(stats_group)
        
        # Results Table
        self.results_table = QTableWidget(0, 11)
        Tooltip(self.results_table, "Calculation results. Not editable.")
        self.ALL_RESULT_COLUMNS = ["Point", "BS", "IS", "FS", "HI", "Rise", "Fall", "RL", "Adjustment", "Adjusted RL", "Design RL", "Cut", "Fill", "Elevation"]
        self.results_table.setHorizontalHeaderLabels(self.ALL_RESULT_COLUMNS)
        header2 = self.results_table.horizontalHeader()
        if header2 is not None:
            header2.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        main_layout.addWidget(self.results_table)

        # Keyboard shortcuts
        self.table.installEventFilter(self)
        self.undo_button.setShortcut('Ctrl+Z')
        self.redo_button.setShortcut('Ctrl+Y')

    def eventFilter(self, obj, event):
        if obj == self.table:
            if event.type() == event.Type.KeyPress:
                key = event.key()
                if key == Qt.Key.Key_Z and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                    self.undo()
                    return True
                elif key == Qt.Key.Key_Y and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                    self.redo()
                    return True
        return super().eventFilter(obj, event)

    def push_undo(self):
        snapshot = self.get_table_data()
        self.undo_stack.append(snapshot)
        self.redo_stack.clear()
        self.update_undo_redo_buttons()

    def undo(self):
        if len(self.undo_stack) > 1:
            self.redo_stack.append(self.undo_stack.pop())
            self.set_table_data(self.undo_stack[-1])
            self.update_undo_redo_buttons()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.redo_stack.pop())
            self.set_table_data(self.undo_stack[-1])
            self.update_undo_redo_buttons()

    def update_undo_redo_buttons(self):
        self.undo_button.setEnabled(len(self.undo_stack) > 1)
        self.redo_button.setEnabled(bool(self.redo_stack))

    def get_table_data(self):
        data = []
        for row in range(self.table.rowCount()):
            row_data = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                row_data.append(item.text() if isinstance(item, QTableWidgetItem) else "")
            data.append(row_data)
        return data

    def set_table_data(self, snapshot):
        self.table.setRowCount(len(snapshot))
        for row, row_data in enumerate(snapshot):
            for col, value in enumerate(row_data):
                self.table.setItem(row, col, QTableWidgetItem(value))

    def on_item_changed(self, item):
        if self.table.signalsBlocked():
            return
        self.table.blockSignals(True)
        try:
            self.push_undo()
            self.update_stats()
            self.validate_table()
            self.apply_row_striping()
        finally:
            self.table.blockSignals(False)

    def validate_table(self):
        error_found = False
        error_msg = ""
        # Columns that require numeric input: BS, IS, FS, RL (columns 1,2,3, and RL fields)
        numeric_cols = [1, 2, 3]
        for row in range(self.table.rowCount()):
            for col in numeric_cols:
                item = self.table.item(row, col)
                text = item.text() if item is not None else ""
                if text.strip() != "" and not self.is_number(text):
                    if item is not None:
                        item.setBackground(QColor("#ffcccc"))  # Red highlight
                    error_found = True
                    error_msg = f"Invalid number in row {row+1}, column {self.COLUMN_NAMES[col]}"
                else:
                    if item is not None:
                        # Restore normal coloring for this cell only
                        if settings["theme"] == "Dark":
                            bg = QColor("#23272e") if row % 2 == 0 else QColor("#1a1c1e")
                            fg = QColor("#f8f8f2")
                        else:
                            bg = QColor("#fff") if row % 2 == 0 else QColor("#f0f0f0")
                            fg = QColor("#222")
                        item.setBackground(bg)
                        item.setForeground(fg)
        # Validate RL fields
        for entry, label in [(self.first_rl_entry, "First RL"), (self.last_rl_entry, "Last RL")]:
            text = entry.text() if entry is not None else ""
            pal = entry.palette()
            if text.strip() != "" and not self.is_number(text):
                pal.setColor(entry.backgroundRole(), QColor("#ffcccc"))
                entry.setPalette(pal)
                error_found = True
                error_msg = f"Invalid number in {label}"
            else:
                entry.setPalette(self.palette())
        if error_found:
            if self.error_label is not None and hasattr(self.error_label, 'setText'):
                self.error_label.setText(error_msg)
        else:
            if self.error_label is not None and hasattr(self.error_label, 'setText'):
                self.error_label.setText("")

    @staticmethod
    def is_number(val: str) -> bool:
        try:
            float(val)
            return True
        except Exception:
            return False

    def on_item_double_clicked(self, item):
        # Validation can be added here if needed
        pass

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.push_undo()
        self.apply_row_striping()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.addAction(QIcon(os.path.join(ICON_DIR, 'copy.svg')), "Copy Row", self.copy_row)
        menu.addAction(QIcon(os.path.join(ICON_DIR, 'copy.svg')), "Paste Row", self.paste_row)
        menu.addSeparator()
        menu.addAction(QIcon(os.path.join(ICON_DIR, 'insert_above.svg')), "Insert Row Above", self.insert_row_above)
        menu.addAction(QIcon(os.path.join(ICON_DIR, 'insert_below.svg')), "Insert Row Below", self.insert_row_below)
        menu.addSeparator()
        menu.addAction(QIcon(os.path.join(ICON_DIR, 'delete.svg')), "Delete Row", self.delete_row)
        menu.addSeparator()
        if self.column_customizer is not None and hasattr(self.column_customizer, 'customize_columns_dialog'):
            menu.addAction(QIcon(os.path.join(ICON_DIR, 'columns.svg')), "Customize Columns...", lambda: getattr(self.column_customizer, 'customize_columns_dialog', lambda x: None)('result'))
        viewport = getattr(self.table, 'viewport', lambda: None)()
        if viewport is not None and hasattr(viewport, 'mapToGlobal'):
            menu.exec(viewport.mapToGlobal(pos))
        else:
            menu.exec(pos)

    def copy_row(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            return
        
        copied_text = ""
        for selection in selected_ranges:
            for row in range(selection.topRow(), selection.bottomRow() + 1):
                row_data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                copied_text += "\t".join(row_data) + "\n"
        QApplication.clipboard().setText(copied_text.strip())

    def paste_row(self):
        row = self.table.currentRow()
        if row < 0:
            row = 0
            
        clipboard_text = QApplication.clipboard().text()
        if not clipboard_text:
            return
            
        lines = clipboard_text.strip().split("\n")
        for i, line in enumerate(lines):
            values = line.split("\t")
            target_row = row + i
            if target_row >= self.table.rowCount():
                self.table.insertRow(target_row)
            for col, value in enumerate(values):
                if col < self.table.columnCount():
                    self.table.setItem(target_row, col, QTableWidgetItem(value))
        
        self.push_undo()
        self.apply_row_striping()
        self.validate_table()

    def insert_row_above(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.insertRow(row)
            self.push_undo()
            self.apply_row_striping()

    def insert_row_below(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.insertRow(row + 1)
            self.push_undo()
            self.apply_row_striping()

    def delete_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.push_undo()
            self.apply_row_striping()

    def clear_all_data(self):
        print("DEBUG: clear_all_data called")
        self.table.setRowCount(0)
        print("DEBUG: setRowCount(0) in clear_all_data")
        self.table.setRowCount(DEFAULT_ROW_COUNT)
        print(f"DEBUG: setRowCount({DEFAULT_ROW_COUNT}) in clear_all_data")
        self.results_table.setRowCount(0)
        self.stations_label.setText("Number of Stations (CP): 0")
        self.bs_label.setText("Backsights: 0")
        self.is_label.setText("Intersights: 0")
        self.fs_label.setText("Foresights: 0")
        self.arith_label.setText("Arithmetic Check: -")
        self.error_label.setText("")
        self.push_undo()
        self.apply_row_striping()

    def apply_row_striping(self):
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    if settings["theme"] == "Dark":
                        bg = QColor("#23272e") if row % 2 == 0 else QColor("#1a1c1e")
                        fg = QColor("#f8f8f2")
                    else:
                        bg = QColor("#fff") if row % 2 == 0 else QColor("#f0f0f0")
                        fg = QColor("#222")
                    item.setBackground(bg)
                    item.setForeground(fg)

    def update_stats(self, stats=None, *args, **kwargs):
        if stats:
            # Update from calculated stats
            if self.stations_label is not None:
                self.stations_label.setText(f"Number of Stations (CP): {stats.get('cp', 0)}")
            if self.bs_label is not None:
                self.bs_label.setText(f"Backsights: {stats.get('bs', 0)}")
            if self.is_label is not None:
                self.is_label.setText(f"Intersights: {stats.get('is', 0)}")
            if self.fs_label is not None:
                self.fs_label.setText(f"Foresights: {stats.get('fs', 0)}")
            
            method = "HI" if self.hi_radio.isChecked() else "RF"
            if method == "HI":
                check_msg = f"ΣBS-ΣFS = {stats.get('arith_check', 0):.3f}\nLastRL-FirstRL = {stats.get('rl_diff', 0):.3f}"
            else: # RF
                check_msg = f"ΣRise-ΣFall = {stats.get('arith_check', 0):.3f}\nLastRL-FirstRL = {stats.get('rl_diff', 0):.3f}"

            if stats.get('arith_failed'):
                check_msg += "\n⚠️ Arithmetic check failed!"
            else:
                check_msg += "\n✔️ Arithmetic check passed."
            if self.arith_label is not None:
                self.arith_label.setText(check_msg)
        else:
            # Update from table data (live update)
            cp = bs = is_ = fs = 0
            for row in range(self.table.rowCount()):
                vals = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    val = item.text() if item is not None else ""
                    vals.append(val)
                if any(vals):
                    cp += 1
                if len(vals) > 1 and vals[1]:
                    bs += 1
                if len(vals) > 2 and vals[2]:
                    is_ += 1
                if len(vals) > 3 and vals[3]:
                    fs += 1
            if self.stations_label is not None:
                self.stations_label.setText(f"Number of Stations (CP): {cp}")
            if self.bs_label is not None:
                self.bs_label.setText(f"Backsights: {bs}")
            if self.is_label is not None:
                self.is_label.setText(f"Intersights: {is_}")
            if self.fs_label is not None:
                self.fs_label.setText(f"Foresights: {fs}")
            if self.arith_label is not None:
                self.arith_label.setText("Arithmetic Check: -")

    def calculate_and_update(self):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        QApplication.processEvents()

        try:
            first_rl = float(self.first_rl_entry.text())
        except ValueError:
            QMessageBox.critical(self, "Input Error", "First RL must be a valid number.")
            self.progress_bar.setVisible(False)
            return

        last_rl_str = self.last_rl_entry.text().strip()
        last_rl = float(last_rl_str) if self.is_number(last_rl_str) else None

        data = self.get_table_data()
        method = "HI" if self.hi_radio.isChecked() else "RF"

        try:
            calculator = LevelingCalculator(settings)
            results, stats = calculator.calculate_leveling(method, first_rl, last_rl, data)
            
            self.results_table.setRowCount(0)
            if results:
                method = "HI" if self.hi_radio.isChecked() else "RF"
                if method == "HI":
                    headers = ["Point", "BS", "IS", "FS", "HI", "RL", "Adjustment", "Adjusted RL", "Design RL", "Cut", "Fill", "Elevation"]
                else: # RF
                    headers = ["Point", "BS", "IS", "FS", "Rise", "Fall", "RL", "Adjustment", "Adjusted RL", "Design RL", "Cut", "Fill", "Elevation"]
                
                self.results_table.setColumnCount(len(headers))
                self.results_table.setHorizontalHeaderLabels(headers)
                self.results_table.setRowCount(len(results))
                for row_idx, row_data in enumerate(results):
                    for col_idx, key in enumerate(headers):
                        self.results_table.setItem(row_idx, col_idx, QTableWidgetItem(str(row_data.get(key, ""))))

            self.error_label.setText("")
            self.update_stats(stats)

            if self.on_results_ready:
                self.on_results_ready(results)

        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"An error occurred during calculation: {e}")
        finally:
            self.progress_bar.setVisible(False)

    def get_data_for_session(self):
        return self.get_table_data()

    def set_data_from_session(self, data):
        print("DEBUG: set_data_from_session called with data length:", len(data))
        self.progress_bar.setVisible(True)
        if len(data) < 20:
            self.progress_bar.setRange(0, 0)  # Indeterminate for small/fast restores
        else:
            self.progress_bar.setRange(0, max(1, len(data)))
        self.table.setRowCount(len(data))  # Ensure table can show all rows
        print(f"DEBUG: setRowCount({len(data)}) in set_data_from_session")
        self.progress_bar.setValue(0)
        self.progress_bar.setToolTip("Restoring session data...")
        QApplication.processEvents()
        for row, row_data in enumerate(data):
            print(f"DEBUG: _restore_row row={row}, len(row_data)={len(row_data)}, expected columns={self.table.columnCount()}")
            for col, value in enumerate(row_data):
                if value is None:
                    print(f"ERROR: None value at row {row}, col {col}")
                self.table.setItem(row, col, QTableWidgetItem(str(value) if value is not None else ""))
            if len(data) >= 20:
                self.progress_bar.setValue(row + 1)
            QApplication.processEvents()
        print("DEBUG: Final table row count after restore:", self.table.rowCount())
        QTimer.singleShot(1000, lambda: print("DEBUG: Row count after 1s:", self.table.rowCount()))
        self.push_undo()
        self.update_stats()
        self.apply_row_striping()
        self.progress_bar.setVisible(False)

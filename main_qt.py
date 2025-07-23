import sys
import os
import logging
import json
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QFileDialog, QPushButton, QStatusBar, QMenuBar, QTableWidgetItem, QInputDialog, QDialog, QListWidget, QHBoxLayout, QMessageBox
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QKeySequence, QAction, QIcon
from leveling_app_modular.ui_leveling_qt import LevelingApp
from leveling_app_modular.ui_graph_qt import GraphApp
from leveling_app_modular.utils_qt import Tooltip, ImportDialog, show_onboarding, show_about, apply_theme_qt
from leveling_app_modular.import_export_qt import ImportExportManager
from leveling_app_modular.settings_qt import SettingsDialog
from leveling_app_modular.help_qt import HelpManager
from leveling_app_modular.db import DatabaseManager
from leveling_app_modular.calculator import LevelingCalculator
from .settings import settings, save_settings
from leveling_app_modular.session import SessionManager
from leveling_app_modular.dialogs_qt import AboutDialog, AppLogDialog
from PyQt6.QtCore import QTimer, Qt

ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Leveling & Graphing App (PyQt)")
        self.setGeometry(100, 100, 1400, 900)

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Apply theme at startup
        apply_theme_qt()

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._status_clear_timer = QTimer(self)
        self._status_clear_timer.setSingleShot(True)
        self._status_clear_timer.timeout.connect(lambda: self.status_bar.clearMessage())

        # Session manager
        self.session_manager = SessionManager(settings)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self.autosave)
        self._autosave_timer.setInterval(settings.get("autosave_interval", 5) * 60 * 1000)
        self._autosave_timer.start()

        # Initialize managers
        self.db_manager = DatabaseManager()
        self.import_export = ImportExportManager(self, settings, save_settings)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.leveling_app = LevelingApp()
        self.tabs.addTab(self.leveling_app, "Leveling Calculator")

        self.graph_app = GraphApp()
        self.tabs.addTab(self.graph_app, "Profile Graph")

        # Wire up the leveling app to the graph app
        self.leveling_app.on_results_ready = self.graph_app.update_from_leveling

        # Add Help tab
        self.help_manager = HelpManager(self)
        self.help_manager.init_help_tab(self.tabs)
        
        self.leveling_app.calculate_button.clicked.connect(self.calculate_and_update)

        # Ensure menu bar exists
        if not self.menuBar():
            self.setMenuBar(QMenuBar(self))
        self._create_menus()
        self._setup_shortcuts()

        # Theme toggle button (bottom right)
        self.theme_toggle_btn = QPushButton("\U0001F319")  # Moon emoji
        self.theme_toggle_btn.setToolTip("Toggle Light/Dark Theme")
        self.theme_toggle_btn.setFixedSize(36, 36)
        self.theme_toggle_btn.setStyleSheet("border-radius: 18px; font-size: 18pt;")
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)
        self.theme_toggle_btn.setParent(self)
        self.theme_toggle_btn.show()
        Tooltip(self.theme_toggle_btn, "Toggle between light and dark theme.")
        self._position_overlay_buttons()

        # Show onboarding if needed
        if not settings.get("onboarding_complete", False):
            show_onboarding(self, settings, save_settings)

    def resizeEvent(self, event):
        margin = 16
        x_theme = self.width() - self.theme_toggle_btn.width() - margin
        y_theme = self.height() - self.theme_toggle_btn.height() - margin
        self.theme_toggle_btn.move(x_theme, y_theme)
        return super().resizeEvent(event)

    def _position_overlay_buttons(self):
        margin = 16
        # Theme toggle stays bottom right
        x_theme = self.width() - self.theme_toggle_btn.width() - margin
        y_theme = self.height() - self.theme_toggle_btn.height() - margin
        self.theme_toggle_btn.move(x_theme, y_theme)

    def toggle_theme(self):
        # Toggle theme in settings and apply
        settings["theme"] = "Dark" if settings["theme"] == "Light" else "Light"
        save_settings()
        apply_theme_qt()
        # Optionally, refresh widgets if needed
        self.leveling_app.apply_row_striping()
        if hasattr(self.graph_app, '_redraw_graph'):
            self.graph_app._redraw_graph()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            # self.fullscreen_btn.setText("\u2B1B")  # ⬛ # This line was removed
        else:
            self.showFullScreen()

    def _create_menus(self):
        menubar = self.menuBar()
        if menubar is None:
            self.setMenuBar(QMenuBar(self))
            menubar = self.menuBar()
        if menubar is None:
            return  # Fail gracefully if still None
        # File Menu
        file_menu = menubar.addMenu("&File")
        if file_menu is not None:
            restore_session_action = QAction(QIcon(os.path.join(ICON_DIR, 'restore.svg')), "Restore Session", self)
            restore_session_action.setToolTip("Restore your last session.")
            restore_session_action.triggered.connect(self.offer_session_restore)
            file_menu.addAction(restore_session_action)
            open_leveling_csv_action = QAction(QIcon(os.path.join(ICON_DIR, 'open.svg')), "Open Leveling CSV...", self)
            open_leveling_csv_action.setToolTip("Open a CSV file with leveling data.")
            open_leveling_csv_action.triggered.connect(self.open_leveling_csv)
            file_menu.addAction(open_leveling_csv_action)
            # Comparison profile
            open_comparison_action = QAction(QIcon(os.path.join(ICON_DIR, 'compare.svg')), "Open Comparison Profile...", self)
            open_comparison_action.setToolTip("Load a CSV to overlay a comparison profile on the graph.")
            open_comparison_action.triggered.connect(self.open_comparison_profile)
            file_menu.addAction(open_comparison_action)
            # Export to PDF
            export_pdf_action = QAction(QIcon(os.path.join(ICON_DIR, 'pdf_export.svg')), "Export to PDF...", self)
            export_pdf_action.setToolTip("Export results and graph to a PDF report.")
            export_pdf_action.triggered.connect(self.export_to_pdf)
            file_menu.addAction(export_pdf_action)
            # Settings action
            settings_action = QAction(QIcon(os.path.join(ICON_DIR, 'settings.svg')), "Settings...", self)
            settings_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
            settings_action.setToolTip("Open settings dialog.")
            settings_action.triggered.connect(self.show_settings_dialog)
            file_menu.addAction(settings_action)
            # Recent Files submenu
            self.recent_files_menu = file_menu.addMenu(QIcon(os.path.join(ICON_DIR, 'recent.svg')), "Recent Files")
            self._rebuild_recent_files_menu()
            file_menu.addSeparator()
            exit_action = QAction(QIcon(os.path.join(ICON_DIR, 'exit.svg')) if os.path.exists(os.path.join(ICON_DIR, 'exit.svg')) else QIcon(), "Exit", self)
            exit_action.setToolTip("Exit the application.")
            exit_action.triggered.connect(self.close)
            file_menu.addAction(exit_action)
        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")
        if edit_menu is not None:
            # Undo
            undo_action = QAction(QIcon(os.path.join(ICON_DIR, 'undo.svg')) if os.path.exists(os.path.join(ICON_DIR, 'undo.svg')) else QIcon(), "Undo", self)
            undo_action.setShortcut(QKeySequence.StandardKey.Undo)
            if hasattr(self.leveling_app, 'undo'):
                undo_action.triggered.connect(self.leveling_app.undo)
            edit_menu.addAction(undo_action)
            # Redo
            redo_action = QAction(QIcon(os.path.join(ICON_DIR, 'redo.svg')) if os.path.exists(os.path.join(ICON_DIR, 'redo.svg')) else QIcon(), "Redo", self)
            redo_action.setShortcut(QKeySequence.StandardKey.Redo)
            if hasattr(self.leveling_app, 'redo'):
                redo_action.triggered.connect(self.leveling_app.redo)
            edit_menu.addAction(redo_action)
            edit_menu.addSeparator()
            # Cut
            cut_action = QAction(QIcon(os.path.join(ICON_DIR, 'cut.svg')) if os.path.exists(os.path.join(ICON_DIR, 'cut.svg')) else QIcon(), "Cut", self)
            cut_action.setShortcut(QKeySequence.StandardKey.Cut)
            cut_action.triggered.connect(lambda: self.leveling_app.table.cut())
            edit_menu.addAction(cut_action)
            # Copy
            copy_action = QAction(QIcon(os.path.join(ICON_DIR, 'copy.svg')) if os.path.exists(os.path.join(ICON_DIR, 'copy.svg')) else QIcon(), "Copy", self)
            copy_action.setShortcut(QKeySequence.StandardKey.Copy)
            copy_action.triggered.connect(lambda: self.leveling_app.table.copy())
            edit_menu.addAction(copy_action)
            # Paste
            paste_action = QAction(QIcon(os.path.join(ICON_DIR, 'paste.svg')) if os.path.exists(os.path.join(ICON_DIR, 'paste.svg')) else QIcon(), "Paste", self)
            paste_action.setShortcut(QKeySequence.StandardKey.Paste)
            paste_action.triggered.connect(lambda: self.leveling_app.table.paste())
            edit_menu.addAction(paste_action)
            # Delete
            delete_action = QAction(QIcon(os.path.join(ICON_DIR, 'delete.svg')) if os.path.exists(os.path.join(ICON_DIR, 'delete.svg')) else QIcon(), "Delete", self)
            delete_action.setShortcut(QKeySequence.StandardKey.Delete)
            delete_action.triggered.connect(lambda: self.leveling_app.table.clear())
            edit_menu.addAction(delete_action)
            edit_menu.addSeparator()
            # Select All
            select_all_action = QAction("Select All", self)
            select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
            select_all_action.triggered.connect(lambda: self.leveling_app.table.selectAll())
            edit_menu.addAction(select_all_action)
        # View Menu
        view_menu = menubar.addMenu("&View")
        if view_menu is not None:
            app_log_action = QAction(QIcon(os.path.join(ICON_DIR, 'log.svg')) if os.path.exists(os.path.join(ICON_DIR, 'log.svg')) else QIcon(), "App Log", self)
            app_log_action.setToolTip("Show application log window.")
            app_log_action.triggered.connect(self.show_app_log_window)
            view_menu.addAction(app_log_action)
            # Save Theme (advanced)
            save_theme_action = QAction(QIcon(os.path.join(ICON_DIR, 'save.svg')), "Save Theme As...", self)
            save_theme_action.setToolTip("Save the current theme as a new theme file.")
            def save_theme():
                from pathlib import Path
                theme_dir = os.path.join(os.path.dirname(__file__), 'themes')
                os.makedirs(theme_dir, exist_ok=True)
                name, ok = QInputDialog.getText(self, "Save Theme", "Enter theme name:")
                if ok and name.strip():
                    theme_path = os.path.join(theme_dir, f"{name.strip()}.json")
                    theme_data = {k: v for k, v in settings.items() if k in ["theme", "graph_line_color", "graph_marker_color", "comparison_line_color", "label_color", "grade_slope_label_color"]}
                    try:
                        with open(theme_path, 'w') as f:
                            json.dump(theme_data, f, indent=2)
                        QMessageBox.information(self, "Theme Saved", f"Theme '{name.strip()}' saved.")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to save theme: {e}")
            save_theme_action.triggered.connect(save_theme)
            view_menu.addAction(save_theme_action)
            # Restore Theme (advanced)
            restore_theme_action = QAction(QIcon(os.path.join(ICON_DIR, 'restore.svg')), "Restore Theme...", self)
            restore_theme_action.setToolTip("Restore a theme from saved themes.")
            def restore_theme():
                from pathlib import Path
                theme_dir = os.path.join(os.path.dirname(__file__), 'themes')
                os.makedirs(theme_dir, exist_ok=True)
                themes = [f for f in os.listdir(theme_dir) if f.endswith('.json')]
                if not themes:
                    QMessageBox.information(self, "No Themes", "No saved themes found.")
                    return
                dlg = QDialog(self)
                dlg.setWindowTitle("Restore Theme")
                layout = QVBoxLayout(dlg)
                list_widget = QListWidget()
                list_widget.addItems([os.path.splitext(f)[0] for f in themes])
                layout.addWidget(list_widget)
                btn_box = QHBoxLayout()
                restore_btn = QPushButton(QIcon(os.path.join(ICON_DIR, 'restore.svg')), "Restore")
                rename_btn = QPushButton(QIcon(os.path.join(ICON_DIR, 'draft_24dp_E3E3E3_FILL0_wght100_GRAD-25_opsz24.svg')), "Rename")
                btn_box.addWidget(restore_btn)
                btn_box.addWidget(rename_btn)
                layout.addLayout(btn_box)
                def do_restore():
                    sel = list_widget.currentItem()
                    if not sel:
                        QMessageBox.warning(dlg, "No Selection", "Please select a theme to restore.")
                        return
                    theme_file = os.path.join(theme_dir, sel.text() + '.json')
                    try:
                        with open(theme_file, 'r') as f:
                            theme_data = json.load(f)
                        settings.update(theme_data)
                        save_settings()
                        apply_theme_qt()
                        self.leveling_app.apply_row_striping()
                        if hasattr(self.graph_app, '_redraw_graph'):
                            self.graph_app._redraw_graph()
                        QMessageBox.information(dlg, "Theme Restored", f"Theme '{sel.text()}' applied.")
                        dlg.accept()
                    except Exception as e:
                        QMessageBox.critical(dlg, "Error", f"Failed to restore theme: {e}")
                def do_rename():
                    sel = list_widget.currentItem()
                    if not sel:
                        QMessageBox.warning(dlg, "No Selection", "Please select a theme to rename.")
                        return
                    old_name = sel.text()
                    new_name, ok = QInputDialog.getText(dlg, "Rename Theme", f"Rename theme '{old_name}' to:", text=old_name)
                    if ok and new_name.strip() and new_name.strip() != old_name:
                        old_path = os.path.join(theme_dir, old_name + '.json')
                        new_path = os.path.join(theme_dir, new_name.strip() + '.json')
                        try:
                            os.rename(old_path, new_path)
                            list_widget.clear()
                            themes = [f for f in os.listdir(theme_dir) if f.endswith('.json')]
                            list_widget.addItems([os.path.splitext(f)[0] for f in themes])
                            QMessageBox.information(dlg, "Renamed", f"Theme renamed to '{new_name.strip()}'.")
                        except Exception as e:
                            QMessageBox.critical(dlg, "Error", f"Failed to rename theme: {e}")
                restore_btn.clicked.connect(do_restore)
                rename_btn.clicked.connect(do_rename)
                dlg.exec()
            restore_theme_action.triggered.connect(restore_theme)
            view_menu.addAction(restore_theme_action)
            restore_default_theme_action = QAction(QIcon(os.path.join(ICON_DIR, 'restore_theme.svg')) if os.path.exists(os.path.join(ICON_DIR, 'restore_theme.svg')) else QIcon(), "Restore Default Theme", self)
            restore_default_theme_action.setToolTip("Restore the default (current) theme.")
            def restore_default_theme():
                # Reset theme-related settings to their current (default) values
                default_theme = {
                    "theme": settings.get("theme", "Light"),
                    "graph_line_color": settings.get("graph_line_color", "royalblue"),
                    "graph_marker_color": settings.get("graph_marker_color", "orange"),
                    "comparison_line_color": settings.get("comparison_line_color", "green"),
                    "label_color": settings.get("label_color", "darkred"),
                    "grade_slope_label_color": settings.get("grade_slope_label_color", "blue")
                }
                settings.update(default_theme)
                save_settings()
                apply_theme_qt()
                self.leveling_app.apply_row_striping()
                if hasattr(self.graph_app, '_redraw_graph'):
                    self.graph_app._redraw_graph()
                QMessageBox.information(self, "Theme Restored", "Default theme has been restored.")
            restore_default_theme_action.triggered.connect(restore_default_theme)
            view_menu.addAction(restore_default_theme_action)
        # Help Menu
        help_menu = menubar.addMenu("&Help")
        if help_menu is not None:
            about_action = QAction(QIcon(os.path.join(ICON_DIR, 'help.svg')) if os.path.exists(os.path.join(ICON_DIR, 'help.svg')) else QIcon(), "About", self)
            about_action.setToolTip("About this application.")
            about_action.triggered.connect(self.show_about_dialog)
            help_menu.addAction(about_action)
            # Add Help/Guide action with icon
            help_action = QAction(QIcon(os.path.join(ICON_DIR, 'help.svg')) if os.path.exists(os.path.join(ICON_DIR, 'help.svg')) else QIcon(), "Help / Guide", self)
            help_action.setToolTip("Open the help and user guide tab.")
            help_action.triggered.connect(lambda: self.tabs.setCurrentIndex(self.tabs.count() - 1))
            help_menu.addAction(help_action)

    def _rebuild_recent_files_menu(self):
        if not hasattr(self, 'recent_files_menu') or self.recent_files_menu is None:
            return
        self.recent_files_menu.clear()
        recent_files = settings.get("recent_files", [])
        if not recent_files:
            action = QAction("(No recent files)", self)
            action.setEnabled(False)
            self.recent_files_menu.addAction(action)
        else:
            for path in recent_files:
                action = QAction(path, self)
                action.triggered.connect(lambda checked, p=path: self._open_recent_file(p))
                self.recent_files_menu.addAction(action)

    def _add_to_recent_files(self, file_path):
        recent_files = settings.get("recent_files", [])
        if file_path in recent_files:
            recent_files.remove(file_path)
        recent_files.insert(0, file_path)
        recent_files = recent_files[:10]  # Limit to 10
        settings["recent_files"] = recent_files
        save_settings()
        self._rebuild_recent_files_menu()

    def _open_recent_file(self, file_path):
        # Try to open as Leveling CSV, fallback to Profile CSV
        if file_path.lower().endswith('.csv'):
            try:
                column_names = []
                for i in range(self.leveling_app.table.columnCount()):
                    header_item = self.leveling_app.table.horizontalHeaderItem(i)
                    col_name = header_item.text() if header_item is not None else ""
                    column_names.append(col_name)
                self.import_export.import_leveling_csv(self.leveling_app.table, column_names, None, None, file_path)
                self.set_status(f"Opened: {file_path}")
            except Exception:
                # Try as profile CSV
                try:
                    column_names = []
                    for i in range(self.graph_app.table.columnCount()):
                        header_item = self.graph_app.table.horizontalHeaderItem(i)
                        col_name = header_item.text() if header_item is not None else ""
                        column_names.append(col_name)
                    if hasattr(self.import_export, 'import_profile_csv'):
                        self.import_export.import_profile_csv(self.graph_app.table, column_names, self.graph_app._redraw_graph, None, file_path=file_path)
                        self.set_status(f"Opened as profile: {file_path}")
                except Exception as e:
                    self.set_status(f"Failed to open: {file_path}", error=True)
        elif file_path.lower().endswith('.db'):
            from PyQt6.QtWidgets import QMessageBox
            resp = QMessageBox.question(self, "Open DB", f"Open '{file_path}' as Leveling DB? (No = Profile DB)", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            try:
                if resp == QMessageBox.StandardButton.Yes:
                    # Load as Leveling DB
                    rows = self.db_manager.load_leveling_data(file_path)
                    if rows:
                        self.leveling_app.table.setRowCount(len(rows))
                        self.leveling_app.table.setColumnCount(4)
                        self.leveling_app.table.setHorizontalHeaderLabels(["Point", "BS", "IS", "FS"])
                        for row_idx, row_data in enumerate(rows):
                            for col_idx, value in enumerate(row_data):
                                self.leveling_app.table.setItem(row_idx, col_idx, QTableWidgetItem(str(value) if value is not None else ""))
                        self.leveling_app.push_undo()
                        self.leveling_app.apply_row_striping()
                        self.set_status(f"Loaded Leveling DB: {file_path}")
                    else:
                        self.set_status(f"No data found in Leveling DB: {file_path}", error=True)
                else:
                    # Load as Profile DB
                    rows = self.db_manager.load_profile_data(file_path)
                    if rows:
                        self.graph_app.table.setRowCount(len(rows))
                        self.graph_app.table.setColumnCount(3)
                        self.graph_app.table.setHorizontalHeaderLabels(["Point", "Elevation", "Distance"])
                        for row_idx, row_data in enumerate(rows):
                            for col_idx, value in enumerate(row_data):
                                self.graph_app.table.setItem(row_idx, col_idx, QTableWidgetItem(str(value) if value is not None else ""))
                        self.graph_app.sync_data_from_table()
                        if hasattr(self.graph_app, '_redraw_graph'):
                            self.graph_app._redraw_graph()
                        self.set_status(f"Loaded Profile DB: {file_path}")
                    else:
                        self.set_status(f"No data found in Profile DB: {file_path}", error=True)
            except Exception as e:
                self.set_status(f"Failed to open DB: {e}", error=True)
        else:
            self.set_status(f"Unsupported file type: {file_path}", error=True)

    def show_about_dialog(self):
        show_about(self)

    def open_leveling_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Leveling CSV", "", "CSV Files (*.csv)")
        if file_path:
            column_names = []
            for i in range(self.leveling_app.table.columnCount()):
                header_item = self.leveling_app.table.horizontalHeaderItem(i)
                col_name = header_item.text() if header_item is not None else ""
                column_names.append(col_name)
            self.import_export.import_leveling_csv(self.leveling_app.table, column_names, None, None, file_path)
            self._add_to_recent_files(file_path)

    def open_comparison_profile(self):
        if hasattr(self.graph_app, 'load_comparison_profile'):
            self.graph_app.load_comparison_profile()

    def calculate_and_update(self):
        # Call the leveling app's calculation method
        self.leveling_app.calculate_and_update()

    def set_status(self, msg, error=False, timeout=4000):
        self.status_bar.showMessage(msg)
        if error:
            self.status_bar.setStyleSheet("color: red;")
        else:
            self.status_bar.setStyleSheet("")
        if msg:
            self._status_clear_timer.start(timeout)

    def offer_session_restore(self):
        logging.debug("offer_session_restore called")
        print("DEBUG: offer_session_restore called")
        session = self.session_manager.load_session()
        if session:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(self, "Restore Session", "A previous session was found. Restore it?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                logging.debug("User selected YES to restore session")
                print("DEBUG: User selected YES to restore session")
                self.restore_session_data(session)
                self.set_status("Session restored.")
            else:
                logging.debug("User selected NO to restore session")
                print("DEBUG: User selected NO to restore session")

    def restore_session_data(self, session):
        logging.debug("Starting restore_session_data")
        print("DEBUG: restore_session_data called with session:", session)
        if hasattr(self.leveling_app, 'set_data_from_session'):
            self.leveling_app.set_data_from_session(session.get("data", []))
        # Optionally restore settings (except theme)
        for k, v in session.get("settings", {}).items():
            if k != "theme":
                settings[k] = v
        save_settings()
        apply_theme_qt()
        self.leveling_app.apply_row_striping()
        # Removed graph redraw during restore

    def save_session(self):
        # Assumes LevelingApp has get_data_for_session
        if hasattr(self.leveling_app, 'get_data_for_session'):
            data = self.leveling_app.get_data_for_session()
        else:
            data = []
        self.session_manager.save_session(data)
        self.set_status("Session saved.")

    def autosave(self):
        self.save_session()
        self.set_status("Autosaved.")

    def closeEvent(self, event):
        self.save_session()
        event.accept()

    def dragEnterEvent(self, event: QDragEnterEvent):
        mime = event.mimeData()
        if mime is not None and mime.hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        mime = event.mimeData()
        files = [u.toLocalFile() for u in mime.urls()] if mime is not None and mime.hasUrls() else []
        for file_path in files:
            if file_path.lower().endswith('.csv'):
                from PyQt6.QtWidgets import QMessageBox
                resp = QMessageBox.question(self, "Import CSV", f"Import '{file_path}' as Leveling CSV? (No = Profile CSV)", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if resp == QMessageBox.StandardButton.Yes:
                    column_names = []
                    for i in range(self.leveling_app.table.columnCount()):
                        header_item = self.leveling_app.table.horizontalHeaderItem(i)
                        col_name = header_item.text() if header_item is not None else ""
                        column_names.append(col_name)
                    self.import_export.import_leveling_csv(self.leveling_app.table, column_names, self.leveling_app.apply_row_striping, getattr(self.leveling_app, 'progress_bar', None), file_path=file_path)
                    self.set_status(f"Imported Leveling CSV: {file_path}")
                else:
                    column_names = []
                    for i in range(self.graph_app.table.columnCount()):
                        header_item = self.graph_app.table.horizontalHeaderItem(i)
                        col_name = header_item.text() if header_item is not None else ""
                        column_names.append(col_name)
                    if hasattr(self.import_export, 'import_profile_csv'):
                        self.import_export.import_profile_csv(self.graph_app.table, column_names, self.graph_app._redraw_graph, None, file_path=file_path)
                    self.set_status(f"Imported Profile CSV: {file_path}")
            elif file_path.lower().endswith('.db'):
                from PyQt6.QtWidgets import QMessageBox
                resp = QMessageBox.question(self, "Open DB", f"Open '{file_path}' as Leveling DB? (No = Profile DB)", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if resp == QMessageBox.StandardButton.Yes:
                    self.set_status(f"Loaded Leveling DB: {file_path}")
                    # TODO: implement loading Leveling DB
                else:
                    self.set_status(f"Loaded Profile DB: {file_path}")
                    # TODO: implement loading Profile DB
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Unsupported File", f"Only CSV and DB files can be imported by drag-and-drop. Ignored: {file_path}")
                self.set_status(f"Ignored: {file_path}")

    def show_app_log_window(self):
        dialog = AppLogDialog(self)
        dialog.exec()

    def show_settings_dialog(self):
        dlg = SettingsDialog(self, apply_theme_qt, getattr(self.graph_app, '_redraw_graph', lambda: None))
        dlg.exec()

    def _setup_shortcuts(self):
        # Undo
        undo_shortcut = QAction(self)
        undo_shortcut.setShortcut(QKeySequence("Ctrl+Z"))
        undo_shortcut.triggered.connect(self.leveling_app.undo)
        self.addAction(undo_shortcut)
        # Redo
        redo_shortcut = QAction(self)
        redo_shortcut.setShortcut(QKeySequence("Ctrl+Y"))
        redo_shortcut.triggered.connect(self.leveling_app.redo)
        self.addAction(redo_shortcut)
        # Open (Leveling CSV)
        open_shortcut = QAction(self)
        open_shortcut.setShortcut(QKeySequence("Ctrl+O"))
        open_shortcut.triggered.connect(self.open_leveling_csv)
        self.addAction(open_shortcut)
        # Save/Export (Leveling CSV)
        save_shortcut = QAction(self)
        save_shortcut.setShortcut(QKeySequence("Ctrl+S"))
        save_shortcut.triggered.connect(lambda: self.import_export.export_leveling_csv(self.leveling_app.results_table, getattr(self.leveling_app, 'progress_bar', None)))
        self.addAction(save_shortcut)
        # Save to DB (Leveling)
        db_shortcut = QAction(self)
        db_shortcut.setShortcut(QKeySequence("Ctrl+D"))
        db_shortcut.triggered.connect(self.save_leveling_to_db)
        self.addAction(db_shortcut)
        # Settings dialog
        settings_shortcut = QAction(self)
        settings_shortcut.setShortcut(QKeySequence("Ctrl+Shift+S"))
        settings_shortcut.triggered.connect(self.show_settings_dialog)
        self.addAction(settings_shortcut)
        # Fullscreen (F11)
        fullscreen_shortcut = QAction(self)
        fullscreen_shortcut.setShortcut(QKeySequence("F11"))
        fullscreen_shortcut.triggered.connect(self.toggle_fullscreen)
        self.addAction(fullscreen_shortcut)
        # Exit Fullscreen (Esc)
        esc_shortcut = QAction(self)
        esc_shortcut.setShortcut(QKeySequence("Esc"))
        esc_shortcut.triggered.connect(lambda: self.showNormal() if self.isFullScreen() else None)
        self.addAction(esc_shortcut)

    def save_leveling_to_db(self):
        # Save leveling data to database
        if hasattr(self.leveling_app, 'get_table_data'):
            data = self.leveling_app.get_table_data()
            self.db_manager.save_leveling_data(data)
            self.set_status("Leveling data saved to database.")

    def export_to_pdf(self):
        self.import_export.export_pdf_with_options(self.leveling_app.results_table, self.graph_app.fig)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())

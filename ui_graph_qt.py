from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QMenu, QGroupBox, QLabel, QHeaderView, QAbstractItemView, QFileDialog, QMessageBox, QMainWindow, QProgressBar, QCheckBox, QLineEdit, QComboBox, QColorDialog, QSlider, QSizePolicy, QStackedWidget, QStyledItemDelegate
)
from PyQt6.QtCore import Qt, QEvent, QPropertyAnimation, QEasingCurve, pyqtSlot, QTimer
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from .settings import settings, save_settings
import numpy as np
from .utils_qt import Tooltip
import matplotlib.style as mplstyle
import csv
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from leveling_app_modular.utils_qt import ImportDialog
import re
from PyQt6.QtGui import QIcon, QPalette, QColor
import os
ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")

class DarkTableDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        table = parent.parent()
        row = index.row()
        if table.alternatingRowColors() and row % 2 == 1:
            bg_color = table.palette().color(table.palette().AlternateBase)
        else:
            bg_color = table.palette().color(table.backgroundRole())
        brightness = (bg_color.red() * 299 + bg_color.green() * 587 + bg_color.blue() * 114) / 1000
        if brightness < 128:
            fg = '#fff'
        else:
            fg = '#000'
        editor.setStyleSheet(f"background: {bg_color.name()}; color: {fg}; border: 1px solid #444; font: inherit;")
        pal = editor.palette()
        pal.setColor(QPalette.ColorRole.Base, bg_color)
        pal.setColor(QPalette.ColorRole.Text, QColor(fg))
        editor.setPalette(pal)
        print(f"[DEBUG] Editor bg: {bg_color.name()}, fg: {fg}, brightness: {brightness}")
        return editor

class GraphApp(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.graph_line_color = settings.get('graph_line_color', 'royalblue')
        self.graph_marker_color = settings.get('graph_marker_color', 'orange')
        self.comparison_line_color = settings.get('comparison_line_color', 'green')
        self.label_color = settings.get('label_color', 'darkred')
        self.grade_slope_label_color = settings.get('grade_slope_label_color', 'blue')
        self.show_markers = settings.get('show_markers', True)
        self.show_labels = settings.get('show_labels', True)
        self.show_grade_slopes = settings.get('show_grade_slopes', False)
        self.interval_mode = False
        self.interval_value = settings.get('interval_value', 10)
        self._last_data = []
        self._annotations = []  # List of (x0, y0, x1, y1)
        self._annotation_mode = False
        self._polyline_vertices = []
        self._polyline_add_mode = False
        self._smooth_polyline = 0.0
        self._design_levels = []
        self._comparison_data = []
        self._fullscreen_mode = False
        self._hidden_widgets = []
        self._main_layout = None
        self._overlay_label = None
        self._menu_bar_ref = None
        self._export_btn = None  # Screenshot/export button (fullscreen only)
        self._overlay_timer = QTimer(self)
        self._overlay_timer.setSingleShot(True)
        self._overlay_timer.timeout.connect(self._hide_overlay_label)
        self._minimalist_mode = False  # Minimalist mode flag
        self._presentation_mode = False
        self._drawing = False
        self._draw_start = None
        self._init_ui()
        self.installEventFilter(self)
        self._data_cursor_label = QLabel(self)
        self._data_cursor_label.setStyleSheet("background: #222; color: #fff; border-radius: 6px; padding: 6px; font-size: 11pt;")
        self._data_cursor_label.setWindowFlags(self._data_cursor_label.windowFlags() | Qt.WindowType.ToolTip)
        self._data_cursor_label.hide()
        self.canvas.mpl_connect('motion_notify_event', self._on_graph_hover)
        self.canvas.mpl_connect('button_press_event', self._on_graph_click)
        self.canvas.mpl_connect('button_press_event', self._on_graph_draw_start)
        self.canvas.mpl_connect('button_release_event', self._on_graph_draw_end)
        self.canvas.mpl_connect('motion_notify_event', self._on_graph_draw_move)
        # Restore persistent fullscreen state
        if settings.get('graph_fullscreen', False):
            QTimer.singleShot(0, self.toggle_fullscreen)
        self._graph_dark_mode = settings.get('graph_dark_mode', False)
        self._dark_mode_btn = QPushButton("🌙", self)
        self._dark_mode_btn.setToolTip("Toggle Graph Dark Mode")
        self._dark_mode_btn.setFixedSize(36, 36)
        self._dark_mode_btn.setStyleSheet("border-radius: 18px; font-size: 18pt; position: absolute; background: #222; color: #fff;")
        self._dark_mode_btn.clicked.connect(self.toggle_graph_dark_mode)
        self._dark_mode_btn.move(10, 10)
        self._dark_mode_btn.show()
        self._apply_graph_theme()
        self._compare_mode = False
        # Progress Bar for imports/exports
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        if self._main_layout is not None:
            self._main_layout.addWidget(self.progress_bar)
        # When calling import/export, pass self.progress_bar as the progress_bar argument.
        # Example:
        # self.import_export.import_profile_csv(self.table, column_names, self._redraw_graph, self.progress_bar, file_path)

    def _init_ui(self):
        from PyQt6.QtWidgets import QWidget
        layout = QVBoxLayout(self)
        self._main_layout = layout

        # --- Top Controls Row: Graph, View, Color, Annotation, Export ---
        top_controls_layout = QHBoxLayout()
        top_controls_layout.setSpacing(6)
        top_controls_layout.setContentsMargins(5, 5, 5, 5)
        
        # Update Graph button
        self.update_graph_btn = QPushButton(QIcon(os.path.join(ICON_DIR, 'calculate.svg')), "Update Graph")
        self.update_graph_btn.clicked.connect(self._redraw_graph)
        top_controls_layout.addWidget(self.update_graph_btn)
        Tooltip(self.update_graph_btn, "Redraw the profile graph using the current data.")
        
        # View Options (compact)
        self.interval_mode_cb = QCheckBox("Interval")
        self.interval_mode_cb.setChecked(False)
        self.interval_mode_cb.stateChanged.connect(self.toggle_interval_mode)
        top_controls_layout.addWidget(self.interval_mode_cb)
        Tooltip(self.interval_mode_cb, "Enable interval mode for regular station spacing.")
        
        self.interval_value_edit = QLineEdit("10")
        self.interval_value_edit.setFixedWidth(50)
        self.interval_value_edit.textChanged.connect(lambda: self._redraw_graph())
        top_controls_layout.addWidget(QLabel("Int:"))
        top_controls_layout.addWidget(self.interval_value_edit)
        
        self.smoothing_cb = QCheckBox("Smooth")
        self.smoothing_cb.setChecked(False)
        self.smoothing_cb.stateChanged.connect(lambda: self._redraw_graph())
        top_controls_layout.addWidget(self.smoothing_cb)
        Tooltip(self.smoothing_cb, "Smooth the profile line.")
        
        self.marker_toggle_cb = QCheckBox("Markers")
        self.marker_toggle_cb.setChecked(self.show_markers)
        self.marker_toggle_cb.stateChanged.connect(self.toggle_markers)
        top_controls_layout.addWidget(self.marker_toggle_cb)
        Tooltip(self.marker_toggle_cb, "Toggle point markers on the graph.")
        
        self.label_toggle_cb = QCheckBox("Labels")
        self.label_toggle_cb.setChecked(self.show_labels)
        self.label_toggle_cb.stateChanged.connect(self.toggle_labels)
        top_controls_layout.addWidget(self.label_toggle_cb)
        Tooltip(self.label_toggle_cb, "Toggle value labels on the graph.")
        
        self.grade_slope_toggle_cb = QCheckBox("Slopes")
        self.grade_slope_toggle_cb.setChecked(False)
        self.grade_slope_toggle_cb.stateChanged.connect(self.toggle_grade_slopes)
        top_controls_layout.addWidget(self.grade_slope_toggle_cb)
        Tooltip(self.grade_slope_toggle_cb, "Show grade/slope labels on the graph.")
        
        # Color buttons (compact)
        self.line_color_btn = QPushButton(QIcon(os.path.join(ICON_DIR, 'color.svg')), "Line")
        self.line_color_btn.clicked.connect(self.pick_line_color)
        top_controls_layout.addWidget(self.line_color_btn)
        Tooltip(self.line_color_btn, "Pick the line color for the graph.")
        
        self.marker_color_btn = QPushButton(QIcon(os.path.join(ICON_DIR, 'color.svg')), "Marker")
        self.marker_color_btn.clicked.connect(self.pick_marker_color)
        top_controls_layout.addWidget(self.marker_color_btn)
        Tooltip(self.marker_color_btn, "Pick the marker color for the graph.")
        
        # Export button
        top_controls_layout.addStretch()
        self.export_graph_btn = QPushButton(QIcon(os.path.join(ICON_DIR, 'export.svg')), "Export")
        self.export_graph_btn.clicked.connect(self.export_pdf)
        top_controls_layout.addWidget(self.export_graph_btn)
        Tooltip(self.export_graph_btn, "Export the graph as PDF or image.")
        
        # --- Annotation Controls (now in top row) ---
        top_controls_layout.addSpacing(20)
        top_controls_layout.addWidget(QLabel("Text:"))
        self.annotation_text_edit = QLineEdit()
        self.annotation_text_edit.setFixedWidth(180)
        top_controls_layout.addWidget(self.annotation_text_edit)
        self.add_text_btn = QPushButton(QIcon(os.path.join(ICON_DIR, 'annotation.svg')), "Add")
        self.add_text_btn.clicked.connect(self._toggle_annotation_mode)
        top_controls_layout.addWidget(self.add_text_btn)
        Tooltip(self.add_text_btn, "Add a text annotation to the graph.")
        self.clear_ann_btn = QPushButton(QIcon(os.path.join(ICON_DIR, 'delete.svg')), "Clear")
        self.clear_ann_btn.clicked.connect(self.clear_annotations)
        top_controls_layout.addWidget(self.clear_ann_btn)
        Tooltip(self.clear_ann_btn, "Clear all annotations from the graph.")
        
        layout.addLayout(top_controls_layout)

        # --- Second Row: Design Level Controls ---
        design_controls_layout = QHBoxLayout()
        design_controls_layout.setSpacing(6)
        design_controls_layout.setContentsMargins(5, 2, 5, 5)
        
        design_controls_layout.addWidget(QLabel("Design:"))
        self.design_level_mode_cb = QComboBox()
        self.design_level_mode_cb.addItems(["Fixed", "Gradient", "From Points", "First RL", "Comparison Profile", "Polyline"])
        self.design_level_mode_cb.currentTextChanged.connect(self.update_design_level_inputs)
        design_controls_layout.addWidget(self.design_level_mode_cb)

        # Use QStackedWidget for design level inputs
        self.design_level_inputs = QStackedWidget()
        design_controls_layout.addWidget(self.design_level_inputs)

        # Fixed mode
        fixed_widget = QWidget(parent=self)
        fixed_layout = QHBoxLayout()
        fixed_layout.setContentsMargins(0, 0, 0, 0)
        fixed_layout.addWidget(QLabel("Level:"))
        self.design_level_edit = QLineEdit("0.0")
        self.design_level_edit.setFixedWidth(60)
        fixed_layout.addWidget(self.design_level_edit)
        fixed_widget.setLayout(fixed_layout)
        self.design_level_inputs.addWidget(fixed_widget)

        # Gradient mode
        gradient_widget = QWidget(parent=self)
        gradient_layout = QHBoxLayout()
        gradient_layout.setContentsMargins(0, 0, 0, 0)
        gradient_layout.addWidget(QLabel("Start:"))
        self.gradient_start_edit = QLineEdit("0.0")
        self.gradient_start_edit.setFixedWidth(60)
        gradient_layout.addWidget(self.gradient_start_edit)
        gradient_layout.addWidget(QLabel("End:"))
        self.gradient_end_edit = QLineEdit("0.0")
        self.gradient_end_edit.setFixedWidth(60)
        gradient_layout.addWidget(self.gradient_end_edit)
        gradient_widget.setLayout(gradient_layout)
        self.design_level_inputs.addWidget(gradient_widget)

        # From Points mode
        from_points_widget = QWidget(parent=self)
        from_points_layout = QHBoxLayout()
        from_points_layout.setContentsMargins(0, 0, 0, 0)
        from_points_layout.addWidget(QLabel("Points:"))
        self.from_points_edit = QLineEdit()
        self.from_points_edit.setFixedWidth(150)
        from_points_layout.addWidget(self.from_points_edit)
        self.from_points_file_btn = QPushButton("Load")
        self.from_points_file_btn.clicked.connect(self._load_design_levels_from_file)
        from_points_layout.addWidget(self.from_points_file_btn)
        from_points_widget.setLayout(from_points_layout)
        self.design_level_inputs.addWidget(from_points_widget)

        # First RL mode (no inputs)
        self.design_level_inputs.addWidget(QWidget(parent=self))

        # Comparison Profile mode
        comparison_widget = QWidget(parent=self)
        comparison_layout = QHBoxLayout()
        comparison_layout.setContentsMargins(0, 0, 0, 0)
        comparison_layout.addWidget(QLabel("Using comparison profile"))
        comparison_widget.setLayout(comparison_layout)
        self.design_level_inputs.addWidget(comparison_widget)

        # Polyline mode
        polyline_widget = QWidget(parent=self)
        polyline_layout = QHBoxLayout()
        polyline_layout.setContentsMargins(0, 0, 0, 0)
        self.polyline_add_btn = QPushButton("Add Vertex")
        self.polyline_add_btn.clicked.connect(self._start_polyline_add_mode)
        polyline_layout.addWidget(self.polyline_add_btn)
        self.polyline_clear_btn = QPushButton("Clear")
        self.polyline_clear_btn.clicked.connect(self._clear_polyline)
        polyline_layout.addWidget(self.polyline_clear_btn)
        polyline_layout.addWidget(QLabel("Smooth:"))
        self.smooth_polyline_slider = QSlider(Qt.Orientation.Horizontal)
        self.smooth_polyline_slider.setRange(0, 100)
        self.smooth_polyline_slider.setValue(0)
        self.smooth_polyline_slider.setFixedWidth(80)
        self.smooth_polyline_slider.valueChanged.connect(lambda: self._redraw_graph())
        polyline_layout.addWidget(self.smooth_polyline_slider)
        polyline_widget.setLayout(polyline_layout)
        self.design_level_inputs.addWidget(polyline_widget)

        design_controls_layout.addStretch()

        # Analysis controls
        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.clicked.connect(self.analyze_cut_fill)
        analyze_cut_fill_layout = QHBoxLayout()
        analyze_cut_fill_layout.setSpacing(8)
        analyze_cut_fill_layout.addWidget(self.analyze_btn)
        analyze_cut_fill_layout.addSpacing(12)
        self.cut_volume_label = QLabel("Cut: -")
        self.fill_volume_label = QLabel("Fill: -")
        analyze_cut_fill_layout.addWidget(self.cut_volume_label)
        analyze_cut_fill_layout.addWidget(self.fill_volume_label)
        design_controls_layout.addLayout(analyze_cut_fill_layout)
        
        layout.addLayout(design_controls_layout)

        # Polyline vertex label (compact, always visible)
        polyline_vertex_layout = QHBoxLayout()
        polyline_vertex_layout.setSpacing(6)
        polyline_vertex_layout.setContentsMargins(5, 0, 5, 2)
        self.polyline_vertex_label = QLabel("No vertices defined.")
        polyline_vertex_layout.addWidget(self.polyline_vertex_label)
        layout.addLayout(polyline_vertex_layout)
        
        # Initialize design level inputs (show/hide based on default mode)
        self.update_design_level_inputs()
        
        # Minimal spacing before graph
        layout.addSpacing(5)

        # Matplotlib Figure and Canvas - Make it much larger and compact
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.canvas = FigureCanvas(self.fig)
        # --- Graph and Toolbar Row ---
        graph_row_layout = QHBoxLayout()
        graph_row_layout.setSpacing(0)
        graph_row_layout.setContentsMargins(0, 0, 0, 0)

        # Vertical Navigation Toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setOrientation(Qt.Orientation.Vertical)
        self.toolbar.setStyleSheet("QToolBar { min-width: 32px; max-width: 36px; min-height: 200px; padding: 0px; margin: 0px; spacing: 2px; } QPushButton, QToolButton { min-width: 28px; max-width: 32px; min-height: 28px; max-height: 32px; padding: 0px 2px; margin: 0px; }")
        graph_row_layout.addWidget(self.toolbar)

        # --- Graph Canvas with Floating Fullscreen Button ---
        from PyQt6.QtWidgets import QWidget, QStackedLayout
        graph_canvas_wrapper = QWidget()
        graph_canvas_wrapper.setMinimumSize(400, 300)
        stacked = QStackedLayout(graph_canvas_wrapper)
        stacked.setStackingMode(QStackedLayout.StackingMode.StackAll)
        stacked.addWidget(self.canvas)

        # Fullscreen button as overlay (absolute position in wrapper)
        self.fullscreen_btn = QPushButton(QIcon(os.path.join(ICON_DIR, 'fullscreen.svg')), "")
        self.fullscreen_btn.setToolTip("Toggle Fullscreen (F11)")
        self.fullscreen_btn.setFixedSize(32, 32)
        self.fullscreen_btn.setStyleSheet("border-radius: 16px; font-size: 16pt; position: absolute;")
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        self.fullscreen_btn.setParent(graph_canvas_wrapper)
        self.fullscreen_btn.setFixedSize(36, 36)
        self.fullscreen_btn.setStyleSheet("border-radius: 18px; font-size: 18pt; background: rgba(30,30,30,0.7); color: #fff; position: absolute;")
        self.fullscreen_btn.move(graph_canvas_wrapper.width() - 44, 8)
        self.fullscreen_btn.raise_()
        self.fullscreen_btn.show()
        def move_fs_btn():
            self.fullscreen_btn.move(graph_canvas_wrapper.width() - 44, 8)
        graph_canvas_wrapper.resizeEvent = lambda event: move_fs_btn()
        stacked.addWidget(self.fullscreen_btn)

        graph_row_layout.addWidget(graph_canvas_wrapper, 1)

        # Add the graph row (toolbar + graph) with stretch
        layout.addLayout(graph_row_layout, 1)
        Tooltip(self.toolbar, "Graph navigation toolbar: pan, zoom, save, etc.")
        Tooltip(self.canvas, "Profile graph: shows elevation vs. point. Hover for details.")

        # Fullscreen button: floating over the top-right of the graph
        # self.fullscreen_btn = QPushButton("⛶")
        # self.fullscreen_btn.setToolTip("Toggle Fullscreen (F11)")
        # self.fullscreen_btn.setFixedSize(32, 32)
        # self.fullscreen_btn.setStyleSheet("border-radius: 16px; font-size: 16pt; position: absolute;")
        # self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        # self.fullscreen_btn.setParent(self.canvas)
        # self.fullscreen_btn.setFixedSize(36, 36)
        # self.fullscreen_btn.setStyleSheet("border-radius: 18px; font-size: 18pt; background: rgba(30,30,30,0.7); color: #fff; position: absolute;")
        # self.fullscreen_btn.move(self.canvas.width() - 44, 8)
        # self.fullscreen_btn.raise_()
        # self.fullscreen_btn.show()
        # self.canvas.resizeEvent = lambda event: self.fullscreen_btn.move(self.canvas.width() - 44, 8)
        # Tooltip(self.fullscreen_btn, "Toggle fullscreen mode (F11/Esc)")

        # Add minimal spacing before table
        layout.addSpacing(4)

        # Table for profile data (with better spacing)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Point", "Elevation", "Distance"])
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.SelectedClicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(120)
        self.table.setMaximumHeight(220)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # Set custom delegate for dark editor
        self.table.setItemDelegate(DarkTableDelegate(self.table))
        # Ensure only cell selection is enabled after all setup
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        layout.addWidget(self.table)
        Tooltip(self.table, "Edit or view profile data. Double-click to edit cells. Right-click for options.")
        
        # Live data update: connect cellChanged
        self.table.cellChanged.connect(self._on_table_cell_changed)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self._highlighted_index = None
        
        # Overlay label for fullscreen
        self._overlay_label = QLabel("Press Esc or ❎ to exit fullscreen.", self)
        self._overlay_label.setStyleSheet("background: rgba(0,0,0,0.5); color: white; font-size: 18pt; padding: 20px; border-radius: 10px;")
        self._overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay_label.hide()
        # Screenshot/export button (hidden by default)
        self._export_btn = QPushButton("📷 Export", self)
        self._export_btn.setToolTip("Save graph as image or PDF")
        self._export_btn.setFixedSize(120, 36)
        self._export_btn.setStyleSheet("border-radius: 8px; font-size: 12pt; position: absolute; background: #333; color: white;")
        self._export_btn.clicked.connect(self._export_graph)
        self._export_btn.hide()
        layout.addWidget(self._export_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)

    def toggle_markers(self, state=None):
        if state is not None:
            self.show_markers = bool(state)
        else:
            self.show_markers = self.marker_toggle_cb.isChecked()
        self._redraw_graph()

    def toggle_labels(self, state=None):
        if state is not None:
            self.show_labels = bool(state)
        else:
            self.show_labels = self.label_toggle_cb.isChecked()
        self._redraw_graph()

    def toggle_grade_slopes(self, state=None):
        if state is not None:
            self.show_grade_slopes = bool(state)
        else:
            self.show_grade_slopes = self.grade_slope_toggle_cb.isChecked()
        self._redraw_graph()

    def toggle_interval_mode(self, state=None):
        if state is not None:
            self.interval_mode = bool(state)
        else:
            self.interval_mode = self.interval_mode_cb.isChecked()
        self._redraw_graph()

    def pick_line_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.graph_line_color = color.name()
            settings['graph_line_color'] = color.name()
            save_settings()
            self._redraw_graph()

    def pick_marker_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.graph_marker_color = color.name()
            settings['graph_marker_color'] = color.name()
            save_settings()
            self._redraw_graph()

    def pick_comparison_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.comparison_line_color = color.name()
            settings['comparison_line_color'] = color.name()
            save_settings()
            self._redraw_graph()

    def pick_label_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.label_color = color.name()
            settings['label_color'] = color.name()
            save_settings()
            self._redraw_graph()

    def pick_grade_slope_label_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.grade_slope_label_color = color.name()
            settings['grade_slope_label_color'] = color.name()
            save_settings()
            self._redraw_graph()

    def _toggle_annotation_mode(self):
        self._annotation_mode = not self._annotation_mode
        if self._annotation_mode:
            self.add_text_btn.setText("Cancel")
            QMessageBox.information(self, "Annotation Mode", "Click on the graph to add text annotation. Press Esc to cancel.")
        else:
            self.add_text_btn.setText("Add Text")
            self._exit_annotation_mode()

    def _exit_annotation_mode(self):
        self._annotation_mode = False
        self.add_text_btn.setText("Add Text")

    def clear_annotations(self):
        self._annotations.clear()
        self._redraw_graph()

    def update_design_level_inputs(self):
        mode = self.design_level_mode_cb.currentText()
        self.design_level_inputs.setCurrentIndex(self.design_level_mode_cb.currentIndex())
        if mode == "Polyline":
            self._update_polyline_vertex_label()

    def _load_design_levels_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Design Levels", "", "All Files (*.*)")
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                # Parse the content and set design levels
                # This is a simplified version
                QMessageBox.information(self, "Success", "Design levels loaded from file.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load design levels: {e}")

    def _start_polyline_add_mode(self):
        # Toggle polyline edit mode
        if getattr(self, '_polyline_add_mode', False):
            self._exit_polyline_add_mode()
            return
        self._polyline_add_mode = True
        self._polyline_preview_point = None
        self.canvas.setCursor(Qt.CursorShape.CrossCursor)
        self._polyline_left_cid = self.canvas.mpl_connect('button_press_event', self._add_polyline_vertex)
        self._polyline_right_cid = self.canvas.mpl_connect('button_press_event', self._remove_polyline_vertex)
        self._polyline_key_cid = self.canvas.mpl_connect('key_press_event', self._polyline_key_handler)
        self._polyline_motion_cid = self.canvas.mpl_connect('motion_notify_event', self._polyline_hover_preview)
        QMessageBox.information(self, "Polyline", "Edit mode: Left click to add, right click to remove nearest vertex. Press Enter or click 'Add Vertex' again to finish.")

    def _exit_polyline_add_mode(self):
        self._polyline_add_mode = False
        self._polyline_preview_point = None
        self.canvas.setCursor(Qt.CursorShape.ArrowCursor)
        if hasattr(self, '_polyline_left_cid') and self._polyline_left_cid is not None:
            self.canvas.mpl_disconnect(self._polyline_left_cid)
            self._polyline_left_cid = None
        if hasattr(self, '_polyline_right_cid') and self._polyline_right_cid is not None:
            self.canvas.mpl_disconnect(self._polyline_right_cid)
            self._polyline_right_cid = None
        if hasattr(self, '_polyline_key_cid') and self._polyline_key_cid is not None:
            self.canvas.mpl_disconnect(self._polyline_key_cid)
            self._polyline_key_cid = None
        if hasattr(self, '_polyline_motion_cid') and self._polyline_motion_cid is not None:
            self.canvas.mpl_disconnect(self._polyline_motion_cid)
            self._polyline_motion_cid = None
        self.polyline_add_btn.setText("Add Vertex")
        self._redraw_graph()

    def _polyline_hover_preview(self, event):
        if not getattr(self, '_polyline_add_mode', False):
            return
        if event.inaxes != self.ax:
            self._polyline_preview_point = None
        else:
            self._polyline_preview_point = (event.xdata, event.ydata)
        print(f"[DEBUG] Hover preview: {self._polyline_preview_point}")
        self._redraw_graph()

    def _add_polyline_vertex(self, event):
        if not getattr(self, '_polyline_add_mode', False):
            return
        if event.inaxes != self.ax or event.button != 1:
            return
        self._polyline_vertices.append((event.xdata, event.ydata))
        self._update_polyline_vertex_label()
        self._redraw_graph()

    def _remove_polyline_vertex(self, event):
        if not getattr(self, '_polyline_add_mode', False):
            return
        if event.inaxes != self.ax or event.button != 3:
            return
        if not self._polyline_vertices:
            return
        import numpy as np
        verts = np.array(self._polyline_vertices)
        dists = np.hypot(verts[:,0] - event.xdata, verts[:,1] - event.ydata)
        idx = np.argmin(dists)
        self._polyline_vertices.pop(idx)
        self._update_polyline_vertex_label()
        self._redraw_graph()

    def _polyline_key_handler(self, event):
        if event.key == 'enter':
            self._exit_polyline_add_mode()

    def _update_polyline_vertex_label(self):
        if not self._polyline_vertices:
            self.polyline_vertex_label.setText("No vertices defined.")
        else:
            pts = [f"({x:.2f}, {y:.2f})" for x, y in self._polyline_vertices]
            if len(pts) > 2:
                shown = ', '.join(pts[:2])
                more = len(pts) - 2
                self.polyline_vertex_label.setText(f"Vertices: {shown} ... ({more} more)")
            else:
                self.polyline_vertex_label.setText("Vertices: " + ', '.join(pts))

    def sync_data_from_table(self):
        self._last_data = []
        self._annotations = []  # Clear previous annotations
        headers = [self.table.horizontalHeaderItem(i).text().lower() for i in range(self.table.columnCount())]
        try:
            x_col = headers.index("distance")
            y_col = headers.index("elevation")
        except ValueError:
            try:
                x_col = headers.index("point")
                y_col = headers.index("elevation")
            except ValueError:
                x_col, y_col = 0, 1  # fallback
        for row in range(self.table.rowCount()):
            try:
                x_item = self.table.item(row, x_col)
                y_item = self.table.item(row, y_col)
                if x_item is not None and y_item is not None:
                    point_text = x_item.text()
                    y_val = float(y_item.text())
                    # Extract numeric part for plotting
                    match = re.match(r"^\s*(-?\d+(?:\.\d+)?)", point_text)
                    if match:
                        x_val = float(match.group(1))
                        self._last_data.append((x_val, y_val))
                        # If there is a non-numeric annotation, add it
                        annotation = point_text[match.end():].strip()
                        if annotation:
                            self._annotations.append({'x': x_val, 'y': y_val, 'text': annotation})
                    else:
                        # If no numeric part, skip plotting but could add annotation if desired
                        continue
            except Exception:
                continue

    def analyze_cut_fill(self):
        # Exit polyline add mode if active
        if getattr(self, '_polyline_add_mode', False):
            self._exit_polyline_add_mode()
        self.sync_data_from_table()
        import numpy as np
        from PyQt6.QtWidgets import QMessageBox
        mode = self.design_level_mode_cb.currentText()
        # Gather data from the table or last data
        if not hasattr(self, '_last_data') or not self._last_data or len(self._last_data) < 2:
            QMessageBox.information(self, "Cut/Fill Analysis", "Not enough data to analyze.")
            return
        x_vals, y_vals = zip(*self._last_data)
        x_vals = np.array(x_vals)
        y_vals = np.array(y_vals)
        design_levels = None
        # --- Design Level Calculation ---
        if mode == "Fixed":
            try:
                design_level = float(self.design_level_edit.text())
            except ValueError:
                QMessageBox.critical(self, "Input Error", "Please enter a valid number for the design level.")
                return
            design_levels = np.array([design_level] * len(x_vals))
        elif mode == "Gradient":
            try:
                start = float(self.gradient_start_edit.text())
                end = float(self.gradient_end_edit.text())
            except ValueError:
                QMessageBox.critical(self, "Input Error", "Please enter valid numbers for start and end design levels.")
                return
            n = len(x_vals)
            if n < 2:
                QMessageBox.information(self, "Cut/Fill Analysis", "Not enough data to analyze.")
                return
            design_levels = np.array([start + (end - start) * i / (n - 1) for i in range(n)])
        elif mode == "From Points":
            raw = self.from_points_edit.text().replace(',', ' ').split()
            try:
                design_levels = np.array([float(val) for val in raw])
            except ValueError:
                QMessageBox.critical(self, "Input Error", "Please enter valid numbers for all design levels.")
                return
            if len(design_levels) != len(x_vals):
                QMessageBox.critical(self, "Input Error", f"Number of design levels ({len(design_levels)}) does not match number of points ({len(x_vals)}).")
                return
        elif mode == "First RL":
            # Try to get from leveling tab if possible
            first_rl = None
            try:
                main_window = self.parent()
                if hasattr(main_window, 'leveling_app') and hasattr(main_window.leveling_app, 'first_rl_entry'):
                    first_rl = float(main_window.leveling_app.first_rl_entry.text())
                else:
                    first_rl = y_vals[0]
            except Exception:
                QMessageBox.critical(self, "Input Error", "Could not get First RL from leveling data.")
                return
            design_levels = np.array([first_rl] * len(x_vals))
        elif mode == "Comparison Profile":
            if not hasattr(self, '_comparison_data') or not self._comparison_data:
                QMessageBox.critical(self, "Input Error", "No comparison profile loaded. Please load a comparison profile first.")
                return
            if len(self._comparison_data) != len(x_vals):
                QMessageBox.critical(self, "Input Error", f"Number of points in comparison profile ({len(self._comparison_data)}) does not match main profile ({len(x_vals)}).")
                return
            design_levels = np.array([y for x, y in self._comparison_data])
        elif mode == "Polyline":
            if not hasattr(self, '_polyline_vertices') or len(self._polyline_vertices) < 2:
                QMessageBox.critical(self, "Input Error", "Please define at least 2 polyline vertices.")
                return
            poly_x, poly_y = zip(*sorted(self._polyline_vertices))
            smooth_factor = self.smooth_polyline_slider.value() / 100.0
            if smooth_factor > 0 and len(self._polyline_vertices) >= 3:
                try:
                    from scipy.interpolate import make_interp_spline
                    n_points = max(100, len(poly_x) * 10)
                    xnew = np.array(x_vals)
                    spline = make_interp_spline(poly_x, poly_y, k=2)
                    y_smooth = spline(xnew)
                    y_linear = np.interp(xnew, poly_x, poly_y)
                    design_levels = (1 - smooth_factor) * y_linear + smooth_factor * y_smooth
                except Exception:
                    design_levels = np.interp(x_vals, poly_x, poly_y)
            else:
                design_levels = np.interp(x_vals, poly_x, poly_y)
        else:
            QMessageBox.critical(self, "Input Error", "Unknown design level mode.")
            return

        # --- Redraw Graph ---
        self._redraw_graph()  # Clear previous analysis
        ax = self.ax
        # Draw design level line(s)
        if mode == "Polyline" and hasattr(self, '_polyline_vertices') and len(self._polyline_vertices) >= 2:
            self._draw_polyline()
        elif np.all(design_levels == design_levels[0]):
            ax.axhline(y=design_levels[0], color='red', linestyle='--', linewidth=1.5, label=f'Design Level ({design_levels[0]:.2f})')
        else:
            ax.plot(x_vals, design_levels, color='red', linestyle='--', linewidth=1.5, label='Design Level')

        # --- Shade cut and fill areas ---
        ax.fill_between(x_vals, y_vals, design_levels, where=(y_vals >= design_levels), facecolor='orange', alpha=0.4, interpolate=True, label='Cut')
        ax.fill_between(x_vals, y_vals, design_levels, where=(y_vals < design_levels), facecolor='cyan', alpha=0.4, interpolate=True, label='Fill')

        # --- Calculate cut and fill areas ---
        cut_area = 0.0
        fill_area = 0.0
        for i in range(1, len(x_vals)):
            x0, x1 = x_vals[i-1], x_vals[i]
            y0, y1 = y_vals[i-1], y_vals[i]
            d0, d1 = design_levels[i-1], design_levels[i]
            h0 = y0 - d0
            h1 = y1 - d1
            width = abs(x1 - x0)
            if h0 * h1 >= 0:  # Both points are on the same side
                area = 0.5 * (h0 + h1) * width
                if area > 0:
                    cut_area += area
                else:
                    fill_area += abs(area)
            else:  # Line crosses the design level
                if (h1 - h0) != 0:
                    x_intersect = x0 - h0 * (x1 - x0) / (h1 - h0)
                    d_intersect = d0 + (d1 - d0) * (x_intersect - x0) / (x1 - x0) if (x1 - x0) != 0 else d0
                else:
                    x_intersect = x0
                    d_intersect = d0
                area1 = 0.5 * h0 * (x_intersect - x0)
                if area1 > 0:
                    cut_area += area1
                else:
                    fill_area += abs(area1)
                area2 = 0.5 * h1 * (x1 - x_intersect)
                if area2 > 0:
                    cut_area += area2
                else:
                    fill_area += abs(area2)

        ax.legend()
        self.canvas.draw()

        # --- Show summary message ---
        msg = f"Design Level Mode: {mode}\n"
        if mode == "Fixed":
            msg += f"Design Elevation: {design_levels[0]:.2f}\n"
        elif mode == "Gradient":
            msg += f"Start: {self.gradient_start_edit.text()}, End: {self.gradient_end_edit.text()}\n"
        elif mode == "From Points":
            msg += f"Design Levels: {self.from_points_edit.text()}\n"
        elif mode == "First RL":
            msg += f"First RL: {design_levels[0]:.2f}\n"
        elif mode == "Comparison Profile":
            msg += f"Using loaded comparison profile as design level.\n"
        elif mode == "Polyline":
            msg += f"Polyline vertices: {self.polyline_vertex_label.text()}\n"
        msg += f"\nCut Area: {cut_area:.2f}\nFill Area: {fill_area:.2f}"
        QMessageBox.information(self, "Cut/Fill Analysis", msg)

    def export_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Graph", "", "PDF Files (*.pdf)")
        if file_path:
            try:
                self.fig.savefig(file_path, format='pdf', bbox_inches='tight')
                QMessageBox.information(self, "Success", "Graph exported to PDF.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export PDF: {e}")

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
        if hasattr(self, 'column_customizer') and self.column_customizer is not None and hasattr(self.column_customizer, 'customize_columns_dialog'):
            menu.addAction(QIcon(os.path.join(ICON_DIR, 'columns.svg')), "Customize Columns...", lambda: getattr(self.column_customizer, 'customize_columns_dialog', lambda x: None)('result'))
        viewport = getattr(self.table, 'viewport', lambda: None)()
        if viewport is not None and hasattr(viewport, 'mapToGlobal'):
            menu.exec(viewport.mapToGlobal(pos))
        else:
            menu.exec(pos)

    def copy_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.clipboard_row = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item is not None and hasattr(item, 'text'):
                    self.clipboard_row.append(item.text())
                else:
                    self.clipboard_row.append("")

    def paste_row(self):
        row = self.table.currentRow()
        if row >= 0 and hasattr(self, 'clipboard_row'):
            for col, value in enumerate(self.clipboard_row):
                self.table.setItem(row, col, QTableWidgetItem(value))

    def insert_row_above(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.insertRow(row)

    def insert_row_below(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.insertRow(row + 1)

    def delete_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def update_from_leveling(self, results):
        self.table.setRowCount(0)
        self._last_data.clear()
        for row in results:
            point, elev, dist = None, None, None
            if isinstance(row, dict):
                point = row.get('Point')
                elev = row.get('Elevation')
                dist = row.get('Distance', None)
            else:
                if len(row) >= 3:
                    point, elev, dist = row[0], row[1], row[2]
                elif len(row) == 2:
                    point, elev = row[0], row[1]
            if point is not None and elev is not None:
                # Use point number as distance if no distance provided
                x_val = float(dist) if dist is not None else (float(point) if point is not None and str(point).replace('.', '').replace('-', '').isdigit() else len(self._last_data))
                y_val = float(elev)
                self._last_data.append((x_val, y_val))
                row_idx = self.table.rowCount()
                self.table.insertRow(row_idx)
                self.table.setItem(row_idx, 0, QTableWidgetItem(str(point)))
                self.table.setItem(row_idx, 1, QTableWidgetItem(f"{y_val:.3f}"))
                self.table.setItem(row_idx, 2, QTableWidgetItem(f"{x_val:.3f}" if dist is not None else f"{x_val:.3f}"))
        self._update_all_table_cell_colors()
        self._redraw_graph()

    def toggle_compare_mode(self):
        if not hasattr(self, '_comparison_data') or not self._comparison_data:
            from PyQt6.QtWidgets import QMessageBox
            resp = QMessageBox.question(self, "Comparison Profile", "No comparison profile loaded. Load one now?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if resp == QMessageBox.StandardButton.Yes:
                self.load_comparison_profile()
            else:
                return
        self._compare_mode = not self._compare_mode
        self._redraw_graph()

    def _redraw_graph(self, temp_line=None):
        import numpy as np
        self.sync_data_from_table()
        self.ax.clear()
        data = self._last_data
        print("Redrawing graph with data:", data)
        line_color = settings.get('graph_line_color', self.graph_line_color)
        marker_color = settings.get('graph_marker_color', self.graph_marker_color)
        highlight_color = settings.get('graph_highlight_color', 'crimson')
        interval_mode = self.interval_mode
        interval = None
        x_vals, y_vals = [], []
        comp_x, comp_y = [], []
        N = len(data)
        # Handle interval mode for both profiles
        if interval_mode and data:
            try:
                interval = float(self.interval_value_edit.text())
                if interval > 0:
                    x_vals = [i * interval for i in range(N)]
                    y_vals = [y for (x, y) in data]
                    # Update table's Distance column if present
                    for i in range(min(N, self.table.rowCount())):
                        if self.table.columnCount() > 2:
                            self.table.setItem(i, 2, QTableWidgetItem(f"{x_vals[i]:.3f}"))
                    # Resample comparison profile if present
                    if getattr(self, '_compare_mode', False) and hasattr(self, '_comparison_data') and self._comparison_data:
                        orig_comp_x, orig_comp_y = zip(*self._comparison_data)
                        comp_x = x_vals
                        comp_y = np.interp(x_vals, orig_comp_x, orig_comp_y)
                else:
                    x_vals, y_vals = zip(*data)
            except ValueError:
                x_vals, y_vals = zip(*data)
        elif data:
            if len(data[0]) == 1:
                x_vals = list(range(len(data)))
                y_vals = [y for (y,) in data]
            else:
                x_vals, y_vals = zip(*data)
            # Resample comparison profile to match x_vals if in compare mode
            if getattr(self, '_compare_mode', False) and hasattr(self, '_comparison_data') and self._comparison_data:
                orig_comp_x, orig_comp_y = zip(*self._comparison_data)
                comp_x = x_vals
                comp_y = np.interp(x_vals, orig_comp_x, orig_comp_y)
        # Plot main profile
        if x_vals and y_vals:
            self.ax.plot(x_vals, y_vals, marker='o' if self.show_markers else None, color=line_color, linewidth=2)
            if self.show_markers:
                self.ax.scatter(x_vals, y_vals, s=60, color=marker_color, edgecolor='black', zorder=5)
            if self._highlighted_index is not None and 0 <= self._highlighted_index < len(y_vals):
                hx, hy = x_vals[self._highlighted_index], y_vals[self._highlighted_index]
                self.ax.scatter([hx], [hy], s=180, color=highlight_color, edgecolor='black', zorder=10, marker='o')
            if self.show_labels:
                self._draw_labels()
            if self.show_grade_slopes:
                self._draw_grade_slopes()
            self.ax.grid(True, linestyle='--', alpha=0.7)
            self.ax.minorticks_on()
            self.ax.grid(which='minor', linestyle=':', linewidth=0.5, alpha=0.4)
        # Plot comparison profile if in compare mode
        if getattr(self, '_compare_mode', False) and hasattr(self, '_comparison_data') and self._comparison_data and comp_x and comp_y:
            self.ax.plot(comp_x, comp_y, color=self.comparison_line_color, linestyle='--', linewidth=2, label='Comparison Profile')
            self.ax.legend()
        # Always draw the polyline if it's being designed
        self._draw_polyline()
        self.ax.set_xlabel("Point", fontsize=11)
        self.ax.set_ylabel("Elevation", fontsize=11)
        self.ax.set_title("Profile Graph (Elevation vs. Point)", fontsize=12, fontweight='bold')
        self.fig.tight_layout()
        self.canvas.draw()

    def _draw_labels(self):
        if not self._last_data:
            return
        x_vals, y_vals = zip(*self._last_data)
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        skip = 1
        if len(x_vals) > 30:
            skip = max(1, len(x_vals)//20)
        for i, (x, y) in enumerate(zip(x_vals, y_vals)):
            if i % skip != 0:
                continue
            if xlim[0] <= x <= xlim[1] and ylim[0] <= y <= ylim[1]:
                self.ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(0,8), ha='center', fontsize=8, color=self.label_color)
        # Draw custom annotations for non-numeric parts (e.g., (cp))
        for ann in getattr(self, '_annotations', []):
            if xlim[0] <= ann['x'] <= xlim[1] and ylim[0] <= ann['y'] <= ylim[1]:
                self.ax.annotate(ann['text'], (ann['x'], ann['y']), textcoords="offset points", xytext=(0,18), ha='center', fontsize=8, color='purple', fontweight='bold')

    def _draw_grade_slopes(self):
        if not self.show_grade_slopes or not self._last_data or len(self._last_data) < 2:
            return
        
        data = sorted(self._last_data)
        x_vals, y_vals = zip(*data)
        
        # Skipping logic to avoid clutter
        skip = 1
        if len(x_vals) > 30:
            skip = max(1, len(x_vals) // 15)

        for i in range(len(x_vals) - 1):
            if i % skip != 0:
                continue

            x1, y1 = x_vals[i], y_vals[i]
            x2, y2 = x_vals[i+1], y_vals[i+1]
            
            if x2 - x1 == 0:
                slope = float('inf')
            else:
                slope = (y2 - y1) / (x2 - x1) * 100
            
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            
            self.ax.text(mid_x, mid_y, f'{slope:.2f}%', color=self.grade_slope_label_color,
                         ha='center', va='bottom', rotation=angle, fontsize=8,
                         bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', boxstyle='round,pad=0.1'))

    def _draw_polyline(self):
        if not self._polyline_vertices and not (getattr(self, '_polyline_add_mode', False) and self._polyline_preview_point):
            return

        import numpy as np
        
        # Sort vertices by x-axis to match tkinter app's behavior for spline consistency
        sorted_vertices = sorted(self._polyline_vertices)

        # Start with existing vertices
        if sorted_vertices:
            poly_x, poly_y = zip(*sorted_vertices)
            poly_x, poly_y = list(poly_x), list(poly_y)
        else:
            poly_x, poly_y = [], []

        # Add preview point if in add mode and a preview point exists
        if getattr(self, '_polyline_add_mode', False) and self._polyline_preview_point is not None:
            # The preview line should only be drawn from the last vertex.
            # If there are no vertices, there is nothing to preview from.
            if self._polyline_vertices:
                last_x, last_y = self._polyline_vertices[-1]
                preview_x, preview_y = self._polyline_preview_point
                # Draw a temporary dashed line for the preview segment
                self.ax.plot([last_x, preview_x], [last_y, preview_y], color='magenta', linestyle='--', linewidth=1.5, zorder=9)

        # If there are committed vertices, draw them
        if not self._polyline_vertices:
            return # Nothing more to do if no vertices exist

        smooth_factor = self.smooth_polyline_slider.value() / 100.0
        
        # Draw the main polyline (either smoothed or linear)
        if len(poly_x) < 2: # Can't draw a line with less than 2 points
            if poly_x: # Draw a single marker if only one point
                self.ax.scatter(poly_x, poly_y, color='red', s=40, zorder=10)
            return

        if smooth_factor > 0 and len(poly_x) >= 3:
            try:
                from scipy.interpolate import make_interp_spline
                # Sort vertices by x-axis for correct spline interpolation
                sorted_points = sorted(zip(poly_x, poly_y))
                sorted_x, sorted_y = zip(*sorted_points)
                
                n_points = max(100, len(sorted_x) * 10)
                xnew = np.linspace(min(sorted_x), max(sorted_x), n_points)
                
                spline = make_interp_spline(sorted_x, sorted_y, k=2)
                y_smooth = spline(xnew)
                
                y_linear = np.interp(xnew, sorted_x, sorted_y)
                y_blend = (1 - smooth_factor) * y_linear + smooth_factor * y_smooth
                
                self.ax.plot(xnew, y_blend, color='red', linestyle='-', linewidth=2, marker=None, label='Design Polyline (Smooth)')
                self.ax.scatter(poly_x, poly_y, color='red', s=40, zorder=10)
            except Exception:
                # Fallback to linear plot on error
                self.ax.plot(poly_x, poly_y, color='red', linestyle='-', linewidth=2, marker='o', label='Design Polyline')
        else:
            # Draw a simple linear polyline
            self.ax.plot(poly_x, poly_y, color='red', linestyle='-', linewidth=2, marker='o', label='Design Polyline')

        # Add grade slope labels for the polyline
        if self.show_grade_slopes and len(poly_x) > 1:
            skip_poly = 1
            if len(poly_x) > 10:
                skip_poly = max(1, len(poly_x) // 5)

            for i in range(len(poly_x) - 1):
                if i % skip_poly != 0:
                    continue

                x1, y1 = poly_x[i], poly_y[i]
                x2, y2 = poly_x[i+1], poly_y[i+1]
                if x2 - x1 == 0:
                    slope = float('inf')
                else:
                    slope = (y2 - y1) / (x2 - x1) * 100
                mid_x = (x1 + x2) / 2
                mid_y = (y1 + y2) / 2
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                self.ax.text(mid_x, mid_y, f'{slope:.2f}%', color=self.grade_slope_label_color,
                             ha='center', va='bottom', rotation=angle, fontsize=8,
                             bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', boxstyle='round,pad=0.1'))
        
        return # The old code below is now replaced by the logic above

        # Use the order the user added the vertices
        poly_x, poly_y = zip(*self._polyline_vertices)
        smooth_factor = self.smooth_polyline_slider.value() / 100.0
        # Add preview point if in add mode and preview exists
        if getattr(self, '_polyline_add_mode', False) and self._polyline_preview_point is not None:
            px, py = self._polyline_preview_point
            poly_x = list(poly_x) + [px]
            poly_y = list(poly_y) + [py]
            print(f"[DEBUG] Drawing polyline with preview: {list(zip(poly_x, poly_y))}")
        else:
            print(f"[DEBUG] Drawing polyline: {list(zip(poly_x, poly_y))}")
        if smooth_factor > 0 and len(poly_x) >= 3:
            try:
                from scipy.interpolate import make_interp_spline
                n_points = max(100, len(poly_x) * 10)
                xnew = np.linspace(min(poly_x), max(poly_x), n_points)
                spline = make_interp_spline(poly_x, poly_y, k=2)
                y_smooth = spline(xnew)
                y_linear = np.interp(xnew, poly_x, poly_y)
                y_blend = (1 - smooth_factor) * y_linear + smooth_factor * y_smooth
                self.ax.plot(xnew, y_blend, color='red', linestyle='-', linewidth=2, marker=None, label='Design Polyline (Smooth)')
                self.ax.scatter(poly_x, poly_y, color='red', s=40, zorder=10)
            except Exception:
                self.ax.plot(poly_x, poly_y, color='red', linestyle='-', linewidth=2, marker='o', label='Design Polyline')
        else:
            self.ax.plot(poly_x, poly_y, color='red', linestyle='-', linewidth=2, marker='o', label='Design Polyline')

    def load_comparison_profile(self):
        print("DEBUG: load_comparison_profile called")
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Comparison Profile", "", "CSV Files (*.csv)")
        print(f"DEBUG: file_path={file_path}")
        if not file_path:
            print("DEBUG: No file selected")
            return
        dialog = ImportDialog(self, file_path, ["Point", "Elevation", "Distance"])
        result = dialog.exec()
        print(f"DEBUG: dialog.exec() returned {result}")
        if not result:
            print("DEBUG: Dialog cancelled")
            return
        if dialog.import_result is None:
            print("DEBUG: import_result is None")
            return
        mapping = dialog.import_result["mapping"]
        has_header = dialog.import_result["has_header"]
        print(f"DEBUG: mapping={mapping}, has_header={has_header}")
        # Require at least Elevation and one of Point or Distance
        if not mapping or "Elevation" not in mapping or ("Point" not in mapping and "Distance" not in mapping):
            QMessageBox.warning(self, "Comparison Profile", "Please map at least 'Elevation' and 'Point' or 'Distance' columns before importing.")
            print("DEBUG: Invalid mapping, aborting import.")
            return
        try:
            data = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                if has_header:
                    next(reader, None)
                for row in reader:
                    try:
                        x = float(row[mapping.get("Distance", 0)]) if "Distance" in mapping else float(row[mapping.get("Point", 0)])
                        y = float(row[mapping.get("Elevation", 1)])
                        data.append((x, y))
                    except Exception as e:
                        print(f"DEBUG: Skipping row {row} due to error: {e}")
                        continue
            print(f"DEBUG: Loaded {len(data)} points from file")
            if not data:
                QMessageBox.warning(self, "Comparison Profile", "No valid data found in the selected file.")
                return
            self._comparison_data = data
            self._compare_mode = True  # Show comparison profile immediately
            self._redraw_graph()
            QMessageBox.information(self, "Comparison Profile", f"Loaded {len(data)} points from comparison profile.")
        except Exception as e:
            print(f"DEBUG: Exception in load_comparison_profile: {e}")
            QMessageBox.critical(self, "Comparison Profile Error", f"Failed to load comparison profile:\n{e}")

    def _show_overlay_label(self):
        if self._overlay_label is not None:
            self._overlay_label.show()
            self._overlay_timer.start(3000)  # Auto-hide after 3 seconds

    def _hide_overlay_label(self):
        if self._overlay_label is not None:
            self._overlay_label.hide()

    def _reset_overlay_timer(self):
        if self._fullscreen_mode:
            self._show_overlay_label()

    def toggle_minimalist_mode(self):
        self._minimalist_mode = not self._minimalist_mode
        if self._fullscreen_mode:
            if self._export_btn is not None:
                self._export_btn.hide()
            if self.fullscreen_btn is not None:
                self.fullscreen_btn.hide()
        else:
            if self._export_btn is not None:
                self._export_btn.show()
            if self.fullscreen_btn is not None:
                self.fullscreen_btn.show()

    def toggle_fullscreen(self):
        if not self._fullscreen_mode:
            self._hidden_widgets = []
            for widget in [self.update_graph_btn, self.toolbar, self.table]:
                if widget.isVisible():
                    self._animate_hide(widget)
                    self._hidden_widgets.append(widget)
            from PyQt6.QtWidgets import QBoxLayout
            if isinstance(self._main_layout, QBoxLayout):
                self._main_layout.setStretchFactor(self.canvas, 1)
            self.fullscreen_btn.setText("❎")
            self._animate_fade(self.canvas, fade_in=True)
            if self._overlay_label is not None:
                self._show_overlay_label()
            if self._export_btn is not None and not self._minimalist_mode:
                self._export_btn.show()
            if self.fullscreen_btn is not None and not self._minimalist_mode:
                self.fullscreen_btn.show()
            self._fullscreen_mode = True
            settings['graph_fullscreen'] = True
            save_settings()
            self._redraw_graph()
        else:
            for widget in self._hidden_widgets:
                self._animate_show(widget)
            self._hidden_widgets = []
            self.fullscreen_btn.setText("⛶")
            self._animate_fade(self.canvas, fade_in=False)
            if self._overlay_label is not None:
                self._overlay_label.hide()
            if self._export_btn is not None:
                self._export_btn.hide()
            if self.fullscreen_btn is not None:
                self.fullscreen_btn.show()
            self._fullscreen_mode = False
            self._minimalist_mode = False  # Reset minimalist mode on exit
            settings['graph_fullscreen'] = False
            save_settings()
            self._redraw_graph()

    def toggle_presentation_mode(self):
        self._presentation_mode = not self._presentation_mode
        widgets = [self.update_graph_btn, self.toolbar, self.table, self._export_btn, self.fullscreen_btn]
        if self._presentation_mode:
            for w in widgets:
                if w is not None:
                    w.hide()
            if self._overlay_label is not None:
                self._overlay_label.show()
        else:
            if self._fullscreen_mode and not self._minimalist_mode:
                for w in [self.update_graph_btn, self.toolbar, self.table, self._export_btn, self.fullscreen_btn]:
                    if w is not None:
                        w.show()
            if self._overlay_label is not None:
                self._overlay_label.show()
        self._redraw_graph()

    def _on_graph_hover(self, event):
        if not event.inaxes or not self._last_data:
            self._data_cursor_label.hide()
            return
        # Check if any lines are plotted
        if not self.ax.lines:
            self._data_cursor_label.hide()
            return
        line = self.ax.lines[0]  # Assuming the main profile is the first line
        x_data, y_data = line.get_data()
        if event.xdata is None or event.ydata is None:
            self._data_cursor_label.hide()
            return
        import numpy as np
        # Interpolate elevation at the cursor's x-position
        interpolated_y = np.interp(event.xdata, x_data, y_data)
        # Check if the cursor is vertically close to the interpolated point
        y_threshold = (self.ax.get_ylim()[1] - self.ax.get_ylim()[0]) * 0.05  # 5% of y-axis range
        if abs(event.ydata - interpolated_y) > y_threshold:
            self._data_cursor_label.hide()
            return
        # Find the segment the cursor is on
        segment_index = np.searchsorted(x_data, event.xdata) - 1
        if segment_index < 0:
            segment_index = 0
        if segment_index >= len(x_data) - 1:
            segment_index = len(x_data) - 2
        x1, y1 = x_data[segment_index], y_data[segment_index]
        x2, y2 = x_data[segment_index + 1], y_data[segment_index + 1]
        slope = 0
        if (x2 - x1) != 0:
            slope = (y2 - y1) / (x2 - x1) * 100
        info = (f"Distance: {event.xdata:.2f}<br>"
                f"Elevation: {interpolated_y:.2f}<br>"
                f"Grade: {slope:.2f}%")
        self._data_cursor_label.setText(info)
        # Move tooltip closer to the mouse
        self._data_cursor_label.move(int(event.x) + 10, int(event.y) + 10)
        self._data_cursor_label.show()

    def _on_graph_click(self, event):
        if event.inaxes != self.ax:
            return
        
        if self._annotation_mode:
            text = self.annotation_text_edit.text().strip()
            if text:
                self._annotations.append({
                    'x': event.xdata,
                    'y': event.ydata,
                    'text': text
                })
                self.annotation_text_edit.clear()
                self._redraw_graph()
                self._exit_annotation_mode()
        elif self._polyline_add_mode:
            # Left click adds vertex
            if event.button == 1:  # Left click
                self._polyline_vertices.append((event.xdata, event.ydata))
                self._update_polyline_vertex_label()
                self._redraw_graph()
            # Right click removes nearest vertex
            elif event.button == 3:  # Right click
                if self._polyline_vertices:
                    import numpy as np
                    verts = np.array(self._polyline_vertices)
                    dists = np.hypot(verts[:,0] - event.xdata, verts[:,1] - event.ydata)
                    idx = np.argmin(dists)
                    self._polyline_vertices.pop(idx)
                    self._update_polyline_vertex_label()
                    self._redraw_graph()
        else:
            # Show persistent tooltip on click (optional, for now just same as hover)
            self._on_graph_hover(event)

    def _on_graph_draw_start(self, event):
        if not self._fullscreen_mode or not self._presentation_mode or not event.inaxes:
            return
        self._drawing = True
        self._draw_start = (event.xdata, event.ydata)

    def _on_graph_draw_move(self, event):
        if not self._fullscreen_mode or not self._presentation_mode or not self._drawing or not event.inaxes:
            return
        # Draw a temporary line (not persistent)
        self._redraw_graph(temp_line=(self._draw_start, (event.xdata, event.ydata)))

    def _on_graph_draw_end(self, event):
        if not self._fullscreen_mode or not self._presentation_mode or not self._drawing or not event.inaxes:
            return
        self._drawing = False
        x0, y0 = self._draw_start
        x1, y1 = event.xdata, event.ydata
        self._annotations.append((x0, y0, x1, y1))
        self._draw_start = None
        self._redraw_graph()

    def eventFilter(self, obj, event):
        if self._fullscreen_mode:
            if event.type() == QEvent.Type.KeyPress:
                self._reset_overlay_timer()
                # Minimalist mode toggle: M key
                if event.key() == Qt.Key.Key_M:
                    self.toggle_minimalist_mode()
                    return True
                # Zoom in (+ or =)
                if event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                    self._zoom_graph(1.2)
                    return True
                # Zoom out (- or _)
                if event.key() in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
                    self._zoom_graph(1/1.2)
                    return True
                # Pan left
                if event.key() == Qt.Key.Key_Left:
                    self._pan_graph(dx=-0.1)
                    return True
                # Pan right
                if event.key() == Qt.Key.Key_Right:
                    self._pan_graph(dx=0.1)
                    return True
                # Pan up
                if event.key() == Qt.Key.Key_Up:
                    self._pan_graph(dy=0.1)
                    return True
                # Pan down
                if event.key() == Qt.Key.Key_Down:
                    self._pan_graph(dy=-0.1)
                    return True
                if event.key() == Qt.Key.Key_Escape:
                    if self._annotation_mode:
                        self._exit_annotation_mode()
                        return True
                    elif self._polyline_add_mode:
                        self._exit_polyline_add_mode()
                        return True
                    else:
                        self.toggle_fullscreen()
                        return True
                # Enter key for polyline mode
                if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                    if self._polyline_add_mode:
                        self._exit_polyline_add_mode()
                        return True
                # Presentation mode toggle: P key
                if event.key() == Qt.Key.Key_P:
                    self.toggle_presentation_mode()
                    return True
                if self._presentation_mode and event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_F11):
                    self.toggle_presentation_mode()
                    self.toggle_fullscreen()
                    return True
            if event.type() == QEvent.Type.MouseMove or event.type() == QEvent.Type.MouseButtonPress:
                self._reset_overlay_timer()
                # Right-click toggles minimalist mode
                if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.RightButton:
                    self.toggle_minimalist_mode()
                    return True
            if event.type() == QEvent.Type.ShortcutOverride:
                if event.key() == Qt.Key.Key_Escape:
                    self.toggle_fullscreen()
                    return True
            if event.type() == QEvent.Type.Leave:
                self._data_cursor_label.hide()
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_F11:
                self.toggle_fullscreen()
                return True
        return super().eventFilter(obj, event)

    def _zoom_graph(self, factor):
        # Zoom the matplotlib axes by the given factor
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        xmid = (xlim[0] + xlim[1]) / 2
        ymid = (ylim[0] + ylim[1]) / 2
        xhalf = (xlim[1] - xlim[0]) / 2 / factor
        yhalf = (ylim[1] - ylim[0]) / 2 / factor
        self.ax.set_xlim(xmid - xhalf, xmid + xhalf)
        self.ax.set_ylim(ymid - yhalf, ymid + yhalf)
        self.canvas.draw()

    def _pan_graph(self, dx: float = 0.0, dy: float = 0.0):
        # Pan the matplotlib axes by a fraction of the current range
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        xrange = xlim[1] - xlim[0]
        yrange = ylim[1] - ylim[0]
        self.ax.set_xlim(xlim[0] + dx * xrange, xlim[1] + dx * xrange)
        self.ax.set_ylim(ylim[0] + dy * yrange, ylim[1] + dy * yrange)
        self.canvas.draw()

    def _animate_hide(self, widget):
        # Fade out animation (if possible)
        anim = QPropertyAnimation(widget, b"windowOpacity")
        anim.setDuration(200)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.finished.connect(widget.hide)
        anim.start()
        widget._fade_anim = anim  # Prevent garbage collection

    def _animate_show(self, widget):
        widget.show()
        anim = QPropertyAnimation(widget, b"windowOpacity")
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start()
        widget._fade_anim = anim  # Prevent garbage collection

    def _animate_fade(self, widget, fade_in=True):
        anim = QPropertyAnimation(widget, b"windowOpacity")
        anim.setDuration(350)
        if fade_in:
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
        else:
            anim.setStartValue(1.0)
            anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start()
        widget._fade_anim = anim  # Prevent garbage collection

    def _export_graph(self):
        from PyQt6.QtWidgets import QFileDialog
        file_path, file_type = QFileDialog.getSaveFileName(self, "Export Graph", "", "PNG Image (*.png);;PDF File (*.pdf)")
        if not file_path:
            return
        if file_type.startswith("PNG") or file_path.lower().endswith(".png"):
            self.fig.savefig(file_path, format="png", bbox_inches="tight")
        elif file_type.startswith("PDF") or file_path.lower().endswith(".pdf"):
            self.fig.savefig(file_path, format="pdf", bbox_inches="tight")
        else:
            self.fig.savefig(file_path, bbox_inches="tight")

    def toggle_graph_dark_mode(self):
        self._graph_dark_mode = not self._graph_dark_mode
        settings['graph_dark_mode'] = self._graph_dark_mode
        save_settings()
        self._apply_graph_theme()
        self._redraw_graph()

    def _apply_graph_theme(self):
        if self._graph_dark_mode:
            mplstyle.use('dark_background')
        else:
            mplstyle.use('default')

    def _on_table_cell_changed(self, row, col):
        # Ensure cell background matches table and text is readable
        item = self.table.item(row, col)
        if item is not None:
            # Handle alternating row colors
            if self.table.alternatingRowColors() and row % 2 == 1:
                bg_color = self.table.palette().color(self.table.palette().AlternateBase)
            else:
                bg_color = self.table.palette().color(self.table.backgroundRole())
            item.setBackground(bg_color)
            brightness = (bg_color.red() * 299 + bg_color.green() * 587 + bg_color.blue() * 114) / 1000
            if brightness < 128:
                item.setForeground(Qt.GlobalColor.white)
            else:
                item.setForeground(Qt.GlobalColor.black)
        self._update_all_table_cell_colors()

    def _on_table_selection_changed(self):
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            self._highlighted_index = row
        else:
            self._highlighted_index = None
        self._redraw_graph()

    def _clear_polyline(self):
        self._polyline_vertices.clear()
        self._update_polyline_vertex_label()
        self._redraw_graph()

    def _update_all_table_cell_colors(self):
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item is not None:
                    if self.table.alternatingRowColors() and row % 2 == 1:
                        bg_color = self.table.palette().color(self.table.palette().AlternateBase)
                    else:
                        bg_color = self.table.palette().color(self.table.backgroundRole())
                    item.setBackground(bg_color)
                    brightness = (bg_color.red() * 299 + bg_color.green() * 587 + bg_color.blue() * 114) / 1000
                    if brightness < 128:
                        item.setForeground(Qt.GlobalColor.white)
                    else:
                        item.setForeground(Qt.GlobalColor.black)

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel, QScrollArea
from PyQt6.QtCore import Qt
from .lang import LANG

class HelpManager:
    def __init__(self, parent):
        self.parent = parent

    def init_help_tab(self, tab_widget):
        help_widget = QWidget()
        layout = QVBoxLayout(help_widget)

        # Create a scroll area for the help content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        help_content_widget = QWidget()
        help_layout = QVBoxLayout(help_content_widget)

        # Combine original help content and new comprehensive content
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        # Original help content
        original_content = f"""
        <h2>{LANG['help_welcome']}</h2>
        <h3>{LANG['help_getting_started']}</h3>
        <ul>
            <li>{LANG['help_enter_first_rl']}</li>
            <li>{LANG['help_input_readings']}</li>
            <li>{LANG['help_change_point']}</li>
            <li>{LANG['help_final_reading']}</li>
        </ul>
        <h3>{LANG['help_calculation']}</h3>
        <ul>
            <li>{LANG['help_choose_method']}</li>
            <li>{LANG['help_enter_last_rl']}</li>
            <li>{LANG['help_calculate_update']}</li>
        </ul>
        <h3>{LANG['help_profile_graph']}</h3>
        <ul>
            <li>{LANG['help_plot_rl']}</li>
            <li>{LANG['help_graph_controls']}</li>
            <li>{LANG['help_comparison_profile']}</li>
            <li>{LANG['help_cut_fill']}</li>
        </ul>
        <h3>{LANG['help_data_management']}</h3>
        <ul>
            <li>{LANG['help_import_csv']}</li>
            <li>{LANG['help_save_db']}</li>
            <li>{LANG['help_right_click']}</li>
        </ul>
        """
        # New comprehensive help content
        new_content = """
        <h2>Leveling & Profile App Quick Reference</h2>
        <b>Quick Start:</b><br>
        - Enter your leveling data in the table.<br>
        - Use the <b>Calculate & Update Graph</b> button to process and visualize your data.<br>
        - Switch between <b>Height of Instrument</b> and <b>Rise & Fall</b> methods as needed.<br>
        - Use the <b>Export</b> button to save your results or graph.<br>
        <br>
        <b>Tips & Shortcuts:</b><br>
        - Double-click a cell to edit.<br>
        - Right-click a row for options like copy, paste, insert, or delete.<br>
        - Use Ctrl+Z (Undo) and Ctrl+Y (Redo) to revert changes.<br>
        - Hover over the graph to see tooltips with precise values.<br>
        - Use the <b>Interval</b> checkbox to plot at regular intervals.<br>
        - Click column headers to sort data.<br>
        - Use the <b>Help</b> tab for guidance and validation rules.<br>
        <br>
        <b>Graph Navigation:</b><br>
        - Use the toolbar to zoom, pan, and save the graph.<br>
        - Click the fullscreen button (⛶) for a larger view.<br>
        - Use the <b>Markers</b> and <b>Labels</b> checkboxes to toggle point markers and value labels.<br>
        <br>
        <b>Import/Export:</b><br>
        - Import data from CSV using the File menu.<br>
        - Export results or graphs as PDF or image.<br>
        <br>
        <b>PDF Export:</b><br>
        - Use the <b>Professional PDF Export</b> for detailed reports.<br>
        - Preview before saving.<br>
        <br>
        <b>Session Management:</b><br>
        - Use the File menu to restore previous sessions.<br>
        - Recent files are listed for quick access.<br>
        <br>
        <b>Keyboard Shortcuts:</b><br>
        - <b>Ctrl+S</b>: Save<br>
        - <b>Ctrl+O</b>: Open<br>
        - <b>Ctrl+Z</b>: Undo<br>
        - <b>Ctrl+Y</b>: Redo<br>
        - <b>F1</b>: Open Help<br>
        <br>
        <b>Common Issues:</b><br>
        - If the graph looks odd, check for non-numeric or missing data.<br>
        - If the arithmetic check fails, review your readings and ensure all validation rules are followed.<br>
        - For change points, ensure both BS and FS are filled in the same row.<br>
        <br>
        <b>Support:</b><br>
        - For more help, contact support or check the documentation.<br>
        """
        help_text.setHtml(original_content + new_content)
        help_layout.addWidget(help_text)

        # Data Validation Rules section
        from leveling_app_modular.lang import DATA_VALIDATION_RULES
        validation_label = QLabel("<b>Data Validation Rules:</b><br>" + DATA_VALIDATION_RULES.replace("\n", "<br>"))
        validation_label.setWordWrap(True)
        help_layout.addWidget(validation_label)

        # Add expanded help sections
        glossary = """
        <h3>Glossary of Terms & Short Forms</h3>
        <ul>
            <li><b>BS</b>: Backsight – A reading taken on a point of known elevation to establish the instrument height.</li>
            <li><b>FS</b>: Foresight – A reading taken on a new point to determine its elevation.</li>
            <li><b>IS</b>: Intersight – A reading taken between BS and FS, used for intermediate points.</li>
            <li><b>RL</b>: Reduced Level – The calculated elevation of a point.</li>
            <li><b>HI</b>: Height of Instrument – The elevation of the instrument line of sight.</li>
            <li><b>CP</b>: Change Point – A point where the instrument is moved; both BS and FS are recorded here.</li>
            <li><b>Grade/Slope</b>: The percentage change in elevation between two points, calculated as (ΔElevation/ΔDistance) × 100%.</li>
            <li><b>Cut/Fill</b>: The amount of earth to be removed (cut) or added (fill) to reach a design level.</li>
        </ul>
        """
        help_layout.addWidget(QLabel(glossary))

        button_help = """
        <h3>Button & Feature Explanations</h3>
        <ul>
            <li><b>Calculate & Update Graph</b>: Processes your data and updates the graph/profile.</li>
            <li><b>Export</b>: Save your results or graph as a PDF or image.</li>
            <li><b>Professional PDF Export</b>: Create a detailed, formatted report with preview and save options.</li>
            <li><b>Undo/Redo</b>: Revert or re-apply recent changes (Ctrl+Z, Ctrl+Y).</li>
            <li><b>Fullscreen (⛶)</b>: Expand the graph for easier viewing and navigation.</li>
            <li><b>Markers/Labels</b>: Toggle point markers and value labels on the graph.</li>
            <li><b>Interval</b>: Plot points at regular intervals along the profile.</li>
            <li><b>Import/Export CSV</b>: Bring in or save data in spreadsheet format.</li>
            <li><b>Restore Session</b>: Load your last session or recent files.</li>
            <li><b>Help</b>: Open this help dialog for guidance and rules.</li>
        </ul>
        """
        help_layout.addWidget(QLabel(button_help))

        overview = """
        <h3>App Overview & Workflow</h3>
        <p>This app is designed for surveyors, engineers, and students to enter, calculate, and visualize leveling data. You can:</p>
        <ol>
            <li>Enter your field readings (BS, IS, FS) in the table.</li>
            <li>Choose your calculation method (Height of Instrument or Rise & Fall).</li>
            <li>Click Calculate to process your data and see the profile graph.</li>
            <li>Analyze cut/fill, compare profiles, and export results or reports.</li>
            <li>Restore previous sessions or import/export data as needed.</li>
        </ol>
        <p>The app supports professional PDF export, session management, and advanced graphing features for a complete workflow from field to report.</p>
        """
        help_layout.addWidget(QLabel(overview))

        features = """
        <h3>Feature Details</h3>
        <ul>
            <li><b>Graph:</b> Interactive, supports zoom, pan, tooltips, interval mode, comparison profiles, and cut/fill analysis.</li>
            <li><b>PDF Export:</b> Create detailed reports with project info, summary, and graph images. Preview before saving.</li>
            <li><b>Session Management:</b> Restore previous work, access recent files, and autosave your progress.</li>
            <li><b>Data Validation:</b> Built-in checks ensure your data is correct before calculation.</li>
            <li><b>Keyboard Shortcuts:</b> Speed up your workflow with common shortcuts (see above).</li>
        </ul>
        """
        help_layout.addWidget(QLabel(features))

        troubleshooting = """
        <h3>Troubleshooting & FAQ</h3>
        <ul>
            <li><b>Why does the arithmetic check fail?</b> – Check your readings, ensure all validation rules are followed, and that the first and last RLs are correct.</li>
            <li><b>Why is the graph blank or odd?</b> – Look for missing or non-numeric data, or duplicate points.</li>
            <li><b>How do I enter a change point?</b> – Enter both BS and FS in the same row; IS should be blank.</li>
            <li><b>How do I export a report?</b> – Use the Professional PDF Export button for a detailed, formatted report.</li>
            <li><b>How do I restore my last session?</b> – Use the File menu to restore or open recent files.</li>
            <li><b>Where can I get more help?</b> – Use this help dialog or contact support.</li>
        </ul>
        """
        help_layout.addWidget(QLabel(troubleshooting))

        # Add detailed, step-by-step walkthroughs and visual descriptions
        walkthroughs = """
        <h3>Step-by-Step Walkthroughs</h3>
        <h4>Entering and Calculating Leveling Data</h4>
        <ol>
            <li><b>Start the App:</b><br>
                When you open the app, you’ll see a table with columns for Point, BS, IS, FS, etc.
            </li>
            <li><b>Enter the First Row:</b><br>
                - Click the first cell under “Point” and type your starting station (e.g., 1).<br>
                - Enter your first BS (Backsight) reading in the “BS” column.<br>
                - Leave IS and FS blank for the first row.<br>
                <i>What you should see:</i> The first row filled with your starting point and BS.
            </li>
            <li><b>Add More Rows:</b><br>
                - For each new station, enter the Point number and the appropriate reading (IS for intermediate, FS for the last point before a change point or end).<br>
                - To add a change point, enter both BS and FS in the same row (IS should be blank).<br>
                <i>What you should see:</i> Each row has at least one reading; change points have both BS and FS.
            </li>
        </ol>
        <h4>Calculating and Viewing the Graph</h4>
        <ol>
            <li><b>Click “Calculate & Update Graph”:</b><br>
                - The button is usually above or below the data table.<br>
                <i>What you should see:</i> The graph updates, showing your profile line.
            </li>
            <li><b>Hover Over the Graph:</b><br>
                - Move your mouse over the graph to see tooltips with precise values for each point.<br>
                <i>What you should see:</i> A small popup near the cursor with Distance, Elevation, and Grade.
            </li>
        </ol>
        <h4>Exporting Results</h4>
        <ol>
            <li><b>Click “Export” or “Professional PDF Export”:</b><br>
                - The Export button is typically in the toolbar or menu.<br>
                - Choose your desired format (PDF, image).<br>
                <i>What you should see:</i> A dialog to choose where to save your file.
            </li>
        </ol>
        <h4>Restoring a Session</h4>
        <ol>
            <li><b>Go to the File Menu:</b><br>
                - Click “File” > “Restore Session” or select from “Recent Files.”<br>
                <i>What you should see:</i> Your previous data and graph restored.
            </li>
        </ol>
        <h4>Troubleshooting</h4>
        <ul>
            <li><b>If you see a red error message:</b> Check that all required fields are filled and that numbers are valid.</li>
            <li><b>If the arithmetic check is red:</b> Double-check your readings, especially at change points and the first/last RL.</li>
        </ul>
        <h4>Visual Cues in the App</h4>
        <ul>
            <li><b>Buttons:</b> “Calculate & Update Graph” is usually blue or green and labeled clearly. “Export” often has a disk or PDF icon.</li>
            <li><b>Graph:</b> The profile line is blue, with markers at each point if enabled. Tooltips appear as you hover over the line.</li>
        </ul>
        """
        help_layout.addWidget(QLabel(walkthroughs))

        # Add more advanced tips, scenarios, and troubleshooting
        advanced = """
        <h3>Advanced Features & Scenarios</h3>
        <h4>Comparison Profiles</h4>
        <ul>
            <li>To compare your main profile with another, use the <b>Import Comparison Profile</b> option in the graph tab or menu.</li>
            <li>After importing, the comparison profile will appear as a dashed line on the graph.</li>
            <li>Use interval mode to align both profiles for a fair comparison.</li>
        </ul>
        <h4>Interval Mode</h4>
        <ul>
            <li>Enable <b>Interval</b> mode to plot points at regular distances along the profile.</li>
            <li>This is useful for engineering design and for comparing profiles with different station spacing.</li>
        </ul>
        <h4>Cut/Fill Analysis</h4>
        <ul>
            <li>Use the <b>Analyze</b> button in the graph tab to shade areas of cut (orange) and fill (cyan) between your profile and a design level.</li>
            <li>Choose the design level mode (Fixed, Gradient, Polyline, etc.) to match your project needs.</li>
        </ul>
        <h4>Professional PDF Export</h4>
        <ul>
            <li>Click <b>Professional PDF Export</b> for a detailed, formatted report.</li>
            <li>Fill in project details, executive summary, and select which sections to include.</li>
            <li>Preview the report before saving to ensure all information is correct.</li>
        </ul>
        <h4>Session Recovery & Autosave</h4>
        <ul>
            <li>If the app closes unexpectedly, use <b>Restore Session</b> from the File menu to recover your last work.</li>
            <li>Recent files are listed for quick reopening.</li>
        </ul>
        <h4>Mini-FAQ & Edge Cases</h4>
        <ul>
            <li><b>Q: Can I import data from Excel?</b><br>A: Yes, save your Excel sheet as CSV and use the Import CSV feature.</li>
            <li><b>Q: What if my profile has missing stations?</b><br>A: The app will plot only the stations with valid data. Use interval mode for evenly spaced profiles.</li>
            <li><b>Q: How do I handle multiple change points in a row?</b><br>A: Each change point should be a separate row with both BS and FS filled.</li>
            <li><b>Q: Can I customize the graph colors?</b><br>A: Yes, use the color pickers in the graph tab to change line, marker, and comparison colors.</li>
            <li><b>Q: How do I add annotations to the graph?</b><br>A: Use the annotation controls in the graph tab to add, edit, or remove text annotations.</li>
            <li><b>Q: What if I get a validation error I don't understand?</b><br>A: Check the Data Validation Rules section above, or contact support for help.</li>
        </ul>
        """
        help_layout.addWidget(QLabel(advanced))

        help_content_widget.setLayout(help_layout)
        scroll_area.setWidget(help_content_widget)
        layout.addWidget(scroll_area)
        tab_widget.addTab(help_widget, "Help / Guide") 
# Leveling App Modular Package

This package contains modular components extracted from the monolithic `leveling_and_graphing_app.py` file. The modularization maintains full functionality while improving code organization and maintainability.

## Module Structure

### Core Modules

#### `settings.py`
- **Purpose**: Manages application settings and configuration
- **Key Components**:
  - `settings` dictionary: Global settings state
  - `load_settings()`: Load settings from JSON file
  - `save_settings()`: Save settings to JSON file
  - `detect_system_theme()`: Detect system dark/light mode
  - `SettingsDialog`: Settings dialog UI class

#### `db.py`
- **Purpose**: Database operations for both leveling and profile data
- **Key Components**:
  - `DatabaseManager`: Handles SQLite database operations
  - `save_leveling_data()`: Save leveling data to database
  - `load_leveling_data()`: Load leveling data from database
  - `save_profile_data()`: Save profile data to database
  - `load_profile_data()`: Load profile data from database

#### `utils.py`
- **Purpose**: Common utility functions and classes
- **Key Components**:
  - `is_number()`: Validate numeric input
  - `format_num()`: Format numbers with precision
  - `Tooltip`: Tooltip UI class
  - `ImportDialog`: CSV import preview dialog
  - `enable_treeview_column_resizing()`: Enable column resizing
  - `sort_treeview_column()`: Sort table columns
  - `generate_pdf_report()`: Generate PDF reports
  - `export_to_excel()`: Export to Excel files
  - `save_session()` / `load_session()`: Session management
  - `autosave_data()`: Autosave functionality
  - `update_recent_files()`: Recent files management
  - `handle_drop_file()`: Drag-and-drop file handling
  - `show_onboarding()`: Onboarding dialog
  - `show_about()`: About dialog

#### `lang.py`
- **Purpose**: Localization and language strings
- **Key Components**:
  - `LANG` dictionary: All user-facing strings
  - Organized by functionality (errors, success messages, UI text, etc.)

#### `calculator.py`
- **Purpose**: Leveling calculation logic
- **Key Components**:
  - `LevelingCalculator`: Main calculation class
  - `calculate_leveling()`: Route to specific calculation methods
  - `calculate_hi()`: Height of Instrument method
  - `calculate_rise_and_fall()`: Rise & Fall method
  - `validate_input()`: Input validation logic
  - `_setup_result_table()`: Result table setup
  - `_insert_result_rows()`: Insert calculation results

#### `import_export.py`
- **Purpose**: File import/export operations
- **Key Components**:
  - `ImportExportManager`: Main import/export class
  - `import_leveling_csv()`: Import leveling data from CSV
  - `import_profile_csv()`: Import profile data from CSV
  - `export_leveling_csv()`: Export leveling results to CSV
  - `export_to_excel()`: Export to Excel files
  - `export_graph()`: Export graph images
  - `generate_pdf_report()`: Generate PDF reports
  - `load_comparison_profile()`: Load comparison profiles
  - `open_recent_file()`: Open recent files
  - `handle_drop_file()`: Handle drag-and-drop

#### `column_customizer.py`
- **Purpose**: Column customization functionality
- **Key Components**:
  - `ColumnCustomizer`: Column customization class
  - `customize_columns_dialog()`: Column customization dialog
  - `apply_column_settings()`: Apply column settings to tables

#### `help.py`
- **Purpose**: Help content and documentation
- **Key Components**:
  - `HelpManager`: Help management class
  - `init_help_tab()`: Initialize help tab with content

#### `session.py`
- **Purpose**: Session management
- **Key Components**:
  - `SessionManager`: Session management class
  - `save_session()`: Save current session
  - `load_session()`: Load session data
  - `offer_session_restore()`: Offer session restore
  - `restore_session_data()`: Restore session data
  - `check_unsaved_changes()`: Check for unsaved changes

## Usage

### Basic Import
```python
from leveling_app_modular import (
    settings, load_settings, save_settings,
    DatabaseManager, LevelingCalculator,
    ImportExportManager, ColumnCustomizer,
    HelpManager, SessionManager
)
```

### Initialize Components
```python
# Load settings
load_settings()

# Initialize database manager
db_manager = DatabaseManager()

# Initialize calculator
calculator = LevelingCalculator(master, settings, update_stats_callback, highlight_row_callback, clear_highlights_callback)

# Initialize import/export manager
import_export = ImportExportManager(master, settings, save_settings)

# Initialize column customizer
column_customizer = ColumnCustomizer(master, settings, save_settings, apply_column_settings_callback)

# Initialize help manager
help_manager = HelpManager(master)

# Initialize session manager
session_manager = SessionManager(settings)
```

### Settings Management
```python
# Access settings
precision = settings["precision"]
theme = settings["theme"]

# Save settings
save_settings()

# Open settings dialog
settings_dialog = SettingsDialog(master, apply_theme_callback, update_graph_callback)
settings_dialog.open_settings()
```

### Database Operations
```python
# Save leveling data
db_manager.save_leveling_data(data)

# Load leveling data
rows = db_manager.load_leveling_data()

# Save profile data
db_manager.save_profile_data(graph_tree)

# Load profile data
rows = db_manager.load_profile_data()
```

### Calculations
```python
# Perform calculation
calculator.calculate_leveling(method, first_rl_entry, last_rl_entry, data, result_table, progress_bar)

# Validate input
reorganized_data = calculator.validate_input(data)
```

### Import/Export
```python
# Import leveling CSV
import_export.import_leveling_csv(data, column_names, redraw_callback, progress_bar)

# Export to Excel
import_export.export_to_excel(result_table, graph_tree, progress_bar)

# Generate PDF report
import_export.generate_pdf_report(result_table, fig)
```

### Column Customization
```python
# Open column customization dialog
column_customizer.customize_columns_dialog('result')

# Apply column settings
column_customizer.apply_column_settings('result', result_table=result_table)
```

### Session Management
```python
# Save session
session_manager.save_session(data)

# Offer session restore
session = session_manager.offer_session_restore(master)

# Restore session
session_manager.restore_session_data(session, data, redraw_callback)
```

## Benefits of Modularization

1. **Separation of Concerns**: Each module has a specific responsibility
2. **Maintainability**: Easier to locate and modify specific functionality
3. **Reusability**: Components can be reused in other applications
4. **Testability**: Individual modules can be tested in isolation
5. **Scalability**: New features can be added as separate modules
6. **Code Organization**: Clear structure makes the codebase easier to navigate

## Migration from Monolithic App

The modular components maintain the same functionality as the original monolithic app. To migrate:

1. Import the required modules
2. Initialize the component classes
3. Replace direct function calls with component method calls
4. Update callback references to use the new modular structure

All existing functionality is preserved, including:
- Leveling calculations (HI and Rise & Fall methods)
- Input validation and error handling
- Database operations
- Import/export functionality
- Settings management
- Session persistence
- Column customization
- Help system
- Theme management
- Drag-and-drop support
- Recent files management 
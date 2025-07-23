import pytest
from PyQt6.QtWidgets import QApplication
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from main_qt import MainWindow

@pytest.fixture(scope="session")
def app(request):
    """Session-wide Qt Application."""
    q_app = QApplication.instance()
    if q_app is None:
        q_app = QApplication([])
    return q_app

@pytest.fixture
def main_window(app):
    """Create a MainWindow instance for each test."""
    window = MainWindow()
    yield window
    window.close()

def test_app_startup(main_window):
    """Test that the main window starts up without errors."""
    assert main_window is not None
    assert main_window.windowTitle() == "Leveling & Graphing App (PyQt)"

def test_calculation_hi(main_window):
    """Test a basic HI calculation."""
    leveling_app = main_window.leveling_app
    leveling_app.first_rl_entry.setText("100.0")
    leveling_app.last_rl_entry.setText("100.3")
    
    leveling_app.table.setItem(0, 1, "1.5") # BS
    leveling_app.table.setItem(1, 3, "1.2") # FS
    
    leveling_app.hi_radio.setChecked(True)
    leveling_app.calculate_button.click()
    
    results_table = leveling_app.results_table
    assert results_table.rowCount() == 2
    
    # Check RL of the second point
    rl_item = results_table.item(1, 5) # RL is in column 5
    assert rl_item is not None
    assert abs(float(rl_item.text()) - 100.3) < 0.001

def test_calculation_rf(main_window):
    """Test a basic Rise & Fall calculation."""
    leveling_app = main_window.leveling_app
    leveling_app.first_rl_entry.setText("50.0")
    leveling_app.last_rl_entry.setText("51.0")
    
    leveling_app.table.setItem(0, 1, "2.0") # BS
    leveling_app.table.setItem(1, 3, "1.0") # FS
    
    leveling_app.rf_radio.setChecked(True)
    leveling_app.calculate_button.click()
    
    results_table = leveling_app.results_table
    assert results_table.rowCount() == 2
    
    # Check RL of the second point
    rl_item = results_table.item(1, 6) # RL is in column 6 for RF
    assert rl_item is not None
    assert abs(float(rl_item.text()) - 51.0) < 0.001

import sqlite3
import logging
from pathlib import Path

class DatabaseManager:
    def __init__(self):
        self.db_file = Path("leveling_data.db")
        self.profile_db_file = Path("profile_data.db")
        self._initialize_databases()

    def _initialize_databases(self):
        """Initializes both SQLite databases and creates tables if they don't exist."""
        try:
            # Leveling database
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS leveling_data (
                    id INTEGER PRIMARY KEY,
                    point TEXT,
                    bs TEXT,
                    is_val TEXT,
                    fs TEXT
                )
            """)
            conn.commit()
            conn.close()

            # Profile database
            conn = sqlite3.connect(self.profile_db_file)
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS profile_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    point TEXT,
                    elevation TEXT,
                    distance TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Could not initialize databases: {e}")
            raise

    def save_leveling_data(self, data):
        """Saves the current data from the input table to the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()
            c.execute("DELETE FROM leveling_data")  # Clear old data
            data_to_save = []
            for row_data in data:
                # Assuming row_data is a list of strings
                if any(row_data):  # Save only non-empty rows
                    data_to_save.append(tuple(row_data))
            c.executemany("INSERT INTO leveling_data (point, bs, is_val, fs) VALUES (?, ?, ?, ?)", data_to_save)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Could not save to database: {e}")
            raise

    def load_leveling_data(self, file_path=None):
        """Loads leveling data from the SQLite database."""
        if not file_path:
            file_path = self.db_file if self.db_file.exists() else None
        if not file_path or not Path(file_path).exists():
            return None
        try:
            conn = sqlite3.connect(file_path)
            c = conn.cursor()
            c.execute("SELECT point, bs, is_val, fs FROM leveling_data ORDER BY id")
            rows = c.fetchall()
            conn.close()
            return rows
        except Exception as e:
            logging.error(f"Could not load from database: {e}")
            raise

    def save_profile_data(self, data):
        """Saves the current profile graph data to the SQLite database."""
        try:
            conn = sqlite3.connect(self.profile_db_file)
            c = conn.cursor()
            c.execute("DELETE FROM profile_data")
            data_to_save = []
            for row in data:
                # Assuming row is a dict with 'point', 'elevation', 'distance'
                if row.get('point') is not None and row.get('elevation') is not None:
                    data_to_save.append((row.get('point'), row.get('elevation'), row.get('distance')))
            c.executemany("INSERT INTO profile_data (point, elevation, distance) VALUES (?, ?, ?)", data_to_save)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Could not save profile data: {e}")
            raise

    def load_profile_data(self, file_path=None):
        """Loads profile data from the SQLite database."""
        if not file_path:
            file_path = self.profile_db_file if self.profile_db_file.exists() else None
        if not file_path or not Path(file_path).exists():
            return None
        try:
            conn = sqlite3.connect(file_path)
            c = conn.cursor()
            c.execute("SELECT point, elevation, distance FROM profile_data ORDER BY id")
            rows = c.fetchall()
            conn.close()
            return rows
        except Exception as e:
            logging.error(f"Could not load profile data: {e}")
            raise

import sqlite3
import os
from datetime import datetime

DB_PATH = "data/betting_intelligence.db"

def get_db_connection():
    """Returns a connection to the SQLite database with row factory enabled."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn

def initialize_db():
    """Initializes the database schema with all 7 required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. fixtures
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fixtures (
            match_id TEXT PRIMARY KEY,
            home TEXT,
            away TEXT,
            league TEXT,
            kickoff TEXT,
            collected_at TEXT
        )
    """)

    # 2. odds
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS odds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            market_name TEXT,
            sub_type_id TEXT,
            selection TEXT,
            odd REAL,
            line TEXT,
            collected_at TEXT,
            FOREIGN KEY (match_id) REFERENCES fixtures(match_id)
        )
    """)

    # 3. match_links
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_links (
            betika_match_id TEXT PRIMARY KEY,
            flashscore_match_id TEXT,
            fs_home TEXT,
            fs_away TEXT,
            confidence REAL,
            FOREIGN KEY (betika_match_id) REFERENCES fixtures(match_id)
        )
    """)

    # 4. ultimate_stats
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ultimate_stats (
            match_id TEXT PRIMARY KEY,
            home_team TEXT,
            away_team TEXT,
            tournament_pair TEXT,
            overall_table TEXT,
            home_table TEXT,
            away_table TEXT,
            over_under_table TEXT,
            ht_ft_table TEXT,
            form_overall_table TEXT,
            form_home_table TEXT,
            form_away_table TEXT,
            ou_all TEXT,
            collected_at TEXT,
            FOREIGN KEY (match_id) REFERENCES fixtures(match_id)
        )
    """)

    # 5. deep_stats
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deep_stats (
            match_id TEXT PRIMARY KEY,
            home_form_last5 TEXT,
            away_form_last5 TEXT,
            h2h_last5 TEXT,
            FOREIGN KEY (match_id) REFERENCES fixtures(match_id)
        )
    """)

    # 6. flashscore_h2h
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flashscore_h2h (
            match_id TEXT PRIMARY KEY,
            home_team_name TEXT,
            away_team_name TEXT,
            h2h_data TEXT,
            FOREIGN KEY (match_id) REFERENCES fixtures(match_id)
        )
    """)

    # 7. match_extras
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_extras (
            betika_match_id TEXT PRIMARY KEY,
            available_tabs TEXT,
            injuries TEXT,
            news TEXT,
            report TEXT,
            lineups TEXT,
            collected_at TEXT,
            FOREIGN KEY (betika_match_id) REFERENCES fixtures(match_id)
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ Database initialized successfully at {DB_PATH}")

if __name__ == "__main__":
    initialize_db()

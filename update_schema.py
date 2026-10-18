from database import get_db_connection

def add_value_bets_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS value_bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            market_name TEXT,
            selection TEXT,
            betika_odd REAL,
            model_probability REAL,
            fair_odd REAL,
            ev_percent REAL,
            confidence TEXT,
            FOREIGN KEY (match_id) REFERENCES fixtures(match_id)
        )
    """)
    conn.commit()
    conn.close()
    print("✅ value_bets table created.")

if __name__ == "__main__":
    add_value_bets_table()

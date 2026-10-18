from database import get_db_connection

def add_columns():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE value_bets ADD COLUMN matches_used INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE value_bets ADD COLUMN confidence_score REAL DEFAULT 0.0")
        conn.commit()
        print("✅ Added 'matches_used' and 'confidence_score' columns.")
    except Exception as e:
        print(f"ℹ️ Columns might already exist (this is fine): {e}")
        
    conn.close()

if __name__ == "__main__":
    add_columns()

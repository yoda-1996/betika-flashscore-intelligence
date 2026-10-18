"""
Adds ht_ft_home_table and ht_ft_away_table columns to ultimate_stats.
"""
from database import get_db_connection

def add_columns():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(ultimate_stats)")
        columns = [col['name'] for col in cursor.fetchall()]
        
        if 'ht_ft_home_table' not in columns:
            cursor.execute("ALTER TABLE ultimate_stats ADD COLUMN ht_ft_home_table TEXT")
            print("✅ Added 'ht_ft_home_table' column")
        else:
            print("✅ Column 'ht_ft_home_table' already exists")
            
        if 'ht_ft_away_table' not in columns:
            cursor.execute("ALTER TABLE ultimate_stats ADD COLUMN ht_ft_away_table TEXT")
            print("✅ Added 'ht_ft_away_table' column")
        else:
            print("✅ Column 'ht_ft_away_table' already exists")
            
        conn.commit()
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_columns()

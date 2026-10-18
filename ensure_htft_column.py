"""
Ensures the ht_ft_table column exists in ultimate_stats table.
"""

from database import get_db_connection

def add_column():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(ultimate_stats)")
        columns = [col['name'] for col in cursor.fetchall()]
        
        if 'ht_ft_table' not in columns:
            cursor.execute("ALTER TABLE ultimate_stats ADD COLUMN ht_ft_table TEXT")
            conn.commit()
            print("✅ Added 'ht_ft_table' column to ultimate_stats")
        else:
            print("✅ Column 'ht_ft_table' already exists")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_column()

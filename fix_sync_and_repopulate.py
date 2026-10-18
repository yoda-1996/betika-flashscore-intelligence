"""
1. Fixes sync_betika_flashscore.py to use Betika ID (b_id) instead of Flashscore ID (fs_id).
2. Clears old broken data for tomorrow.
3. Re-runs Sync and Model.
"""
import subprocess
from database import get_db_connection

def fix_sync_script():
    print("1. Fixing sync_betika_flashscore.py...")
    with open('sync_betika_flashscore.py', 'r') as f:
        content = f.read()

    # Fix 1: ultimate_stats INSERT
    # Change: VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) """, (fs_id, ...
    # To:     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) """, (b_id, ...
    
    # We look for the specific block in ultimate_stats insertion
    old_stats_insert = """VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fs_id, fs_home, fs_away, t_pair,"""
    
    new_stats_insert = """VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                b_id, fs_home, fs_away, t_pair,"""
                
    if old_stats_insert in content:
        content = content.replace(old_stats_insert, new_stats_insert)
        print("   ✅ Fixed ultimate_stats ID")
    else:
        print("   ️ Could not find exact ultimate_stats block to replace")

    # Fix 2: flashscore_h2h INSERT
    # Change: VALUES (?, ?, ?, ?) """, (fs_id, fs_home, fs_away, h2h_data))
    # To:     VALUES (?, ?, ?, ?) """, (b_id, fs_home, fs_away, h2h_data))
    
    old_h2h_insert = """VALUES (?, ?, ?, ?)
                """, (fs_id, fs_home, fs_away, h2h_data))"""
                
    new_h2h_insert = """VALUES (?, ?, ?, ?)
                """, (b_id, fs_home, fs_away, h2h_data))"""
                
    if old_h2h_insert in content:
        content = content.replace(old_h2h_insert, new_h2h_insert)
        print("   ✅ Fixed flashscore_h2h ID")
    else:
        print("   ⚠️ Could not find exact h2h block to replace")

    with open('sync_betika_flashscore.py', 'w') as f:
        f.write(content)

def clear_old_data():
    print("\n2. Clearing old/broken data for tomorrow...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get betika IDs for tomorrow
    cursor.execute("SELECT betika_match_id FROM match_links ml JOIN fixtures f ON ml.betika_match_id = f.match_id WHERE date(f.kickoff) = date('now', '+1 day')")
    ids = [row['betika_match_id'] for row in cursor.fetchall()]
    
    if ids:
        # Delete from tables where match_id matches these betika IDs
        cursor.execute(f"DELETE FROM ultimate_stats WHERE match_id IN ({','.join(['?']*len(ids))})", ids)
        cursor.execute(f"DELETE FROM flashscore_h2h WHERE match_id IN ({','.join(['?']*len(ids))})", ids)
        cursor.execute(f"DELETE FROM match_extras WHERE betika_match_id IN ({','.join(['?']*len(ids))})", ids)
        conn.commit()
        print(f"   ✅ Cleared data for {len(ids)} matches")
    else:
        print("   ️ No matches found for tomorrow to clear")
        
    conn.close()

def run_pipeline():
    print("\n3. Running Sync Script...")
    subprocess.run(["python", "sync_betika_flashscore.py"])
    
    print("\n4. Running Probability Model...")
    subprocess.run(["python", "probability_model.py"])

if __name__ == "__main__":
    fix_sync_script()
    clear_old_data()
    run_pipeline()
    print("\n🎉 DONE! Check your dashboard.")

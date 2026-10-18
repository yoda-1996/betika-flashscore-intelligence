"""
Fixes the sync script to use the correct tournament pair format: id:stage_id
Then clears old data and re-runs the sync.
"""
import os
from database import get_db_connection

print("="*60)
print("FIXING TOURNAMENT PAIR FORMAT")
print("="*60)

# 1. Fix the sync script
print("\n1. Fixing sync_betika_flashscore.py...")
with open('sync_betika_flashscore.py', 'r') as f:
    content = f.read()

# Find and replace the tournament pair logic
old_logic = """                t_id = c.get('id')
                s_id = c.get('season_id', c.get('id'))
                pair = f"{t_id}:{s_id}" if t_id and s_id else None"""

new_logic = """                t_id = c.get('id')
                stage_id = c.get('stage_id')
                pair = f"{t_id}:{stage_id}" if t_id and stage_id else None"""

if old_logic in content:
    content = content.replace(old_logic, new_logic)
    print("   ✅ Fixed tournament pair to use stage_id")
else:
    print("   ⚠️ Could not find exact logic to replace")

with open('sync_betika_flashscore.py', 'w') as f:
    f.write(content)

# 2. Clear old data
print("\n2. Clearing old ultimate_stats data...")
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("DELETE FROM ultimate_stats")
cursor.execute("DELETE FROM match_extras")
conn.commit()
conn.close()
print("   ✅ Cleared old data")

# 3. Re-run sync
print("\n3. Re-running sync script...")
os.system("python sync_betika_flashscore.py")

print("\n" + "="*60)
print("DONE! Now run:")
print("  python probability_model.py")
print("  streamlit run dashboard.py")
print("="*60)

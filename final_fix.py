import os
from database import get_db_connection

print("="*50)
print("STEP 1: Fixing sync_betika_flashscore.py")
print("="*50)

# Read the file
with open('sync_betika_flashscore.py', 'r') as f:
    code = f.read()

# Replace the wrong ID (fs_id) with the right ID (b_id) in the specific lines
# 1. For Ultimate Stats
code = code.replace("fs_id, fs_home, fs_away, t_pair,", "b_id, fs_home, fs_away, t_pair,")

# 2. For H2H Data
code = code.replace("(fs_id, fs_home, fs_away, h2h_data)", "(b_id, fs_home, fs_away, h2h_data)")

# Save the file
with open('sync_betika_flashscore.py', 'w') as f:
    f.write(code)
print("✅ Code fixed successfully.")

print("\n" + "="*50)
print("STEP 2: Clearing old/broken data")
print("="*50)

conn = get_db_connection()
c = conn.cursor()

# We clear the tables that had the wrong IDs
# This forces the script to re-fetch and save them correctly
c.execute("DELETE FROM ultimate_stats")
c.execute("DELETE FROM flashscore_h2h")
c.execute("DELETE FROM match_extras") 

conn.commit()
conn.close()
print("✅ Database tables cleared.")

print("\n" + "="*50)
print("STEP 3: Running Sync and Model")
print("="*50)

print("Running Sync (this will take a few minutes)...")
os.system("python sync_betika_flashscore.py")

print("\nRunning Probability Model...")
os.system("python probability_model.py")

print("\n" + "="*50)
print(" ALL DONE!")
print("Now run: streamlit run dashboard.py")
print("="*50)

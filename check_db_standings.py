import sqlite3
import json
from database import get_db_connection

# Use the AS Roma vs Genoa match from your screenshot
FS_ID = "6TjFErJ0"  # Flashscore ID

print("="*60)
print("CHECKING DATABASE FOR STANDINGS DATA")
print("="*60)

conn = get_db_connection()
cursor = conn.cursor()

# First, find the Betika match_id from match_links
print(f"\n1. Looking up Betika match_id for Flashscore ID: {FS_ID}")
cursor.execute("SELECT betika_match_id FROM match_links WHERE flashscore_match_id = ?", (FS_ID,))
link = cursor.fetchone()

if not link:
    print(f"❌ No link found for Flashscore ID: {FS_ID}")
    conn.close()
    exit()

betika_id = link['betika_match_id']
print(f"✅ Found Betika match_id: {betika_id}")

# Now check ultimate_stats with the correct ID
print(f"\n2. Checking ultimate_stats for betika_match_id: {betika_id}")
cursor.execute("SELECT * FROM ultimate_stats WHERE match_id = ?", (betika_id,))
row = cursor.fetchone()

if row:
    print(f"✅ Found ultimate_stats!")
    print(f"   home_team: {row['home_team']}")
    print(f"   away_team: {row['away_team']}")
    print(f"   tournament_pair: {row['tournament_pair']}")
    
    # Check each standings column
    for col in ['overall_table', 'home_table', 'away_table', 'form_overall_table', 'ou_all']:
        val = row[col]
        if val:
            print(f"\n   {col}: {len(val)} chars")
            try:
                data = json.loads(val)
                print(f"      Type: {type(data)}")
                if isinstance(data, dict):
                    print(f"      Keys: {list(data.keys())[:10]}")
                    if 'standings' in data:
                        print(f"      Has 'standings' key: YES (length: {len(data['standings'])})")
                        if data['standings']:
                            print(f"      First item keys: {list(data['standings'][0].keys())}")
                elif isinstance(data, list):
                    print(f"      Length: {len(data)}")
                    if data:
                        print(f"      First item keys: {list(data[0].keys())}")
            except Exception as e:
                print(f"      JSON parse error: {e}")
                print(f"      First 200 chars: {val[:200]}")
        else:
            print(f"\n   ❌ {col}: EMPTY")
else:
    print(f"❌ No ultimate_stats found for betika_match_id: {betika_id}")

conn.close()

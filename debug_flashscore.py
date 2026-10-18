"""
Debug script to inspect Flashscore data for a specific match.
"""

import sqlite3
import json
import requests
from database import get_db_connection

# Test with Brentford vs Liverpool (match_id from your screenshot)
MATCH_ID = "72221314"

print("="*60)
print(f"DEBUGGING MATCH ID: {MATCH_ID}")
print("="*60)

# 1. Check what's in the database
conn = get_db_connection()
cursor = conn.cursor()

print("\n1. CHECKING match_links table...")
cursor.execute("SELECT * FROM match_links WHERE betika_match_id = ?", (MATCH_ID,))
link = cursor.fetchone()
if link:
    print(f"✅ Found link: {dict(link)}")
    fs_id = link['flashscore_match_id']
else:
    print("❌ No link found")
    exit()

print("\n2. CHECKING ultimate_stats table...")
cursor.execute("SELECT * FROM ultimate_stats WHERE match_id = ?", (MATCH_ID,))
stats = cursor.fetchone()
if stats:
    stats_dict = dict(stats)
    print(f"✅ Found stats. overall_table length: {len(stats_dict.get('overall_table', '') or '')}")
    print(f"   ou_all length: {len(stats_dict.get('ou_all', '') or '')}")
    # Show first 200 chars of overall_table to see structure
    if stats_dict.get('overall_table'):
        print(f"\n   overall_table preview: {stats_dict['overall_table'][:200]}")
else:
    print("❌ No stats found")

print("\n3. CHECKING deep_stats table...")
cursor.execute("SELECT * FROM deep_stats WHERE match_id = ?", (MATCH_ID,))
deep = cursor.fetchone()
if deep:
    print(f"✅ Found deep stats: {dict(deep)}")
else:
    print("❌ No deep stats found")

print("\n4. CHECKING flashscore_h2h table...")
cursor.execute("SELECT * FROM flashscore_h2h WHERE match_id = ?", (MATCH_ID,))
h2h = cursor.fetchone()
if h2h:
    h2h_dict = dict(h2h)
    print(f"✅ Found H2H. Data length: {len(h2h_dict.get('h2h_data', '') or '')}")
    if h2h_dict.get('h2h_data'):
        print(f"\n   h2h_data preview: {h2h_dict['h2h_data'][:300]}")
else:
    print("❌ No H2H found")

print("\n5. CHECKING match_extras table...")
cursor.execute("SELECT * FROM match_extras WHERE betika_match_id = ?", (MATCH_ID,))
extras = cursor.fetchone()
if extras:
    extras_dict = dict(extras)
    print(f"✅ Found extras.")
    print(f"   available_tabs: {extras_dict.get('available_tabs')}")
    print(f"   injuries length: {len(extras_dict.get('injuries', '') or '')}")
    print(f"   lineups length: {len(extras_dict.get('lineups', '') or '')}")
else:
    print("❌ No extras found")

conn.close()

# 2. Test Flashscore API directly
print("\n" + "="*60)
print("TESTING FLASHSCORE API DIRECTLY")
print("="*60)

FS_BASE = "http://localhost:8000"

print(f"\n6. Fetching H2H for match {fs_id}...")
try:
    resp = requests.get(f"{FS_BASE}/matches/h2h", params={"match": fs_id}, timeout=10)
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        print(f"   Full response (first 500 chars): {json.dumps(data, indent=2)[:500]}")
    else:
        print(f"   Error: {resp.text[:200]}")
except Exception as e:
    print(f"   Error: {e}")

print(f"\n7. Fetching tournament standings...")
# We need the tournament ID first
try:
    resp = requests.get(f"{FS_BASE}/matches/details", params={"match": fs_id}, timeout=10)
    if resp.status_code == 200:
        details = resp.json()
        print(f"   Details keys: {list(details.keys()) if isinstance(details, dict) else 'Not a dict'}")
        if 'tournament' in details:
            tournament_id = details['tournament'].get('id') or details['tournament'].get('slug')
            print(f"   Tournament ID: {tournament_id}")
            
            # Now fetch standings
            if tournament_id:
                resp2 = requests.get(f"{FS_BASE}/tournaments/standings", params={"tournament": tournament_id}, timeout=10)
                print(f"   Standings status: {resp2.status_code}")
                if resp2.status_code == 200:
                    standings = resp2.json()
                    print(f"   Standings keys: {list(standings.keys()) if isinstance(standings, dict) else 'Not a dict'}")
                    print(f"   Standings preview: {json.dumps(standings, indent=2)[:500]}")
except Exception as e:
    print(f"   Error: {e}")

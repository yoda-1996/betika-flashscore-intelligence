"""
Fixes ALL ID mismatches in the database.
Changes flashscore_h2h, ultimate_stats, and match_extras to use Betika match_id.
"""
import json
import requests
import time
from database import get_db_connection

API = "http://localhost:8000"

def fix_id_mismatches():
    print("="*60)
    print("FIXING ALL ID MISMATCHES")
    print("="*60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all match links
    cursor.execute("SELECT betika_match_id, flashscore_match_id FROM match_links")
    links = cursor.fetchall()
    
    print(f"Processing {len(links)} links...")
    
    # 1. Fix flashscore_h2h
    print("\n1. Fixing flashscore_h2h IDs...")
    fixed_h2h = 0
    for link in links:
        betika_id = link['betika_match_id']
        fs_id = link['flashscore_match_id']
        cursor.execute("UPDATE flashscore_h2h SET match_id = ? WHERE match_id = ?", (betika_id, fs_id))
        if cursor.rowcount > 0:
            fixed_h2h += 1
    conn.commit()
    print(f"   ✅ Fixed {fixed_h2h} H2H records")
    
    # 2. Fix ultimate_stats IDs and re-fetch O/U data
    print("\n2. Fixing ultimate_stats IDs and re-fetching O/U data...")
    fixed_stats = 0
    OU_LINES = ['0.5', '1.5', '2.5', '3.5', '4.5', '5.5']
    
    for link in links:
        betika_id = link['betika_match_id']
        fs_id = link['flashscore_match_id']
        
        # Get the tournament_pair from the old record
        cursor.execute("SELECT tournament_pair FROM ultimate_stats WHERE match_id = ?", (fs_id,))
        row = cursor.fetchone()
        
        if row and row['tournament_pair']:
            tournament_pair = row['tournament_pair']
            
            # Re-fetch O/U data using tournament endpoint
            ou_all = {}
            for line in OU_LINES:
                try:
                    params = {'tournament': tournament_pair, 'type': 'over-under', 'line': line}
                    r = requests.get(f"{API}/tournaments/standings", params=params, timeout=10)
                    time.sleep(0.15)
                    d = r.json()
                    if 'error' not in d and d.get('standings'):
                        ou_all[line] = d
                except Exception:
                    pass
            
            # Get other data from old record
            cursor.execute("""
                SELECT overall_table, home_table, away_table, 
                       form_overall_table, form_home_table, form_away_table,
                       ht_ft_table, ht_ft_home_table, ht_ft_away_table,
                       over_under_table
                FROM ultimate_stats WHERE match_id = ?
            """, (fs_id,))
            old_data = cursor.fetchone()
            
            if old_data:
                # Insert/update with Betika ID
                cursor.execute("""
                    INSERT OR REPLACE INTO ultimate_stats 
                    (match_id, home_team, away_team, tournament_pair, 
                     overall_table, home_table, away_table,
                     over_under_table, ht_ft_table, ht_ft_home_table, ht_ft_away_table,
                     form_overall_table, form_home_table, form_away_table, 
                     ou_all, collected_at)
                    VALUES (?, 
                           (SELECT home_team FROM ultimate_stats WHERE match_id = ?),
                           (SELECT away_team FROM ultimate_stats WHERE match_id = ?),
                           ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    betika_id, fs_id, fs_id, tournament_pair,
                    old_data['overall_table'], old_data['home_table'], old_data['away_table'],
                    old_data['over_under_table'], old_data['ht_ft_table'], 
                    old_data['ht_ft_home_table'], old_data['ht_ft_away_table'],
                    old_data['form_overall_table'], old_data['form_home_table'], 
                    old_data['form_away_table'],
                    json.dumps(ou_all) if ou_all else None,
                    time.strftime('%Y-%m-%dT%H:%M:%S')
                ))
                fixed_stats += 1
                
                if fixed_stats % 10 == 0:
                    print(f"   ...fixed {fixed_stats} stats records")
    
    conn.commit()
    print(f"   ✅ Fixed {fixed_stats} ultimate_stats records with O/U data")
    
    # 3. Fix match_extras
    print("\n3. Fixing match_extras IDs...")
    fixed_extras = 0
    for link in links:
        betika_id = link['betika_match_id']
        fs_id = link['flashscore_match_id']
        # match_extras already uses betika_match_id, so just verify
        cursor.execute("SELECT 1 FROM match_extras WHERE betika_match_id = ?", (betika_id,))
        if not cursor.fetchone():
            cursor.execute("SELECT 1 FROM match_extras WHERE betika_match_id = ?", (fs_id,))
            if cursor.fetchone():
                cursor.execute("UPDATE match_extras SET betika_match_id = ? WHERE betika_match_id = ?", 
                             (betika_id, fs_id))
                fixed_extras += 1
    conn.commit()
    print(f"   ✅ Fixed {fixed_extras} match_extras records")
    
    conn.close()
    print("\n" + "="*60)
    print("✅ ALL ID MISMATCHES FIXED")
    print("="*60)

if __name__ == "__main__":
    fix_id_mismatches()

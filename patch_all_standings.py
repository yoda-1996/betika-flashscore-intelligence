"""
Patch script to fetch standings using /matches/standings endpoint directly.
This bypasses the broken tournament_pair logic.
"""

import requests
import json
import time
import logging
from datetime import datetime
from database import get_db_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
FS_BASE_URL = "http://localhost:8000"

def fetch_match_standings(fs_id):
    """Fetch all standings types for a match using the direct endpoint."""
    results = {}
    
    # Fetch different standings types
    endpoints = [
        ('overall_table', {'type': 'overall'}),
        ('home_table', {'type': 'home'}),
        ('away_table', {'type': 'away'}),
        ('form_overall_table', {'type': 'form'}),
    ]
    
    for key, params in endpoints:
        try:
            params['match'] = fs_id
            r = requests.get(f"{FS_BASE_URL}/matches/standings", params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data and 'standings' in data and data['standings']:
                    results[key] = json.dumps(data)
                    logging.debug(f"✅ {key}: fetched")
                else:
                    logging.debug(f"⚠️  {key}: empty response")
            else:
                logging.debug(f" {key}: HTTP {r.status_code}")
            time.sleep(0.2)
        except Exception as e:
            logging.debug(f"❌ {key}: {e}")
    
    # Fetch Over/Under data (0.5 to 6.5)
    ou_all = {}
    for line in ['0.5', '1.5', '2.5', '3.5', '4.5', '5.5', '6.5']:
        try:
            params = {'match': fs_id, 'type': 'over-under', 'line': line}
            r = requests.get(f"{FS_BASE_URL}/matches/standings", params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data and 'standings' in data and data['standings']:
                    ou_all[line] = data
            time.sleep(0.2)
        except Exception as e:
            logging.debug(f" O/U {line}: {e}")
    
    if ou_all:
        results['ou_all'] = json.dumps(ou_all)
        if '2.5' in ou_all:
            results['over_under_table'] = json.dumps(ou_all['2.5'])
    
    return results

def patch_all_standings():
    print("="*60)
    print("PATCHING ALL STANDINGS DATA")
    print("="*60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all linked matches
    cursor.execute("""
        SELECT ml.betika_match_id, ml.flashscore_match_id, ml.fs_home, ml.fs_away
        FROM match_links ml
    """)
    links = cursor.fetchall()
    
    print(f"\nFound {len(links)} linked matches to process.\n")
    
    updated_count = 0
    for link in links:
        betika_id = link['betika_match_id']
        fs_id = link['flashscore_match_id']
        fs_home = link['fs_home']
        fs_away = link['fs_away']
        
        logging.info(f"Processing: {fs_home} vs {fs_away} (FS: {fs_id})")
        
        # Fetch standings
        standings = fetch_match_standings(fs_id)
        
        if standings:
            # Update database
            cursor.execute("""
                INSERT OR REPLACE INTO ultimate_stats 
                (match_id, home_team, away_team, tournament_pair, overall_table, home_table, away_table, 
                 over_under_table, ht_ft_table, form_overall_table, form_home_table, form_away_table, ou_all, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                betika_id, fs_home, fs_away, 'patched',
                standings.get('overall_table', ''),
                standings.get('home_table', ''),
                standings.get('away_table', ''),
                standings.get('over_under_table', ''),
                '',  # ht_ft_table
                standings.get('form_overall_table', ''),
                '',  # form_home_table
                '',  # form_away_table
                standings.get('ou_all', ''),
                datetime.now().isoformat()
            ))
            conn.commit()
            updated_count += 1
            logging.info(f"✅ Updated {betika_id}")
        else:
            logging.warning(f"⚠️  No standings data for {betika_id}")
    
    conn.close()
    print(f"\n{'='*60}")
    print(f"✅ PATCH COMPLETE! Updated {updated_count}/{len(links)} matches.")
    print(f"{'='*60}")

if __name__ == "__main__":
    patch_all_standings()

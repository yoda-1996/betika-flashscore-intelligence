"""
Patch script to fetch Form Home and Form Away tables.
"""

import requests
import json
import time
import logging
from datetime import datetime
from database import get_db_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
FS_BASE_URL = "http://localhost:8000"

def fetch_form_tables(fs_id):
    """Fetch form-home and form-away standings."""
    results = {}
    endpoints = [
        ('form_home_table', {'type': 'form-home'}),
        ('form_away_table', {'type': 'form-away'}),
    ]
    
    for key, params in endpoints:
        try:
            params['match'] = fs_id
            params['line'] = '5' # Last 5 matches
            r = requests.get(f"{FS_BASE_URL}/matches/standings", params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data and 'standings' in data and data['standings']:
                    results[key] = json.dumps(data)
                    logging.debug(f"✅ {key}: fetched")
            time.sleep(0.2)
        except Exception as e:
            logging.debug(f"❌ {key}: {e}")
    return results

def patch_form_data():
    print("="*60)
    print("PATCHING FORM HOME/AWAY DATA")
    print("="*60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT betika_match_id, flashscore_match_id, fs_home, fs_away FROM match_links")
    links = cursor.fetchall()
    
    print(f"\nProcessing {len(links)} matches...\n")
    
    updated_count = 0
    for link in links:
        betika_id = link['betika_match_id']
        fs_id = link['flashscore_match_id']
        fs_home = link['fs_home']
        fs_away = link['fs_away']
        
        # Fetch new form data
        form_data = fetch_form_tables(fs_id)
        
        if form_data:
            # We need to update existing rows, not replace entirely, to keep other data
            # But INSERT OR REPLACE is easier if we have all data. 
            # Since we only have form data here, let's do a specific UPDATE.
            
            set_clause = []
            values = []
            for col, val in form_data.items():
                set_clause.append(f"{col} = ?")
                values.append(val)
            
            if set_clause:
                values.append(betika_id)
                sql = f"UPDATE ultimate_stats SET {', '.join(set_clause)} WHERE match_id = ?"
                cursor.execute(sql, values)
                conn.commit()
                updated_count += 1
                
        if updated_count % 50 == 0:
            print(f"  Processed {updated_count}...")

    conn.close()
    print(f"\n{'='*60}")
    print(f"✅ FORM PATCH COMPLETE! Updated {updated_count} matches.")
    print(f"{'='*60}")

if __name__ == "__main__":
    patch_form_data()

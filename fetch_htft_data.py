"""
Fetch HT/FT (Half-Time/Full-Time) statistics from Flashscore API.
"""

import requests
import json
import time
import logging
from datetime import datetime
from database import get_db_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
FS_BASE_URL = "http://localhost:8000"

def fetch_htft_standings(fs_id):
    """Fetch HT/FT standings table for a match."""
    try:
        params = {'match': fs_id, 'type': 'ht-ft'}
        r = requests.get(f"{FS_BASE_URL}/matches/standings", params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data and 'standings' in data and data['standings']:
                return json.dumps(data)
        return None
    except Exception as e:
        logging.debug(f"HT/FT fetch error: {e}")
        return None

def patch_htft_data():
    print("="*60)
    print("FETCHING HT/FT DATA")
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
        
        logging.info(f"Processing: {fs_home} vs {fs_away}")
        
        # Fetch HT/FT data
        htft_data = fetch_htft_standings(fs_id)
        
        if htft_data:
            # Update the ht_ft_table column in ultimate_stats
            cursor.execute("""
                UPDATE ultimate_stats 
                SET ht_ft_table = ?
                WHERE match_id = ?
            """, (htft_data, betika_id))
            conn.commit()
            updated_count += 1
            logging.info(f"✅ Updated {betika_id}")
        else:
            logging.warning(f"⚠️  No HT/FT data for {betika_id}")
        
        if updated_count % 50 == 0:
            print(f"  Processed {updated_count}...")
    
    conn.close()
    print(f"\n{'='*60}")
    print(f"✅ HT/FT PATCH COMPLETE! Updated {updated_count} matches.")
    print(f"{'='*60}")

if __name__ == "__main__":
    patch_htft_data()

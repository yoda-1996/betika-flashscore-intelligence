"""
Fetch HT/FT data using the correct tournament-based endpoint.
"""

import requests
import json
import time
import logging
from datetime import datetime
from database import get_db_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
FS_BASE_URL = "http://localhost:8000"

def get_tournament_id(fs_id):
    """Get tournament ID from match details."""
    try:
        r = requests.get(f"{FS_BASE_URL}/matches/details", params={"match": fs_id}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            # Try different possible keys for tournament ID
            tournament = data.get('tournament') or data.get('competition') or {}
            t_id = tournament.get('id') or tournament.get('slug')
            return t_id
        return None
    except Exception as e:
        logging.debug(f"Error getting tournament ID: {e}")
        return None

def fetch_htft_standings(tournament_id):
    """Fetch HT/FT standings for a tournament."""
    try:
        params = {'tournament': tournament_id, 'type': 'ht-ft'}
        r = requests.get(f"{FS_BASE_URL}/tournaments/standings", params=params, timeout=10)
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
    print("FETCHING HT/FT DATA (TOURNAMENT-BASED)")
    print("="*60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT betika_match_id, flashscore_match_id, fs_home, fs_away FROM match_links")
    links = cursor.fetchall()
    
    print(f"\nProcessing {len(links)} matches...\n")
    
    updated_count = 0
    tournament_cache = {}  # Cache tournament IDs to avoid redundant API calls
    
    for link in links:
        betika_id = link['betika_match_id']
        fs_id = link['flashscore_match_id']
        fs_home = link['fs_home']
        fs_away = link['fs_away']
        
        logging.info(f"Processing: {fs_home} vs {fs_away}")
        
        # Get tournament ID (with caching)
        if fs_id in tournament_cache:
            tournament_id = tournament_cache[fs_id]
        else:
            tournament_id = get_tournament_id(fs_id)
            tournament_cache[fs_id] = tournament_id
            time.sleep(0.2)  # Rate limit
        
        if not tournament_id:
            logging.warning(f"⚠️  No tournament ID for {betika_id}")
            continue
        
        # Fetch HT/FT data
        htft_data = fetch_htft_standings(tournament_id)
        
        if htft_data:
            # Update the ht_ft_table column
            cursor.execute("""
                UPDATE ultimate_stats 
                SET ht_ft_table = ?
                WHERE match_id = ?
            """, (htft_data, betika_id))
            conn.commit()
            updated_count += 1
            logging.info(f"✅ Updated {betika_id} with HT/FT data")
        else:
            logging.warning(f"️  No HT/FT data for tournament {tournament_id}")
        
        if updated_count % 50 == 0:
            print(f"  Updated {updated_count} matches...")
    
    conn.close()
    print(f"\n{'='*60}")
    print(f"✅ HT/FT PATCH COMPLETE! Updated {updated_count} matches.")
    print(f"{'='*60}")

if __name__ == "__main__":
    patch_htft_data()

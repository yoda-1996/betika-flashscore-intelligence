"""
Fetches HT/FT data using the correct Match endpoint with a delay to avoid blocking.
"""
import requests
import json
import time
from database import get_db_connection

API = "http://localhost:8000"

def main():
    print("Fetching HT/FT Data (Match Endpoint)...")
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT betika_match_id, flashscore_match_id FROM match_links")
    links = cur.fetchall()
    
    print(f"Processing {len(links)} matches...")
    count = 0
    
    for link in links:
        betika_id = link['betika_match_id']
        fs_id = link['flashscore_match_id']
        
        try:
            # 1. Use the MATCH endpoint
            # 2. Use type=ht-ft
            r = requests.get(f"{API}/matches/standings", params={"match": fs_id, "type": "ht-ft"}, timeout=10)
            
            # CRITICAL: Wait 0.3 seconds so the API doesn't block us
            time.sleep(0.3)
            
            if r.status_code == 200:
                data = r.json()
                # Check if standings data exists
                if data and isinstance(data, dict) and data.get('standings'):
                    # Update the existing row for this Betika ID
                    cur.execute("UPDATE ultimate_stats SET ht_ft_table = ? WHERE match_id = ?", 
                                (json.dumps(data), betika_id))
                    conn.commit()
                    count += 1
                    if count % 50 == 0:
                        print(f"  ...updated {count} matches so far.")
        except Exception:
            pass
            
    print(f"✅ Successfully updated {count} matches with HT/FT data.")
    conn.close()

if __name__ == "__main__":
    main()

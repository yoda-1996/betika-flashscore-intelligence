"""
Fetches HT/FT Home and Away tables using the Match endpoint.
"""
import requests
import json
import time
from database import get_db_connection

API = "http://localhost:8000"

def main():
    print("Fetching HT/FT Home/Away Data...")
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
            # Fetch HT/FT Home
            r_home = requests.get(f"{API}/matches/standings", 
                                  params={"match": fs_id, "type": "ht-ft-home"}, 
                                  timeout=10)
            time.sleep(0.2)
            
            # Fetch HT/FT Away
            r_away = requests.get(f"{API}/matches/standings", 
                                  params={"match": fs_id, "type": "ht-ft-away"}, 
                                  timeout=10)
            time.sleep(0.2)
            
            home_data = None
            away_data = None
            
            if r_home.status_code == 200:
                data = r_home.json()
                if data and isinstance(data, dict) and data.get('standings'):
                    home_data = json.dumps(data)
            
            if r_away.status_code == 200:
                data = r_away.json()
                if data and isinstance(data, dict) and data.get('standings'):
                    away_data = json.dumps(data)
            
            if home_data or away_data:
                cur.execute("""
                    UPDATE ultimate_stats 
                    SET ht_ft_home_table = COALESCE(?, ht_ft_home_table),
                        ht_ft_away_table = COALESCE(?, ht_ft_away_table)
                    WHERE match_id = ?
                """, (home_data, away_data, betika_id))
                conn.commit()
                count += 1
                
                if count % 50 == 0:
                    print(f"  ...updated {count} matches so far.")
                    
        except Exception:
            pass
            
    print(f"✅ Successfully updated {count} matches with HT/FT Home/Away data.")
    conn.close()

if __name__ == "__main__":
    main()

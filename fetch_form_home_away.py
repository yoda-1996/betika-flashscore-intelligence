"""
Fetches Form (Home) and Form (Away) tables using the Match endpoint.
"""
import requests
import json
import time
from database import get_db_connection

API = "http://localhost:8000"

def main():
    print("Fetching Form Home/Away Data...")
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
            # Fetch Form Home
            r_home = requests.get(f"{API}/matches/standings", 
                                  params={"match": fs_id, "type": "form-home"}, 
                                  timeout=10)
            time.sleep(0.2)
            
            # Fetch Form Away
            r_away = requests.get(f"{API}/matches/standings", 
                                  params={"match": fs_id, "type": "form-away"}, 
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
                    SET form_home_table = COALESCE(?, form_home_table),
                        form_away_table = COALESCE(?, form_away_table)
                    WHERE match_id = ?
                """, (home_data, away_data, betika_id))
                conn.commit()
                count += 1
                
                if count % 50 == 0:
                    print(f"  ...updated {count} matches so far.")
                    
        except Exception:
            pass
            
    print(f"✅ Successfully updated {count} matches with Form Home/Away data.")
    conn.close()

if __name__ == "__main__":
    main()

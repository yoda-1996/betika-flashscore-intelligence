"""
Fetches HT/FT data using the correct Tournament endpoint and updates the database.
"""
import requests
import json
from database import get_db_connection

API = "http://localhost:8000"

def main():
    print("Fetching HT/FT Data (Tournament Endpoint)...")
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get all linked matches AND their tournament_pair from ultimate_stats
    cur.execute("""
        SELECT ml.betika_match_id, ml.flashscore_match_id, us.tournament_pair 
        FROM match_links ml
        JOIN ultimate_stats us ON ml.flashscore_match_id = us.match_id
        WHERE us.tournament_pair IS NOT NULL AND us.tournament_pair != ''
    """)
    links = cur.fetchall()
    
    print(f"Processing {len(links)} matches with valid tournament pairs...")
    count = 0
    
    for link in links:
        betika_id = link['betika_match_id']
        fs_id = link['flashscore_match_id']
        tournament_pair = link['tournament_pair']
        
        try:
            # 1. Use the TOURNAMENT endpoint with the tournament_pair
            # 2. Extract just the tournament ID (part before the colon)
            t_id = tournament_pair.split(':')[0] if ':' in tournament_pair else tournament_pair
            
            r = requests.get(
                f"{API}/tournaments/standings", 
                params={"tournament": t_id, "type": "ht-ft"}, 
                timeout=10
            )
            
            if r.status_code == 200:
                data = r.json()
                # Check if standings data exists
                if data and isinstance(data, dict) and data.get('standings'):
                    # ✅ FIXED: Update using the Flashscore ID (fs_id), NOT betika_id
                    cur.execute("""
                        UPDATE ultimate_stats 
                        SET ht_ft_table = ? 
                        WHERE match_id = ?
                    """, (json.dumps(data), fs_id))
                    conn.commit()
                    count += 1
            else:
                print(f"⚠️ API Error {r.status_code} for FS ID: {fs_id}")
                
        except Exception as e:
            # ✅ FIXED: Print the error so we know why it failed
            print(f"❌ Exception for FS ID {fs_id}: {e}")
            
    print(f"\n✅ Successfully updated {count} out of {len(links)} matches with HT/FT data.")
    conn.close()

if __name__ == "__main__":
    main()

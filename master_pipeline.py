"""
MASTER PIPELINE - Does everything in one run
1. Backs up current working files
2. Scrapes Betika for tomorrow
3. Links to Flashscore
4. Fetches ALL data (standings, form, HT/FT, O/U, H2H, extras)
5. Runs probability model
6. Reports results
"""

import subprocess
import sys
from datetime import datetime
from database import get_db_connection

def run_command(cmd, description):
    print(f"\n{'='*60}")
    print(f"📋 {description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True, capture_output=False)
    if result.returncode != 0:
        print(f"❌ {description} failed!")
        return False
    print(f"✅ {description} complete")
    return True

def fetch_all_match_data():
    """Fetches ALL data for linked matches using match-based endpoints."""
    print(f"\n{'='*60}")
    print("📊 Fetching Complete Match Data")
    print(f"{'='*60}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all linked matches for tomorrow
    cursor.execute("""
        SELECT ml.betika_match_id, ml.flashscore_match_id, ml.fs_home, ml.fs_away
        FROM match_links ml
        JOIN fixtures f ON ml.betika_match_id = f.match_id
        WHERE date(f.kickoff) = date('now', '+1 day')
    """)
    links = cursor.fetchall()
    
    print(f"Processing {len(links)} matches...")
    
    import requests
    import json
    import time
    
    API = "http://localhost:8000"
    count = 0
    
    for link in links:
        betika_id = link['betika_match_id']
        fs_id = link['flashscore_match_id']
        fs_home = link['fs_home']
        fs_away = link['fs_away']
        
        try:
            # 1. Fetch Overall Standings
            r = requests.get(f"{API}/matches/standings", params={"match": fs_id, "type": "overall"}, timeout=10)
            time.sleep(0.2)
            overall_data = json.dumps(r.json()) if r.status_code == 200 and r.json().get('standings') else None
            
            # 2. Fetch Home Standings
            r = requests.get(f"{API}/matches/standings", params={"match": fs_id, "type": "home"}, timeout=10)
            time.sleep(0.2)
            home_data = json.dumps(r.json()) if r.status_code == 200 and r.json().get('standings') else None
            
            # 3. Fetch Away Standings
            r = requests.get(f"{API}/matches/standings", params={"match": fs_id, "type": "away"}, timeout=10)
            time.sleep(0.2)
            away_data = json.dumps(r.json()) if r.status_code == 200 and r.json().get('standings') else None
            
            # 4. Fetch Form Overall
            r = requests.get(f"{API}/matches/standings", params={"match": fs_id, "type": "form"}, timeout=10)
            time.sleep(0.2)
            form_data = json.dumps(r.json()) if r.status_code == 200 and r.json().get('standings') else None
            
            # 5. Fetch Form Home
            r = requests.get(f"{API}/matches/standings", params={"match": fs_id, "type": "form-home"}, timeout=10)
            time.sleep(0.2)
            form_home_data = json.dumps(r.json()) if r.status_code == 200 and r.json().get('standings') else None
            
            # 6. Fetch Form Away
            r = requests.get(f"{API}/matches/standings", params={"match": fs_id, "type": "form-away"}, timeout=10)
            time.sleep(0.2)
            form_away_data = json.dumps(r.json()) if r.status_code == 200 and r.json().get('standings') else None
            
            # 7. Fetch HT/FT Overall
            r = requests.get(f"{API}/matches/standings", params={"match": fs_id, "type": "ht-ft"}, timeout=10)
            time.sleep(0.2)
            htft_data = json.dumps(r.json()) if r.status_code == 200 and r.json().get('standings') else None
            
            # 8. Fetch HT/FT Home
            r = requests.get(f"{API}/matches/standings", params={"match": fs_id, "type": "ht-ft-home"}, timeout=10)
            time.sleep(0.2)
            htft_home_data = json.dumps(r.json()) if r.status_code == 200 and r.json().get('standings') else None
            
            # 9. Fetch HT/FT Away
            r = requests.get(f"{API}/matches/standings", params={"match": fs_id, "type": "ht-ft-away"}, timeout=10)
            time.sleep(0.2)
            htft_away_data = json.dumps(r.json()) if r.status_code == 200 and r.json().get('standings') else None
            
            # 10. Fetch ALL Over/Under lines (0.5 to 5.5)
            ou_all = {}
            for line in ['0.5', '1.5', '2.5', '3.5', '4.5', '5.5']:
                r = requests.get(f"{API}/matches/standings", params={"match": fs_id, "type": "over-under", "line": line}, timeout=10)
                time.sleep(0.15)
                if r.status_code == 200 and r.json().get('standings'):
                    ou_all[line] = r.json()
            ou_data = json.dumps(ou_all) if ou_all else None
            
            # 11. Fetch H2H
            r = requests.get(f"{API}/matches/h2h", params={"match": fs_id}, timeout=10)
            time.sleep(0.2)
            h2h_data = json.dumps(r.json()) if r.status_code == 200 and 'error' not in r.json() else None
            
            # 12. Fetch Missing Players
            r = requests.get(f"{API}/matches/missing-players", params={"match": fs_id}, timeout=10)
            time.sleep(0.2)
            injuries_data = json.dumps(r.json()) if r.status_code == 200 else None
            
            # 13. Fetch News
            r = requests.get(f"{API}/matches/news", params={"match": fs_id}, timeout=10)
            time.sleep(0.2)
            news_data = json.dumps(r.json()) if r.status_code == 200 else None
            
            # 14. Fetch Summary/Report
            r = requests.get(f"{API}/matches/summary", params={"match": fs_id}, timeout=10)
            time.sleep(0.2)
            report_data = json.dumps(r.json()) if r.status_code == 200 else None
            
            # 15. Fetch Lineups
            r = requests.get(f"{API}/matches/lineups", params={"match": fs_id}, timeout=10)
            time.sleep(0.2)
            lineups_data = json.dumps(r.json()) if r.status_code == 200 else None
            
            # Save Ultimate Stats
            cursor.execute("""
                INSERT OR REPLACE INTO ultimate_stats 
                (match_id, home_team, away_team, overall_table, home_table, away_table,
                 form_overall_table, form_home_table, form_away_table,
                 ht_ft_table, ht_ft_home_table, ht_ft_away_table,
                 over_under_table, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                betika_id, fs_home, fs_away,
                overall_data, home_data, away_data,
                form_data, form_home_data, form_away_data,
                htft_data, htft_home_data, htft_away_data,
                ou_data, datetime.now().isoformat()
            ))
            
            # Save H2H
            if h2h_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO flashscore_h2h 
                    (match_id, home_team_name, away_team_name, h2h_data) 
                    VALUES (?, ?, ?, ?)
                """, (betika_id, fs_home, fs_away, h2h_data))
            
            # Save Extras
            cursor.execute("""
                INSERT OR REPLACE INTO match_extras 
                (betika_match_id, injuries, news, report, lineups, collected_at) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                betika_id, injuries_data, news_data, report_data, lineups_data,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            count += 1
            
            if count % 10 == 0:
                print(f"  Processed {count}/{len(links)} matches...")
                
        except Exception as e:
            print(f"  Error processing {fs_home} vs {fs_away}: {e}")
            continue
    
    conn.close()
    print(f"\n✅ Complete data fetched for {count} matches")

def main():
    print("🚀 MASTER PIPELINE STARTING")
    print(f"Time: {datetime.now()}")
    
    # Step 1: Backup
    run_command("python backup_system.py", "Creating backup of working files")
    
    # Step 2: Scrape Betika
    run_command("python betika_scraper.py", "Scraping Betika odds for tomorrow")
    
    # Step 3: Sync with Flashscore (linking only)
    run_command("python sync_betika_flashscore.py", "Linking matches to Flashscore")
    
    # Step 4: Fetch ALL data
    fetch_all_match_data()
    
    # Step 5: Run probability model
    run_command("python probability_model.py", "Running probability model")
    
    print(f"\n{'='*60}")
    print("🎉 MASTER PIPELINE COMPLETE")
    print(f"{'='*60}")
    print("\nNext steps:")
    print("1. streamlit run dashboard.py")
    print("2. Check all tabs for data")

if __name__ == "__main__":
    main()

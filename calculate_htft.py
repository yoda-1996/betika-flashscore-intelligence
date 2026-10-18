"""
Calculates HT/FT statistics directly from existing H2H match data.
This is more accurate for betting than generic league tables.
"""

import sqlite3
import json
from database import get_db_connection

def calculate_team_htft(h2h_json, team_name):
    """Calculates HT/FT record from the last 10 matches."""
    try:
        data = json.loads(h2h_json)
        sections = data.get('sections', [])
        target_name = f"last matches: {team_name.lower()}"
        
        matches = []
        for sec in sections:
            if sec.get('name', '').lower() == target_name:
                matches = sec.get('matches', [])
                break
        
        htft_counts = {
            'W/W': 0, 'W/D': 0, 'W/L': 0,
            'D/W': 0, 'D/D': 0, 'D/L': 0,
            'L/W': 0, 'L/D': 0, 'L/L': 0
        }
        
        for m in matches[:10]:
            # Get HT and FT scores
            home_score_ht = m.get('home_score', {}).get('period1', 0)
            away_score_ht = m.get('away_score', {}).get('period1', 0)
            home_score_ft = m.get('home_score', {}).get('current', 0)
            away_score_ft = m.get('away_score', {}).get('current', 0)
            
            if home_score_ht is None or home_score_ft is None:
                continue
                
            past_home_name = (m.get('home') or {}).get('name', '').lower()
            is_home = team_name.lower() in past_home_name
            
            if is_home:
                team_ht, opp_ht = home_score_ht, away_score_ht
                team_ft, opp_ft = home_score_ft, away_score_ft
            else:
                team_ht, opp_ht = away_score_ht, home_score_ht
                team_ft, opp_ft = away_score_ft, home_score_ft
                
            # Determine HT result
            if team_ht > opp_ht: ht_res = 'W'
            elif team_ht == opp_ht: ht_res = 'D'
            else: ht_res = 'L'
            
            # Determine FT result
            if team_ft > opp_ft: ft_res = 'W'
            elif team_ft == opp_ft: ft_res = 'D'
            else: ft_res = 'L'
            
            combo = f"{ht_res}/{ft_res}"
            if combo in htft_counts:
                htft_counts[combo] += 1
                
        return htft_counts
    except Exception as e:
        return None

def main():
    print("="*60)
    print("CALCULATING HT/FT STATISTICS FROM H2H DATA")
    print("="*60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT h2h.match_id, h2h.home_team_name, h2h.away_team_name, h2h.h2h_data
        FROM flashscore_h2h h2h
    """)
    rows = cursor.fetchall()
    
    print(f"\nProcessing {len(rows)} matches...\n")
    
    updated_count = 0
    for row in rows:
        match_id = row['match_id']
        home_team = row['home_team_name']
        away_team = row['away_team_name']
        h2h_data = row['h2h_data']
        
        home_htft = calculate_team_htft(h2h_data, home_team)
        away_htft = calculate_team_htft(h2h_data, away_team)
        
        if home_htft and away_htft:
            combined_htft = {
                'standings': [
                    {'team': {'name': home_team}, 'stats': home_htft},
                    {'team': {'name': away_team}, 'stats': away_htft}
                ]
            }
            
            cursor.execute("""
                INSERT OR REPLACE INTO ultimate_stats 
                (match_id, home_team, away_team, ht_ft_table)
                VALUES (?, ?, ?, ?)
            """, (match_id, home_team, away_team, json.dumps(combined_htft)))
            
            conn.commit()
            updated_count += 1
            
        if updated_count % 50 == 0:
            print(f"  Processed {updated_count} matches...")
            
    conn.close()
    print(f"\n✅ HT/FT CALCULATION COMPLETE! Updated {updated_count} matches.")

if __name__ == "__main__":
    main()

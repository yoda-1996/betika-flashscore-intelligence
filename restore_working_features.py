"""
Restores the working Over/Under fetching logic and Safe Bets configuration.
Based on the original sync_betika_flashscore.py that worked.
"""

import json
from database import get_db_connection

def restore_ou_data():
    """Re-fetches O/U data using the tournament endpoint that actually works."""
    print("="*60)
    print("RESTORING OVER/UNDER DATA (Tournament Endpoint)")
    print("="*60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all linked matches with their tournament pairs
    cursor.execute("""
        SELECT ml.betika_match_id, ml.flashscore_match_id, us.tournament_pair
        FROM match_links ml
        JOIN ultimate_stats us ON ml.flashscore_match_id = us.match_id
        JOIN fixtures f ON ml.betika_match_id = f.match_id
        WHERE date(f.kickoff) = date('now', '+1 day')
        AND us.tournament_pair IS NOT NULL
    """)
    
    matches = cursor.fetchall()
    print(f"Found {len(matches)} matches with tournament data")
    
    import requests
    import time
    
    API = "http://localhost:8000"
    OU_LINES = ['0.5', '1.5', '2.5', '3.5', '4.5', '5.5']
    
    updated_count = 0
    cache = {}  # Cache by tournament_pair to avoid redundant calls
    
    for match in matches:
        betika_id = match['betika_match_id']
        fs_id = match['flashscore_match_id']
        tournament_pair = match['tournament_pair']
        
        if not tournament_pair:
            continue
        
        # Use cached data if available
        if tournament_pair in cache:
            ou_all = cache[tournament_pair]
        else:
            # Fetch O/U data using TOURNAMENT endpoint (this is what worked!)
            ou_all = {}
            for line in OU_LINES:
                try:
                    params = {'tournament': tournament_pair, 'type': 'over-under', 'line': line}
                    r = requests.get(f"{API}/tournaments/standings", params=params, timeout=10)
                    time.sleep(0.2)
                    d = r.json()
                    if 'error' not in d and d.get('standings'):
                        ou_all[line] = d
                except Exception:
                    pass
            
            cache[tournament_pair] = ou_all
        
        if ou_all:
            # Update the ultimate_stats table
            cursor.execute("""
                UPDATE ultimate_stats 
                SET ou_all = ?
                WHERE match_id = ?
            """, (json.dumps(ou_all), fs_id))
            
            # Also update over_under_table with just 2.5
            if '2.5' in ou_all:
                cursor.execute("""
                    UPDATE ultimate_stats 
                    SET over_under_table = ?
                    WHERE match_id = ?
                """, (json.dumps(ou_all['2.5']), fs_id))
            
            conn.commit()
            updated_count += 1
            
            if updated_count % 10 == 0:
                print(f"  Updated {updated_count} matches...")
    
    conn.close()
    print(f"\n✅ Restored O/U data for {updated_count} matches")

def verify_safe_bets_setup():
    """Checks if the Safe Bets tab is properly configured."""
    print("\n" + "="*60)
    print("VERIFYING SAFE BETS CONFIGURATION")
    print("="*60)
    
    with open('dashboard.py', 'r') as f:
        content = f.read()
    
    checks = {
        "Safe Bets tab in navigation": "Safe Bets (Bankers)" in content,
        "Safe Bets query exists": "vb.betika_odd BETWEEN 1.01 AND 1.30" in content,
        "Percentage fix applied": "display_df['model_probability'] = display_df['model_probability'] * 100" in content,
        "Data Quality fix applied": "max_value=100.0" in content
    }
    
    all_good = True
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check}")
        if not result:
            all_good = False
    
    if all_good:
        print("\n✅ Safe Bets tab is properly configured")
    else:
        print("\n⚠️  Some Safe Bets features need fixing")
    
    return all_good

if __name__ == "__main__":
    restore_ou_data()
    verify_safe_bets_setup()
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("1. Run: python probability_model.py")
    print("2. Run: streamlit run dashboard.py")
    print("3. Check Over/Under tab in Ultimate Report")
    print("4. Check Safe Bets tab")
    print("="*60)

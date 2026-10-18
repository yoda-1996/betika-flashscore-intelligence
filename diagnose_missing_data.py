"""
Diagnoses why tournament-level data (standings, form, O/U) is missing.
"""
import json
from database import get_db_connection

def diagnose():
    print("="*60)
    print("DIAGNOSING MISSING TOURNAMENT DATA")
    print("="*60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Check match_links
    print("\n1. Checking match_links table...")
    cursor.execute("SELECT betika_match_id, flashscore_match_id, confidence FROM match_links LIMIT 5")
    links = cursor.fetchall()
    print(f"   Found {len(links)} sample links")
    for link in links:
        print(f"   - Betika ID: {link['betika_match_id']}, FS ID: {link['flashscore_match_id']}, Confidence: {link['confidence']}")
    
    # 2. Check ultimate_stats
    print("\n2. Checking ultimate_stats table...")
    cursor.execute("SELECT match_id, home_team, away_team, tournament_pair, overall_table, ou_all FROM ultimate_stats LIMIT 5")
    stats = cursor.fetchall()
    print(f"   Found {len(stats)} sample stats records")
    for stat in stats:
        has_overall = "YES" if stat['overall_table'] else "NO"
        has_ou = "YES" if stat['ou_all'] else "NO"
        print(f"   - Match ID: {stat['match_id']}, Tournament: {stat['tournament_pair']}, Overall: {has_overall}, O/U: {has_ou}")
    
    # 3. Check flashscore_h2h
    print("\n3. Checking flashscore_h2h table...")
    cursor.execute("SELECT match_id, h2h_data FROM flashscore_h2h LIMIT 3")
    h2h = cursor.fetchall()
    print(f"   Found {len(h2h)} sample H2H records")
    for h in h2h:
        has_data = "YES" if h['h2h_data'] else "NO"
        print(f"   - Match ID: {h['match_id']}, Has H2H: {has_data}")
    
    # 4. The Critical Check: Do we have tournament_pair for tomorrow's matches?
    print("\n4. Checking tournament_pair for TOMORROW's matches...")
    cursor.execute("""
        SELECT ml.betika_match_id, ml.flashscore_match_id, us.tournament_pair
        FROM match_links ml
        LEFT JOIN ultimate_stats us ON ml.betika_match_id = us.match_id
        JOIN fixtures f ON ml.betika_match_id = f.match_id
        WHERE date(f.kickoff) = date('now', '+1 day')
        LIMIT 10
    """)
    tomorrow = cursor.fetchall()
    print(f"   Found {len(tomorrow)} tomorrow's matches")
    for t in tomorrow:
        has_pair = "YES" if t['tournament_pair'] else "NO"
        print(f"   - Betika: {t['betika_match_id']}, FS: {t['flashscore_match_id']}, Tournament Pair: {has_pair} ({t['tournament_pair']})")
    
    conn.close()
    
    print("\n" + "="*60)
    print("DIAGNOSIS COMPLETE")
    print("="*60)
    print("\nIf tournament_pair is 'NO' for tomorrow's matches,")
    print("the sync script is not saving it correctly.")

if __name__ == "__main__":
    diagnose()

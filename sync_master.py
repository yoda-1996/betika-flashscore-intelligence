import requests
import sqlite3
import json
import time
import re
from datetime import datetime, timedelta
from database import get_db_connection

FLASHSCORE_API = "http://localhost:8000"
THRESHOLD = 0.65

# ─── 1. Name Matching Logic (Clean & Robust) ─────────────────────────────────
NOISE = {'sc', 'fc', 'cf', 'ac', 'sk', 'fk', 'if', 'bk', 'club', 'the', 'w', 
         'women', 'ladies', 'u19', 'u20', 'u21', 'ii', 'iii', 'iv', 'united', 
         'city', 'real', 'san', 'sao', 'santa', 'st', 'athletic', 'atletico', 
         'sporting', 'sport', 'association', 'football', 'soccer', 'de', 'da', 
         'do', 'dos', 'del', 'la', 'el', 'los', 'las'}

def clean_name(name):
    """Normalize team names for comparison."""
    if not name: return ""
    n = name.lower()
    n = re.sub(r'\(.*?\)', '', n)  # Remove (Country)
    n = re.sub(r'\d+', '', n)      # Remove numbers
    words = [w for w in re.findall(r'\b\w+\b', n) if w not in NOISE]
    return " ".join(words)

def name_sim(a, b):
    """Calculate similarity between two cleaned names."""
    ca, cb = clean_name(a), clean_name(b)
    if not ca or not cb: return 0.0
    if ca == cb: return 1.0
    if ca in cb or cb in ca: return 0.85
    set_a, set_b = set(ca.split()), set(cb.split())
    if not set_a or not set_b: return 0.0
    return len(set_a & set_b) / len(set_a | set_b)

def find_best_match(b_home, b_away, fs_pool):
    """Find the best Flashscore match for a Betika fixture."""
    best_match = None
    best_score = 0.0
    best_swap = False

    for cand in fs_pool:
        f_home, f_away = cand['home'], cand['away']
        
        # Check straight orientation
        score_straight = 0.6 * name_sim(b_home, f_home) + 0.4 * name_sim(b_away, f_away)
        # Check swapped orientation
        score_swapped = 0.6 * name_sim(b_home, f_away) + 0.4 * name_sim(b_away, f_home)
        
        current_score = max(score_straight, score_swapped)
        is_swapped = score_swapped > score_straight

        if current_score > best_score:
            best_score = current_score
            best_match = cand
            best_swap = is_swapped

    if best_score >= THRESHOLD:
        return best_match, best_score, best_swap
    return None, 0.0, False

# ─── 2. Flashscore Data Fetchers ────────────────────────────────────────────
standings_cache = {}
OU_LINES = ['0.5', '1.5', '2.5', '3.5', '4.5', '5.5', '6.5']

def get_standings(pair):
    """Fetch all standings tables for a tournament pair."""
    if pair in standings_cache:
        return standings_cache[pair]
    
    res = {}
    if not pair:
        return res

    # Standard tables
    plans = [
        ('overall', [{'type': 'overall'}]),
        ('home', [{'type': 'home'}]),
        ('away', [{'type': 'away'}]),
        ('ht-ft', [{'type': 'ht-ft'}]),
        ('form-overall', [{'type': 'form', 'line': '5'}, {'type': 'form'}]),
        ('form-home', [{'type': 'form-home', 'line': '5'}, {'type': 'form-home'}]),
        ('form-away', [{'type': 'form-away', 'line': '5'}, {'type': 'form-away'}]),
    ]

    for key, param_sets in plans:
        for extra in param_sets:
            params = {'tournament': pair}
            params.update(extra)
            try:
                r = requests.get(f"{FLASHSCORE_API}/tournaments/standings", params=params, timeout=10)
                d = r.json()
                time.sleep(0.2)
                if 'error' not in d and d.get('standings'):
                    res[key] = json.dumps(d)
                    break
            except Exception:
                pass

    # Over/Under tables (0.5 to 6.5)
    ou_all = {}
    for line in OU_LINES:
        try:
            params = {'tournament': pair, 'type': 'over-under', 'line': line}
            r = requests.get(f"{FLASHSCORE_API}/tournaments/standings", params=params, timeout=10)
            d = r.json()
            time.sleep(0.2)
            if 'error' not in d and d.get('standings'):
                ou_all[line] = d
        except Exception:
            pass
            
    if ou_all:
        res['ou_all'] = json.dumps(ou_all)
        if '2.5' in ou_all:
            res['over-under'] = json.dumps(ou_all['2.5'])

    standings_cache[pair] = res
    return res

def get_h2h(fs_id):
    """Fetch Head-to-Head data."""
    try:
        r = requests.get(f"{FLASHSCORE_API}/matches/h2h", params={'match': fs_id}, timeout=10)
        d = r.json()
        return json.dumps(d) if 'error' not in d else ""
    except Exception:
        return ""

def get_extras(fs_id):
    """Fetch injuries, news, lineups, and report."""
    extras = {'injuries': '', 'news': '', 'report': '', 'lineups': ''}
    endpoints = [
        ('/matches/missing-players', 'injuries'), # Updated to missing-players as per docs
        ('/matches/news', 'news'),
        ('/matches/summary', 'report'), 
        ('/matches/lineups', 'lineups')
    ]
    
    for path, key in endpoints:
        try:
            r = requests.get(f"{FLASHSCORE_API}{path}", params={'match': fs_id}, timeout=10)
            d = r.json()
            time.sleep(0.2)
            if isinstance(d, (dict, list)) and d and not (isinstance(d, dict) and 'error' in d):
                extras[key] = json.dumps(d)
        except Exception:
            pass
    return extras

# ─── 3. Main Sync Logic ──────────────────────────────────────────────────────
def main():
    print("Starting Flashscore Sync Engine (Master Version)...")
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Get Betika fixtures from DB
    cur.execute("SELECT match_id, home, away, league FROM fixtures")
    betika_fixtures = cur.fetchall()
    print(f"Loaded {len(betika_fixtures)} Betika fixtures from DB.")

    # 2. Fetch Flashscore matches for a date range (Today +/- 3 days)
    print("Fetching Flashscore matches...")
    fs_pool = []
    today = datetime.now()
    for i in range(-3, 4):
        date_str = (today + timedelta(days=i)).strftime('%Y-%m-%d')
        try:
            r = requests.get(f"{FLASHSCORE_API}/matches", params={'sport': 'football', 'date': date_str}, timeout=15)
            data = r.json()
            for comp in data.get('competitions', []):
                c = comp.get('competition', {})
                t_id = c.get('id')
                s_id = c.get('season_id', c.get('id'))
                pair = f"{t_id}:{s_id}" if t_id and s_id else None
                
                for m in comp.get('matches', []):
                    fs_pool.append({
                        'id': m.get('id'),
                        'home': (m.get('home') or {}).get('name', ''),
                        'away': (m.get('away') or {}).get('name', ''),
                        'comp': c.get('name', ''),
                        'tournament_pair': pair
                    })
        except Exception as e:
            print(f"Error fetching FS for {date_str}: {e}")
    print(f"Flashscore pool: {len(fs_pool)} candidates.")

    # 3. Link Matches
    print("Linking matches...")
    linked_count = 0
    for b_id, b_home, b_away, b_league in betika_fixtures:
        match, score, is_swapped = find_best_match(b_home, b_away, fs_pool)
        
        if match:
            fs_home = match['away'] if is_swapped else match['home']
            fs_away = match['home'] if is_swapped else match['away']
            
            cur.execute("""
                INSERT OR REPLACE INTO match_links 
                (betika_match_id, flashscore_match_id, fs_home, fs_away, confidence) 
                VALUES (?, ?, ?, ?, ?)
            """, (b_id, match['id'], fs_home, fs_away, round(score, 3)))
            linked_count += 1

    print(f"✅ Linked {linked_count} matches.")
    conn.commit()

    # 4. Fetch Deep Intelligence for Linked Matches
    print("Fetching deep intelligence (Standings, H2H, Extras)...")
    cur.execute("""
        SELECT ml.betika_match_id, ml.flashscore_match_id, ml.fs_home, ml.fs_away, ml.confidence
        FROM match_links ml
    """)
    links = cur.fetchall()
    
    stats_count = 0
    for b_id, fs_id, fs_home, fs_away, conf in links:
        # Find tournament pair for this match
        t_pair = next((m['tournament_pair'] for m in fs_pool if m['id'] == fs_id), None)
        
        if t_pair:
            # A. Ultimate Stats (14 columns) - FIXED: uses b_id
            tables = get_standings(t_pair)
            cur.execute("""
                INSERT OR REPLACE INTO ultimate_stats 
                (match_id, home_team, away_team, tournament_pair, overall_table, home_table, away_table, 
                 over_under_table, ht_ft_table, form_overall_table, form_home_table, form_away_table, ou_all, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                b_id, fs_home, fs_away, t_pair,
                tables.get('overall', ''), tables.get('home', ''), tables.get('away', ''),
                tables.get('over-under', ''), tables.get('ht-ft', ''),
                tables.get('form-overall', ''), tables.get('form-home', ''), tables.get('form-away', ''),
                tables.get('ou_all', ''), datetime.now().isoformat()
            ))

            # B. H2H Data (4 columns) - FIXED: uses b_id
            h2h_data = get_h2h(fs_id)
            if h2h_data:
                cur.execute("""
                    INSERT OR REPLACE INTO flashscore_h2h 
                    (match_id, home_team_name, away_team_name, h2h_data) 
                    VALUES (?, ?, ?, ?)
                """, (b_id, fs_home, fs_away, h2h_data))

                # Parse form for deep_stats (4 columns) - FIXED: uses b_id
                hf = af = hh = ""
                try:
                    d = json.loads(h2h_data)
                    nh = clean_name(fs_home)
                    na = clean_name(fs_away)
                    for sec in d.get('sections', []):
                        nm = (sec.get('name') or '').lower()
                        ms = sec.get('matches', [])
                        if not nm or not ms: continue
                        line = " | ".join([f"{m.get('home_score')}-{m.get('away_score')}" for m in ms[:5]])
                        if 'head-to-head' in nm or 'h2h' in nm or ' vs ' in nm:
                            hh = line
                        elif nh and nh in nm:
                            hf = line
                        elif na and na in nm:
                            af = line
                except Exception: 
                    pass
                
                cur.execute("""
                    INSERT OR REPLACE INTO deep_stats 
                    (match_id, home_form_last5, away_form_last5, h2h_last5) 
                    VALUES (?, ?, ?, ?)
                """, (b_id, hf, af, hh))

            # C. Extras (7 columns) - Already correct (uses b_id)
            extras = get_extras(fs_id)
            cur.execute("""
                INSERT OR REPLACE INTO match_extras 
                (betika_match_id, available_tabs, injuries, news, report, lineups, collected_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                b_id, json.dumps(list(extras.keys())), 
                extras.get('injuries', ''), extras.get('news', ''), 
                extras.get('report', ''), extras.get('lineups', ''), 
                datetime.now().isoformat()
            ))
            stats_count += 1
            
            if stats_count % 20 == 0:
                print(f"  Processed {stats_count}/{len(links)} matches...")

    conn.commit()
    conn.close()
    print(f"🎉 Sync Complete! Processed deep stats for {stats_count} matches.")

if __name__ == "__main__":
    main()

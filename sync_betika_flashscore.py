"""
sync_betika_flashscore.py - HIGH SPEED VERSION
Uses Parallel Processing and Narrow Search Windows.
"""

import requests
import sqlite3
import json
import time
import re
from datetime import datetime, timedelta
from database import get_db_connection
from concurrent.futures import ThreadPoolExecutor, as_completed

FLASHSCORE_API = "http://localhost:8000"
THRESHOLD = 0.60

# ── 1. Name Matching Logic ──────────────────────────────────────────────────
NOISE = {'sc', 'fc', 'cf', 'ac', 'sk', 'fk', 'if', 'bk', 'club', 'the', 'w', 
         'women', 'ladies', 'u19', 'u20', 'u21', 'ii', 'iii', 'iv', 'united', 
         'city', 'real', 'san', 'sao', 'santa', 'st', 'athletic', 'atletico', 
         'sporting', 'sport', 'association', 'football', 'soccer', 'de', 'da', 
         'do', 'dos', 'del', 'la', 'el', 'los', 'las'}

def clean_name(name):
    if not name: return ""
    n = name.lower()
    n = re.sub(r'\(.*?\)', '', n)
    n = re.sub(r'\d+', '', n)
    words = [w for w in re.findall(r'\b\w+\b', n) if w not in NOISE]
    return " ".join(words)

def name_sim(a, b):
    ca, cb = clean_name(a), clean_name(b)
    if not ca or not cb: return 0.0
    if ca == cb: return 1.0
    if ca in cb or cb in ca: return 0.85
    set_a, set_b = set(ca.split()), set(cb.split())
    if not set_a or not set_b: return 0.0
    return len(set_a & set_b) / len(set_a | set_b)

def find_best_match(b_home, b_away, fs_pool):
    best_match, best_score, best_swap = None, 0.0, False
    for cand in fs_pool:
        f_home, f_away = cand['home'], cand['away']
        score_straight = 0.6 * name_sim(b_home, f_home) + 0.4 * name_sim(b_away, f_away)
        score_swapped = 0.6 * name_sim(b_home, f_away) + 0.4 * name_sim(b_away, f_home)
        current_score = max(score_straight, score_swapped)
        if current_score > best_score:
            best_score = current_score
            best_match = cand
            best_swap = score_swapped > score_straight
            
    if best_score >= THRESHOLD:
        return best_match, best_score, best_swap
    return None, 0.0, False

# ── 2. Flashscore Data Fetchers ─────────────────────────────────────────────
standings_cache = {}
OU_LINES = ['0.5', '1.5', '2.5', '3.5', '4.5', '5.5']

def get_standings(pair):
    if pair in standings_cache:
        return standings_cache[pair]
    
    res = {}
    if not pair: return res

    plans = [
        ('overall', [{'type': 'overall'}]), ('home', [{'type': 'home'}]), ('away', [{'type': 'away'}]),
        ('ht-ft', [{'type': 'ht-ft'}]), ('ht-ft-home', [{'type': 'ht-ft-home'}]), ('ht-ft-away', [{'type': 'ht-ft-away'}]),
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
                time.sleep(0.1) # Faster sleep
                if 'error' not in d and d.get('standings'):
                    res[key] = json.dumps(d)
                    break
            except Exception: pass

    ou_all = {}
    for line in OU_LINES:
        try:
            params = {'tournament': pair, 'type': 'over-under', 'line': line}
            r = requests.get(f"{FLASHSCORE_API}/tournaments/standings", params=params, timeout=10)
            d = r.json()
            time.sleep(0.1)
            if 'error' not in d and d.get('standings'): ou_all[line] = d
        except Exception: pass
            
    if ou_all:
        res['ou_all'] = json.dumps(ou_all)
        if '2.5' in ou_all: res['over-under'] = json.dumps(ou_all['2.5'])

    standings_cache[pair] = res
    return res

def get_match_extras(fs_id):
    """Fetches H2H, News, Injuries, Lineups in one go."""
    extras = {'h2h': '', 'injuries': '', 'news': '', 'report': '', 'lineups': ''}
    endpoints = [
        ('/matches/h2h', 'h2h'), ('/matches/missing-players', 'injuries'),
        ('/matches/news', 'news'), ('/matches/summary', 'report'), ('/matches/lineups', 'lineups')
    ]
    
    for path, key in endpoints:
        try:
            r = requests.get(f"{FLASHSCORE_API}{path}", params={'match': fs_id}, timeout=10)
            d = r.json()
            time.sleep(0.1)
            if isinstance(d, (dict, list)) and d and not (isinstance(d, dict) and 'error' in d):
                extras[key] = json.dumps(d)
        except Exception: pass
    return extras

# ── 3. Worker Function for Parallel Processing ──────────────────────────────
def process_single_match(link_data):
    """Fetches deep stats for one match. Runs in parallel."""
    b_id, fs_id, fs_home, fs_away, t_pair = link_data
    if not t_pair: return None
    
    try:
        tables = get_standings(t_pair)
        extras = get_match_extras(fs_id)
        
        return {
            'b_id': b_id, 'fs_home': fs_home, 'fs_away': fs_away, 't_pair': t_pair,
            'tables': tables, 'extras': extras
        }
    except Exception as e:
        print(f"  Error processing {fs_home} vs {fs_away}: {e}")
        return None

# ── 4. Main Sync Logic ────────────────────────────────────────────────────
def main():
    print("🚀 Starting HIGH-SPEED Flashscore Sync Engine...")
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Get Betika fixtures for TOMORROW only
    cur.execute("SELECT match_id, home, away, league FROM fixtures WHERE date(kickoff) = date('now', '+1 day')")
    betika_fixtures = cur.fetchall()
    print(f"Loaded {len(betika_fixtures)} Betika fixtures for tomorrow.")
    if not betika_fixtures:
        print("No fixtures found. Exiting.")
        conn.close(); return

    # 2. Fetch Flashscore matches (NARROW WINDOW: Yesterday to Day after tomorrow)
    print("Fetching Flashscore pool (Narrow Window)...")
    fs_pool = []
    today = datetime.now()
    # SPEEDUP 1: Only look at -1 to +3 days instead of -5 to +6
    for i in range(-1, 4): 
        date_str = (today + timedelta(days=i)).strftime('%Y-%m-%d')
        try:
            r = requests.get(f"{FLASHSCORE_API}/matches", params={'sport': 'football', 'date': date_str}, timeout=15)
            data = r.json()
            for comp in data.get('competitions', []):
                c = comp.get('competition', {})
                t_id = c.get('id')
                stage_id = c.get('stage_id')
                pair = f"{t_id}:{stage_id}" if t_id and stage_id else None
                
                for m in comp.get('matches', []):
                    fs_pool.append({
                        'id': m.get('id'), 'home': (m.get('home') or {}).get('name', ''),
                        'away': (m.get('away') or {}).get('name', ''), 'tournament_pair': pair
                    })
        except Exception as e: print(f"Error fetching FS for {date_str}: {e}")
    print(f"Flashscore pool: {len(fs_pool)} candidates.")

    # 3. Link Matches
    print("Linking matches...")
    linked_data = []
    for b_id, b_home, b_away, b_league in betika_fixtures:
        match, score, is_swapped = find_best_match(b_home, b_away, fs_pool)
        if match:
            fs_home = match['away'] if is_swapped else match['home']
            fs_away = match['home'] if is_swapped else match['away']
            cur.execute("INSERT OR REPLACE INTO match_links (betika_match_id, flashscore_match_id, fs_home, fs_away, confidence) VALUES (?, ?, ?, ?, ?)",
                        (b_id, match['id'], fs_home, fs_away, round(score, 3)))
            linked_data.append((b_id, match['id'], fs_home, fs_away, match.get('tournament_pair')))
    conn.commit()
    print(f"✅ Linked {len(linked_data)} matches.")

    # 4. Fetch Deep Intelligence IN PARALLEL
    print(f"\nFetching deep stats for {len(linked_data)} matches (Parallel Mode)...")
    results = []
    
    # SPEEDUP 2: Use 5 threads to fetch data simultaneously
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_single_match, data): data for data in linked_data}
        for i, future in enumerate(as_completed(futures)):
            res = future.result()
            if res: results.append(res)
            if (i+1) % 20 == 0: print(f"  Processed {i+1}/{len(linked_data)} matches...")

    # 5. Batch Save to Database
    print("Saving to database...")
    for res in results:
        b_id, fs_home, fs_away, t_pair = res['b_id'], res['fs_home'], res['fs_away'], res['t_pair']
        tables, extras = res['tables'], res['extras']
        
        cur.execute("""INSERT OR REPLACE INTO ultimate_stats 
            (match_id, home_team, away_team, tournament_pair, overall_table, home_table, away_table, 
             over_under_table, ht_ft_table, ht_ft_home_table, ht_ft_away_table,
             form_overall_table, form_home_table, form_away_table, ou_all, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (b_id, fs_home, fs_away, t_pair, tables.get('overall',''), tables.get('home',''), tables.get('away',''),
             tables.get('over-under',''), tables.get('ht-ft',''), tables.get('ht-ft-home',''), tables.get('ht-ft-away',''),
             tables.get('form-overall',''), tables.get('form-home',''), tables.get('form-away',''),
             tables.get('ou_all',''), datetime.now().isoformat()))

        if extras.get('h2h'):
            cur.execute("INSERT OR REPLACE INTO flashscore_h2h (match_id, home_team_name, away_team_name, h2h_data) VALUES (?, ?, ?, ?)",
                        (b_id, fs_home, fs_away, extras['h2h']))

        cur.execute("""INSERT OR REPLACE INTO match_extras 
            (betika_match_id, available_tabs, injuries, news, report, lineups, collected_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (b_id, json.dumps([k for k,v in extras.items() if v]), extras.get('injuries',''), 
             extras.get('news',''), extras.get('report',''), extras.get('lineups',''), datetime.now().isoformat()))

    conn.commit()
    conn.close()
    print(f"\n🎉 HIGH-SPEED Sync Complete! Processed {len(results)} matches.")

if __name__ == "__main__":
    main()


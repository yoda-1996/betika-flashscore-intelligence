"""
Fixed Sync Engine - Properly fetches and parses Flashscore data.
"""

import requests
import json
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set

from database import get_db_connection, initialize_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler("sync_fixed.log"),
        logging.StreamHandler()
    ]
)

FS_BASE_URL = "http://localhost:8000"

NOISE: Set[str] = {'sc', 'fc', 'united', 'city', 'real', 'cf', 'ac', 'club', 'the', 'w', 'women', 'ladies'}
ALIASES: Dict[str, str] = {
    'dragonas': 'independiente del valle', 
    'psg': 'paris saint-germain', 
    'inter': 'internazionale'
}
LINK_THRESHOLD = 0.65

def clean_name(name: str) -> str:
    if not name:
        return ""
    name = name.lower().strip()
    for alias, full_name in ALIASES.items():
        if alias in name:
            name = full_name
    words = name.split()
    cleaned_words = [w for w in words if w not in NOISE]
    cleaned_str = " ".join(cleaned_words)
    return re.sub(r'[^a-z0-9\s]', '', cleaned_str).strip()

def jaccard_sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    set_a = set(a.split())
    set_b = set(b.split())
    if not set_a or not set_b:
        return 0.0
    intersection = set_a.intersection(set_b)
    union = set_a.union(set_b)
    return len(intersection) / len(union)

def match_score(betika_home: str, betika_away: str, fs_home: str, fs_away: str) -> float:
    bh = clean_name(betika_home)
    ba = clean_name(betika_away)
    fh = clean_name(fs_home)
    fa = clean_name(fs_away)
    score_straight = (jaccard_sim(bh, fh) + jaccard_sim(ba, fa)) / 2.0
    score_swapped = (jaccard_sim(bh, fa) + jaccard_sim(ba, fh)) / 2.0
    return max(score_straight, score_swapped)


class FlashscoreSyncer:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "BetikaIntelligence/1.0"})

    def _fs_get(self, endpoint: str, params: dict = None) -> Optional[Dict]:
        try:
            url = f"{FS_BASE_URL}{endpoint}"
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logging.warning(f"Flashscore API returned {response.status_code} for {endpoint}")
                return None
        except Exception as e:
            logging.error(f"Flashscore API request failed: {e}")
            return None

    def fetch_flashscore_matches(self) -> List[Dict]:
        all_matches = []
        today = datetime.now()
        for i in range(-3, 5):
            target_date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            logging.info(f"Fetching Flashscore matches for {target_date}...")
            data = self._fs_get("/matches", params={"sport": "football", "date": target_date})
            if data and "competitions" in data:
                for comp in data["competitions"]:
                    for match in comp.get("matches", []):
                        match['tournament_name'] = comp.get('competition', {}).get('name', '')
                        match['tournament_slug'] = comp.get('competition', {}).get('slug', '')
                        all_matches.append(match)
        logging.info(f"Total Flashscore matches fetched: {len(all_matches)}")
        return all_matches

    def link_matches(self, betika_fixtures: List[Dict], fs_matches: List[Dict]):
        conn = get_db_connection()
        cursor = conn.cursor()
        linked_count = 0

        for bf in betika_fixtures:
            best_score = 0.0
            best_match = None

            for fm in fs_matches:
                score = match_score(
                    bf['home'], bf['away'], 
                    fm['home']['name'], fm['away']['name']
                )
                if score > best_score:
                    best_score = score
                    best_match = fm

            if best_score >= LINK_THRESHOLD and best_match:
                cursor.execute("""
                    INSERT OR REPLACE INTO match_links 
                    (betika_match_id, flashscore_match_id, fs_home, fs_away, confidence)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    bf['match_id'], 
                    best_match['id'], 
                    best_match['home']['name'], 
                    best_match['away']['name'], 
                    best_score
                ))
                linked_count += 1
                logging.info(f"Linked: {bf['home']} vs {bf['away']} -> {best_match['home']['name']} vs {best_match['away']['name']} ({best_score:.2f})")

        conn.commit()
        conn.close()
        logging.info(f"✅ Linked {linked_count} matches.")

    def extract_form_from_events(self, events: List[Dict], team_name: str) -> str:
        """Extract form string (W/D/L) from match events for a specific team."""
        form = []
        for event in events[:5]:  # Last 5 matches
            home_team = event.get('homeTeam', {}).get('name', '')
            away_team = event.get('awayTeam', {}).get('name', '')
            home_score = event.get('homeScore', {}).get('current', 0)
            away_score = event.get('awayScore', {}).get('current', 0)
            
            # Determine if this team is home or away
            is_home = team_name.lower() in home_team.lower()
            
            if is_home:
                team_score = home_score
                opp_score = away_score
            else:
                team_score = away_score
                opp_score = home_score
            
            if team_score > opp_score:
                form.append('W')
            elif team_score < opp_score:
                form.append('L')
            else:
                form.append('D')
        
        return ''.join(form) if form else 'Unknown'

    def fetch_and_save_deep_stats(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM match_links")
        links = cursor.fetchall()
        
        collected_at = datetime.now().isoformat()

        for link in links:
            betika_id = link['betika_match_id']
            fs_id = link['flashscore_match_id']
            fs_home = link['fs_home']
            fs_away = link['fs_away']
            
            logging.info(f"Fetching deep stats for Betika ID: {betika_id} (FS ID: {fs_id})")

            # 1. Fetch H2H data
            h2h_data = self._fs_get("/matches/h2h", params={"match": fs_id})
            if h2h_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO flashscore_h2h 
                    (match_id, home_team_name, away_team_name, h2h_data)
                    VALUES (?, ?, ?, ?)
                """, (betika_id, fs_home, fs_away, json.dumps(h2h_data)))
                
                # Extract form from H2H events
                events = h2h_data.get('events', [])
                home_form = self.extract_form_from_events(events, fs_home)
                away_form = self.extract_form_from_events(events, fs_away)
                
                # Extract H2H last 5 scores
                h2h_scores = []
                for event in events[:5]:
                    home_team = event.get('homeTeam', {}).get('name', '')
                    away_team = event.get('awayTeam', {}).get('name', '')
                    home_score = event.get('homeScore', {}).get('current', 0)
                    away_score = event.get('awayScore', {}).get('current', 0)
                    h2h_scores.append(f"{home_team} {home_score}-{away_score} {away_team}")
                
                h2h_last5 = ' | '.join(h2h_scores) if h2h_scores else 'Unknown'
                
                cursor.execute("""
                    INSERT OR REPLACE INTO deep_stats 
                    (match_id, home_form_last5, away_form_last5, h2h_last5)
                    VALUES (?, ?, ?, ?)
                """, (betika_id, home_form, away_form, h2h_last5))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO deep_stats 
                    (match_id, home_form_last5, away_form_last5, h2h_last5)
                    VALUES (?, ?, ?, ?)
                """, (betika_id, 'Unknown', 'Unknown', 'Unknown'))

            # 2. Fetch Match Extras
            injuries = self._fs_get("/matches/missing-players", params={"match": fs_id})
            news = self._fs_get("/matches/news", params={"match": fs_id})
            lineups = self._fs_get("/matches/lineups", params={"match": fs_id})
            summary = self._fs_get("/matches/summary", params={"match": fs_id})
            
            details = self._fs_get("/matches/details", params={"match": fs_id})
            available_tabs = []
            tournament_id = None
            if details:
                available_tabs = details.get('available_tabs', [])
                if 'tournament' in details:
                    tournament_id = details['tournament'].get('id') or details['tournament'].get('slug')

            cursor.execute("""
                INSERT OR REPLACE INTO match_extras 
                (betika_match_id, available_tabs, injuries, news, report, lineups, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                betika_id, 
                json.dumps(available_tabs), 
                json.dumps(injuries) if injuries else None,
                json.dumps(news) if news else None,
                json.dumps(summary) if summary else None,
                json.dumps(lineups) if lineups else None,
                collected_at
            ))

            # 3. Fetch Standings
            if tournament_id:
                standings = self._fs_get("/tournaments/standings", params={"tournament": tournament_id})
                ou_standings = self._fs_get("/tournaments/standings", params={"tournament": tournament_id, "type": "over-under"})
                
                cursor.execute("""
                    INSERT OR REPLACE INTO ultimate_stats 
                    (match_id, home_team, away_team, tournament_pair, overall_table, home_table, away_table, over_under_table, ht_ft_table, form_overall_table, form_home_table, form_away_table, ou_all, collected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    betika_id, fs_home, fs_away, str(tournament_id),
                    json.dumps(standings) if standings else None,
                    None, None,
                    json.dumps(ou_standings) if ou_standings else None,
                    None, None, None, None,
                    json.dumps(ou_standings) if ou_standings else None,
                    collected_at
                ))
            else:
                logging.warning(f"No tournament ID for {betika_id}")

        conn.commit()
        conn.close()
        logging.info("✅ Deep stats fetching complete.")

    def run(self):
        logging.info("="*60)
        logging.info("Starting Flashscore Sync Engine (Fixed)")
        logging.info("="*60)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fixtures")
        betika_fixtures = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if not betika_fixtures:
            logging.error("No Betika fixtures found in database. Run main.py first.")
            return

        fs_matches = self.fetch_flashscore_matches()
        if not fs_matches:
            logging.error("Could not fetch Flashscore matches. Is the API running?")
            return

        self.link_matches(betika_fixtures, fs_matches)
        self.fetch_and_save_deep_stats()
        
        logging.info("Sync Engine Complete.")


if __name__ == "__main__":
    initialize_db()
    syncer = FlashscoreSyncer()
    syncer.run()

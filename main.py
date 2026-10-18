"""
Step 2: Betika Scraper
Fetches upcoming football fixtures and odds from Betika and saves them to SQLite.
"""

import requests
import time
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Import our database functions
from database import get_db_connection, initialize_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler("betika_scraper.log"),
        logging.StreamHandler()
    ]
)

BASE_URL = "https://api.betika.com"

class BetikaScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.betika.com",
            "Referer": "https://www.betika.com/en-ke/",
        })

    def _make_request(self, url: str, params: dict, max_retries: int = 3) -> dict:
        """Makes a request with exponential backoff for rate limiting."""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    wait_time = (2 ** attempt)
                    logging.warning(f"Rate limited (429). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logging.error(f"HTTP {response.status_code} for {url}: {e}")
                    return {}
            except requests.exceptions.RequestException as e:
                logging.error(f"Request failed: {e}")
                time.sleep(2)
        return {}

    def fetch_tomorrow_matches(self) -> List[Dict[str, Any]]:
        """Fetches all soccer matches for tomorrow."""
        tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        logging.info(f"Fetching matches for date: {tomorrow_date}")
        
        all_matches = []
        page = 1

        while True:
            params = {
                "sport_id": 14,       # Soccer
                "tab": "prematch",
                "per_page": 50,
                "page": page,
                "date": tomorrow_date,
                "period_id": 1        # Tomorrow tab fallback
            }
            
            data = self._make_request(f"{BASE_URL}/v1/uo/matches", params)
            if not data:
                break

            batch = data.get("data") or []
            meta = data.get("meta") or {}

            if not batch:
                if page == 1:
                    logging.warning("No matches found. Betika may not have published tomorrow's fixtures yet.")
                break

            all_matches.extend(batch)
            total = int(meta.get("total") or 0)
            logging.info(f"Page {page}: Retrieved {len(batch)} matches (Total: {len(all_matches)}/{total})")

            if len(all_matches) >= total or len(batch) < 50:
                break
            page += 1
            time.sleep(0.3) # Polite throttling

        return all_matches

    def fetch_markets(self, parent_match_id: str) -> List[Dict[str, Any]]:
        """Fetches all market groups for a specific match."""
        params = {"parent_match_id": parent_match_id, "tab": "prematch"}
        data = self._make_request(f"{BASE_URL}/v1/uo/match", params)
        return data.get("data") or []

    def save_to_db(self, fixtures: List[Dict], all_odds: List[Dict]):
        """Saves fixtures and odds to the SQLite database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        collected_at = datetime.now().isoformat()

        # 1. Save/Update Fixtures
        fixture_data = [
            (
                f["match_id"], f["home"], f["away"], f["league"], 
                f["kickoff"], collected_at
            ) for f in fixtures
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO fixtures 
            (match_id, home, away, league, kickoff, collected_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, fixture_data)

        # 2. Save/Update Odds
        odds_data = [
            (
                o["match_id"], o["market_name"], o["sub_type_id"], 
                o["selection"], o["odd"], o["line"], collected_at
            ) for o in all_odds
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO odds 
            (match_id, market_name, sub_type_id, selection, odd, line, collected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, odds_data)

        conn.commit()
        conn.close()
        logging.info(f"✅ Saved {len(fixtures)} fixtures and {len(all_odds)} odds to database.")

    def run(self):
        logging.info("="*60)
        logging.info("Starting Betika Scraper")
        logging.info("="*60)

        matches = self.fetch_tomorrow_matches()
        if not matches:
            logging.error("No matches found. Exiting.")
            return

        logging.info(f"Found {len(matches)} matches. Fetching detailed markets...")
        
        fixtures_to_save = []
        all_odds_to_save = []

        for idx, match in enumerate(matches, 1):
            mid = str(match.get("parent_match_id") or match.get("match_id") or match.get("id") or "")
            if not mid:
                continue

            home = match.get("home_team") or "Home"
            away = match.get("away_team") or "Away"
            league = match.get("competition_name") or match.get("category") or "Unknown League"
            kickoff = match.get("start_time") or ""

            logging.info(f"[{idx}/{len(matches)}] {home} vs {away}")

            # Fetch markets
            raw_groups = self.fetch_markets(mid)
            
            # Parse and flatten odds for database insertion
            seen_ids = set()
            for group in raw_groups:
                if not isinstance(group, dict):
                    continue
                
                sub_type_id = str(group.get("sub_type_id") or "")
                market_name = group.get("name") or sub_type_id or "unknown"
                odds_list = group.get("odds") or []

                if not sub_type_id or sub_type_id in seen_ids:
                    continue
                seen_ids.add(sub_type_id)

                for o in odds_list:
                    if not isinstance(o, dict):
                        continue
                    
                    odd_value = o.get("odd_value")
                    if odd_value is None:
                        continue
                    
                    try:
                        val = round(float(odd_value), 3)
                    except (ValueError, TypeError):
                        continue
                    
                    if not (1.001 <= val <= 1000):
                        continue

                    line = o.get("special_bet_value") or ""
                    all_odds_to_save.append({
                        "match_id": mid,
                        "market_name": market_name,
                        "sub_type_id": sub_type_id,
                        "selection": o.get("odd_key") or o.get("display") or "?",
                        "odd": val,
                        "line": line if line else None
                    })

            fixtures_to_save.append({
                "match_id": mid,
                "home": home,
                "away": away,
                "league": league,
                "kickoff": kickoff
            })

            time.sleep(0.4) # Throttle to avoid 429

        # Save everything to the database
        self.save_to_db(fixtures_to_save, all_odds_to_save)
        logging.info("Betika Scraper Complete.")


if __name__ == "__main__":
    # Ensure DB is initialized before running
    initialize_db()
    
    scraper = BetikaScraper()
    scraper.run()

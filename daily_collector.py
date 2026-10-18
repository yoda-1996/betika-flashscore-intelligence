"""
Daily Betika Fixture and Odds Collector
Automatically calculates "tomorrow's" date and scrapes all matches and markets.
Outputs to JSON (raw) and CSV (structured).
"""

import json
import time
import logging
import requests
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# --- Configuration ---
OUT_DIR = Path("betika_data")
OUT_DIR.mkdir(exist_ok=True)

EAT_TZ = ZoneInfo("Africa/Nairobi")
BASE_URL = "https://api.betika.com"

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler(OUT_DIR / "daily_collector.log"),
        logging.StreamHandler()
    ]
)

class DailyBetikaCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.betika.com",
            "Referer": "https://www.betika.com/en-ke/",
        })

    def _make_request(self, url: str, params: dict, max_retries: int = 3) -> Optional[dict]:
        """Handles requests with exponential backoff for rate limiting."""
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
                    return None
            except requests.exceptions.RequestException as e:
                logging.error(f"Request failed: {e}")
                time.sleep(2)
        return None

    def fetch_tomorrow_matches(self) -> list:
        """Fetches matches for tomorrow. Tries 'date' param, falls back to 'period_id=1'."""
        tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        logging.info(f"Target date for scraping: {tomorrow_date}")
        
        all_matches = []
        page = 1

        while True:
            # Try both date and period_id=1 (Tomorrow tab) to ensure compatibility
            params = {
                "sport_id": 14,
                "tab": "prematch",
                "per_page": 50,
                "page": page,
                "date": tomorrow_date,
                "period_id": 1 
            }
            
            data = self._make_request(f"{BASE_URL}/v1/uo/matches", params)
            if not data:
                break

            batch = data.get("data") or []
            meta = data.get("meta") or {}

            if not batch:
                if page == 1:
                    logging.warning("No matches found. Betika may not have published tomorrow's fixtures yet, or the API parameters have changed.")
                break

            all_matches.extend(batch)
            total = int(meta.get("total") or 0)
            logging.info(f"Page {page}: Retrieved {len(batch)} matches (Total: {len(all_matches)}/{total})")

            if len(all_matches) >= total or len(batch) < 50:
                break
            page += 1
            time.sleep(0.3)

        return all_matches

    def fetch_markets(self, parent_match_id: str) -> list:
        params = {"parent_match_id": parent_match_id, "tab": "prematch"}
        data = self._make_request(f"{BASE_URL}/v1/uo/match", params)
        return data.get("data") or [] if data else []

    def parse_markets(self, market_groups: list) -> list:
        markets = []
        seen_ids = set()

        for group in market_groups:
            if not isinstance(group, dict):
                continue

            sub_type_id = str(group.get("sub_type_id") or "")
            name = group.get("name") or sub_type_id or "unknown"
            odds_list = group.get("odds") or []

            if not sub_type_id or sub_type_id in seen_ids:
                continue
            seen_ids.add(sub_type_id)

            selections = []
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
                selections.append({
                    "selection": o.get("odd_key") or o.get("display") or "?",
                    "odd": val,
                    "line": line if line else None,
                    "display": o.get("display"),
                    "outcome_id": o.get("outcome_id"),
                })

            if selections:
                markets.append({
                    "sub_type_id": sub_type_id,
                    "market_name": name,
                    "selections": selections,
                })

        return markets

    def convert_to_eat(self, time_str: str) -> str:
        if not time_str:
            return "Unknown"
        try:
            time_str = time_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(time_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
            eat_dt = dt.astimezone(EAT_TZ)
            return eat_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        except Exception:
            return time_str

    def run(self):
        logging.info("="*60)
        logging.info("Starting Daily Automated Collection for TOMORROW")
        logging.info("="*60)

        matches = self.fetch_tomorrow_matches()
        if not matches:
            logging.error("No matches found. Exiting.")
            return

        logging.info(f"Found {len(matches)} matches. Fetching detailed markets...")
        
        results = []
        total = len(matches)

        for idx, match in enumerate(matches, 1):
            mid = str(match.get("parent_match_id") or match.get("match_id") or match.get("id") or "")
            if not mid:
                continue

            home = match.get("home_team") or "Home"
            away = match.get("away_team") or "Away"
            league = match.get("competition_name") or match.get("category") or "Unknown League"
            raw_kickoff = match.get("start_time") or ""
            eat_kickoff = self.convert_to_eat(raw_kickoff)

            logging.info(f"[{idx}/{total}] {home} vs {away} ({eat_kickoff})")

            raw_groups = self.fetch_markets(mid)
            markets = self.parse_markets(raw_groups)
            
            if raw_groups:
                raw_file = OUT_DIR / f"raw_{mid}.json"
                raw_file.write_text(json.dumps(raw_groups, indent=2, ensure_ascii=False))

            results.append({
                "match_id": mid,
                "home_team": home,
                "away_team": away,
                "league": league,
                "kickoff_eat": eat_kickoff,
                "market_count": len(markets),
                "markets": markets,
            })

            time.sleep(0.4)

        self._save_outputs(results)

    def _save_outputs(self, results: list):
        tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        json_path = OUT_DIR / f"{tomorrow_date}_matches_full.json"
        json_payload = {
            "scraped_at": datetime.now().isoformat(),
            "target_date": tomorrow_date,
            "total_matches": len(results),
            "matches_with_markets": sum(1 for r in results if r["market_count"] > 0),
            "matches": results,
        }
        json_path.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False))
        logging.info(f"Saved JSON to: {json_path}")

        csv_path = OUT_DIR / f"{tomorrow_date}_markets_flat.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "match_id", "kickoff_eat", "league", "home_team", "away_team",
                "market_name", "sub_type_id", "selection", "odd", "line"
            ])
            for match in results:
                for market in match["markets"]:
                    for sel in market["selections"]:
                        writer.writerow([
                            match["match_id"], match["kickoff_eat"], match["league"],
                            match["home_team"], match["away_team"], market["market_name"],
                            market["sub_type_id"], sel["selection"], sel["odd"], sel["line"] or ""
                        ])
        logging.info(f"Saved CSV to: {csv_path}")
        logging.info("Daily Collection Complete.")


if __name__ == "__main__":
    collector = DailyBetikaCollector()
    collector.run()

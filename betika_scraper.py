"""
betika_scraper.py

Scrapes ALL tomorrow football matches + FULL markets/odds from Betika Kenya.
Uses Betika's public REST API and saves directly to the SQLite database.

Run:  python betika_scraper.py
"""

import json
import time
import random
import requests
from datetime import datetime, timedelta
from pathlib import Path
from database import get_db_connection  # <-- ADDED: Database connection

OUT_DIR = Path("betika_data")
OUT_DIR.mkdir(exist_ok=True)

BASE = "https://api.betika.com"
HEADERS = {
    "User-Agent":      "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept":          "application/json, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin":          "https://www.betika.com",
    "Referer":         "https://www.betika.com/en-ke/",
}

def fetch_matches() -> list:
    """
    GET /v1/uo/matches
    sport_id=14  Soccer
    period_id=1  Tomorrow tab
    """
    print("Fetching tomorrow Soccer matches...")
    all_matches = []
    page = 1

    while True:
        try:
            r = requests.get(
                f"{BASE}/v1/uo/matches",
                params={
                    "sport_id":  14,
                    "period_id": 1,  # 1 = Tomorrow
                    "per_page":  50,
                    "page":      page,
                    "tab":       "prematch",
                },
                headers=HEADERS,
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            batch = data.get("data") or []
            meta = data.get("meta") or {}
        except Exception as e:
            print(f"  Page {page} error: {e}")
            break

        if not batch:
            break

        all_matches.extend(batch)
        total = int(meta.get("total") or 0)
        print(f"  Page {page}: +{len(batch)} ({len(all_matches)}/{total})")

        if len(all_matches) >= total or len(batch) < 50:
            break

        page += 1
        time.sleep(random.uniform(0.2, 0.4))

    return all_matches

def fetch_markets(parent_match_id) -> list:
    try:
        r = requests.get(
            f"{BASE}/v1/uo/match",
            params={"parent_match_id": parent_match_id, "tab": "prematch"},
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("data") or []
    except Exception as e:
        print(f"  Markets error for {parent_match_id}: {e}")
        return []

def parse_markets(market_groups: list) -> list:
    markets = []
    seen_ids = set()

    for group in market_groups:
        if not isinstance(group, dict):
            continue

        sub_type_id = str(group.get("sub_type_id") or "")
        name        = group.get("name") or sub_type_id or "unknown"
        odds_list   = group.get("odds") or []

        if sub_type_id and sub_type_id in seen_ids:
            continue
        if sub_type_id:
            seen_ids.add(sub_type_id)

        selections = []
        for o in odds_list:
            if not isinstance(o, dict):
                continue
            val = o.get("odd_value")
            if val is None:
                continue
            try:
                val = round(float(val), 3)
            except Exception:
                continue
            if not (1.001 <= val <= 1000):
                continue

            line = o.get("special_bet_value") or ""
            selections.append({
                "selection":  o.get("odd_key") or o.get("display") or "?",
                "odd":        val,
                "line":       line if line else None,
                "display":    o.get("display"),
                "outcome_id": o.get("outcome_id"),
            })

        if selections:
            markets.append({
                "sub_type_id": sub_type_id,
                "market_name": name,
                "selections":  selections,
            })

    return markets

def display_markets(markets: list):
    for m in markets:
        sels = []
        for s in m["selections"]:
            entry = f"{s['selection']}={s['odd']}"
            if s['line']:
                entry += f"@{s['line']}"
            sels.append(entry)
        sels_str = ", ".join(sels)
        print(f"    [{m['sub_type_id']:>3}] {m['market_name']:<35} {sels_str}")

def run():
    today_str = datetime.now().strftime("%Y-%m-%d")
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    matches = fetch_matches()
    if not matches:
        print("\nNo matches found.")
        return

    print(f"\n{len(matches)} matches found. Fetching full markets and saving to DB...\n")
    print("-" * 70)

    # --- DATABASE SETUP ---
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clear old fixtures/odds for tomorrow to prevent duplicates if run multiple times
    cursor.execute("DELETE FROM fixtures WHERE date(kickoff) = ?", (tomorrow_str,))
    # We also delete odds for matches that will be inserted, to be safe
    conn.commit()

    results = []
    total = len(matches)

    for idx, match in enumerate(matches, 1):
        mid     = str(match.get("parent_match_id") or match.get("match_id") or match.get("id") or "")
        home    = match.get("home_team")      or "Home"
        away    = match.get("away_team")      or "Away"
        league  = match.get("competition_name") or match.get("category") or ""
        kickoff = match.get("start_time")     or ""
        # STRICT DATE CHECK: Only keep matches for tomorrow
        if tomorrow_str not in str(kickoff):
            continue  # Skip this match if it's not for tomorrow

        print(f"\n[{idx:>4}/{total}] {home} vs {away}")
        print(f"    League  : {league}")
        print(f"    Kickoff : {kickoff}")

        raw_groups = fetch_markets(mid)
        markets    = parse_markets(raw_groups)
        mc         = len(markets)

        if mc > 0:
            print(f"    Markets : {mc}")
            # display_markets(markets) # Commented out to keep terminal clean, uncomment if you want to see them
        else:
            print("    No markets found")

        if raw_groups:
            (OUT_DIR / f"raw_{mid}.json").write_text(
                json.dumps(raw_groups, ensure_ascii=False)
            )

        # --- SAVE TO DATABASE ---
        try:
            # 1. Save Fixture
            cursor.execute("""
                INSERT OR REPLACE INTO fixtures 
                (match_id, home, away, league, kickoff)
                VALUES (?, ?, ?, ?, ?)
            """, (mid, home, away, league, kickoff))

            # 2. Save Odds
            for m in markets:
                market_name = m["market_name"]
                for s in m["selections"]:
                    cursor.execute("""
                        INSERT OR REPLACE INTO odds 
                        (match_id, market_name, selection, odd, line)
                        VALUES (?, ?, ?, ?, ?)
                    """, (mid, market_name, s["selection"], s["odd"], s["line"] or ""))
            
            conn.commit()
        except Exception as e:
            print(f"    DB Error: {e}")

        results.append({
            "match_id":     mid,
            "home":         home,
            "away":         away,
            "league":       league,
            "kickoff":      kickoff,
            "market_count": mc,
            "markets":      markets,
        })

        time.sleep(random.uniform(0.1, 0.3)) # Slightly faster since we are saving to DB

    # Close DB connection
    conn.close()

    out_path = OUT_DIR / f"{today_str}_matches.json"
    out_path.write_text(json.dumps(
        {
            "scraped_at":    datetime.now().isoformat(),
            "date":          tomorrow_str,
            "total_matches": len(results),
            "with_markets":  sum(1 for r in results if r["market_count"] > 0),
            "matches":       results,
        },
        indent=2,
        ensure_ascii=False,
    ))

    counts = [r["market_count"] for r in results]
    filled = [c for c in counts if c > 0]

    print(f"\n{'-'*70}")
    print(f"SCRAPE & DB SAVE COMPLETE")
    print(f"  Matches processed : {len(results)}")
    print(f"  With markets      : {len(filled)}")
    if filled:
        print(f"  Avg markets/match : {sum(filled)/len(filled):.1f}")
    print(f"  Output file       : {out_path}")
    print(f"  Database          : ✅ Updated with tomorrow's fixtures & odds")
    print(f"{'-'*70}")

if __name__ == "__main__":
    run()

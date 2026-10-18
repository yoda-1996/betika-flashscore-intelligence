"""
Betika Odds Scraper - Tomorrow's Matches Only
Scrapes matches from 00:00 of tomorrow to 00:00 of the day after.
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import json
import re
from datetime import datetime, timedelta
from database import get_db_connection

BETIKA_URL = "https://www.betika.com/en-ke/sports/football"

def get_tomorrow_date():
    """Returns tomorrow's date in YYYY-MM-DD format."""
    tomorrow = datetime.now() + timedelta(days=1)
    return tomorrow.strftime('%Y-%m-%d')

def parse_kickoff_time(time_str):
    """Converts kickoff time string to datetime object."""
    try:
        # Try common formats
        for fmt in ['%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M', '%H:%M']:
            try:
                return datetime.strptime(time_str, fmt)
            except:
                continue
    except:
        return None

def scrape_betika_tomorrow():
    print("="*60)
    print("SCRAPING BETIKA ODDS FOR TOMORROW'S MATCHES")
    print("="*60)
    
    target_date = get_tomorrow_date()
    print(f"Target date: {target_date}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clear old fixtures for tomorrow (if any)
    cursor.execute("DELETE FROM fixtures WHERE date(kickoff) = ?", (target_date,))
    conn.commit()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01'
    }
    
    # Try the API endpoint first (Betika often uses this)
    api_url = f"https://www.betika.com/api/v1/sports/football/events?date={target_date}"
    
    try:
        print(f"Fetching from API: {api_url}")
        r = requests.get(api_url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            events = data.get('data', []) if isinstance(data, dict) else data
            
            print(f"Found {len(events)} events for {target_date}")
            
            match_count = 0
            for event in events:
                try:
                    home = event.get('home', '')
                    away = event.get('away', '')
                    league = event.get('league', event.get('competition', ''))
                    kickoff = event.get('kickoff', event.get('start_time', ''))
                    event_id = event.get('id', event.get('event_id', ''))
                    
                    if not home or not away:
                        continue
                    
                    # Insert fixture
                    cursor.execute("""
                        INSERT OR IGNORE INTO fixtures 
                        (match_id, home, away, league, kickoff)
                        VALUES (?, ?, ?, ?, ?)
                    """, (str(event_id), home, away, league, kickoff))
                    
                    # Fetch odds for this match
                    odds_url = f"https://www.betika.com/api/v1/sports/football/events/{event_id}/odds"
                    odds_r = requests.get(odds_url, headers=headers, timeout=10)
                    
                    if odds_r.status_code == 200:
                        odds_data = odds_r.json()
                        markets = odds_data.get('data', []) if isinstance(odds_data, dict) else odds_data
                        
                        for market in markets:
                            market_name = market.get('market_name', market.get('name', ''))
                            selections = market.get('selections', market.get('outcomes', []))
                            
                            for sel in selections:
                                selection = sel.get('name', sel.get('selection', ''))
                                odd = sel.get('odd', sel.get('odds', 0))
                                line = sel.get('line', sel.get('handicap', ''))
                                
                                cursor.execute("""
                                    INSERT OR IGNORE INTO odds 
                                    (match_id, market_name, selection, odd, line)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (str(event_id), market_name, selection, float(odd), str(line)))
                    
                    match_count += 1
                    if match_count % 20 == 0:
                        print(f"  Processed {match_count} matches...")
                        
                except Exception as e:
                    pass
            
            conn.commit()
            print(f"\n✅ Scraped {match_count} matches for {target_date}")
            return
            
    except Exception as e:
        print(f"API failed: {e}")
    
    # Fallback: Try scraping the HTML page
    print("\nTrying HTML scraping fallback...")
    try:
        r = requests.get(BETIKA_URL, headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            # Parse HTML structure (adjust selectors based on actual Betika HTML)
            print("HTML scraping would go here - adjust selectors based on actual page structure")
    except Exception as e:
        print(f"HTML scraping failed: {e}")
    
    conn.close()
    print("Scraping complete.")

if __name__ == "__main__":
    scrape_betika_tomorrow()

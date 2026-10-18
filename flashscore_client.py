"""
Flashscore Client
Connects to the local Flashscore Scraper API to get H2H, Form, and Stats.
"""

import requests
import json
from typing import Optional, Dict, List

# The local API URL provided by the Flashscore Scraper
BASE_URL = "http://localhost:8000"

class FlashscoreClient:
    def __init__(self):
        self.session = requests.Session()

    def search_team(self, team_name: str) -> Optional[Dict]:
        """Search for a team to get its Flashscore ID."""
        try:
            # Using the /search endpoint
            response = self.session.get(f"{BASE_URL}/search", params={"query": team_name, "sport": "football"})
            data = response.json()
            
            # The structure usually returns a list of results. We look for the first team match.
            # Note: The exact structure depends on the scraper version, usually data['results'] or similar.
            # Based on standard Flashscore API, we might need to look through the response.
            # For now, let's assume a standard search response.
            
            if 'results' in data:
                for item in data['results']:
                    if item.get('type') == 'team' and team_name.lower() in item.get('name', '').lower():
                        return item
                        
            return None
        except Exception as e:
            print(f"Search error: {e}")
            return None

    def get_team_form(self, team_id: str, limit: int = 5) -> List[Dict]:
        """Get recent results for a team to calculate form."""
        try:
            response = self.session.get(f"{BASE_URL}/teams/results", params={"team": team_id})
            data = response.json()
            # Return the last 'limit' matches
            return data.get('events', [])[:limit] 
        except Exception as e:
            print(f"Form error: {e}")
            return []

    def get_h2h(self, home_team_id: str, away_team_id: str) -> List[Dict]:
        """Get Head-to-Head history."""
        # The Flashscore API usually takes a match ID for H2H, but we can try to find it via team IDs
        # Or we use the /matches/h2h endpoint if it supports team IDs. 
        # According to the docs, /matches/h2h usually requires a match ID.
        # We will use a workaround: Get recent matches for Home team and filter for Away team.
        print("Note: H2H usually requires a specific Match ID from Flashscore. We will use Team Results for now.")
        return []

def main():
    client = FlashscoreClient()
    
    print("Searching for 'Arsenal'...")
    team = client.search_team("Arsenal")
    
    if team:
        print(f"Found: {team.get('name')} (ID: {team.get('id')})")
        
        print("\nFetching recent form...")
        form = client.get_team_form(team['id'])
        for match in form:
            print(f"- {match.get('homeTeam', {}).get('name')} vs {match.get('awayTeam', {}).get('name')}")
    else:
        print("Team not found.")

if __name__ == "__main__":
    main()

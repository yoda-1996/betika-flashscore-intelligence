"""
Tests different parameter formats for the standings API.
"""
import requests
import json

API = "http://localhost:8000"
TOURNAMENT_ID = "WELfKJSN"
SEASON_ID = "WELfKJSN"

print("="*60)
print("TESTING API PARAMETER FORMATS")
print("="*60)

# Test 1: tournament parameter only
print("\n1. tournament=WELfKJSN")
r = requests.get(f"{API}/tournaments/standings", params={'tournament': TOURNAMENT_ID, 'type': 'overall'}, timeout=10)
if r.status_code == 200:
    data = r.json()
    count = len(data.get('standings', []))
    print(f"   Status: {r.status_code}, Standings: {count}")
    if count > 0:
        print(f"   ✅ WORKS!")

# Test 2: tournament and season parameters
print("\n2. tournament=WELfKJSN&season=WELfKJSN")
r = requests.get(f"{API}/tournaments/standings", params={'tournament': TOURNAMENT_ID, 'season': SEASON_ID, 'type': 'overall'}, timeout=10)
if r.status_code == 200:
    data = r.json()
    count = len(data.get('standings', []))
    print(f"   Status: {r.status_code}, Standings: {count}")
    if count > 0:
        print(f"   ✅ WORKS!")

# Test 3: tournament_id and season_id parameters
print("\n3. tournament_id=WELfKJSN&season_id=WELfKJSN")
r = requests.get(f"{API}/tournaments/standings", params={'tournament_id': TOURNAMENT_ID, 'season_id': SEASON_ID, 'type': 'overall'}, timeout=10)
if r.status_code == 200:
    data = r.json()
    count = len(data.get('standings', []))
    print(f"   Status: {r.status_code}, Standings: {count}")
    if count > 0:
        print(f"   ✅ WORKS!")

# Test 4: Check if the issue is with this specific tournament
# Let's try a well-known tournament like Premier League
print("\n4. Testing with Premier League (if we can find a valid ID)")
# We'll need to find a valid tournament ID first
r = requests.get(f"{API}/matches", params={'sport': 'football', 'date': '2026-10-19'}, timeout=10)
if r.status_code == 200:
    data = r.json()
    # Find a Premier League match
    for comp in data.get('competitions', []):
        c = comp.get('competition', {})
        if 'premier' in c.get('name', '').lower() or 'england' in c.get('name', '').lower():
            t_id = c.get('id')
            s_id = c.get('season_id', c.get('id'))
            print(f"   Found: {c.get('name')} - ID: {t_id}, Season: {s_id}")
            
            # Test standings for this tournament
            r2 = requests.get(f"{API}/tournaments/standings", params={'tournament': t_id, 'type': 'overall'}, timeout=10)
            if r2.status_code == 200:
                d2 = r2.json()
                count = len(d2.get('standings', []))
                print(f"   Standings count: {count}")
                if count > 0:
                    print(f"   ✅ WORKS! First team: {d2['standings'][0].get('team', {}).get('name')}")
            break

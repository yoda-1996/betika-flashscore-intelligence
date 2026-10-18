"""
Tests multiple API variations to find the correct way to fetch standings.
"""
import requests
import json

API = "http://localhost:8000"
TEST_PAIR = "WELfKJSN:WELfKJSN"

print("="*60)
print("TESTING API VARIATIONS")
print("="*60)

# Variation 1: Full pair (current approach)
print("\n1. Full pair: WELfKJSN:WELfKJSN")
r = requests.get(f"{API}/tournaments/standings", params={'tournament': TEST_PAIR, 'type': 'overall'}, timeout=10)
if r.status_code == 200:
    data = r.json()
    count = len(data.get('standings', []))
    print(f"   Status: {r.status_code}, Standings count: {count}")
    if count > 0:
        print(f"   ✅ WORKS! First team: {data['standings'][0].get('team', {}).get('name', 'Unknown')}")

# Variation 2: Just the first ID
print("\n2. Single ID: WELfKJSN")
r = requests.get(f"{API}/tournaments/standings", params={'tournament': 'WELfKJSN', 'type': 'overall'}, timeout=10)
if r.status_code == 200:
    data = r.json()
    count = len(data.get('standings', []))
    print(f"   Status: {r.status_code}, Standings count: {count}")
    if count > 0:
        print(f"   ✅ WORKS! First team: {data['standings'][0].get('team', {}).get('name', 'Unknown')}")

# Variation 3: Try with season parameter
print("\n3. With season parameter")
r = requests.get(f"{API}/tournaments/standings", params={'tournament': TEST_PAIR, 'type': 'overall', 'season': 'WELfKJSN'}, timeout=10)
if r.status_code == 200:
    data = r.json()
    count = len(data.get('standings', []))
    print(f"   Status: {r.status_code}, Standings count: {count}")
    if count > 0:
        print(f"   ✅ WORKS!")

# Variation 4: Try a different known tournament (Premier League)
print("\n4. Different tournament: GtXxRctR:GtXxRctR")
r = requests.get(f"{API}/tournaments/standings", params={'tournament': 'GtXxRctR:GtXxRctR', 'type': 'overall'}, timeout=10)
if r.status_code == 200:
    data = r.json()
    count = len(data.get('standings', []))
    print(f"   Status: {r.status_code}, Standings count: {count}")
    if count > 0:
        print(f"   ✅ WORKS! First team: {data['standings'][0].get('team', {}).get('name', 'Unknown')}")

# Variation 5: Check what the full response looks like
print("\n5. Full response structure (first 1000 chars):")
r = requests.get(f"{API}/tournaments/standings", params={'tournament': TEST_PAIR, 'type': 'overall'}, timeout=10)
if r.status_code == 200:
    print(json.dumps(r.json(), indent=2)[:1000])

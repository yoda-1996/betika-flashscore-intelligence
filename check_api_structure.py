import requests
import json

FS_ID = "nylhpPON"  # Bayern vs Leipzig
API = "http://localhost:8000"

print("="*60)
print("CHECKING API RESPONSE STRUCTURE")
print("="*60)

# 1. Check Standings
print("\n1. MATCH STANDINGS:")
r = requests.get(f"{API}/matches/standings", params={"match": FS_ID})
if r.status_code == 200:
    data = r.json()
    print(f"   Type: {type(data)}")
    print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
    print(f"   Length: {len(data) if isinstance(data, (list, dict)) else 'N/A'}")
    if isinstance(data, dict) and 'standings' in data:
        print(f"   Has 'standings' key: YES")
        print(f"   Standings type: {type(data['standings'])}")
        if isinstance(data['standings'], list) and len(data['standings']) > 0:
            print(f"   First standing keys: {list(data['standings'][0].keys())}")
            if 'rows' in data['standings'][0]:
                print(f"   First row: {data['standings'][0]['rows'][0] if data['standings'][0]['rows'] else 'Empty'}")
    else:
        print(f"   Raw data (first 500 chars):\n{json.dumps(data, indent=2)[:500]}")
else:
    print(f"   Status: {r.status_code}")

# 2. Check H2H
print("\n2. MATCH H2H:")
r = requests.get(f"{API}/matches/h2h", params={"match": FS_ID})
if r.status_code == 200:
    data = r.json()
    print(f"   Type: {type(data)}")
    print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
    if 'events' in data:
        print(f"   Has 'events' key: YES (count: {len(data['events'])})")
        if data['events']:
            print(f"   First event keys: {list(data['events'][0].keys())}")
            print(f"   First event: {json.dumps(data['events'][0], indent=2)[:300]}")
    else:
        print(f"   Raw data (first 500 chars):\n{json.dumps(data, indent=2)[:500]}")
else:
    print(f"   Status: {r.status_code}")

# 3. Check Match Details (to get tournament info)
print("\n3. MATCH DETAILS:")
r = requests.get(f"{API}/matches/details", params={"match": FS_ID})
if r.status_code == 200:
    data = r.json()
    print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
    if 'tournament' in data:
        print(f"   Tournament: {json.dumps(data['tournament'], indent=2)}")
    if 'homeTeam' in data:
        print(f"   Home Team ID: {data['homeTeam'].get('id')}")
    if 'awayTeam' in data:
        print(f"   Away Team ID: {data['awayTeam'].get('id')}")
else:
    print(f"   Status: {r.status_code}")

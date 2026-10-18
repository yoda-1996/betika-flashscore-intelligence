"""
Debug script to check what the HT/FT API actually returns.
"""
import requests
import json

# Use the match from your screenshot
FS_ID = "YkshMFT1"  # Al-Nasr vs Hatta
API = "http://localhost:8000"

print("="*60)
print("DEBUGGING HT/FT API RESPONSE")
print("="*60)

# Test 1: Try the match endpoint
print("\n1. Testing /matches/standings?type=ht-ft")
r = requests.get(f"{API}/matches/standings", params={"match": FS_ID, "type": "ht-ft"})
print(f"   Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"   Response type: {type(data)}")
    print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
    
    if isinstance(data, dict):
        if 'standings' in data:
            print(f"   Has 'standings': YES (count: {len(data['standings'])})")
            if data['standings']:
                print(f"   First standing keys: {list(data['standings'][0].keys())}")
                print(f"   First standing: {json.dumps(data['standings'][0], indent=2)[:500]}")
        else:
            print(f"   No 'standings' key. Full response (first 500 chars):")
            print(f"   {json.dumps(data, indent=2)[:500]}")
    else:
        print(f"   Response is not a dict. First 500 chars: {str(data)[:500]}")
else:
    print(f"   Error: {r.text[:300]}")

# Test 2: Try without type parameter
print("\n2. Testing /matches/standings (no type)")
r = requests.get(f"{API}/matches/standings", params={"match": FS_ID})
print(f"   Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
    if isinstance(data, dict) and 'available_tabs' in data:
        print(f"   Available tabs: {data['available_tabs']}")

# Test 3: Try tournament endpoint
print("\n3. Testing /tournaments/standings?type=ht-ft")
# First get tournament ID from match details
r = requests.get(f"{API}/matches/details", params={"match": FS_ID})
if r.status_code == 200:
    details = r.json()
    tournament_id = details.get('tournament', {}).get('id') or details.get('competition', {}).get('id')
    print(f"   Tournament ID: {tournament_id}")
    
    if tournament_id:
        r = requests.get(f"{API}/tournaments/standings", params={"tournament": tournament_id, "type": "ht-ft"})
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
            if isinstance(data, dict) and 'standings' in data:
                print(f"   Has standings: YES (count: {len(data['standings'])})")
                if data['standings']:
                    print(f"   First standing: {json.dumps(data['standings'][0], indent=2)[:500]}")

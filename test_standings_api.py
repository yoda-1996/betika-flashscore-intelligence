"""
Tests the Flashscore API directly with a known Tournament Pair to see why data is missing.
"""
import requests
import json

API = "http://localhost:8000"
# Using a pair from your diagnostic output
TEST_PAIR = "WELfKJSN:WELfKJSN" 

print(f"Testing API for Tournament Pair: {TEST_PAIR}")
print("="*50)

# 1. Test Overall Standings
print("\n1. Testing /tournaments/standings?type=overall")
try:
    r = requests.get(f"{API}/tournaments/standings", params={'tournament': TEST_PAIR, 'type': 'overall'}, timeout=10)
    print(f"Status Code: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"Response Keys: {list(data.keys())}")
        
        if 'standings' in data:
            print(f"✅ SUCCESS: Found 'standings' key with {len(data['standings'])} items.")
        else:
            print(f"❌ FAIL: 'standings' key missing.")
            print(f"Full Response (first 500 chars): {json.dumps(data, indent=2)[:500]}")
    else:
        print(f"❌ HTTP Error: {r.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}")

# 2. Test Over/Under
print("\n2. Testing /tournaments/standings?type=over-under&line=2.5")
try:
    r = requests.get(f"{API}/tournaments/standings", params={'tournament': TEST_PAIR, 'type': 'over-under', 'line': '2.5'}, timeout=10)
    print(f"Status Code: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        if 'standings' in data:
            print(f"✅ SUCCESS: Found O/U data.")
        else:
            print(f"❌ FAIL: 'standings' key missing.")
            print(f"Response: {json.dumps(data, indent=2)[:300]}")
            
except Exception as e:
    print(f"❌ Exception: {e}")

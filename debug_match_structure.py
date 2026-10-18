import requests
import json

API = "http://localhost:8000"

print("Fetching matches for tomorrow to inspect structure...")
r = requests.get(f"{API}/matches", params={'sport': 'football', 'date': '2026-10-19'}, timeout=10)

if r.status_code == 200:
    data = r.json()
    comps = data.get('competitions', [])
    
    if comps:
        # Look at the first competition
        comp = comps[0].get('competition', {})
        print(f"\n--- Competition Structure ---")
        print(json.dumps(comp, indent=2))
        
        c_id = comp.get('id')
        s_id = comp.get('season_id')
        name = comp.get('name')
        
        print(f"\n--- Testing Standings for {name} ---")
        print(f"ID: {c_id}")
        print(f"Season ID: {s_id}")
        
        # Test 1: Just ID
        print("\n1. Try tournament=id")
        r1 = requests.get(f"{API}/tournaments/standings", params={'tournament': c_id, 'type': 'overall'}, timeout=10)
        if r1.status_code == 200:
            d1 = r1.json()
            print(f"   Count: {len(d1.get('standings', []))}")
            
        # Test 2: ID and Season
        if s_id:
            print(f"\n2. Try tournament=id&season={s_id}")
            r2 = requests.get(f"{API}/tournaments/standings", params={'tournament': c_id, 'season': s_id, 'type': 'overall'}, timeout=10)
            if r2.status_code == 200:
                d2 = r2.json()
                print(f"   Count: {len(d2.get('standings', []))}")
                if len(d2.get('standings', [])) > 0:
                    print("   ✅ THIS WORKS!")
                    
        # Test 3: Just Season ID as tournament
        if s_id:
            print(f"\n3. Try tournament=season_id ({s_id})")
            r3 = requests.get(f"{API}/tournaments/standings", params={'tournament': s_id, 'type': 'overall'}, timeout=10)
            if r3.status_code == 200:
                d3 = r3.json()
                print(f"   Count: {len(d3.get('standings', []))}")
                if len(d3.get('standings', [])) > 0:
                    print("   ✅ THIS WORKS!")

    else:
        print("No competitions found.")
else:
    print(f"Error: {r.status_code}")

import requests
import json

API = "http://localhost:8000"

print("Fetching matches to find correct ID for standings...")
r = requests.get(f"{API}/matches", params={'sport': 'football', 'date': '2026-10-19'}, timeout=10)

if r.status_code == 200:
    data = r.json()
    comps = data.get('competitions', [])
    
    if comps:
        comp = comps[0].get('competition', {})
        c_id = comp.get('id')
        stage_id = comp.get('stage_id')
        template_id = comp.get('template_id')
        name = comp.get('name')
        
        print(f"\nCompetition: {name}")
        print(f"id: {c_id}")
        print(f"stage_id: {stage_id}")
        print(f"template_id: {template_id}")
        
        # Test 1: id
        print(f"\n1. Testing tournament={c_id}")
        r1 = requests.get(f"{API}/tournaments/standings", params={'tournament': c_id, 'type': 'overall'}, timeout=10)
        if r1.status_code == 200:
            d1 = r1.json()
            count = len(d1.get('standings', []))
            print(f"   Count: {count}")
            if count > 0:
                print(f"   ✅ WORKS!")
        
        # Test 2: stage_id
        if stage_id:
            print(f"\n2. Testing tournament={stage_id}")
            r2 = requests.get(f"{API}/tournaments/standings", params={'tournament': stage_id, 'type': 'overall'}, timeout=10)
            if r2.status_code == 200:
                d2 = r2.json()
                count = len(d2.get('standings', []))
                print(f"   Count: {count}")
                if count > 0:
                    print(f"   ✅ WORKS!")
        
        # Test 3: template_id
        if template_id:
            print(f"\n3. Testing tournament={template_id}")
            r3 = requests.get(f"{API}/tournaments/standings", params={'tournament': template_id, 'type': 'overall'}, timeout=10)
            if r3.status_code == 200:
                d3 = r3.json()
                count = len(d3.get('standings', []))
                print(f"   Count: {count}")
                if count > 0:
                    print(f"   ✅ WORKS!")
        
        # Test 4: id:stage_id format
        if stage_id:
            print(f"\n4. Testing tournament={c_id}:{stage_id}")
            r4 = requests.get(f"{API}/tournaments/standings", params={'tournament': f"{c_id}:{stage_id}", 'type': 'overall'}, timeout=10)
            if r4.status_code == 200:
                d4 = r4.json()
                count = len(d4.get('standings', []))
                print(f"   Count: {count}")
                if count > 0:
                    print(f"   ✅ WORKS!")

import requests
import json

FS_ID = "6TjFErJ0"  # AS Roma vs Genoa
API = "http://localhost:8000"

print("="*60)
print("DEBUGGING COMPETITION OBJECT")
print("="*60)

r = requests.get(f"{API}/matches/details", params={"match": FS_ID})
if r.status_code == 200:
    data = r.json()
    
    print("\n1. Competition object:")
    comp = data.get('competition')
    if comp:
        print(f"   Keys: {list(comp.keys()) if isinstance(comp, dict) else 'N/A'}")
        print(f"   Full object: {json.dumps(comp, indent=2)}")
    else:
        print("   ❌ No 'competition' key found")
    
    print("\n2. Tournament object:")
    tourn = data.get('tournament')
    if tourn:
        print(f"   Keys: {list(tourn.keys()) if isinstance(tourn, dict) else 'N/A'}")
        print(f"   Full object: {json.dumps(tourn, indent=2)}")
    else:
        print("   ❌ No 'tournament' key found")
        
    print("\n3. Stage object:")
    stage = data.get('stage')
    if stage:
        print(f"   Keys: {list(stage.keys()) if isinstance(stage, dict) else 'N/A'}")
        print(f"   Full object: {json.dumps(stage, indent=2)}")
else:
    print(f"❌ API returned status {r.status_code}")

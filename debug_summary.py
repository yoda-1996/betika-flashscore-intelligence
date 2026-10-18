"""
Debug script to see the exact structure of the /matches/summary endpoint.
"""
import requests
import json

# Bayern Munich vs RB Leipzig
FS_ID = "nylhpPON"
API = "http://localhost:8000"

print("="*60)
print("DEBUGGING SUMMARY STRUCTURE")
print("="*60)

r = requests.get(f"{API}/matches/summary", params={"match": FS_ID}, timeout=10)
print(f"Status: {r.status_code}")

if r.status_code == 200:
    data = r.json()
    
    print(f"\nTop-level keys: {list(data.keys())}")
    
    # Print the full structure (first 3000 chars)
    print(f"\nFull response (first 3000 chars):")
    print(json.dumps(data, indent=2)[:3000])
    
    # Try to find text fields
    print(f"\n\nSearching for long text strings (>100 chars)...")
    
    def find_text(obj, path=""):
        if isinstance(obj, str) and len(obj) > 100:
            print(f"  Found at {path}: {obj[:200]}...")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                find_text(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                find_text(item, f"{path}[{i}]")
    
    find_text(data)
else:
    print(f"Error: {r.text}")

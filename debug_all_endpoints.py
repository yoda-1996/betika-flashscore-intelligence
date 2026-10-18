"""
Check multiple endpoints to find where the Flashscore Preview text is stored.
"""
import requests
import json

FS_ID = "nylhpPON"  # Bayern Munich vs RB Leipzig
API = "http://localhost:8000"

print("="*60)
print("CHECKING MULTIPLE ENDPOINTS FOR PREVIEW TEXT")
print("="*60)

endpoints_to_check = [
    ("/matches/summary", {"match": FS_ID}),
    ("/matches/news", {"match": FS_ID}),
    ("/matches/report", {"match": FS_ID}),
    ("/matches/commentary", {"match": FS_ID}),
]

for path, params in endpoints_to_check:
    print(f"\n{'='*40}")
    print(f"Testing: {path}")
    print(f"{'='*40}")
    
    try:
        r = requests.get(f"{API}{path}", params=params, timeout=10)
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            
            # Check if it's a dict or list
            if isinstance(data, dict):
                print(f"Type: dict, Keys: {list(data.keys())[:10]}")
            elif isinstance(data, list):
                print(f"Type: list, Length: {len(data)}")
                if data:
                    print(f"First item type: {type(data[0])}")
                    if isinstance(data[0], dict):
                        print(f"First item keys: {list(data[0].keys())[:10]}")
            
            # Search for long text strings
            def find_long_text(obj, path="", max_depth=5, depth=0):
                if depth > max_depth:
                    return
                if isinstance(obj, str) and len(obj) > 100:
                    print(f"   Found text at {path}: {obj[:150]}...")
                elif isinstance(obj, dict):
                    for k, v in obj.items():
                        find_long_text(v, f"{path}.{k}", max_depth, depth+1)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj[:5]):  # Check first 5 items
                        find_long_text(item, f"{path}[{i}]", max_depth, depth+1)
            
            print(f"\n  Searching for text >100 chars...")
            find_long_text(data)
            
            # Show first 500 chars of response
            print(f"\n  Response preview (first 500 chars):")
            print(f"  {json.dumps(data, indent=2)[:500]}")
        else:
            print(f"Error: {r.text[:200]}")
    except Exception as e:
        print(f"Exception: {e}")

"""
Fixes the master pipeline to fetch ALL Over/Under lines.
"""

with open('master_pipeline.py', 'r') as f:
    content = f.read()

# Find the O/U 2.5 section and replace it with all lines
old_ou_section = """            # 10. Fetch Over/Under 2.5
            r = requests.get(f"{API}/matches/standings", params={"match": fs_id, "type": "over-under", "line": "2.5"}, timeout=10)
            time.sleep(0.2)
            ou_data = json.dumps(r.json()) if r.status_code == 200 and r.json().get('standings') else None"""

new_ou_section = """            # 10. Fetch ALL Over/Under lines (0.5 to 5.5)
            ou_all = {}
            for line in ['0.5', '1.5', '2.5', '3.5', '4.5', '5.5']:
                r = requests.get(f"{API}/matches/standings", params={"match": fs_id, "type": "over-under", "line": line}, timeout=10)
                time.sleep(0.15)
                if r.status_code == 200 and r.json().get('standings'):
                    ou_all[line] = r.json()
            ou_data = json.dumps(ou_all) if ou_all else None"""

if old_ou_section in content:
    content = content.replace(old_ou_section, new_ou_section)
    print("✅ Fixed O/U fetching to get all lines")
else:
    print("⚠️  Could not find exact O/U section")

with open('master_pipeline.py', 'w') as f:
    f.write(content)

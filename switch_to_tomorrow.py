"""
Switches the system back to scrape and display TOMORROW's matches.
"""
print("Switching system to TOMORROW mode...")

# 1. Fix Scraper (Change period_id 0 -> 1)
with open('betika_scraper.py', 'r') as f:
    content = f.read()
content = content.replace('"period_id": 0', '"period_id": 1')
content = content.replace('today_str', 'tomorrow_str') 
with open('betika_scraper.py', 'w') as f:
    f.write(content)
print("✅ Scraper updated to Tomorrow")

# 2. Fix Sync, Model, and Dashboard to look for Tomorrow
files_to_update = [
    'sync_betika_flashscore.py',
    'probability_model.py',
    'dashboard.py'
]

for file in files_to_update:
    with open(file, 'r') as f:
        content = f.read()
    # Change the SQL date filter from Today to Tomorrow
    content = content.replace("date('now')", "date('now', '+1 day')")
    with open(file, 'w') as f:
        f.write(content)
    print(f"✅ {file} updated to Tomorrow")

print("\n🎉 System is now in TOMORROW mode!")
print("Run: python betika_scraper.py to get tomorrow's games.")

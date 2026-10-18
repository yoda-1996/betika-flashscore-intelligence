"""
Switches the system to scrape and display TODAY's matches.
"""
import os

print("Switching system to TODAY mode...")

# 1. Fix Scraper (Change period_id 1 -> 0)
with open('betika_scraper.py', 'r') as f:
    content = f.read()
content = content.replace('"period_id": 1', '"period_id": 0')
# Also fix the date variable used for cleanup so it doesn't delete tomorrow's games by mistake
content = content.replace('tomorrow_str', 'today_str') 
with open('betika_scraper.py', 'w') as f:
    f.write(content)
print("✅ Scraper updated to Today")

# 2. Fix Sync, Model, and Dashboard to look for Today
files_to_update = [
    'sync_betika_flashscore.py',
    'probability_model.py',
    'dashboard.py'
]

for file in files_to_update:
    with open(file, 'r') as f:
        content = f.read()
    # Change the SQL date filter from Tomorrow to Today
    content = content.replace("date('now', '+1 day')", "date('now')")
    with open(file, 'w') as f:
        f.write(content)
    print(f"✅ {file} updated to Today")

print("\n🎉 System is now in TODAY mode!")
print("Run: python betika_scraper.py")

"""
Automatic backup system. Run this before making any changes.
Creates timestamped backups of all working files.
"""
import shutil
from datetime import datetime
from pathlib import Path

BACKUP_DIR = Path("backups")
BACKUP_DIR.mkdir(exist_ok=True)

FILES_TO_BACKUP = [
    "betika_scraper.py",
    "sync_betika_flashscore.py",
    "probability_model.py",
    "dashboard.py",
    "database.py",
]

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_folder = BACKUP_DIR / f"backup_{timestamp}"
backup_folder.mkdir()

print(f"Creating backup: {backup_folder}")

for file in FILES_TO_BACKUP:
    if Path(file).exists():
        shutil.copy(file, backup_folder / file)
        print(f"  ✅ Backed up {file}")
    else:
        print(f"  ⚠️  {file} not found, skipping")

print(f"\n Backup complete: {backup_folder}")
print("To restore: cp backups/backup_YYYYMMDD_HHMMSS/* .")

"""
Fetches the clean Flashscore Preview/Summary text for each match.
"""
import requests
import json
import time
from database import get_db_connection

API = "http://localhost:8000"

def main():
    print("Fetching Match Summary Text...")
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT betika_match_id, flashscore_match_id FROM match_links")
    links = cur.fetchall()
    
    print(f"Processing {len(links)} matches...")
    count = 0
    
    for link in links:
        betika_id = link['betika_match_id']
        fs_id = link['flashscore_match_id']
        
        try:
            # Fetch match summary
            r = requests.get(f"{API}/matches/summary", params={"match": fs_id}, timeout=10)
            time.sleep(0.2)
            
            if r.status_code == 200:
                data = r.json()
                
                # Try to find the preview text in various locations
                preview_text = None
                
                # Check common keys
                for key in ['summary', 'preview', 'text', 'description', 'content']:
                    if key in data and isinstance(data[key], str) and len(data[key]) > 50:
                        preview_text = data[key]
                        break
                
                # Check nested structures
                if not preview_text:
                    for section_key in ['home', 'away', 'match', 'data']:
                        if section_key in data and isinstance(data[section_key], dict):
                            for key in ['summary', 'preview', 'text', 'description']:
                                if key in data[section_key] and isinstance(data[section_key][key], str):
                                    preview_text = data[section_key][key]
                                    break
                            if preview_text:
                                break
                
                # Check if it's a list of text blocks
                if not preview_text and isinstance(data, list):
                    texts = []
                    for item in data:
                        if isinstance(item, str) and len(item) > 50:
                            texts.append(item)
                        elif isinstance(item, dict):
                            for key in ['text', 'content', 'summary']:
                                if key in item and isinstance(item[key], str):
                                    texts.append(item[key])
                    if texts:
                        preview_text = "\n\n".join(texts)
                
                # Save the clean text
                if preview_text:
                    cur.execute("""
                        UPDATE match_extras 
                        SET report = ?
                        WHERE betika_match_id = ?
                    """, (json.dumps({"preview": preview_text}), betika_id))
                    conn.commit()
                    count += 1
                    
                    if count % 50 == 0:
                        print(f"  ...found {count} previews so far.")
                        
        except Exception:
            pass
            
    print(f"✅ Successfully extracted {count} match previews.")
    conn.close()

if __name__ == "__main__":
    main()

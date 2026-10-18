"""
Fetches match news and converts article slugs to readable titles.
"""
import requests
import json
import time
import re
from database import get_db_connection

API = "http://localhost:8000"

def slug_to_title(slug):
    """Convert URL slug to readable title."""
    # Remove 'soccer-' prefix if present
    slug = re.sub(r'^soccer-', '', slug)
    # Replace hyphens with spaces and capitalize
    title = slug.replace('-', ' ').title()
    return title

def main():
    print("Fetching Match News/Preview...")
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
            # Try /matches/preview first
            r_preview = requests.get(f"{API}/matches/preview", params={"match": fs_id}, timeout=10)
            time.sleep(0.1)
            
            preview_text = None
            
            if r_preview.status_code == 200:
                data = r_preview.json()
                # Check if it has preview text
                if isinstance(data, dict):
                    for key in ['preview', 'summary', 'text', 'description']:
                        if key in data and isinstance(data[key], str) and len(data[key]) > 50:
                            preview_text = data[key]
                            break
            
            # If no preview, try /matches/news
            if not preview_text:
                r_news = requests.get(f"{API}/matches/news", params={"match": fs_id}, timeout=10)
                time.sleep(0.1)
                
                if r_news.status_code == 200:
                    data = r_news.json()
                    articles = data.get('articles', [])
                    
                    if articles:
                        # Convert slugs to readable titles
                        titles = []
                        for article in articles[:5]:  # Top 5 articles
                            slug = article.get('slug', '')
                            if slug:
                                title = slug_to_title(slug)
                                titles.append(f"• {title}")
                        
                        if titles:
                            preview_text = "\n".join(titles)
            
            # Save the text
            if preview_text:
                cur.execute("""
                    UPDATE match_extras 
                    SET report = ?
                    WHERE betika_match_id = ?
                """, (json.dumps({"preview": preview_text, "source": "news_articles"}), betika_id))
                conn.commit()
                count += 1
                
                if count % 50 == 0:
                    print(f"  ...found {count} previews so far.")
                    
        except Exception:
            pass
            
    print(f"✅ Successfully extracted {count} match previews/news.")
    conn.close()

if __name__ == "__main__":
    main()

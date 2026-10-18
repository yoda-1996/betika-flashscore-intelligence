Here is the complete, consolidated documentation of how the system works, combining the linking logic, the data pipeline, and the specific API endpoints. You can copy and paste the entire block below.

***

# Betika & Flashscore Intelligence System: Architecture & Mechanics

## Part 1: The Linking Engine (Bridging Betika and Flashscore)

To successfully link the Betika odds data with the Flashscore intelligence data, we had to build a "bridge" between them because the two sources speak different languages when it comes to naming teams. 

### 1. The Core Problem: Naming Discrepancies
If Betika lists a match as **"Al Khairitiyat SC vs Al Bidda SC"**, Flashscore might list the exact same match as **"Al Khairitiyath vs Al Bidda"**. A simple database search for the exact team name will fail. 

### 2. The Solution: A Fuzzy Matching Engine
Instead of looking for exact matches, we built a script that acts like a smart translator. It compares the Betika fixtures against the Flashscore fixtures using a multi-step logic process:

*   **Cleaning the Names:** First, the script strips out all the "noise" that causes mismatches. It removes suffixes like "(Country)", removes numbers, and ignores common football words like "SC", "FC", "United", "City", "Club", etc. 
*   **The Alias Dictionary:** For teams that have completely different nicknames or abbreviations (e.g., Betika saying "PSG" but Flashscore saying "Paris Saint-Germain"), we used a predefined dictionary to translate them into a common format before comparing.
*   **Similarity Scoring:** Once the names are cleaned, the script calculates a "similarity score" between the Betika team name and every Flashscore team name playing that day. It looks at how many words they share (Jaccard similarity). 
*   **Checking Orientations:** It checks both possibilities: Is the Betika Home team the Flashscore Home team? Or are they swapped? It takes whichever orientation gives the highest similarity score.

### 3. The Threshold and The "Handshake"
If the highest similarity score between a Betika match and a Flashscore match crosses a specific threshold (e.g., a 65% match or higher), the script declares them to be the same game. 

### 4. Creating the "Bridge" Table (`match_links`)
Once a match is declared a success, the script saves this connection in a dedicated database table called `match_links`. This table acts as a bridge. It stores the **Betika Match ID** on one side, and the corresponding **Flashscore Match ID** (along with the normalized team names) on the other side.

### 5. How the Dashboard Uses It
When you open your Streamlit dashboard and select a match from the Betika dropdown menu, the dashboard looks at the selected Betika ID, crosses the bridge via the `match_links` table to find the Flashscore ID, and then pulls all the deep charts, tables, and stats associated with that Flashscore ID. 

---

## Part 2: Data Pipeline (Fetching, Storing, and Displaying Stats)

To understand how we successfully pulled all the deep statistics from Flashscore and displayed them on the dashboard, you need to understand the four-part mechanical pipeline we built. 

### 1. The Engine: The Local Docker Proxy
Flashscore does not have a public API, and they actively block direct scraping. The foundational mechanic of our entire system was a local Docker container (`flashscore-scraper`) running on the computer at `localhost:8000`. 
*   **What it did:** This container reverse-engineered Flashscore's hidden websockets and translated them into clean, simple REST API endpoints (like `/tournaments/standings` or `/matches/h2h`). 
*   **Why it matters:** The Python scripts didn't talk to the internet; they talked to the local Docker container, which handled all the complex anti-bot bypassing in the background.

### 2. The Two-Tier Fetching Strategy
When fetching data, we split the fetching into two distinct tiers to save time and avoid getting blocked by Flashscore:
*   **Tournament-Level Data (Cached):** Things like League Standings, Home/Away tables, Form tables, HT/FT matrices, and Over/Under stats apply to the *entire league*, not just one match. The script fetched these once per tournament, saved them in a temporary memory cache, and applied them to every match in that league. 
*   **Match-Level Data (Individual):** Things like Head-to-Head history, Injuries, Lineups, and Match Previews are unique to a specific game. The script had to make individual API calls for every single linked match to get this data.

### 3. The Storage Strategy: JSON inside SQLite
Instead of trying to create hundreds of specific database columns for every possible stat, we used a highly flexible storage mechanic:
*   We created broad tables like `ultimate_stats` and `match_extras`.
*   When the script fetched complex data (like the HT/FT matrix or the O/U tables), it converted that entire JSON structure into a **text string** and saved it into a single database column (e.g., the `ht_ft_table` column).
*   This kept the database schema simple while allowing us to store infinitely complex nested data structures.

### 4. The Display Strategy: The Bridge and the Generic Parser
When the Streamlit dashboard opens, it only reads from the SQLite database. The display mechanics rely on two clever tricks:

*   **The Router (The Bridge Table):** When a user selects a match from the Betika dropdown, the dashboard looks at the `match_links` table, finds the corresponding Flashscore Match ID, and uses that ID to query the `ultimate_stats` and `match_extras` tables.
*   **The Universal Translator (The Generic Parser):** Because we stored complex JSON as text strings, we built a single, generic helper function to render them. Flashscore returns data in a very specific format: a list of rows where one key is always "team". 
    *   For league standings, the "team" name is the actual club name (e.g., "Arsenal").
    *   **The Clever Trick:** For the HT/FT matrix, Flashscore still uses the "team" key, but the value is the Half-Time score (e.g., "1-0", "0-0", "0-1"). The generic parser didn't need to know the difference; it just extracted the "team" name and the subsequent columns (Wins, Draws, Losses) and automatically rendered a perfect matrix table for both scenarios.

### 5. Defensive Mechanics (Crash Prevention)
To ensure the dashboard never crashed when a user selected a match that didn't have full data (like a lower-league game with no lineups), we wrapped every single database query in a "guard." Before the dashboard tried to display data, it checked if the result was empty. If it was, it simply displayed a friendly "No data available" caption instead of throwing a fatal error.

---

## Part 3: The Successful Flashscore API Endpoints

Here is the complete list of Flashscore API endpoints that worked through the local Docker proxy (`http://localhost:8000`), grouped into the two tiers discussed above.

### Tier 1: Tournament-Level Endpoints
*These endpoints use the `tournament` parameter (usually the tournament ID and season ID combined, like `WdNk9YwP:WdNk9YwP`) and return data as a JSON object containing a `"standings"` array.*

**1. League Standings**
*   **Endpoint:** `/tournaments/standings`
*   **Parameters:** `?tournament={id}&type=overall`
*   **Data:** The main league table (Rank, Team, Played, Wins, Draws, Losses, Points, etc.).

**2. Home & Away Standings**
*   **Endpoint:** `/tournaments/standings`
*   **Parameters:** `?tournament={id}&type=home` (and `type=away`)
*   **Data:** Separate tables showing how teams perform specifically at home or away.

**3. Half-Time / Full-Time (HT/FT) Matrix**
*   **Endpoint:** `/tournaments/standings`
*   **Parameters:** `?tournament={id}&type=ht-ft`
*   **Data:** A matrix showing how often teams are winning/drawing/losing at half-time and how those games finish at full-time.

**4. Form Tables (Last 5 Matches)**
*   **Endpoint:** `/tournaments/standings`
*   **Parameters:** 
    *   `?tournament={id}&type=form&line=5` (Overall form)
    *   `?tournament={id}&type=form-home&line=5` (Home form)
    *   `?tournament={id}&type=form-away&line=5` (Away form)
*   **Data:** League tables ranked purely by points earned in the last 5 games.

**5. Over/Under Goal Stats**
*   **Endpoint:** `/tournaments/standings`
*   **Parameters:** `?tournament={id}&type=over-under&line={X.X}`
*   **Data:** This endpoint was called 7 times per tournament for lines: `0.5`, `1.5`, `2.5`, `3.5`, `4.5`, `5.5`, and `6.5`. It returns tables showing how often teams go over or under those specific goal totals.

### Tier 2: Match-Level Endpoints
*These endpoints use the specific `match` parameter (the unique Flashscore Match ID) and return data specific to a single fixture.*

**6. Head-to-Head (H2H) History**
*   **Endpoint:** `/matches/h2h`
*   **Parameters:** `?match={fs_id}`
*   **Data:** The historical match results between the two specific teams, including past scores, dates, and competitions.

**7. Injuries & Suspensions**
*   **Endpoint:** `/matches/injuries`
*   **Parameters:** `?match={fs_id}`
*   **Data:** A list of missing players, categorized by team, along with the reason (injury, suspension, etc.).

**8. Team News / Articles**
*   **Endpoint:** `/matches/news`
*   **Parameters:** `?match={fs_id}`
*   **Data:** Recent news articles, press conference snippets, or team updates related to the fixture.

**9. Match Preview / Summary**
*   **Endpoint:** `/matches/summary`
*   **Parameters:** `?match={fs_id}`
*   **Data:** Textual previews, statistical summaries, and AI-generated match insights provided by Flashscore.

**10. Lineups (Predicted & Confirmed)**
*   **Endpoint:** `/matches/lineups`
*   **Parameters:** `?match={fs_id}`
*   **Data:** The starting XI, formations, coaches, and player ratings. (Note: Confirmed lineups usually only appear here about 1 hour before kickoff; before that, it might return predicted lineups or empty data).

### The Verification Endpoint
*   **Endpoint:** `/matches`
*   **Parameters:** `?sport=football&date=YYYY-MM-DD`
*   **Usage:** Used at the very beginning of the sync script to build the "pool" of all Flashscore matches for the week so they could be linked to the Betika fixtures.
### Part 4: Performance & Speed Optimizations".

To link hundreds of matches and fetch deep statistics without taking hours or getting blocked by Flashscore's anti-bot systems, we used several specific speed and efficiency optimizations in the sync script. 

Here is exactly how we achieved that speed:

### 1. The "Pool" Strategy for Linking (Local Processing)
Instead of querying the Flashscore API one-by-one to find a match (e.g., asking "Do you have Betika Match #123?"), we did the opposite:
*   **Bulk Fetch:** We made just a few API calls to grab a massive "pool" of *all* Flashscore matches for a 7-day window (today ± 3 days). 
*   **In-Memory Matching:** Once we had that pool in our computer's RAM, the script looped through the Betika fixtures and compared them against the pool using Python's fast string-matching logic (Jaccard similarity). 
*   **Why it was fast:** Network requests are slow; Python math is instant. We minimized network calls and did the heavy lifting locally.

### 2. Tournament-Level Caching (The Biggest Speedup)
This was the most critical optimization. Stats like League Standings, Form Tables, HT/FT matrices, and Over/Under tables belong to the *entire league*, not just one specific match. 
*   **The Problem:** If there are 10 Premier League matches on a Saturday, a naive script would ask the API for the Premier League standings 10 separate times.
*   **The Solution:** We created a Python dictionary called `standings_cache`. The first time the script encountered a Premier League match, it fetched the standings and saved them in this cache. For the next 9 Premier League matches, the script simply grabbed the data from the cache instantly, making **zero** extra API calls. 
*   **Result:** What would have taken 500+ API calls was reduced to just a few dozen.

### 3. "Fail Fast" Timeouts
When dealing with external APIs (even local Docker ones), sometimes a request will hang indefinitely. 
*   We set strict timeouts on every request: `timeout=10` or `timeout=15`. 
*   If the Flashscore proxy didn't respond within 10 seconds, the script immediately moved on to the next task instead of freezing the entire program for minutes.

### 4. Strategic Rate Limiting (`time.sleep`)
It sounds counterintuitive, but adding tiny pauses actually made the overall process faster and more reliable.
*   We added `time.sleep(0.2)` (a 200-millisecond pause) between API calls. 
*   **Why?** If we blasted the Docker container with 100 requests a second, it would crash, throw errors, or Flashscore would temporarily ban the IP. By spacing them out slightly, we ensured a 100% success rate, meaning the script never had to waste time retrying failed requests.

### 5. Efficient Database Writes
Writing to a SQLite database row-by-row can be slow if not handled correctly.
*   We used `INSERT OR REPLACE` statements. This meant if a match was already in the database, it updated it cleanly without throwing "Duplicate Key" errors that would crash the script.
*   We grouped our database commits. Instead of saving to the hard drive after every single match, the script built up the data in memory and committed it to the database in large batches, which is significantly faster for disk I/O.

### Summary of the Flow:
1.  **Fetch Pool** (Few API calls) -> **Match Locally** (Instant).
2.  **Fetch Tournament Stats** (One API call per league) -> **Cache in RAM** (Instant for subsequent matches).
3.  **Fetch Match Stats** (One API call per match for H2H/Lineups) -> **Sleep 0.2s** -> **Save to DB**.

This architecture allowed us to process 500+ matches, link them, and fetch dozens of data points for each in just a few minutes, rather than hours.

# 📊 Betika & Flashscore Intelligence Dashboard - Master Documentation

## 1. Project Overview
A sports betting intelligence system that scrapes odds from Betika, links them to deep statistical data from Flashscore, calculates Expected Value (EV) using a Poisson probability model, and displays "Value Bets" and "Safe Bankers" via a Streamlit dashboard.

## 2. System Architecture & Data Flow
The system operates in a strict linear pipeline. **Do not skip steps.**

1. **Scrape (Betika):** `betika_scraper.py` fetches tomorrow's fixtures and odds from Betika API. Saves to `fixtures` and `odds` tables.
2. **Link (Sync):** `sync_betika_flashscore.py` matches Betika team names to Flashscore team names. Saves links to `match_links` table.
3. **Fetch (Flashscore):** The Sync script fetches deep stats (Standings, Form, HT/FT, O/U, H2H, News) from Flashscore API. Saves to `ultimate_stats`, `flashscore_h2h`, `match_extras`.
4. **Analyze (Model):** `probability_model.py` reads H2H data, calculates Poisson probabilities, compares with Betika odds, and saves results to `value_bets`.
5. **Display (Dashboard):** `dashboard.py` reads from the database and displays the UI.

## 3. Database Schema & The "Golden Rule" of IDs

**CRITICAL RULE:** The Dashboard and Model MUST query using the **Betika Match ID**. 
The Flashscore ID is ONLY used internally by the sync script to fetch data from the API.

### Core Tables:
*   **`fixtures`**: `match_id` (Betika ID), `home`, `away`, `league`, `kickoff`.
*   **`odds`**: `match_id` (Betika ID), `market_name`, `selection`, `odd`.
*   **`match_links`**: `betika_match_id` (PK), `flashscore_match_id`, `confidence`. *This is the bridge.*
*   **`ultimate_stats`**: `match_id` (MUST be Betika ID), `overall_table`, `ht_ft_table`, `ou_all`, etc.
*   **`flashscore_h2h`**: `match_id` (MUST be Betika ID), `h2h_data`.
*   **`match_extras`**: `betika_match_id` (PK), `injuries`, `news`, `report`.
*   **`value_bets`**: `match_id` (Betika ID), `market_name`, `ev_percent`, `confidence_score`.

## 4. Script Inventory

| Script Name | Purpose |
| :--- | :--- |
| `betika_scraper.py` | Fetches tomorrow's odds from Betika API (`period_id=1`). |
| `sync_betika_flashscore.py` | Links teams and fetches ALL Flashscore data. Uses Tournament endpoint for O/U. |
| `probability_model.py` | Calculates EV using Dynamic League Averages and Time-Decay. |
| `dashboard.py` | Streamlit UI. Queries DB using `date(kickoff) = date('now', '+1 day')`. |
| `master_pipeline.py` | Runs the whole sequence automatically. |
| `backup_system.py` | Creates timestamped backups of all .py files. |

## 5. Critical API Endpoints (What Worked)

*   **Standings/Form/HT/FT:** `GET /tournaments/standings?tournament={pair}&type={type}`
    *   *Types:* `overall`, `home`, `away`, `ht-ft`, `form`, `form-home`, `form-away`.
*   **Over/Under:** `GET /tournaments/standings?tournament={pair}&type=over-under&line={line}`
    *   *Lines:* `0.5`, `1.5`, `2.5`, `3.5`, `4.5`, `5.5`.
*   **H2H:** `GET /matches/h2h?match={fs_id}`
*   **News/Extras:** `GET /matches/news?match={fs_id}`

## 6. Daily Standard Operating Procedure (SOP)

To run the system for the next day:

1.  **Backup:** `python backup_system.py`
2.  **Scrape & Sync:** `python master_pipeline.py` (This runs scraper, sync, and model).
3.  **View:** `streamlit run dashboard.py`

## 7. Troubleshooting & Lessons Learned

*   **Bug:** "No data for Over/Under" or "No H2H data".
    *   *Cause:* Data was saved using Flashscore ID instead of Betika ID.
    *   *Fix:* Ensure `sync_betika_flashscore.py` uses `b_id` in all `INSERT` statements.
*   **Bug:** Dashboard shows matches from yesterday.
    *   *Cause:* Query missing date filter.
    *   *Fix:* Ensure all dashboard queries have `WHERE date(kickoff) = date('now', '+1 day')`.
*   **Bug:** Percentages show as 0.8% instead of 80%.
    *   *Fix:* Multiply decimal probabilities by 100 in the dashboard dataframe display logic.

"""
Probability Model v3 - Refined
Features: Dynamic League Averages & Time-Decay Weighting.
"""

import sqlite3

def calculate_verbose_probs(lambda_home, lambda_away):
    # --- 1. POISSON CALCULATION (For Comparison) ---
    p_home_poisson = 0
    p_draw_poisson = 0
    p_away_poisson = 0
    for h in range(10):
        for a in range(10):
            prob = (poisson.pmf(h, lambda_home) * poisson.pmf(a, lambda_away))
            if h > a: p_home_poisson += prob
            elif h == a: p_draw_poisson += prob
            else: p_away_poisson += prob

    # --- 2. SKELLAM CALCULATION (The Main Model) ---
    p_home_skellam = skellam.sf(0, lambda_home, lambda_away)
    p_draw_skellam = skellam.pmf(0, lambda_home, lambda_away)
    p_away_skellam = skellam.cdf(-1, lambda_home, lambda_away)
    
    # Normalize Skellam
    total = p_home_skellam + p_draw_skellam + p_away_skellam
    if total > 0:
        p_home_skellam /= total
        p_draw_skellam /= total
        p_away_skellam /= total

    # --- 3. PRINT COMPARISON ---
    print(f"\n--- Model Check (Lambda H:{lambda_home:.2f} / A:{lambda_away:.2f}) ---")
    print(f"Outcome      | Poisson   | Skellam")
    print(f"Home Win     | {p_home_poisson*100:6.2f}%  | {p_home_skellam*100:6.2f}%")
    print(f"Draw         | {p_draw_poisson*100:6.2f}%  | {p_draw_skellam*100:6.2f}%")
    print(f"Away Win     | {p_away_poisson*100:6.2f}%  | {p_away_skellam*100:6.2f}%")
    print(f"------------------------------------------------")

    # --- 4. RETURN RESULTS ---
    probs = {}
    probs['Home Win'] = p_home_skellam
    probs['Draw'] = p_draw_skellam
    probs['Away Win'] = p_away_skellam
    
    lambda_total = lambda_home + lambda_away
    probs['Over 2.5'] = 1 - poisson.cdf(2, lambda_total)
    probs['Under 2.5'] = poisson.cdf(2, lambda_total)
    probs['BTTS Yes'] = (1 - poisson.pmf(0, lambda_home)) * (1 - poisson.pmf(0, lambda_away))
    probs['BTTS No'] = 1 - probs['BTTS Yes']
    
    # 1st Half Approximation (42% of goals usually happen in 1st half)
    lambda_home_1h = lambda_home * 0.42
    lambda_away_1h = lambda_away * 0.42
    p_home_1h_scores = 1 - poisson.pmf(0, lambda_home_1h)
    p_away_1h_scores = 1 - poisson.pmf(0, lambda_away_1h)
    probs['1H BTTS Yes'] = p_home_1h_scores * p_away_1h_scores
    probs['1H BTTS No'] = 1 - probs['1H BTTS Yes']
    
    return probs


def calculate_skellam_hybrid_probs(lambda_home, lambda_away):
    """
    Hybrid Model:
    - Uses Skellam Distribution for 1X2 (More accurate)
    - Uses Poisson Sum for Over/Under
    - Uses Independent Poisson for BTTS
    """
    probs = {}

    # --- 1X2 (Skellam Distribution) ---
    # P(Home Win) = P(Home Goals - Away Goals > 0)
    p_home = skellam.sf(0, lambda_home, lambda_away)
    # P(Draw) = P(Home Goals - Away Goals == 0)
    p_draw = skellam.pmf(0, lambda_home, lambda_away)
    # P(Away Win) = P(Home Goals - Away Goals < 0)
    p_away = skellam.cdf(-1, lambda_home, lambda_away)

    # Normalize to ensure they sum to 1 (handling float precision)
    total_1x2 = p_home + p_draw + p_away
    probs['Home Win'] = p_home / total_1x2
    probs['Draw'] = p_draw / total_1x2
    probs['Away Win'] = p_away / total_1x2

    # --- Over/Under 2.5 (Poisson Sum) ---
    # The sum of two independent Poisson variables is also Poisson
    lambda_total = lambda_home + lambda_away
    probs['Over 2.5'] = 1 - poisson.cdf(2, lambda_total)
    probs['Under 2.5'] = poisson.cdf(2, lambda_total)

    # --- BTTS (Independent Poissons) ---
    p_home_scores = 1 - poisson.pmf(0, lambda_home)
    p_away_scores = 1 - poisson.pmf(0, lambda_away)
    
    probs['BTTS Yes'] = p_home_scores * p_away_scores
    probs['BTTS No'] = 1 - probs['BTTS Yes']

    # --- 1st Half Approximation ---
    lambda_home_1h = lambda_home * 0.42
    lambda_away_1h = lambda_away * 0.42

    p_home_1h_scores = 1 - poisson.pmf(0, lambda_home_1h)
    p_away_1h_scores = 1 - poisson.pmf(0, lambda_away_1h)
    
    probs['1H BTTS Yes'] = p_home_1h_scores * p_away_1h_scores
    probs['1H BTTS No'] = 1 - probs['1H BTTS Yes']

    return probs

from scipy.stats import skellam, poisson
import json
import math
from scipy.stats import poisson
from database import get_db_connection

# --- Configuration ---
# We will calculate these dynamically now, but keep defaults as fallback
DEFAULT_AVG_HOME_GOALS = 1.45
DEFAULT_AVG_AWAY_GOALS = 1.25

def calculate_dynamic_league_averages(cursor):
    """
    Scans the database to find the actual average goals scored 
    by home and away teams across all available form data.
    """
    cursor.execute("SELECT flashscore_match_id FROM match_links")
    links = cursor.fetchall()
    
    total_home_goals = 0
    total_away_goals = 0
    total_matches = 0
    
    # We sample a subset to keep it fast (first 100 matches)
    sample_size = min(100, len(links))
    
    for i in range(sample_size):
        fs_id = links[i]['flashscore_match_id']
        cursor.execute("SELECT h2h_data FROM flashscore_h2h WHERE match_id = ?", (fs_id,))
        row = cursor.fetchone()
        if row and row['h2h_data']:
            try:
                data = json.loads(row['h2h_data'])
                # Look for "Last matches" sections to get recent scores
                for sec in data.get('sections', []):
                    if 'last matches' in sec.get('name', '').lower():
                        for m in sec.get('matches', [])[:5]:
                            hs = m.get('home_score')
                            aws = m.get('away_score')
                            if hs is not None and aws is not None:
                                total_home_goals += hs
                                total_away_goals += aws
                                total_matches += 1
            except:
                pass
                
    if total_matches > 0:
        avg_home = total_home_goals / total_matches
        avg_away = total_away_goals / total_matches
        print(f"📊 Calculated League Averages: Home {avg_home:.2f} | Away {avg_away:.2f} (from {total_matches} games)")
        return avg_home, avg_away
    
    return DEFAULT_AVG_HOME_GOALS, DEFAULT_AVG_AWAY_GOALS

def get_team_form_goals_weighted(h2h_json, team_name):
    """
    Returns weighted averages. Recent games count more than older games.
    """
    try:
        data = json.loads(h2h_json)
        sections = data.get('sections', [])
        
        target_name = f"last matches: {team_name.lower()}"
        matches = []
        for sec in sections:
            if sec.get('name', '').lower() == target_name:
                matches = sec.get('matches', [])
                break
        
        if not matches:
            return None, None, 0

        recent = matches[:10]
        
        total_scored_weighted = 0
        total_conceded_weighted = 0
        total_weight = 0
        count = 0

        for idx, m in enumerate(recent):
            home_score = m.get('home_score')
            away_score = m.get('away_score')
            if home_score is None or away_score is None:
                continue
            
            past_home_name = (m.get('home') or {}).get('name', '').lower()
            is_home = team_name.lower() in past_home_name
            
            if is_home:
                scored = home_score
                conceded = away_score
            else:
                scored = away_score
                conceded = home_score
                
            # TIME DECAY: Most recent match (idx=0) gets weight 1.0
            # Oldest match (idx=9) gets weight 0.55
            weight = 1.0 - (idx * 0.05)
            
            total_scored_weighted += (scored * weight)
            total_conceded_weighted += (conceded * weight)
            total_weight += weight
            count += 1

        if count == 0 or total_weight == 0:
            return None, None, 0
            
        return total_scored_weighted / total_weight, total_conceded_weighted / total_weight, count

    except Exception as e:
        print(f"Error parsing form: {e}")
        return None, None, 0

# DEPRECATED: def calculate_poisson_probs(lambda_home, lambda_away):
    max_goals = 10
    probs = {}
    
    for h in range(max_goals):
        for a in range(max_goals):
            prob_h = poisson.pmf(h, lambda_home)
            prob_a = poisson.pmf(a, lambda_away)
            score_prob = prob_h * prob_a
            probs[f"{h}-{a}"] = score_prob

    p_home_win = sum(p for k, p in probs.items() if int(k.split('-')[0]) > int(k.split('-')[1]))
    p_draw = sum(p for k, p in probs.items() if int(k.split('-')[0]) == int(k.split('-')[1]))
    p_away_win = sum(p for k, p in probs.items() if int(k.split('-')[0]) < int(k.split('-')[1]))
    
    p_over_25 = sum(p for k, p in probs.items() if (int(k.split('-')[0]) + int(k.split('-')[1])) >= 3)
    p_under_25 = 1 - p_over_25
    
    p_btts = sum(p for k, p in probs.items() if int(k.split('-')[0]) > 0 and int(k.split('-')[1]) > 0)
    
    # 1st Half approximation (42% of goals usually happen in 1st half)
    lambda_home_1h = lambda_home * 0.42
    lambda_away_1h = lambda_away * 0.42
    p_btts_1h = (1 - poisson.pmf(0, lambda_home_1h)) * (1 - poisson.pmf(0, lambda_away_1h))

    return {
        'Home Win': p_home_win, 'Draw': p_draw, 'Away Win': p_away_win,
        'Over 2.5': p_over_25, 'Under 2.5': p_under_25,
        'BTTS Yes': p_btts, 'BTTS No': 1 - p_btts,
        '1H BTTS Yes': p_btts_1h, '1H BTTS No': 1 - p_btts_1h
    }

def run_model():
    print("🚀 Starting Probability Model v3 (Refined)...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Calculate Dynamic Averages first
    league_avg_home, league_avg_away = calculate_dynamic_league_averages(cursor)
    
    cursor.execute("DELETE FROM value_bets")
    
        # Only process tomorrow's fixtures
    cursor.execute("""
        SELECT DISTINCT f.match_id, f.home, f.away, f.league
        FROM fixtures f
        JOIN match_links ml ON f.match_id = ml.betika_match_id
        WHERE date(f.kickoff) = date('now', '+1 day')
    """)
    fixtures = cursor.fetchall()
    
    print(f"Processing {len(fixtures)} fixtures...")
    value_bets_found = 0

    for row in fixtures:
        match_id = row['match_id']
        home_team = row['home']
        away_team = row['away']
        
        cursor.execute("SELECT h2h_data FROM flashscore_h2h WHERE match_id = ?", (match_id,))
        h2h_row = cursor.fetchone()
        if not h2h_row or not h2h_row['h2h_data']:
            continue
            
        h2h_json = h2h_row['h2h_data']
        
        # 2. Get Weighted Form
        home_scored, home_conceded, home_count = get_team_form_goals_weighted(h2h_json, home_team)
        away_scored, away_conceded, away_count = get_team_form_goals_weighted(h2h_json, away_team)
        
        if not home_scored or not away_scored:
            continue
            
        # Confidence Score
        min_games = min(home_count, away_count)
        confidence_score = min(min_games / 10.0, 1.0)
        
        # 3. Regression to Mean (using Dynamic League Averages)
        # If a team has played < 5 games, we trust the league average more.
        regression_factor = 0.3 # 30% regression to league average
        
        home_attack = (home_scored * (1 - regression_factor)) + (league_avg_home * regression_factor)
        away_attack = (away_scored * (1 - regression_factor)) + (league_avg_away * regression_factor)
        
        # Defense is inverted (lower is better), so we regress towards the league average conceded
        home_defense = (home_conceded * (1 - regression_factor)) + (league_avg_away * regression_factor)
        away_defense = (away_conceded * (1 - regression_factor)) + (league_avg_home * regression_factor)
        
        # Lambda Calculation
        lambda_home = (home_attack + away_defense) / 2.0
        lambda_away = (away_attack + home_defense) / 2.0
        
        # Home Advantage Boost
        lambda_home *= 1.10
        
        probs = calculate_verbose_probs(lambda_home, lambda_away)
        
        cursor.execute("SELECT market_name, selection, odd, line FROM odds WHERE match_id = ?", (match_id,))
        odds = cursor.fetchall()
        
        for odd_row in odds:
            market = odd_row['market_name']
            selection = odd_row['selection']
            betika_odd = odd_row['odd']
            line = odd_row['line'] if 'line' in odd_row.keys() else ''
            
            model_prob = 0.0
            
            if market in ["1X2", "Match Result"]:
                if selection == home_team: model_prob = probs['Home Win']
                elif selection.lower() == "draw": model_prob = probs['Draw']
                elif selection == away_team: model_prob = probs['Away Win']
            elif "HANDICAP" in market.upper():
                try:
                    if line and 'hcp=' in str(line):
                        h_val, a_val = map(int, str(line).split('=')[1].split(':'))
                        target_diff = a_val - h_val
                        if home_team.split()[0] in selection:
                            model_prob = skellam.sf(target_diff, lambda_home, lambda_away)
                        elif 'draw' in selection.lower():
                            model_prob = skellam.pmf(target_diff, lambda_home, lambda_away)
                        elif away_team.split()[0] in selection:
                            model_prob = skellam.cdf(target_diff - 1, lambda_home, lambda_away)
                except Exception:
                    pass
            elif market in ["TOTAL", "Over/Under"]:
                if "over 2.5" in selection.lower(): model_prob = probs['Over 2.5']
                elif "under 2.5" in selection.lower(): model_prob = probs['Under 2.5']
            elif "both teams" in market.lower() and "1st half" not in market.lower():
                if selection.lower() == "yes": model_prob = probs['BTTS Yes']
                elif selection.lower() == "no": model_prob = probs['BTTS No']
            elif "1st half" in market.lower() and "both teams" in market.lower():
                if selection.lower() == "yes": model_prob = probs['1H BTTS Yes']
                elif selection.lower() == "no": model_prob = probs['1H BTTS No']

            if model_prob > 0.01 and betika_odd > 1.01:
                fair_odd = 1 / model_prob
                ev = (model_prob * betika_odd) - 1
                
                if ev > 0:
                    confidence_label = "High Value" if (ev > 0.05 and confidence_score > 0.8) else "Value"
                    
                    cursor.execute("""
                        INSERT INTO value_bets 
                        (match_id, market_name, selection, betika_odd, model_probability, fair_odd, ev_percent, confidence, matches_used, confidence_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (match_id, market, selection, betika_odd, model_prob, fair_odd, ev, confidence_label, min_games, confidence_score))
                    
                    if ev > 0.05 and confidence_score > 0.8:
                        value_bets_found += 1
                        print(f"💎 HIGH VALUE: {home_team} vs {away_team} | {market}: {selection} | EV: {ev*100:.1f}%")

    conn.commit()
    conn.close()
    print(f"\n Model v3 Complete. Found {value_bets_found} High-Confidence Value Bets.")

if __name__ == "__main__":
    run_model()


def calculate_skellam_hybrid_probs(lambda_home, lambda_away):
    """
    Hybrid Model:
    - Uses Skellam Distribution for 1X2 (More accurate, infinite goal range)
    - Uses Poisson Sum for Over/Under (Faster than looping)
    - Uses Independent Poisson for BTTS
    """
    probs = {}

    # --- 1X2 (Skellam Distribution) ---
    # P(Home Win) = P(Home Goals - Away Goals > 0)
    p_home = skellam.sf(0, lambda_home, lambda_away)
    # P(Draw) = P(Home Goals - Away Goals == 0)
    p_draw = skellam.pmf(0, lambda_home, lambda_away)
    # P(Away Win) = P(Home Goals - Away Goals < 0)
    p_away = skellam.cdf(-1, lambda_home, lambda_away)

    # Normalize to ensure they sum to 1 (handling float precision)
    total_1x2 = p_home + p_draw + p_away
    probs['Home Win'] = p_home / total_1x2
    probs['Draw'] = p_draw / total_1x2
    probs['Away Win'] = p_away / total_1x2

    # --- Over/Under 2.5 (Poisson Sum) ---
    # The sum of two independent Poisson variables is also Poisson
    lambda_total = lambda_home + lambda_away
    probs['Over 2.5'] = 1 - poisson.cdf(2, lambda_total)
    probs['Under 2.5'] = poisson.cdf(2, lambda_total)

    # --- BTTS (Independent Poissons) ---
    # Probability Home scores at least 1
    p_home_scores = 1 - poisson.pmf(0, lambda_home)
    # Probability Away scores at least 1
    p_away_scores = 1 - poisson.pmf(0, lambda_away)
    
    probs['BTTS Yes'] = p_home_scores * p_away_scores
    probs['BTTS No'] = 1 - probs['BTTS Yes']

    # --- 1st Half Approximation ---
    # Using the 42% rule mentioned in your original code comments
    lambda_home_1h = lambda_home * 0.42
    lambda_away_1h = lambda_away * 0.42

    p_home_1h_scores = 1 - poisson.pmf(0, lambda_home_1h)
    p_away_1h_scores = 1 - poisson.pmf(0, lambda_away_1h)
    
    probs['1H BTTS Yes'] = p_home_1h_scores * p_away_1h_scores
    probs['1H BTTS No'] = 1 - probs['1H BTTS Yes']

    return probs

"""
Probability Model v2 - Refined
Fixes: 1st Half bug, adds league normalization, more markets, better confidence scoring.
"""

import sqlite3
import json
import math
from scipy.stats import poisson
from database import get_db_connection

# --- League Averages (will be calculated dynamically) ---
DEFAULT_AVG_HOME_GOALS = 1.5
DEFAULT_AVG_AWAY_GOALS = 1.2

# 1st Half typically has ~40-45% of total goals
FIRST_HALF_GOAL_RATIO = 0.42

def calculate_league_averages(cursor):
    """Calculate actual league averages from all fixtures in DB."""
    cursor.execute("""
        SELECT AVG(home_goals) as avg_home, AVG(away_goals) as avg_away
        FROM (
            SELECT 
                CASE WHEN f.home = h2h.home_team THEN h2h.home_score ELSE h2h.away_score END as home_goals,
                CASE WHEN f.away = h2h.away_team THEN h2h.away_score ELSE h2h.home_score END as away_goals
            FROM fixtures f
            JOIN flashscore_h2h h2h ON f.match_id = h2h.match_id
        )
    """)
    # Simplified - use defaults for now
    return DEFAULT_AVG_HOME_GOALS, DEFAULT_AVG_AWAY_GOALS

def get_team_form_goals(h2h_json, team_name, is_home_in_fixture):
    """
    Returns: (avg_scored, avg_conceded, match_count, home_record, away_record)
    home_record: (wins, draws, losses) when team played at home
    away_record: (wins, draws, losses) when team played away
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
            return None, None, 0, (0,0,0), (0,0,0)

        recent = matches[:10]
        
        total_scored = 0
        total_conceded = 0
        count = 0
        home_wins = home_draws = home_losses = 0
        away_wins = away_draws = away_losses = 0

        for m in recent:
            home_score = m.get('home_score')
            away_score = m.get('away_score')
            if home_score is None or away_score is None:
                continue
            
            past_home_name = (m.get('home') or {}).get('name', '').lower()
            is_home_match = team_name.lower() in past_home_name
            
            if is_home_match:
                scored = home_score
                conceded = away_score
                if scored > conceded: home_wins += 1
                elif scored == conceded: home_draws += 1
                else: home_losses += 1
            else:
                scored = away_score
                conceded = home_score
                if scored > conceded: away_wins += 1
                elif scored == conceded: away_draws += 1
                else: away_losses += 1
                
            total_scored += scored
            total_conceded += conceded
            count += 1

        if count == 0:
            return None, None, 0, (0,0,0), (0,0,0)
            
        return (total_scored / count, 
                total_conceded / count, 
                count, 
                (home_wins, home_draws, home_losses),
                (away_wins, away_draws, away_losses))

    except Exception as e:
        print(f"Error parsing form: {e}")
        return None, None, 0, (0,0,0), (0,0,0)

def calculate_poisson_probs(lambda_home, lambda_away):
    """
    Returns dict with probabilities for ALL markets.
    """
    max_goals = 10
    probs = {}
    
    # Scoreline matrix
    for h in range(max_goals):
        for a in range(max_goals):
            prob_h = poisson.pmf(h, lambda_home)
            prob_a = poisson.pmf(a, lambda_away)
            score_prob = prob_h * prob_a
            probs[f"{h}-{a}"] = score_prob

    # Full Time Markets
    p_home_win = sum(p for k, p in probs.items() if int(k.split('-')[0]) > int(k.split('-')[1]))
    p_draw = sum(p for k, p in probs.items() if int(k.split('-')[0]) == int(k.split('-')[1]))
    p_away_win = sum(p for k, p in probs.items() if int(k.split('-')[0]) < int(k.split('-')[1]))
    
    # Goal Lines
    p_over_05 = sum(p for k, p in probs.items() if (int(k.split('-')[0]) + int(k.split('-')[1])) >= 1)
    p_over_15 = sum(p for k, p in probs.items() if (int(k.split('-')[0]) + int(k.split('-')[1])) >= 2)
    p_over_25 = sum(p for k, p in probs.items() if (int(k.split('-')[0]) + int(k.split('-')[1])) >= 3)
    p_over_35 = sum(p for k, p in probs.items() if (int(k.split('-')[0]) + int(k.split('-')[1])) >= 4)
    p_over_45 = sum(p for k, p in probs.items() if (int(k.split('-')[0]) + int(k.split('-')[1])) >= 5)
    
    # BTTS
    p_btts_yes = sum(p for k, p in probs.items() if int(k.split('-')[0]) > 0 and int(k.split('-')[1]) > 0)
    
    # Draw No Bet (Home wins + draws refunded)
    p_dnb_home = p_home_win + (p_draw * 0.5)  # Simplified
    p_dnb_away = p_away_win + (p_draw * 0.5)
    
    # Double Chance
    p_1x = p_home_win + p_draw
    p_x2 = p_away_win + p_draw
    p_12 = p_home_win + p_away_win
    
    # 1st Half Markets (using ratio)
    lambda_home_1h = lambda_home * FIRST_HALF_GOAL_RATIO
    lambda_away_1h = lambda_away * FIRST_HALF_GOAL_RATIO
    
    p_btts_1h = 1 - (poisson.pmf(0, lambda_home_1h) * poisson.pmf(0, lambda_away_1h) + 
                      poisson.pmf(0, lambda_home_1h) * (1 - poisson.pmf(0, lambda_away_1h)) +
                      (1 - poisson.pmf(0, lambda_home_1h)) * poisson.pmf(0, lambda_away_1h))
    # Simplified 1H BTTS: both teams score at least 1 in first half
    p_no_1h_home = poisson.pmf(0, lambda_home_1h)
    p_no_1h_away = poisson.pmf(0, lambda_away_1h)
    p_btts_1h_yes = (1 - p_no_1h_home) * (1 - p_no_1h_away)

    return {
        # Full Time Result
        'Home Win': p_home_win,
        'Draw': p_draw,
        'Away Win': p_away_win,
        # Goal Lines
        'Over 0.5': p_over_05,
        'Over 1.5': p_over_15,
        'Over 2.5': p_over_25,
        'Over 3.5': p_over_35,
        'Over 4.5': p_over_45,
        'Under 0.5': 1 - p_over_05,
        'Under 1.5': 1 - p_over_15,
        'Under 2.5': 1 - p_over_25,
        'Under 3.5': 1 - p_over_35,
        'Under 4.5': 1 - p_over_45,
        # BTTS
        'BTTS Yes': p_btts_yes,
        'BTTS No': 1 - p_btts_yes,
        # 1st Half
        '1H BTTS Yes': p_btts_1h_yes,
        '1H BTTS No': 1 - p_btts_1h_yes,
        # DNB
        'DNB Home': p_dnb_home,
        'DNB Away': p_dnb_away,
        # Double Chance
        '1X': p_1x,
        'X2': p_x2,
        '12': p_12
    }

def map_selection_to_prob(market, selection, home_team, away_team, probs):
    """Maps Betika market/selection to model probability."""
    model_prob = 0.0
    
    # 1X2
    if market in ["1X2", "Match Result"]:
        if selection == home_team: model_prob = probs['Home Win']
        elif selection.lower() == "draw": model_prob = probs['Draw']
        elif selection == away_team: model_prob = probs['Away Win']
    
    # Over/Under - Full Time
    elif market in ["TOTAL", "Over/Under", "Goals Over/Under"]:
        sel_lower = selection.lower()
        if "over 0.5" in sel_lower: model_prob = probs['Over 0.5']
        elif "under 0.5" in sel_lower: model_prob = probs['Under 0.5']
        elif "over 1.5" in sel_lower: model_prob = probs['Over 1.5']
        elif "under 1.5" in sel_lower: model_prob = probs['Under 1.5']
        elif "over 2.5" in sel_lower: model_prob = probs['Over 2.5']
        elif "under 2.5" in sel_lower: model_prob = probs['Under 2.5']
        elif "over 3.5" in sel_lower: model_prob = probs['Over 3.5']
        elif "under 3.5" in sel_lower: model_prob = probs['Under 3.5']
        elif "over 4.5" in sel_lower: model_prob = probs['Over 4.5']
        elif "under 4.5" in sel_lower: model_prob = probs['Under 4.5']
    
    # BTTS - Full Time Only
    elif "both teams" in market.lower() and "1st half" not in market.lower():
        if selection.lower() == "yes": model_prob = probs['BTTS Yes']
        elif selection.lower() == "no": model_prob = probs['BTTS No']
    
    # 1st Half BTTS
    elif "1st half" in market.lower() and "both teams" in market.lower():
        if selection.lower() == "yes": model_prob = probs['1H BTTS Yes']
        elif selection.lower() == "no": model_prob = probs['1H BTTS No']
    
    # Double Chance
    elif market == "Double Chance":
        sel_upper = selection.upper()
        if "1X" in sel_upper or "HOME OR DRAW" in sel_upper: model_prob = probs['1X']
        elif "X2" in sel_upper or "AWAY OR DRAW" in sel_upper: model_prob = probs['X2']
        elif "12" in sel_upper or "HOME OR AWAY" in sel_upper: model_prob = probs['12']
    
    # Draw No Bet
    elif "draw no bet" in market.lower() or "dnb" in market.lower():
        if selection == home_team: model_prob = probs['DNB Home']
        elif selection == away_team: model_prob = probs['DNB Away']
    
    return model_prob

def run_model():
    print(" Starting Probability Model v2 (Refined)...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM value_bets")
    
    cursor.execute("""
        SELECT DISTINCT f.match_id, f.home, f.away, f.league
        FROM fixtures f
        JOIN match_links ml ON f.match_id = ml.betika_match_id
    """)
    fixtures = cursor.fetchall()
    
    print(f"Processing {len(fixtures)} fixtures...")
    
    value_bets_found = 0

    for row in fixtures:
        match_id = row['match_id']
        home_team = row['home']
        away_team = row['away']
        league = row['league']
        
        cursor.execute("SELECT h2h_data FROM flashscore_h2h WHERE match_id = ?", (match_id,))
        h2h_row = cursor.fetchone()
        if not h2h_row or not h2h_row['h2h_data']:
            continue
            
        h2h_json = h2h_row['h2h_data']
        
        # Get form data with home/away splits
        home_scored, home_conceded, home_count, home_record, away_record_h = get_team_form_goals(h2h_json, home_team, True)
        away_scored, away_conceded, away_count, away_record, home_record_a = get_team_form_goals(h2h_json, away_team, False)
        
        if not home_scored or not away_scored:
            continue
            
        # Confidence Score (based on minimum games)
        min_games = min(home_count, away_count)
        confidence_score = min(min_games / 10.0, 1.0)
        
        # Expected Goals Calculation with regression to mean
        # If a team has extreme form, pull it slightly toward league average
        regression_factor = 0.2  # 20% regression to league average
        league_avg_scored = (DEFAULT_AVG_HOME_GOALS + DEFAULT_AVG_AWAY_GOALS) / 2
        
        home_attack = (home_scored * (1 - regression_factor)) + (league_avg_scored * regression_factor)
        away_attack = (away_scored * (1 - regression_factor)) + (league_avg_scored * regression_factor)
        home_defense = (home_conceded * (1 - regression_factor)) + (league_avg_scored * regression_factor)
        away_defense = (away_conceded * (1 - regression_factor)) + (league_avg_scored * regression_factor)
        
        # Lambda (expected goals)
        lambda_home = (home_attack + away_defense) / 2.0
        lambda_away = (away_attack + home_defense) / 2.0
        
        # Home advantage boost (typically 10-15%)
        lambda_home *= 1.10
        
        # Calculate all probabilities
        probs = calculate_poisson_probs(lambda_home, lambda_away)
        
        # Get odds
        cursor.execute("SELECT market_name, selection, odd FROM odds WHERE match_id = ?", (match_id,))
        odds = cursor.fetchall()
        
        for odd_row in odds:
            market = odd_row['market_name']
            selection = odd_row['selection']
            betika_odd = odd_row['odd']
            
            # Skip markets we don't model
            if "handicap" in market.lower() or "asian" in market.lower():
                continue
            if "correct score" in market.lower():
                continue
                
            model_prob = map_selection_to_prob(market, selection, home_team, away_team, probs)
            
            if model_prob > 0.01 and betika_odd > 1.01:  # Minimum thresholds
                fair_odd = 1 / model_prob
                ev = (model_prob * betika_odd) - 1
                
                # Confidence label
                if confidence_score >= 0.8 and ev > 0.05:
                    confidence_label = "High Value"
                elif ev > 0.05:
                    confidence_label = "Value"
                elif ev > 0:
                    confidence_label = "Slight Value"
                else:
                    continue  # Skip negative EV
                
                cursor.execute("""
                    INSERT INTO value_bets 
                    (match_id, market_name, selection, betika_odd, model_probability, fair_odd, ev_percent, confidence, matches_used, confidence_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (match_id, market, selection, betika_odd, model_prob, fair_odd, ev, confidence_label, min_games, confidence_score))
                
                if ev > 0.05 and confidence_score >= 0.8:
                    value_bets_found += 1
                    print(f" VALUE BET: {home_team} vs {away_team} | {market}: {selection} | EV: {ev*100:.1f}% | Confidence: {confidence_score*100:.0f}%")

    conn.commit()
    conn.close()
    print(f"\n Model v2 Complete. Found {value_bets_found} high-confidence value bets.")

if __name__ == "__main__":
    run_model()

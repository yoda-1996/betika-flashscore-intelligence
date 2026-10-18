"""
Betika & Flashscore Intelligence Dashboard (Final Clean Version)
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from database import get_db_connection

st.set_page_config(page_title="Betika Intelligence Dashboard", layout="wide", page_icon="⚽")

# --- Helpers ---
@st.cache_data(ttl=300)
def load_data(query, params=None):
    conn = get_db_connection()
    try:
        if params:
            df = pd.read_sql_query(query, conn, params=params)
        else:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def parse_json_safe(json_str):
    if not json_str: return None
    try: return json.loads(json_str)
    except: return None

def render_standings_table(json_str, title):
    data = parse_json_safe(json_str)
    if not data:
        st.info(f"No data for {title}.")
        return

    standings_list = data.get('standings', [])
    if not standings_list and isinstance(data, list):
        standings_list = data
    elif not standings_list:
        st.json(data)
        return

    rows = []
    for item in standings_list:
        team_info = item.get('team', {})
        team_name = team_info.get('name', 'Unknown') if isinstance(team_info, dict) else str(team_info)
        
        rows.append({
            'Pos': item.get('rank', ''),
            'Team': team_name,
            'MP': item.get('matches_played', 0),
            'W': item.get('wins', 0),
            'D': item.get('draws', 0),
            'L': item.get('losses', 0),
            'GF': item.get('goals_for', 0),
            'GA': item.get('goals_against', 0),
            'Pts': item.get('points', 0),
            'Form': str(item.get('recent_matches', ''))
        })

    if rows:
        st.subheader(title)
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

def render_over_under_table(json_str, title):
    data = parse_json_safe(json_str)
    if not data: return
    
    standings_list = data.get('standings', [])
    if not standings_list and isinstance(data, list):
        standings_list = data

    rows = []
    for item in standings_list:
        team_info = item.get('team', {})
        team_name = team_info.get('name', 'Unknown') if isinstance(team_info, dict) else str(team_info)
        
        rows.append({
            'Pos': item.get('rank', ''),
            'Team': team_name,
            'MP': item.get('matches_played', 0),
            'Over': item.get('over', 0),
            'Under': item.get('under', 0),
            'Avg': item.get('average', 0)
        })
    
    if rows:
        st.subheader(title)
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

def render_h2h_sections(json_str):
    data = parse_json_safe(json_str)
    if not data:
        st.info("No H2H data.")
        return

    sections = data.get('sections', [])
    if not sections:
        st.info("No sections found in H2H data.")
        return

    for section in sections:
        section_name = section.get('name', 'Unknown Section')
        matches = section.get('matches', [])
        
        if matches:
            st.subheader(f"📅 {section_name}")
            rows = []
            for m in matches[:10]:
                date_str = m.get('start_time', '')[:10]
                home_t = (m.get('home') or {}).get('name', 'Home')
                away_t = (m.get('away') or {}).get('name', 'Away')
                home_s = m.get('home_score')
                away_s = m.get('away_score')
                
                score_display = f"{home_s} - {away_s}" if home_s is not None else "vs"
                
                rows.append({
                    'Date': date_str,
                    'Home': home_t,
                    'Score': score_display,
                    'Away': away_t
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

def render_htft_table(json_str, title):
    """Renders HT/FT matrix specifically for Flashscore data structure."""
    if not json_str or len(str(json_str)) < 10:
        st.info(f"No data for {title}")
        return
    
    try:
        data = json.loads(json_str)
        rows = data.get("standings", [])
        if not rows:
            st.info(f"No rows for {title}")
            return
        
        clean_rows = []
        for r in rows:
            team_info = r.get("team", {})
            team_name = team_info.get("name", "Unknown") if isinstance(team_info, dict) else str(team_info)
            htft_data = r.get("half_time_full_time", {})
            
            clean_rows.append({
                "Team": team_name,
                "MP": r.get("matches_played", 0),
                "W/W": htft_data.get("win_win", 0),
                "W/D": htft_data.get("win_draw", 0),
                "W/L": htft_data.get("win_loss", 0),
                "D/W": htft_data.get("draw_win", 0),
                "D/D": htft_data.get("draw_draw", 0),
                "D/L": htft_data.get("draw_loss", 0),
                "L/W": htft_data.get("loss_win", 0),
                "L/D": htft_data.get("loss_draw", 0),
                "L/L": htft_data.get("loss_loss", 0),
                "Pts": r.get("points", 0)
            })
            
        if clean_rows:
            st.subheader(title)
            st.dataframe(pd.DataFrame(clean_rows), use_container_width=True)
            st.markdown("""
            **How to read:**
            - **W/W**: Winning at HT and won at FT.
            - **D/W**: Drawing at HT but won at FT (Strong finishers).
            - **L/W**: Losing at HT but won at FT (Comebacks).
            """)
    except Exception as e:
        st.error(f"Error parsing HT/FT data: {e}")

# --- Main App ---
st.title(" Betika & Flashscore Intelligence Dashboard")

tab = st.sidebar.radio("Navigation", ["Fixtures Overview", "Market Explorer", "Value Bets", "Safe Bets (Bankers)", "Ultimate Report"])

if tab == "Fixtures Overview":
    st.header("All Scraped Fixtures")
    df = load_data("SELECT * FROM fixtures WHERE date(kickoff) = date('now', '+1 day') ORDER BY kickoff")
    if not df.empty: st.dataframe(df, use_container_width=True)

elif tab == "Market Explorer":
    st.header("Betika Odds Market Explorer")
    df_matches = load_data("SELECT match_id, home, away, league FROM fixtures ORDER BY kickoff ASC")
    if df_matches.empty:
        st.warning("No data.")
    else:
        df_matches['label'] = df_matches['home'] + " vs " + df_matches['away']
        selected_label = st.selectbox("Select Match", df_matches['label'])
        selected_id = df_matches[df_matches['label'] == selected_label]['match_id'].values[0]
        
        df_odds = load_data("SELECT market_name, selection, odd, line FROM odds WHERE match_id = ?", (selected_id,))
        if not df_odds.empty:
            for market, group in df_odds.groupby('market_name'):
                st.subheader(market)
                st.dataframe(group[['selection', 'odd', 'line']], use_container_width=True)

elif tab == "Value Bets":
    st.header(" Value Bets (Expected Value > 0%)")
    
    df_bets = load_data("""
        SELECT vb.match_id, f.home, f.away, f.league, f.kickoff, 
               vb.market_name, vb.selection, vb.betika_odd, 
               vb.model_probability, vb.fair_odd, vb.ev_percent, vb.confidence,
               vb.matches_used, vb.confidence_score
        FROM value_bets vb
        JOIN fixtures f ON vb.match_id = f.match_id
        WHERE vb.ev_percent > 0 AND date(f.kickoff) = date('now', '+1 day')
        ORDER BY f.kickoff ASC
    """)
    
    if df_bets.empty:
        st.warning("No value bets found.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Value Bets", len(df_bets))
        col2.metric("High Confidence (EV > 5%)", len(df_bets[df_bets['ev_percent'] > 0.05]))
        col3.metric("Avg EV", f"{df_bets['ev_percent'].mean()*100:.1f}%")
        
        st.markdown("---")
        
        confidence_filter = st.multiselect(
            "Filter by Confidence Level",
            options=df_bets['confidence'].unique(),
            default=df_bets['confidence'].unique()
        )
        
        filtered_bets = df_bets[df_bets['confidence'].isin(confidence_filter)]
        filtered_bets = filtered_bets.copy()
        filtered_bets['adjusted_ev'] = filtered_bets['ev_percent'] * filtered_bets['confidence_score']
        display_df = filtered_bets.sort_values(by='adjusted_ev', ascending=False)

        st.dataframe(
            display_df[['league', 'home', 'away', 'market_name', 'selection', 
                        'betika_odd', 'model_probability', 'ev_percent', 
                        'matches_used', 'confidence_score']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "ev_percent": st.column_config.NumberColumn("EV %", format="%.2f%%"),
                "confidence_score": st.column_config.ProgressColumn("Data Quality", min_value=0.0, max_value=1.0, format="%.0f%%"),
                "matches_used": st.column_config.NumberColumn("Games Analyzed")
            }
        )
elif tab == "Safe Bets (Bankers)":
    st.header("🛡️ Safe Bets / Banker Builder (Odds 1.01 - 1.30)")
    st.markdown("""
    This section identifies low-odds markets (1.01 to 1.30) where our Model confirms a high probability of winning.
    These are ideal for building safe accumulators.
    """)
    
    # Query specifically for low odds that have positive Expected Value
    df_safe = load_data("""
        SELECT vb.match_id, f.home, f.away, f.league, f.kickoff, 
               vb.market_name, vb.selection, vb.betika_odd, 
               vb.model_probability, vb.confidence_score
        FROM value_bets vb
        JOIN fixtures f ON vb.match_id = f.match_id
        WHERE vb.betika_odd BETWEEN 1.01 AND 1.30
        AND vb.ev_percent > 0 AND date(f.kickoff) = date('now', '+1 day')
        ORDER BY f.kickoff ASC
    """)
    
    if df_safe.empty:
        st.warning("No safe bets found with positive value right now. Try running the model again.")
    else:
        # Calculate "Safety Margin"
        # Implied Probability = 1 / Odd
        # Safety Margin = Model Probability - Implied Probability
        df_safe['implied_prob'] = 1 / df_safe['betika_odd']
        df_safe['safety_margin'] = (df_safe['model_probability'] - df_safe['implied_prob']) * 100
        
        # Filter for high confidence only (Data Quality > 50%)
        df_safe = df_safe[df_safe['confidence_score'] >= 0.5]
        
        if df_safe.empty:
            st.info("No safe bets found with sufficient data quality (50%+).")
        else:
            st.subheader(f"Found {len(df_safe)} High-Confidence Safe Bets")
            
            # Display Table
            # Fix display numbers (multiply decimals by 100 for %)
            display_df = df_safe.copy()
            display_df['model_probability'] = display_df['model_probability'] * 100
            display_df['confidence_score'] = display_df['confidence_score'] * 100
            
            st.dataframe(
                display_df[['league', 'home', 'away', 'market_name', 'selection', 
                         'betika_odd', 'model_probability', 'safety_margin', 'confidence_score']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "betika_odd": st.column_config.NumberColumn("Odds", format="%.2f"),
                    "model_probability": st.column_config.NumberColumn("Model Win %", format="%.1f%%"),
                    "safety_margin": st.column_config.NumberColumn("Safety Margin %", format="%.1f%%"),
                    "confidence_score": st.column_config.ProgressColumn("Data Quality", min_value=0.0, max_value=100.0, format="%.0f%%")
                }
            )
            
            st.markdown("---")
            st.markdown("""
            **How to use this:**
            1. **Odds (1.01-1.30):** These are your "Bankers".
            2. **Model Win %:** What our math says the chance of winning is.
            3. **Safety Margin:** If this is positive, our model thinks the bet is safer than the bookie implies.
            4. **Data Quality:** Only trust bets with high data quality (red bars).
            """)

elif tab == "Ultimate Report":
    st.header("Ultimate Match Report")
    df_matches = load_data("SELECT match_id, home, away FROM fixtures WHERE date(kickoff) = date('now', '+1 day') ORDER BY kickoff ASC")
    if df_matches.empty:
        st.warning("No data.")
    else:
        df_matches['label'] = df_matches['home'] + " vs " + df_matches['away']
        selected_label = st.selectbox("Select Match for Deep Analysis", df_matches['label'], key="ult_select")
        selected_id = df_matches[df_matches['label'] == selected_label]['match_id'].values[0]
        
        df_link = load_data("SELECT * FROM match_links WHERE betika_match_id = ?", (selected_id,))
        
        if df_link.empty:
            st.warning("Not linked to Flashscore.")
        else:
            link_data = df_link.iloc[0]
            st.success(f"Linked to Flashscore ID: {link_data['flashscore_match_id']} (Confidence: {link_data['confidence']})")
            
            df_stats = load_data("SELECT * FROM ultimate_stats WHERE match_id = ?", (selected_id,))
            df_h2h = load_data("SELECT * FROM flashscore_h2h WHERE match_id = ?", (selected_id,))
            df_extras = load_data("SELECT * FROM match_extras WHERE betika_match_id = ?", (selected_id,))
            
            if not df_stats.empty:
                row = df_stats.iloc[0]
                
                st.subheader("📈 League Standings & Form")
                s_tab1, s_tab2, s_tab3, s_tab4, s_tab5, s_tab6, s_tab7 = st.tabs([
                    "Overall", "Home", "Away", 
                    "Form (Last 5)", "Form (Home)", "Form (Away)",
                    "HT/FT"
                ])
                
                with s_tab1: render_standings_table(row['overall_table'], "Overall Standings")
                with s_tab2: render_standings_table(row['home_table'], "Home Standings")
                with s_tab3: render_standings_table(row['away_table'], "Away Standings")
                with s_tab4: render_standings_table(row['form_overall_table'], "Form Table (Last 5)")
                with s_tab5: render_standings_table(row['form_home_table'], "Form Table (Home Last 5)")
                with s_tab6: render_standings_table(row['form_away_table'], "Form Table (Away Last 5)")
                
                with s_tab7:
                    htft_sub1, htft_sub2, htft_sub3 = st.tabs(["Overall", "Home", "Away"])
                    with htft_sub1: render_htft_table(row['ht_ft_table'], "HT/FT Stats (Overall)")
                    with htft_sub2: render_htft_table(row['ht_ft_home_table'], "HT/FT Stats (Home)")
                    with htft_sub3: render_htft_table(row['ht_ft_away_table'], "HT/FT Stats (Away)")

                st.subheader("⚽ Over/Under Statistics")
                ou_data = parse_json_safe(row['ou_all'])
                if ou_data:
                    ou_tabs = st.tabs([f"O/U {k}" for k in ou_data.keys()])
                    for idx, (k, v) in enumerate(ou_data.items()):
                        with ou_tabs[idx]:
                            render_over_under_table(json.dumps(v), f"Over/Under {k} Goals")
                else:
                    st.info("No Over/Under data available.")

            st.divider()

            st.subheader("️ Head-to-Head & Recent Matches")
            if not df_h2h.empty:
                render_h2h_sections(df_h2h.iloc[0]['h2h_data'])
            else:
                st.info("No H2H data found.")

            st.divider()

            st.subheader("🏥 Match Extras")
            if not df_extras.empty:
                row_ex = df_extras.iloc[0]
                
                                # 1. Flashscore Preview / News
                with st.expander("📰 Match News & Preview", expanded=True):
                    report_data = parse_json_safe(row_ex['report'])
                    if report_data:
                        preview_text = report_data.get('preview')
                        
                        if preview_text:
                            st.markdown("**Related News Articles:**")
                            # Split by bullet points and display each on its own line
                            articles = preview_text.split('•')
                            for article in articles:
                                article = article.strip()
                                if article:
                                    st.markdown(f"• {article}")
                            
                            # Add link to Flashscore for full preview
                            if link_data.get('flashscore_match_id'):
                                fs_url = f"https://www.flashscore.com/match/{link_data['flashscore_match_id']}/"
                                st.markdown(f"\n🔗 [Read full Flashscore preview here]({fs_url})")
                        else:
                            st.info("No preview available for this match.")
                    else:
                        st.info("No preview available for this match.")
                
                # 2. Injuries
                with st.expander(" Injuries / Missing Players"):
                    inj = parse_json_safe(row_ex['injuries'])
                    if inj:
                        if isinstance(inj, dict):
                            home_injuries = inj.get('home', [])
                            away_injuries = inj.get('away', [])
                            
                            if home_injuries:
                                st.subheader("🏠 Home Team Injuries")
                                for player in home_injuries:
                                    player_info = player.get('player', {})
                                    name = player_info.get('name', 'Unknown')
                                    reason = player.get('reason', 'Unknown')
                                    likelihood = player.get('likelihood', '')
                                    st.markdown(f"- **{name}**: {reason} {likelihood}")
                            
                            if away_injuries:
                                st.subheader("✈️ Away Team Injuries")
                                for player in away_injuries:
                                    player_info = player.get('player', {})
                                    name = player_info.get('name', 'Unknown')
                                    reason = player.get('reason', 'Unknown')
                                    likelihood = player.get('likelihood', '')
                                    st.markdown(f"- **{name}**: {reason} {likelihood}")
                        else:
                            st.json(inj)
                    else:
                        st.write("No injury data.")
                
                # 3. Lineups
                with st.expander("👥 Lineups"):
                    lin = parse_json_safe(row_ex['lineups'])
                    if lin:
                        st.json(lin)
                    else:
                        st.write("Lineups not announced.")

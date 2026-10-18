"""
Updates dashboard.py to only show matches for Tomorrow.
"""

with open('dashboard.py', 'r') as f:
    content = f.read()

# 1. Fixtures Overview
old_q1 = "SELECT * FROM fixtures ORDER BY kickoff"
new_q1 = "SELECT * FROM fixtures WHERE date(kickoff) = date('now', '+1 day') ORDER BY kickoff"
if old_q1 in content:
    content = content.replace(old_q1, new_q1)
    print("✅ Fixed Fixtures Overview (Tomorrow only)")

# 2. Market Explorer
old_q2 = "SELECT match_id, home, away, league FROM fixtures ORDER BY home"
new_q2 = "SELECT match_id, home, away, league FROM fixtures WHERE date(kickoff) = date('now', '+1 day') ORDER BY kickoff"
if old_q2 in content:
    content = content.replace(old_q2, new_q2)
    print("✅ Fixed Market Explorer (Tomorrow only)")

# 3. Ultimate Report Dropdown
old_q3 = "SELECT match_id, home, away FROM fixtures ORDER BY kickoff ASC"
new_q3 = "SELECT match_id, home, away FROM fixtures WHERE date(kickoff) = date('now', '+1 day') ORDER BY kickoff ASC"
if old_q3 in content:
    content = content.replace(old_q3, new_q3)
    print("✅ Fixed Ultimate Report Dropdown (Tomorrow only)")

# 4. Value Bets & Safe Bets (Join with fixtures)
# We need to ensure the JOIN only picks tomorrow's fixtures
old_join = "JOIN fixtures f ON vb.match_id = f.match_id"
new_join = "JOIN fixtures f ON vb.match_id = f.match_id WHERE date(f.kickoff) = date('now', '+1 day')"

# Note: The Value Bets query already has a WHERE clause (vb.ev_percent > 0). 
# We need to append the date check carefully.
# Actually, simpler to just replace the specific query blocks if possible, 
# but let's try a targeted replacement for the specific lines.

# For Value Bets:
old_vb_query = """SELECT vb.match_id, f.home, f.away, f.league, f.kickoff, 
               vb.market_name, vb.selection, vb.betika_odd, 
               vb.model_probability, vb.fair_odd, vb.ev_percent, vb.confidence,
               vb.matches_used, vb.confidence_score
        FROM value_bets vb
        JOIN fixtures f ON vb.match_id = f.match_id
        WHERE vb.ev_percent > 0
        ORDER BY f.kickoff ASC"""
        
new_vb_query = """SELECT vb.match_id, f.home, f.away, f.league, f.kickoff, 
               vb.market_name, vb.selection, vb.betika_odd, 
               vb.model_probability, vb.fair_odd, vb.ev_percent, vb.confidence,
               vb.matches_used, vb.confidence_score
        FROM value_bets vb
        JOIN fixtures f ON vb.match_id = f.match_id
        WHERE vb.ev_percent > 0 AND date(f.kickoff) = date('now', '+1 day')
        ORDER BY f.kickoff ASC"""

if old_vb_query in content:
    content = content.replace(old_vb_query, new_vb_query)
    print("✅ Fixed Value Bets (Tomorrow only)")

# For Safe Bets:
old_sb_query = """SELECT vb.match_id, f.home, f.away, f.league, f.kickoff, 
               vb.market_name, vb.selection, vb.betika_odd, 
               vb.model_probability, vb.confidence_score
        FROM value_bets vb
        JOIN fixtures f ON vb.match_id = f.match_id
        WHERE vb.betika_odd BETWEEN 1.01 AND 1.30
        AND vb.ev_percent > 0
        ORDER BY f.kickoff ASC"""

new_sb_query = """SELECT vb.match_id, f.home, f.away, f.league, f.kickoff, 
               vb.market_name, vb.selection, vb.betika_odd, 
               vb.model_probability, vb.confidence_score
        FROM value_bets vb
        JOIN fixtures f ON vb.match_id = f.match_id
        WHERE vb.betika_odd BETWEEN 1.01 AND 1.30
        AND vb.ev_percent > 0 AND date(f.kickoff) = date('now', '+1 day')
        ORDER BY f.kickoff ASC"""

if old_sb_query in content:
    content = content.replace(old_sb_query, new_sb_query)
    print("✅ Fixed Safe Bets (Tomorrow only)")

with open('dashboard.py', 'w') as f:
    f.write(content)

print("\n🎉 Dashboard updated to show ONLY Tomorrow's matches!")

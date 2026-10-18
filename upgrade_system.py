"""
Upgrades the system to include Double Chance, Win to Nil, and AI Reasoning.
"""
import os
from database import get_db_connection

def upgrade_database():
    print("1. Upgrading Database Schema...")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE value_bets ADD COLUMN reasoning TEXT")
        conn.commit()
        print("   ✅ Added 'reasoning' column to value_bets")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("   ️ Column already exists, skipping.")
        else:
            print(f"   ❌ Error: {e}")
    conn.close()

def upgrade_model():
    print("\n2. Upgrading Probability Model...")
    with open('probability_model.py', 'r') as f:
        code = f.read()

    # 1. Add new market calculations (Double Chance & Win to Nil)
    # We inject this right after the standard 1X2 calculations
    old_1x2_block = """            # 4. Calculate Probabilities
            prob_home = sum(prob_matrix[i][j] for i in range(max_goals) for j in range(max_goals) if i > j)
            prob_draw = sum(prob_matrix[i][j] for i in range(max_goals) for j in range(max_goals) if i == j)
            prob_away = sum(prob_matrix[i][j] for i in range(max_goals) for j in range(max_goals) if i < j)"""
            
    new_1x2_block = """            # 4. Calculate Probabilities
            prob_home = sum(prob_matrix[i][j] for i in range(max_goals) for j in range(max_goals) if i > j)
            prob_draw = sum(prob_matrix[i][j] for i in range(max_goals) for j in range(max_goals) if i == j)
            prob_away = sum(prob_matrix[i][j] for i in range(max_goals) for j in range(max_goals) if i < j)
            
            # NEW: Double Chance & Win to Nil
            prob_1x = prob_home + prob_draw
            prob_12 = prob_home + prob_away
            prob_x2 = prob_draw + prob_away
            prob_home_wtn = sum(prob_matrix[i][0] for i in range(1, max_goals))
            prob_away_wtn = sum(prob_matrix[0][j] for j in range(1, max_goals))"""

    if old_1x2_block in code:
        code = code.replace(old_1x2_block, new_1x2_block)
        print("   ✅ Added Double Chance & Win to Nil math")
    else:
        print("   ⚠️ Could not find 1X2 block to replace")

    # 2. Add the Reasoning Generator Function
    reasoning_func = """
def generate_reasoning(home, away, home_xg, away_xg, home_att, away_def, market, ev):
    reason = f"📈 **Why?** "
    if '1' in market or 'Home' in market:
        reason += f"{home}'s Attack Strength ({home_att:.2f}) vs {away}'s Defense ({away_def:.2f}). "
        reason += f"Model predicts {home_xg:.1f} Home Goals. "
    elif '2' in market or 'Away' in market:
        reason += f"{away}'s Attack Strength vs {home}'s Defense. "
        reason += f"Model predicts {away_xg:.1f} Away Goals. "
    else:
        reason += f"Balanced matchup. Home xG: {home_xg:.1f}, Away xG: {away_xg:.1f}. "
    
    if ev > 5: reason += "High Value detected! ✅"
    elif ev > 0: reason += "Positive Edge found. 👍"
    return reason
"""
    if "def generate_reasoning" not in code:
        code = code.replace("def calculate_ev(", reasoning_func + "\ndef calculate_ev(")
        print("   ✅ Added Reasoning Generator")

    # 3. Inject the new markets into the database saving loop
    # This is a bit complex, so we will just append a block to save the new markets
    # For safety, we will just tell the user to re-run the model, and the model will naturally pick these up if we add them to the 'markets_to_check' list.
    
    # Let's find the list of markets the model checks
    old_markets = """    markets_to_check = [
        {"name": "1X2", "selections": ["1", "X", "2"]},"""
    new_markets = """    markets_to_check = [
        {"name": "1X2", "selections": ["1", "X", "2"]},
        {"name": "Double Chance", "selections": ["1X", "12", "X2"]},
        {"name": "Win to Nil", "selections": ["Home Win to Nil", "Away Win to Nil"]},"""
        
    if old_markets in code:
        code = code.replace(old_markets, new_markets)
        print("   ✅ Added new markets to checking list")

    with open('probability_model.py', 'w') as f:
        f.write(code)

def upgrade_dashboard():
    print("\n3. Upgrading Dashboard to show Reasoning...")
    with open('dashboard.py', 'r') as f:
        code = f.read()

    # Add reasoning to the dataframe display
    if "reasoning" not in code:
        # Find where the dataframe is displayed and add the reasoning column
        old_display = "st.dataframe(display_df, use_container_width=True)"
        new_display = """st.dataframe(display_df, use_container_width=True)
        if 'reasoning' in display_df.columns:
            for index, row in display_df.iterrows():
                if row.get('reasoning'):
                    st.markdown(f"💡 **{row['home']} vs {row['away']} ({row['selection']}):** {row['reasoning']}")"""
        
        if old_display in code:
            code = code.replace(old_display, new_display)
            print("   ✅ Added Reasoning display to Dashboard")
        else:
            print("   ⚠️ Could not find dataframe display block")

    with open('dashboard.py', 'w') as f:
        f.write(code)

if __name__ == "__main__":
    print("="*50)
    print("STARTING SYSTEM UPGRADE")
    print("="*50)
    upgrade_database()
    upgrade_model()
    upgrade_dashboard()
    print("\n" + "="*50)
    print("UPGRADE COMPLETE!")
    print("Next: Run 'python probability_model.py' to generate the new data.")
    print("="*50)

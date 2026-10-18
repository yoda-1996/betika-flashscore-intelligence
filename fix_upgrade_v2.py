"""
Smart Patch for Probability Model and Dashboard.
Finds keywords and injects code safely.
"""
import re

print("🔧 Starting Smart Patch...")

# --- 1. Patch Probability Model ---
print("\n1. Patching probability_model.py...")
with open('probability_model.py', 'r') as f:
    lines = f.readlines()

new_lines = []
added_math = False
added_markets = False

for i, line in enumerate(lines):
    new_lines.append(line)
    
    # A. Add DC/WTN Math after prob_away calculation
    if 'prob_away' in line and 'sum' in line and not added_math:
        indent = line[:len(line) - len(line.lstrip())]
        # We assume max_goals is the variable used in the sum. If not, we use 10 as a safe fallback.
        if 'max_goals' in line:
            range_var = 'max_goals'
        else:
            range_var = '10' 
            
        new_lines.append(f"{indent}# --- NEW MARKETS MATH ---\n")
        new_lines.append(f"{indent}prob_1x = prob_home + prob_draw\n")
        new_lines.append(f"{indent}prob_12 = prob_home + prob_away\n")
        new_lines.append(f"{indent}prob_x2 = prob_draw + prob_away\n")
        new_lines.append(f"{indent}prob_home_wtn = sum(prob_matrix[i][0] for i in range(1, {range_var}))\n")
        new_lines.append(f"{indent}prob_away_wtn = sum(prob_matrix[0][j] for j in range(1, {range_var}))\n")
        added_math = True
        print("   ✅ Added Double Chance & Win to Nil Math")

    # B. Add New Markets to the list
    if '"1X2"' in line and 'selections' in line and not added_markets:
        indent = line[:len(line) - len(line.lstrip())]
        # Insert before the 1X2 line
        insert_idx = len(new_lines) - 1
        new_lines.insert(insert_idx, f'{indent}{{"name": "Win to Nil", "selections": ["Home Win to Nil", "Away Win to Nil"]}},\n')
        new_lines.insert(insert_idx, f'{indent}{{"name": "Double Chance", "selections": ["1X", "X2"]}},\n')
        added_markets = True
        print("   ✅ Added New Markets to List")

with open('probability_model.py', 'w') as f:
    f.writelines(new_lines)

# --- 2. Patch Dashboard ---
print("\n2. Patching dashboard.py...")
with open('dashboard.py', 'r') as f:
    content = f.read()

if 'reasoning' not in content:
    if 'st.dataframe' in content:
        lines = content.split('\n')
        new_content = []
        for line in lines:
            new_content.append(line)
            # Find the dataframe display and add reasoning below it
            if 'st.dataframe' in line and 'display_df' in line:
                indent = line[:len(line) - len(line.lstrip())]
                new_content.append(f"{indent}# --- REASONING DISPLAY ---")
                new_content.append(f"{indent}if 'reasoning' in display_df.columns:")
                new_content.append(f"{indent}    for index, row in display_df.iterrows():")
                new_content.append(f"{indent}        if row.get('reasoning'):")
                new_content.append(f"{indent}            st.markdown(f\" **{{row.get('home', '')}} vs {{row.get('away', '')}} ({{row.get('selection', '')}}):** {{row['reasoning']}}\")")
        content = '\n'.join(new_content)
        print("   ✅ Added Reasoning Display to Dashboard")
    else:
        print("   ⚠️ Could not find st.dataframe in dashboard.py")

with open('dashboard.py', 'w') as f:
    f.write(content)

print("\n🎉 Smart Patch Complete!")
print("Next: Run 'python probability_model.py' to generate the new data.")

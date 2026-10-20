"""
Replaces the old Poisson loop with the new Skellam Hybrid function.
"""
import re

print("🔧 Installing Skellam Function...")

with open('probability_model.py', 'r') as f:
    content = f.read()

# 1. Ensure imports
if 'from scipy.stats import skellam' not in content:
    content = content.replace("import sqlite3", "import sqlite3\nfrom scipy.stats import skellam, poisson")
    print("   ✅ Added SciPy imports")

# 2. Define the new function
new_func = """def calculate_skellam_hybrid_probs(lambda_home, lambda_away):
    \"\"\"
    Hybrid Model:
    - Uses Skellam Distribution for 1X2 (More accurate)
    - Uses Poisson Sum for Over/Under
    - Uses Independent Poisson for BTTS
    \"\"\"
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

"""

# 3. Find and Replace the old function
# We look for the start of the old function and replace it until we hit the next major block (like 'probs = calculate')
# Pattern: "def calculate_poisson_probs..." followed by anything, until we see "probs = calculate_poisson_probs"
# We want to keep the CALL, just replace the DEFINITION.

# Let's just replace the definition block.
# The old function starts at "def calculate_poisson_probs"
# We need to find where it ends. In your screenshot, it seemed to end before the main logic loop.

# Safer strategy: 
# If the old function exists, delete it. Then insert the new one at a safe spot (e.g. before the main run_model function).

old_func_pattern = r"def calculate_poisson_probs\(lambda_home, lambda_away\):.*?(?=\ndef |\nif __name__)"
# This regex finds the old function and stops before the next 'def' or 'if __name__'

if "def calculate_poisson_probs" in content:
    # We found the old function. Let's replace it.
    # We will replace the whole block with the new one.
    # But we need to be careful not to delete the CALL to the function.
    # The call is usually `probs = calculate_poisson_probs(...)`.
    # The regex above `.*?(?=\ndef |\nif __name__)` will stop before the next function definition.
    # The call `probs = ...` is usually INSIDE another function (like run_model).
    # So replacing `def calculate...` up to the next `def` should be safe.
    
    # Let's try to match the old function definition specifically.
    # It starts with "def calculate_poisson_probs" and ends when indentation returns to 0 or next def.
    # Since I can't perfectly regex indentation, I'll use a simpler marker.
    # I will look for "def calculate_poisson_probs" and replace everything until "return probs" (roughly).
    
    # Actually, let's just append the new function to the TOP of the file (after imports) and rename the call.
    # And delete the old function.
    
    # Find the old function start
    start_idx = content.find("def calculate_poisson_probs")
    if start_idx != -1:
        # Find the next function definition or end of file to know where old one ends? 
        # No, that's risky.
        
        # Let's just APPEND the new function to the very top (after imports) and DELETE the old one.
        # 1. Delete old one:
        # We need to find where it ends.
        # In your screenshot, the function seemed to end around line 139.
        # Let's assume it ends before the comment "# Home Advantage Boost" or similar logic outside it.
        # Actually, looking at screenshot 1, the function ENDS at line 139 (return probs is implied or explicit).
        # Wait, line 139 is "# 1st Half approximation".
        # The function likely returns after that.
        
        # Let's try a different tactic.
        # I will simply ADD the new function at the top, and RENAME the call.
        # Then I will COMMENT OUT the old function so it doesn't conflict.
        
        # Find imports
        import_end = content.find("import sqlite3")
        if import_end != -1:
            # Find end of import block
            next_line = content.find("\n", import_end)
            insert_pos = next_line + 1
            
            content = content[:insert_pos] + "\n" + new_func + content[insert_pos:]
            print("   ✅ Inserted new function after imports")
        
        # Now comment out the old function to prevent errors
        # We look for the line "def calculate_poisson_probs"
        content = content.replace("def calculate_poisson_probs(lambda_home, lambda_away):", "# DEPRECATED: def calculate_poisson_probs(lambda_home, lambda_away):")
        print("   ✅ Deprecated old function")

# 4. Update the call
content = content.replace(
    "probs = calculate_poisson_probs(lambda_home, lambda_away)",
    "probs = calculate_skellam_hybrid_probs(lambda_home, lambda_away)"
)
print("   ✅ Updated function call")

with open('probability_model.py', 'w') as f:
    f.write(content)

print("\n🎉 Fix Applied!")

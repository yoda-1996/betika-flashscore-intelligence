"""
Upgrades probability_model.py to use Skellam Distribution for 1X2 
and optimized Poisson for Totals/BTTS.
"""
import re

print("🚀 Upgrading Model to Skellam Hybrid...")

with open('probability_model.py', 'r') as f:
    content = f.read()

# 1. Ensure imports are there
if 'from scipy.stats import skellam' not in content:
    # Add import at the top, after the first import block
    content = content.replace("import sqlite3", "import sqlite3\nfrom scipy.stats import skellam, poisson")
    print("   ✅ Added SciPy imports")

# 2. Define the new Hybrid Function
new_function = """
def calculate_skellam_hybrid_probs(lambda_home, lambda_away):
    \"\"\"
    Hybrid Model:
    - Uses Skellam Distribution for 1X2 (More accurate, infinite goal range)
    - Uses Poisson Sum for Over/Under (Faster than looping)
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
"""

# 3. Replace the old function
# We look for the old function definition and replace it until the next function or end of logic
# The old function starts with "def calculate_poisson_probs"
# We will use regex to find it and replace it.

pattern = r"def calculate_poisson_probs\(lambda_home, lambda_away\):.*?(?=\n\s*# Home Advantage Boost|\n\s*probs = calculate_|\n\s*cursor\.execute)"
# Note: The regex above tries to stop before the code that USES the function.
# Looking at your screenshot, the function ends around line 139, and the usage is around line 140 ("probs = calculate...").
# Actually, looking closely at screenshot 2, line 140 is `probs = calculate_poisson_probs(lambda_home, lambda_away)`.
# So we need to replace everything from `def calculate_poisson_probs` up to (but not including) `probs = calculate_poisson_probs`.

# Let's do a simpler string replacement based on the structure we saw.
old_func_start = "def calculate_poisson_probs(lambda_home, lambda_away):"
# We need to find where this function ends. In your screenshot, it seems to end before `# Home Advantage Boost`? 
# No, `# Home Advantage Boost` is OUTSIDE the function in the second screenshot (line 116 is lambda calc, line 118 is boost, line 120 is function def? No wait.)

# Let's look at the line numbers in Screenshot 1:
# 119: def calculate_poisson_probs...
# 139: # 1st Half approximation...
# It seems the function continues.

# SAFEST APPROACH:
# We will just append the new function to the end of the file, 
# and change the CALL to use the new name.
# This avoids breaking the old code structure.

content += "\n" + new_function
print("   ✅ Appended new Skellam function to file")

# 4. Update the function call
# Change `probs = calculate_poisson_probs(lambda_home, lambda_away)` 
# to `probs = calculate_skellam_hybrid_probs(lambda_home, lambda_away)`
content = content.replace(
    "probs = calculate_poisson_probs(lambda_home, lambda_away)",
    "probs = calculate_skellam_hybrid_probs(lambda_home, lambda_away)"
)
print("   ✅ Updated function call to use Hybrid Model")

with open('probability_model.py', 'w') as f:
    f.write(content)

print("\n🎉 Model Upgraded to Skellam Hybrid!")
print("Next: Run 'python probability_model.py' to test the new math.")

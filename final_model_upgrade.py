"""
Final Upgrade: Adds Verbose Skellam Model correctly.
"""
print(" Starting Final Upgrade...")

with open('probability_model.py', 'r') as f:
    content = f.read()

# 1. The New Function Code
# We use simple prints to avoid syntax errors
new_function = """
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
    print(f"\\n--- Model Check (Lambda H:{lambda_home:.2f} / A:{lambda_away:.2f}) ---")
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
    
    return probs

"""

# 2. Insert the function after the imports
# We look for 'import sqlite3' and insert after that line
import_marker = "import sqlite3"
if import_marker in content and "def calculate_verbose_probs" not in content:
    # Find the end of the import line
    idx = content.find(import_marker)
    end_of_line = content.find("\n", idx)
    
    # Insert the new function
    content = content[:end_of_line+1] + new_function + content[end_of_line+1:]
    print("✅ Inserted function after imports")
else:
    print("⚠️ Could not find import or function already exists.")

# 3. Update the function call
old_call = "probs = calculate_skellam_hybrid_probs(lambda_home, lambda_away)"
new_call = "probs = calculate_verbose_probs(lambda_home, lambda_away)"

if old_call in content:
    content = content.replace(old_call, new_call)
    print("✅ Updated function call")
else:
    print("⚠️ Could not find the function call to update.")

# 4. Save
with open('probability_model.py', 'w') as f:
    f.write(content)

print("\n🎉 Upgrade Complete!")

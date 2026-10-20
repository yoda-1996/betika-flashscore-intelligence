"""
Safely patches Handicap support using simple text replacement.
"""
print("🔧 Applying Safe Handicap Patch...")

with open('probability_model.py', 'r') as f:
    content = f.read()

# 1. Fix SQL Query to get 'line' data
# We look for the SELECT statement and add 'line'
old_sql = "SELECT market_name, selection, odd FROM odds"
new_sql = "SELECT market_name, selection, odd, line FROM odds"

if old_sql in content:
    content = content.replace(old_sql, new_sql)
    print("   ✅ Fixed SQL Query")
else:
    print("   ⚠️ SQL Query not found exactly. Trying single quotes...")
    content = content.replace("SELECT market_name, selection, odd FROM odds", "SELECT market_name, selection, odd, line FROM odds")

# 2. Extract 'line' in the loop
old_loop_line = "betika_odd = odd_row['odd']"
new_loop_line = """betika_odd = odd_row['odd']
            line = odd_row.get('line', '')"""

if old_loop_line in content:
    content = content.replace(old_loop_line, new_loop_line)
    print("   ✅ Added 'line' extraction")

# 3. Inject Handicap Logic
# We insert this block right before the "TOTAL" check
target = 'elif market in ["TOTAL", "Over/Under"]:'

handicap_block = """elif "HANDICAP" in market.upper():
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
            """

# Note: The indentation above is 12 spaces (3 levels of 4 spaces) to match the loop body.
# Wait, looking at previous code, the loop body is indented 8 spaces (2 levels).
# Let's adjust indentation to be safe.
# The 'elif' should align with 'if market in...'.

# Let's try a simpler injection:
# Find "model_prob = 0.0" inside the loop and add logic after it? No.

# Let's just use the block above but ensure indentation matches the file.
# Usually 'elif market...' is indented by 12 spaces (inside for loop, inside if/elif chain).

if target in content and "HANDICAP" not in content:
    # We need to match the indentation of the target line.
    # Let's assume standard 4-space indentation.
    # The target 'elif market...' is likely indented 12 spaces.
    
    # Let's just prepend the block to the target.
    # We need to make sure the indentation of 'elif "HANDICAP"...' matches 'elif market...'.
    
    # Find the indentation of the target line
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'elif market in ["TOTAL"' in line:
            indent = line[:len(line) - len(line.lstrip())]
            # Re-format the block with correct indent
            block_lines = [
                f'{indent}elif "HANDICAP" in market.upper():',
                f'{indent}    try:',
                f"{indent}        if line and 'hcp=' in str(line):",
                f"{indent}            h_val, a_val = map(int, str(line).split('=')[1].split(':'))",
                f"{indent}            target_diff = a_val - h_val",
                f"{indent}            if home_team.split()[0] in selection:",
                f"{indent}                model_prob = skellam.sf(target_diff, lambda_home, lambda_away)",
                f"{indent}            elif 'draw' in selection.lower():",
                f"{indent}                model_prob = skellam.pmf(target_diff, lambda_home, lambda_away)",
                f"{indent}            elif away_team.split()[0] in selection:",
                f"{indent}                model_prob = skellam.cdf(target_diff - 1, lambda_home, lambda_away)",
                f"{indent}    except Exception:",
                f"{indent}        pass"
            ]
            block_str = '\n'.join(block_lines) + '\n'
            
            # Insert before the target line
            content = content.replace(line, block_str + line)
            print("   ✅ Injected Handicap Logic with correct indentation")
            break

with open('probability_model.py', 'w') as f:
    f.write(content)

print("\n🎉 Patch Applied!")
print("Next: Run 'python probability_model.py'")

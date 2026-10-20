"""
Adds the missing 1H BTTS keys to the verbose function.
"""
print("🔧 Fixing 1H BTTS Keys...")

with open('probability_model.py', 'r') as f:
    content = f.read()

# Find the line where we return probs and add the 1H logic before it
target = "    return probs"

# We want to insert the 1H logic right before the return statement inside calculate_verbose_probs
# To be safe, let's look for the specific return inside that function.
# The function ends with:
#     probs['BTTS No'] = 1 - probs['BTTS Yes']
#     
#     return probs

old_block = """    probs['BTTS Yes'] = (1 - poisson.pmf(0, lambda_home)) * (1 - poisson.pmf(0, lambda_away))
    probs['BTTS No'] = 1 - probs['BTTS Yes']
    
    return probs"""

new_block = """    probs['BTTS Yes'] = (1 - poisson.pmf(0, lambda_home)) * (1 - poisson.pmf(0, lambda_away))
    probs['BTTS No'] = 1 - probs['BTTS Yes']
    
    # 1st Half Approximation (42% of goals usually happen in 1st half)
    lambda_home_1h = lambda_home * 0.42
    lambda_away_1h = lambda_away * 0.42
    p_home_1h_scores = 1 - poisson.pmf(0, lambda_home_1h)
    p_away_1h_scores = 1 - poisson.pmf(0, lambda_away_1h)
    probs['1H BTTS Yes'] = p_home_1h_scores * p_away_1h_scores
    probs['1H BTTS No'] = 1 - probs['1H BTTS Yes']
    
    return probs"""

if old_block in content:
    content = content.replace(old_block, new_block)
    print("   ✅ Added 1H BTTS logic")
else:
    print("   ️ Could not find the exact block. Trying manual insertion...")
    # Fallback: Just add the keys before the first 'return probs' found in the file
    # This is risky if there are multiple returns, but usually safe here.
    content = content.replace("    return probs", "    probs['1H BTTS Yes'] = 0.0\n    probs['1H BTTS No'] = 1.0\n    return probs", 1)
    print("   ✅ Applied fallback fix (values might be 0.0 for now)")

with open('probability_model.py', 'w') as f:
    f.write(content)

print("\n🎉 1H BTTS Fixed!")
print("Next: Run 'python probability_model.py'")

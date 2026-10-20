"""
Fixes the duplication issue by clearing value_bets before each model run.
"""
print("🔧 Fixing Duplicate Bets Issue...")

with open('probability_model.py', 'r') as f:
    content = f.read()

# Find the start of run_model() and add a DELETE statement
# We want to clear value_bets before processing new fixtures
target = "def run_model():"

cleanup_code = """def run_model():
    # Clear old value bets to prevent duplicates
    cursor.execute("DELETE FROM value_bets")
    conn.commit()
    print("️ Cleared old value bets")
"""

if target in content:
    # Replace the function definition with one that includes cleanup
    content = content.replace(target, cleanup_code, 1)
    print("   ✅ Added cleanup at start of run_model()")
else:
    print("   ⚠️ Could not find run_model() function")

with open('probability_model.py', 'w') as f:
    f.write(content)

print("\n🎉 Duplicate Fix Applied!")
print("Next: Run 'python probability_model.py' then check dashboard")

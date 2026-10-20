"""
Fixes the sqlite3.Row 'get' attribute error.
"""
print(" Fixing sqlite3.Row attribute error...")

with open('probability_model.py', 'r') as f:
    content = f.read()

# Replace .get('line', '') with ['line'] or dict conversion
old_line = "line = odd_row.get('line', '')"
new_line = "line = odd_row['line'] if 'line' in odd_row.keys() else ''"

if old_line in content:
    content = content.replace(old_line, new_line)
    print("   ✅ Fixed line extraction")
else:
    print("   ⚠️ Could not find exact line to fix.")

with open('probability_model.py', 'w') as f:
    f.write(content)

print("\n🎉 Fix Applied!")
print("Next: Run 'python probability_model.py'")

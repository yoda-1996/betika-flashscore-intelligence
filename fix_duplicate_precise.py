"""
Precisely fixes the duplicate bets issue by finding the correct cursor initialization.
"""
print("🔧 Applying Precise Duplicate Fix...")

with open('probability_model.py', 'r') as f:
    lines = f.readlines()

# Find the run_model function and locate cursor initialization
new_lines = []
in_run_model = False
cleanup_added = False

for i, line in enumerate(lines):
    new_lines.append(line)
    
    # Detect when we're inside run_model
    if 'def run_model()' in line:
        in_run_model = True
        continue
    
    # Look for cursor initialization inside run_model
    if in_run_model and not cleanup_added and 'cursor = conn.cursor()' in line:
        # Add cleanup right after cursor is created
        indent = '    '  # 4 spaces for function body
        new_lines.append(f'{indent}# Clear old value bets to prevent duplicates\n')
        new_lines.append(f'{indent}cursor.execute("DELETE FROM value_bets")\n')
        new_lines.append(f'{indent}conn.commit()\n')
        new_lines.append(f'{indent}print("🗑️ Cleared old value bets")\n')
        cleanup_added = True
        print("   ✅ Added cleanup after cursor initialization")

with open('probability_model.py', 'w') as f:
    f.writelines(new_lines)

print("\n🎉 Precise Fix Applied!")
print("Next: Run 'python probability_model.py'")

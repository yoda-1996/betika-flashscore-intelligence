"""
Smart Fix: Removes broken DELETE statement and places it correctly after cursor initialization.
"""
print(" Applying Smart Fix...")

with open('probability_model.py', 'r') as f:
    lines = f.readlines()

new_lines = []
fixed = False

for line in lines:
    # 1. Remove the broken DELETE statement causing the crash
    if 'DELETE FROM value_bets' in line:
        continue # Skip this line entirely
        
    # 2. Find the correct cursor initialization and inject after it
    if not fixed and line.strip() == 'cursor = conn.cursor()':
        new_lines.append(line)
        # Dynamically copy indentation from the cursor line
        indent = line[:len(line) - len(line.lstrip())]
        new_lines.append(f"{indent}# Clear old value bets to prevent duplicates\n")
        new_lines.append(f"{indent}cursor.execute('DELETE FROM value_bets')\n")
        new_lines.append(f"{indent}conn.commit()\n")
        new_lines.append(f"{indent}print('🗑️ Cleared old value bets')\n")
        fixed = True
        print("   ✅ Injected cleanup after cursor initialization")
        continue
        
    new_lines.append(line)

with open('probability_model.py', 'w') as f:
    f.writelines(new_lines)

print("\n🎉 Smart Fix Complete!")

"""
Smart Fix: Cleans up broken code and injects the DELETE statement in the exact right spot.
"""
print(" Working Smarter: Applying Robust Fix...")

with open('probability_model.py', 'r') as f:
    lines = f.readlines()

new_lines = []
in_run_model = False
cleanup_added = False

for line in lines:
    # 1. CLEANUP: Remove any old, broken DELETE statements we added previously
    if 'DELETE FROM value_bets' in line:
        continue  # Skip this line entirely (effectively deleting it)
    
    # 2. Add the current line to our new file
    new_lines.append(line)
    
    # 3. Track when we enter the main function
    if 'def run_model()' in line:
        in_run_model = True
        
    # 4. INJECT: If we are in the function, haven't added cleanup yet, 
    # and we see the cursor being created...
    if in_run_model and not cleanup_added and 'cursor = conn.cursor()' in line:
        # Get the indentation of the current line (usually 4 spaces)
        indent = len(line) - len(line.lstrip())
        spaces = ' ' * indent
        
        # Insert the cleanup code immediately after the cursor is created
        new_lines.append(f"{spaces}# Clear old value bets to prevent duplicates\n")
        new_lines.append(f"{spaces}cursor.execute('DELETE FROM value_bets')\n")
        new_lines.append(f"{spaces}conn.commit()\n")
        new_lines.append(f"{spaces}print('🗑️ Cleared old value bets')\n")
        
        cleanup_added = True
        print("   ✅ Injected cleanup at the perfect spot")

# Save the fixed file
with open('probability_model.py', 'w') as f:
    f.writelines(new_lines)

if cleanup_added:
    print("\n🎉 Smart Fix Applied Successfully!")
else:
    print("\n⚠️ Could not find the right spot. Check the file manually.")

print("Next: Run 'python probability_model.py'")

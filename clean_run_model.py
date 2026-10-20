"""
Cleanly rewrites the top of run_model to fix scope errors and duplicates.
"""
print("🧹 Cleaning up run_model function...")

with open('probability_model.py', 'r') as f:
    content = f.read()

# 1. Define the correct start of the function
correct_start = """def run_model():
    print("🚀 Starting Probability Model v3 (Refined) ...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clear old value bets to prevent duplicates
    cursor.execute('DELETE FROM value_bets')
    conn.commit()
    print("🗑️ Cleared old value bets")
"""

# 2. Find the start of the function and the first valid line after the mess
# We look for "def run_model():" and then "print("🚀 Starting..."
# Actually, looking at the sed output, the print statement is on line 260.

# Let's use a regex to replace everything from "def run_model():" up to "conn = get_db_connection()"
import re

# Pattern: def run_model(): ... (anything) ... conn = get_db_connection()
# We want to keep "def run_model():" and "conn = get_db_connection()" but fix the middle.

# Actually, simpler: Just replace the specific broken block we saw in the screenshot.
# The broken block is:
# def run_model():
#     # Clear old value bets to prevent duplicates
#     conn.commit()
#     print(" Cleared old value bets")
# 
#     print(" Starting Probability Model v3 (Refined) ...")

broken_block_pattern = r"def run_model\(\):\s*# Clear old value bets to prevent duplicates\s*conn\.commit\(\)\s*print\([\"'].*?Cleared old value bets[\"']\)\s*print\([\"'].*?Starting Probability Model.*?[\"']\)"

replacement = """def run_model():
    print("🚀 Starting Probability Model v3 (Refined) ...")"""

if re.search(broken_block_pattern, content, re.DOTALL):
    content = re.sub(broken_block_pattern, replacement, content, count=1)
    print("   ✅ Removed broken startup code")
else:
    print("   ⚠️ Could not find exact broken block. Trying manual line removal...")
    # Fallback: Just remove lines containing "conn.commit()" that appear before "conn = get_db_connection()"
    lines = content.split('\n')
    new_lines = []
    found_conn_def = False
    cleanup_added = False
    
    for i, line in enumerate(lines):
        # If we see the connection definition, mark it
        if 'conn = get_db_connection()' in line:
            found_conn_def = True
            
        # If we see a cleanup print/commit BEFORE the connection is defined, skip it
        if not found_conn_def and ('conn.commit()' in line or 'Cleared old value bets' in line):
            continue
            
        # If we see a duplicate cleanup block AFTER the connection is defined (and we already added one), skip it
        if found_conn_def and 'Cleared old value bets' in line and cleanup_added:
            # Skip this line and the previous comment line if it exists
            if new_lines and '# Clear old value bets' in new_lines[-1]:
                new_lines.pop()
            continue
            
        # If we see the cursor execution for DELETE, mark that we've added cleanup
        if 'DELETE FROM value_bets' in line:
            cleanup_added = True
            
        new_lines.append(line)
        
    content = '\n'.join(new_lines)
    print("   ✅ Applied manual cleanup")

# 3. Ensure the correct cleanup block exists after cursor creation
# If it's missing, add it.
if 'DELETE FROM value_bets' not in content:
    # Add it after cursor = conn.cursor()
    content = content.replace(
        'cursor = conn.cursor()',
        'cursor = conn.cursor()\n    # Clear old value bets to prevent duplicates\n    cursor.execute("DELETE FROM value_bets")\n    conn.commit()\n    print("️ Cleared old value bets")',
        1
    )
    print("   ✅ Added missing cleanup block")

with open('probability_model.py', 'w') as f:
    f.write(content)

print("\n🎉 Function Cleaned!")
print("Next: Run 'python probability_model.py'")

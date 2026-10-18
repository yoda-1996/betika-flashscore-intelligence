"""
Fixes the indentation error in dashboard.py around line 297.
"""

with open('dashboard.py', 'r') as f:
    lines = f.readlines()

# Find the problematic "with s_tab7:" line
new_lines = []
skip_next_3 = False

for i, line in enumerate(lines):
    # Look for the broken "with s_tab7:" block
    if 'with s_tab7:' in line and 'render_htft_table' not in line:
        # This is the start of our new block - replace it and the next 3 lines
        # Find the correct indentation by looking at the previous "with s_tab6:" line
        indent = "                "  # 16 spaces (matches the other tabs)
        
        new_lines.append(f"{indent}with s_tab7:\n")
        new_lines.append(f"{indent}    htft_sub1, htft_sub2, htft_sub3 = st.tabs([\"Overall\", \"Home\", \"Away\"])\n")
        new_lines.append(f"{indent}    with htft_sub1: render_htft_table(row['ht_ft_table'], \"Half-Time/Full-Time Stats (Overall)\")\n")
        new_lines.append(f"{indent}    with htft_sub2: render_htft_table(row['ht_ft_home_table'], \"Half-Time/Full-Time Stats (Home)\")\n")
        new_lines.append(f"{indent}    with htft_sub3: render_htft_table(row['ht_ft_away_table'], \"Half-Time/Full-Time Stats (Away)\")\n")
        
        # Skip the next few lines that were part of the broken block
        skip_next_3 = True
        continue
    
    if skip_next_3:
        # Skip lines that are part of the old broken block
        if 'htft_sub' in line or ('render_htft_table' in line and 'ht_ft' in line):
            continue
        else:
            skip_next_3 = False
    
    new_lines.append(line)

with open('dashboard.py', 'w') as f:
    f.writelines(new_lines)

print("✅ Indentation fixed!")

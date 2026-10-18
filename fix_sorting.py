"""Updates dashboard.py to sort all tabs by Kickoff Time."""

with open('dashboard.py', 'r') as f:
    content = f.read()

# 1. Fix Value Bets Query
if "ORDER BY vb.ev_percent DESC" in content:
    content = content.replace("ORDER BY vb.ev_percent DESC", "ORDER BY f.kickoff ASC")
    print("✅ Fixed Value Bets sorting")

# 2. Fix Safe Bets Query  
if "ORDER BY vb.model_probability DESC" in content:
    content = content.replace("ORDER BY vb.model_probability DESC", "ORDER BY f.kickoff ASC")
    print("✅ Fixed Safe Bets sorting")

# 3. Fix Ultimate Report Dropdown
if "ORDER BY home" in content:
    content = content.replace("ORDER BY home", "ORDER BY kickoff ASC")
    print("✅ Fixed Ultimate Report sorting")

with open('dashboard.py', 'w') as f:
    f.write(content)

print("\n🎉 Dashboard sorting updated!")

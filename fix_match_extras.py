"""
Fixes the indentation error in dashboard.py around line 323.
Replaces the Match Extras section with correctly indented code.
"""

with open('dashboard.py', 'r') as f:
    content = f.read()

# Find the start of the broken section
target = '            st.subheader("🏥 Match Extras")'
if target not in content:
    # Try a slightly different indentation
    target = '        st.subheader("🏥 Match Extras")'

if target in content:
    # Split the content at the target
    parts = content.split(target)
    before = parts[0]
    
    # The correctly indented replacement block
    # Note: The indentation here must match the 'st.subheader("⚔️ Head-to-Head...")' block above it
    replacement = '''            st.subheader("🏥 Match Extras")
            if not df_extras.empty:
                row_ex = df_extras.iloc[0]
                
                # 1. Flashscore Preview / Summary
                with st.expander("📰 Flashscore Preview / Match News", expanded=True):
                    report_data = parse_json_safe(row_ex['report'])
                    if report_data:
                        preview_text = None
                        for key in ['preview', 'summary', 'text', 'description', 'content']:
                            if key in report_data and isinstance(report_data[key], str):
                                preview_text = report_data[key]
                                break
                        
                        if not preview_text and isinstance(report_data, dict):
                            for section in ['home', 'away', 'match']:
                                if section in report_data and isinstance(report_data[section], dict):
                                    for key in ['preview', 'summary', 'text', 'description']:
                                        if key in report_data[section]:
                                            preview_text = report_data[section][key]
                                            break
                                    if preview_text:
                                        break
                        
                        if preview_text:
                            st.markdown(f"**Match Preview:**\\n\\n{preview_text}")
                        else:
                            st.json(report_data)
                    else:
                        st.info("No preview available for this match.")
                
                # 2. Injuries / Missing Players
                with st.expander(" Injuries / Missing Players"):
                    inj = parse_json_safe(row_ex['injuries'])
                    if inj:
                        if isinstance(inj, dict):
                            home_injuries = inj.get('home', [])
                            away_injuries = inj.get('away', [])
                            
                            if home_injuries:
                                st.subheader("🏠 Home Team Injuries")
                                for player in home_injuries:
                                    player_info = player.get('player', {})
                                    name = player_info.get('name', 'Unknown')
                                    reason = player.get('reason', 'Unknown')
                                    likelihood = player.get('likelihood', '')
                                    st.markdown(f"- **{name}**: {reason} {likelihood}")
                            
                            if away_injuries:
                                st.subheader("✈️ Away Team Injuries")
                                for player in away_injuries:
                                    player_info = player.get('player', {})
                                    name = player_info.get('name', 'Unknown')
                                    reason = player.get('reason', 'Unknown')
                                    likelihood = player.get('likelihood', '')
                                    st.markdown(f"- **{name}**: {reason} {likelihood}")
                        else:
                            st.json(inj)
                    else:
                        st.write("No injury data.")
                
                # 3. Lineups
                with st.expander("👥 Lineups"):
                    lin = parse_json_safe(row_ex['lineups'])
                    if lin:
                        st.json(lin)
                    else:
                        st.write("Lineups not announced.")
'''
    
    new_content = before + replacement
    
    with open('dashboard.py', 'w') as f:
        f.write(new_content)
        
    print("✅ Match Extras section fixed!")
else:
    print("❌ Could not find the target line to replace.")

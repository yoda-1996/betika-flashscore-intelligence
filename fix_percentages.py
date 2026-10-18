"""
Automatically fixes the percentage display in the Safe Bets tab.
"""
with open('dashboard.py', 'r') as f:
    content = f.read()

# The old, broken dataframe block
old_block = """            st.dataframe(
                df_safe[['league', 'home', 'away', 'market_name', 'selection', 
                         'betika_odd', 'model_probability', 'safety_margin', 'confidence_score']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "betika_odd": st.column_config.NumberColumn("Odds", format="%.2f"),
                    "model_probability": st.column_config.NumberColumn("Model Win %", format="%.1f%%"),
                    "safety_margin": st.column_config.NumberColumn("Safety Margin %", format="%.1f%%", help="How much safer this is than the odds suggest"),
                    "confidence_score": st.column_config.ProgressColumn("Data Quality", min_value=0.0, max_value=1.0, format="%.0f%%")
                }
            )"""

# The new, fixed dataframe block
new_block = """            # Fix display numbers (multiply decimals by 100 for %)
            display_df = df_safe.copy()
            display_df['model_probability'] = display_df['model_probability'] * 100
            display_df['confidence_score'] = display_df['confidence_score'] * 100
            
            st.dataframe(
                display_df[['league', 'home', 'away', 'market_name', 'selection', 
                         'betika_odd', 'model_probability', 'safety_margin', 'confidence_score']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "betika_odd": st.column_config.NumberColumn("Odds", format="%.2f"),
                    "model_probability": st.column_config.NumberColumn("Model Win %", format="%.1f%%"),
                    "safety_margin": st.column_config.NumberColumn("Safety Margin %", format="%.1f%%"),
                    "confidence_score": st.column_config.ProgressColumn("Data Quality", min_value=0.0, max_value=100.0, format="%.0f%%")
                }
            )"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('dashboard.py', 'w') as f:
        f.write(content)
    print("✅ Percentages fixed successfully!")
else:
    print("ℹ️ Code already looks correct or block not found. You're good to go!")

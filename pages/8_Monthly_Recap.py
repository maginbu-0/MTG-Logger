import streamlit as st
import pandas as pd
import datetime
from zoneinfo import ZoneInfo
import db

def get_ast_today():
    return datetime.datetime.now(ZoneInfo("America/Santo_Domingo")).date()

st.subheader("📅 Monthly Session Recap & Share")

@st.fragment
def render_monthly_recap_fragment():
    today = get_ast_today()
    
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        selected_year = st.selectbox("Select Year", options=[2026, 2025], index=0, key="monthly_year_picker")
    with col_r2:
        selected_month = st.selectbox(
            "Select Month",
            options=list(range(1, 13)),
            index=today.month - 1,
            format_func=lambda x: datetime.date(2026, x, 1).strftime("%B"),
            key="monthly_month_picker"
        )
        
    month_date = datetime.date(selected_year, selected_month, 1)
    
    # Fetch data using your db helper pattern
    recap_data = db.fetch_monthly_session_summary(selected_year, selected_month) if hasattr(db, 'fetch_monthly_session_summary') else None
    
    if recap_data:
        ov = recap_data['overview']
        p_df = pd.DataFrame(recap_data['players'])
        d_df = pd.DataFrame(recap_data['decks'])
        
        mvp_player = p_df.iloc[0]['player_name'] if not p_df.empty else "N/A"
        mvp_wins = p_df.iloc[0]['wins'] if not p_df.empty else 0
        best_deck = d_df.iloc[0]['deck_name'] if not d_df.empty else "N/A"
        
        st.markdown(f"### ⚔️ Monthly Breakdown — {month_date.strftime('%B %Y')}")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Matches Logged", ov['total_games'])
        m2.metric("Total Playtime", f"{int(ov['total_playtime'])} mins")
        m3.metric("Avg Turn Count", f"Turn {ov['avg_turns']}")
        m4.metric("Monthly MVP 🏆", f"{mvp_player}")
        
        st.divider()
        
        col_p_tab, col_d_tab = st.columns(2)
        
        with col_p_tab:
            st.markdown("#### 👤 Player Leaderboard (Monthly)")
            st.dataframe(
                p_df[['player_name', 'games_played', 'wins', 'win_rate']],
                column_config={
                    "player_name": st.column_config.TextColumn("Player"),
                    "games_played": st.column_config.NumberColumn("Played", format="%d"),
                    "wins": st.column_config.NumberColumn("Wins", format="%d"),
                    "win_rate": st.column_config.NumberColumn("Win %", format="%.1f%%"),
                },
                hide_index=True,
                use_container_width=True
            )
            
        with col_d_tab:
            st.markdown("#### 🃏 Top Decks Performance (Monthly)")
            st.dataframe(
                d_df[['deck_name', 'owner_name', 'wins', 'win_rate']],
                column_config={
                    "deck_name": st.column_config.TextColumn("Deck"),
                    "owner_name": st.column_config.TextColumn("Pilot"),
                    "wins": st.column_config.NumberColumn("Wins", format="%d"),
                    "win_rate": st.column_config.NumberColumn("Win %", format="%.1f%%"),
                },
                hide_index=True,
                use_container_width=True
            )
            
        st.divider()
        
        st.markdown("#### 💬 Group Chat Monthly Recap Export")
        
        summary_text = f"🏆 *EDH MONTHLY RECAP — {month_date.strftime('%B %Y').upper()}*\n"
        summary_text += f"📊 *Total Games:* {ov['total_games']} | *Playtime:* {int(ov['total_playtime'])} mins | *Avg:* Turn {ov['avg_turns']}\n"
        summary_text += f"👑 *Monthly MVP:* {mvp_player} ({mvp_wins} Wins)\n"
        summary_text += f"🔥 *Top Deck:* {best_deck}\n\n"
        summary_text += "*Monthly Standings:*\n"
        for _, row in p_df.iterrows():
            summary_text += f"• {row['player_name']}: {row['wins']}W / {row['games_played']}G ({row['win_rate']}%)\n"

        st.code(summary_text, language="text")
        st.caption("💡 Click the copy button in the top right of the text box above to share directly into your playgroup's chat!")
    else:
        st.info(f"No match sessions logged in {month_date.strftime('%B %Y')}.")

render_monthly_recap_fragment()
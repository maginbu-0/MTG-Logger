import streamlit as st
import pandas as pd
from datetime import datetime
from utils.db import get_supabase_client  # Adapt based on your DB module helper

st.set_page_config(page_title="Monthly Recap", page_icon="📅", layout="wide")
st.title("📅 Monthly Recap")

supabase = get_supabase_client()

# --- 1. Month / Year Selector ---
col1, col2 = st.columns(2)
with col1:
    selected_year = st.selectbox("Year", options=[2026, 2025], index=0)
with col2:
    selected_month = st.selectbox(
        "Month", 
        options=list(range(1, 13)), 
        format_func=lambda x: datetime(2026, x, 1).strftime("%B")
    )

month_name = datetime(2026, selected_month, 1).strftime("%B")

# --- 2. Fetch Monthly Match Data ---
# Calculate start and end dates for filtering
start_date = f"{selected_year}-{selected_month:02d}-01"
if selected_month == 12:
    end_date = f"{selected_year + 1}-01-01"
else:
    end_date = f"{selected_year}-{selected_month + 1:02d}-01"

# Query Supabase for completed matches in range
response = supabase.table("matches") \
    .select("*, match_players(*)") \
    .gte("created_at", start_date) \
    .lt("created_at", end_date) \
    .execute()

matches = response.data

if not matches:
    st.info(f"No matches recorded for {month_name} {selected_year}.")
    st.stop()

# --- 3. Compute Monthly Stats ---
total_games = len(matches)

# Process win rates and stats across players
player_stats = {}
for m in matches:
    for p in m.get("match_players", []):
        name = p["player_name"]
        deck = p["deck_name"]
        is_winner = p["is_winner"]
        
        if name not in player_stats:
            player_stats[name] = {"wins": 0, "games": 0, "decks": {}}
        
        player_stats[name]["games"] += 1
        if is_winner:
            player_stats[name]["wins"] += 1
            
        player_stats[name]["decks"][deck] = player_stats[name]["decks"].get(deck, 0) + (1 if is_winner else 0)

# Identify Top Player & Most Played/Winning Decks
leaderboard = []
for name, stats in player_stats.items():
    win_rate = (stats["wins"] / stats["games"]) * 100 if stats["games"] > 0 else 0
    leaderboard.append({
        "Player": name,
        "Wins": stats["wins"],
        "Games": stats["games"],
        "WinRate": win_rate
    })

df_leaderboard = pd.DataFrame(leaderboard).sort_values(by=["Wins", "WinRate"], ascending=False)
top_player = df_leaderboard.iloc[0]["Player"] if not df_leaderboard.empty else "N/A"

# Display Dashboard Cards
m1, m2, m3 = st.columns(3)
m1.metric("Total Games Played", total_games)
m2.metric("Most Dominant Player", top_player)
m3.metric("Active Players", len(player_stats))

st.dataframe(df_leaderboard, use_container_width=True)

# --- 4. Generate Chat Share Message ---
st.subheader("💬 Chat Share Message")

# Construct Markdown/Plain Text for Discord/WhatsApp
chat_text = f"🏆 **{month_name.upper()} {selected_year} MTG RECAP** 🏆\n\n"
chat_text += f"📊 **Total Games Played:** {total_games}\n"
chat_text += f"👑 **Monthly MVP:** {top_player}\n\n"
chat_text += "🥇 **Leaderboard:**\n"

for i, row in df_leaderboard.iterrows():
    chat_text += f"• {row['Player']}: {row['Wins']}W / {row['Games']}G ({row['WinRate']:.1f}% Win Rate)\n"

chat_text += "\nGGs everyone! See you on the battlefield next month ⚔️"

# Show message preview in text area
st.text_area("Copy-paste preview", value=chat_text, height=200)

# Streamlit code snippet for easy copy button (requires streamlit >= 1.27)
st.code(chat_text, language="markdown")
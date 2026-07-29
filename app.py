import streamlit as st
import db
import requests
import pandas as pd

# Configure mobile-first page layout
st.set_page_config(
    page_title="EDH Tracker",
    page_icon="⚔️",
    layout="centered"
)

st.title("🛡️ Commander Tracker")

tab_log, tab_deck, tab_stats = st.tabs(["⚔️ Log Match", "➕ Add Deck", "📊 Analytics"])

# ==========================================
# TAB 1: LOG MATCH
# ==========================================
with tab_log:
    st.subheader("Match Details")
    
    players = db.fetch_players()
    
    if not players:
        st.warning("No players found in database. Please check your setup!")
    else:
        player_dict = {p['display_name']: p['player_id'] for p in players}
        player_names = list(player_dict.keys())

        # Match Overview Inputs
        col1, col2 = st.columns(2)
        with col1:
            total_turns = st.number_input("Total Turns", min_value=1, max_value=30, value=8)
        with col2:
            duration = st.number_input("Duration (mins)", min_value=5, max_value=300, value=45)

        win_condition = st.selectbox(
            "Win Condition",
            ["Combat Damage", "Infinite Combo", "Alternate Win-Con", "Commander Damage", "Scoop / Surrender"],
            index=None,
            placeholder="How did it end?"
        )

        st.divider()
        st.subheader("Participants")

        participants_input = []

        # Expandable Seat Layout for Mobile Cleanliness
        for seat in range(1, 5):
            with st.expander(f"👤 Seat {seat}", expanded=(seat == 1)):
                selected_player_name = st.selectbox(
                    f"Player", 
                    player_names,
                    index=None,
                    placeholder="Select player...",
                    key=f"seat_player_{seat}"
                )
                
                selected_player_id = None
                selected_deck_id = None
                
                # Dynamic Deck Fetching on Player Select
                if selected_player_name:
                    selected_player_id = player_dict[selected_player_name]
                    available_decks = db.fetch_player_decks(selected_player_id)
                    
                    if available_decks:
                        deck_dict = {d['deck_name']: d['deck_id'] for d in available_decks}
                        selected_deck_name = st.selectbox(
                            "Deck", 
                            list(deck_dict.keys()),
                            index=None,
                            placeholder="Select deck...",
                            key=f"seat_deck_{seat}"
                        )
                        if selected_deck_name:
                            selected_deck_id = deck_dict[selected_deck_name]
                    else:
                        st.caption("⚠️ No active decks found for this player.")
                else:
                    st.selectbox("Deck", [], disabled=True, index=None, placeholder="Waiting for player...", key=f"seat_deck_disabled_{seat}")

                col_mull, col_win = st.columns(2)
                with col_mull:
                    mulligans = st.number_input("Mulligans", 0, 7, 0, key=f"seat_mull_{seat}")
                with col_win:
                    is_winner = st.checkbox("Winner 🏆", key=f"seat_win_{seat}")

                participants_input.append({
                    "seat_position": seat,
                    "player_id": selected_player_id,
                    "deck_id": selected_deck_id,
                    "mulligan_count": mulligans,
                    "is_winner": is_winner
                })

        notes = st.text_input("Match Notes (Optional)", placeholder="e.g. Turn 6 Rhystic Study went unanswered")

        submit_match = st.button("Save Game Log", use_container_width=True, type="primary")

        if submit_match:
            missing_players = any(p['player_id'] is None for p in participants_input)
            missing_decks = any(p['deck_id'] is None for p in participants_input)
            winners_count = sum(1 for p in participants_input if p['is_winner'])

            if not win_condition:
                st.error("Please select a Win Condition.")
            elif missing_players:
                st.error("Please select a player for all 4 seats.")
            elif missing_decks:
                st.error("Please select a deck for all 4 seats.")
            elif winners_count != 1:
                st.warning("Please mark exactly ONE player as the winner.")
            else:
                game_data = {
                    "total_turns": total_turns,
                    "duration_minutes": duration,
                    "win_condition": win_condition,
                    "notes": notes
                }
                
                db.log_game_session(game_data, participants_input)
                st.toast("Game successfully logged!", icon="🎉")
                st.success("Game successfully logged!")

# ==========================================
# TAB 2: ADD DECK (With Moxfield Import)
# ==========================================
with tab_deck:
    st.subheader("➕ Add a New Deck")
    
    players = db.fetch_players()
    if not players:
        st.warning("No players found in database.")
    else:
        player_dict = {p['display_name']: p['player_id'] for p in players}
        player_names = list(player_dict.keys())

        owner_name = st.selectbox("Who owns this deck?", player_names, index=None, placeholder="Select a player...")
        
        st.divider()
        
        import_mox, import_manual = st.tabs(["🔗 Import from Moxfield", "✍️ Manual Entry"])
        
        # --- METHOD 1: MOXFIELD IMPORT ---
        with import_mox:
            mox_url = st.text_input("Moxfield Deck URL", placeholder="https://www.moxfield.com/decks/...")
            fetch_btn = st.button("Fetch & Save Deck", type="primary", use_container_width=True)
            
            if fetch_btn:
                if not owner_name:
                    st.error("Please select an owner first.")
                elif not mox_url:
                    st.error("Please paste a Moxfield URL.")
                else:
                    try:
                        deck_id = mox_url.strip().split('/')[-1]
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                            "Accept": "application/json, text/plain, */*",
                            "Accept-Language": "en-US,en;q=0.9",
                            "Referer": "https://www.moxfield.com/"
                        }
                        
                        response = requests.get(f"https://api.moxfield.com/v2/decks/all/{deck_id}", headers=headers)
                        
                        if response.status_code == 200:
                            data = response.json()
                            deck_name = data.get("name", "Untitled Moxfield Deck")
                            commanders_dict = data.get("commanders", {})
                            
                            if not commanders_dict:
                                st.error("No commander found in this Moxfield deck.")
                            else:
                                commander_ids = []
                                for comm_name, comm_data in commanders_dict.items():
                                    colors = "".join(comm_data.get("card", {}).get("colors", []))
                                    if not colors:
                                        colors = "C" # Colorless
                                        
                                    comm_id = db.get_or_create_commander(comm_name, colors)
                                    commander_ids.append(comm_id)
                                
                                owner_id = player_dict[owner_name]
                                new_deck_id = db.create_deck(owner_id, deck_name, commander_ids)
                                
                                st.success(f"Successfully imported **{deck_name}**!")
                                st.balloons()
                        else:
                            st.error(f"Failed to fetch deck from Moxfield (Error {response.status_code}). Check the URL.")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

        # --- METHOD 2: MANUAL ENTRY ---
        with import_manual:
            manual_deck_name = st.text_input("Deck Name", placeholder="e.g. Orzhov Aristocrats")
            manual_comm_name = st.text_input("Commander Name", placeholder="e.g. Teysa Karlov")
            manual_colors = st.text_input("Color Identity", placeholder="e.g. WB, UR, WUBRG")
            
            save_manual_btn = st.button("Save Manual Deck", use_container_width=True)
            
            if save_manual_btn:
                if not owner_name:
                    st.error("Please select an owner.")
                elif not manual_deck_name or not manual_comm_name:
                    st.error("Please fill in both the deck and commander names.")
                else:
                    owner_id = player_dict[owner_name]
                    comm_id = db.get_or_create_commander(manual_comm_name.strip(), manual_colors.strip().upper())
                    db.create_deck(owner_id, manual_deck_name.strip(), [comm_id])
                    st.success(f"Deck '{manual_deck_name}' created manually!")

# ==========================================
# TAB 3: ANALYTICS DASHBOARD
# ==========================================

def format_mana_symbols(color_str):
    """Converts a string like 'WUB' or 'Orzhov' into Scryfall SVG image URLs."""
    if not color_str:
        return ""
    
    # Standard MTG color code mapping
    color_map = {
        'W': 'W', 'U': 'U', 'B': 'B', 'R': 'R', 'G': 'G', 'C': 'C',
        'WHITE': 'W', 'BLUE': 'U', 'BLACK': 'B', 'RED': 'R', 'GREEN': 'G',
        'ORZHOV': 'WB', 'IZZET': 'UR', 'GOLGARI': 'BG', 'BOROS': 'WR', 'SIMIC': 'UG',
        'AZORIUS': 'WU', 'DIMIR': 'UB', 'RAKDOS': 'BR', 'GRUUL': 'RG', 'SELESNYA': 'GW'
    }
    
    # Parse input string into individual color characters
    cleaned_str = color_str.upper()
    
    # If the database stored guild names instead of raw letters, map them
    if cleaned_str in color_map and len(cleaned_str) > 1 and cleaned_str not in ['WUBRG']:
        cleaned_str = color_map[cleaned_str]

    # Build image URLs for each symbol (Scryfall CDN)
    symbols = []
    for char in cleaned_str:
        if char in ['W', 'U', 'B', 'R', 'G', 'C']:
            symbols.append(f"https://svgs.scryfall.io/card-symbols/{char}.svg")
            
    # Return the primary/first symbol URL for ImageColumn or list of URLs
    return symbols[0] if symbols else ""

with tab_stats:
    st.subheader("📊 Playgroup Operations & Metrics")
    
    raw_stats = db.get_player_stats()
    
    if not raw_stats:
        st.info("No game data available yet. Log a match to see the dashboard!")
    else:
        df = pd.DataFrame([dict(row) for row in raw_stats])
        df['win_rate'] = (df['wins'] / df['games_played']) * 100
        
        # High-Level Meta Metrics
        total_games_played = int(df['wins'].sum()) 
        overview_data = db.get_game_overview_stats()
        
        avg_turns = 0
        avg_duration = 0
        if overview_data:
            overview_df = pd.DataFrame([dict(row) for row in overview_data])
            avg_turns = round(overview_df['avg_turns'].mean(), 1)
            avg_duration = round(overview_df['avg_duration'].mean(), 0)

        # 2x2 Metric grid on mobile
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Matches", total_games_played)
            st.metric("Avg Turn Count", f"Turn {avg_turns}" if avg_turns else "N/A")
        with col2:
            st.metric("Active Players", len(df))
            st.metric("Avg Game Length", f"{int(avg_duration)} mins" if avg_duration else "N/A")
        
        st.divider()
        
        # 1. Player Leaderboard
        st.markdown("### 🏆 Player Leaderboard")
        st.dataframe(
            df[['display_name', 'games_played', 'wins', 'win_rate']],
            column_config={
                "display_name": st.column_config.TextColumn("Player Name"),
                "games_played": st.column_config.NumberColumn("Matches Played", format="%d"),
                "wins": st.column_config.NumberColumn("Wins", format="%d"),
                "win_rate": st.column_config.ProgressColumn(
                    "Win Rate (%)",
                    help="Target equity in a 4-player pod is 25%",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
            },
            hide_index=True,
            use_container_width=True
        )

        st.divider()
        
        # 2. Deck Performance (Full-Width Stacked)
        st.markdown("### 🃏 Deck Performance")
        raw_deck_stats = db.get_deck_stats()
        if raw_deck_stats:
            df_decks = pd.DataFrame([dict(row) for row in raw_deck_stats])
            df_decks['win_rate'] = (df_decks['wins'] / df_decks['games_played']) * 100
            
            st.dataframe(
                df_decks[['deck_name', 'owner_name', 'games_played', 'wins', 'win_rate']],
                column_config={
                    "deck_name": st.column_config.TextColumn("Deck Name"),
                    "owner_name": st.column_config.TextColumn("Pilot/Owner"),
                    "games_played": st.column_config.NumberColumn("Played", format="%d"),
                    "wins": st.column_config.NumberColumn("Wins", format="%d"),
                    "win_rate": st.column_config.ProgressColumn(
                        "Win Rate (%)",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                    ),
                },
                hide_index=True,
                use_container_width=True
            )

        st.divider()

        # 3. Color Identity Performance (With MTG Mana Symbols)
        st.markdown("### 🎨 Color Identity Win Rates")
        color_stats = db.get_color_identity_stats()
        if color_stats:
            df_colors = pd.DataFrame([dict(row) for row in color_stats])
            df_colors['win_rate'] = (df_colors['wins'] / df_colors['games_played']) * 100
            
            # Map color codes to Scryfall SVG URIs
            df_colors['symbol_url'] = df_colors['color_identity'].apply(format_mana_symbols)
            
            st.dataframe(
                df_colors[['symbol_url', 'color_identity', 'games_played', 'wins', 'win_rate']],
                column_config={
                    "symbol_url": st.column_config.ImageColumn(
                        "Symbol",
                        help="Official MTG Mana Symbol from Scryfall",
                        width="small"
                    ),
                    "color_identity": st.column_config.TextColumn("Color Identity"),
                    "games_played": st.column_config.NumberColumn("Played", format="%d"),
                    "wins": st.column_config.NumberColumn("Wins", format="%d"),
                    "win_rate": st.column_config.ProgressColumn(
                        "Win Rate (%)",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                    ),
                },
                hide_index=True,
                use_container_width=True
            )
import streamlit as st
import db
import requests
import pandas as pd

# Page setup
st.set_page_config(
    page_title="EDH Tracker",
    page_icon="⚔️",
    layout="centered"
)

st.title("🛡️ Commander Tracker")

# ------------------------------------------------------------------------------
# 1. PIN AUTHENTICATION (SIDEBAR)
# ------------------------------------------------------------------------------
# Retrieve PINs from Secrets (with fallback defaults)
ADMIN_PIN = st.secrets.get("ADMIN_PIN", "1234")
LOGGER_PIN = st.secrets.get("LOGGER_PIN", "5678")

# Initialize session state for user role
if "user_role" not in st.session_state:
    st.session_state.user_role = "Viewer"  # Options: "Admin", "Logger", "Viewer"

with st.sidebar:
    st.header("🔒 Access Control")
    
    if st.session_state.user_role == "Viewer":
        entered_pin = st.text_input("Enter PIN to unlock features", type="password")
        if st.button("Unlock"):
            if entered_pin == ADMIN_PIN:
                st.session_state.user_role = "Admin"
                st.toast("Unlocked Admin Access!", icon="🔑")
                st.rerun()
            elif entered_pin == LOGGER_PIN:
                st.session_state.user_role = "Logger"
                st.toast("Unlocked Logger Access!", icon="⚔️")
                st.rerun()
            else:
                st.error("Invalid PIN")
    else:
        st.success(f"Current Role: **{st.session_state.user_role}**")
        if st.button("Lock / Log Out"):
            st.session_state.user_role = "Viewer"
            st.rerun()

# ------------------------------------------------------------------------------
# 2. DYNAMIC TAB RENDERING BASED ON ROLE
# ------------------------------------------------------------------------------
role = st.session_state.user_role

# Build tabs based on authorization level
if role == "Admin":
    tab_log, tab_deck, tab_players, tab_stats = st.tabs([
        "⚔️ Log Match", "➕ Add Deck", "👥 Manage Players", "📊 Analytics"
    ])
elif role == "Logger":
    tab_log, tab_deck, tab_stats = st.tabs([
        "⚔️ Log Match", "➕ Add Deck", "📊 Analytics"
    ])
    tab_players = None
else:
    # Viewer Mode: Only Analytics is active
    st.info("ℹ️ You are in Read-Only mode. Enter a PIN in the sidebar to log games or add decks.")
    tab_stats, = st.tabs(["📊 Analytics"])
    tab_log, tab_deck, tab_players = None, None, None

# ------------------------------------------------------------------------------
# TAB: LOG MATCH (ADMIN & LOGGER ONLY)
# ------------------------------------------------------------------------------
if tab_log:
    with tab_log:
        st.subheader("Match Details")
        players = db.fetch_players()
        
        if not players:
            st.warning("No players found in database!")
        else:
            player_dict = {p['display_name']: p['player_id'] for p in players}
            player_names = list(player_dict.keys())

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

            for seat in range(1, 5):
                with st.expander(f"👤 Seat {seat}", expanded=(seat == 1)):
                    selected_player_name = st.selectbox(
                        "Player", 
                        player_names,
                        index=None,
                        placeholder="Select player...",
                        key=f"seat_player_{seat}"
                    )
                    
                    selected_player_id = None
                    selected_deck_id = None
                    
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

# ------------------------------------------------------------------------------
# TAB: ADD DECK (ADMIN & LOGGER ONLY)
# ------------------------------------------------------------------------------
if tab_deck:
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
                                            colors = "C"
                                        comm_id = db.get_or_create_commander(comm_name, colors)
                                        commander_ids.append(comm_id)
                                    
                                    owner_id = player_dict[owner_name]
                                    db.create_deck(owner_id, deck_name, commander_ids)
                                    st.success(f"Successfully imported **{deck_name}**!")
                                    st.balloons()
                            else:
                                st.error(f"Failed to fetch deck from Moxfield (Error {response.status_code}).")
                        except Exception as e:
                            st.error(f"An error occurred: {e}")

            with import_manual:
                manual_deck_name = st.text_input("Deck Name", placeholder="e.g. Orzhov Aristocrats")
                manual_comm_name = st.text_input("Commander Name", placeholder="e.g. Teysa Karlov")
                manual_colors = st.text_input("Color Identity", placeholder="e.g. WB, UR, WUBRG")
                
                save_manual_btn = st.button("Save Manual Deck", use_container_width=True)
                
                if save_manual_btn:
                    if not owner_name or not manual_deck_name or not manual_comm_name:
                        st.error("Please fill in all required fields.")
                    else:
                        owner_id = player_dict[owner_name]
                        comm_id = db.get_or_create_commander(manual_comm_name.strip(), manual_colors.strip().upper())
                        db.create_deck(owner_id, manual_deck_name.strip(), [comm_id])
                        st.success(f"Deck '{manual_deck_name}' created manually!")

# ------------------------------------------------------------------------------
# TAB: MANAGE PLAYERS & MATCHES (ADMIN ONLY - PIN A)
# ------------------------------------------------------------------------------
if tab_players:
    with tab_players:
        st.subheader("🛠️ Admin Controls")
        
        # --- EXPANDER 1: ADD / REMOVE PLAYERS ---
        with st.expander("👤 Manage Players (Add / Delete)", expanded=False):
            col_add, col_del = st.columns(2)
            
            with col_add:
                st.markdown("#### ➕ Add Player")
                
                # Initialize session state for text input if not present
                if "new_player_input" not in st.session_state:
                    st.session_state.new_player_input = ""

                new_player_name = st.text_input(
                    "Player Name", 
                    placeholder="e.g. John Doe", 
                    key="new_player_input"
                )

                if st.button("Add Player", type="primary", key="btn_add_player"):
                    clean_name = new_player_name.strip()
                    
                    if not clean_name:
                        st.error("Please enter a player name first.")
                    else:
                        try:
                            # Attempt insertion into Supabase
                            db.add_player(clean_name)
                            
                            # SUCCESS: Clear the text box state, show toast & alert, then rerun
                            st.session_state.new_player_input = ""
                            st.toast(f"Added '{clean_name}' successfully!", icon="✅")
                            st.success(f"Player **{clean_name}** was added to the database!")
                            st.rerun()
                            
                        except Exception as e:
                            # FAILURE: Do NOT clear session state, typed text stays in the box
                            st.error(f"Failed to add player '{clean_name}'. It might already exist or a database error occurred.")

            with col_del:
                st.markdown("#### 🗑️ Remove Player")
                players = db.fetch_players()
                if players:
                    player_dict = {p['display_name']: p['player_id'] for p in players}
                    remove_name = st.selectbox("Select Player to Remove", list(player_dict.keys()), index=None, key="admin_remove_player_select")
                    
                    if st.button("Delete Player", type="secondary", key="btn_del_player"):
                        if remove_name:
                            db.delete_player(player_dict[remove_name])
                            st.toast(f"Removed '{remove_name}'", icon="🗑️")
                            st.success(f"Player '{remove_name}' deleted!")
                            st.rerun()
                        else:
                            st.error("Please select a player to remove.")

        # --- EXPANDER 2: LIST PLAYERS & REGISTERED DECKS ---
        with st.expander("🃏 View Registered Players & Decks", expanded=False):
            all_decks = db.fetch_all_decks_with_owners()
            if all_decks:
                df_all_decks = pd.DataFrame([dict(row) for row in all_decks])
                st.dataframe(
                    df_all_decks[['owner_name', 'deck_name', 'commander_names']],
                    column_config={
                        "owner_name": st.column_config.TextColumn("Pilot / Owner"),
                        "deck_name": st.column_config.TextColumn("Deck Name"),
                        "commander_names": st.column_config.TextColumn("Commander(s)"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No decks registered in the database yet.")

        # --- EXPANDER 3: DELETE MATCH LOGS ---
        with st.expander("🗑️ Match Management (Delete Matches)", expanded=False):
            st.markdown("Select a game session to delete from database logs:")
            recent_games = db.fetch_recent_games(limit=20)
            
            if recent_games:
                # Format options cleanly for dropdown
                game_options = {}
                for g in recent_games:
                    label = f"Game #{g['game_id']} | Turns: {g['total_turns']} | Win: {g['win_condition']} ({g['participants']})"
                    game_options[label] = g['game_id']
                
                selected_game_label = st.selectbox("Select Match to Delete", list(game_options.keys()), index=None)
                
                if selected_game_label:
                    game_to_delete_id = game_options[selected_game_label]
                    
                    # Safety check before deletion
                    confirm_delete = st.checkbox(f"I understand this will permanently delete Game #{game_to_delete_id}", key="confirm_game_del")
                    
                    if st.button("⚠️ Delete Match Session", type="primary", key="btn_del_game"):
                        if confirm_delete:
                            db.delete_game_session(game_to_delete_id)
                            st.toast(f"Game #{game_to_delete_id} deleted!", icon="🗑️")
                            st.success(f"Successfully deleted Game #{game_to_delete_id}!")
                            st.rerun()
                        else:
                            st.error("Please check the confirmation box first.")
            else:
                st.info("No logged matches found.")

# ------------------------------------------------------------------------------
# TAB: ANALYTICS (PUBLIC / ALL ROLES)
# ------------------------------------------------------------------------------
with tab_stats:
    st.subheader("📊 Playgroup Operations & Metrics")
    
    raw_stats = db.get_player_stats()
    
    if not raw_stats:
        st.info("No game data available yet. Log a match to see the dashboard!")
    else:
        df = pd.DataFrame([dict(row) for row in raw_stats])
        df['win_rate'] = (df['wins'] / df['games_played']) * 100
        
        total_games_played = int(df['wins'].sum()) 
        overview_data = db.get_game_overview_stats()
        
        avg_turns = 0
        avg_duration = 0
        if overview_data:
            overview_df = pd.DataFrame([dict(row) for row in overview_data])
            avg_turns = round(overview_df['avg_turns'].mean(), 1)
            avg_duration = round(overview_df['avg_duration'].mean(), 0)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Matches", total_games_played)
            st.metric("Avg Turn Count", f"Turn {avg_turns}" if avg_turns else "N/A")
        with col2:
            st.metric("Active Players", len(df))
            st.metric("Avg Game Length", f"{int(avg_duration)} mins" if avg_duration else "N/A")
        
        st.divider()
        
        # Player Leaderboard
        st.markdown("### 🏆 Player Leaderboard")
        st.dataframe(
            df[['display_name', 'games_played', 'wins', 'win_rate']],
            column_config={
                "display_name": st.column_config.TextColumn("Player Name"),
                "games_played": st.column_config.NumberColumn("Matches Played", format="%d"),
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
        
        # Deck Leaderboard
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

        # Color Identity Performance
        st.markdown("### 🎨 Color Identity Win Rates")
        color_stats = db.get_color_identity_stats()
        if color_stats:
            df_colors = pd.DataFrame([dict(row) for row in color_stats])
            df_colors['win_rate'] = (df_colors['wins'] / df_colors['games_played']) * 100
            
            symbol_map = {
                'W': '☀️', 'U': '💧', 'B': '💀', 'R': '🔥', 'G': '🌳', 'C': '💎',
                'ORZHOV': '☀️💀', 'IZZET': '💧🔥', 'GOLGARI': '💀🌳', 'BOROS': '☀️🔥', 'SIMIC': '💧🌳',
                'AZORIUS': '☀️💧', 'DIMIR': '💧💀', 'RAKDOS': '💀🔥', 'GRUUL': '🔥🌳', 'SELESNYA': '☀️🌳',
                'ESPER': '☀️💧💀', 'BANT': '☀️💧🌳', 'GRIXIS': '💧💀🔥', 'JUND': '💀🔥🌳', 'NAYA': '☀️🔥🌳',
                'ABZAN': '☀️💀🌳', 'JESKAI': '☀️💧🔥', 'SULTAI': '💧💀🔥', 'MARDU': '☀️💀🔥'
            }
            
            def get_symbol_text(c):
                cleaned = str(c).upper().strip()
                return f"{symbol_map.get(cleaned, cleaned)} {cleaned}"
            
            df_colors['identity_display'] = df_colors['color_identity'].apply(get_symbol_text)
            
            st.dataframe(
                df_colors[['identity_display', 'games_played', 'wins', 'win_rate']],
                column_config={
                    "identity_display": st.column_config.TextColumn("Color Identity"),
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
import streamlit as st
import requests
import pandas as pd
import db

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
ADMIN_PIN = st.secrets.get("ADMIN_PIN", "1234")
LOGGER_PIN = st.secrets.get("LOGGER_PIN", "5678")

if "user_role" not in st.session_state:
    st.session_state.user_role = "Viewer"

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

if role == "Admin":
    tab_log, tab_deck, tab_admin, tab_stats = st.tabs([
        "⚔️ Log Match", "➕ Add Deck", "🛠️ Admin Controls", "📊 Analytics"
    ])
elif role == "Logger":
    tab_log, tab_deck, tab_stats = st.tabs([
        "⚔️ Log Match", "➕ Add Deck", "📊 Analytics"
    ])
    tab_admin = None
else:
    st.info("ℹ️ You are in Read-Only mode. Enter a PIN in the sidebar to log games or add decks.")
    tab_stats, = st.tabs(["📊 Analytics"])
    tab_log, tab_deck, tab_admin = None, None, None

# ------------------------------------------------------------------------------
# TAB 1: LOG MATCH (ADMIN & LOGGER ONLY)
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
# TAB 2: ADD DECK (ADMIN & LOGGER ONLY)
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
                                    
                                    # Iterate through all commanders (handles single or partner pairs)
                                    for comm_name, comm_data in commanders_dict.items():
                                        # Get raw colors list (e.g. ['W', 'B'])
                                        raw_colors = comm_data.get("card", {}).get("colors", [])
                                        color_str = "".join(raw_colors) if raw_colors else "C"
                                        
                                        # Save individual commander to DB
                                        comm_id = db.get_or_create_commander(comm_name, color_str)
                                        commander_ids.append(comm_id)
                                    
                                    # Save deck with list of commander IDs
                                    db.create_deck(owner_id, deck_name, commander_ids)

                            else:
                                st.error(f"Failed to fetch deck from Moxfield (Error {response.status_code}).")
                        except Exception as e:
                            st.error(f"An error occurred: {e}")

            with import_manual:
                manual_deck_name = st.text_input("Deck Name", placeholder="e.g. Tymna / Kraum Opus")
                
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    comm1_name = st.text_input("Primary Commander Name", placeholder="e.g. Tymna the Weaver")
                    comm1_colors = st.text_input("Commander 1 Colors", placeholder="e.g. WB")
                with col_c2:
                    comm2_name = st.text_input("Partner Commander (Optional)", placeholder="e.g. Kraum, Ludevic's Opus")
                    comm2_colors = st.text_input("Commander 2 Colors", placeholder="e.g. UR")

                save_manual_btn = st.button("Save Manual Deck", use_container_width=True)

                if save_manual_btn:
                    if not owner_name or not manual_deck_name or not comm1_name:
                        st.error("Please fill in the Owner, Deck Name, and Primary Commander.")
                    else:
                        owner_id = player_dict[owner_name]
                        commander_ids = []
                        
                        # Primary Commander
                        comm1_id = db.get_or_create_commander(comm1_name.strip(), comm1_colors.strip().upper())
                        commander_ids.append(comm1_id)
                        
                        # Partner Commander (if provided)
                        if comm2_name.strip():
                            comm2_id = db.get_or_create_commander(comm2_name.strip(), comm2_colors.strip().upper())
                            commander_ids.append(comm2_id)

                        db.create_deck(owner_id, manual_deck_name.strip(), commander_ids)
                        st.success(f"Deck '{manual_deck_name}' created with {len(commander_ids)} commander(s)!")

# ------------------------------------------------------------------------------
# TAB 3: ADMIN CONTROLS (ADMIN ONLY - PIN A)
# ------------------------------------------------------------------------------
if tab_admin:
    with tab_admin:
        st.subheader("🛠️ Admin Controls")
        
        # Display persistent success banner if set on previous rerun
        if "player_add_success_name" in st.session_state:
            added_name = st.session_state.pop("player_add_success_name")
            st.success(f"🎉 Player **{added_name}** was added successfully!")
            st.toast(f"Added '{added_name}'!", icon="👤")

        # --- EXPANDER 1: ADD / REMOVE PLAYERS ---
        with st.expander("👤 Manage Players (Add / Delete)", expanded=False):
            col_add, col_del = st.columns(2)
            
            with col_add:
                st.markdown("#### ➕ Add Player")
                new_player_name = st.text_input(
                    "Player Name", 
                    placeholder="e.g. John Doe", 
                    key="input_add_player_name"
                )

                if st.button("Add Player", type="primary", key="btn_add_player"):
                    clean_name = new_player_name.strip()
                    if not clean_name:
                        st.error("Please enter a player name first.")
                    else:
                        existing_players = [p['display_name'].lower() for p in db.fetch_players()]
                        if clean_name.lower() in existing_players:
                            st.error(f"Player '{clean_name}' already exists in the database!")
                        else:
                            try:
                                db.add_player(clean_name)
                                st.session_state["player_add_success_name"] = clean_name
                                if "input_add_player_name" in st.session_state:
                                    del st.session_state["input_add_player_name"]
                                st.rerun()
                            except Exception as e:
                                st.error(f"Database error: {e}")

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

        # --- EXPANDER 2: UPGRADE / LINK MANUAL DECK TO MOXFIELD ---
        with st.expander("🔗 Upgrade Manual Deck to Moxfield", expanded=False):
            st.markdown("Select a player and deck to sync or re-import from a Moxfield link:")
            players = db.fetch_players()
            if players:
                player_dict = {p['display_name']: p['player_id'] for p in players}
                selected_owner = st.selectbox("Select Deck Owner", list(player_dict.keys()), index=None, key="select_owner_upgrade")
                
                if selected_owner:
                    owner_id = player_dict[selected_owner]
                    user_decks = db.fetch_player_decks(owner_id)
                    
                    if user_decks:
                        deck_options = {d['deck_name']: d['deck_id'] for d in user_decks}
                        selected_deck_name = st.selectbox("Select Deck to Upgrade", list(deck_options.keys()), index=None, key="select_deck_upgrade")
                        
                        if selected_deck_name:
                            selected_deck_id = deck_options[selected_deck_name]
                            mox_url_upgrade = st.text_input("Moxfield Deck URL", placeholder="https://www.moxfield.com/decks/...", key="input_mox_upgrade")
                            
                            if st.button("Sync Deck with Moxfield", type="primary", key="btn_sync_mox"):
                                if not mox_url_upgrade:
                                    st.error("Please paste a valid Moxfield URL.")
                                else:
                                    try:
                                        deck_id_hash = mox_url_upgrade.strip().split('/')[-1]
                                        headers = {
                                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                                            "Accept": "application/json, text/plain, */*",
                                            "Accept-Language": "en-US,en;q=0.9",
                                            "Referer": "https://www.moxfield.com/"
                                        }
                                        response = requests.get(f"https://api.moxfield.com/v2/decks/all/{deck_id_hash}", headers=headers)
                                        
                                        if response.status_code == 200:
                                            data = response.json()
                                            mox_deck_name = data.get("name", selected_deck_name)
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
                                                
                                                db.update_deck_from_moxfield(selected_deck_id, mox_deck_name, commander_ids)
                                                st.toast(f"Updated '{mox_deck_name}'!", icon="🎉")
                                                st.success(f"Successfully linked **{selected_deck_name}** to Moxfield!")
                                                st.rerun()
                                        else:
                                            st.error(f"Failed to fetch deck from Moxfield (Error {response.status_code}).")
                                    except Exception as e:
                                        st.error(f"An error occurred: {e}")
                    else:
                        st.info("This player has no registered decks.")

        # --- EXPANDER 3: LIST PLAYERS & REGISTERED DECKS ---
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

        # --- EXPANDER 4: DELETE MATCH LOGS ---
        with st.expander("🗑️ Match Management (Delete Matches)", expanded=False):
            st.markdown("Select a game session to delete from database logs:")
            recent_games = db.fetch_recent_games(limit=20)
            
            if recent_games:
                game_options = {}
                for g in recent_games:
                    label = f"Game #{g['game_id']} | Turns: {g['total_turns']} | Win: {g['win_condition']} ({g['participants']})"
                    game_options[label] = g['game_id']
                
                selected_game_label = st.selectbox("Select Match to Delete", list(game_options.keys()), index=None)
                
                if selected_game_label:
                    game_to_delete_id = game_options[selected_game_label]
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
# TAB 4: ANALYTICS (PUBLIC / ALL ROLES)
# ------------------------------------------------------------------------------
with tab_stats:
    st.subheader("📊 Playgroup Operations & Metrics")
    
    # 1. TOP METRICS & OVERVIEW
    raw_stats = db.get_player_stats()
    all_decks = db.get_all_deck_performance_stats()
    
    total_games_played = sum([dict(r)['wins'] for r in raw_stats]) if raw_stats else 0
    total_registered_decks = len(all_decks) if all_decks else 0
    
    overview_data = db.get_game_overview_stats()
    avg_turns = 0
    avg_duration = 0
    if overview_data:
        overview_df = pd.DataFrame([dict(row) for row in overview_data])
        avg_turns = round(overview_df['avg_turns'].mean(), 1)
        avg_duration = round(overview_df['avg_duration'].mean(), 0)

    # 4-Metric Grid
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Matches Logged", total_games_played)
        st.metric("Avg Turn Count", f"Turn {avg_turns}" if avg_turns else "N/A")
    with col2:
        st.metric("Total Decks Registered", total_registered_decks)
        st.metric("Avg Game Length", f"{int(avg_duration)} mins" if avg_duration else "N/A")
    
    st.divider()

    # 2. DECK OWNERSHIP & COLOR DISTRIBUTION (NEW)
    st.markdown("### 🧮 Playgroup Arsenal & Deck Ownership")
    col_ownership, col_colors = st.columns(2)

    # Decks Owned per Player
    with col_ownership:
        st.markdown("#### 🃏 Decks Owned per Player")
        ownership_stats = db.get_deck_ownership_stats()
        if ownership_stats:
            df_owners = pd.DataFrame([dict(row) for row in ownership_stats])
            
            st.dataframe(
                df_owners[['player_name', 'deck_count']],
                column_config={
                    "player_name": st.column_config.TextColumn("Player"),
                    "deck_count": st.column_config.NumberColumn("Decks Owned", format="%d 🎴"),
                },
                hide_index=True,
                use_container_width=True
            )

    # Color Distribution across all decks
    with col_colors:
        st.markdown("#### 🎨 Color Presence in Arsenal")
        color_presence = db.get_color_presence_stats()
        if color_presence:
            # Aggregate individual WUBRG character presence across all commanders
            color_counts = {'W': 0, 'U': 0, 'B': 0, 'R': 0, 'G': 0, 'C': 0}
            for row in color_presence:
                identity = str(row['color_identity']).upper()
                count = row['deck_count']
                for char in identity:
                    if char in color_counts:
                        color_counts[char] += count

            symbol_map = {'W': '☀️ White', 'U': '💧 Blue', 'B': '💀 Black', 'R': '🔥 Red', 'G': '🌳 Green', 'C': '💎 Colorless'}
            df_color_dist = pd.DataFrame([
                {"color": symbol_map[k], "decks": v} 
                for k, v in color_counts.items() if v > 0
            ]).sort_values(by="decks", ascending=False)

            st.dataframe(
                df_color_dist,
                column_config={
                    "color": st.column_config.TextColumn("Color"),
                    "decks": st.column_config.NumberColumn("Decks Featured In", format="%d"),
                },
                hide_index=True,
                use_container_width=True
            )

    st.divider()

    # 3. PLAYER LEADERBOARD
    st.markdown("### 🏆 Player Leaderboard")
    if raw_stats:
        df_players = pd.DataFrame([dict(row) for row in raw_stats])
        df_players['win_rate'] = (df_players['wins'] / df_players['games_played']) * 100
        
        st.dataframe(
            df_players[['display_name', 'games_played', 'wins', 'win_rate']],
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

    # 4. ALL DECKS PERFORMANCE TABLE (WITH ZERO/NULL SAFETY)
    st.markdown("### 🃏 Complete Deck Performance")
    if all_decks:
        df_decks = pd.DataFrame([dict(row) for row in all_decks])
        
        # Calculate win rate, safely treating 0 games as 0.0% win rate
        df_decks['win_rate'] = df_decks.apply(
            lambda r: (r['wins'] / r['games_played'] * 100) if r['games_played'] > 0 else 0.0, 
            axis=1
        )
        
        st.dataframe(
            df_decks[['deck_name', 'owner_name', 'games_played', 'wins', 'win_rate']],
            column_config={
                "deck_name": st.column_config.TextColumn("Deck Name"),
                "owner_name": st.column_config.TextColumn("Pilot / Owner"),
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

    # 5. COLOR IDENTITY WIN RATES
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
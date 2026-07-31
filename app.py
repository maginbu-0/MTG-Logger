import streamlit as st
import requests
import pandas as pd
import db
from zoneinfo import ZoneInfo
import datetime

# Helper to get local AST current date
def get_ast_today():
    return datetime.datetime.now(ZoneInfo("America/Santo_Domingo")).date()

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
    tab_log, tab_deck, tab_admin_decks, tab_admin_matches, tab_recap, tab_stats = st.tabs([
        "⚔️ Log Match", "➕ Add Deck", "🛠️ Deck & Player Admin", "✏️ Match Admin", "📋 Daily Recap", "📊 Analytics"
    ])
elif role == "Logger":
    tab_log, tab_deck, tab_recap, tab_stats = st.tabs([
        "⚔️ Log Match", "➕ Add Deck", "📋 Daily Recap", "📊 Analytics"
    ])
    tab_admin_decks, tab_admin_matches = None, None
else:
    st.info("ℹ️ You are in Read-Only mode. Enter a PIN in the sidebar to log games or add decks.")
    tab_recap, tab_stats = st.tabs(["📋 Daily Recap", "📊 Analytics"])
    tab_log, tab_deck, tab_admin_decks, tab_admin_matches = None, None, None, None

# ------------------------------------------------------------------------------
# TAB 1: LOG MATCH (ADMIN & LOGGER ONLY)
# ------------------------------------------------------------------------------
if tab_log:
    with tab_log:
        st.subheader("⚔️ Live Match Companion & Logger")

        active_session_key = st.session_state.get("user_role", "Logger")

        if "session_loaded_from_db" not in st.session_state:
            db_session = db.fetch_live_session(active_session_key)
            st.session_state.timer_running = db_session["timer_running"]
            st.session_state.timer_start_time = db_session["timer_start_time"]
            st.session_state.timer_elapsed_seconds = db_session["timer_elapsed_seconds"]
            st.session_state.live_turn_count = db_session["live_turn_count"]
            st.session_state.session_loaded_from_db = True

        def sync_companion_to_db():
            db.update_live_session(
                active_session_key,
                st.session_state.timer_running,
                st.session_state.timer_start_time,
                st.session_state.timer_elapsed_seconds,
                st.session_state.live_turn_count
            )

        import time

        # --- STREAMLIT FRAGMENT: LIVE GAME COMPANION ---
        @st.fragment
        def render_live_companion_fragment():
            current_elapsed = st.session_state.timer_elapsed_seconds
            if st.session_state.timer_running and st.session_state.timer_start_time is not None:
                current_elapsed += int(time.time() - st.session_state.timer_start_time)

            with st.expander(f"⏱️ Live Game Companion ({active_session_key} Pod)", expanded=True):
                col_timer, col_turns = st.columns(2)
                
                with col_timer:
                    st.markdown("#### ⏳ Match Timer")
                    mins, secs = divmod(current_elapsed, 60)
                    hrs, mins = divmod(mins, 60)
                    time_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"
                    
                    st.markdown(f"<h2 style='text-align: center; margin: 0; color: #ff4b4b;'>{time_str}</h2>", unsafe_allow_html=True)
                    
                    t_col1, t_col2 = st.columns(2)
                    with t_col1:
                        if not st.session_state.timer_running:
                            if st.button("▶️ Start / Resume", use_container_width=True, key="btn_timer_start"):
                                st.session_state.timer_running = True
                                st.session_state.timer_start_time = time.time()
                                sync_companion_to_db()
                                st.rerun(scope="fragment")
                        else:
                            if st.button("⏸️ Pause", use_container_width=True, key="btn_timer_pause"):
                                st.session_state.timer_running = False
                                st.session_state.timer_elapsed_seconds = current_elapsed
                                st.session_state.timer_start_time = None
                                sync_companion_to_db()
                                st.rerun(scope="fragment")
                    
                    with t_col2:
                        if st.button("🔄 Reset Timer", use_container_width=True, key="btn_timer_reset"):
                            st.session_state.timer_running = False
                            st.session_state.timer_start_time = None
                            st.session_state.timer_elapsed_seconds = 0
                            st.session_state.live_turn_count = 1
                            sync_companion_to_db()
                            st.rerun(scope="fragment")

                with col_turns:
                    st.markdown("#### 🔄 Turn Counter")
                    st.markdown(f"<h2 style='text-align: center; margin: 0;'>Turn {st.session_state.live_turn_count}</h2>", unsafe_allow_html=True)
                    
                    turn_col1, turn_col2 = st.columns(2)
                    with turn_col1:
                        if st.button("➖ Turn", use_container_width=True, key="btn_sub_turn"):
                            if st.session_state.live_turn_count > 1:
                                st.session_state.live_turn_count -= 1
                                sync_companion_to_db()
                                st.rerun(scope="fragment")
                    with turn_col2:
                        if st.button("➕ Next Turn", type="primary", use_container_width=True, key="btn_add_turn"):
                            st.session_state.live_turn_count += 1
                            sync_companion_to_db()
                            st.rerun(scope="fragment")

                st.divider()
                
                if st.button("🏁 End Match & Auto-Fill Form", type="primary", use_container_width=True, key="btn_end_match"):
                    if st.session_state.timer_running and st.session_state.timer_start_time is not None:
                        st.session_state.timer_elapsed_seconds += int(time.time() - st.session_state.timer_start_time)
                        st.session_state.timer_running = False
                        st.session_state.timer_start_time = None
                    
                    final_minutes = max(1, round(st.session_state.timer_elapsed_seconds / 60))
                    
                    st.session_state["input_total_turns"] = int(st.session_state.live_turn_count)
                    st.session_state["input_duration"] = int(final_minutes)
                    
                    sync_companion_to_db()
                    st.toast(f"Pushed {final_minutes} mins and Turn {st.session_state.live_turn_count} to form!", icon="⏱️")
                    st.rerun()

        # Render companion fragment
        render_live_companion_fragment()

        st.subheader("Match Details")

        if "input_total_turns" not in st.session_state:
            st.session_state["input_total_turns"] = 8
        if "input_duration" not in st.session_state:
            st.session_state["input_duration"] = 45

        if "form_version" not in st.session_state:
            st.session_state.form_version = 0

        form_v = st.session_state.form_version

        players = db.fetch_players()
        
        if not players:
            st.warning("No players found in database!")
        else:
            player_dict = {p['display_name']: p['player_id'] for p in players}
            player_names = list(player_dict.keys())

            all_global_decks = db.fetch_all_decks_with_owners() if hasattr(db, 'fetch_all_decks_with_owners') else []

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_turns = st.number_input("Total Turns", min_value=1, max_value=50, key="input_total_turns")
            with col2:
                duration = st.number_input("Duration (mins)", min_value=1, max_value=500, key="input_duration")
            with col3:
                bracket_level = st.selectbox("Game Bracket", options=[1, 2, 3, 4, 5], index=2, key="input_bracket")
            with col4:
                game_medium = st.selectbox("Platform / Medium", options=["In Person 🃏", "Convoke 💻", "SpellTable 📹"], index=0, key="input_medium")

            win_condition = st.selectbox(
                "Win Condition",
                ["Combat Damage", "Infinite Combo", "Alternate Win-Con", "Commander Damage", "Scoop / Surrender"],
                index=None,
                placeholder="How did it end?",
                key=f"input_win_condition_{form_v}"
            )

            st.divider()
            
            col_p1, col_p2 = st.columns([1, 2])
            with col_p1:
                num_players = st.selectbox("Number of Players", options=[3, 4], index=1, key=f"input_num_players_{form_v}")

            # --- STREAMLIT FRAGMENT: SEAT SELECTORS ---
            @st.fragment
            def render_participants_fragment():
                st.subheader("Participants")
                participants_input = []

                for seat in range(1, num_players + 1):
                    with st.expander(f"👤 Seat {seat}", expanded=(seat == 1)):
                        selected_player_name = st.selectbox("Player", player_names, index=None, placeholder="Select player...", key=f"seat_player_{seat}_{form_v}")
                        is_borrowing = st.checkbox("🎁 Borrowing a deck from someone else?", key=f"seat_borrow_{seat}_{form_v}")
                        
                        selected_player_id = None
                        selected_deck_id = None
                        
                        if selected_player_name:
                            selected_player_id = player_dict[selected_player_name]
                            if is_borrowing:
                                if all_global_decks:
                                    global_deck_dict = {f"{d['deck_name']} (Owner: {d['owner_name']})": d['deck_id'] for d in all_global_decks}
                                    selected_deck_label = st.selectbox("Select Borrowed Deck", list(global_deck_dict.keys()), index=None, placeholder="Select borrowed deck...", key=f"seat_deck_borrowed_{seat}_{form_v}")
                                    if selected_deck_label:
                                        selected_deck_id = global_deck_dict[selected_deck_label]
                                else:
                                    st.caption("⚠️ No global decks found.")
                            else:
                                available_decks = db.fetch_player_decks(selected_player_id)
                                if available_decks:
                                    deck_dict = {f"{d['deck_name']} (⚡ Bracket {d.get('bracket', 3)})": d['deck_id'] for d in available_decks}
                                    selected_deck_name = st.selectbox("Deck", list(deck_dict.keys()), index=None, placeholder="Select deck...", key=f"seat_deck_{seat}_{form_v}")
                                    if selected_deck_name:
                                        selected_deck_id = deck_dict[selected_deck_name]
                                else:
                                    st.caption("⚠️ No active decks found for this player.")
                        else:
                            st.selectbox("Deck", [], disabled=True, index=None, placeholder="Waiting for player...", key=f"seat_deck_disabled_{seat}_{form_v}")

                        col_mull, col_win = st.columns(2)
                        with col_mull:
                            mulligans = st.number_input("Mulligans", 0, 7, 0, key=f"seat_mull_{seat}_{form_v}")
                        with col_win:
                            is_winner = st.checkbox("Winner 🏆", key=f"seat_win_{seat}_{form_v}")

                        participants_input.append({
                            "seat_position": seat,
                            "player_id": selected_player_id,
                            "deck_id": selected_deck_id,
                            "mulligan_count": mulligans,
                            "is_winner": is_winner
                        })

                return participants_input

            participants_input = render_participants_fragment()

            notes = st.text_input("Match Notes (Optional)", placeholder="e.g. Turn 6 Rhystic Study went unanswered", key=f"input_match_notes_{form_v}")
            
            col_save1, col_save2 = st.columns(2)
            with col_save1:
                submit_match = st.button("💾 Save Game Log (Clear Form)", use_container_width=True, type="primary", key=f"btn_save_clear_{form_v}")
            with col_save2:
                rematch_submit = st.button("🔁 Save & Rematch (Keep Pod/Decks)", use_container_width=True, type="secondary", key=f"btn_save_rematch_{form_v}")

            if submit_match or rematch_submit:
                missing_players = any(p['player_id'] is None for p in participants_input)
                missing_decks = any(p['deck_id'] is None for p in participants_input)
                winners_count = sum(1 for p in participants_input if p['is_winner'])

                if not win_condition:
                    st.error("Please select a Win Condition.")
                elif missing_players:
                    st.error(f"Please select a player for all {num_players} seats.")
                elif missing_decks:
                    st.error(f"Please select a deck for all {num_players} seats.")
                elif winners_count != 1:
                    st.warning("Please mark exactly ONE player as the winner.")
                else:
                    game_data = {
                        "total_turns": total_turns,
                        "duration_minutes": duration,
                        "win_condition": win_condition,
                        "notes": notes,
                        "bracket": bracket_level,
                        "medium": game_medium
                    }
                    db.log_game_session(game_data, participants_input)
                    
                    st.session_state.timer_running = False
                    st.session_state.timer_start_time = None
                    st.session_state.timer_elapsed_seconds = 0
                    st.session_state.live_turn_count = 1
                    db.update_live_session(active_session_key, False, None, 0, 1)

                    if submit_match:
                        st.session_state.form_version += 1
                        st.toast("Game logged & form cleared!", icon="🧹")

                    elif rematch_submit:
                        keys_to_reset = [f"input_win_condition_{form_v}", f"input_match_notes_{form_v}"]
                        for seat in range(1, num_players + 1):
                            keys_to_reset.extend([f"seat_mull_{seat}_{form_v}", f"seat_win_{seat}_{form_v}"])
                        for k in keys_to_reset:
                            if k in st.session_state:
                                del st.session_state[k]

                        st.toast("Game logged! Ready for Rematch with same pod & decks!", icon="🔁")

                    st.rerun()

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

            col_o1, col_o2 = st.columns([2, 1])
            with col_o1:
                owner_name = st.selectbox("Who owns this deck?", player_names, index=None, placeholder="Select a player...")
            with col_o2:
                new_deck_bracket = st.selectbox("Deck Power Bracket", options=[1, 2, 3, 4, 5], index=2, key="add_deck_power_bracket")

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
                            owner_id = player_dict[owner_name]
                            deck_id = mox_url.strip().split('/')[-1]
                            headers = {
                                "User-Agent": "Mozilla/5.0",
                                "Accept": "application/json, text/plain, */*",
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
                                        raw_colors = comm_data.get("card", {}).get("colors", [])
                                        color_str = "".join(raw_colors) if raw_colors else "C"
                                        comm_id = db.get_or_create_commander(comm_name, color_str)
                                        commander_ids.append(comm_id)
                                    
                                    db.create_deck(owner_id, deck_name, commander_ids, bracket=new_deck_bracket)
                                    st.success(f"Successfully imported **{deck_name}** (Bracket {new_deck_bracket})!")
                                    st.balloons()
                                    st.rerun()
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
                        
                        comm1_id = db.get_or_create_commander(comm1_name.strip(), comm1_colors.strip().upper())
                        commander_ids.append(comm1_id)
                        
                        if comm2_name.strip():
                            comm2_id = db.get_or_create_commander(comm2_name.strip(), comm2_colors.strip().upper())
                            commander_ids.append(comm2_id)

                        db.create_deck(owner_id, manual_deck_name.strip(), commander_ids, bracket=new_deck_bracket)
                        st.success(f"Deck '{manual_deck_name}' created with {len(commander_ids)} commander(s)!")

# ------------------------------------------------------------------------------
# TAB 3: DECK & PLAYER ADMIN (ADMIN ONLY)
# ------------------------------------------------------------------------------
if tab_admin_decks:
    with tab_admin_decks:
        st.subheader("🛠️ Player & Deck Management")
        
        if "player_add_success_name" in st.session_state:
            added_name = st.session_state.pop("player_add_success_name")
            st.success(f"🎉 Player **{added_name}** was added successfully!")
            st.toast(f"Added '{added_name}'!", icon="👤")

        # 1. MANAGE PLAYERS
        with st.expander("👤 Manage Players (Add / Delete)", expanded=False):
            col_add, col_del = st.columns(2)
            
            with col_add:
                st.markdown("#### ➕ Add Player")
                new_player_name = st.text_input("Player Name", placeholder="e.g. John Doe", key="input_add_player_name")

                if st.button("Add Player", type="primary", key="btn_add_player"):
                    clean_name = new_player_name.strip()
                    if not clean_name:
                        st.error("Please enter a player name first.")
                    else:
                        existing_players = [p['display_name'].lower() for p in db.fetch_players()]
                        if clean_name.lower() in existing_players:
                            st.error(f"Player '{clean_name}' already exists!")
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

        # 2. EDIT / DELETE REGISTERED DECKS
        with st.expander("✏️ Edit & Delete Registered Decks", expanded=True):
            st.markdown("Select a player to view, modify, or remove their registered decks:")
            
            players = db.fetch_players()
            if players:
                player_dict = {p['display_name']: p['player_id'] for p in players}
                selected_edit_owner = st.selectbox("Select Deck Owner", list(player_dict.keys()), index=None, key="admin_edit_deck_owner_select")

                if selected_edit_owner:
                    owner_id = player_dict[selected_edit_owner]
                    user_decks = db.fetch_player_decks(owner_id)

                    if user_decks:
                        deck_options = {f"{d['deck_name']} (⚡ Bracket {d.get('bracket', 3)})": d for d in user_decks}
                        selected_deck_label = st.selectbox("Select Deck to Modify", list(deck_options.keys()), index=None, key="admin_edit_deck_select")

                        if selected_deck_label:
                            deck_obj = deck_options[selected_deck_label]
                            selected_deck_id = deck_obj['deck_id']
                            curr_bracket = int(deck_obj.get('bracket', 3))

                            col_e1, col_e2, col_e3 = st.columns([2, 2, 1])
                            with col_e1:
                                new_name = st.text_input("Deck Name", value=deck_obj['deck_name'], key=f"input_rename_deck_{selected_deck_id}")
                            with col_e2:
                                new_owner_name = st.selectbox(
                                    "Transfer Ownership To", 
                                    list(player_dict.keys()), 
                                    index=list(player_dict.keys()).index(selected_edit_owner),
                                    key=f"input_reassign_owner_{selected_deck_id}"
                                )
                            with col_e3:
                                edit_deck_bracket = st.selectbox(
                                    "Power Bracket",
                                    options=[1, 2, 3, 4, 5],
                                    index=curr_bracket - 1,
                                    key=f"input_deck_bracket_{selected_deck_id}"
                                )

                            col_btn_update, col_btn_del = st.columns(2)

                            with col_btn_update:
                                if st.button("💾 Save Deck Changes", type="primary", use_container_width=True, key=f"btn_save_deck_{selected_deck_id}"):
                                    if not new_name.strip():
                                        st.error("Deck name cannot be empty.")
                                    else:
                                        target_owner_id = player_dict[new_owner_name]
                                        db.update_deck_details(selected_deck_id, new_name.strip(), target_owner_id, edit_deck_bracket)
                                        st.toast(f"Updated '{new_name}'!", icon="✅")
                                        st.success("Deck updated successfully!")
                                        st.rerun()

                            with col_btn_del:
                                confirm_deck_del = st.checkbox("Confirm Delete", key=f"chk_del_deck_{selected_deck_id}")
                                if st.button("🗑️ Delete Deck", type="secondary", use_container_width=True, key=f"btn_del_deck_{selected_deck_id}"):
                                    if confirm_deck_del:
                                        db.delete_deck(selected_deck_id)
                                        st.toast(f"Deleted deck!", icon="🗑️")
                                        st.success("Deck deleted successfully!")
                                        st.rerun()
                                    else:
                                        st.error("Please check the confirmation box first.")
                    else:
                        st.info("This player has no registered decks.")

        # 3. DIRECT COMMANDER COLOR IDENTITY EDITOR
        with st.expander("🎨 Edit Commander Color Identity", expanded=False):
            st.markdown("Select a specific Commander card to directly edit its WUBRG color identity:")
            
            all_commanders = db.fetch_all_commanders() if hasattr(db, 'fetch_all_commanders') else []
            if all_commanders:
                comm_map = {f"{c['name']} (Current Colors: {c['colors']})": c for c in all_commanders}
                selected_comm_label = st.selectbox("Select Commander Card", list(comm_map.keys()), index=None, key="admin_edit_comm_colors_select")
                
                if selected_comm_label:
                    comm_obj = comm_map[selected_comm_label]
                    comm_id = comm_obj['commander_id']
                    
                    color_options = ["W ⚪", "U 🔵", "B 💀", "R 🔥", "G 🌲", "C ⚙️"]
                    raw_colors = str(comm_obj['colors']).upper()
                    default_colors = [opt for opt in color_options if opt[0] in raw_colors]

                    selected_colors = st.multiselect("Color Identity", color_options, default=default_colors, key=f"edit_comm_cols_{comm_id}")
                    
                    if st.button("💾 Save Commander Colors", type="primary", key=f"btn_save_comm_cols_{comm_id}"):
                        clean_color_str = "".join([c.split()[0] for c in selected_colors]) if selected_colors else "C"
                        
                        db.update_commander_colors(comm_id, clean_color_str)
                        st.toast(f"Updated {comm_obj['name']} to {clean_color_str}!", icon="🎨")
                        st.success(f"Successfully updated {comm_obj['name']} color identity to **{clean_color_str}**!")
                        st.rerun()
            else:
                st.info("No commanders registered in the database.")

        # 4. UPGRADE MANUAL DECK TO MOXFIELD
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
                                            "User-Agent": "Mozilla/5.0",
                                            "Accept": "application/json, text/plain, */*",
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

        # 5. VIEW REGISTERED DECKS
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

# ------------------------------------------------------------------------------
# TAB 4: MATCH ADMIN (ADMIN ONLY)
# ------------------------------------------------------------------------------
if tab_admin_matches:
    with tab_admin_matches:
        st.subheader("✏️ Match Management & Editing")

        with st.expander("✏️ Edit Logged Matches & Participants", expanded=True):
            st.markdown("Filter by date to view and modify game sessions:")
            
            col_filter1, col_filter2 = st.columns([1, 2])
            with col_filter1:
                filter_date = st.date_input("Filter Matches by Date", value=get_ast_today(), key="admin_edit_match_date")
            
            games_for_date = db.fetch_games_by_date(filter_date) if hasattr(db, 'fetch_games_by_date') else db.fetch_recent_games(limit=25)
            
            if games_for_date:
                game_options = {}
                for g in games_for_date:
                    label = f"Game #{g['game_id']} | Turns: {g['total_turns']} | Win: {g['win_condition']} ({g['participants']})"
                    game_options[label] = g['game_id']
                
                with col_filter2:
                    selected_edit_game_label = st.selectbox(
                        f"Select Match from {filter_date.strftime('%b %d, %Y')}", 
                        list(game_options.keys()), 
                        index=0 if len(game_options) == 1 else None, 
                        key=f"admin_select_match_edit_{filter_date}"
                    )
                
                if selected_edit_game_label:
                    game_to_edit_id = game_options[selected_edit_game_label]
                    
                    # --- STREAMLIT FRAGMENT: RETROACTIVE MATCH EDITOR ---
                    @st.fragment
                    def render_edit_match_fragment(game_id):
                        game_data = next((g for g in games_for_date if g['game_id'] == game_id), None)
                        seat_participants = db.fetch_game_participants(game_id)
                        all_global_decks = db.fetch_all_decks_with_owners() if hasattr(db, 'fetch_all_decks_with_owners') else []
                        players = db.fetch_players()
                        player_dict = {p['display_name']: p['player_id'] for p in players} if players else {}
                        
                        if game_data and seat_participants:
                            st.markdown("#### 1. Match Details")
                            ecol1, ecol2, ecol3, ecol4 = st.columns(4)
                            
                            with ecol1:
                                edit_turns = st.number_input("Turns", 1, 50, value=int(game_data.get('total_turns', 8)), key=f"edit_turns_{game_id}")
                            with ecol2:
                                edit_duration = st.number_input("Duration (mins)", 1, 500, value=int(game_data.get('duration_minutes', 45)), key=f"edit_dur_{game_id}")
                            with ecol3:
                                edit_bracket = st.selectbox("Bracket", [1, 2, 3, 4, 5], index=int(game_data.get('bracket', 3)) - 1, key=f"edit_brack_{game_id}")
                            with ecol4:
                                medium_opts = ["In Person 🃏", "Convoke 💻", "SpellTable 📹"]
                                curr_med = game_data.get('medium', "In Person 🃏")
                                med_idx = medium_opts.index(curr_med) if curr_med in medium_opts else 0
                                edit_medium = st.selectbox("Medium", medium_opts, index=med_idx, key=f"edit_med_{game_id}")

                            edit_win_con = st.selectbox(
                                "Win Condition",
                                ["Combat Damage", "Infinite Combo", "Alternate Win-Con", "Commander Damage", "Scoop / Surrender"],
                                index=["Combat Damage", "Infinite Combo", "Alternate Win-Con", "Commander Damage", "Scoop / Surrender"].index(game_data['win_condition']) if game_data.get('win_condition') in ["Combat Damage", "Infinite Combo", "Alternate Win-Con", "Commander Damage", "Scoop / Surrender"] else 0,
                                key=f"edit_wincon_{game_id}"
                            )
                            
                            edit_notes = st.text_input("Match Notes", value=game_data.get('notes', ''), key=f"edit_notes_{game_id}")

                            st.markdown("#### 2. Seats & Decks (Retroactive Fixes)")
                            updated_seats = []
                            global_deck_map = {d['deck_id']: d for d in all_global_decks} if all_global_decks else {}

                            for idx, seat in enumerate(seat_participants, start=1):
                                seat_dict = dict(seat)
                                part_id = seat_dict.get('participant_id', seat_dict.get('id', idx))
                                s_pos = seat_dict.get('seat_number', seat_dict.get('seat_position', seat_dict.get('seat', idx)))
                                p_id = seat_dict.get('player_id')
                                d_id = seat_dict.get('deck_id')
                                
                                curr_deck_info = global_deck_map.get(d_id, {})
                                deck_owner_id = curr_deck_info.get('owner_id')
                                curr_deck_name = curr_deck_info.get('deck_name', 'Unknown Deck')
                                curr_p_name = next((name for name, pid in player_dict.items() if pid == p_id), "Select Player")
                                is_currently_borrowed = (p_id != deck_owner_id) if deck_owner_id else False

                                with st.expander(f"👤 Seat {s_pos}: {curr_p_name} ({'🎁 Borrowed Deck' if is_currently_borrowed else 'Owned Deck'})", expanded=True):
                                    player_names = list(player_dict.keys())
                                    p_idx = player_names.index(curr_p_name) if curr_p_name in player_names else 0
                                    
                                    new_seat_player = st.selectbox("Player", player_names, index=p_idx, key=f"edit_p_seat_{part_id}_{idx}")
                                    new_seat_player_id = player_dict[new_seat_player]

                                    edit_borrowing = st.checkbox("🎁 Was this a borrowed deck?", value=is_currently_borrowed, key=f"edit_borrow_chk_{part_id}_{idx}")

                                    if edit_borrowing:
                                        global_deck_dict = {f"{d['deck_name']} (Owner: {d['owner_name']})": d['deck_id'] for d in all_global_decks}
                                        curr_deck_label = next((k for k, v in global_deck_dict.items() if v == d_id), None)
                                        g_keys = list(global_deck_dict.keys())
                                        g_idx = g_keys.index(curr_deck_label) if curr_deck_label in g_keys else 0

                                        selected_deck_label = st.selectbox("Borrowed Deck", g_keys, index=g_idx, key=f"edit_d_global_{part_id}_{idx}")
                                        new_seat_deck_id = global_deck_dict[selected_deck_label]
                                    else:
                                        player_decks = db.fetch_player_decks(new_seat_player_id)
                                        if player_decks:
                                            p_deck_dict = {d['deck_name']: d['deck_id'] for d in player_decks}
                                            p_deck_names = list(p_deck_dict.keys())
                                            d_idx = p_deck_names.index(curr_deck_name) if curr_deck_name in p_deck_names else 0

                                            selected_deck_name = st.selectbox("Owned Deck", p_deck_names, index=d_idx, key=f"edit_d_owned_{part_id}_{idx}")
                                            new_seat_deck_id = p_deck_dict[selected_deck_name]
                                        else:
                                            st.caption("⚠️ Selected player has no registered decks. Toggle 'Borrowed deck' above to pick from global list.")
                                            new_seat_deck_id = d_id

                                    scol1, scol2 = st.columns(2)
                                    with scol1:
                                        edit_mull = st.number_input("Mulligans", 0, 7, value=int(seat_dict.get('mulligan_count', 0)), key=f"edit_mull_{part_id}_{idx}")
                                    with scol2:
                                        edit_win = st.checkbox("Winner 🏆", value=bool(seat_dict.get('is_winner', False)), key=f"edit_win_{part_id}_{idx}")

                                    updated_seats.append({
                                        "seat_position": s_pos,
                                        "player_id": new_seat_player_id,
                                        "deck_id": new_seat_deck_id,
                                        "mulligan_count": edit_mull,
                                        "is_winner": edit_win
                                    })

                            if st.button("💾 Save Match Edits", type="primary", use_container_width=True, key=f"btn_save_match_edit_{game_id}"):
                                winners_count = sum(1 for s in updated_seats if s['is_winner'])
                                missing_decks = any(s['deck_id'] is None for s in updated_seats)
                                
                                if winners_count != 1:
                                    st.warning("Please mark exactly ONE player as the winner.")
                                elif missing_decks:
                                    st.error("Please ensure a valid deck is assigned to all seats.")
                                else:
                                    db.update_full_game_match(
                                        game_id=game_id,
                                        total_turns=edit_turns,
                                        duration_minutes=edit_duration,
                                        win_condition=edit_win_con,
                                        notes=edit_notes,
                                        bracket=edit_bracket,
                                        medium=edit_medium,
                                        participants=updated_seats
                                    )
                                    st.toast(f"Game #{game_id} updated successfully!", icon="✅")
                                    st.success("Match record updated!")
                                    st.rerun()

                    render_edit_match_fragment(game_to_edit_id)
            else:
                st.info(f"No logged matches found on {filter_date.strftime('%B %d, %Y')}.")

        with st.expander("🗑️ Delete Matches", expanded=False):
            st.markdown("Select a game session to permanently delete from database logs:")
            recent_games = db.fetch_recent_games(limit=20)
            
            if recent_games:
                game_options = {}
                for g in recent_games:
                    label = f"Game #{g['game_id']} | Turns: {g['total_turns']} | Win: {g['win_condition']} ({g['participants']})"
                    game_options[label] = g['game_id']
                
                selected_game_label = st.selectbox("Select Match to Delete", list(game_options.keys()), index=None, key="admin_select_match_delete")
                
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
# TAB 5: DAILY SESSION RECAP & EXPORT
# ------------------------------------------------------------------------------
if tab_recap:
    with tab_recap:
        st.subheader("📋 Daily Session Recap & Share")
        
        col_r1, col_r2 = st.columns([1, 2])
        with col_r1:
            recap_date = st.date_input("Select Game Session Date", value=get_ast_today(), key="recap_date_picker")
            
        recap_data = db.fetch_daily_session_summary(recap_date) if hasattr(db, 'fetch_daily_session_summary') else None
        
        if recap_data:
            ov = recap_data['overview']
            p_df = pd.DataFrame(recap_data['players'])
            d_df = pd.DataFrame(recap_data['decks'])
            
            mvp_player = p_df.iloc[0]['player_name'] if not p_df.empty else "N/A"
            mvp_wins = p_df.iloc[0]['wins'] if not p_df.empty else 0
            best_deck = d_df.iloc[0]['deck_name'] if not d_df.empty else "N/A"
            
            st.markdown(f"### ⚔️ Session Breakdown — {recap_date.strftime('%B %d, %Y')}")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Matches Logged", ov['total_games'])
            m2.metric("Total Playtime", f"{int(ov['total_playtime'])} mins")
            m3.metric("Avg Turn Count", f"Turn {ov['avg_turns']}")
            m4.metric("Session MVP 🏆", f"{mvp_player}")
            
            st.divider()
            
            col_p_tab, col_d_tab = st.columns(2)
            
            with col_p_tab:
                st.markdown("#### 👤 Player Leaderboard (Today)")
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
                st.markdown("#### 🃏 Deck Performance (Today)")
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
            
            st.markdown("#### 💬 Group Chat Summary Export")
            
            summary_text = f"⚔️ *EDH SESSION RECAP — {recap_date.strftime('%b %d, %Y')}*\n"
            summary_text += f"📊 *Total Games:* {ov['total_games']} | *Playtime:* {int(ov['total_playtime'])} mins | *Avg:* Turn {ov['avg_turns']}\n"
            summary_text += f"🏆 *Session MVP:* {mvp_player} ({mvp_wins} Wins)\n"
            summary_text += f"🔥 *Top Deck:* {best_deck}\n\n"
            summary_text += "*Player Standings:*\n"
            for _, row in p_df.iterrows():
                summary_text += f"• {row['player_name']}: {row['wins']}W / {row['games_played']}G ({row['win_rate']}%)\n"

            st.code(summary_text, language="text")
            st.caption("💡 Click the copy button in the top right of the text box above to share directly into your playgroup's chat!")
            
        else:
            st.info(f"No match sessions logged on {recap_date.strftime('%B %d, %Y')}.")

# ------------------------------------------------------------------------------
# TAB 6: ANALYTICS (PUBLIC / ALL ROLES)
# ------------------------------------------------------------------------------
with tab_stats:
    st.subheader("📊 Playgroup Operations & Metrics")
    
    raw_stats = db.get_player_stats()
    all_decks = db.get_all_deck_performance_stats()
    
    total_games_played = db.get_total_games_count() if hasattr(db, 'get_total_games_count') else (sum([dict(r)['wins'] for r in raw_stats]) if raw_stats else 0)
    total_registered_decks = len(all_decks) if all_decks else 0
    bracket_val, bracket_sub = db.get_most_common_deck_bracket() if hasattr(db, 'get_most_common_deck_bracket') else ("N/A", "")
    
    overview_data = db.get_game_overview_stats()
    avg_turns = 0
    avg_duration = 0
    if overview_data:
        overview_df = pd.DataFrame([dict(row) for row in overview_data])
        avg_turns = round(overview_df['avg_turns'].mean(), 1)
        avg_duration = round(overview_df['avg_duration'].mean(), 0)

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("Total Matches Logged", total_games_played)
        st.metric("Avg Turn Count", f"Turn {avg_turns}" if avg_turns else "N/A")
    with col_m2:
        st.metric("Total Decks Registered", total_registered_decks)
        st.metric("Avg Game Length", f"{int(avg_duration)} mins" if avg_duration else "N/A")
    with col_m3:
        st.metric("Most Played Bracket", bracket_val, delta=bracket_sub, delta_color="off")
    
    st.divider()

    st.markdown("### 📜 Last 2 Matches Logged")
    recent_2_games = db.fetch_last_n_games_detailed(limit=2) if hasattr(db, 'fetch_last_n_games_detailed') else []
    
    if recent_2_games:
        for g in recent_2_games:
            winner_name = next((s['player_name'] for s in g['seats'] if s['is_winner']), "Unknown")
            winner_deck = next((s['deck_name'] for s in g['seats'] if s['is_winner']), "Unknown Deck")
            
            with st.expander(f"🏆 Game #{g['game_id']} Winner: {winner_name} ({winner_deck}) — {g['win_condition']}", expanded=False):
                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    st.caption(f"⏱️ **Duration:** {g['duration_minutes']} mins | **Turns:** Turn {g['total_turns']}")
                with sc2:
                    st.caption(f"🎯 **Game Bracket:** Bracket {g.get('bracket', 3)} | **Platform:** {g.get('medium', 'In Person')}")
                with sc3:
                    if g['notes']:
                        st.caption(f"📝 **Notes:** {g['notes']}")

                seat_rows = []
                for s in g['seats']:
                    seat_rows.append({
                        "Seat": f"Seat {s['seat_position']}",
                        "Player": s['player_name'],
                        "Deck Played": f"{s['deck_name']} (⚡ B{s['deck_bracket']})",
                        "Mulligans": s['mulligan_count'],
                        "Result": "🏆 WINNER" if s['is_winner'] else "❌ Defeat"
                    })
                st.dataframe(pd.DataFrame(seat_rows), hide_index=True, use_container_width=True)
    else:
        st.info("No recent matches found.")

    st.divider()

    st.markdown("### 🧮 Playgroup Arsenal & Deck Ownership")
    col_ownership, col_colors = st.columns(2)

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

    with col_colors:
        st.markdown("#### 🎨 Color Presence in Arsenal")
        color_presence = db.get_color_presence_stats()
        if color_presence:
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

    st.markdown("### 🃏 Complete Deck Performance")
    if all_decks:
        df_decks = pd.DataFrame([dict(row) for row in all_decks])
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

    st.markdown("### 🎨 Color Identity Win Rates")
    color_stats = db.get_color_identity_stats()
    if color_stats:
        df_colors = pd.DataFrame([dict(row) for row in color_stats])
        
        mana_icons = {'W': '☀️', 'U': '💧', 'B': '💀', 'R': '🔥', 'G': '🌳', 'C': '💎'}
        guild_names = {
            'W': 'Mono White', 'U': 'Mono Blue', 'B': 'Mono Black', 'R': 'Mono Red', 'G': 'Mono Green', 'C': 'Colorless',
            'WU': 'Azorius', 'UB': 'Dimir', 'BR': 'Rakdos', 'RG': 'Gruul', 'GW': 'Selesnya',
            'WB': 'Orzhov', 'UR': 'Izzet', 'BG': 'Golgari', 'RW': 'Boros', 'GU': 'Simic',
            'GWU': 'Bant', 'WUB': 'Esper', 'UBR': 'Grixis', 'BRG': 'Jund', 'RGW': 'Naya',
            'WBG': 'Abzan', 'URW': 'Jeskai', 'BGU': 'Sultai', 'RWB': 'Mardu', 'GUR': 'Temur',
            'UBRG': 'Yidris', 'BRGW': 'Saskia', 'RGWU': 'Kynaios and Tiro', 'GWUB': 'Atraxa', 'WUBR': 'Breya',
            'WUBRG': '5-Color'
        }
        
        def normalize_color_identity(color_raw):
            if not color_raw:
                return "C"
            wubrg_order = "WUBRG"
            sorted_chars = sorted(
                str(color_raw).upper().strip(), 
                key=lambda x: wubrg_order.find(x) if x in wubrg_order else 99
            )
            return "".join(sorted_chars)

        df_colors['canonical_color'] = df_colors['color_identity'].apply(normalize_color_identity)
        
        df_grouped_colors = df_colors.groupby('canonical_color', as_index=False).agg({
            'games_played': 'sum',
            'wins': 'sum'
        })
        
        df_grouped_colors['win_rate'] = (df_grouped_colors['wins'] / df_grouped_colors['games_played']) * 100
        
        def format_color_identity(clean_code):
            if clean_code == "C":
                return "💎 Colorless"
            emojis = "".join([mana_icons.get(char, '') for char in clean_code])
            name = guild_names.get(clean_code, clean_code)
            return f"{emojis} {name}"
            
        df_grouped_colors['identity_display'] = df_grouped_colors['canonical_color'].apply(format_color_identity)
        df_grouped_colors = df_grouped_colors.sort_values(by=['win_rate', 'games_played'], ascending=[False, False])
        
        st.dataframe(
            df_grouped_colors[['identity_display', 'games_played', 'wins', 'win_rate']],
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

    st.divider()

    st.markdown("### 🎯 Bracket Distribution & Game Velocity")
    if hasattr(db, 'get_bracket_stats'):
        bracket_data = db.get_bracket_stats()
        if bracket_data:
            df_bracket = pd.DataFrame([dict(row) for row in bracket_data])
            
            df_bracket['avg_turns'] = df_bracket['avg_turns'].astype(str).str.replace(r'["\\]', '', regex=True)
            
            def clean_to_float(val):
                try:
                    f = float(val)
                    if f > 20:  
                        f = f / 10.0
                    return f
                except:
                    return 0.0

            df_bracket['avg_turns'] = df_bracket['avg_turns'].apply(clean_to_float)
            df_bracket['avg_duration'] = pd.to_numeric(df_bracket['avg_duration'], errors='coerce')
            df_bracket['total_games'] = pd.to_numeric(df_bracket['total_games'], errors='coerce')
            
            df_bracket['bracket_label'] = df_bracket['bracket'].apply(lambda x: f"Bracket {x}")
            
            col_b_chart1, col_b_chart2 = st.columns(2)
            
            with col_b_chart1:
                st.markdown("#### 📊 Total Matches per Bracket")
                st.bar_chart(df_bracket, x='bracket_label', y='total_games', color='#ff4b4b')
                
            with col_b_chart2:
                st.markdown("#### ⚡ Average Turns by Bracket")
                st.bar_chart(df_bracket, x='bracket_label', y='avg_turns', color='#29b5e8')
                
            st.dataframe(
                df_bracket[['bracket_label', 'total_games', 'avg_turns', 'avg_duration']],
                column_config={
                    "bracket_label": st.column_config.TextColumn("Power Bracket"),
                    "total_games": st.column_config.NumberColumn("Matches Logged", format="%d"),
                    "avg_turns": st.column_config.NumberColumn("Avg Turn Count", format="Turn %.1f"),
                    "avg_duration": st.column_config.NumberColumn("Avg Duration", format="%d mins"),
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No bracket data logged yet.")

    if hasattr(db, 'get_medium_stats'):
        st.divider()
        st.markdown("### 🌐 Game Platform Distribution")
        medium_data = db.get_medium_stats()
        if medium_data:
            df_medium = pd.DataFrame([dict(row) for row in medium_data])
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.dataframe(
                    df_medium[['medium', 'total_games', 'avg_duration']],
                    column_config={
                        "medium": st.column_config.TextColumn("Platform / Medium"),
                        "total_games": st.column_config.NumberColumn("Matches Logged", format="%d"),
                        "avg_duration": st.column_config.NumberColumn("Avg Game Length", format="%d mins"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
            with col_m2:
                st.bar_chart(df_medium, x='medium', y='total_games', color='#9061f9')
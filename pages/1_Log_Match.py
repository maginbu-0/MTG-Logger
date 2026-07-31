import streamlit as st
import time
import db

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

if "input_total_turns" not in st.session_state:
    st.session_state["input_total_turns"] = 8
if "input_duration" not in st.session_state:
    st.session_state["input_duration"] = 45
if "form_version" not in st.session_state:
    st.session_state.form_version = 0

# --- STREAMLIT FRAGMENT: LIVE GAME COMPANION ---
@st.fragment(run_every=1)
def render_live_companion_fragment():
    current_elapsed = st.session_state.get("timer_elapsed_seconds", 0)
    if st.session_state.get("timer_running", False) and st.session_state.get("timer_start_time") is not None:
        current_elapsed += int(time.time() - st.session_state.timer_start_time)

    last_sync = st.session_state.get("last_db_sync_time", 0)
    if st.session_state.get("timer_running", False) and (time.time() - last_sync > 15):
        st.session_state.last_db_sync_time = time.time()
        sync_companion_to_db()

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
                if not st.session_state.get("timer_running", False):
                    if st.button("▶️ Start / Resume", use_container_width=True, key="btn_timer_start"):
                        st.session_state.timer_running = True
                        st.session_state.timer_start_time = time.time()
                        st.session_state.last_db_sync_time = time.time()
                        sync_companion_to_db()
                        st.rerun()
                else:
                    if st.button("⏸️ Pause", use_container_width=True, key="btn_timer_pause"):
                        st.session_state.timer_running = False
                        st.session_state.timer_elapsed_seconds = current_elapsed
                        st.session_state.timer_start_time = None
                        sync_companion_to_db()
                        st.rerun()
            
            with t_col2:
                if st.button("🔄 Reset Timer", use_container_width=True, key="btn_timer_reset"):
                    st.session_state.timer_running = False
                    st.session_state.timer_start_time = None
                    st.session_state.timer_elapsed_seconds = 0
                    st.session_state.live_turn_count = 1
                    sync_companion_to_db()
                    st.rerun()

        with col_turns:
            st.markdown("#### 🔄 Turn Counter")
            st.markdown(f"<h2 style='text-align: center; margin: 0;'>Turn {st.session_state.get('live_turn_count', 1)}</h2>", unsafe_allow_html=True)
            
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
            if st.session_state.get("timer_running", False) and st.session_state.get("timer_start_time") is not None:
                st.session_state.timer_elapsed_seconds += int(time.time() - st.session_state.timer_start_time)
                st.session_state.timer_running = False
                st.session_state.timer_start_time = None
            
            final_minutes = max(1, round(st.session_state.timer_elapsed_seconds / 60))
            
            st.session_state["input_total_turns"] = int(st.session_state.live_turn_count)
            st.session_state["input_duration"] = int(final_minutes)
            st.session_state.form_version += 1
            
            sync_companion_to_db()
            st.toast(f"Pushed {final_minutes} mins and Turn {st.session_state.live_turn_count} to form!", icon="⏱️")
            st.rerun()

render_live_companion_fragment()

# MATCH DETAILS FORM
st.subheader("Match Details")

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
        total_turns = st.number_input(
            "Total Turns", 
            min_value=1, 
            max_value=50, 
            value=int(st.session_state.get("input_total_turns", 8)), 
            key=f"input_total_turns_{form_v}"
        )
    with col2:
        duration = st.number_input(
            "Duration (mins)", 
            min_value=1, 
            max_value=500, 
            value=int(st.session_state.get("input_duration", 45)), 
            key=f"input_duration_{form_v}"
        )
    with col3:
        bracket_level = st.selectbox("Game Bracket", options=[1, 2, 3, 4, 5], index=2, key=f"input_bracket_{form_v}")
    with col4:
        game_medium = st.selectbox("Platform / Medium", options=["In Person 🃏", "Convoke 💻", "SpellTable 📹"], index=0, key=f"input_medium_{form_v}")

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
from datetime import datetime, date
import streamlit as st
import time
from zoneinfo import ZoneInfo
import db


def get_ast_today():
    return datetime.now(ZoneInfo("America/Santo_Domingo")).date()

st.subheader("⚔️ Live Match Companion & Logger")

active_session_key = st.session_state.get("user_role", "Logger")

if "form_v" not in st.session_state:
    st.session_state.form_v = 0

def init_session_state_from_db():
    """Deferred loader to prevent container startup locks & normalize types."""
    if "timer_running" not in st.session_state:
        try:
            db_session = db.fetch_live_session(active_session_key)
            st.session_state.timer_running = db_session["timer_running"]
            st.session_state.timer_start_time = db_session["timer_start_time"]
            st.session_state.timer_elapsed_seconds = db_session["timer_elapsed_seconds"]
            st.session_state.live_turn_count = db_session["live_turn_count"]

            db_draft = db.fetch_live_pod_draft(active_session_key) if hasattr(db, 'fetch_live_pod_draft') else {}
            if isinstance(db_draft, dict):
                for k, v in db_draft.items():
                    # Safely convert ISO date strings back into native datetime.date objects for any date key
                    if ("date" in k or k == "input_match_date") and isinstance(v, str):
                        try:
                            st.session_state[k] = datetime.strptime(v, "%Y-%m-%d").date()
                        except ValueError:
                            st.session_state[k] = get_ast_today()
                    else:
                        st.session_state[k] = v
        except Exception:
            # Fallback values if DB is unreachable during boot
            st.session_state.timer_running = False
            st.session_state.timer_start_time = None
            st.session_state.timer_elapsed_seconds = 0
            st.session_state.live_turn_count = 1

def sync_companion_to_db():
    db.update_live_session(
        active_session_key,
        st.session_state.timer_running,
        st.session_state.timer_start_time,
        st.session_state.timer_elapsed_seconds,
        st.session_state.live_turn_count
    )

def save_current_draft_to_db():
    if st.session_state.get("skip_draft_save", False):
        return
    if hasattr(db, 'update_live_pod_draft'):
        POD_KEYS_PREFIXES = ("seat_player_", "seat_borrow_", "seat_deck_id_borrowed_", "seat_deck_id_owned_", "seat_mull_", "seat_win_", "input_")
        draft = {}
        for k, v in st.session_state.items():
            if any(k.startswith(p) for p in POD_KEYS_PREFIXES) and v is not None:
                if isinstance(v, (date, datetime)):
                    formatted_date = v.strftime("%Y-%m-%d") if isinstance(v, (date, datetime)) else str(v)
                    draft[k] = formatted_date
                else:
                    draft[k] = v
        db.update_live_pod_draft(active_session_key, draft)

def clear_form_selections():
    """Completely wipes session state keys & clears Supabase draft."""
    st.session_state.saved_pod_state = {}
    st.session_state.skip_draft_save = True
    
    if hasattr(db, 'update_live_pod_draft'):
        db.update_live_pod_draft(active_session_key, {})
    
    st.session_state.input_match_date = get_ast_today()
    st.session_state.input_total_turns = 8
    st.session_state.input_duration = 45
    st.session_state.input_win_condition = None
    st.session_state.input_match_notes = ""
    st.session_state.input_bracket = 3
    st.session_state.input_medium = "In Person 🃏"
    st.session_state.input_num_players = 4
    
    for seat in range(1, 5):
        st.session_state[f"seat_player_{seat}"] = None
        st.session_state[f"seat_borrow_{seat}"] = False
        st.session_state[f"seat_deck_id_borrowed_{seat}"] = None
        st.session_state[f"seat_deck_id_owned_{seat}"] = None
        st.session_state[f"seat_mull_{seat}"] = 0
        st.session_state[f"seat_win_{seat}"] = False

# SAFELY INITIALIZE DB STATE ONLY AFTER STREAMLIT MOUNTS
init_session_state_from_db()

# Reset skip flag on render start
st.session_state.skip_draft_save = False

# --- LIVE GAME COMPANION FRAGMENT ---
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

render_live_companion_fragment()

# --- END MATCH BUTTON ---
if st.button("🏁 End Match & Auto-Fill Form", type="primary", use_container_width=True, key="btn_end_match"):
    current_elapsed = st.session_state.get("timer_elapsed_seconds", 0)
    if st.session_state.get("timer_running", False) and st.session_state.get("timer_start_time") is not None:
        current_elapsed += int(time.time() - st.session_state.timer_start_time)
        st.session_state.timer_elapsed_seconds = current_elapsed
        st.session_state.timer_running = False
        st.session_state.timer_start_time = None
    
    final_minutes = max(1, round(current_elapsed / 60))
    final_turns = int(st.session_state.get("live_turn_count", 1))
    
    st.session_state.input_total_turns = final_turns
    st.session_state.input_duration = final_minutes
    st.session_state.form_v += 1
    
    sync_companion_to_db()
    save_current_draft_to_db()

    st.toast(f"Pushed {final_minutes} mins and Turn {final_turns} to form!", icon="⏱️")
    st.rerun()

st.divider()

# MATCH DETAILS FORM
col_header1, col_header2 = st.columns([3, 1])
with col_header1:
    st.subheader("Match Details")
with col_header2:
    if st.button("🧹 Clear Form Inputs", use_container_width=True):
        clear_form_selections()
        st.session_state.form_v += 1
        st.toast("Form cleared!", icon="🧹")
        st.rerun()

players = db.fetch_players()

if not players:
    st.warning("No players found in database!")
else:
    player_dict = {p['display_name']: p['player_id'] for p in players}
    player_names = list(player_dict.keys())
    all_global_decks = db.fetch_all_decks_with_owners() if hasattr(db, 'fetch_all_decks_with_owners') else []

    fv = st.session_state.form_v

    # DATE SELECTION ROW WITH GUARANTEED NATIVE TYPE CASTING
    col_d1, _ = st.columns([1, 1])
    with col_d1:
        raw_saved_date = st.session_state.get("input_match_date", get_ast_today())
        
        if isinstance(raw_saved_date, str):
            try:
                saved_date = datetime.strptime(raw_saved_date, "%Y-%m-%d").date()
            except ValueError:
                saved_date = get_ast_today()
        elif isinstance(raw_saved_date, datetime):
            saved_date = raw_saved_date.date()
        elif isinstance(raw_saved_date, date):
            saved_date = raw_saved_date
        else:
            saved_date = get_ast_today()

        match_date = st.date_input(
            "📅 Match Date", 
            value=saved_date, 
            key=f"input_match_date_{fv}",
            on_change=save_current_draft_to_db
        )
        st.session_state["input_match_date"] = match_date

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_turns = st.number_input(
            "Total Turns", 
            min_value=1, 
            max_value=50, 
            value=int(st.session_state.get("input_total_turns", 8)), 
            key=f"input_total_turns_{fv}",
            on_change=save_current_draft_to_db
        )
    with col2:
        duration = st.number_input(
            "Duration (mins)", 
            min_value=1, 
            max_value=500, 
            value=int(st.session_state.get("input_duration", 45)), 
            key=f"input_duration_{fv}",
            on_change=save_current_draft_to_db
        )
    with col3:
        bracket_options = [1, 2, 3, 4, 5]
        curr_b = int(st.session_state.get("input_bracket", 3))
        b_idx = bracket_options.index(curr_b) if curr_b in bracket_options else 2
        bracket_level = st.selectbox(
            "Game Bracket", 
            options=bracket_options, 
            index=b_idx, 
            key=f"input_bracket_{fv}",
            on_change=save_current_draft_to_db
        )
    with col4:
        medium_options = ["In Person 🃏", "Convoke 💻", "SpellTable 📹"]
        curr_m = st.session_state.get("input_medium", "In Person 🃏")
        m_idx = medium_options.index(curr_m) if curr_m in medium_options else 0
        game_medium = st.selectbox(
            "Platform / Medium", 
            options=medium_options, 
            index=m_idx, 
            key=f"input_medium_{fv}",
            on_change=save_current_draft_to_db
        )

    win_options = ["Combat Damage", "Infinite Combo", "Alternate Win-Con", "Commander Damage", "Scoop / Surrender"]
    curr_w = st.session_state.get("input_win_condition")
    w_idx = win_options.index(curr_w) if curr_w in win_options else None
    
    win_condition = st.selectbox(
        "Win Condition",
        win_options,
        index=w_idx,
        placeholder="How did it end?",
        key=f"input_win_condition_{fv}",
        on_change=save_current_draft_to_db
    )

    st.divider()
    
    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        p_num_opt = [3, 4]
        curr_p_num = int(st.session_state.get("input_num_players", 4))
        p_num_idx = p_num_opt.index(curr_p_num) if curr_p_num in p_num_opt else 1
        num_players = st.selectbox(
            "Number of Players", 
            options=p_num_opt, 
            index=p_num_idx, 
            key=f"input_num_players_{fv}",
            on_change=save_current_draft_to_db
        )

    st.subheader("Participants")
    participants_input = []

    for seat in range(1, num_players + 1):
        pk = f"seat_player_{seat}"
        bk = f"seat_borrow_{seat}"
        bdk = f"seat_deck_id_borrowed_{seat}"
        odk = f"seat_deck_id_owned_{seat}"
        mk = f"seat_mull_{seat}"
        wk = f"seat_win_{seat}"

        saved_p_val = st.session_state.get(pk, None)
        p_idx = player_names.index(saved_p_val) if saved_p_val in player_names else None
        header_text = f"👤 Seat {seat}" + (f": {saved_p_val}" if saved_p_val else "")

        with st.expander(header_text, expanded=True):
            selected_player_name = st.selectbox(
                "Player", 
                player_names, 
                index=p_idx, 
                placeholder="Select player...", 
                key=f"{pk}_{fv}",
                on_change=save_current_draft_to_db
            )
            st.session_state[pk] = selected_player_name
            
            saved_b_val = bool(st.session_state.get(bk, False))
            is_borrowing = st.checkbox(
                "🎁 Borrowing a deck from someone else?", 
                value=saved_b_val,
                key=f"{bk}_{fv}",
                on_change=save_current_draft_to_db
            )
            st.session_state[bk] = is_borrowing
            
            selected_player_id = None
            selected_deck_id = None
            
            if selected_player_name:
                selected_player_id = player_dict[selected_player_name]
                if is_borrowing:
                    if all_global_decks:
                        global_deck_map = {int(d['deck_id']): f"{d['deck_name']} (Owner: {d['owner_name']})" for d in all_global_decks}
                        g_deck_ids = list(global_deck_map.keys())
                        
                        raw_bd_id = st.session_state.get(bdk, None)
                        saved_bd_id = int(raw_bd_id) if raw_bd_id is not None and str(raw_bd_id).isdigit() else None
                        bd_idx = g_deck_ids.index(saved_bd_id) if saved_bd_id in g_deck_ids else None

                        selected_deck_id = st.selectbox(
                            "Select Borrowed Deck", 
                            g_deck_ids, 
                            format_func=lambda did: global_deck_map.get(did, ""),
                            index=bd_idx, 
                            placeholder="Select borrowed deck...", 
                            key=f"{bdk}_{fv}",
                            on_change=save_current_draft_to_db
                        )
                        st.session_state[bdk] = selected_deck_id
                    else:
                        st.caption("⚠️ No global decks found.")
                else:
                    available_decks = db.fetch_player_decks(selected_player_id)
                    if available_decks:
                        owned_deck_map = {int(d['deck_id']): f"{d['deck_name']} (⚡ Bracket {d.get('bracket', 3)})" for d in available_decks}
                        o_deck_ids = list(owned_deck_map.keys())
                        
                        raw_od_id = st.session_state.get(odk, None)
                        saved_od_id = int(raw_od_id) if raw_od_id is not None and str(raw_od_id).isdigit() else None
                        od_idx = o_deck_ids.index(saved_od_id) if saved_od_id in o_deck_ids else None

                        selected_deck_id = st.selectbox(
                            "Deck", 
                            o_deck_ids, 
                            format_func=lambda did: owned_deck_map.get(did, ""),
                            index=od_idx, 
                            placeholder="Select deck...", 
                            key=f"{odk}_{fv}",
                            on_change=save_current_draft_to_db
                        )
                        st.session_state[odk] = selected_deck_id
                    else:
                        st.caption("⚠️ No active decks found for this player.")
            else:
                st.selectbox("Deck", [], disabled=True, index=None, placeholder="Waiting for player...", key=f"seat_deck_disabled_{seat}_{fv}")

            col_mull, col_win = st.columns(2)
            with col_mull:
                saved_mull = int(st.session_state.get(mk, 0))
                mulligans = st.number_input("Mulligans", 0, 7, value=saved_mull, key=f"{mk}_{fv}", on_change=save_current_draft_to_db)
                st.session_state[mk] = mulligans
            with col_win:
                saved_win = bool(st.session_state.get(wk, False))
                is_winner = st.checkbox("Winner 🏆", value=saved_win, key=f"{wk}_{fv}", on_change=save_current_draft_to_db)
                st.session_state[wk] = is_winner

            participants_input.append({
                "seat_position": seat,
                "player_id": selected_player_id,
                "deck_id": selected_deck_id,
                "mulligan_count": mulligans,
                "is_winner": is_winner
            })

    notes = st.text_input("Match Notes (Optional)", placeholder="e.g. Turn 6 Rhystic Study went unanswered", value=st.session_state.get("input_match_notes", ""), key=f"input_match_notes_{fv}", on_change=save_current_draft_to_db)
    st.session_state["input_match_notes"] = notes

    col_save1, col_save2 = st.columns(2)
    with col_save1:
        submit_match = st.button("💾 Save Game Log (Clear Form)", use_container_width=True, type="primary", key="btn_save_clear")
    with col_save2:
        rematch_submit = st.button("🔁 Save & Rematch (Keep Pod/Decks)", use_container_width=True, type="secondary", key="btn_save_rematch")

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
            db.log_game_session(game_data, participants_input, match_date=match_date)
            
            st.session_state.timer_running = False
            st.session_state.timer_start_time = None
            st.session_state.timer_elapsed_seconds = 0
            st.session_state.live_turn_count = 1
            db.update_live_session(active_session_key, False, None, 0, 1)

            if submit_match:
                clear_form_selections()
                st.session_state.form_v += 1
                st.toast(f"Game logged for {match_date.strftime('%b %d, %Y')} & form cleared!", icon="🧹")
                st.rerun()

            elif rematch_submit:
                st.session_state.form_v += 1
                st.session_state.input_win_condition = None
                st.session_state.input_match_notes = ""
                for seat in range(1, num_players + 1):
                    st.session_state[f"seat_mull_{seat}"] = 0
                    st.session_state[f"seat_win_{seat}"] = False
                
                save_current_draft_to_db()
                st.toast(f"Game logged for {match_date.strftime('%b %d, %Y')}! Ready for Rematch!", icon="🔁")
                st.rerun()
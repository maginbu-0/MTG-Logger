import streamlit as st
import datetime
from zoneinfo import ZoneInfo
import db

def get_ast_today():
    return datetime.datetime.now(ZoneInfo("America/Santo_Domingo")).date()

st.subheader("✏️ Match Management & Editing")

@st.fragment
def render_admin_matches_fragment():
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
                game_data = next((g for g in games_for_date if g['game_id'] == game_to_edit_id), None)
                seat_participants = db.fetch_game_participants(game_to_edit_id)
                all_global_decks = db.fetch_all_decks_with_owners() if hasattr(db, 'fetch_all_decks_with_owners') else []
                players = db.fetch_players()
                player_dict = {p['display_name']: p['player_id'] for p in players} if players else {}
                
                if game_data and seat_participants:
                    st.markdown("#### 1. Match Details")
                    ecol1, ecol2, ecol3, ecol4 = st.columns(4)
                    
                    with ecol1:
                        edit_turns = st.number_input("Turns", 1, 50, value=int(game_data.get('total_turns', 8)), key=f"edit_turns_{game_to_edit_id}")
                    with ecol2:
                        edit_duration = st.number_input("Duration (mins)", 1, 500, value=int(game_data.get('duration_minutes', 45)), key=f"edit_dur_{game_to_edit_id}")
                    with ecol3:
                        raw_bracket = game_data.get('bracket')
                        bracket_idx = (int(raw_bracket) - 1) if raw_bracket and 1 <= int(raw_bracket) <= 5 else 2
                        edit_bracket = st.selectbox("Bracket", [1, 2, 3, 4, 5], index=bracket_idx, key=f"edit_brack_{game_to_edit_id}")

                    with ecol4:
                        medium_opts = ["In Person 🃏", "Convoke 💻", "SpellTable 📹"]
                        curr_med = str(game_data.get('medium', '') or '')
                        
                        med_idx = 0
                        for idx, opt in enumerate(medium_opts):
                            if curr_med.lower() in opt.lower() or opt.lower() in curr_med.lower():
                                med_idx = idx
                                break
            
                        edit_medium = st.selectbox("Medium", medium_opts, index=med_idx, key=f"edit_med_{game_to_edit_id}")

                    edit_win_con = st.selectbox(
                        "Win Condition",
                        ["Combat Damage", "Infinite Combo", "Alternate Win-Con", "Commander Damage", "Scoop / Surrender"],
                        index=["Combat Damage", "Infinite Combo", "Alternate Win-Con", "Commander Damage", "Scoop / Surrender"].index(game_data['win_condition']) if game_data.get('win_condition') in ["Combat Damage", "Infinite Combo", "Alternate Win-Con", "Commander Damage", "Scoop / Surrender"] else 0,
                        key=f"edit_wincon_{game_to_edit_id}"
                    )
                    
                    edit_notes = st.text_input("Match Notes", value=game_data.get('notes', ''), key=f"edit_notes_{game_to_edit_id}")

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

                    if st.button("💾 Save Match Edits", type="primary", use_container_width=True, key=f"btn_save_match_edit_{game_to_edit_id}"):
                        winners_count = sum(1 for s in updated_seats if s['is_winner'])
                        missing_decks = any(s['deck_id'] is None for s in updated_seats)
                        
                        if winners_count != 1:
                            st.error("Please mark exactly ONE player as the winner.")
                        elif missing_decks:
                            st.error("Please ensure a valid deck is assigned to all seats.")
                        else:
                            db.update_full_game_match(
                                game_id=game_to_edit_id,
                                total_turns=edit_turns,
                                duration_minutes=edit_duration,
                                win_condition=edit_win_con,
                                notes=edit_notes,
                                bracket=edit_bracket,
                                medium=edit_medium,
                                participants=updated_seats
                            )
                            
                            # Deselect the game dropdown state so the editor closes on rerun
                            select_widget_key = f"admin_select_match_edit_{filter_date}"
                            if select_widget_key in st.session_state:
                                del st.session_state[select_widget_key]
                                
                            st.toast(f"Game #{game_to_edit_id} updated successfully!", icon="✅")
                            st.success("Match record updated!")
                            st.rerun()
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

render_admin_matches_fragment()
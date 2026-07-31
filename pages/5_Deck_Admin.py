import streamlit as st
import pandas as pd
import db

st.subheader("🛠️ Player & Deck Management")

@st.fragment
def render_admin_decks_fragment():
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
                                    data = db.fetch_moxfield_deck(mox_url_upgrade)
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

render_admin_decks_fragment()
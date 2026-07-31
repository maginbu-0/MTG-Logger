import streamlit as st
import db

st.subheader("➕ Add a New Deck")

@st.fragment
def render_add_deck_fragment():
    players = db.fetch_players()
    if not players:
        st.warning("No players found in database.")
        return

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
                    data = db.fetch_moxfield_deck(mox_url)
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

render_add_deck_fragment()
import streamlit as st
import db

# ------------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & MOBILE STYLING
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Commander Tracker",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for quick touch targets on mobile devices
st.markdown("""
    <style>
    /* Make buttons easy to tap on mobile touchscreens */
    .stButton > button {
        width: 100%;
        height: 3rem;
        font-weight: bold;
        border-radius: 8px;
    }
    /* Reduce top padding for mobile screens */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Commander Tracker")

# ------------------------------------------------------------------------------
# 2. NAVIGATION TABS
# ------------------------------------------------------------------------------
tab_log, tab_add_deck, tab_analytics = st.tabs([
    "⚔️ Log Match", 
    "➕ Add Deck", 
    "📊 Analytics"
])

# ------------------------------------------------------------------------------
# TAB 1: LOG MATCH (DYNAMIC SELECTION FIX)
# ------------------------------------------------------------------------------
with tab_log:
    st.header("Log Match Details")

    players = db.fetch_players()
    
    if not players:
        st.warning("No players found in database. Add players to Supabase first!")
    else:
        player_dict = {p['display_name']: p['player_id'] for p in players}
        player_names = list(player_dict.keys())

        # --- 1. Match Overview Inputs ---
        st.subheader("1. Match Overview")
        col1, col2 = st.columns(2)
        with col1:
            total_turns = st.number_input("Total Turns", min_value=1, max_value=30, value=8)
            win_condition = st.selectbox(
                "Win Condition", 
                ["Combat Damage", "Commander Damage", "Combo / Alternate Win", "Concession", "Other"]
            )
        with col2:
            duration_minutes = st.number_input("Duration (Mins)", min_value=5, max_value=300, value=45, step=5)
            num_players = st.selectbox("Number of Players", [4, 3, 5, 6], index=0)

        st.divider()

        # --- 2. Dynamic Participants Selection ---
        st.subheader("2. Participants")
        
        participants_input = []
        
        for i in range(num_players):
            st.markdown(f"**Seat {i+1}**")
            p_col1, p_col2, p_col3, p_col4 = st.columns([2, 2, 1, 1])
            
            with p_col1:
                default_idx = i if i < len(player_names) else 0
                selected_player_name = st.selectbox(
                    "Player", 
                    player_names, 
                    index=default_idx, 
                    key=f"seat_{i}_player"
                )
                selected_player_id = player_dict[selected_player_name]

            with p_col2:
                # Fetch decks live outside of st.form so selecting a player updates decks instantly
                user_decks = db.fetch_player_decks(selected_player_id)
                deck_options = {d['deck_name']: d['deck_id'] for d in user_decks}
                
                if deck_options:
                    selected_deck_name = st.selectbox(
                        "Deck", 
                        list(deck_options.keys()), 
                        key=f"seat_{i}_deck"
                    )
                    selected_deck_id = deck_options[selected_deck_name]
                else:
                    st.selectbox("Deck", ["No Decks Found"], disabled=True, key=f"seat_{i}_deck_disabled")
                    selected_deck_id = None

            with p_col3:
                mulligans = st.number_input("Mulls", min_value=0, max_value=7, value=0, key=f"seat_{i}_mull")

            with p_col4:
                is_winner = st.checkbox("Winner?", key=f"seat_{i}_win")

            participants_input.append({
                "seat_position": i + 1,
                "player_id": selected_player_id,
                "deck_id": selected_deck_id,
                "mulligan_count": mulligans,
                "is_winner": is_winner
            })

        st.divider()

        # --- 3. Match Notes & Action ---
        notes = st.text_input("Match Notes (Optional)", placeholder="e.g., Turn 7 Craterhoof / Orzhov player had great board control")
        
        st.write("") # Padding
        if st.button("⚔️ Save Game Session", type="primary"):
            missing_decks = [p for p in participants_input if p['deck_id'] is None]
            winners = [p for p in participants_input if p['is_winner']]

            if missing_decks:
                st.error("Every player must have a valid deck selected!")
            elif len(winners) == 0:
                st.error("Please mark at least one winner for the match!")
            else:
                game_data = {
                    "total_turns": total_turns,
                    "duration_minutes": duration_minutes,
                    "win_condition": win_condition,
                    "notes": notes
                }
                game_id = db.log_game_session(game_data, participants_input)
                st.toast(f"🎉 Game #{game_id} logged successfully!", icon="✅")
                st.success("Match saved to database!")

# ------------------------------------------------------------------------------
# TAB 2: ADD DECK (MOXFIELD IMPORT / MANUAL)
# ------------------------------------------------------------------------------
with tab_add_deck:
    st.header("Add a New Deck")
    
    players = db.fetch_players()
    if players:
        player_dict = {p['display_name']: p['player_id'] for p in players}
        selected_owner_name = st.selectbox("Deck Owner", list(player_dict.keys()), key="owner_select")
        owner_id = player_dict[selected_owner_name]
        
        deck_name = st.text_input("Deck Name", placeholder="e.g., Wilhelt Zombie Tribal")
        commander_name = st.text_input("Commander Name", placeholder="e.g., Wilhelt, the Rotcleaver")
        color_id = st.text_input("Color Identity", placeholder="e.g., UB or Orzhov")

        if st.button("Save Deck"):
            if deck_name and commander_name:
                comm_id = db.get_or_create_commander(commander_name, color_id or "Unknown")
                deck_id = db.create_deck(owner_id, deck_name, [comm_id])
                st.toast(f"Deck '{deck_name}' created!", icon="🎴")
                st.success(f"Added '{deck_name}' for {selected_owner_name}!")
            else:
                st.error("Please fill in both Deck Name and Commander Name.")

# ------------------------------------------------------------------------------
# TAB 3: ANALYTICS
# ------------------------------------------------------------------------------
with tab_analytics:
    st.header("📊 Playgroup Performance")

    st.subheader("Player Leaderboard")
    player_stats = db.get_player_stats()
    if player_stats:
        st.dataframe(player_stats, use_container_width=True)
    else:
        st.info("No games logged yet. Play some matches to populate stats!")

    st.subheader("Deck Leaderboard")
    deck_stats = db.get_deck_stats()
    if deck_stats:
        st.dataframe(deck_stats, use_container_width=True)
    else:
        st.info("No deck performance data available yet.")
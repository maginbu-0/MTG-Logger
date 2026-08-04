import streamlit as st
import pandas as pd
import db

st.subheader("📊 Playgroup Operations & Metrics")

@st.fragment
def render_analytics_fragment():
    raw_stats = db.get_player_stats()
    all_decks = db.get_all_deck_performance_stats()
    
    total_games_played = len(db.fetch_recent_games(limit=1000)) if hasattr(db, 'fetch_recent_games') else (sum([dict(r)['wins'] for r in raw_stats]) if raw_stats else 0)
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
                "owner_name": st.column_config.TextColumn("Owner"),
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
                        "medium": st.column_config.TextColumn("Platform"),
                        "total_games": st.column_config.NumberColumn("Matches Logged", format="%d"),
                        "avg_duration": st.column_config.NumberColumn("Avg Game Length", format="%d mins"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
            with col_m2:
                st.bar_chart(df_medium, x='medium', y='total_games', color='#9061f9')

render_analytics_fragment()
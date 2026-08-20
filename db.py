import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from contextlib import contextmanager
import streamlit as st

# Load local .env file if running locally
load_dotenv()

DATABASE_URL = None

try:
    DATABASE_URL = st.secrets.get("DATABASE_URL")
except Exception:
    DATABASE_URL = None

if not DATABASE_URL:
    DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_db():
    """Context manager for Supabase PostgreSQL connection with strict timeout guard."""
    if not DATABASE_URL:
        raise ValueError(
            "DATABASE_URL is missing. Please add DATABASE_URL = \"your_connection_string\" "
            "in Streamlit Cloud's Secrets manager (Settings -> Secrets) or in your local .env file."
        )
        
    try:
        conn = psycopg2.connect(
            DATABASE_URL, 
            cursor_factory=RealDictCursor,
            connect_timeout=3
        )
    except Exception as e:
        print(f"Database Connection Error: {e}")
        st.error("⚠️ Unable to connect to database. Please check connection string / secrets.")
        raise e

    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Database Query Error: {e}")
        raise e
    finally:
        conn.close()

# ------------------------------------------------------------------------------
# CACHED FETCH FUNCTIONS (READ OPERATIONS)
# ------------------------------------------------------------------------------

@st.cache_data(ttl=300)
def fetch_players():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT player_id, display_name, role FROM players ORDER BY display_name ASC;")
        return cur.fetchall()

@st.cache_data(ttl=300)
def fetch_commanders():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT commander_id, name, color_identity FROM commanders ORDER BY name ASC;")
        return cur.fetchall()

@st.cache_data(ttl=300)
def fetch_player_decks(player_id):
    query = """
        SELECT 
            d.deck_id,
            d.deck_name,
            COALESCE(d.bracket, 3) AS bracket,
            STRING_AGG(c.name, ' // ') AS commander_names,
            STRING_AGG(c.color_identity, '') AS composite_color_identity
        FROM decks d
        LEFT JOIN deck_commanders dc ON d.deck_id = dc.deck_id
        LEFT JOIN commanders c ON dc.commander_id = c.commander_id
        WHERE d.player_id = %s
        GROUP BY d.deck_id, d.deck_name, d.bracket
        ORDER BY d.deck_name;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, (player_id,))
        return cur.fetchall()

@st.cache_data(ttl=300)
def fetch_all_decks_with_owners():
    query = """
        SELECT 
            d.deck_id,
            d.deck_name,
            p.display_name AS owner_name,
            STRING_AGG(c.name, ' & ') AS commander_names
        FROM decks d
        JOIN players p ON d.player_id = p.player_id
        LEFT JOIN deck_commanders dc ON d.deck_id = dc.deck_id
        LEFT JOIN commanders c ON dc.commander_id = c.commander_id
        GROUP BY d.deck_id, d.deck_name, p.display_name
        ORDER BY p.display_name, d.deck_name;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query)
        return cur.fetchall()

@st.cache_data(ttl=300)
def fetch_all_commanders():
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT commander_id, name, COALESCE(color_identity, 'C') AS colors FROM commanders ORDER BY name ASC;")
            return cur.fetchall()
        except Exception:
            conn.rollback()

        try:
            cur.execute("SELECT commander_id, name, COALESCE(colors, 'C') AS colors FROM commanders ORDER BY name ASC;")
            return cur.fetchall()
        except Exception:
            conn.rollback()

        try:
            cur.execute("SELECT commander_id, name, COALESCE(color, 'C') AS colors FROM commanders ORDER BY name ASC;")
            return cur.fetchall()
        except Exception:
            conn.rollback()

        cur.execute("SELECT commander_id, name, 'C' AS colors FROM commanders ORDER BY name ASC;")
        return cur.fetchall()

@st.cache_data(ttl=300)
def fetch_recent_games(limit=25):
    query = """
        SELECT 
            g.game_id,
            g.total_turns,
            g.win_condition,
            COALESCE(g.notes, '') AS notes,
            STRING_AGG(p.display_name, ', ' ORDER BY gp.seat_position) AS participants
        FROM games g
        JOIN game_participants gp ON g.game_id = gp.game_id
        JOIN players p ON gp.player_id = p.player_id
        GROUP BY g.game_id, g.total_turns, g.win_condition, g.notes
        ORDER BY g.game_id DESC
        LIMIT %s;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, (limit,))
        return cur.fetchall()

@st.cache_data(ttl=300)
def fetch_game_participants(game_id):
    query = "SELECT * FROM game_participants WHERE game_id = %s;"
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute(query, (game_id,))
            rows = cur.fetchall()
        except Exception:
            conn.rollback()
            cur.execute("SELECT * FROM game_participants WHERE session_id = %s;", (game_id,))
            rows = cur.fetchall()

        if not rows:
            return []

        participants = [dict(r) for r in rows]
        participants.sort(key=lambda x: x.get('seat_number', x.get('seat_position', x.get('seat', 0))))
        return participants

@st.cache_data(ttl=300)
def fetch_games_by_date(selected_date):
    date_str = str(selected_date)
    query = """
        SELECT 
            g.game_id,
            g.total_turns,
            g.duration_minutes,
            g.win_condition,
            g.bracket,
            g.medium,
            COALESCE(g.notes, '') AS notes,
            STRING_AGG(p.display_name, ', ' ORDER BY gp.seat_position) AS participants
        FROM games g
        JOIN game_participants gp ON g.game_id = gp.game_id
        JOIN players p ON gp.player_id = p.player_id
        WHERE TO_CHAR(g.played_at AT TIME ZONE 'America/Santo_Domingo', 'YYYY-MM-DD') = %s
        GROUP BY g.game_id, g.total_turns, g.duration_minutes, g.win_condition, g.bracket, g.medium, g.notes
        ORDER BY g.game_id DESC;
    """
    query_fallback = """
        SELECT 
            g.game_id,
            g.total_turns,
            g.duration_minutes,
            g.win_condition,
            g.bracket,
            g.medium,
            COALESCE(g.notes, '') AS notes,
            STRING_AGG(p.display_name, ', ' ORDER BY gp.seat_position) AS participants
        FROM games g
        JOIN game_participants gp ON g.game_id = gp.game_id
        JOIN players p ON gp.player_id = p.player_id
        WHERE TO_CHAR(g.played_at - INTERVAL '4 hours', 'YYYY-MM-DD') = %s
        GROUP BY g.game_id, g.total_turns, g.duration_minutes, g.win_condition, g.bracket, g.medium, g.notes
        ORDER BY g.game_id DESC;
    """
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute(query, (date_str,))
            return cur.fetchall()
        except Exception:
            conn.rollback()
            cur.execute(query_fallback, (date_str,))
            return cur.fetchall()

@st.cache_data(ttl=300)
def fetch_daily_session_summary(selected_date):
    date_str = str(selected_date)
    with get_db() as conn:
        cur = conn.cursor()
        query_overview = """
            SELECT 
                COUNT(DISTINCT g.game_id) AS total_games,
                ROUND(AVG(g.total_turns), 1) AS avg_turns,
                ROUND(AVG(g.duration_minutes), 0) AS avg_duration,
                SUM(g.duration_minutes) AS total_playtime
            FROM games g
            WHERE TO_CHAR(g.played_at - INTERVAL '4 hours', 'YYYY-MM-DD') = %s;
        """
        cur.execute(query_overview, (date_str,))
        overview = cur.fetchone()
        
        if not overview or overview['total_games'] == 0:
            return None
            
        query_players = """
            SELECT 
                p.display_name AS player_name,
                COUNT(gp.game_id) AS games_played,
                SUM(CASE WHEN gp.is_winner IS TRUE THEN 1 ELSE 0 END) AS wins,
                ROUND((SUM(CASE WHEN gp.is_winner IS TRUE THEN 1 ELSE 0 END)::numeric / COUNT(gp.game_id)) * 100, 1) AS win_rate
            FROM game_participants gp
            JOIN games g ON gp.game_id = g.game_id
            JOIN players p ON gp.player_id = p.player_id
            WHERE TO_CHAR(g.played_at - INTERVAL '4 hours', 'YYYY-MM-DD') = %s
            GROUP BY p.player_id, p.display_name
            ORDER BY wins DESC, games_played ASC;
        """
        cur.execute(query_players, (date_str,))
        players_summary = cur.fetchall()
        
        query_decks = """
            SELECT 
                d.deck_name,
                p.display_name AS owner_name,
                COUNT(gp.game_id) AS games_played,
                SUM(CASE WHEN gp.is_winner IS TRUE THEN 1 ELSE 0 END) AS wins,
                ROUND((SUM(CASE WHEN gp.is_winner IS TRUE THEN 1 ELSE 0 END)::numeric / COUNT(gp.game_id)) * 100, 1) AS win_rate
            FROM game_participants gp
            JOIN games g ON gp.game_id = g.game_id
            JOIN decks d ON gp.deck_id = d.deck_id
            JOIN players p ON gp.player_id = p.player_id
            WHERE TO_CHAR(g.played_at - INTERVAL '4 hours', 'YYYY-MM-DD') = %s
            GROUP BY d.deck_id, d.deck_name, p.display_name
            ORDER BY wins DESC, games_played ASC;
        """
        cur.execute(query_decks, (date_str,))
        decks_summary = cur.fetchall()
        
        return {
            "overview": dict(overview),
            "players": [dict(r) for r in players_summary],
            "decks": [dict(r) for r in decks_summary]
        }

@st.cache_data(ttl=300)
def get_player_stats():
    query = """
        SELECT 
            p.display_name,
            COUNT(gp.game_id) AS games_played,
            SUM(CASE WHEN gp.is_winner IS TRUE THEN 1 ELSE 0 END) AS wins
        FROM players p
        JOIN game_participants gp ON p.player_id = gp.player_id
        GROUP BY p.player_id
        HAVING COUNT(gp.game_id) > 0
        ORDER BY wins DESC, games_played ASC;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query)
        return cur.fetchall()

@st.cache_data(ttl=300)
def get_deck_stats():
    query = """
        SELECT 
            d.deck_name,
            p.display_name AS owner_name,
            COUNT(gp.game_id) AS games_played,
            SUM(CASE WHEN gp.is_winner IS TRUE THEN 1 ELSE 0 END) AS wins
        FROM decks d
        JOIN game_participants gp ON d.deck_id = gp.deck_id
        JOIN players p ON d.player_id = p.player_id
        GROUP BY d.deck_id, d.deck_name, p.display_name
        HAVING COUNT(gp.game_id) > 0
        ORDER BY wins DESC, games_played ASC;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query)
        return cur.fetchall()

@st.cache_data(ttl=300)
def get_color_identity_stats():
    query = """
        SELECT 
            c.color_identity,
            COUNT(gp.game_id) AS games_played,
            SUM(CASE WHEN gp.is_winner IS TRUE THEN 1 ELSE 0 END) AS wins
        FROM commanders c
        JOIN deck_commanders dc ON c.commander_id = dc.commander_id
        JOIN decks d ON dc.deck_id = d.deck_id
        JOIN game_participants gp ON d.deck_id = gp.deck_id
        GROUP BY c.color_identity
        HAVING COUNT(gp.game_id) > 0
        ORDER BY wins DESC, games_played ASC;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query)
        return cur.fetchall()

@st.cache_data(ttl=300)
def get_game_overview_stats():
    query = """
        SELECT 
            AVG(total_turns) AS avg_turns,
            AVG(duration_minutes) AS avg_duration,
            win_condition,
            COUNT(*) as condition_count
        FROM games
        GROUP BY win_condition;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query)
        return cur.fetchall()

@st.cache_data(ttl=300)
def get_deck_ownership_stats():
    query = """
        SELECT 
            p.display_name AS player_name,
            COUNT(d.deck_id) AS deck_count
        FROM players p
        LEFT JOIN decks d ON p.player_id = d.player_id
        GROUP BY p.player_id, p.display_name
        ORDER BY deck_count DESC, player_name ASC;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query)
        return cur.fetchall()

@st.cache_data(ttl=300)
def get_color_presence_stats():
    query = """
        SELECT 
            c.color_identity,
            COUNT(DISTINCT d.deck_id) AS deck_count
        FROM decks d
        JOIN deck_commanders dc ON d.deck_id = dc.deck_id
        JOIN commanders c ON dc.commander_id = c.commander_id
        GROUP BY c.color_identity;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query)
        return cur.fetchall()

@st.cache_data(ttl=300)
def get_all_deck_performance_stats():
    query = """
        SELECT 
            d.deck_name,
            p.display_name AS owner_name,
            COUNT(gp.game_id) AS games_played,
            SUM(CASE WHEN gp.is_winner IS TRUE THEN 1 ELSE 0 END) AS wins
        FROM decks d
        JOIN players p ON d.player_id = p.player_id
        LEFT JOIN game_participants gp ON d.deck_id = gp.deck_id
        GROUP BY d.deck_id, d.deck_name, p.display_name
        ORDER BY games_played DESC, wins DESC, d.deck_name ASC;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query)
        return cur.fetchall()

@st.cache_data(ttl=300)
def get_bracket_stats():
    query = """
        SELECT 
            bracket,
            COUNT(*) AS total_games,
            ROUND(AVG(total_turns), 1) AS avg_turns,
            ROUND(AVG(duration_minutes), 0) AS avg_duration
        FROM games
        WHERE bracket IS NOT NULL
        GROUP BY bracket
        ORDER BY bracket ASC;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query)
        return cur.fetchall()

@st.cache_data(ttl=300)
def get_medium_stats():
    query = """
        SELECT 
            COALESCE(medium, 'In Person') AS medium,
            COUNT(*) AS total_games,
            ROUND(AVG(duration_minutes)::numeric, 0) AS avg_duration
        FROM games
        GROUP BY COALESCE(medium, 'In Person')
        ORDER BY total_games DESC;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query)
        return cur.fetchall()

@st.cache_data(ttl=300)
def get_most_common_deck_bracket():
    query = """
        SELECT bracket, COUNT(*) as count 
        FROM decks 
        WHERE bracket IS NOT NULL 
        GROUP BY bracket 
        ORDER BY count DESC, bracket ASC 
        LIMIT 1;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query)
        row = cur.fetchone()
        if row:
            return f"Bracket {row['bracket']}", f"{row['count']} decks"
        return "N/A", ""

@st.cache_data(ttl=300)
def fetch_last_n_games_detailed(limit=2):
    query_games = """
        SELECT game_id, total_turns, duration_minutes, win_condition, COALESCE(notes, '') as notes, bracket, medium
        FROM games
        ORDER BY game_id DESC
        LIMIT %s;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query_games, (limit,))
        games = cur.fetchall()
        
        detailed_games = []
        for g in games:
            g_dict = dict(g)
            g_id = g_dict['game_id']
            
            query_participants = """
                SELECT 
                    gp.seat_position,
                    gp.mulligan_count,
                    gp.is_winner,
                    p.display_name AS player_name,
                    d.deck_name,
                    COALESCE(d.bracket, 3) AS deck_bracket
                FROM game_participants gp
                JOIN players p ON gp.player_id = p.player_id
                JOIN decks d ON gp.deck_id = d.deck_id
                WHERE gp.game_id = %s
                ORDER BY gp.seat_position ASC;
            """
            cur.execute(query_participants, (g_id,))
            g_dict['seats'] = cur.fetchall()
            detailed_games.append(g_dict)
            
        return detailed_games

# ------------------------------------------------------------------------------
# UNCACHED REAL-TIME SESSION FUNCTIONS
# ------------------------------------------------------------------------------

def fetch_live_session(session_key="Viewer"):
    query = "SELECT timer_running, timer_start_time, timer_elapsed_seconds, live_turn_count FROM live_game_sessions WHERE session_key = %s;"
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, (session_key,))
        row = cur.fetchone()
        if row:
            return dict(row)
        return {"timer_running": False, "timer_start_time": None, "timer_elapsed_seconds": 0, "live_turn_count": 1}

def update_live_session(session_key, running, start_time, elapsed, turns):
    query = """
        INSERT INTO live_game_sessions (session_key, timer_running, timer_start_time, timer_elapsed_seconds, live_turn_count, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        ON CONFLICT (session_key) 
        DO UPDATE SET 
            timer_running = EXCLUDED.timer_running,
            timer_start_time = EXCLUDED.timer_start_time,
            timer_elapsed_seconds = EXCLUDED.timer_elapsed_seconds,
            live_turn_count = EXCLUDED.live_turn_count,
            updated_at = NOW();
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, (session_key, running, start_time, elapsed, turns))

# ------------------------------------------------------------------------------
# WRITE OPERATIONS & API HELPERS
# ------------------------------------------------------------------------------

def create_deck(player_id, deck_name, commander_ids, bracket=3):
    query_deck = "INSERT INTO decks (player_id, deck_name, bracket) VALUES (%s, %s, %s) RETURNING deck_id;"
    query_link = "INSERT INTO deck_commanders (deck_id, commander_id) VALUES (%s, %s);"
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query_deck, (player_id, deck_name, bracket))
        deck_id = cur.fetchone()['deck_id']
        
        for comm_id in commander_ids:
            cur.execute(query_link, (deck_id, comm_id))
            
    st.cache_data.clear()
    return deck_id

def log_game_session(game_data, participants, match_date=None):
    # Use selected date or default to current timestamp
    if match_date:
        query_game = """
            INSERT INTO games (total_turns, duration_minutes, win_condition, notes, bracket, medium, played_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s::timestamp + TIME '20:00:00') 
            RETURNING game_id;
        """
        query_game_fallback = """
            INSERT INTO games (total_turns, duration_minutes, win_condition, notes, bracket, medium) 
            VALUES (%s, %s, %s, %s, %s, %s) 
            RETURNING game_id;
        """
    else:
        query_game = """
            INSERT INTO games (total_turns, duration_minutes, win_condition, notes, bracket, medium, played_at) 
            VALUES (%s, %s, %s, %s, %s, %s, NOW() - INTERVAL '4 hours') 
            RETURNING game_id;
        """
        query_game_fallback = """
            INSERT INTO games (total_turns, duration_minutes, win_condition, notes, bracket, medium) 
            VALUES (%s, %s, %s, %s, %s, %s) 
            RETURNING game_id;
        """

    query_participant = """
        INSERT INTO game_participants (game_id, seat_position, player_id, deck_id, mulligan_count, is_winner)
        VALUES (%s, %s, %s, %s, %s, %s);
    """
    with get_db() as conn:
        cur = conn.cursor()
        try:
            if match_date:
                cur.execute(query_game, (
                    game_data['total_turns'],
                    game_data['duration_minutes'],
                    game_data['win_condition'],
                    game_data['notes'],
                    game_data['bracket'],
                    game_data['medium'],
                    str(match_date)
                ))
            else:
                cur.execute(query_game, (
                    game_data['total_turns'],
                    game_data['duration_minutes'],
                    game_data['win_condition'],
                    game_data['notes'],
                    game_data['bracket'],
                    game_data['medium']
                ))
        except Exception:
            conn.rollback()
            cur.execute(query_game_fallback, (
                game_data['total_turns'],
                game_data['duration_minutes'],
                game_data['win_condition'],
                game_data['notes'],
                game_data['bracket'],
                game_data['medium']
            ))
            
        game_id = cur.fetchone()['game_id']
        
        for p in participants:
            cur.execute(query_participant, (
                game_id,
                p['seat_position'],
                p['player_id'],
                p['deck_id'],
                p['mulligan_count'],
                p['is_winner']
            ))

    st.cache_data.clear()
    return game_id

def get_or_create_commander(name, color_identity="Unknown"):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT commander_id FROM commanders WHERE name = %s;", (name,))
        row = cur.fetchone()
        
        if row:
            return row['commander_id']
        else:
            cur.execute(
                "INSERT INTO commanders (name, color_identity) VALUES (%s, %s) RETURNING commander_id;", 
                (name, color_identity)
            )
            comm_id = cur.fetchone()['commander_id']
            st.cache_data.clear()
            return comm_id

def fetch_moxfield_deck(moxfield_url):
    import re
    import json
    import urllib.request
    
    match = re.search(r'decks/([a-zA-Z0-9_-]+)', moxfield_url)
    if not match:
        raise ValueError("Invalid Moxfield URL format. Expected 'https://www.moxfield.com/decks/<deck_id>'")
    
    deck_id = match.group(1)
    api_url = f"https://api.moxfield.com/v2/decks/all/{deck_id}"

    req = urllib.request.Request(
        api_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )

    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                return data
            else:
                raise Exception(f"Moxfield API returned status code {response.status}")
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise Exception("Failed to fetch deck from Moxfield (Error 403). Make sure the deck privacy on Moxfield is set to Public, not Unlisted or Private!")
        else:
            raise Exception(f"Failed to fetch deck from Moxfield (HTTP {e.code}: {e.reason})")
    except Exception as e:
        raise Exception(f"Failed to fetch deck from Moxfield: {e}")

def add_player(display_name):
    query = "INSERT INTO players (display_name) VALUES (%s) RETURNING player_id;"
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, (display_name,))
        pid = cur.fetchone()['player_id']
    st.cache_data.clear()
    return pid

def delete_player(player_id):
    query = "DELETE FROM players WHERE player_id = %s;"
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, (player_id,))
    st.cache_data.clear()

def delete_game_session(game_id):
    query_participants = "DELETE FROM game_participants WHERE game_id = %s;"
    query_game = "DELETE FROM games WHERE game_id = %s;"
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query_participants, (game_id,))
        cur.execute(query_game, (game_id,))
    st.cache_data.clear()

def update_deck_from_moxfield(deck_id, new_deck_name, commander_ids):
    query_update_deck = "UPDATE decks SET deck_name = %s WHERE deck_id = %s;"
    query_clear_commanders = "DELETE FROM deck_commanders WHERE deck_id = %s;"
    query_add_commander = "INSERT INTO deck_commanders (deck_id, commander_id) VALUES (%s, %s);"
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query_update_deck, (new_deck_name, deck_id))
        cur.execute(query_clear_commanders, (deck_id,))
        for comm_id in commander_ids:
            cur.execute(query_add_commander, (deck_id, comm_id))
    st.cache_data.clear()

def update_commander_colors(commander_id, clean_colors):
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("UPDATE commanders SET color_identity = %s WHERE commander_id = %s;", (clean_colors, commander_id))
            st.cache_data.clear()
            return
        except Exception:
            conn.rollback()

        try:
            cur.execute("UPDATE commanders SET colors = %s WHERE commander_id = %s;", (clean_colors, commander_id))
            st.cache_data.clear()
            return
        except Exception:
            conn.rollback()

        try:
            cur.execute("UPDATE commanders SET color = %s WHERE commander_id = %s;", (clean_colors, commander_id))
            st.cache_data.clear()
            return
        except Exception:
            conn.rollback()

def update_deck_details(deck_id, deck_name, owner_id=None, bracket=3, *args, **kwargs):
    query = """
        UPDATE decks 
        SET deck_name = %s,
            player_id = COALESCE(%s, player_id),
            bracket = %s
        WHERE deck_id = %s;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, (deck_name, owner_id, bracket, deck_id))
    st.cache_data.clear()

def delete_deck(deck_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM deck_commanders WHERE deck_id = %s;", (deck_id,))
        cur.execute("DELETE FROM game_participants WHERE deck_id = %s;", (deck_id,))
        cur.execute("DELETE FROM decks WHERE deck_id = %s;", (deck_id,))
    st.cache_data.clear()

def update_full_game_match(game_id, total_turns, duration_minutes, win_condition, notes, bracket, medium, participants):
    params_games = (total_turns, duration_minutes, win_condition, notes, bracket, medium, game_id)
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("""
                UPDATE games 
                SET total_turns = %s, duration_minutes = %s, win_condition = %s, notes = %s, bracket = %s, medium = %s
                WHERE game_id = %s;
            """, params_games)
        except Exception:
            conn.rollback()
            try:
                cur.execute("""
                    UPDATE game_sessions 
                    SET total_turns = %s, duration_minutes = %s, win_condition = %s, notes = %s, bracket = %s, medium = %s
                    WHERE game_id = %s;
                """, params_games)
            except Exception:
                conn.rollback()
                cur.execute("""
                    UPDATE games 
                    SET total_turns = %s, duration_minutes = %s, win_condition = %s, notes = %s, bracket = %s, medium = %s
                    WHERE id = %s;
                """, params_games)

        for p in participants:
            try:
                cur.execute("""
                    INSERT INTO game_participants (game_id, player_id, deck_id, mulligan_count, is_winner)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (game_id, player_id) 
                    DO UPDATE SET 
                        deck_id = EXCLUDED.deck_id,
                        mulligan_count = EXCLUDED.mulligan_count,
                        is_winner = EXCLUDED.is_winner;
                """, (game_id, p['player_id'], p['deck_id'], p['mulligan_count'], p['is_winner']))
            except Exception:
                conn.rollback()
                cur.execute("""
                    UPDATE game_participants 
                    SET deck_id = %s, mulligan_count = %s, is_winner = %s
                    WHERE game_id = %s AND player_id = %s;
                """, (p['deck_id'], p['mulligan_count'], p['is_winner'], game_id, p['player_id']))

    st.cache_data.clear()

def fetch_live_pod_draft(session_key="Logger"):
    import json
    query = "SELECT pod_draft_json FROM live_game_sessions WHERE session_key = %s;"
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute(query, (session_key,))
            row = cur.fetchone()
            if row and row.get('pod_draft_json'):
                return json.loads(row['pod_draft_json'])
        except Exception:
            conn.rollback()
        return {}

def update_live_pod_draft(session_key, pod_dict):
    import json
    query = """
        UPDATE live_game_sessions 
        SET pod_draft_json = %s, updated_at = NOW() 
        WHERE session_key = %s;
    """
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute(query, (json.dumps(pod_dict), session_key))
        except Exception:
            conn.rollback()
            pass

def fetch_daily_card_from_db(today_date_str):
    import json
    query = "SELECT card_data FROM daily_card WHERE card_date = %s::date;"
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute(query, (today_date_str,))
            row = cur.fetchone()
            if row and row.get('card_data'):
                data = row['card_data']
                return json.loads(data) if isinstance(data, str) else data
        except Exception as e:
            conn.rollback()
            print(f"Error fetching daily card from DB: {e}")
        return None

def save_daily_card_to_db(today_date_str, card_data):
    import json
    query = """
        INSERT INTO daily_card (card_date, card_data, created_at)
        VALUES (%s::date, %s, NOW())
        ON CONFLICT (card_date) 
        DO UPDATE SET card_data = EXCLUDED.card_data;
    """
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute(query, (today_date_str, json.dumps(card_data)))
        except Exception as e:
            conn.rollback()
            print(f"Error saving daily card to DB: {e}")
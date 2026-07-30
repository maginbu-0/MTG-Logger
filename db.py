import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from contextlib import contextmanager
import streamlit as st

# 1. Load local .env file if running locally
load_dotenv()

DATABASE_URL = None

# 2. Safely attempt to read Streamlit Secrets without triggering an unhandled exception
try:
    # Try directly accessing the key inside st.secrets
    DATABASE_URL = st.secrets.get("DATABASE_URL")
except Exception:
    # If st.secrets is completely uninitialized/empty on Streamlit Cloud, catch the error silently
    DATABASE_URL = None

# 3. Fallback to OS environment variable (.env) if st.secrets was empty or missing
if not DATABASE_URL:
    DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_db():
    """Context manager for Supabase PostgreSQL connection."""
    if not DATABASE_URL:
        raise ValueError(
            "DATABASE_URL is missing. Please add DATABASE_URL = \"your_connection_string\" "
            "in Streamlit Cloud's Secrets manager (Settings -> Secrets) or in your local .env file."
        )
        
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Database Error: {e}")
        raise
    finally:
        conn.close()

def fetch_players():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT player_id, display_name, role FROM players ORDER BY display_name ASC;")
        return cur.fetchall()

def fetch_commanders():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT commander_id, name, color_identity FROM commanders ORDER BY name ASC;")
        return cur.fetchall()

def fetch_player_decks(player_id):
    """Fetches all decks for a player, formatting partner commanders as 'Comm A // Comm B'."""
    query = """
        SELECT 
            d.deck_id,
            d.deck_name,
            STRING_AGG(c.name, ' // ') AS commander_names,
            STRING_AGG(c.color_identity, '') AS composite_color_identity
        FROM decks d
        LEFT JOIN deck_commanders dc ON d.deck_id = dc.deck_id
        LEFT JOIN commanders c ON dc.commander_id = c.commander_id
        WHERE d.player_id = %s
        GROUP BY d.deck_id, d.deck_name
        ORDER BY d.deck_name;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, (player_id,))
        return cur.fetchall()

def create_deck(player_id, deck_name, commander_ids):
    """Creates a deck and links 1 or 2 commanders (partner commanders)."""
    query_deck = "INSERT INTO decks (player_id, deck_name) VALUES (%s, %s) RETURNING deck_id;"
    query_link = "INSERT INTO deck_commanders (deck_id, commander_id) VALUES (%s, %s);"
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query_deck, (player_id, deck_name))
        deck_id = cur.fetchone()['deck_id']
        
        # Link all commanders (handles single or partner commanders)
        for comm_id in commander_ids:
            cur.execute(query_link, (deck_id, comm_id))
            
        return deck_id



def log_game_session(game_data, participants):
    """Logs a game session including turn count, duration, win con, notes, bracket, and medium."""
    query_game = """
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
        cur.execute(query_game, (
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

    return game_id

def get_or_create_commander(name, color_identity="Unknown"):
    """Checks if a commander exists by name. If not, adds it to the database."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT commander_id FROM commanders WHERE name = %s;", (name,))
        row = cur.fetchone()
        
        if row:
            return row['commander_id']
        else:
            # Insert the new commander and use RETURNING commander_id
            cur.execute(
                "INSERT INTO commanders (name, color_identity) VALUES (%s, %s) RETURNING commander_id;", 
                (name, color_identity)
            )
            return cur.fetchone()['commander_id']


def get_player_stats():
    """Aggregates games played and total wins per player."""
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


def get_deck_stats():
    """Aggregates games played and total wins per deck."""
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


def get_color_identity_stats():
    """Aggregates win rates based on commander color identity."""
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

def get_game_overview_stats():
    """Calculates meta averages like duration, turns, and win condition counts."""
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


def add_player(display_name):
    """Adds a new player to the database safely."""
    query = "INSERT INTO players (display_name) VALUES (%s) RETURNING player_id;"
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, (display_name,))
        return cur.fetchone()['player_id']

def delete_player(player_id):
    """Deletes or deactivates a player by ID."""
    query = "DELETE FROM players WHERE player_id = %s;"
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, (player_id,))

def fetch_recent_games(limit=25):
    """Fetches a list of recent games with summary details for deletion/review."""
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

def delete_game_session(game_id):
    """Deletes a game session and its associated participant records."""
    query_participants = "DELETE FROM game_participants WHERE game_id = %s;"
    query_game = "DELETE FROM games WHERE game_id = %s;"
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query_participants, (game_id,))
        cur.execute(query_game, (game_id,))

def fetch_all_decks_with_owners():
    """Fetches all registered decks and their corresponding owners."""
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


def get_deck_ownership_stats():
    """Returns the total number of registered decks per player."""
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

def get_color_presence_stats():
    """Counts how many decks in the playgroup contain each individual MTG color."""
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

def get_all_deck_performance_stats():
    """Fetches ALL registered decks, their owner, games played, wins, and win rates (defaults 0 for unused decks)."""
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




def get_bracket_stats():
    """Fetches total games played and average turn counts grouped by power bracket."""
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


def get_medium_stats():
    """Fetches total games played and average duration grouped by platform medium."""
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

def fetch_live_session(session_key="Viewer"):
    """Fetches the current live match session state for a specific user role/logger."""
    query = "SELECT timer_running, timer_start_time, timer_elapsed_seconds, live_turn_count FROM live_game_sessions WHERE session_key = %s;"
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, (session_key,))
        row = cur.fetchone()
        if row:
            return dict(row)
        return {"timer_running": False, "timer_start_time": None, "timer_elapsed_seconds": 0, "live_turn_count": 1}

def update_live_session(session_key, running, start_time, elapsed, turns):
    """Upserts (inserts or updates) the live match session state for a specific user role/logger."""
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

def update_deck_details(deck_id, new_deck_name, new_owner_id, bracket=None):
    """Updates deck name, owner, and optional bracket rating."""
    query = """
        UPDATE decks
        SET deck_name = %s, owner_id = %s
        WHERE deck_id = %s;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, (new_deck_name, new_owner_id, deck_id))

def delete_deck(deck_id):
    """Permanently deletes a deck and its commander associations."""
    with get_db() as conn:
        cur = conn.cursor()
        # Clean up commander links first if using a bridge table
        cur.execute("DELETE FROM deck_commanders WHERE deck_id = %s;", (deck_id,))
        # Delete participant references or nullify if necessary, then delete deck
        cur.execute("DELETE FROM game_participants WHERE deck_id = %s;", (deck_id,))
        cur.execute("DELETE FROM decks WHERE deck_id = %s;", (deck_id,))

def fetch_game_participants(game_id):
    """Fetches seat participants for a specific game session cleanly."""
    query = """
        SELECT 
            gp.participant_id,
            gp.seat_number AS seat_position,
            gp.player_id,
            gp.deck_id,
            gp.mulligan_count,
            gp.is_winner,
            p.display_name AS player_name,
            d.deck_name,
            d.owner_id AS deck_owner_id
        FROM game_participants gp
        JOIN players p ON gp.player_id = p.player_id
        JOIN decks d ON gp.deck_id = d.deck_id
        WHERE gp.game_id = %s
        ORDER BY gp.participant_id ASC;
    """
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute(query, (game_id,))
            return cur.fetchall()
        except Exception:
            # Fallback if seat_number vs seat_position differs
            conn.rollback()
            query_fallback = """
                SELECT 
                    gp.participant_id,
                    gp.player_id,
                    gp.deck_id,
                    gp.mulligan_count,
                    gp.is_winner,
                    p.display_name AS player_name,
                    d.deck_name,
                    d.owner_id AS deck_owner_id
                FROM game_participants gp
                JOIN players p ON gp.player_id = p.player_id
                JOIN decks d ON gp.deck_id = d.deck_id
                WHERE gp.game_id = %s;
            """
            cur.execute(query_fallback, (game_id,))
            results = cur.fetchall()
            # Assign artificial seat positions if column is missing
            formatted = []
            for idx, r in enumerate(results, start=1):
                item = dict(r)
                item['seat_position'] = idx
                formatted.append(item)
            return formatted

def update_game_session_details(game_id, total_turns, duration_minutes, win_condition, notes, bracket, medium):
    """Updates high-level game session details."""
    query = """
        UPDATE game_sessions
        SET total_turns = %s, duration_minutes = %s, win_condition = %s, notes = %s, bracket = %s, medium = %s
        WHERE game_id = %s;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, (total_turns, duration_minutes, win_condition, notes, bracket, medium, game_id))

def update_game_participant(participant_id, player_id, deck_id, mulligan_count, is_winner):
    """Updates an individual participant seat record."""
    query = """
        UPDATE game_participants
        SET player_id = %s, deck_id = %s, mulligan_count = %s, is_winner = %s
        WHERE participant_id = %s;
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, (player_id, deck_id, mulligan_count, is_winner, participant_id))
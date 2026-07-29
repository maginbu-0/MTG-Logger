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
    with get_db() as conn:
        cur = conn.cursor()
        # Changed archived = 0 to archived = FALSE
        cur.execute(
            "SELECT deck_id, deck_name FROM decks WHERE player_id = %s AND archived = FALSE ORDER BY deck_name ASC;", 
            (player_id,)
        )
        return cur.fetchall()

def create_deck(player_id, deck_name, commander_ids):
    with get_db() as conn:
        cur = conn.cursor()
        # Added RETURNING deck_id
        cur.execute(
            "INSERT INTO decks (player_id, deck_name) VALUES (%s, %s) RETURNING deck_id;", 
            (player_id, deck_name)
        )
        deck_id = cur.fetchone()['deck_id']

        for comm_id in commander_ids:
            cur.execute(
                "INSERT INTO deck_commanders (deck_id, commander_id) VALUES (%s, %s);", 
                (deck_id, comm_id)
            )
    return deck_id

def log_game_session(game_data, participants):
    with get_db() as conn:
        cur = conn.cursor()
        
        # Insert game match header and use RETURNING game_id
        cur.execute("""
            INSERT INTO games (total_turns, duration_minutes, win_condition, notes)
            VALUES (%s, %s, %s, %s)
            RETURNING game_id;
        """, (
            game_data['total_turns'],
            game_data['duration_minutes'],
            game_data['win_condition'],
            game_data.get('notes', '')
        ))
        
        game_id = cur.fetchone()['game_id']

        # Insert granular participant results
        for p in participants:
            cur.execute("""
                INSERT INTO game_participants (
                    game_id, player_id, deck_id, seat_position, mulligan_count, is_winner
                ) VALUES (%s, %s, %s, %s, %s, %s);
            """, (
                game_id,
                p['player_id'],
                p['deck_id'],
                p['seat_position'],
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
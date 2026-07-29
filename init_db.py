import sqlite3
import os

DB_NAME = "edh_tracker.db"

def init_database():
    """Creates tables and populates initial seed data."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Enable foreign key support in SQLite
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. PLAYERS TABLE (with simple role and password fields for future login)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        player_id INTEGER PRIMARY KEY AUTOINCREMENT,
        display_name TEXT NOT NULL UNIQUE,
        password_hash TEXT,
        role TEXT DEFAULT 'player', -- 'admin' or 'player'
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. COMMANDERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS commanders (
        commander_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        color_identity TEXT NOT NULL -- e.g., 'WB', 'UR', 'WUBRG'
    );
    """)

    # 3. DECKS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decks (
        deck_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER REFERENCES players(player_id) ON DELETE CASCADE,
        deck_name TEXT NOT NULL,
        archived BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. DECK_COMMANDERS (Bridge table for Partner/Background decks)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deck_commanders (
        deck_id INTEGER REFERENCES decks(deck_id) ON DELETE CASCADE,
        commander_id INTEGER REFERENCES commanders(commander_id) ON DELETE CASCADE,
        PRIMARY KEY (deck_id, commander_id)
    );
    """)

    # 5. GAMES TABLE (Match headers)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS games (
        game_id INTEGER PRIMARY KEY AUTOINCREMENT,
        played_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        total_turns INTEGER,
        duration_minutes INTEGER,
        win_condition TEXT,
        notes TEXT
    );
    """)

    # 6. GAME_PARTICIPANTS TABLE (Granular results per seat)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS game_participants (
        game_id INTEGER REFERENCES games(game_id) ON DELETE CASCADE,
        player_id INTEGER REFERENCES players(player_id),
        deck_id INTEGER REFERENCES decks(deck_id),
        seat_position INTEGER CHECK (seat_position BETWEEN 1 AND 6),
        mulligan_count INTEGER DEFAULT 0,
        is_winner BOOLEAN DEFAULT 0,
        PRIMARY KEY (game_id, player_id)
    );
    """)

    conn.commit()
    print("Database tables created successfully.")

    # --- SEED DATA ---
    # Add initial players (Defaulting your user as admin)
    sample_players = [
        ("YourName", "admin"),
        ("Alice", "player"),
        ("Bob", "player"),
        ("Charlie", "player")
    ]
    
    for name, role in sample_players:
        cursor.execute(
            "INSERT OR IGNORE INTO players (display_name, role) VALUES (?, ?);", 
            (name, role)
        )

    # Add sample commanders
    sample_commanders = [
        ("Teysa Karlov", "WB"),
        ("Stella Lee, Wild Card", "UR"),
        ("Atraxa, Praetors' Voice", "GWUB"),
        ("The Ur-Dragon", "WUBRG")
    ]

    for comm_name, colors in sample_commanders:
        cursor.execute(
            "INSERT OR IGNORE INTO commanders (name, color_identity) VALUES (?, ?);", 
            (comm_name, colors)
        )

    conn.commit()
    conn.close()
    print("Seed data inserted successfully.")

if __name__ == "__main__":
    init_database()
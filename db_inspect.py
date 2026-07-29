import sqlite3
import pandas as pd

DB_NAME = "edh_tracker.db"

def inspect_database():
    # Connect to the local database
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Query sqlite_master to find the names of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"\n{'='*50}")
    print(f" EXPLORING DATABASE: {DB_NAME}")
    print(f"{'='*50}")
    
    for table_tuple in tables:
        table_name = table_tuple[0]
        
        # Skip SQLite's internal tracking table
        if table_name == 'sqlite_sequence':
            continue
            
        print(f"\n\n--- TABLE: {table_name.upper()} ---")
        
        # 1. Fetch and print the column names using PRAGMA
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        # The column name is the 2nd item (index 1) in the PRAGMA result
        col_names = [col[1] for col in columns] 
        print(f"Columns: {', '.join(col_names)}\n")
        
        # 2. Fetch and print the first 5 rows using Pandas for clean CLI formatting
        query = f"SELECT * FROM {table_name} LIMIT 5;"
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            print("  (Table is empty)")
        else:
            # .to_string() prints the dataframe cleanly without truncating columns
            print(df.to_string(index=False))
            
    conn.close()
    print(f"\n{'='*50}\n")

if __name__ == "__main__":
    inspect_database()
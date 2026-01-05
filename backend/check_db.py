"""Quick script to check database contents."""

import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent / "selenite.db"
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Check what tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Tables in database: {[t[0] for t in tables]}")

# Check if jobs table exists
if any(t[0] == "jobs" for t in tables):
    cursor.execute("SELECT COUNT(*) FROM jobs")
    count = cursor.fetchone()[0]
    print(f"Jobs in DB: {count}")

    if count > 0:
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Jobs table columns: {columns}")

        cursor.execute("SELECT * FROM jobs LIMIT 3")
        for row in cursor.fetchall():
            print(f"  Row: {row[:5]}...")  # Print first 5 fields
else:
    print("Jobs table does not exist - database needs to be initialized")

conn.close()

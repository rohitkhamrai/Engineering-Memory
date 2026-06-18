import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.database.connection import engine

def migrate():
    with engine.connect() as conn:
        try:
            # Add repository column to chunks
            conn.execute(text("ALTER TABLE chunks ADD COLUMN repository VARCHAR DEFAULT 'httpx'"))
            print("Added 'repository' column to chunks.")
        except Exception as e:
            print("Failed to add 'repository' column (might already exist):", str(e))
            
        try:
            # Backfill existing chunks
            conn.execute(text("UPDATE chunks SET repository = 'httpx' WHERE repository IS NULL"))
            print("Backfilled chunks with repository='httpx'.")
        except Exception as e:
            print("Failed to backfill chunks:", str(e))

        try:
            # Add columns to ingestion_jobs
            conn.execute(text("ALTER TABLE ingestion_jobs ADD COLUMN error_message VARCHAR"))
            conn.execute(text("ALTER TABLE ingestion_jobs ADD COLUMN started_at TIMESTAMP"))
            conn.execute(text("ALTER TABLE ingestion_jobs ADD COLUMN completed_at TIMESTAMP"))
            print("Added error_message, started_at, completed_at to ingestion_jobs.")
        except Exception as e:
            print("Failed to add columns to ingestion_jobs (might already exist):", str(e))
            
        conn.commit()

if __name__ == "__main__":
    migrate()

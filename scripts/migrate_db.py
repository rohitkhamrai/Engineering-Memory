import sys
import os

# Add root to pythonpath
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.database.connection import SessionLocal, engine
from app.database.models import Base

def migrate():
    print("Starting migration...")
    session = SessionLocal()
    
    try:
        session.execute(text("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS heading VARCHAR;"))
        session.execute(text("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS parent_heading VARCHAR;"))
        session.execute(text("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS doc_type VARCHAR;"))
        
        print("Truncating chunks table to prepare for re-ingestion...")
        session.execute(text("TRUNCATE TABLE chunks;"))
        
        session.commit()
        print("Columns added and table truncated successfully.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        session.rollback()
    finally:
        session.close()

    print("Creating new tables (IngestionJob)...")
    Base.metadata.create_all(bind=engine)
    print("Migration complete.")

if __name__ == "__main__":
    migrate()

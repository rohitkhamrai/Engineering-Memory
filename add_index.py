from sqlalchemy import text
from app.database.connection import SessionLocal

def create_index():
    session = SessionLocal()
    try:
        print("Creating HNSW index on chunks table...")
        session.execute(text("CREATE INDEX IF NOT EXISTS ix_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"))
        session.commit()
        print("Index created successfully!")
    except Exception as e:
        session.rollback()
        print(f"Error creating index: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    create_index()

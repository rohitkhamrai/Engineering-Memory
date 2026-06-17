import os
import json
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.models import Chunk, ChunkType, Incident
from app.database.connection import SessionLocal
from app.ingestion.embeddings import generate_embedding

HTTPX_REPO_DIR = Path("data/httpx")
ISSUES_FILE = Path("data/issues.json")

def process_python_file(file_path: Path, session: Session):
    try:
        content = file_path.read_text(encoding="utf-8")
        # Basic chunking: split by classes/functions or just paragraphs
        # For simplicity in MVP, we split by double newlines if it's too large
        # but storing the whole file is fine if it's small.
        # A better approach is AST parsing, but we'll use a naive chunker here.
        chunks = [c for c in content.split("\n\n") if len(c.strip()) > 50]
        
        for i, chunk_text in enumerate(chunks):
            embedding = generate_embedding(chunk_text)
            # Create chunk
            db_chunk = Chunk(
                content=chunk_text,
                type=ChunkType.CODE,
                source_file=str(file_path.relative_to(HTTPX_REPO_DIR)),
                start_line=i * 10, # rough estimate
                embedding=embedding
            )
            session.add(db_chunk)
        session.commit() # Commit per file to avoid large transactions
            
    except Exception as e:
        print(f"Failed to process {file_path}: {e}")

def process_markdown_file(file_path: Path, session: Session):
    try:
        content = file_path.read_text(encoding="utf-8")
        chunks = [c for c in content.split("\n\n") if len(c.strip()) > 50]
        
        for i, chunk_text in enumerate(chunks):
            embedding = generate_embedding(chunk_text)
            db_chunk = Chunk(
                content=chunk_text,
                type=ChunkType.DOC,
                source_file=str(file_path.relative_to(HTTPX_REPO_DIR)),
                start_line=i * 5,
                embedding=embedding
            )
            session.add(db_chunk)
        session.commit() # Commit per file to avoid large transactions
    except Exception as e:
        print(f"Failed to process {file_path}: {e}")

def load_issues(session: Session):
    if not ISSUES_FILE.exists():
        print("No issues.json found.")
        return
    
    with open(ISSUES_FILE, "r", encoding="utf-8") as f:
        issues = json.load(f)
        
    for issue in issues:
        # Save to incidents table
        db_incident = Incident(
            symptom=issue.get("symptom", ""),
            cause=issue.get("cause", ""),
            fix=issue.get("fix", ""),
            issue_url=issue.get("issue_url", ""),
            commit_sha=issue.get("commit_sha", "")
        )
        session.add(db_incident)
        session.flush() # get ID
        
        # Also save as a searchable chunk
        chunk_content = f"Symptom: {db_incident.symptom}\nCause: {db_incident.cause}\nFix: {db_incident.fix}"
        embedding = generate_embedding(chunk_content)
        db_chunk = Chunk(
            content=chunk_content,
            type=ChunkType.ISSUE,
            source_file=f"Issue: {db_incident.issue_url}",
            embedding=embedding
        )
        session.add(db_chunk)

def update_fts_vectors(session: Session):
    # Update the tsvector column using the English dictionary
    session.execute(text("""
        UPDATE chunks SET fts_vector = to_tsvector('english', content);
    """))

def ingest_all():
    session = SessionLocal()
    try:
        print("Processing Python and Markdown files...")
        for root, _, files in os.walk(HTTPX_REPO_DIR):
            for file in files:
                file_path = Path(root) / file
                if file.endswith(".py"):
                    process_python_file(file_path, session)
                elif file.endswith(".md"):
                    process_markdown_file(file_path, session)
        
        print("Processing issues...")
        load_issues(session)
        
        print("Committing chunks to database...")
        session.commit()
        
        print("Updating FTS vectors...")
        update_fts_vectors(session)
        session.commit()
        print("Ingestion complete.")
    finally:
        session.close()

if __name__ == "__main__":
    from app.database.connection import engine, Base
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    ingest_all()

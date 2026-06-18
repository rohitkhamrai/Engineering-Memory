import os
import json
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.models import Chunk, ChunkType, Incident, IngestionJob
from app.database.connection import SessionLocal
from app.ingestion.embeddings import generate_embedding

HTTPX_REPO_DIR = Path("data/httpx")
ISSUES_FILE = Path("data/issues.json")

def process_python_file(file_path: Path, session: Session, repository: str, base_dir: Path):
    try:
        content = file_path.read_text(encoding="utf-8")
        chunks = [c for c in content.split("\n\n") if len(c.strip()) > 50]
        
        for i, chunk_text in enumerate(chunks):
            embedding = generate_embedding(chunk_text)
            db_chunk = Chunk(
                content=chunk_text,
                type=ChunkType.CODE,
                source_file=str(file_path.relative_to(base_dir)),
                repository=repository,
                start_line=i * 10,
                embedding=embedding
            )
            session.add(db_chunk)
        session.commit()
            
    except Exception as e:
        print(f"Failed to process {file_path}: {e}")

def parse_markdown(content: str):
    chunks = []
    current_h1 = ""
    current_h2 = ""
    current_h3 = ""
    current_chunk_lines = []
    
    def finalize_chunk():
        if current_chunk_lines:
            text = "\n".join(current_chunk_lines).strip()
            if len(text) > 20:
                parent = current_h2 if current_h3 else current_h1
                heading = current_h3 or current_h2 or current_h1
                chunks.append({
                    "heading": heading,
                    "parent_heading": parent,
                    "content": text
                })
            current_chunk_lines.clear()

    in_code_block = False
    for line in content.split("\n"):
        if line.startswith("```"):
            in_code_block = not in_code_block
            current_chunk_lines.append(line)
            continue
            
        if not in_code_block:
            if line.startswith("# "):
                finalize_chunk()
                current_h1 = line[2:].strip()
                current_h2 = ""
                current_h3 = ""
                current_chunk_lines.append(line)
            elif line.startswith("## "):
                finalize_chunk()
                current_h2 = line[3:].strip()
                current_h3 = ""
                current_chunk_lines.append(line)
            elif line.startswith("### "):
                finalize_chunk()
                current_h3 = line[4:].strip()
                current_chunk_lines.append(line)
            else:
                current_chunk_lines.append(line)
        else:
            current_chunk_lines.append(line)
            
    finalize_chunk()
    return chunks

def process_markdown_file(file_path: Path, session: Session, repository: str, base_dir: Path):
    try:
        content = file_path.read_text(encoding="utf-8")
        parsed_chunks = parse_markdown(content)
        
        for i, chunk_data in enumerate(parsed_chunks):
            chunk_text = chunk_data["content"]
            embedding = generate_embedding(chunk_text)
            db_chunk = Chunk(
                content=chunk_text,
                type=ChunkType.DOC,
                source_file=str(file_path.relative_to(base_dir)),
                repository=repository,
                start_line=i * 5,
                embedding=embedding,
                heading=chunk_data["heading"],
                parent_heading=chunk_data["parent_heading"],
                doc_type="documentation"
            )
            session.add(db_chunk)
        session.commit()
    except Exception as e:
        print(f"Failed to process {file_path}: {e}")

def update_fts_vectors(session: Session, repository: str):
    session.execute(text("""
        UPDATE chunks SET fts_vector = to_tsvector('english', content)
        WHERE repository = :repository AND fts_vector IS NULL;
    """), {"repository": repository})
    session.commit()

def run_github_ingestion(job_id: int, repo_url: str, owner_repo: str):
    session = SessionLocal()
    job = session.query(IngestionJob).filter_by(id=job_id).first()
    if not job:
        session.close()
        return

    job.status = "cloning"
    job.started_at = datetime.utcnow()
    session.commit()
    
    target_dir = Path(f"data/repos/{job_id}")
    try:
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Clone
        subprocess.run(["git", "clone", "--depth", "1", repo_url, str(target_dir)], check=True, timeout=300, capture_output=True)
        
        job.status = "parsing"
        session.commit()
        
        # Parse & Embed
        for root, dirs, files in os.walk(target_dir):
            if ".git" in dirs:
                dirs.remove(".git")
            for file in files:
                file_path = Path(root) / file
                if file.endswith(".py"):
                    process_python_file(file_path, session, repository=owner_repo, base_dir=target_dir)
                elif file.endswith(".md"):
                    process_markdown_file(file_path, session, repository=owner_repo, base_dir=target_dir)
        
        job.status = "embedding"
        session.commit()
        
        # FTS Update
        update_fts_vectors(session, repository=owner_repo)
        
        # Post Ingest Smoke Test
        from app.retrieval.search import hybrid_search
        smoke = hybrid_search("What is this repository?", session, repository=owner_repo, top_k=1)
        if len(smoke) == 0:
            job.status = "failed"
            job.error_message = "Smoke test failed: 0 citations retrieved."
            shutil.rmtree(target_dir)
        else:
            job.status = "ready"
            job.completed_at = datetime.utcnow()
            if target_dir.exists():
                shutil.rmtree(target_dir)
            
    except subprocess.TimeoutExpired:
        job.status = "failed"
        job.error_message = "Git clone timed out after 300s."
        if target_dir.exists():
            shutil.rmtree(target_dir)
    except subprocess.CalledProcessError as e:
        job.status = "failed"
        job.error_message = f"Git clone failed: {e.stderr.decode('utf-8', errors='ignore')}"
        if target_dir.exists():
            shutil.rmtree(target_dir)
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        if target_dir.exists():
            shutil.rmtree(target_dir)
    finally:
        session.commit()
        session.close()

def load_issues(session: Session):
    if not ISSUES_FILE.exists():
        return
    
    with open(ISSUES_FILE, "r", encoding="utf-8") as f:
        issues = json.load(f)
        
    for issue in issues:
        db_incident = Incident(
            symptom=issue.get("symptom", ""),
            cause=issue.get("cause", ""),
            fix=issue.get("fix", ""),
            issue_url=issue.get("issue_url", ""),
            commit_sha=issue.get("commit_sha", "")
        )
        session.add(db_incident)
        session.flush()
        
        chunk_content = f"Symptom: {db_incident.symptom}\nCause: {db_incident.cause}\nFix: {db_incident.fix}"
        embedding = generate_embedding(chunk_content)
        db_chunk = Chunk(
            content=chunk_content,
            type=ChunkType.ISSUE,
            source_file=f"Issue: {db_incident.issue_url}",
            repository="httpx",
            embedding=embedding
        )
        session.add(db_chunk)

def ingest_all():
    session = SessionLocal()
    try:
        print("Processing Python and Markdown files...")
        for root, _, files in os.walk(HTTPX_REPO_DIR):
            for file in files:
                file_path = Path(root) / file
                if file.endswith(".py"):
                    process_python_file(file_path, session, "httpx", HTTPX_REPO_DIR)
                elif file.endswith(".md"):
                    process_markdown_file(file_path, session, "httpx", HTTPX_REPO_DIR)
        
        print("Processing issues...")
        load_issues(session)
        
        print("Committing chunks to database...")
        session.commit()
        
        print("Updating FTS vectors...")
        session.execute(text("UPDATE chunks SET fts_vector = to_tsvector('english', content)"))
        session.commit()
        print("Ingestion complete.")
    finally:
        session.close()

if __name__ == "__main__":
    from app.database.connection import engine, Base
    Base.metadata.create_all(bind=engine)
    ingest_all()

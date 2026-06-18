import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.loader import run_github_ingestion
from app.database.models import IngestionJob
from app.database.connection import SessionLocal

def test():
    session = SessionLocal()
    # 1. Create Job
    job = IngestionJob(
        repo_url="https://github.com/tiangolo/fastapi",
        status="queued"
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    
    print(f"Job created: {job.id}")
    
    # 2. Run ingestion (blocking for test)
    print("Running ingestion (will take a minute...)")
    run_github_ingestion(job.id, "https://github.com/tiangolo/fastapi", "tiangolo_fastapi")
    
    # 3. Check status
    session.refresh(job)
    print(f"Status: {job.status}")
    if job.status == "failed":
        print(f"Error: {job.error_message}")
        
    # 4. S5: Clone isolation filesystem audit
    import pathlib
    repo_dir = pathlib.Path(f"data/repos/{job.id}")
    print(f"data/repos/{job.id} exists: {repo_dir.exists()}")
    
    httpx_dir = pathlib.Path("data/httpx")
    print(f"data/httpx exists: {httpx_dir.exists()}")
    
    # 5. Check UI Dropdown values now
    from sqlalchemy import text
    res = session.execute(text("SELECT repository, count(*) FROM chunks GROUP BY repository")).fetchall()
    print("Repos in DB:")
    for r in res:
        print(f" - {r[0]}: {r[1]} chunks")
        
    session.close()

if __name__ == "__main__":
    test()

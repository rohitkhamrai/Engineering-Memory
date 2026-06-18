import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.connection import SessionLocal
from sqlalchemy import text

def check():
    session = SessionLocal()
    # Check ingestion jobs
    jobs = session.execute(text("SELECT id, status, repo_url, error_message FROM ingestion_jobs ORDER BY id DESC LIMIT 1")).fetchall()
    if jobs:
        print(f"Latest Job: ID {jobs[0][0]}, Status {jobs[0][1]}, URL {jobs[0][2]}")
        if jobs[0][3]:
            print(f"Error: {jobs[0][3]}")
            
    # Check chunk counts
    counts = session.execute(text("SELECT repository, count(*) FROM chunks GROUP BY repository")).fetchall()
    print("\nChunk Counts:")
    for repo, count in counts:
        print(f" - {repo}: {count} chunks")
        
    session.close()

if __name__ == "__main__":
    check()

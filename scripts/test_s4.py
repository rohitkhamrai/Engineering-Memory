import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.connection import SessionLocal
from app.retrieval.search import hybrid_search

def test_s4():
    session = SessionLocal()
    question = "How do I create a FastAPI application?"
    
    print(f"Question: {question}")
    
    print("\n[tiangolo_fastapi]")
    res_fastapi = hybrid_search(question, session, repository="tiangolo_fastapi", top_k=5)
    for c in res_fastapi:
        print(f" - [{c['type']}] {c['source_file']}")
        
    print("\n[httpx]")
    res_httpx = hybrid_search(question, session, repository="httpx", top_k=5)
    for c in res_httpx:
        print(f" - [{c['type']}] {c['source_file']}")
        
    session.close()

if __name__ == "__main__":
    test_s4()

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

def run_verifications():
    print("--- S7: URL VALIDATION ---")
    bad_urls = [
        "file:///etc/passwd",
        "git@github.com:owner/repo.git",
        "https://google.com"
    ]
    for url in bad_urls:
        res = client.post("/api/ingest", json={"repo_url": url})
        print(f"URL: {url} -> Status: {res.status_code}")
        assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    
    good_url = "https://github.com/tiangolo/fastapi"
    # We won't actually ingest here via client because background task runs.
    # We will just verify it accepts it and queues it.
    print(f"URL: {good_url} -> (Will test via actual ingestion)")

    print("\n--- S6: FAILURE PATH ---")
    res = client.post("/api/ingest", json={"repo_url": "https://github.com/fake-owner/fake-repo"})
    print(f"Fake Repo Ingest -> Status: {res.status_code}")
    # GitHub API will return 404
    assert res.status_code == 404, f"Expected 404, got {res.status_code}"
    print(f"Error detail: {res.json().get('detail')}")

    print("\n--- S3: REPO DROPDOWN ---")
    res = client.get("/api/repos")
    print(f"Repos: {res.json()}")
    assert len(res.json()) >= 1

    print("\n--- S4: REPO ISOLATION ---")
    # Query against HTTPX
    res_httpx = client.post("/api/ask", json={"question": "How does dependency injection work?", "repository": "httpx"})
    print(f"HTTPX Citations for DI: {[c['source_file'] for c in res_httpx.json()['citations']]}")
    
    # Query against FastAPI (even if empty right now, should return 0)
    res_fastapi = client.post("/api/ask", json={"question": "How does dependency injection work?", "repository": "tiangolo_fastapi"})
    print(f"FastAPI Citations for DI: {[c['source_file'] for c in res_fastapi.json()['citations']]}")
    
    print("\nVerifications completed successfully.")

if __name__ == "__main__":
    run_verifications()

import os
import httpx
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.database.connection import get_db
from app.database.models import IngestionJob, Chunk
from app.retrieval.search import hybrid_search
from app.retrieval.evidence import compute_confidence, ConfidenceLevel
from app.ingestion.loader import run_github_ingestion
from sqlalchemy import func
import re

app = FastAPI(title="Engineering Memory API")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct")

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    repository: str = "httpx"

class IngestRequest(BaseModel):
    repo_url: str

class Citation(BaseModel):
    id: int
    source_file: str
    type: str

class QueryResponse(BaseModel):
    answer: str
    confidence: ConfidenceLevel
    citations: List[Citation]

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

async def generate_llm_answer(question: str, context: str) -> str:
    if not GROQ_API_KEY:
        return "Error: GROQ_API_KEY is not set."
        
    prompt = f"""You are Engineering Memory, a precise technical assistant.
Answer the question based ONLY on the provided context. If the context does not contain the answer, say so. Do not hallucinate.

Context:
{context}

Question:
{question}

Answer:"""
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False
                },
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM Generation failed: {str(e)}")

@app.post("/api/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest, db: Session = Depends(get_db)):
    # 1. Retrieve Context
    results = hybrid_search(request.question, db, repository=request.repository, top_k=request.top_k)
    
    if not results:
        return QueryResponse(
            answer=f"No relevant context found in repository '{request.repository}'.",
            confidence=ConfidenceLevel.UNKNOWN,
            citations=[]
        )
    
    # 2. Compute Evidence Confidence
    source_types = [doc["type"] for doc in results]
    confidence = compute_confidence(source_types)
    
    if confidence == ConfidenceLevel.UNKNOWN:
        return QueryResponse(
            answer="Insufficient evidence to provide a confident answer.",
            confidence=confidence,
            citations=[]
        )
    
    # 3. Prepare Context for LLM
    context_blocks = []
    citations = []
    for doc in results:
        citations.append(Citation(id=doc["id"], source_file=doc["source_file"], type=doc["type"]))
        context_blocks.append(f"[{doc['type']} - {doc['source_file']}]\n{doc['content']}\n")
    
    full_context = "\n".join(context_blocks)
    
    # 4. Generate Answer
    answer = await generate_llm_answer(request.question, full_context)
    
    return QueryResponse(
        answer=answer,
        confidence=confidence,
        citations=citations
    )

from fastapi import BackgroundTasks, Header

@app.post("/api/ingest")
async def ingest_repository(
    request: IngestRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None)
):
    expected_secret = os.getenv("INGEST_SECRET")
    if expected_secret and x_api_key != expected_secret:
        raise HTTPException(status_code=401, detail="Invalid X-API-Key header")
        
    url = request.repo_url.strip()
    m = re.match(r"^https://github\.com/([^/]+)/([^/]+)/?$", url)
    if not m:
        raise HTTPException(status_code=400, detail="URL must be exactly https://github.com/<owner>/<repo>")
        
    owner, repo = m.group(1), m.group(2).replace(".git", "")
    owner_repo = f"{owner}_{repo}"
    
    # Check repo size using GitHub API
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"https://api.github.com/repos/{owner}/{repo}", timeout=10.0)
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail="Repository not found or is private.")
            resp.raise_for_status()
            size_kb = resp.json().get("size", 0)
            if size_kb > 100 * 1024:
                raise HTTPException(status_code=400, detail="Repository too large. Limit is 100MB.")
        except httpx.RequestError:
            pass # ignore network errors to GitHub API for size check
            
    # Create Job
    job = IngestionJob(
        repo_url=url,
        status="queued"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    background_tasks.add_task(run_github_ingestion, job.id, url, owner_repo)
    return {"job_id": job.id, "repository_id": owner_repo, "status": "queued"}

@app.get("/api/ingest/status/{job_id}")
async def get_ingest_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "status": job.status,
        "error_message": job.error_message,
        "started_at": job.started_at,
        "completed_at": job.completed_at
    }

@app.get("/api/repos")
async def list_repositories(db: Session = Depends(get_db)):
    repos = db.query(Chunk.repository, func.count(Chunk.id)).group_by(Chunk.repository).all()
    return [{"name": r[0], "chunks": r[1]} for r in repos]

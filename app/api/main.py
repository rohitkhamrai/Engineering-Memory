import os
import httpx
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.database.connection import get_db
from app.retrieval.search import hybrid_search
from app.retrieval.evidence import compute_confidence, ConfidenceLevel

app = FastAPI(title="Engineering Memory API")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct")

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5

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
    results = hybrid_search(request.question, db, top_k=request.top_k)
    
    if not results:
        return QueryResponse(
            answer="No relevant context found in the codebase or issues.",
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

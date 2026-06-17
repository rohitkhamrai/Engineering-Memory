from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.models import Chunk
from app.ingestion.embeddings import generate_embedding
from typing import List, Dict, Any

def vector_search(query: str, session: Session, top_k: int = 20) -> List[Dict[str, Any]]:
    query_embedding = generate_embedding(query)
    
    # Global retrieval
    sql = text("""
        SELECT id, content, type, source_file, embedding <=> CAST(:query_embedding AS vector) AS distance 
        FROM chunks 
        ORDER BY distance 
        LIMIT :top_k
    """)
    
    results = session.execute(sql, {"query_embedding": str(query_embedding), "top_k": top_k}).fetchall()
    
    return [
        {
            "id": r.id,
            "content": r.content,
            "type": r.type,
            "source_file": r.source_file,
            "score": 1.0 - r.distance # rough similarity
        }
        for r in results
    ]

def fts_search(query: str, session: Session, top_k: int = 20) -> List[Dict[str, Any]]:
    # Global retrieval
    sql = text("""
        SELECT id, content, type, source_file, ts_rank(fts_vector, websearch_to_tsquery('english', :query)) AS rank 
        FROM chunks 
        WHERE fts_vector @@ websearch_to_tsquery('english', :query) 
        ORDER BY rank DESC 
        LIMIT :top_k
    """)
    
    results = session.execute(sql, {"query": query, "top_k": top_k}).fetchall()
    
    return [
        {
            "id": r.id,
            "content": r.content,
            "type": r.type,
            "source_file": r.source_file,
            "score": r.rank
        }
        for r in results
    ]

def hybrid_search(query: str, session: Session, top_k: int = 5) -> List[Dict[str, Any]]:
    vector_results = vector_search(query, session, top_k=20)
    fts_results = fts_search(query, session, top_k=20)
    
    # Reciprocal Rank Fusion (RRF)
    K = 60
    scores = {}
    docs = {}
    
    for rank, doc in enumerate(vector_results):
        doc_id = doc["id"]
        docs[doc_id] = doc
        scores[doc_id] = scores.get(doc_id, 0) + (1.0 / (K + rank + 1))
        
    for rank, doc in enumerate(fts_results):
        doc_id = doc["id"]
        docs[doc_id] = doc
        scores[doc_id] = scores.get(doc_id, 0) + (1.0 / (K + rank + 1))
        
    # Sort by RRF score descending
    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # Source diversification (honest approach)
    # Rule: max 2 DOC, max 2 CODE, max 1 ISSUE
    type_counts = {"DOC": 0, "CODE": 0, "ISSUE": 0}
    max_counts = {"DOC": 2, "CODE": 2, "ISSUE": 1}
    
    final_docs = []
    
    # Filter highly relevant documents while enforcing diversity caps
    for doc_id, score in sorted_docs:
        if len(final_docs) >= top_k:
            break
            
        doc = docs[doc_id]
        doc_type = doc["type"]
        
        if type_counts.get(doc_type, 0) < max_counts.get(doc_type, 2):
            doc["rrf_score"] = score
            final_docs.append(doc)
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            
    # If we haven't reached top_k due to caps (rare, but possible if only one type was retrieved),
    # we can fall back to adding remaining top docs regardless of type to fill context.
    if len(final_docs) < top_k:
        for doc_id, score in sorted_docs:
            if len(final_docs) >= top_k:
                break
            if not any(d["id"] == doc_id for d in final_docs):
                doc = docs[doc_id]
                doc["rrf_score"] = score
                final_docs.append(doc)
            
    return final_docs

import sys
from app.database.connection import SessionLocal
from app.retrieval.search import vector_search, fts_search, hybrid_search

def trace_query(query: str):
    session = SessionLocal()
    
    print(f"=== QUERY TRACE: '{query}' ===\n")
    
    print("--- VECTOR SEARCH TOP 20 ---")
    v_results = vector_search(query, session, top_k=20)
    v_dict = {}
    for i, r in enumerate(v_results):
        v_dict[r['id']] = i + 1
        print(f"{i+1:2d}. [ID: {r['id']}] {r['type']:5s} | {r['source_file'][:40]} | Score: {r['score']:.4f}")
        
    print("\n--- FTS SEARCH TOP 20 ---")
    f_results = fts_search(query, session, top_k=20)
    f_dict = {}
    for i, r in enumerate(f_results):
        f_dict[r['id']] = i + 1
        print(f"{i+1:2d}. [ID: {r['id']}] {r['type']:5s} | {r['source_file'][:40]} | Rank: {r['score']:.4f}")
        
    print("\n--- HYBRID RRF FINAL SELECTION ---")
    # We will replicate the RRF scoring to see the raw ranks
    K = 60
    scores = {}
    docs = {}
    for rank, doc in enumerate(v_results):
        docs[doc["id"]] = doc
        scores[doc["id"]] = scores.get(doc["id"], 0) + (1.0 / (K + rank + 1))
    for rank, doc in enumerate(f_results):
        docs[doc["id"]] = doc
        scores[doc["id"]] = scores.get(doc["id"], 0) + (1.0 / (K + rank + 1))
        
    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    for i, (doc_id, score) in enumerate(sorted_docs[:20]):
        doc = docs[doc_id]
        v_rank = v_dict.get(doc_id, "Miss")
        f_rank = f_dict.get(doc_id, "Miss")
        print(f"RRF {i+1:2d}. [ID: {doc_id}] {doc['type']:5s} | {doc['source_file'][:35]:35s} | RRF Score: {score:.4f} (Vector: {v_rank}, FTS: {f_rank})")
        
    session.close()

if __name__ == "__main__":
    trace_query("What is the difference between the data and json kwargs")

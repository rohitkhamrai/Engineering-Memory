import os
import json
import time
from collections import defaultdict
from pathlib import Path
from app.database.connection import SessionLocal
from app.retrieval.search import hybrid_search

EVAL_FILE = Path("data/50_questions.json")

def run_retrieval_benchmark():
    with open(EVAL_FILE, "r") as f:
        questions = json.load(f)

    session = SessionLocal()
    total_questions = len(questions)
    
    metrics = {
        "overall": {"hit3": 0, "hit5": 0, "latencies": []},
        "difficulty": defaultdict(lambda: {"total": 0, "hit3": 0, "hit5": 0}),
        "category": defaultdict(lambda: {"total": 0, "hit3": 0, "hit5": 0}),
        "generation": defaultdict(lambda: {"total": 0, "hit3": 0, "hit5": 0}),
        "evidence_match": {"DOC": {"total": 0, "hit": 0}, "CODE": {"total": 0, "hit": 0}, "ISSUE": {"total": 0, "hit": 0}}
    }

    try:
        for q in questions:
            question_text = q["question"]
            acceptable_sources = [s.replace("\\", "/") for s in q.get("acceptable_sources", [])]
            expected_evidence = q.get("expected_evidence", [])
            difficulty = q.get("difficulty", "unknown")
            category = q.get("category", "unknown")
            gen_type = q.get("generation_type", "synthetic")

            metrics["difficulty"][difficulty]["total"] += 1
            metrics["category"][category]["total"] += 1
            metrics["generation"][gen_type]["total"] += 1

            start_time = time.time()
            
            # Pure retrieval call - no LLM
            results = hybrid_search(question_text, session, repository="httpx", top_k=5)
            
            latency = time.time() - start_time
            metrics["overall"]["latencies"].append(latency)

            # Check Hit@3 and Hit@5 against acceptable sources
            hit_rank = -1
            for rank, doc in enumerate(results):
                doc_source_normalized = doc["source_file"].replace("\\", "/")
                if any(acc in doc_source_normalized for acc in acceptable_sources):
                    hit_rank = rank + 1
                    break
            
            if hit_rank > 0 and hit_rank <= 3:
                metrics["overall"]["hit3"] += 1
                metrics["difficulty"][difficulty]["hit3"] += 1
                metrics["category"][category]["hit3"] += 1
                metrics["generation"][gen_type]["hit3"] += 1
                
            if hit_rank > 0 and hit_rank <= 5:
                metrics["overall"]["hit5"] += 1
                metrics["difficulty"][difficulty]["hit5"] += 1
                metrics["category"][category]["hit5"] += 1
                metrics["generation"][gen_type]["hit5"] += 1
                
            # Evidence Type Match Rate (checking top 3)
            retrieved_types = set(d["type"] for d in results[:3])
            for ev in expected_evidence:
                metrics["evidence_match"][ev]["total"] += 1
                if ev in retrieved_types:
                    metrics["evidence_match"][ev]["hit"] += 1

            print(f"[{gen_type[:3].upper()}] Q: {question_text[:40]}... | Hit@3: {'Yes' if (0 < hit_rank <= 3) else 'No'} | Rank: {hit_rank if hit_rank > 0 else 'Miss'}")
            
    finally:
        session.close()

    # Print summary
    latencies = metrics["overall"]["latencies"]
    if latencies:
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95) - 1]
        print(f"\n--- Final Pure Retrieval Benchmark Report ---")
        print(f"Overall:")
        print(f"  Total Questions: {total_questions}")
        print(f"  Hit@3: {metrics['overall']['hit3']/total_questions*100:.1f}%")
        print(f"  Hit@5: {metrics['overall']['hit5']/total_questions*100:.1f}%")
        print(f"  Retrieval Latency P95: {p95_latency:.4f}s")
        
        print(f"\nBy Generation Type (Hit@3):")
        for gen, data in metrics["generation"].items():
            if data['total'] > 0:
                print(f"  {gen.capitalize()} = {data['hit3']/data['total']*100:.1f}% Hit@3 | {data['hit5']/data['total']*100:.1f}% Hit@5")

        print(f"\nBy Category (Hit@3):")
        for cat, data in metrics["category"].items():
            if data['total'] > 0:
                print(f"  {cat.capitalize()} = {data['hit3']/data['total']*100:.1f}% Hit@3")
                
        print(f"\nEvidence Precision:")
        for ev, data in metrics["evidence_match"].items():
            if data['total'] > 0:
                print(f"  {ev} = {data['hit']/data['total']*100:.1f}% Match Rate")

if __name__ == "__main__":
    run_retrieval_benchmark()

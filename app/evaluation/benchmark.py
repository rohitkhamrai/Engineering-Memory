import os
import json
import time
import requests
import csv
from collections import defaultdict
from pathlib import Path
from app.database.connection import SessionLocal
from app.database.models import EvalResult

API_URL = "http://localhost:8000/api/ask"
EVAL_FILE = Path("data/50_questions.json")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def evaluate_answer_correctness(question: str, answer: str, citations: list, key_facts: list) -> int:
    if not GROQ_API_KEY:
        return 0
        
    prompt = f"""Evaluate the generated answer based on whether it correctly conveys the required Key Facts.

Question:
{question}

Generated Answer:
{answer}

Key Facts Required:
{json.dumps(key_facts, indent=2)}

Retrieved Citations:
{json.dumps(citations, indent=2)}

Grade:
1. Does the answer convey the essential meaning of the Key Facts?
2. Does the answer contradict known facts?
3. Final verdict: PASS/FAIL

Return JSON only in the following format:
{{
    "contains_key_facts": true/false,
    "contradicts_known_facts": true/false,
    "verdict": "PASS"
}}
"""
    try:
        # Rate limit protection for Groq Free Tier
        time.sleep(2.5)
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.0
            },
            timeout=15
        )
        response.raise_for_status()
        result = response.json()
        content = json.loads(result["choices"][0]["message"]["content"])
        return 1 if content.get("verdict") == "PASS" else 0
    except Exception as e:
        print(f"LLM Judge Error: {e}")
        return 0

def run_benchmark():
    with open(EVAL_FILE, "r") as f:
        questions = json.load(f)

    session = SessionLocal()
    total_questions = len(questions)
    
    metrics = {
        "overall": {"hit": 0, "ans": 0, "latencies": []},
        "difficulty": defaultdict(lambda: {"total": 0, "hit": 0, "ans": 0}),
        "category": defaultdict(lambda: {"total": 0, "hit": 0, "ans": 0}),
        "generation": defaultdict(lambda: {"total": 0, "hit": 0, "ans": 0}),
        "evidence_match": {"DOC": {"total": 0, "hit": 0}, "CODE": {"total": 0, "hit": 0}, "ISSUE": {"total": 0, "hit": 0}},
        "failures": {"retrieval": 0, "reasoning": 0, "judge": 0}
    }
    
    audit_rows = []

    try:
        for q in questions:
            question_text = q["question"]
            acceptable_sources = [s.replace("\\", "/") for s in q.get("acceptable_sources", [])]
            expected_evidence = q.get("expected_evidence", [])
            key_facts = q.get("key_facts", [])
            difficulty = q.get("difficulty", "unknown")
            category = q.get("category", "unknown")
            gen_type = q.get("generation_type", "synthetic")

            metrics["difficulty"][difficulty]["total"] += 1
            metrics["category"][category]["total"] += 1
            metrics["generation"][gen_type]["total"] += 1

            start_time = time.time()
            try:
                # Rate limit protection
                time.sleep(2.5)
                response = requests.post(API_URL, json={"question": question_text, "top_k": 5, "repository": "httpx"}, timeout=15)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                print(f"Error querying {question_text[:30]}... : {e}")
                continue
            
            latency = time.time() - start_time
            metrics["overall"]["latencies"].append(latency)

            citations = data.get("citations", [])
            answer = data.get("answer", "")
            
            # Check Hit@3 against acceptable sources
            hit_rank = -1
            for rank, cit in enumerate(citations[:3]):
                cit_source_normalized = cit["source_file"].replace("\\", "/")
                if any(acc in cit_source_normalized for acc in acceptable_sources):
                    hit_rank = rank + 1
                    break
            
            is_hit = 1 if hit_rank > 0 else 0
            if is_hit:
                metrics["overall"]["hit"] += 1
                metrics["difficulty"][difficulty]["hit"] += 1
                metrics["category"][category]["hit"] += 1
                metrics["generation"][gen_type]["hit"] += 1
                
            # Evidence Type Match Rate
            retrieved_types = set(c.get("type", "") for c in citations[:3])
            for ev in expected_evidence:
                metrics["evidence_match"][ev]["total"] += 1
                if ev in retrieved_types:
                    metrics["evidence_match"][ev]["hit"] += 1

            # LLM Judge Evaluation
            cit_texts = [{"source_file": c["source_file"], "content": c.get("content", "")[:200]} for c in citations]
            answer_correct = evaluate_answer_correctness(question_text, answer, cit_texts, key_facts)
            
            if answer_correct:
                metrics["overall"]["ans"] += 1
                metrics["difficulty"][difficulty]["ans"] += 1
                metrics["category"][category]["ans"] += 1
                metrics["generation"][gen_type]["ans"] += 1

            # Failure Analysis Bucketing
            if not is_hit:
                metrics["failures"]["retrieval"] += 1
            elif not answer_correct:
                metrics["failures"]["reasoning"] += 1

            # Save to db
            eval_record = EvalResult(
                question=question_text,
                category=category,
                hit=hit_rank,
                latency=latency,
                citation_correct=is_hit,
                answer_correct=answer_correct
            )
            session.add(eval_record)
            session.commit()
            
            audit_rows.append({
                "Question": question_text,
                "Difficulty": difficulty,
                "Generation": gen_type,
                "Hit Rank": hit_rank if hit_rank > 0 else "Miss",
                "Answer Correct (Judge)": "YES" if answer_correct else "NO",
                "Latency": f"{latency:.2f}s",
                "Generated Answer": answer
            })
            
            print(f"[{gen_type[:3].upper()}] Q: {question_text[:40]}... | Hit@3: {'Yes' if is_hit else 'No'} | Answer: {'Yes' if answer_correct else 'No'}")
            
    finally:
        session.close()

    # Print summary
    latencies = metrics["overall"]["latencies"]
    if latencies:
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95) - 1]
        print(f"\n--- Final Engineering Benchmark Report ---")
        print(f"Overall:")
        print(f"  Total Questions: {total_questions}")
        print(f"  Hit@3: {metrics['overall']['hit']/total_questions*100:.1f}%")
        print(f"  Answer Accuracy: {metrics['overall']['ans']/total_questions*100:.1f}%")
        print(f"  Latency P95: {p95_latency:.2f}s")
        
        print(f"\nBy Generation Type:")
        for gen, data in metrics["generation"].items():
            if data['total'] > 0:
                print(f"  {gen.capitalize()} = {data['hit']/data['total']*100:.1f}% Hit@3 | {data['ans']/data['total']*100:.1f}% Ans")

        print(f"\nBy Difficulty:")
        for diff, data in metrics["difficulty"].items():
            if data['total'] > 0:
                print(f"  {diff.capitalize()} = {data['hit']/data['total']*100:.1f}% Hit@3 | {data['ans']/data['total']*100:.1f}% Ans")
                
        print(f"\nBy Category:")
        for cat, data in metrics["category"].items():
            if data['total'] > 0:
                print(f"  {cat.capitalize()} = {data['hit']/data['total']*100:.1f}% Hit@3")
                
        print(f"\nEvidence Precision:")
        for ev, data in metrics["evidence_match"].items():
            if data['total'] > 0:
                print(f"  {ev} = {data['hit']/data['total']*100:.1f}% Match Rate")

        print(f"\nFailure Analysis:")
        print(f"  Retrieval Failures = {metrics['failures']['retrieval']}")
        print(f"  Reasoning Failures = {metrics['failures']['reasoning']}")
        
        with open("human_audit.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Question", "Difficulty", "Generation", "Hit Rank", "Answer Correct (Judge)", "Latency", "Gold Accuracy (Human Review)", "Generated Answer"])
            writer.writeheader()
            for row in audit_rows:
                row["Gold Accuracy (Human Review)"] = ""
                writer.writerow(row)

if __name__ == "__main__":
    from app.database.connection import engine, Base
    Base.metadata.create_all(bind=engine)
    run_benchmark()

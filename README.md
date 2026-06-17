# Engineering Memory v1.0

Engineering Memory is an AI-powered enterprise assistant designed to answer highly specific technical questions by referencing your organization's codebase, official documentation, and issue tracker history.

## System Architecture
* **Frontend:** Streamlit container for an interactive, conversational UI.
* **Backend API:** FastAPI container utilizing honest, faceted "hybrid search".
* **Database Layer:** Neon Serverless PostgreSQL.
  * **Vector Index:** `pgvector` with HNSW for semantic search (`embedding <=> query_embedding`).
  * **FTS Index:** Native PostgreSQL `websearch_to_tsquery` for exact keyword matches.
* **Inference Engine:** Generation and LLM-as-a-Judge evaluation via the Groq API (`llama-3.1-8b-instant`).

## Evaluation Methodology (Hybrid Benchmark)

To rigorously evaluate the system's accuracy, we decoupled source retrieval performance from generation accuracy and tested the system against a 50-question hybrid dataset tracking difficulty and generalization capability.

### The Dataset: 50 Questions
To avoid benchmark leakage, the questions were strictly divided into three generation tiers:
- **20 Synthetic Questions:** Reverse-generated from exact database chunks to act as a retrieval sanity check.
- **20 Human Questions:** Hand-crafted using various engineering personas (maintainer, API user, bug investigator) to simulate messy, natural queries.
- **10 Adversarial Questions:** Intentionally complex questions designed to break the confidence engine and embedding model.

*Note on Benchmark Transparency:* During development, the initial benchmark dataset labels were audited and corrected after manual review. Several questions rigidly expected bug-tracker tickets when official documentation provided a superior, authoritative answer. The labels were adjusted to utilize an `acceptable_sources` array to reflect the true optimal sources.

### Benchmark Execution Report

```text
--- Final Engineering Benchmark Report ---
Overall:
  Total Questions: 50
  Hit@3: 54.0%
  Answer Accuracy: 10.0%
  Latency P95: 4.93s

By Generation Type:
  Synthetic = 65.0% Hit@3 | 5.0% Ans
  Human = 55.0% Hit@3 | 20.0% Ans
  Adversarial = 30.0% Hit@3 | 0.0% Ans

By Difficulty:
  Easy = 56.0% Hit@3 | 4.0% Ans
  Medium = 70.0% Hit@3 | 30.0% Ans
  Hard = 40.0% Hit@3 | 6.7% Ans

By Category:
  Docs = 100.0% Hit@3
  Api = 53.1% Hit@3
  Architecture = 54.5% Hit@3
  Dependencies = 40.0% Hit@3

Evidence Precision:
  DOC = 100.0% Match Rate
  CODE = 96.9% Match Rate

Failure Analysis:
  Retrieval Failures = 22
  Reasoning Failures = 22
```

## Next Steps for v1.1
The retrieval pipeline is working adequately, and the Evidence Precision is remarkably high (~97%+). The final engineering focus for the next iteration is diagnosing the massive Generator/Judge disparity.

1. **Confusion Matrix Audit:** Review the `human_audit.csv` output for all 22 reasoning failures to determine if failures are caused by:
   - **A:** Generator hallucinating or failing synthesis (llama-3.1-8b limits).
   - **B:** The LLM Judge being overly strict on phrasing.
   - **C:** Poor system prompts causing the Generator to ignore retrieved evidence.
2. **Handle API Throttling:** Some queries timed out due to aggressive Groq API rate limits (HTTP 429). Implement robust `tenacity` retry logic to stabilize benchmark execution.

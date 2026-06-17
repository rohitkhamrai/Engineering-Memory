# Engineering Memory - Evaluation Methodology & Benchmark

This document details the rigorous evaluation pipeline used to benchmark Engineering Memory v1.0. 
Rather than relying on vibes or "it looks right" manual testing, we built a mathematically auditable hybrid dataset.

## The Problem with Standard RAG Demos
Most RAG (Retrieval-Augmented Generation) tutorials test their architecture on 3-5 basic questions, leading to a false sense of security. When deployed against real codebases, they fail silently because standard semantic search struggles with deep, multi-hop engineering reasoning.

## The 50-Question Dataset Structure
To decouple retrieval performance from the LLM's reasoning capability, we generated a 50-question hybrid dataset spanning architecture, APIs, documentation, dependencies, and issue tracker history.

To prevent benchmark leakage, the questions are divided into three generation tiers:
1. **20 Synthetic Questions (Easy/Medium):** Reverse-generated from exact database chunks. Acts as a baseline retrieval sanity check.
2. **20 Human Questions (Medium/Hard):** Hand-crafted using various engineering personas (maintainer, API user, bug investigator) to simulate messy, natural phrasing.
3. **10 Adversarial Questions (Hard):** Intentionally complex, multi-hop questions designed to break the confidence engine and embedding model.

## Target Repository
The benchmark was run against the open-source `HTTPX` repository, indexing its codebase, `docs/` folder, and GitHub issues.

## Final Benchmark Report (v1.0)

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

## Failure Analysis & Root Cause

The drop-off in Adversarial performance (30% Hit@3) compared to Documentation lookups (100% Hit@3) is exactly what we set out to measure.

Through our `trace_query.py` script, we diagnosed the root cause of the Human/Adversarial retrieval failures. 
**It was not an embedding model failure.**

By querying the exact database chunks, we discovered that **Semantic Context Loss occurred during ingestion**. The naive token-window chunking algorithm was splitting explanatory paragraphs away from their corresponding code examples. 
Because the chunking brutally severed the context, neither the FTS engine (requiring exact word matches) nor the Vector engine (requiring semantic alignment in a single chunk) could map the question to the answer.

*No embedding model or reranker can recover information that has been sliced apart at the ingestion layer.*

This insight directly drives the roadmap for v1.1.

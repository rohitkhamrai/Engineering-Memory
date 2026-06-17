# Engineering Memory

**A highly rigorous, evaluated hybrid-retrieval system built to answer software engineering questions using your organization's codebase, documentation, and issue tracker.**

![Demo](demo.gif)

## Why This Project Exists

Engineers spend an enormous amount of time searching through sprawling codebases, outdated wikis, and closed GitHub issues. While many "RAG Chatbots" exist, they often rely on naive semantic search that hallucinates or fails on complex, multi-hop engineering reasoning.

Engineering Memory was built to solve this by providing **honest, evidence-backed answers** with measurable retrieval quality. It separates generation accuracy from retrieval performance, relying on a mathematically sound Confidence Engine to ensure developers can trust the output.

## Features
- **Hybrid Search Engine:** Combines PostgreSQL FTS (Full Text Search) for exact keyword matches with `pgvector` HNSW for semantic understanding.
- **Honest Confidence Engine:** Evaluates the diversity and relevance of retrieved sources (`DOC`, `CODE`, `ISSUE`) before generating an answer. If evidence is lacking, the system abstains instead of hallucinating.
- **Decoupled Architecture:** Clean separation between the FastAPI inference backend and the Streamlit conversational frontend.
- **Rigorous Evaluation Suite:** Includes an automated 50-question hybrid benchmark to test retrieval Hit@3 and LLM-as-a-Judge answer accuracy.

## Architecture

![Architecture](docs/architecture.png)

1. **Frontend:** Streamlit Container
2. **Backend API:** FastAPI Container
3. **Database Layer:** Neon Serverless PostgreSQL (`pgvector`, `tsvector`)
4. **Embeddings:** Local SentenceTransformers (`BAAI/bge-small-en-v1.5`)
5. **Generation & Evaluation:** Groq API (`llama-3.1-8b-instant`)

## Evaluation Methodology & Results

Most RAG projects hide behind 3-5 successful queries. Engineering Memory was subjected to a grueling 50-question hybrid benchmark, explicitly designed to test its limits. 

The dataset is divided into:
- 20 Synthetic Questions (Sanity check)
- 20 Human Questions (Natural phrasing)
- 10 Adversarial Questions (Multi-hop edge cases)

**Overall Hit@3: 54.0%**
- **Documentation Retrieval:** 100% Hit@3
- **Adversarial Retrieval:** 30% Hit@3

*For the full deep-dive into the methodology and detailed aggregator metrics, read the [BENCHMARK.md](BENCHMARK.md).*

## What I Learned (Root Cause Analysis)

The most valuable takeaway from this project was not the vector search itself, but the debugging loop: **Measure → Observe → Trace → Prove → Fix.**

1. **Retrieval failures are not always embedding failures.** When Adversarial retrieval dropped to 30%, it was tempting to swap to a larger embedding model or add a reranker.
2. **Query tracing is more useful than changing models.** By writing a custom `trace_query.py` script, we traced the exact chunks the vector and FTS engines were fetching.
3. **Semantic context loss during ingestion breaks retrieval.** We proved that our naive token-window chunking algorithm was splitting explanatory markdown text away from the corresponding Python code examples. The information was destroyed at the database level, meaning no reranker or embedding model could ever recover it.
4. **Benchmarking exposes what demos hide.** Without the 50-question hybrid dataset, the project would have looked flawless on simple documentation lookups. The benchmark exposed the exact ingestion flaw that will drive the v1.1 architecture.

## Known Limitations

- **Adversarial Retrieval is Weak:** Performance on multi-hop reasoning remains significantly lower than straight documentation retrieval.
- **Naive Chunking:** The current fixed-window chunking destroys markdown semantic structure (separating Headings from Paragraphs from Code blocks).
- **Confidence Metric:** The Confidence Engine currently measures source *diversity* (e.g. DOC + CODE) rather than absolute evidence *relevance*.
- **Single Repository:** The benchmark dataset is currently based exclusively on the `HTTPX` repository history.

## Installation / Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rohitkhamrai/Engineering-Memory.git
   cd Engineering-Memory
   ```
2. **Set up Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. **Configure Environment:**
   Export your database and inference keys in the terminal or `.env` file:
   ```bash
   export DATABASE_URL="postgresql://user:pass@host/dbname"
   export GROQ_API_KEY="your_groq_api_key"
   ```
4. **Run the Backend (FastAPI):**
   ```bash
   uvicorn app.api.main:app --reload
   ```
5. **Run the Frontend (Streamlit):**
   ```bash
   streamlit run app/ui/app.py
   ```

## Example Queries

Once running, try testing the system across varying difficulty tiers:
- **Easy:** *"What is the default timeout value for AsyncClient?"*
- **Medium:** *"How do I mount a custom transport?"*
- **Hard:** *"Why might SSL verification fail specifically during a redirect even if the initial request succeeded?"*

## Future Work (v1.1)
The immediate focus for v1.1 is migrating from token-based chunking to a **Markdown-Aware Parser** that preserves document hierarchy (Headings + Paragraphs + Code blocks as a single cohesive unit). We will re-ingest the corpus and re-run the benchmark to mathematically prove the retrieval improvement before introducing any advanced AI Agents or Graph databases.

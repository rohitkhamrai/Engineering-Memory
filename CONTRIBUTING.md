# Contributing to Engineering Memory

Thank you for your interest in contributing! This project is an ongoing exploration of reliable, evaluated RAG systems.

## Architecture Philosophy
- **Honesty Over Hallucination:** The system must never confidently invent answers. If context is missing, it should abstain.
- **Evidence-Backed Answers:** All generation is strictly grounded in `DOC`, `CODE`, and `ISSUE` citations.
- **Evaluated Engineering:** We measure Retrieval Quality (Hit@3) and Generation Accuracy separately. New architectural changes must prove their value against the 50-question hybrid benchmark before merging.

## Development Setup
1. Clone the repository and set up a local virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Ensure you have Neon PostgreSQL and Groq API keys exported in your `.env`.
4. Start the backend: `uvicorn app.api.main:app --reload`
5. Start the frontend: `streamlit run app/ui/app.py`

## Running the Benchmark
Any major PRs should include a run of the hybrid benchmark to prove retrieval hasn't regressed.
```bash
python -m app.evaluation.benchmark
```
Check `BENCHMARK.md` for our current metrics baseline.

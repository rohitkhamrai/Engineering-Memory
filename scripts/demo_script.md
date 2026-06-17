# Demo GIF Recording Script

To record a high-impact demo GIF for the `README.md` and your portfolio, follow this 3-minute flow:

## Prep
1. Ensure the Backend and Frontend are running locally.
2. Have a screen recording tool ready (e.g., LICEcap, OBS, or Mac/Windows built-in screen recorder).
3. Clear the Streamlit chat history by refreshing the page.

## The Script

### 1. The Easy Win (0:00 - 0:15)
- **Action:** Type and submit: *"How do I set a global timeout for all requests?"*
- **Visual:** Wait for the streaming response.
- **Action:** Click the `📚 View Citations` expander.
- **Visual:** Show that it successfully retrieved `docs/advanced/timeouts.md` and `CODE` files, and awarded a `STRONG` confidence badge.

### 2. The Adversarial Honest Failure (0:15 - 0:40)
- **Action:** Type and submit: *"What is the difference between the data and json kwargs?"*
- **Visual:** The system searches, and returns a `MODERATE` confidence badge, but the LLM responds with: *"Context does not contain information to directly answer the question."*
- **Key Point:** This proves the LLM is HONEST and does not hallucinate when retrieval fails. Expand the citations to show the retrieved chunks were incorrect (e.g., `httpx_urls.py`).

### 3. The Terminal Trace (0:40 - 0:55)
- **Action:** Quickly alt-tab to your terminal.
- **Action:** Run the trace script: `python -m scripts.trace_query`
- **Visual:** Scroll up slightly to show the split output: `--- VECTOR SEARCH TOP 20 ---` and `--- FTS SEARCH TOP 20 (Empty) ---`. This proves you built tracing tools to debug the architecture.

### 4. The Benchmark Output (0:55 - 1:10)
- **Action:** Alt-tab to VS Code or your editor, showing the `human_audit.csv` file.
- **Visual:** Scroll through the rows of Easy/Medium/Hard Synthetic/Human/Adversarial queries.
- **Action:** Open `BENCHMARK.md` to show the final aggregated metrics.

### Export
- Save as a `.mp4` or `.gif` and place it in the root folder as `demo.gif` or `demo.mp4`.
- Update the `README.md` image link if necessary.

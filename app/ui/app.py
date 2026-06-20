import os
import time
import streamlit as st
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

API_ASK_URL = f"{API_BASE_URL}/api/ask"
API_INGEST_URL = f"{API_BASE_URL}/api/ingest"
API_REPOS_URL = f"{API_BASE_URL}/api/repos"
API_STATUS_URL = f"{API_BASE_URL}/api/ingest/status"

st.set_page_config(page_title="Engineering Memory", page_icon="🧠", layout="centered")

# --- CSS Theme Injection ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', system-ui, sans-serif !important;
}

.glass-card {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
}

.glass-card-header {
    font-size: 0.75em;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #888;
    margin-bottom: 12px;
    font-weight: 600;
}

.glass-card-value {
    font-size: 1.1em;
    font-weight: 500;
    color: #eee;
}

.glass-card-sub {
    font-size: 0.85em;
    color: #888;
    margin-top: 4px;
}

.citation-chip {
    display: inline-flex;
    align-items: center;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 6px;
    padding: 4px 10px;
    margin: 4px 6px 4px 0;
    font-size: 0.8em;
    color: #ccc;
    font-family: monospace;
    transition: all 0.2s ease;
}
.citation-chip:hover {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.3);
}

.confidence-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 4px;
    font-size: 0.75em;
    font-weight: 600;
    margin-bottom: 16px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.confidence-STRONG { background: rgba(46, 204, 113, 0.1); color: #2ecc71; border: 1px solid rgba(46, 204, 113, 0.2); }
.confidence-MODERATE { background: rgba(241, 196, 15, 0.1); color: #f1c40f; border: 1px solid rgba(241, 196, 15, 0.2); }
.confidence-WEAK { background: rgba(231, 76, 60, 0.1); color: #e74c3c; border: 1px solid rgba(231, 76, 60, 0.2); }
.confidence-UNKNOWN { background: rgba(149, 165, 166, 0.1); color: #95a5a6; border: 1px solid rgba(149, 165, 166, 0.2); }

.block-container {
    padding-top: 3rem;
    max-width: 800px;
}
</style>
""", unsafe_allow_html=True)

# Fetch available repos
try:
    repos_resp = requests.get(API_REPOS_URL, timeout=5)
    if repos_resp.status_code == 200:
        repos_data = repos_resp.json()
    else:
        repos_data = [{"name": "httpx", "chunks": 0}]
except:
    repos_data = [{"name": "httpx", "chunks": 0}]

# Dropdown mapping display name -> actual repo name
repo_options = {f"{r['name']}": r['name'] for r in repos_data}
if not repo_options:
    repo_options = {"httpx": "httpx"}
    repos_data = [{"name": "httpx", "chunks": 0}]

# -- SIDEBAR --
with st.sidebar:
    st.markdown("### Control Panel")
    st.markdown("<br/>", unsafe_allow_html=True)
    
    # Repository Card
    selected_display = st.selectbox("Active Repository", list(repo_options.keys()), label_visibility="collapsed")
    selected_repo = repo_options[selected_display]
    selected_chunks = next((r['chunks'] for r in repos_data if r['name'] == selected_repo), 0)
    
    st.markdown(f"""
    <div class="glass-card">
        <div class="glass-card-header">Repository</div>
        <div class="glass-card-value">{selected_repo}</div>
        <div class="glass-card-sub">{selected_chunks:,} chunks</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Ingestion Card
    with st.container():
        st.markdown("""
        <div class="glass-card" style="margin-bottom: 0; padding-bottom: 4px;">
            <div class="glass-card-header">Ingest Repository</div>
        """, unsafe_allow_html=True)
        repo_url = st.text_input("GitHub URL", placeholder="https://github.com/owner/repo", label_visibility="collapsed")
        if st.button("Ingest", use_container_width=True):
            if not repo_url:
                st.error("URL required")
            else:
                headers = {}
                secret = os.getenv("INGEST_SECRET")
                if secret:
                    headers["X-API-Key"] = secret
                    
                resp = requests.post(API_INGEST_URL, json={"repo_url": repo_url}, headers=headers)
                if resp.status_code == 200:
                    st.session_state.job_id = resp.json()["job_id"]
                    st.rerun()
                else:
                    err = resp.json().get("detail", "Ingest failed")
                    if isinstance(err, list):
                        st.error(f"Error: {err[0].get('msg', 'Invalid request')}")
                    else:
                        st.error(f"Error: {err}")
        st.markdown("</div>", unsafe_allow_html=True)

    # Polling for ingest status
    if "job_id" in st.session_state:
        job_id = st.session_state.job_id
        try:
            status_resp = requests.get(f"{API_STATUS_URL}/{job_id}")
            if status_resp.status_code == 200:
                status_data = status_resp.json()
                status = status_data["status"]
                
                status_map = {
                    "ready": "🟢 Ready",
                    "parsing": "🟡 Parsing",
                    "embedding": "🔵 Embedding",
                    "failed": "🔴 Failed",
                    "cloning": "🟡 Cloning",
                    "queued": "⚪ Queued"
                }
                display_status = status_map.get(status.lower(), f"⚪ {status}")
                
                st.markdown(f"""
                <div class="glass-card" style="margin-top: 16px;">
                    <div class="glass-card-header">Ingestion Status</div>
                    <div class="glass-card-value" style="font-size: 1em;">{display_status}</div>
                </div>
                """, unsafe_allow_html=True)
                
                if status == "failed":
                    st.error(status_data.get("error_message", "Unknown error"))
                    if st.button("Dismiss"):
                        del st.session_state.job_id
                        st.rerun()
                elif status == "ready":
                    if st.button("Refresh"):
                        del st.session_state.job_id
                        st.rerun()
                else:
                    time.sleep(2)
                    st.rerun()
        except Exception as e:
            st.error("Failed to check status.")

# -- MAIN CHAT --
st.markdown("<h1 style='margin-bottom: 0;'>Engineering Memory</h1>", unsafe_allow_html=True)

# Repository Metrics Header
total_repos = len(repos_data)
total_chunks = sum(r['chunks'] for r in repos_data)
st.markdown(f"""
<div style="display:flex; gap: 24px; font-size: 0.85em; color: #888; margin-bottom: 32px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 16px;">
    <div><b>Repositories:</b> {total_repos}</div>
    <div><b>Chunks:</b> {total_chunks:,}</div>
    <div><b>Status:</b> 🟢 Healthy</div>
</div>
""", unsafe_allow_html=True)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Empty State
if not st.session_state.messages:
    st.markdown("""
    <div style="text-align: center; margin-top: 100px; margin-bottom: 100px; color: #888;">
        <h3 style="font-weight: 500; margin-bottom: 12px; color: #eee;">Ask questions about your codebase</h3>
        <p style="font-size: 0.9em;">Search across documentation, source code, and ingested repositories.</p>
    </div>
    """, unsafe_allow_html=True)

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            st.markdown(message.get("confidence_html", ""), unsafe_allow_html=True)
            st.markdown(message["content"])
            st.markdown(message.get("citations_html", ""), unsafe_allow_html=True)
        else:
            st.markdown(message["content"])

# React to user input
if prompt := st.chat_input(f"Ask a question about {selected_repo}..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.status("Searching repository...", expanded=True) as status:
            st.write("Retrieving context...")
            try:
                response = requests.post(API_ASK_URL, json={"question": prompt, "top_k": 5, "repository": selected_repo}, timeout=120)
                st.write("Generating answer...")
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "")
                    confidence = data.get("confidence", "UNKNOWN")
                    citations = data.get("citations", [])

                    status.update(label="Complete", state="complete", expanded=False)
                    
                    # Format response components
                    confidence_html = f'<div class="confidence-badge confidence-{confidence}">Confidence: {confidence}</div>'
                    
                    citations_html = ""
                    if citations:
                        citations_html = "<div style='margin-top: 16px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 12px;'>"
                        for c in citations:
                            citations_html += f"<span class='citation-chip'>[{c['type']}] {c['source_file']}</span>"
                        citations_html += "</div>"
                    
                    # Render sequentially to preserve native markdown parsing for the answer
                    st.markdown(confidence_html, unsafe_allow_html=True)
                    st.markdown(answer)
                    if citations_html:
                        st.markdown(citations_html, unsafe_allow_html=True)
                    
                    # Add to history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer,
                        "confidence_html": confidence_html,
                        "citations_html": citations_html
                    })
                else:
                    status.update(label="Error", state="error", expanded=False)
                    err_msg = f"Error: {response.text}"
                    st.error(err_msg)
                    st.session_state.messages.append({"role": "assistant", "content": err_msg})
            except Exception as e:
                status.update(label="Failed", state="error", expanded=False)
                err_msg = f"Failed to connect to backend API: {e}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})

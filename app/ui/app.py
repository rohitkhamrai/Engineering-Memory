import os
import time
import streamlit as st
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

API_ASK_URL = f"{API_BASE_URL}/api/ask"
API_INGEST_URL = f"{API_BASE_URL}/api/ingest"
API_REPOS_URL = f"{API_BASE_URL}/api/repos"
API_STATUS_URL = f"{API_BASE_URL}/api/ingest/status"

st.set_page_config(page_title="Engineering Memory", page_icon="🧠", layout="wide")

st.title("🧠 Engineering Memory")
st.markdown("Ask technical questions backed by **Code**, **Docs**, and **Issues**.")

# -- SIDEBAR --
st.sidebar.header("Repository Selection")

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
repo_options = {f"{r['name']} ({r['chunks']} chunks)": r['name'] for r in repos_data}
if not repo_options:
    repo_options = {"httpx (0 chunks)": "httpx"}

selected_display = st.sidebar.selectbox("Current Repository", list(repo_options.keys()))
selected_repo = repo_options[selected_display]

st.sidebar.markdown("---")
st.sidebar.header("Ingest New Repository")

repo_url = st.sidebar.text_input("GitHub URL", placeholder="https://github.com/owner/repo")
if st.sidebar.button("Ingest"):
    if not repo_url:
        st.sidebar.error("URL required")
    else:
        resp = requests.post(API_INGEST_URL, json={"repo_url": repo_url})
        if resp.status_code == 200:
            st.session_state.job_id = resp.json()["job_id"]
            st.rerun()
        else:
            err = resp.json().get("detail", "Ingest failed")
            if isinstance(err, list):
                st.sidebar.error(f"Error: {err[0].get('msg', 'Invalid request')}")
            else:
                st.sidebar.error(f"Error: {err}")

# Polling for ingest status
if "job_id" in st.session_state:
    job_id = st.session_state.job_id
    try:
        status_resp = requests.get(f"{API_STATUS_URL}/{job_id}")
        if status_resp.status_code == 200:
            status_data = status_resp.json()
            status = status_data["status"]
            st.sidebar.info(f"Ingestion Status: **{status}**")
            
            if status == "failed":
                st.sidebar.error(status_data.get("error_message", "Unknown error"))
                if st.sidebar.button("Dismiss"):
                    del st.session_state.job_id
                    st.rerun()
            elif status == "ready":
                st.sidebar.success("Ingestion Complete!")
                if st.sidebar.button("Refresh"):
                    del st.session_state.job_id
                    st.rerun()
            else:
                time.sleep(2)
                st.rerun()
    except Exception as e:
        st.sidebar.error("Failed to check status.")

# -- MAIN CHAT --

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def get_badge_color(confidence: str) -> str:
    if confidence == "STRONG": return "green"
    elif confidence == "MODERATE": return "orange"
    elif confidence == "WEAK": return "red"
    return "grey"

# React to user input
if prompt := st.chat_input(f"Ask a question about {selected_repo}..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner(f"Searching {selected_repo} and analyzing evidence..."):
            try:
                response = requests.post(API_ASK_URL, json={"question": prompt, "top_k": 5, "repository": selected_repo}, timeout=120)
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "")
                    confidence = data.get("confidence", "UNKNOWN")
                    citations = data.get("citations", [])

                    # Format response
                    color = get_badge_color(confidence)
                    header = f"**Confidence:** :{color}[{confidence}]\n\n"
                    
                    st.markdown(header + answer)
                    
                    if citations:
                        with st.expander("📚 View Citations"):
                            for c in citations:
                                st.write(f"- **{c['type']}**: `{c['source_file']}`")

                    # Add assistant response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": header + answer})
                else:
                    st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"Failed to connect to backend API: {e}")

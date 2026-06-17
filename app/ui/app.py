import os
import streamlit as st
import requests

API_URL = os.getenv("API_URL", "http://localhost:8000/api/ask")

st.set_page_config(page_title="Engineering Memory", page_icon="🧠", layout="wide")

st.title("🧠 Engineering Memory")
st.markdown("Ask technical questions about the HTTPX codebase, and get answers backed by **Code**, **Docs**, and **Issues**.")

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
if prompt := st.chat_input("How does httpx handle connection timeouts?"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Searching repository and analyzing evidence..."):
            try:
                response = requests.post(API_URL, json={"question": prompt, "top_k": 5}, timeout=120)
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

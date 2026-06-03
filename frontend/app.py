from pathlib import Path
import os
import sys
import uuid

import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from frontend.api_client import ApiClientError, send_chat_message

st.set_page_config(page_title="Voice Travel Agent", page_icon="🎙️")
st.title("Voice Travel Agent")
st.write("Speak or type about your trip goals, and get destination, hotel, weather, and food guidance.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "api_base_url" not in st.session_state:
    st.session_state.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

st.sidebar.header("Voice-first tips")
st.sidebar.write("Use text input as a fallback if browser voice capture is unavailable.")
st.sidebar.write("Ask for destinations or hotels to trigger TripAdvisor enrichment when available.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

voice_note = st.text_input("Voice transcript or typed message", placeholder="Ask about your trip")

if st.button("Send") and voice_note.strip():
    prompt = voice_note.strip()
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Planning your trip..."):
            try:
                result = send_chat_message(
                    st.session_state.api_base_url,
                    prompt,
                    st.session_state.conversation_id,
                )
                reply = result["reply"]
                st.session_state.conversation_id = result["conversation_id"]
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except ApiClientError as exc:
                st.error(f"Could not reach API: {exc}")
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")

st.caption("Voice capture and text-to-speech can be added on top of this MVP flow.")

from pathlib import Path
import os
import sys
import uuid

# pyrefly: ignore [missing-import]
import streamlit as st
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from frontend.api_client import ApiClientError, send_chat_message
# pyrefly: ignore [missing-import]
import streamlit.components.v1 as components

# Declare voice component
parent_dir = os.path.dirname(os.path.abspath(__file__))
build_dir = os.path.join(parent_dir, "voice_button")
voice_button = components.declare_component("voice_button", path=build_dir)

st.set_page_config(page_title="Voice Travel Agent", page_icon="🎙️")
st.title("Voice Travel Agent")
st.write("Speak or type about your trip goals, and get destination, hotel, weather, and food guidance.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "api_base_url" not in st.session_state:
    st.session_state.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
if "last_voice_ts" not in st.session_state:
    st.session_state.last_voice_ts = 0
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = ""

def handle_send():
    prompt = st.session_state.user_message.strip()
    if prompt:
        st.session_state.pending_prompt = prompt
    st.session_state.user_message = ""

st.sidebar.header("Voice-first tips")
st.sidebar.write("Use text input as a fallback if browser voice capture is unavailable.")
st.sidebar.write("Ask for destinations, hotels, weather, or food to trigger SerpAPI enrichment when available.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if "user_message" not in st.session_state:
    st.session_state.user_message = ""

# Text input for manual messages or showing the voice transcript placeholder
voice_note = st.text_input(
    "Voice transcript or typed message",
    placeholder="Ask about your trip",
    key="user_message"
)

# Voice Button and Send button
col1, col2 = st.columns([1, 4])
with col1:
    st.button("Send", use_container_width=True, on_click=handle_send)
with col2:
    voice_data = voice_button(key="voice_input")

# Handle Voice Component transcription
if voice_data and isinstance(voice_data, dict):
    ts = voice_data.get("timestamp", 0)
    text = voice_data.get("text", "").strip()
    if ts > st.session_state.last_voice_ts and text:
        st.session_state.last_voice_ts = ts
        st.session_state.pending_prompt = text

# Choose source of prompt
prompt = st.session_state.pending_prompt
if prompt:
    st.session_state.pending_prompt = ""

if prompt:
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
    st.rerun()

st.caption("Voice capture is powered by browser-native Web Speech API. Text fallback is supported.")

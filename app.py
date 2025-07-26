import streamlit as st
import requests
import tempfile
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import time

API_URL = "http://localhost:8000"  # Change this if backend is hosted remotely

st.set_page_config(page_title="PDF Chat Assistant", layout="wide")
st.title("📚 PDF Voice & Text Assistant")

# Session states
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "recording" not in st.session_state:
    st.session_state.recording = False

if "audio_data" not in st.session_state:
    st.session_state.audio_data = None

# === PDF Upload ===
with st.expander("📄 Upload PDF", expanded=True):
    uploaded_pdf = st.file_uploader("Upload your PDF", type="pdf")
    if st.button("Upload and Process PDF") and uploaded_pdf:
        with st.spinner("Processing PDF..."):
            res = requests.post(
                f"{API_URL}/upload-pdf",
                files={"file": (uploaded_pdf.name, uploaded_pdf, "application/pdf")}
            )
        msg_placeholder = st.empty()
        if res.status_code == 200:
            msg_placeholder.success("✅ PDF processed successfully!")
            time.sleep(1)
            st.rerun()
        else:
            msg_placeholder.error(f"❌ Error: {res.json()['detail']}")
        time.sleep(1)
        st.rerun()

st.divider()

# === Chat Input ===
col1, col2 = st.columns([10, 1])
with col1:
    user_input = st.text_input("Ask something by typing...", key="text_input")
with col2:
    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)  # spacing
    mic_clicked = st.button("🎙️", key="mic_button")

# === Voice Control ===
if mic_clicked:
    msg_placeholder = st.empty()
    if not st.session_state.recording:
        st.session_state.recording = True
        st.session_state.audio_data = sd.rec(
            int(30 * 44100),  # Max 30 seconds
            samplerate=44100,
            channels=1,
            dtype='int16'
        )
        msg_placeholder.success("🔴 Recording... Click mic again to stop.")
    else:
        sd.stop()
        st.session_state.recording = False
        msg_placeholder.success("✅ Recording stopped.")
        time.sleep(1)
        msg_placeholder.empty()

        # Save and send audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
            wav.write(tmpfile.name, 44100, st.session_state.audio_data)
            tmpfile.seek(0)
            audio_bytes = tmpfile.read()

        with st.spinner("🧠 Transcribing and answering..."):
            response = requests.post(
                f"{API_URL}/voice-chat",
                files={"audio": ("audio.wav", audio_bytes, "audio/wav")}
            )

        if response.status_code == 200:
            data = response.json()
            st.session_state.chat_history.append(("You (voice)", data["transcribed"]))
            st.session_state.chat_history.append(("Bot", data["answer"]))
        else:
            msg_placeholder = st.empty()
            msg_placeholder.error("❌ Voice processing failed: " + response.json()["detail"])
            time.sleep(1)
            msg_placeholder.empty()

# === Handle Text Input ===
if st.button("Send") and user_input:
    with st.spinner("Thinking..."):
        res = requests.get(f"{API_URL}/chat", params={"question": user_input})
    if res.status_code == 200:
        data = res.json()
        st.session_state.chat_history.append(("You", user_input))
        st.session_state.chat_history.append(("Bot", data["answer"]))

        # Clear the text input by resetting the key and rerunning
        st.session_state.pop("text_input")
        st.rerun()
    else:
        msg_placeholder = st.empty()
        msg_placeholder.error("❌ Chat failed: " + res.json()["detail"])
        time.sleep(1)
        msg_placeholder.empty()

# === Chat History ===
st.markdown("## 💬 Chat History")
for role, message in st.session_state.chat_history:
    if "You" in role:
        st.markdown(f"**🧑 {role}:** {message}")
    else:
        st.markdown(f"**🤖 {role}:** {message}")

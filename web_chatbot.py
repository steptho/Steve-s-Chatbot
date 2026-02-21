# web_chatbot.py

import os
import json
import base64
import tempfile
import streamlit as st
from openai import OpenAI
import PyPDF2
import pandas as pd
import docx
from pptx import Presentation
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode
import av
import numpy as np
import soundfile as sf

# -----------------------------------
# PAGE CONFIG
# -----------------------------------
st.set_page_config(page_title="Steve's Chatbot Pro", page_icon="🤖", layout="wide")
st.title("🤖 Steve's Chatbot Pro")

# -----------------------------------
# STORAGE SETUP
# -----------------------------------
CHAT_DIR = "saved_chats"
os.makedirs(CHAT_DIR, exist_ok=True)

# -----------------------------------
# OPENAI CLIENT
# -----------------------------------
api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("OPENAI_API_KEY not set.")
    st.stop()

client = OpenAI(api_key=api_key)

# -----------------------------------
# SESSION STATE INIT
# -----------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if "document_text" not in st.session_state:
    st.session_state.document_text = None

if "spreadsheet_df" not in st.session_state:
    st.session_state.spreadsheet_df = None

# -----------------------------------
# AUTO SAVE FUNCTION
# -----------------------------------
def save_chat():
    with open(os.path.join(CHAT_DIR, "latest_chat.json"), "w") as f:
        json.dump(st.session_state.messages, f, indent=2)

# -----------------------------------
# SIDEBAR
# -----------------------------------
st.sidebar.header("🛠 Tools")

# -------- Admin Login --------
st.sidebar.subheader("🔐 Admin Login")
password = st.sidebar.text_input("Password", type="password")

if st.sidebar.button("Login"):
    if password == st.secrets.get("ADMIN_PASSWORD"):
        st.session_state.admin_authenticated = True
        st.sidebar.success("Admin authenticated")
    else:
        st.sidebar.error("Incorrect password")

# -----------------------------------
# 📂 DOCUMENT PROCESSOR
# -----------------------------------
st.sidebar.subheader("📂 Document Intelligence")

uploaded_doc = st.sidebar.file_uploader(
    "Upload PDF, Word, PPT, CSV, Excel",
    type=["pdf", "docx", "pptx", "csv", "xlsx"]
)

if uploaded_doc:

    file_text = ""
    file_type = uploaded_doc.type
    st.session_state.spreadsheet_df = None

    try:
        if file_type == "application/pdf":
            pdf = PyPDF2.PdfReader(uploaded_doc)
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    file_text += text + "\n"

        elif file_type.endswith("wordprocessingml.document"):
            doc = docx.Document(uploaded_doc)
            for p in doc.paragraphs:
                if p.text.strip():
                    file_text += p.text + "\n"

        elif file_type.endswith("presentationml.presentation"):
            prs = Presentation(uploaded_doc)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        file_text += shape.text + "\n"

        elif file_type == "text/csv":
            df = pd.read_csv(uploaded_doc)
            st.session_state.spreadsheet_df = df
            file_text = df.head(50).to_string(index=False)

        elif file_type in [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel"
        ]:
            sheets = pd.read_excel(uploaded_doc, sheet_name=None)
            st.session_state.spreadsheet_df = sheets

            for name, df in sheets.items():
                file_text += f"\nSheet: {name}\n"
                file_text += df.head(50).to_string(index=False)
                file_text += "\n"

        if file_text.strip():
            st.session_state.document_text = file_text
            st.sidebar.success("Document loaded.")
        else:
            st.sidebar.error("No extractable text found.")

    except Exception as e:
        st.sidebar.error(f"Processing error: {e}")

# -------- Spreadsheet Preview --------
if st.session_state.spreadsheet_df is not None:
    st.sidebar.subheader("📊 Spreadsheet Preview")

    if isinstance(st.session_state.spreadsheet_df, dict):
        for name, df in st.session_state.spreadsheet_df.items():
            st.sidebar.write(f"Sheet: {name}")
            st.sidebar.dataframe(df.head())
    else:
        st.sidebar.dataframe(st.session_state.spreadsheet_df.head())

# -------- Summarise Document --------
if st.session_state.document_text:
    if st.sidebar.button("Summarise Document"):
        with st.spinner("Analyzing document..."):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Summarise this document clearly in bullet points."},
                    {"role": "user", "content": st.session_state.document_text}
                ]
            )
        summary = response.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": f"📄 Document Summary:\n\n{summary}"})
        save_chat()

# -----------------------------------
# 🖼 Vision AI
# -----------------------------------
st.sidebar.subheader("🖼 Vision AI")

image = st.sidebar.file_uploader("Upload Image", type=["jpg","jpeg","png"])

if image:
    img_bytes = image.getvalue()
    st.sidebar.image(img_bytes)

    if st.sidebar.button("Analyze Image"):
        encoded = base64.b64encode(img_bytes).decode()
        with st.spinner("Analyzing image..."):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image."},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                    ],
                }]
            )
        reply = response.choices[0].message.content
        st.session_state.messages.append({"role":"assistant","content":f"🖼 Image Analysis:\n\n{reply}"})
        save_chat()

# -----------------------------------
# 🎤 Voice
# -----------------------------------
st.sidebar.subheader("🎤 Voice")

class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.frames = []
    def recv(self, frame: av.AudioFrame):
        self.frames.append(frame.to_ndarray())
        return frame

ctx = webrtc_streamer(
    key="speech",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
)

if st.sidebar.button("Transcribe"):
    if ctx.audio_processor and ctx.audio_processor.frames:
        audio = np.concatenate(ctx.audio_processor.frames, axis=0)
        temp = "temp.wav"
        sf.write(temp, audio, 44100)
        with open(temp, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        st.session_state.messages.append({"role":"user","content":transcript.text})
        save_chat()
    else:
        st.sidebar.warning("No audio recorded.")

# -----------------------------------
# MAIN CHAT
# -----------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask me anything..."):
    st.session_state.messages.append({"role":"user","content":prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=st.session_state.messages
    )

    reply = response.choices[0].message.content
    st.session_state.messages.append({"role":"assistant","content":reply})
    with st.chat_message("assistant"):
        st.markdown(reply)

    save_chat()






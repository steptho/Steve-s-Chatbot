# web_chatbot.py

import os
import streamlit as st
from openai import OpenAI
import PyPDF2
import pandas as pd
import docx
from pptx import Presentation
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
import tempfile
import json
import base64
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode
import av

# -----------------------------------
# PAGE CONFIG
# -----------------------------------
st.set_page_config(
    page_title="Steve's Chatbot Pro",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Steve's Chatbot Pro")

# -----------------------------------
# OPENAI CLIENT (API KEY ONLY)
# -----------------------------------
api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")

if not api_key:
    st.error("OPENAI_API_KEY not set in Streamlit Secrets.")
    st.stop()

client = OpenAI(api_key=api_key)

# -----------------------------------
# SESSION STATE
# -----------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# -----------------------------------
# SIDEBAR
# -----------------------------------
st.sidebar.header("🛠 Tools")

# -------- Admin Login --------
st.sidebar.subheader("🔐 Admin Login")

admin_password = st.sidebar.text_input(
    "Enter Admin Password",
    type="password"
)

if st.sidebar.button("Login"):
    if admin_password == st.secrets.get("ADMIN_PASSWORD"):
        st.session_state.admin_authenticated = True
        st.sidebar.success("Admin authenticated")
    else:
        st.sidebar.error("Incorrect password")

# -------- File Upload --------
st.sidebar.subheader("🖼 Vision AI")

uploaded_image = st.sidebar.file_uploader(
    "Upload Image",
    type=["jpg", "jpeg", "png"],
    key="vision_upload"
)

if uploaded_image is not None:

    # Store image bytes immediately
    image_bytes = uploaded_image.getvalue()

    st.sidebar.image(image_bytes, use_container_width=True)

    if st.sidebar.button("Analyze Image"):

        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        with st.spinner("Analyzing image..."):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this image in detail."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
            )

        vision_reply = response.choices[0].message.content

        st.session_state.messages.append({
            "role": "assistant",
            "content": f"🖼 Image Analysis:\n\n{vision_reply}"
        })

        st.success("Image analyzed successfully.")

# -------- Live Voice Section --------
st.sidebar.subheader("🎤 Live Voice")

class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.frames = []

    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        self.frames.append(frame.to_ndarray())
        return frame

webrtc_ctx = webrtc_streamer(
    key="speech",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
)

if st.sidebar.button("Transcribe Voice"):
    if webrtc_ctx.audio_processor and webrtc_ctx.audio_processor.frames:
        import numpy as np
        audio_data = np.concatenate(webrtc_ctx.audio_processor.frames, axis=0)

        temp_audio = "temp_audio.wav"
        import soundfile as sf
        sf.write(temp_audio, audio_data, 44100)

        with open(temp_audio, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        st.session_state.messages.append({
            "role": "user",
            "content": transcript.text
        })

        st.success("Voice transcribed and added to chat.")
    else:
        st.sidebar.warning("No audio recorded.")

# -------- Export Section --------
st.sidebar.subheader("📥 Export Conversation")

# TXT Export
conversation_text = "\n\n".join(
    [f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages]
)

st.sidebar.download_button(
    "Download as TXT",
    conversation_text,
    file_name="conversation.txt"
)

# JSON Export
st.sidebar.download_button(
    "Download as JSON",
    json.dumps(st.session_state.messages, indent=2),
    file_name="conversation.json"
)

# -----------------------------------
# 📂 DOCUMENT PROCESSOR
# -----------------------------------
st.sidebar.subheader("📂 Document Intelligence")

uploaded_doc = st.sidebar.file_uploader(
    "Upload PDF, Word, PPT, or CSV",
    type=["pdf", "docx", "pptx", "csv"],
    key="doc_upload"
)

if uploaded_doc is not None:

    file_text = ""
    file_type = uploaded_doc.type

    try:
        # -------- PDF --------
        if file_type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_doc)
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    file_text += text + "\n"

        # -------- WORD --------
        elif file_type.endswith("wordprocessingml.document"):
            doc = docx.Document(uploaded_doc)
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    file_text += paragraph.text + "\n"

        # -------- POWERPOINT --------
        elif file_type.endswith("presentationml.presentation"):
            prs = Presentation(uploaded_doc)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        file_text += shape.text + "\n"

 # -------- CSV --------
        elif file_type == "text/csv":
            df = pd.read_csv(uploaded_doc)
            st.session_state["spreadsheet_df"] = df
            file_text = df.head(50).to_string(index=False)

        # -------- EXCEL (.xlsx) --------
        elif file_type in [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel"
        ]:
            df_dict = pd.read_excel(uploaded_doc, sheet_name=None)

            combined_text = ""

            for sheet_name, df in df_dict.items():
                combined_text += f"\nSheet: {sheet_name}\n"
                combined_text += df.head(50).to_string(index=False)
                combined_text += "\n"

            st.session_state["spreadsheet_df"] = df_dict
            file_text = combined_text
        # -------- VALIDATION --------
        if file_text.strip() == "":
            st.sidebar.error("No extractable text found in this document.")
        else:
            st.session_state["document_text"] = file_text
            st.sidebar.success("Document loaded successfully.")

    except Exception as e:
        st.sidebar.error(f"Error processing document: {e}")

# -------- SUMMARISE BUTTON --------
if "document_text" in st.session_state:
    if st.sidebar.button("Summarise Document"):

        with st.spinner("Analyzing document..."):

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional document analyst. Summarise the following document clearly, concisely, and in structured bullet points."
                    },
                    {
                        "role": "user",
                        "content": st.session_state["document_text"]
                    }
                ]
            )

        summary = response.choices[0].message.content

        st.session_state.messages.append({
            "role": "assistant",
            "content": f"📄 Document Summary:\n\n{summary}"
        })

        st.success("Summary added to chat.")

        if "spreadsheet_df" in st.session_state:

    st.sidebar.subheader("📊 Spreadsheet Preview")

    if isinstance(st.session_state["spreadsheet_df"], dict):
        for sheet_name, df in st.session_state["spreadsheet_df"].items():
            st.sidebar.write(f"Sheet: {sheet_name}")
            st.sidebar.dataframe(df.head())
    else:
        st.sidebar.dataframe(st.session_state["spreadsheet_df"].head())


# -------- Summarise Button --------
if "pdf_text" in st.session_state:
    if st.sidebar.button("Summarise PDF"):
        with st.spinner("Summarising PDF..."):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Summarise the following document clearly and concisely."},
                    {"role": "user", "content": st.session_state["pdf_text"]}
                ]
            )

        summary = response.choices[0].message.content

        st.session_state.messages.append({
            "role": "assistant",
            "content": f"📄 PDF Summary:\n\n{summary}"
        })

        st.success("Summary added to chat.")

# -------- Admin Controls --------
if st.session_state.admin_authenticated:
    st.sidebar.subheader("⚙ Admin Controls")

    if st.sidebar.button("Clear Conversation"):
        st.session_state.messages = []
        st.sidebar.success("Conversation cleared.")

# -----------------------------------
# MAIN CHAT AREA
# -----------------------------------

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("Ask me anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=st.session_state.messages
        )

        reply = response.choices[0].message.content

        st.session_state.messages.append({
            "role": "assistant",
            "content": reply
        })

        with st.chat_message("assistant"):
            st.markdown(reply)

    except Exception as e:
        st.error(f"Error: {e}")





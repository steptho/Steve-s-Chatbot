# web_chatbot.py
import os
import streamlit as st
from openai import OpenAI
import PyPDF2
import pandas as pd
import docx
from pptx import Presentation
import base64
import tempfile

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(
    page_title="Steve's Chatbot",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Steve's Chatbot")

# -----------------------------
# OpenAI Client
# -----------------------------
api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
org_id = os.getenv("OPENAI_ORG_ID") or st.secrets.get("OPENAI_ORG_ID")
project_id = os.getenv("OPENAI_PROJECT_ID") or st.secrets.get("OPENAI_PROJECT_ID")

if not api_key or not org_id or not project_id:
    st.error(
        "API Key, Organization ID, or Project ID not set! "
        "Please set OPENAI_API_KEY, OPENAI_ORG_ID, and OPENAI_PROJECT_ID."
    )
    st.stop()

client = OpenAI(
    api_key=api_key,
    organization=org_id,
)

# -----------------------------
# Session Memory
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -----------------------------
# File Upload Section
# -----------------------------
uploaded_file = st.file_uploader(
    "Upload PDF, CSV, Word, PowerPoint, Image or Audio",
    type=["pdf", "csv", "docx", "pptx", "jpg", "png", "mp3", "wav"]
)

file_text = ""

if uploaded_file:

    # ---------------- PDF ----------------
    if uploaded_file.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            file_text += page.extract_text() + "\n"

    # ---------------- CSV ----------------
    elif uploaded_file.type == "text/csv":
        df = pd.read_csv(uploaded_file)
        file_text = df.to_string(index=False)

    # ---------------- WORD ----------------
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(uploaded_file)
        file_text = "\n".join([para.text for para in doc.paragraphs])

    # ---------------- POWERPOINT ----------------
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
        prs = Presentation(uploaded_file)
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    file_text += shape.text + "\n"

    # ---------------- IMAGE ----------------
    elif uploaded_file.type in ["image/jpeg", "image/png"]:
        st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
        st.info("Image uploaded. You can ask questions about it.")

        image_bytes = uploaded_file.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        st.session_state.messages.append({
            "role": "system",
            "content": "User uploaded an image. Analyze it if asked."
        })

    # ---------------- AUDIO ----------------
    elif uploaded_file.type in ["audio/mpeg", "audio/wav"]:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name

        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        st.success("Voice transcribed:")
        st.write(transcript.text)

        st.session_state.messages.append({
            "role": "user",
            "content": transcript.text
        })

    # Add extracted text to conversation
    if file_text:
        st.session_state.messages.append({
            "role": "system",
            "content": file_text
        })
        st.success(f"Loaded {uploaded_file.name} into conversation.")

# -----------------------------
# User Input
# -----------------------------
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

        st.session_state.messages.append({"role": "assistant", "content": reply})

        with st.chat_message("assistant"):
            st.markdown(reply)

    except Exception as e:
        st.error(f"Error: {e}")




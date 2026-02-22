import streamlit as st
import os
import json
from datetime import datetime
from openai import OpenAI
import pandas as pd
from pypdf import PdfReader
from docx import Document
from PIL import Image
import base64


# ----------------------------
# HELPER FUNCTIONS
# ----------------------------

def generate_chat_title(text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Generate a short professional conversation title (max 6 words)."},
            {"role": "user", "content": text[:2000]}
        ],
    )
    return response.choices[0].message.content.strip().replace('"', '')


def analyse_large_text(text):
    chunk_size = 12000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    full_response = ""

    for chunk in chunks:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Analyse this document section."},
                {"role": "user", "content": chunk}
            ],
        )
        full_response += response.choices[0].message.content + "\n\n"

    return full_response

import base64

def analyse_image(uploaded_file):

    bytes_data = uploaded_file.read()
    base64_image = base64.b64encode(bytes_data).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Provide a detailed professional analysis of this image."},
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

    return response.choices[0].message.content

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Steve's Chatbot", layout="wide")
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

CHAT_DIR = "saved_chats"
os.makedirs(CHAT_DIR, exist_ok=True)

# -------------------------------------------------
# SESSION STATE SAFE INIT
# -------------------------------------------------
for key in ["messages", "current_chat_id", "uploaded_files", "spreadsheet_df"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key in ["messages", "uploaded_files"] else None

# -------------------------------------------------
# SAVE / LOAD
# -------------------------------------------------
def save_chat(chat_id):
    if chat_id:
        with open(os.path.join(CHAT_DIR, f"{chat_id}.json"), "w") as f:
            json.dump(st.session_state.messages, f, indent=2)

def load_chat(file_name):
    with open(os.path.join(CHAT_DIR, file_name), "r") as f:
        st.session_state.messages = json.load(f)
    st.session_state.current_chat_id = file_name.replace(".json", "")

# -------------------------------------------------
# SIDEBAR - CHATS
# -------------------------------------------------
st.sidebar.title("🗂 Conversations")

if st.sidebar.button("➕ New Conversation"):
    st.session_state.messages = []
    st.session_state.current_chat_id = None
    st.rerun()

st.sidebar.divider()

chat_files = sorted(
    [f for f in os.listdir(CHAT_DIR) if f.endswith(".json")],
    reverse=True
)

for file in chat_files:
    chat_id = file.replace(".json", "")
    if st.sidebar.button(chat_id):
        load_chat(file)
        st.rerun()

# -------------------------------------------------
# FILE UPLOAD
# -------------------------------------------------
st.sidebar.header("📁 Upload Files")

uploaded_files = st.sidebar.file_uploader(
    "Upload PDF, Word, Excel, Images, CSV",
    type=["pdf", "docx", "xlsx", "csv", "png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if uploaded_files:
    st.session_state.uploaded_files = uploaded_files
    st.sidebar.success(f"{len(uploaded_files)} file(s) ready")

# -------------------------------------------------
# ANALYSE BUTTON
# -------------------------------------------------
if st.sidebar.button("🔍 Analyse Uploaded Files"):

    analysis_text = ""

    for file in st.session_state.uploaded_files:

        # ---- PDF ----
        if file.name.endswith(".pdf"):
            reader = PdfReader(file)
            for page in reader.pages:
                analysis_text += page.extract_text() + "\n"

        # ---- Word ----
        elif file.name.endswith(".docx"):
            doc = Document(file)
            for para in doc.paragraphs:
                analysis_text += para.text + "\n"

        # ---- Excel ----
        elif file.name.endswith(".xlsx"):
            df = pd.read_excel(file)
            analysis_text += df.head().to_string()

        elif file.name.endswith(".csv"):
            df = pd.read_csv(file)
            analysis_text += df.head().to_string()

        # ---- Image ----
        elif file.name.endswith(("png", "jpg", "jpeg")):
            image = Image.open(file)
            buffered = base64.b64encode(file.getvalue()).decode()
            
            vision_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe and analyse this image."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{buffered}"
                                },
                            },
                        ],
                    }
                ],
            )
            
            analysis_text += vision_response.choices[0].message.content + "\n"

    if analysis_text:

        if st.session_state.current_chat_id is None:
            st.session_state.current_chat_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are analysing uploaded documents."},
                {"role": "user", "content": analysis_text[:15000]}
            ],
        )

        reply = response.choices[0].message.content

        st.session_state.messages.append({
            "role": "assistant",
            "content": reply
        })

        save_chat(st.session_state.current_chat_id)

        st.rerun()

# -------------------------------------------------
# MAIN CHAT
# -------------------------------------------------
st.title("💬 Steve's Professional Chatbot")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# -------------------------------------------------
# USER CHAT INPUT
# -------------------------------------------------
if prompt := st.chat_input("Ask something..."):

    if st.session_state.current_chat_id is None:
        st.session_state.current_chat_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=st.session_state.messages
    )

    reply = response.choices[0].message.content

    st.session_state.messages.append({"role": "assistant", "content": reply})

    with st.chat_message("assistant"):
        st.markdown(reply)

    save_chat(st.session_state.current_chat_id)


import streamlit as st
import os
import json
from datetime import datetime
from openai import OpenAI
import pandas as pd

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Steve's Chatbot", layout="wide")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

CHAT_DIR = "saved_chats"
os.makedirs(CHAT_DIR, exist_ok=True)

# -------------------------------------------------
# SAFE SESSION STATE INIT
# -------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

if "spreadsheet_df" not in st.session_state:
    st.session_state.spreadsheet_df = None

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
# SIDEBAR
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

if st.session_state.current_chat_id:
    st.sidebar.divider()
    if st.sidebar.button("🗑 Delete Current Conversation"):
        os.remove(os.path.join(CHAT_DIR, f"{st.session_state.current_chat_id}.json"))
        st.session_state.messages = []
        st.session_state.current_chat_id = None
        st.rerun()

# -------------------------------------------------
# FILE UPLOAD (ALWAYS VISIBLE)
# -------------------------------------------------
st.sidebar.header("📁 Upload Files")

uploaded_files = st.sidebar.file_uploader(
    "Upload PDF, Word, Excel, Images, CSV",
    type=["pdf", "docx", "xlsx", "csv", "png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if uploaded_files:
    for file in uploaded_files:
        if file.name not in [f.name for f in st.session_state.uploaded_files]:
            st.session_state.uploaded_files.append(file)

    st.sidebar.success(f"{len(uploaded_files)} file(s) uploaded")

# -------------------------------------------------
# HANDLE SPREADSHEETS
# -------------------------------------------------
for file in st.session_state.uploaded_files:
    if file.name.endswith(".xlsx"):
        st.session_state.spreadsheet_df = pd.read_excel(file)
    elif file.name.endswith(".csv"):
        st.session_state.spreadsheet_df = pd.read_csv(file)

if st.session_state.spreadsheet_df is not None:
    st.sidebar.divider()
    st.sidebar.subheader("📊 Spreadsheet Preview")
    st.sidebar.dataframe(st.session_state.spreadsheet_df.head())

# -------------------------------------------------
# MAIN CHAT
# -------------------------------------------------
st.title("💬 Steve's Professional Chatbot")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# -------------------------------------------------
# USER INPUT
# -------------------------------------------------
if prompt := st.chat_input("Ask something..."):

    if st.session_state.current_chat_id is None:
        st.session_state.current_chat_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    # Attach spreadsheet summary if exists
    context_messages = st.session_state.messages.copy()

    if st.session_state.spreadsheet_df is not None:
        preview_text = st.session_state.spreadsheet_df.head().to_string()
        context_messages.append({
            "role": "system",
            "content": f"Spreadsheet preview:\n{preview_text}"
        })

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=context_messages
    )

    reply = response.choices[0].message.content

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply
    })

    with st.chat_message("assistant"):
        st.markdown(reply)

    save_chat(st.session_state.current_chat_id)

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
    # Added a try/except block to ensure title generation doesn't crash the main chat
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Generate a short professional conversation title (max 6 words). Respond ONLY with the title text."},
                {"role": "user", "content": text[:2000]}
            ],
        )
        # Clean the title for filesystem compatibility
        title = response.choices[0].message.content.strip().replace('"', '').replace(':', '').replace('/', '')
        return title
    except:
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def rename_chat_file(old_id, new_title):
    """Renames the physical JSON file and updates session state."""
    old_path = os.path.join(CHAT_DIR, f"{old_id}.json")
    
    # Create a unique filename using the title
    timestamp = datetime.now().strftime("%H%M")
    new_id = f"{new_title}_{timestamp}"
    new_path = os.path.join(CHAT_DIR, f"{new_id}.json")
    
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
        st.session_state.current_chat_id = new_id
        return new_id
    return old_id

# [Keep your existing analyse_large_text and analyse_image functions here]

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
    key=lambda x: os.path.getmtime(os.path.join(CHAT_DIR, x)),
    reverse=True
)

for file in chat_files:
    # We display the filename as the button label
    display_name = file.replace(".json", "").replace("_", " ")
    if st.sidebar.button(display_name, key=file):
        load_chat(file)
        st.rerun()

# [Keep your existing FILE UPLOAD and ANALYSE BUTTON sections]

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

    # 1. Start with a temporary timestamp ID if it's a new chat
    is_new_chat = False
    if st.session_state.current_chat_id is None:
        st.session_state.current_chat_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        is_new_chat = True

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI Response
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=st.session_state.messages
    )

    reply = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": reply})

    with st.chat_message("assistant"):
        st.markdown(reply)

    # First save (with timestamp)
    save_chat(st.session_state.current_chat_id)

    # 2. TRIGGER AUTO-TITLING: If this was the first message, rename it now
    if is_new_chat:
        with st.spinner("Generating title..."):
            new_title = generate_chat_title(prompt)
            # Rename the file from timestamp to the AI-generated title
            st.session_state.current_chat_id = rename_chat_file(st.session_state.current_chat_id, new_title)
            # Re-save under the new name
            save_chat(st.session_state.current_chat_id)
            st.rerun() # Rerun to refresh the sidebar titles immediately
    else:
        save_chat(st.session_state.current_chat_id)

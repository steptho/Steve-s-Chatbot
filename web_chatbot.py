import streamlit as st
import os
import json
from datetime import datetime
from openai import OpenAI

# -----------------------------------
# 🔧 CONFIG
# -----------------------------------
st.set_page_config(page_title="Steve's Chatbot", layout="wide")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

CHAT_DIR = "saved_chats"
os.makedirs(CHAT_DIR, exist_ok=True)

# -----------------------------------
# 🧠 SESSION STATE INIT (SAFE)
# -----------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

# -----------------------------------
# 💾 SAVE FUNCTION
# -----------------------------------
def save_chat(chat_id):
    if chat_id is None:
        return
    file_path = os.path.join(CHAT_DIR, f"{chat_id}.json")
    with open(file_path, "w") as f:
        json.dump(st.session_state.messages, f, indent=2)

# -----------------------------------
# 📂 LOAD FUNCTION
# -----------------------------------
def load_chat(file_name):
    with open(os.path.join(CHAT_DIR, file_name), "r") as f:
        st.session_state.messages = json.load(f)
    st.session_state.current_chat_id = file_name.replace(".json", "")

# -----------------------------------
# 🗂 SIDEBAR – CHAT HISTORY PANEL
# -----------------------------------
st.sidebar.title("🗂 Conversations")

# ➕ New Chat
if st.sidebar.button("➕ New Conversation"):
    st.session_state.messages = []
    st.session_state.current_chat_id = None
    st.rerun()

st.sidebar.divider()

# 📜 Existing Chats
chat_files = sorted(
    [f for f in os.listdir(CHAT_DIR) if f.endswith(".json")],
    reverse=True
)

for file in chat_files:
    chat_id = file.replace(".json", "")
    if st.sidebar.button(chat_id):
        load_chat(file)
        st.rerun()

# 🗑 Delete Current Chat
if st.session_state.current_chat_id:
    st.sidebar.divider()
    if st.sidebar.button("🗑 Delete Current Conversation"):
        os.remove(os.path.join(CHAT_DIR, f"{st.session_state.current_chat_id}.json"))
        st.session_state.messages = []
        st.session_state.current_chat_id = None
        st.rerun()

# -----------------------------------
# 💬 MAIN CHAT UI
# -----------------------------------
st.title("💬 Steve's Chatbot")

# Display Messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# -----------------------------------
# ✏️ USER INPUT
# -----------------------------------
if prompt := st.chat_input("Ask something..."):

    # Create chat ID if first message
    if st.session_state.current_chat_id is None:
        st.session_state.current_chat_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    # Send to OpenAI
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=st.session_state.messages
    )

    reply = response.choices[0].message.content

    # Add assistant message
    st.session_state.messages.append({
        "role": "assistant",
        "content": reply
    })

    with st.chat_message("assistant"):
        st.markdown(reply)

    # Auto-save
    save_chat(st.session_state.current_chat_id)







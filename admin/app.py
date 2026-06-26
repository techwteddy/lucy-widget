import os
import streamlit as st
import httpx

st.set_page_config(page_title="DinqAgent Admin", page_icon="🤖", layout="wide")

# Config from env or sidebar
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
ADMIN_KEY = os.getenv("ADMIN_KEY", "")

# Sidebar
st.sidebar.title("🤖 DinqAgent Admin")
api_url = st.sidebar.text_input("API URL", value=API_BASE)
admin_key = st.sidebar.text_input("Admin Key", value=ADMIN_KEY, type="password")

if not admin_key:
    st.warning("Enter your Admin Key in the sidebar to continue.")
    st.stop()

HEADERS = {"X-Admin-Key": admin_key}
BASE = api_url.rstrip("/")


def api_get(path: str):
    try:
        r = httpx.get(f"{BASE}{path}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_post(path: str, json=None, files=None, data=None):
    try:
        r = httpx.post(f"{BASE}{path}", headers=HEADERS, json=json, files=files, data=data, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_put(path: str, json=None):
    try:
        r = httpx.put(f"{BASE}{path}", headers=HEADERS, json=json, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_delete(path: str):
    try:
        r = httpx.delete(f"{BASE}{path}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        st.error(f"API error: {e}")
        return False


# Navigation
tab1, tab2, tab3, tab4 = st.tabs(["🤖 Chatbots", "📚 Knowledge Base", "💬 Embed Code", "🔍 Health"])

# --- Tab 1: Chatbots ---
with tab1:
    st.header("Chatbots")

    col1, col2 = st.columns([2, 1])

    with col2:
        st.subheader("Create New Chatbot")
        with st.form("create_chatbot"):
            name = st.text_input("Name", placeholder="My Support Bot")
            system_prompt = st.text_area(
                "System Prompt",
                value="You are a helpful customer support assistant. Answer questions clearly and concisely based on the provided knowledge base. If you don't know something, say so honestly.",
                height=120,
            )
            welcome = st.text_input("Welcome Message", value="Hi! How can I help you today?")
            color = st.color_picker("Primary Color", value="#3B82F6")
            title = st.text_input("Chat Title", value="Chat with Lucy")
            position = st.selectbox("Position", ["bottom-right", "bottom-left"])
            owner_email = st.text_input("Owner Email (optional)")

            submitted = st.form_submit_button("Create Chatbot", type="primary")

            if submitted and name and system_prompt:
                result = api_post("/api/v1/chatbots", json={
                    "name": name,
                    "system_prompt": system_prompt,
                    "welcome_message": welcome,
                    "primary_color": color,
                    "title": title,
                    "position": position,
                    "owner_email": owner_email or None,
                })
                if result:
                    st.success(f"Created! Save your API key — it won't be shown again:")
                    st.code(result.get("api_key", ""), language="text")
                    st.session_state["last_chatbot_id"] = str(result["id"])
                    st.rerun()

    with col1:
        # We can't easily list all chatbots without a list endpoint — but we can fetch by ID
        st.subheader("Manage Chatbot")
        chatbot_id = st.text_input(
            "Chatbot ID",
            value=st.session_state.get("last_chatbot_id", ""),
            placeholder="Paste chatbot UUID here",
        )

        if chatbot_id:
            chatbot = api_get(f"/api/v1/chatbots/{chatbot_id}")
            if chatbot:
                st.json(chatbot)

                with st.expander("Edit Chatbot"):
                    with st.form("update_chatbot"):
                        u_name = st.text_input("Name", value=chatbot.get("name", ""))
                        u_prompt = st.text_area("System Prompt", value=chatbot.get("system_prompt", ""), height=100)
                        u_welcome = st.text_input("Welcome Message", value=chatbot.get("welcome_message", ""))
                        u_color = st.color_picker("Color", value=chatbot.get("primary_color", "#3B82F6"))
                        u_title = st.text_input("Title", value=chatbot.get("title", ""))
                        u_pos = st.selectbox("Position", ["bottom-right", "bottom-left"], index=0 if chatbot.get("position") == "bottom-right" else 1)

                        if st.form_submit_button("Update"):
                            api_put(f"/api/v1/chatbots/{chatbot_id}", json={
                                "name": u_name,
                                "system_prompt": u_prompt,
                                "welcome_message": u_welcome,
                                "primary_color": u_color,
                                "title": u_title,
                                "position": u_pos,
                            })
                            st.success("Updated!")
                            st.rerun()

                if st.button("Delete Chatbot", type="secondary"):
                    if api_delete(f"/api/v1/chatbots/{chatbot_id}"):
                        st.success("Deleted (soft)")
                        st.session_state.pop("last_chatbot_id", None)
                        st.rerun()

# --- Tab 2: Knowledge Base ---
with tab2:
    st.header("Knowledge Base")
    kb_chatbot_id = st.text_input(
        "Chatbot ID",
        value=st.session_state.get("last_chatbot_id", ""),
        key="kb_chatbot_id",
        placeholder="Paste chatbot UUID",
    )

    if kb_chatbot_id:
        # List existing docs
        docs = api_get(f"/api/v1/chatbots/{kb_chatbot_id}/documents")
        if docs:
            st.subheader(f"Documents ({len(docs)})")
            for doc in docs:
                status_icon = {"processed": "✅", "pending": "⏳", "failed": "❌", "processing": "🔄"}.get(doc["status"], "❓")
                cols = st.columns([3, 1, 1, 1])
                cols[0].write(f"{status_icon} **{doc['filename']}**")
                cols[1].write(f"{doc['chunk_count']} chunks")
                cols[2].write(doc["status"])
                if cols[3].button("Delete", key=f"del_{doc['id']}"):
                    if api_delete(f"/api/v1/chatbots/{kb_chatbot_id}/documents/{doc['id']}"):
                        st.success(f"Deleted {doc['filename']}")
                        st.rerun()
                if doc.get("error_message"):
                    st.error(f"Error: {doc['error_message']}")
        elif docs is not None:
            st.info("No documents yet. Upload one below.")

        st.divider()
        st.subheader("Upload Document")
        uploaded = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"])
        if uploaded and st.button("Upload", type="primary"):
            files = {"file": (uploaded.name, uploaded.read(), uploaded.type)}
            result = api_post(f"/api/v1/chatbots/{kb_chatbot_id}/documents", files=files)
            if result:
                st.success(f"Uploaded: {result['filename']} (status: {result['status']})")
                st.rerun()

# --- Tab 3: Embed Code ---
with tab3:
    st.header("Embed Code Generator")
    embed_id = st.text_input(
        "Chatbot ID",
        value=st.session_state.get("last_chatbot_id", ""),
        key="embed_id",
        placeholder="Paste chatbot UUID",
    )
    embed_api_key = st.text_input("API Key (from creation)", placeholder="cbk_...", type="password")
    embed_color = st.color_picker("Primary Color", value="#3B82F6", key="embed_color")
    embed_title = st.text_input("Chat Title", value="Chat with Lucy", key="embed_title")
    embed_pos = st.selectbox("Position", ["bottom-right", "bottom-left"], key="embed_pos")
    embed_host = st.text_input("API Host", value="https://dinqagent.dinqdigital.com")

    if embed_id:
        embed_code = f"""<!-- Paste this before </body> on your website -->
<script src="{embed_host}/widget/lucy.min.js"
        data-chatbot-id="{embed_id}"
        data-api-key="{embed_api_key}"
        data-position="{embed_pos}"
        data-primary-color="{embed_color}"
        data-title="{embed_title}"></script>"""

        st.subheader("Your Embed Code")
        st.code(embed_code, language="html")
        st.info("Copy this snippet and paste it into any HTML page, just before the `</body>` tag.")

        st.subheader("Live Preview")
        iframe_html = f"""
<iframe
  src="{embed_host}/widget/demo"
  width="100%"
  height="400"
  style="border:1px solid #e2e8f0; border-radius: 8px;"
  title="Widget preview">
</iframe>"""
        st.components.v1.html(iframe_html, height=420)

# --- Tab 4: Health ---
with tab4:
    st.header("API Health")
    if st.button("Check Health"):
        health = api_get("/health")
        if health:
            col1, col2, col3 = st.columns(3)
            col1.metric("Status", health.get("status", "unknown").upper())
            col2.metric("Database", "✅ OK" if health.get("db_ok") else "❌ Down")
            col3.metric("Redis", "✅ OK" if health.get("redis_ok") else "❌ Down")

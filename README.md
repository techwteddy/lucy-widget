![Tests](https://img.shields.io/badge/tests-61%20passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![Claude](https://img.shields.io/badge/Claude-Sonnet-blueviolet)
![CI](https://github.com/ChunkyTortoise/chatbot-widget/actions/workflows/ci.yml/badge.svg)

# Chatbot Widget

Add an AI-powered chat bubble to any website with a single script tag.

```html
<script src="https://chatbot-widget-api.onrender.com/widget/chatbot.min.js"
        data-chatbot-id="YOUR_CHATBOT_ID"
        data-api-key="YOUR_API_KEY"
        data-primary-color="#3B82F6"
        data-title="Chat with us"></script>
```

## Features

- **Drop-in embed** — one script tag, zero dependencies, no framework required
- **Streaming responses** — token-by-token output via WebSocket
- **RAG knowledge base** — upload PDFs/text docs, chatbot answers from them
- **Shadow DOM isolation** — no CSS conflicts with the host page
- **Customizable** — colors, position, title, welcome message
- **Mobile responsive** — full-screen on mobile, floating on desktop
- **Session persistence** — conversation continues on page refresh

## Stack

- **Backend**: FastAPI + PostgreSQL (pgvector) + Redis
- **LLM**: Claude claude-sonnet-4-6 (Anthropic)
- **Embeddings**: sentence-transformers `all-MiniLM-L6-v2` (384-dim)
- **Widget**: Vanilla JS, Shadow DOM, ~14KB
- **Admin**: Streamlit dashboard
- **Deploy**: Render

## API

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health` | — | Health check |
| `POST` | `/api/v1/chatbots` | Admin key | Create chatbot, returns API key |
| `GET` | `/api/v1/chatbots/{id}` | Admin key | Get chatbot config |
| `PUT` | `/api/v1/chatbots/{id}` | Admin key | Update chatbot |
| `DELETE` | `/api/v1/chatbots/{id}` | Admin key | Soft delete |
| `GET` | `/api/v1/chatbots/{id}/widget-config` | — | Public display config |
| `POST` | `/api/v1/chatbots/{id}/documents` | Admin key | Upload PDF/TXT to knowledge base |
| `GET` | `/api/v1/chatbots/{id}/documents` | Admin key | List knowledge base docs |
| `POST` | `/api/v1/chat/{id}` | — | REST chat (non-streaming) |
| `WS` | `/ws/chat/{id}` | — | WebSocket streaming chat |
| `GET` | `/widget/chatbot.min.js` | — | Serve widget script |

## Local Development

```bash
# Start Postgres + Redis
docker-compose up -d

# Install dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Copy env
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY

# Start API
uvicorn api.main:app --reload

# Start admin dashboard (separate terminal)
streamlit run admin/app.py
```

Visit `http://localhost:8000/widget/demo` to see the widget.

## Tests

```bash
pytest tests/ -v
```

38 tests covering: chunker, embedder, doc processor, chatbot CRUD, chat service, WebSocket.

## Deploy to Render

1. Connect this repo to Render
2. Use `render.yaml` — it provisions API, Postgres, and Redis automatically
3. Set `ANTHROPIC_API_KEY` in Render dashboard environment variables

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `ADMIN_KEY` | Yes | Protects management endpoints |
| `SECRET_KEY` | Yes | App secret (auto-generated on Render) |

## Widget Options

| Attribute | Default | Description |
|-----------|---------|-------------|
| `data-chatbot-id` | required | Chatbot UUID from API |
| `data-api-key` | optional | API key for authenticated access |
| `data-position` | `bottom-right` | `bottom-right` or `bottom-left` |
| `data-primary-color` | `#3B82F6` | Hex color for bubble and header |
| `data-title` | `Chat with us` | Header title text |

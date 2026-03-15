# chatbot-widget

## Stack
- **Backend**: FastAPI + PostgreSQL/pgvector + Redis + Claude claude-sonnet-4-6 + google-genai (Gemini Embedding)
- **Frontend**: Vanilla JS widget (Shadow DOM, no framework)
- **Admin**: Streamlit
- **Deploy**: Render (chatbot-widget-api.onrender.com)

## Architecture
```
widget/src/chatbot.js   — Embedded widget (single script tag)
api/main.py             — FastAPI app entry point
api/config.py           — Pydantic settings
api/models/             — SQLAlchemy async models
api/services/           — RAG pipeline (embedder, chunker, retriever, chat_service, doc_processor)
api/routes/             — HTTP + WebSocket routes
admin/app.py            — Streamlit admin dashboard
tests/                  — pytest suite
```

## Tests
```bash
pytest tests/ -v
```

## Local Dev
```bash
docker-compose up -d  # Start Postgres + Redis
uvicorn api.main:app --reload  # Start API
streamlit run admin/app.py  # Start admin
```

## Environment
Required env vars:
- DATABASE_URL
- REDIS_URL
- ANTHROPIC_API_KEY
- ADMIN_KEY (protect management endpoints)
- SECRET_KEY

## Key Endpoints
- GET /health
- POST /api/v1/chatbots (X-Admin-Key required)
- GET /api/v1/chatbots/{id}/widget-config (public)
- POST /api/v1/chat/{id} (REST chat)
- WS /ws/chat/{id}?session_id=&api_key= (streaming)
- GET /widget/chatbot.min.js (serves the JS widget)

## Widget Embed
```html
<script src="https://chatbot-widget-api.onrender.com/widget/chatbot.min.js"
        data-chatbot-id="UUID"
        data-api-key="cbk_..."
        data-primary-color="#3B82F6"
        data-title="Chat with us"></script>
```

![Tests](https://img.shields.io/badge/tests-139%20passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![Next.js](https://img.shields.io/badge/Next.js-16.2-000000)
![Claude](https://img.shields.io/badge/Claude-Sonnet-blueviolet)
![CI](https://github.com/ChunkyTortoise/chatbot-widget/actions/workflows/ci.yml/badge.svg)

# Chatbot Widget SaaS

Embeddable AI chatbot with full SaaS infrastructure — auth, billing, RAG knowledge base, analytics, and a Next.js 15 dashboard. Drop a single `<script>` tag on any website and get a streaming AI chat widget backed by Claude, pgvector retrieval, and Stripe subscriptions.

```html
<script src="https://your-api.com/widget/chatbot.min.js"
        data-chatbot-id="YOUR_CHATBOT_ID"
        data-api-key="YOUR_API_KEY"
        data-primary-color="#3B82F6"
        data-title="Chat with us"></script>
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        End User's Website                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Widget (Shadow DOM, ~14KB, vanilla JS, zero dependencies)│  │
│  │  WebSocket streaming  ·  session persistence  ·  mobile   │  │
│  └──────────────────────────────┬────────────────────────────┘  │
└─────────────────────────────────┼───────────────────────────────┘
                                  │ WS / REST
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Python)                     │
│                                                                 │
│  Auth (Supabase JWT)  ·  Billing (Stripe)  ·  Quota Enforcement │
│  RAG Pipeline: chunk → embed → retrieve → Claude LLM            │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐          │
│  │PostgreSQL│  │  Redis   │  │  pgvector (768-dim)   │          │
│  │ chatbots │  │ sessions │  │  document embeddings  │          │
│  │ convos   │  │ quotas   │  │  Gemini Embedding      │          │
│  │ messages │  │ plans    │  │                        │          │
│  └──────────┘  └──────────┘  └──────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                                  ▲
                                  │ Supabase JWT
┌─────────────────────────────────────────────────────────────────┐
│              Next.js 16.2 Dashboard (TypeScript)                 │
│  Supabase Auth  ·  Chatbot CRUD  ·  Analytics  ·  Conversations │
│  Billing Portal  ·  Tailwind CSS  ·  Vitest                    │
└─────────────────────────────────────────────────────────────────┘
```

### Shadow DOM Widget Isolation

The embeddable chat widget uses Shadow DOM for complete isolation:
- Zero CSS conflicts with the host page styles
- ~14KB minified bundle with no framework dependency
- Security boundary: widget DOM is inaccessible to host page scripts
- Drop-in embed: `<script src="widget.js" data-chatbot-id="..."></script>`

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **API** | FastAPI, Python 3.12+, async SQLAlchemy, Pydantic v2 |
| **LLM** | Claude Sonnet (Anthropic) |
| **Embeddings** | Gemini Embedding via `google-genai` (768-dim) |
| **Vector Store** | pgvector on PostgreSQL 16 |
| **Cache / State** | Redis 7 (sessions, quotas, subscription state) |
| **Auth** | Supabase JWT (signup/login/me) |
| **Billing** | Stripe Checkout + Customer Portal + Webhooks |
| **Dashboard** | Next.js 16.2, TypeScript, Tailwind CSS, Supabase JS |
| **Widget** | Vanilla JS, Shadow DOM isolation, ~14KB minified |
| **CI** | GitHub Actions |

## API Reference

### Health

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health` | -- | Health check (db + redis status) |

### Auth

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/signup` | -- | Create account (Supabase), returns JWT |
| `POST` | `/auth/login` | -- | Login, returns JWT |
| `GET` | `/auth/me` | Bearer JWT | Current user info |

### Chatbots

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/v1/chatbots` | Bearer JWT | List user's chatbots |
| `POST` | `/api/v1/chatbots` | `X-Admin-Key` | Create chatbot (admin) |
| `POST` | `/api/v1/chatbots/me` | Bearer JWT | Create chatbot (user) |
| `GET` | `/api/v1/chatbots/{id}` | `X-Admin-Key` | Get chatbot details |
| `PUT` | `/api/v1/chatbots/{id}` | `X-Admin-Key` | Update chatbot |
| `DELETE` | `/api/v1/chatbots/{id}` | `X-Admin-Key` | Soft-delete chatbot |
| `GET` | `/api/v1/chatbots/{id}/widget-config` | -- | Public widget display config |

### Documents (RAG Knowledge Base)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/chatbots/{id}/documents` | `X-Admin-Key` | Upload PDF/TXT (max 10MB) |
| `GET` | `/api/v1/chatbots/{id}/documents` | `X-Admin-Key` | List knowledge base docs |
| `DELETE` | `/api/v1/chatbots/{id}/documents/{doc_id}` | `X-Admin-Key` | Delete document + chunks |

### Chat

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/chat/{id}` | API key (optional) | REST chat (non-streaming) |
| `WS` | `/ws/chat/{id}?session_id=&api_key=` | API key (optional) | WebSocket streaming chat |

### Analytics

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/v1/chatbots/{id}/analytics` | Bearer JWT | Message count, conversation count, avg messages |
| `GET` | `/api/v1/chatbots/{id}/conversations` | Bearer JWT | Recent conversations (paginated) |

### Billing

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/billing/checkout` | Bearer JWT | Create Stripe Checkout session |
| `POST` | `/billing/portal` | Bearer JWT | Open Stripe Customer Portal |
| `POST` | `/billing/webhook` | Stripe signature | Handle subscription lifecycle events |

### Widget

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/widget/chatbot.js` | -- | Serve widget source |
| `GET` | `/widget/chatbot.min.js` | -- | Serve minified widget |
| `GET` | `/widget/demo` | -- | Interactive widget demo page |
| `GET` | `/demo` | -- | Portfolio-quality demo page with live widget embed |
| `POST` | `/auth/demo-login` | -- | Demo login (returns `demo-token`; requires `DEMO_MODE=true`) |

## Plan Tiers

| | **Free** | **Pro** ($49/mo) | **Business** ($149/mo) |
|---|---------|-----------------|----------------------|
| Messages/month | 100 | 5,000 | 50,000 |
| Chatbots | 1 | 5 | Unlimited |
| Knowledge base | 10MB | 500MB | Unlimited |
| Analytics | Basic | Full | Full + export |
| Support | Community | Email | Priority |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Yes | Redis connection string |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude |
| `ADMIN_KEY` | Yes | Protects admin management endpoints (`X-Admin-Key` header) |
| `SECRET_KEY` | Yes | Application secret key |
| `SUPABASE_URL` | Yes* | Supabase project URL (required for auth) |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes* | Supabase service role key (required for auth) |
| `SUPABASE_JWT_SECRET` | Yes* | JWT secret for token verification (required for auth) |
| `STRIPE_SECRET_KEY` | Yes* | Stripe secret key (required for billing) |
| `STRIPE_WEBHOOK_SECRET` | Yes* | Stripe webhook signing secret (required for billing) |
| `STRIPE_PRO_PRICE_ID` | No | Stripe Price ID for Pro plan |
| `STRIPE_BUSINESS_PRICE_ID` | No | Stripe Price ID for Business plan |
| `DEMO_MODE` | No | Enable demo login + demo chatbot resolution (`true`/`false`, default `false`) |
| `NEXT_PUBLIC_DEMO_MODE` | No | Show "Try Demo" button on dashboard login page (`true`/`false`) |
| `NEXT_PUBLIC_API_URL` | No | Backend API URL for dashboard (defaults to `http://localhost:8000`) |

*Required for production. API runs without these in development mode.

## Live Demo

- **Widget demo page**: `GET /demo` — portfolio-quality showcase with live widget, copy-paste embed snippet, and cold-start indicator
- **Admin dashboard**: Next.js dashboard with demo login (no Supabase account needed when `NEXT_PUBLIC_DEMO_MODE=true`)

Run locally:
```bash
DEMO_MODE=true uvicorn api.main:app --reload
# then open http://localhost:8000/demo
```

## Self-Hosting

```bash
git clone https://github.com/ChunkyTortoise/chatbot-widget.git
cd chatbot-widget
cp .env.example .env
# Edit .env with your credentials

docker-compose up -d
```

This starts PostgreSQL 16 (with pgvector), Redis 7, and the FastAPI API on port 8000.

## Development Setup

### API (Python)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start infrastructure
docker-compose up -d db redis

# Run API
uvicorn api.main:app --reload
```

### Dashboard (Next.js 16.2)

```bash
cd dashboard
npm install
npm run dev
```

### Widget

```bash
# Build minified widget
make widget
# Output: widget/dist/chatbot.min.js
```

Visit `http://localhost:8000/widget/demo` to see the widget in action.

## Tests

```bash
# Python (130 tests)
pytest tests/ -v

# Dashboard TypeScript (9 tests)
cd dashboard && npm test

# Total: 139 tests
```

## Widget Embed Options

| Attribute | Default | Description |
|-----------|---------|-------------|
| `data-chatbot-id` | *required* | Chatbot UUID from API |
| `data-api-key` | -- | API key for authenticated access |
| `data-position` | `bottom-right` | `bottom-right` or `bottom-left` |
| `data-primary-color` | `#3B82F6` | Hex color for bubble and header |
| `data-title` | `Chat with us` | Header title text |

## Deploy to Render

1. Connect this repo to [Render](https://render.com)
2. Use `render.yaml` -- provisions API, PostgreSQL, and Redis automatically
3. Set environment variables in the Render dashboard

## Certifications Applied

Skills from completed certifications applied in this project:

| Domain Pillar | Certifications | Applied In |
|--------------|----------------|------------|
| GenAI & LLM Engineering | Google Generative AI, Anthropic Prompt Engineering, DeepLearning.AI | Claude Haiku/Gemini Flash chat completion, KB semantic search |
| RAG & Knowledge Systems | DeepLearning.AI RAG, LangChain & Vector DBs | pgvector semantic search, multi-tenant KB with quota enforcement |
| Cloud & MLOps | Google Cloud, IBM DevOps, GitHub Actions | Render Blueprint deploy, Redis caching, CI coverage + security gates |
| Deep Learning & AI Foundations | DeepLearning.AI specializations | Embedding model selection, vector similarity scoring |

## License

MIT

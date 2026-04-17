# Case Study: Embeddable AI Chatbot Widget SaaS

**One-liner:** A production-grade embeddable AI chatbot SaaS that replaces $49-$2,500/mo platforms like Chatbase and Intercom with an open-source alternative featuring pgvector RAG, WebSocket streaming, multi-tenant billing, and 148 automated tests.

---

## Problem

Businesses want AI-powered chat on their websites but face two bad options: pay $49-$2,500/mo for platforms like Chatbase, Intercom, or Drift, or build from scratch. Most solutions are closed-source, lack true multi-tenancy, and require complex iframe embeds that clash with host page styling.

## Solution

A single `<script>` tag drops a 14KB Shadow DOM widget onto any website. The widget connects via WebSocket to a FastAPI backend with a full RAG pipeline (pgvector + Gemini embeddings), Stripe billing, and a Next.js dashboard for management.

---

## Architecture

```
End User's Website
  Widget (Shadow DOM, ~14KB, vanilla JS)
  WebSocket streaming  |  session persistence  |  mobile responsive
        |
        v  WS / REST
FastAPI Backend (Python 3.12, async)
  Auth (Supabase JWT)  |  Billing (Stripe)  |  Quota Enforcement
  RAG Pipeline: chunk -> embed -> retrieve -> Claude LLM
  Webhook Events: HMAC-signed, retry w/ backoff, dead-letter tracking
  Escalation Detection: RAG confidence scoring + Slack notifications
        |
  PostgreSQL 16 + pgvector  |  Redis 7  |  Gemini Embedding (768-dim)
        ^
  Next.js 16.2 Dashboard (TypeScript, Tailwind, Recharts)
```

---

## Key Decisions and Tradeoffs

### 1. Shadow DOM vs. iframe for Widget Isolation

**Chose:** Shadow DOM
**Alternatives considered:** iframe (full JS isolation, slower), plain DOM injection (no isolation)

Shadow DOM provides complete CSS isolation without the performance penalty of an iframe (4.5x faster load). The tradeoff is no JavaScript isolation from the host page, but for a chat widget this is acceptable. The widget attaches to the host document's DOM via `attachShadow()`, so all styles are scoped and zero CSS conflicts occur regardless of what framework the host page uses.

Result: ~14KB bundle, zero dependencies, drops into any page with one line of HTML.

### 2. pgvector vs. ChromaDB vs. Pinecone for Vector Storage

**Chose:** pgvector on PostgreSQL 16
**Alternatives considered:** ChromaDB (simpler, no managed hosting), Pinecone (managed, expensive)

pgvector runs as a PostgreSQL extension, meaning one database handles both relational data (chatbots, conversations, users, billing) and vector similarity search. No additional infrastructure to manage. ChromaDB would require a separate server; Pinecone would add $70+/mo cost and vendor lock-in.

Result: Single database, HNSW index for cosine similarity, 768-dim Gemini embeddings.

### 3. Gemini Embedding vs. OpenAI Embedding

**Chose:** Google Gemini Embedding (768-dim)
**Alternatives considered:** OpenAI `text-embedding-3-small` (1536-dim), Sentence Transformers (local)

Gemini embedding is free-tier accessible and produces competitive results at 768 dimensions. OpenAI charges per token and produces 1536-dim vectors (2x storage). Running Sentence Transformers locally would eliminate API dependency but require GPU resources for production throughput.

Result: Lower cost, smaller vectors, no single-provider lock-in (LLM uses Claude, embeddings use Gemini).

### 4. WebSocket Streaming vs. SSE vs. REST Polling

**Chose:** WebSocket for real-time token streaming
**Alternatives considered:** Server-Sent Events (simpler, one-directional), REST polling (highest latency)

WebSocket enables bidirectional communication needed for features like typing indicators and real-time session management. SSE would work for one-way streaming but limits future extensibility. The widget implements automatic reconnection with exponential backoff for reliability.

Result: Sub-100ms time-to-first-token perception, smooth streaming UX matching ChatGPT-quality.

### 5. HMAC-Signed Webhook Delivery vs. Simple POST

**Chose:** HMAC-SHA256 signed payloads with exponential backoff retry and dead-letter tracking
**Alternatives considered:** Simple unauthenticated POST (easier, insecure), queue-based delivery (heavier infrastructure)

Webhook recipients need to verify payload authenticity. HMAC-SHA256 signing (the same pattern Stripe and Twilio use) lets receivers validate that the payload hasn't been tampered with. Dead-letter tracking ensures no events are silently lost. This avoids the operational overhead of a separate message queue while still providing delivery guarantees.

Result: 3 event types (conversation.started, message.created, lead.captured), 3-retry backoff, delivery audit trail.

---

## RAG Pipeline Deep Dive

**Ingestion Flow:**
1. User uploads PDF/TXT via dashboard
2. `doc_processor.py` extracts text (PyMuPDF for PDFs)
3. `chunker.py` splits into ~400-char chunks with 50-char overlap
4. `embedder.py` generates 768-dim vectors via Gemini Embedding API
5. Chunks stored in `document_chunks` table with pgvector `HNSW` index

**Retrieval Flow:**
1. User sends message via widget
2. Message embedded via Gemini (same model as ingestion)
3. `retriever.py` performs cosine similarity search against chatbot's chunks
4. Top-5 chunks injected as context into Claude's system prompt
5. If best chunk distance > 0.7, conversation flagged for human review (escalation detection)

---

## Multi-Tenant Security Model

- **Tenant isolation**: Every chatbot, document, conversation, and lead is scoped to a `chatbot_id` FK. No cross-tenant data access.
- **Auth layers**: Supabase JWT for dashboard users, SHA-256 hashed API keys for widget embed authentication.
- **API key design**: Raw keys are never stored. Widget exposes a public-scoped key that is rate-limited (10 msgs/60s per session) and quota-bounded (100-50,000 msgs/mo by plan).
- **Admin separation**: `X-Admin-Key` header for management endpoints, JWT bearer for user-scoped endpoints.

---

## SaaS Billing Architecture

Three tiers enforced via Redis-cached plan state:

| | Free | Pro ($49/mo) | Business ($149/mo) |
|---|---|---|---|
| Messages/month | 100 | 5,000 | 50,000 |
| Chatbots | 1 | 5 | Unlimited |
| Knowledge base | 10MB | 500MB | Unlimited |

- **Stripe Checkout** creates subscription sessions
- **Stripe Customer Portal** handles plan changes and cancellations
- **Webhook handler** processes `customer.subscription.created/updated/deleted` events
- **Quota enforcement**: Redis TTL-based monthly counters (O(1) check per message)
- **Knowledge base quota**: Per-plan document size limits checked at upload time

---

## Testing Strategy

**161 tests** across Python (pytest) and TypeScript (Vitest):

- **Unit tests**: Service-level (chat, embedder, retriever, chunker, doc_processor, webhook_dispatcher)
- **Route tests**: Every API endpoint tested with mock DB, mock Redis, mock Anthropic
- **Integration tests**: Webhook dispatch, lead capture with webhook events, escalation detection with Slack notification
- **Security tests**: Rate limiting, quota enforcement, JWT validation, API key verification
- **CI gates**: 80% coverage floor (`--cov-fail-under=80`), mypy type-checking, bandit security scan, pip-audit dependency audit

---

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Widget bundle size | ~14KB minified (no gzip, no framework) |
| Widget isolation method | Shadow DOM (4.5x faster than iframe) |
| Embedding dimensions | 768 (Gemini, half the size of OpenAI 1536-dim) |
| RAG retrieval | pgvector HNSW index, cosine similarity, top-5 chunks |
| Rate limiting | 10 messages per 60 seconds per session (Redis-backed) |
| Quota check | O(1) Redis GET per message |
| Webhook delivery | 3 retries with exponential backoff (2s, 4s, 8s) |

---

## What I Would Improve

1. **Multi-provider LLM routing**: Add configurable primary/fallback providers (Claude -> Gemini -> GPT) with automatic failover and per-provider cost tracking.
2. **Conversation handoff UI**: Build a live agent interface where support staff can take over from the AI mid-conversation, with socket-based real-time messaging.
3. **Widget A/B testing**: Test different welcome messages, system prompts, or chat flows to optimize conversion rates.
4. **Response quality evaluation**: Integrate RAGAS or custom evaluation framework to measure RAG retrieval quality and answer accuracy at scale.
5. **Horizontal scaling**: Current architecture is single-process. Add Redis pub/sub for WebSocket fanout across multiple API instances behind a load balancer.

---

## Certification Alignment

| Certification | Applied In This Project |
|---|---|
| IBM Generative AI Engineering | Claude streaming chat, WebSocket token delivery, system prompt engineering |
| IBM RAG and Agentic AI | pgvector RAG pipeline, Gemini 768-dim embeddings, document chunking/retrieval |
| Vanderbilt ChatGPT Automation | Embeddable chatbot automation, configurable system prompts per tenant |
| Duke LLMOps | CI/CD hardening (coverage gate, mypy, security scanning), deployment pipeline |
| Google Cloud GenAI Leader | Cloud SaaS deployment, managed database services |
| DeepLearning.AI Deep Learning | 768-dim vector embeddings, cosine similarity scoring, HNSW indexing |
| IBM AI and ML Engineering | Async ML pipeline, quota enforcement, rate limiting architecture |
| Python for Everybody | Async Python backend (FastAPI, SQLAlchemy, asyncpg) |

---

## Links

- **GitHub**: [ChunkyTortoise/chatbot-widget](https://github.com/ChunkyTortoise/chatbot-widget)
- **Dashboard**: [chatbot-widget-dashboard.vercel.app](https://chatbot-widget-dashboard.vercel.app)
- **License**: MIT

---
research_for: 2026-03-19-feature-chatbot-widget-saas-launch-spec
date: 2026-03-19
---

# Research: chatbot-widget SaaS Launch

## Current State Audit

**Test counts**
- pytest: 119 passing (16 test files under `tests/`)
- Vitest: 9 passing (dashboard component tests)
- Total: 128 passing

**Test files (pytest)**:
`test_analytics.py`, `test_auth.py`, `test_billing.py`, `test_chat.py`, `test_chatbot_quota.py`,
`test_chatbots.py`, `test_demo.py`, `test_demo_mode.py`, `test_doc_processor.py`,
`test_documents.py`, `test_health.py`, `test_kb_quota.py`, `test_rag.py`, `test_timeseries.py`,
`test_websocket.py` + `conftest.py`

**Coverage**: pytest-cov is installed and CI runs `--cov=api --cov-report=term-missing`, but
`--cov-fail-under` is NOT set. Coverage is collected but not enforced. Current level unknown
without a local run.

**Deployment status**: Nothing is live. render.yaml and dashboard/vercel.json both exist but
no services have been provisioned.

**Demo mode**: Fully implemented. `api/seed.py` creates a demo chatbot, conversation, and two
messages. `api/main.py` lifespan hook calls `seed_demo_data()` when `settings.demo_mode` is True.
The seed is idempotent (checks for existing demo chatbot before inserting).

**CASE_STUDY.md**: Does not exist.

**Screenshots**: `docs/screenshots/` directory exists but is empty.

---

## render.yaml Analysis

**File**: `/Users/cave/Projects/chatbot-widget/render.yaml`

**Current services**:
```yaml
services:
  - type: web
    name: chatbot-widget-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn api.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL           # auto-wired from chatbot-widget-db
      - key: REDIS_URL              # auto-wired from chatbot-widget-redis
      - key: ANTHROPIC_API_KEY      # sync: false (manual entry required)
      - key: ADMIN_KEY              # generateValue: true
      - key: SECRET_KEY             # generateValue: true

databases:
  - name: chatbot-widget-db         # PostgreSQL 16, starter plan
  - name: chatbot-widget-redis      # Redis, starter plan (type not explicit in yaml)
```

**What's missing**:
- `DEMO_MODE=true` — without this, seed_demo_data() never runs and the demo page has no chatbot
- `ENVIRONMENT=production` — without this, the Pydantic validator in `api/config.py` won't check
  for dev-default secrets (ADMIN_KEY and SECRET_KEY are auto-generated so that's fine, but
  SUPABASE_JWT_SECRET defaults to `dev-jwt-secret` which will fail validation in production mode)
- `SUPABASE_JWT_SECRET` as `sync: false` — required for any JWT auth to work
- `GEMINI_API_KEY` as `sync: false` — required for document embedding (RAG KB upload)
- No `preDeployCommand` needed — the lifespan hook handles seeding on startup

**Redis type note**: render.yaml declares both the PostgreSQL DB and Redis under `databases:`.
Render's Blueprint spec uses `type: redis` for Redis under `services:` not `databases:`. The
current yaml may need correction — confirm against Render Blueprint docs before deploy.

**Intended final state** (new env vars to add):
```yaml
- key: DEMO_MODE
  value: "true"
- key: ENVIRONMENT
  value: production
- key: SUPABASE_JWT_SECRET
  sync: false
- key: GEMINI_API_KEY
  sync: false
```

---

## vercel.json Analysis

**File**: `/Users/cave/Projects/chatbot-widget/dashboard/vercel.json`

**Current content**:
```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "outputDirectory": ".next"
}
```

This is minimal and correct for a Next.js 15 deploy. Nothing is wrong here.

**What's missing**:
- `NEXT_PUBLIC_API_URL` must be set as a Vercel environment variable pointing to the Render URL.
  This cannot be hardcoded in vercel.json because the Render URL is not known until Wave 3a.
- `NEXT_PUBLIC_DEMO_MODE=true` must be set to show the "Try Demo" button on the login page.
  The login page already has the conditional: `{process.env.NEXT_PUBLIC_DEMO_MODE === 'true' && ...}`

**Next.js version**: package.json shows `"next": "16.2.0"` — this is newer than the README badge
which says Next.js 15. Minor discrepancy; not a blocker.

---

## CI/CD Analysis

**File**: `/Users/cave/Projects/chatbot-widget/.github/workflows/ci.yml`

**Trigger**: `on: [push, pull_request]`

**Services spun up**: PostgreSQL 15, Redis 7

**Steps**:
1. checkout, setup-python 3.12, pip install -r requirements.txt
2. pip install ruff pytest pytest-asyncio pytest-cov
3. Lint: `ruff check api/ tests/ --ignore E501`
4. Test: `pytest tests/ -q --tb=short --cov=api --cov-report=term-missing`
5. setup-node 20
6. Test dashboard: `cd dashboard && npm ci && npm test`

**Missing**:
- `--cov-fail-under=80` on the pytest run (coverage collected but not enforced)
- mypy is not installed and has no step in the workflow
- No `types-redis` or mypy stubs for any dependency

**Python version in CI vs local**: CI uses 3.12 which matches requirements and README badge.

**PostgreSQL version mismatch**: CI uses postgres:15 but render.yaml provisions postgres:16.
This is low risk (no 16-specific SQL features in use based on codebase review) but worth noting.

---

## API Architecture

**Entry point**: `api/main.py`
- Lifespan: creates pgvector extension, runs `Base.metadata.create_all`, optionally seeds demo data
- Middleware: CORS (allow_origins=["*"]), request ID header
- Global exception handler: returns 500 JSON

**Key routes**:
- `GET /health` — checks db ping + redis ping, returns `{status, db_ok, redis_ok}`
- `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` — Supabase JWT auth
- `POST /auth/demo-login` — demo-only login (gated by DEMO_MODE)
- `GET|POST /api/v1/chatbots` — list/create chatbots
- `POST /api/v1/chatbots/{id}/documents` — upload PDF/TXT for RAG KB
- `POST /api/v1/chat/{id}` — REST chat (non-streaming)
- `WS /ws/chat/{id}` — WebSocket streaming chat
- `GET /api/v1/chatbots/{id}/analytics` — message count, conversation count
- `POST /billing/checkout`, `/billing/portal`, `/billing/webhook` — Stripe
- `GET /widget/chatbot.min.js` — serves the widget JS
- `GET /demo` — serves `api/static/demo.html` (portfolio demo page)

**Demo mode behavior**: `settings.demo_mode = True` when `DEMO_MODE=true` env var is set.
The lifespan hook seeds one chatbot (id is UUID generated at runtime, name "Demo Assistant",
api_key_hash = sha256("cbk_demo_key_for_testing")), one conversation, and two messages.
The demo chatbot ID changes on each fresh database. The demo HTML page at `/demo` needs to
know this ID — check `api/static/demo.html` to see how it resolves the demo chatbot ID.

---

## Dashboard Architecture

**Framework**: Next.js 16.2.0 (listed as 15 in README badge — minor badge lag)
**Auth**: Supabase JS client, JWT stored in localStorage
**API connection**: `dashboard/lib/api.ts` reads `process.env.NEXT_PUBLIC_API_URL` — all API
calls are prefixed with this base URL. If unset, all fetch calls will be to `undefinedpath`.

**Pages**:
- `/login` — email/password + demo login button (gated by NEXT_PUBLIC_DEMO_MODE)
- `/dashboard` — chatbot list, fetches `GET /api/v1/chatbots` with Bearer token
- `/dashboard/new` — create chatbot form
- `/dashboard/[id]` — chatbot detail (analytics, embed snippet)
- `/dashboard/[id]/knowledge` — KB document upload
- `/dashboard/[id]/conversations` — conversation history
- `/dashboard/billing` — Stripe checkout/portal

**Vitest tests**: 9 tests in `dashboard/tests/` — component-level tests.

**Key env vars needed for Vercel**:
- `NEXT_PUBLIC_API_URL` — required, must be set after Render deploy
- `NEXT_PUBLIC_DEMO_MODE` — set to "true" to enable demo login button
- `NEXT_PUBLIC_SUPABASE_URL` — needed for Supabase JS client (if used directly in dashboard)
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — needed for Supabase JS (if used directly)

Note: The dashboard's auth flow (`/auth/login`) goes through the FastAPI backend, not directly
to Supabase. Check `dashboard/lib/` for whether a Supabase JS client is initialized — if the
dashboard only calls the FastAPI auth endpoints, NEXT_PUBLIC_SUPABASE_* vars may not be needed.

---

## Demo Seed Strategy

**Implementation**: `api/seed.py` — `seed_demo_data()` async function

**What it creates**:
- 1 Chatbot (name="Demo Assistant", owner_email="demo@example.com",
  api_key = "cbk_demo_key_for_testing" stored as sha256 hash)
- 1 Conversation (session_id="demo-session-001")
- 2 Messages (user: "What can you help me with?", assistant: canned response)

**Idempotency**: queries for existing chatbot by name+owner_email before inserting. Safe to
run on every cold start.

**Gap**: The demo chatbot's UUID is generated fresh each time the database is empty. The demo
HTML at `GET /demo` needs to discover this ID dynamically (via the widget-config endpoint or
hardcoded). Verify `api/static/demo.html` handles dynamic chatbot ID resolution before Wave 3.

**No KB seeding**: The seed does not upload any documents to the vector store. The demo chatbot
will answer without RAG context. This is acceptable for demo purposes — Claude has general
knowledge. If a KB demo is wanted, a second seed phase could upload a sample FAQ document,
but this requires GEMINI_API_KEY to be set and is not required for Wave 1-2.

---

## Screenshot Plan

All screenshots captured after Wave 3 (live services). Target dimensions: 1280x800 or 1440x900.

| File | URL | What to show |
|------|-----|-------------|
| `widget-demo.png` | `https://chatbot-widget-api.onrender.com/demo` | Widget bubble open, chat visible |
| `dashboard-login.png` | Vercel URL `/login` | Login form + Try Demo button |
| `dashboard-chatbots.png` | Vercel URL `/dashboard` (after demo login) | Chatbot card list |
| `dashboard-analytics.png` | Vercel URL `/dashboard/<id>` | Analytics stats panel |
| `streaming-chat.gif` | `/demo` page | Open bubble → type → stream tokens |

The GIF should be under 3MB. Use gif_creator tool with a 3-5 second capture window showing
the streaming effect. The WebSocket at `WS /ws/chat/{id}` streams tokens as they arrive from
Claude, so the visual effect of letter-by-letter text appearing should be clearly visible.

---

## Case Study Outline

Key architectural decisions worth highlighting:

1. **Shadow DOM widget isolation**
   - Decision: use Shadow DOM instead of iframe for widget embedding
   - Rationale: Shadow DOM allows direct DOM access for WebSocket while fully isolating CSS
   - Alternative considered: iframe (simpler but can't share WebSocket state easily)
   - Result: zero CSS conflicts on any host site, ~14KB bundle with no framework

2. **pgvector + Gemini embeddings for RAG**
   - Decision: Gemini Embedding (768-dim) over OpenAI text-embedding-ada-002 (1536-dim)
   - Rationale: lower dimensionality = smaller storage, faster queries; single-API-key risk
     mitigation vs OpenAI dependency
   - Implementation: chunk size 400 tokens, 50-token overlap; top-k=5 retrieval

3. **WebSocket streaming over Server-Sent Events**
   - Decision: WS `/ws/chat/{id}` for streaming
   - Rationale: SSE is one-directional; WS allows session management and future bidirectional
     features (typing indicators, read receipts) without protocol change

4. **Supabase JWT vs custom JWT**
   - Decision: delegate auth to Supabase, verify JWT in FastAPI middleware
   - Rationale: eliminates password hashing, email verification, token refresh complexity
   - Tradeoff: dependency on Supabase availability; mitigated by demo mode that bypasses auth

5. **Redis quota enforcement with TTL counters**
   - Decision: Redis TTL keys for monthly message quotas (not DB rows)
   - Rationale: O(1) quota check on every chat request; DB would require aggregation query

6. **Demo mode as first-class pattern**
   - Decision: DEMO_MODE env var that bypasses Supabase auth, auto-seeds data, enables demo login
   - Rationale: enables portfolio deployment without requiring Stripe and Supabase credentials
   - Implementation: idempotent seed in lifespan hook, demo-login endpoint returns synthetic JWT

---

## Notes

- `requirements.txt` does not include `mypy` — must be added to CI pip install, not requirements
  (keep dev tooling out of production requirements to keep Docker image lean)
- `types-redis` stub package needed alongside mypy for redis type annotations
- Dashboard `package.json` lists `"next": "16.2.0"` but README badge says "Next.js 15" —
  update badge to 16 in Wave 5
- CI uses postgres:15 but render.yaml provisions postgres:16 — no functional impact found
- The widget test directory `widget/__tests__/` and `widget/vitest.config.js` exist —
  these are separate from the dashboard Vitest tests; confirm they are included in the 9 Vitest count
  or are a separate suite not yet wired into CI
- `api/static/demo.html` should be reviewed before Wave 3 to confirm it dynamically resolves
  the demo chatbot ID (e.g. via `GET /api/v1/chatbots?owner_email=demo@example.com` or a
  dedicated `GET /demo/widget-config` endpoint from the prior March 17 spec)

---
spec: 2026-03-19-feature-chatbot-widget-saas-launch
status: ready-wave-1-2
complexity: standard
effort_estimate: 8-12 hours
repo: chatbot-widget
github: ChunkyTortoise/chatbot-widget
stack: FastAPI/pgvector/Redis/Claude/Gemini/Next.js
live_url: pending-render-deploy
blocked_at: Wave 3 (Render billing)
---

# Spec: chatbot-widget — SaaS Launch Sprint

## Context

The chatbot-widget repo is code-complete with 128 tests passing (119 pytest + 9 Vitest) but has
never been deployed to production. The following gaps exist before this can serve as a live
portfolio project:

- API not deployed to Render (render.yaml exists but no credit card on file blocks free-tier deploy)
- Next.js dashboard not deployed to Vercel (vercel.json exists but NEXT_PUBLIC_API_URL is unset)
- CI runs coverage but does not enforce a minimum threshold (`--cov-fail-under` absent)
- CI has no mypy step (mypy not in requirements.txt)
- No screenshots or GIF exist (docs/screenshots/ is empty)
- No CASE_STUDY.md
- Demo mode seeding already implemented in `api/seed.py` and wired into `api/main.py` lifespan,
  but render.yaml does not set `DEMO_MODE=true` or run a preDeployCommand

## Goals

- Ship the API to Render (or Railway as alternative) with demo data auto-seeded on first boot
- Ship the Next.js dashboard to Vercel pointing at the Render/Railway API
- Enforce 80% coverage gate in CI
- Add mypy type-checking job to CI
- Add security scanning (Trivy, CodeQL, bandit) to CI
- Fix render.yaml Redis service type (must be under `services:`, not `databases:`)
- Ensure demo chatbot UUID is resolved dynamically (not hardcoded) in demo page
- Highlight Shadow DOM architecture decision in README and CASE_STUDY.md (zero CSS conflicts, ~14KB)
- Add widget embed `<script>` snippet to README hero (the 3-line core product UX)
- Add "Certifications Applied" section in Domain Pillars format
- Capture screenshots and a streaming chat GIF for README/portfolio
- Write CASE_STUDY.md following the docextract format
- Verify widget embed and dashboard auth work end-to-end on live URLs

## Requirements

| ID | Type | Statement |
|----|------|-----------|
| REQ-F01 | Functional | The API shall be deployed to Render with demo mode auto-seeding sample data on startup |
| REQ-F02 | Functional | The Next.js dashboard shall be deployed to Vercel with NEXT_PUBLIC_API_URL pointing to the Render service |
| REQ-F03 | Functional | The README shall include screenshots of the widget embed, dashboard chatbot list, and demo page |
| REQ-F04 | Functional | The README shall include a GIF of WebSocket streaming chat in action |
| REQ-F05 | Functional | A case study shall exist at CASE_STUDY.md covering SaaS architecture decisions |
| REQ-F06 | Functional | CI shall enforce --cov-fail-under=80 on pytest |
| REQ-F07 | Functional | CI shall include a mypy type-checking step that must pass |
| REQ-F08 | Functional | render.yaml shall set DEMO_MODE=true so seed_demo_data() runs on every cold start |
| REQ-NF01 | Non-functional | Widget embed script shall load and open a working chat session on the live Render URL |
| REQ-NF02 | Non-functional | Next.js dashboard shall successfully authenticate and list chatbots against the live API |
| REQ-F09 | Functional | The README hero shall include the 3-line widget embed `<script>` snippet as the primary product demo (this is the killer UX — zero setup for the site owner) |
| REQ-F10 | Functional | The README shall include a "Certifications Applied" section in Domain Pillars format (GenAI & LLM Engineering, RAG & Knowledge Systems, Cloud & MLOps, Deep Learning & AI Foundations) |
| REQ-F11 | Functional | The demo page (`api/static/demo.html`) shall resolve the demo chatbot UUID dynamically via `GET /demo/widget-config` — UUID must not be hardcoded (it changes per fresh DB) |
| REQ-F12 | Functional | `render.yaml` shall declare the Redis service under `services:` with `type: redis` at the service level, not under `databases:`, matching Render's current Blueprint schema |
| REQ-F13 | Functional | The README and CASE_STUDY.md shall include a dedicated section on the Shadow DOM architecture decision: zero CSS conflicts with host page, ~14KB bundle, security boundary between widget and host |

## Architecture

### REQ-F01 / REQ-F08 — Demo mode on Render

`api/main.py` lifespan already calls `seed_demo_data()` when `settings.demo_mode` is `True`.
`api/seed.py` is idempotent — safe to run on every startup. The only missing piece is setting
`DEMO_MODE=true` in render.yaml. No preDeployCommand is needed; the lifespan hook handles it.

### REQ-F02 — Vercel dashboard deploy

`dashboard/vercel.json` has `framework: nextjs` and `buildCommand: npm run build`. The only
missing piece is setting `NEXT_PUBLIC_API_URL` to the Render service URL as a Vercel environment
variable. `dashboard/lib/api.ts` already reads `process.env.NEXT_PUBLIC_API_URL`.

### REQ-F06 — Coverage gate

`.github/workflows/ci.yml` line 51 runs:
```
pytest tests/ -q --tb=short --cov=api --cov-report=term-missing
```
Add `--cov-fail-under=80` to the existing pytest invocation. No other changes needed.

### REQ-F07 — mypy job

Add `mypy` to the CI pip install step and add a separate `mypy` run step after lint.
A `mypy.ini` or inline config is needed to set `ignore_missing_imports = true` for third-party
packages without stubs (fastapi, sqlalchemy, anthropic, stripe, etc.).

### REQ-F03 / REQ-F04 — Screenshots and GIF

Use browser automation (mcp__claude-in-chrome) after Wave 3 to capture:
1. Widget embed demo page at GET /demo
2. Next.js dashboard login page
3. Dashboard chatbot list (authenticated as demo user)
4. GIF: open widget bubble → type message → watch streaming tokens arrive

### REQ-F05 — Case study

Write CASE_STUDY.md at repo root. Follow the docextract format:
architecture decisions, key tradeoffs, results, certification alignment.

## Waves

### Wave 1: CI Hardening (Unblocked)

**Dependencies**: None — can start immediately
**Files to modify**: `.github/workflows/ci.yml`

**Steps**:

1. Add `--cov-fail-under=80` to the pytest invocation on line 51:
   ```yaml
   run: pytest tests/ -q --tb=short --cov=api --cov-report=term-missing --cov-fail-under=80
   ```

2. Add `mypy` to the pip install step on line 38:
   ```yaml
   run: pip install ruff pytest pytest-asyncio pytest-cov mypy types-redis
   ```
   Note: `types-redis` provides stubs for redis; other packages (fastapi, sqlalchemy, anthropic,
   stripe, google-genai) lack stubs so mypy must be configured to ignore missing imports.

3. Add a mypy.ini file at the repo root:
   ```ini
   [mypy]
   python_version = 3.12
   ignore_missing_imports = true
   exclude = tests/
   ```

4. Add a mypy step to ci.yml after the Lint step and before the Test step:
   ```yaml
   - name: Type check
     run: mypy api/
   ```

5. Push and verify the CI workflow is green. If coverage is below 80%, examine the
   `--cov-report=term-missing` output to identify uncovered lines, then add targeted tests or
   adjust coverage scope before forcing the gate open.

6. Add security scanning to CI (R7 from refinements):

   Add a new job after the `test` job in `.github/workflows/ci.yml`:
   ```yaml
   security:
     runs-on: ubuntu-latest
     steps:
       - uses: actions/checkout@v4
       - name: Python security scan (bandit)
         run: pip install bandit && bandit -r api/ -ll
       - name: Dependency audit (pip-audit)
         run: pip install pip-audit && pip-audit
       - name: npm audit (dashboard)
         working-directory: dashboard
         run: npm audit --audit-level=high
   ```
   Note: Trivy and CodeQL can be added as separate workflow files if repo qualifies for GitHub Advanced Security.

**Acceptance**: CI passes with coverage gate enforced, mypy clean, and security scan green.

---

### Wave 2: Deployment Prep (Unblocked)

**Dependencies**: None
**Files to modify**: `render.yaml`

**Steps**:

1. Add `DEMO_MODE=true` to the render.yaml `envVars` block for the web service:
   ```yaml
   - key: DEMO_MODE
     value: true
   ```

2. Add the Supabase and Stripe env vars as `sync: false` entries so Render prompts for them
   on first deploy (they are optional for demo mode but the validator in `api/config.py` will
   raise if environment is not "development" and jwt_secret is the dev default):
   ```yaml
   - key: SUPABASE_JWT_SECRET
     sync: false
   - key: GEMINI_API_KEY
     sync: false
   ```

3. Set `environment: production` via an env var in render.yaml so the Pydantic validator runs:
   ```yaml
   - key: ENVIRONMENT
     value: production
   ```
   Note: with DEMO_MODE=true and proper SUPABASE_JWT_SECRET set, the validator will pass.

4. Document the complete list of env vars that must be set manually in the Render dashboard
   (those with `sync: false`):
   - ANTHROPIC_API_KEY
   - SUPABASE_JWT_SECRET (set to any 32+ char secret for demo mode)
   - GEMINI_API_KEY (required for document embeddings; can skip if no KB upload planned)
   - SUPABASE_URL (optional, set to placeholder if demo-only)
   - SUPABASE_SERVICE_ROLE_KEY (optional, set to placeholder if demo-only)
   - STRIPE_SECRET_KEY (optional, set to placeholder if billing not tested)
   - STRIPE_WEBHOOK_SECRET (optional, set to placeholder if billing not tested)

5. Verify render.yaml is valid by reviewing the Render Blueprint schema. The current file
   declares a `databases` block using the `redis` type for the Redis service but the type key
   should be at the service level — confirm the format matches Render's current YAML spec.

**Critical pre-deploy fix — must complete before Wave 3**:

6. Verify and fix render.yaml Redis type (REQ-F12):

   Read the current `render.yaml`. The Redis service MUST be declared under `services:` with `type: redis`, not under a `databases:` block. Correct format:
   ```yaml
   services:
     - type: web
       name: chatbot-widget-api
       ...
     - type: redis
       name: chatbot-widget-redis
       plan: free
       ipAllowList: []
   ```
   If it is currently under `databases:`, move it to `services:` and remove the `databases:` block entirely.

7. Verify demo chatbot UUID resolution (REQ-F11):

   Read `api/static/demo.html` (if it exists) and `api/routes/` to check if `GET /demo/widget-config` is implemented. This endpoint must return the demo chatbot UUID so the demo page never has a hardcoded UUID. If not implemented:
   - Add `GET /demo/widget-config` route that queries the DB for the demo chatbot and returns `{"chatbot_id": "<uuid>", "api_key": "<demo_key>"}`
   - Update `api/static/demo.html` to fetch this endpoint on load and inject the UUID into the `<script>` tag dynamically

8. Add widget embed snippet to README hero (REQ-F09):

   In the README, add the following immediately after the project description (before Features):
   ```markdown
   ## Add to Any Website

   ```html
   <script src="https://chatbot-widget-api.onrender.com/widget/chatbot.min.js"
           data-chatbot-id="YOUR_CHATBOT_UUID"
           data-api-key="cbk_your_api_key"></script>
   ```
   That's it. The widget self-injects into your page using Shadow DOM — zero CSS conflicts.
   ```

9. Add "Certifications Applied" section in Domain Pillars format (REQ-F10):

   Add before `## License` in README.md:
   ```markdown
   ## Certifications Applied

   ### GenAI & LLM Engineering
   - **IBM Generative AI Engineering** — Claude streaming chat pipeline, WebSocket token delivery
   - **Vanderbilt ChatGPT Automation** — embeddable chatbot automation, system prompt engineering

   ### RAG & Knowledge Systems
   - **IBM RAG and Agentic AI** — pgvector RAG knowledge base, Gemini 768-dim embeddings, document chunking/retrieval

   ### Cloud & MLOps
   - **Duke LLMOps** — CI/CD hardening (coverage gate, mypy, security scanning), Render deploy pipeline
   - **Google Cloud GenAI Leader** — cloud SaaS deployment, managed services

   ### Deep Learning & AI Foundations
   - **DeepLearning.AI Deep Learning** — 768-dim vector embeddings, cosine similarity search
   - **IBM AI and ML Engineering** — async ML pipeline, quota enforcement, rate limiting
   ```

10. Add Shadow DOM architecture highlight to README and CASE_STUDY.md (REQ-F13):

    In README, add to the Architecture section:
    ```markdown
    ### Shadow DOM Widget Isolation

    The embedded widget uses the Web Shadow DOM API — a hard boundary between the widget and the host page:
    - **Zero CSS conflicts**: widget styles cannot leak into the host page and vice versa
    - **~14KB bundle**: minified vanilla JS, no framework dependency
    - **Security boundary**: widget DOM is inaccessible to host page scripts
    - **WebSocket inside Shadow DOM**: the chat connection lives entirely within the isolated component
    ```

**Acceptance**: render.yaml has DEMO_MODE=true, Redis type is correct, demo UUID resolves dynamically, all required env vars documented.

---

### Wave 3: Deploy (Render OR Railway alternative)

**Primary Blocker**: Render credit card required before any service (including free tier) can be created.
**Railway Alternative**: Railway.app offers $5/month free credit with no credit card required for initial deploy — use as the unblocked alternative.
**Dependencies**: Wave 2 complete (including critical pre-deploy fixes), billing resolved on chosen platform.

**Steps**:

#### 3a-Render. Deploy API to Render (requires credit card)

1. Go to dashboard.render.com → New → Blueprint → select ChunkyTortoise/chatbot-widget
2. Render reads render.yaml and provisions: web service + PostgreSQL (starter) + Redis (starter)
3. In the Render dashboard, set the `sync: false` env vars manually (see Wave 2 step 4)
4. Trigger deploy. Monitor logs for:
   - `CREATE EXTENSION IF NOT EXISTS vector` — confirms pgvector installed
   - `DEMO_MODE enabled — seeding demo data...` — confirms seed ran
   - `Demo data seeded: chatbot=<uuid>` — confirms idempotent seed completed
   - `Application startup complete` — confirms Uvicorn is ready
5. Note the deployed URL (e.g. `https://chatbot-widget-api.onrender.com`)
6. Verify: `curl https://chatbot-widget-api.onrender.com/health` returns `{"status":"healthy",...}`

#### 3a-Railway. Deploy API to Railway (no credit card required — preferred if Render is blocked)

**Why Railway**: Railway supports persistent volumes for pgvector, has built-in PostgreSQL with pgvector extension, includes Redis, and offers $5 free credit. Best DX for this stack.

1. Go to railway.app → New Project → Deploy from GitHub → select ChunkyTortoise/chatbot-widget
2. Railway auto-detects the Dockerfile (use the `api/` directory or repo root Dockerfile)
3. Add services:
   - PostgreSQL: Railway → Add Service → PostgreSQL → enable pgvector plugin
   - Redis: Railway → Add Service → Redis
4. Set environment variables in Railway dashboard:
   - `DATABASE_URL` — copy from Railway PostgreSQL connection string (auto-injected if linked)
   - `REDIS_URL` — copy from Railway Redis connection string
   - `DEMO_MODE=true`
   - `ANTHROPIC_API_KEY` — set your key
   - `SUPABASE_JWT_SECRET` — set any 32+ char secret for demo mode
   - `GEMINI_API_KEY` — set your key (required for embeddings)
   - `SECRET_KEY` — `python -c "import secrets; print(secrets.token_hex(32))"`
5. Note the deployed URL (e.g. `https://chatbot-widget-api.up.railway.app`)
6. Verify: `curl https://chatbot-widget-api.up.railway.app/health` returns `{"status":"healthy",...}`

Note: If using Railway, update all hardcoded Render URLs in README.md and render.yaml references accordingly. The widget `<script>` tag URL must use the Railway URL.

#### 3b. Deploy Next.js Dashboard to Vercel

1. Go to vercel.com → New Project → Import ChunkyTortoise/chatbot-widget
2. Set Root Directory to `dashboard/`
3. Set environment variable `NEXT_PUBLIC_API_URL` to the API URL from step 3a (Render or Railway)
4. Set `NEXT_PUBLIC_DEMO_MODE=true` to enable the demo login button on the login page
5. Deploy. Note the Vercel URL (e.g. `https://chatbot-widget-dashboard.vercel.app`)
6. Verify: open the Vercel URL, click "Try Demo", confirm dashboard loads with demo chatbot listed

**Acceptance**: GET /health returns 200, dashboard demo login works.

---

### Wave 4: Screenshots and GIF

**Dependencies**: Wave 3 (live services running)
**Tools**: browser automation via mcp__claude-in-chrome + mcp__claude-in-chrome__gif_creator

**Steps**:

1. Capture screenshot: widget demo page
   - URL: `https://chatbot-widget-api.onrender.com/demo`
   - Show the widget bubble in bottom-right, chat open with demo conversation
   - Save to `docs/screenshots/widget-demo.png`

2. Capture screenshot: Next.js dashboard login
   - URL: Vercel dashboard URL `/login`
   - Show the login form with "Try Demo" button visible
   - Save to `docs/screenshots/dashboard-login.png`

3. Capture screenshot: Next.js dashboard chatbot list
   - After demo login, show the chatbot list page with the Demo Assistant card
   - Save to `docs/screenshots/dashboard-chatbots.png`

4. Capture screenshot: chatbot detail / analytics page
   - Click into the Demo Assistant → show analytics (message count, conversations)
   - Save to `docs/screenshots/dashboard-analytics.png`

5. Capture GIF: WebSocket streaming chat
   - Open the widget demo page
   - Click the chat bubble to open
   - Type "What can you help me with?" and send
   - Capture streaming tokens arriving in the widget
   - Save to `docs/screenshots/streaming-chat.gif`

**Acceptance**: All 4 PNG files and 1 GIF saved to docs/screenshots/.

---

### Wave 5: Case Study and README Updates

**Dependencies**: Wave 4 complete (screenshots/GIF exist)

**Steps**:

1. Write `CASE_STUDY.md` at repo root. Structure:
   - **Overview**: problem solved, target user (any website owner wanting AI chat)
   - **Architecture decisions**:
     - Shadow DOM isolation for zero-conflict widget embedding
     - pgvector + Gemini 768-dim embeddings vs OpenAI (cost, single-provider risk)
     - WebSocket streaming vs polling for real-time feel
     - Supabase JWT for auth (vs rolling custom JWT) — tradeoffs
     - Redis for quota enforcement (TTL-based monthly counters)
     - Demo mode pattern: DEMO_MODE env var + idempotent seed function
   - **Key technical challenges**: embedding chunking strategy, Shadow DOM CORS for WebSockets,
     async SQLAlchemy with pgvector, Stripe webhook idempotency
   - **Results**: 128 tests, live SaaS deployment, production-ready architecture
   - **Certification alignment**: table mapping skills to certs

2. Update README.md:
   - Add screenshots section with the 4 PNG images using relative paths:
     ```markdown
     ## Screenshots
     ![Widget Demo](docs/screenshots/widget-demo.png)
     ![Dashboard Login](docs/screenshots/dashboard-login.png)
     ![Dashboard Chatbots](docs/screenshots/dashboard-chatbots.png)
     ![Dashboard Analytics](docs/screenshots/dashboard-analytics.png)
     ```
   - Add GIF immediately after the architecture diagram:
     ```markdown
     ![Streaming Chat Demo](docs/screenshots/streaming-chat.gif)
     ```
   - Update the badge at line 1 from `128 passing` to `128 passing` (confirm actual count post-CI)
   - Add live URLs to the Deploy to Render section once known

**Acceptance**: CASE_STUDY.md exists, README images render on GitHub.

---

### Wave 6: Verification

**Dependencies**: Waves 1-5 complete

**Steps**:

1. Run full local test suite: `pytest tests/ --cov=api --cov-fail-under=80 -q`
2. Confirm CI is green on GitHub Actions (check the badge in README)
3. Hit the live health endpoint: `curl https://chatbot-widget-api.onrender.com/health`
4. Test widget embed from a plain HTML file:
   ```html
   <script src="https://chatbot-widget-api.onrender.com/widget/chatbot.min.js"
           data-chatbot-id="<DEMO_CHATBOT_UUID>"
           data-api-key="cbk_demo_key_for_testing"></script>
   ```
   Open in browser → widget bubble appears → click → send message → streaming response received
5. Test dashboard: open Vercel URL → Try Demo → chatbot list loads → click chatbot → analytics show
6. Verify all README image URLs load (open raw GitHub URL for each image)
7. Verify CASE_STUDY.md exists at repo root and is ≥ 300 words

## Verification Criteria

- [ ] `pytest tests/ --cov=api --cov-fail-under=80` passes in CI (no manual override)
- [ ] `mypy api/` passes with zero errors in CI
- [ ] `GET https://chatbot-widget-api.onrender.com/health` returns `{"status":"healthy"}`
- [ ] Widget embed `<script>` opens chat on live Render URL and receives a streaming response
- [ ] Dashboard demo login works on Vercel URL and chatbot list is populated
- [ ] `CASE_STUDY.md` exists at repo root, follows docextract format, ≥ 300 words
- [ ] All 4 PNG screenshots load on GitHub (no broken image icons)
- [ ] Streaming chat GIF loads on GitHub
- [ ] README hero includes the 3-line widget `<script>` embed snippet (REQ-F09)
- [ ] README includes "Certifications Applied" section in Domain Pillars format, 4 pillars (REQ-F10)
- [ ] Demo page resolves chatbot UUID dynamically via `GET /demo/widget-config`, not hardcoded (REQ-F11)
- [ ] `render.yaml` Redis service is under `services:` with `type: redis`, not under `databases:` (REQ-F12)
- [ ] README and CASE_STUDY.md include Shadow DOM section: zero CSS conflicts, ~14KB, security boundary (REQ-F13)
- [ ] CI includes security scanning step (bandit + pip-audit + npm audit) green
- [ ] Next.js dashboard version badge shows actual version (not 15 if it's 16.x)
- [ ] Deploy successful on Railway OR Render (not blocked)

## Certification Coverage

| Certification | Relevance | Evidence in this project |
|--------------|-----------|--------------------------|
| IBM GenAI Engineering | Strong | Claude LLM chat pipeline, streaming tokens via WebSocket |
| IBM RAG and Agentic AI | Strong | pgvector RAG KB, Gemini embeddings, document chunking/retrieval |
| Duke LLMOps | Moderate | CI/CD hardening (coverage gate, mypy), Render deploy pipeline |
| DeepLearning.AI Deep Learning | Moderate | 768-dim embeddings, vector similarity search |
| Vanderbilt ChatGPT Automation | Strong | Embeddable chatbot automation, system prompt engineering |
| Google Digital Marketing | Moderate | SaaS product launch, free/pro/business tier structure |
| Python for Everybody | Moderate | Python async backend, FastAPI, SQLAlchemy |
| Microsoft AI-Enhanced Data Analysis | Light | Chat analytics endpoint, conversation metrics |
| DeepLearning.AI AI For Everyone | Light | AI product design decisions, demo mode UX |
| Meta Social Media Marketing | Light | Product marketing framing for portfolio |

## Blockers

**Wave 3+ is blocked until Render credit card is added.**

Steps to unblock:
1. Go to https://dashboard.render.com
2. Click account avatar (top right) → Account Settings → Billing
3. Add a payment method (Render requires this even for free-tier Blueprint deploys)
4. Return to this spec and execute Wave 3a

Waves 1 and 2 have zero dependencies on billing and can be executed in any session right now.

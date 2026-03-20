# Spec: Chatbot Widget — Demo UI + Vercel Deploy + Portfolio Polish

**Date:** 2026-03-17
**Type:** feature
**Repo:** `~/Projects/chatbot-widget/`
**Complexity:** medium
**Target executor:** claude-sonnet-4-6 in a separate chat

---

## 1. Overview

Chatbot Widget has 119 pytest tests, a production-ready FastAPI backend with RAG, and a Next.js 15 admin dashboard — but it has zero live deployments and no interactive demo. The portfolio card currently links to nothing.

This spec covers three waves:
1. **Demo UI** — upgrade `widget/index.html` to a full portfolio-quality demo page + add a `GET /demo` FastAPI route; add a demo-login button to the dashboard login page so `DEMO_MODE=true` is accessible without Supabase
2. **Deploy** — deploy the Next.js dashboard to Vercel and confirm the FastAPI backend (chatbot-widget-api.onrender.com) is live
3. **Polish** — screenshots, README updates, portfolio site link, `.env.example` and `vercel.json` cleanup

---

## 2. Requirements

### Functional

- **REQ-F01**: The system shall serve an interactive demo page at `GET /demo` that embeds the live widget (chatbot.js) with a demo chatbot, displays a copy-paste integration snippet, and works without authentication.
- **REQ-F02**: The demo page shall show a "waking up…" banner when the first widget message takes >3 seconds (Render free-tier cold start).
- **REQ-F03**: The dashboard login page shall have a "Try Demo" button that calls `POST /auth/demo-login` and stores the returned `demo-token` so users can access the dashboard without Supabase credentials.
- **REQ-F04**: The `GET /demo` route shall be hidden from the OpenAPI schema (`include_in_schema=False`).
- **REQ-F05**: The Next.js dashboard shall be deployed to Vercel with `NEXT_PUBLIC_API_URL` pointing to the Render API.
- **REQ-F06**: `dashboard/vercel.json` shall not contain `@api-url` secret references; env vars shall be set via the Vercel dashboard instead.
- **REQ-F07**: The demo page shall be self-contained (one HTML file, no CDN deps, no build step).

### Non-Functional

- **REQ-NF01**: All 119 existing tests shall remain green after changes.
- **REQ-NF02**: New tests for `GET /demo` and demo login button shall be added (≥8 tests).
- **REQ-NF03**: The demo page shall load < 2s on a cold browser (no external network requests before widget).
- **REQ-NF04**: The demo page and dashboard shall work on mobile (480px viewport).

---

## 3. Architecture Decisions

### ADR-01: Demo page at `GET /demo` (not `/demo/ui`)

The existing route in `widget.py` is `GET /widget/demo` and serves `widget/index.html`. The new route shall be `GET /demo` served from `api/routes/demo.py` (new file), returning `FileResponse("api/static/demo.html")`. Rationale: `/widget/demo` is for the raw widget embed test; `/demo` is the portfolio-quality showcase. Two different files, two different purposes.

`api/static/` directory shall be created; `StaticFiles` mount is not needed (single HTML file pattern matches existing `FileResponse` usage in `widget.py`).

### ADR-02: Dashboard demo login — frontend change only

Add a "Try Demo (no account needed)" button to `dashboard/app/login/page.tsx` that calls `POST /auth/demo-login`. The button is only rendered if `process.env.NEXT_PUBLIC_DEMO_MODE === "true"` (an additional build-time env var set in Vercel for the demo deployment). This avoids showing the demo button on production builds where Supabase is configured.

### ADR-03: `vercel.json` simplified

Remove the `env` block with `@api-url` secret reference from `dashboard/vercel.json`. Set `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_DEMO_MODE` directly in the Vercel project's Environment Variables settings. The `vercel.json` retains only `framework`, `buildCommand`, `outputDirectory`.

Also remove the `env` block from `dashboard/next.config.ts` — it silently swallows a missing production env var by falling back to `localhost:8000`. Let the env var fail loudly at build time instead.

### ADR-04: Demo HTML embeds widget directly

The demo page shall embed `chatbot.min.js` from the Render URL with `data-chatbot-id` set to the demo chatbot's UUID (or the string `"demo"` if the backend resolves it specially). The page shall show a copy-paste snippet with the embed code highlighted. The page shall NOT duplicate the GHL kit's vertical-selector pattern — the widget IS the demo.

### ADR-05: Screenshots via Playwright

Screenshots shall be taken using Playwright Python (`playwright install chromium`) with the local server running (`DEMO_MODE=true`). Saved to `docs/screenshots/`.

---

## 4. Interface Contracts

### New endpoint: `GET /demo`

```python
# api/routes/demo.py
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

@router.get("/demo", include_in_schema=False)
async def demo_ui() -> FileResponse:
    return FileResponse(_STATIC_DIR / "demo.html", media_type="text/html")
```

Register in `api/routes/__init__.py`:
```python
from api.routes.demo import router as demo_router
api_router.include_router(demo_router, tags=["demo"])
```

### Modified: `dashboard/app/login/page.tsx`

Add below the existing login form:

```tsx
{process.env.NEXT_PUBLIC_DEMO_MODE === 'true' && (
  <button onClick={handleDemoLogin} className="w-full mt-3 ...">
    Try Demo (no account needed)
  </button>
)}
```

`handleDemoLogin` POSTs to `/auth/demo-login`, stores `access_token` in `localStorage` as `token`, then `router.push('/dashboard')`.

### Modified: `dashboard/vercel.json`

```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "outputDirectory": ".next"
}
```

### Modified: `dashboard/next.config.ts`

```typescript
import type { NextConfig } from 'next'

const config: NextConfig = {}

export default config
```

(Remove the `env` block entirely — `NEXT_PUBLIC_API_URL` shall be injected by the build environment.)

---

## 5. Task Decomposition

### Wave 1: FastAPI Demo UI

**Task 1.1 — Create `api/static/demo.html`** (new file, ~400 lines)

Self-contained HTML/CSS/JS page. No external deps, no build step.

**Sections:**
1. **Hero header** — dark gradient, title "Chatbot Widget", tagline "Embed AI chat on any website in 60 seconds"
2. **Live widget demo** — full-page section with the embedded widget pre-loaded. The widget is injected via a `<script>` tag pointed at `window.API_URL + '/widget/chatbot.min.js'` with `data-chatbot-id` from a JS fetch to `GET /api/v1/chatbots?demo=true` (or hardcoded demo UUID from seed). A "waking up..." banner (yellow, dismissible) appears if the health check takes >3s.
3. **Integration snippet** — dark code block showing the `<script>` embed tag with one-click copy button
4. **Features list** — 3 cards: "RAG Knowledge Base", "Streaming WebSocket Chat", "Shadow DOM — zero CSS conflict"
5. **CTA** — "View on GitHub" + "Get the full kit"

**JS architecture:**
- On load: `fetch('/health')` — if response in <3s show green "Live" badge, else show "Waking up..." banner until response
- On load: `fetch('/api/v1/chatbots')` with `Authorization: Bearer demo-token` header (demo mode accepts this) → get first chatbot's id and api_key → inject widget script tag dynamically
- `window.API_URL` = detected from `window.location.origin` (works both local and deployed)
- Copy button: `navigator.clipboard.writeText(snippetText)` → show "Copied!" for 2s
- No conversation history to manage (widget handles its own state)

**Files:** Create `api/static/demo.html`, create `api/static/` directory

---

**Task 1.2 — Add `GET /demo` route**

New file `api/routes/demo.py` following the ADR-01 pattern.

Register in `api/routes/__init__.py`.

**Files:** Create `api/routes/demo.py`, modify `api/routes/__init__.py`

---

**Task 1.3 — Add demo login button to dashboard**

Modify `dashboard/app/login/page.tsx`:
- Add `handleDemoLogin` async function: `POST /auth/demo-login` → `localStorage.setItem('token', data.access_token)` → `router.push('/dashboard')`
- Add conditional button rendered only when `process.env.NEXT_PUBLIC_DEMO_MODE === 'true'`
- No changes to existing Supabase login flow

**Files:** Modify `dashboard/app/login/page.tsx`

---

**Task 1.4 — Tests for new endpoints**

New file `tests/test_demo.py` (8+ tests):

- `test_demo_ui_returns_200` — GET /demo → 200, content-type text/html
- `test_demo_ui_hidden_from_schema` — GET /openapi.json → "/demo" not in paths
- `test_demo_ui_contains_key_elements` — response body contains "chatbot.min.js", "copy", "GitHub"
- `test_demo_ui_contains_api_url_reference` — response body contains "/widget/chatbot.min.js"
- `test_demo_login_in_demo_mode` — DEMO_MODE=true, POST /auth/demo-login → 200, has access_token
- `test_demo_login_disabled_in_production` — DEMO_MODE=false, POST /auth/demo-login → 404
- `test_demo_ui_static_dir_exists` — Path("api/static/demo.html").exists() is True
- `test_demo_ui_no_external_links_in_head` — no CDN URLs in `<head>` (self-contained check)

**Files:** Create `tests/test_demo.py`

---

### Wave 1 Exit Gate

```bash
cd ~/Projects/chatbot-widget
pytest tests/ -v                   # All 119 + 8+ new tests pass
ruff check api/                    # No lint errors
# Manual: DEMO_MODE=true uvicorn api.main:app --reload
# Open http://localhost:8000/demo → page loads, widget appears
# Open http://localhost:3000/login → "Try Demo" button visible if NEXT_PUBLIC_DEMO_MODE=true
```

---

### Wave 2: Deploy

**Task 2.1 — Clean up `dashboard/vercel.json`**

Remove the `env` block with `@api-url`. Final file per ADR-03.

**Task 2.2 — Clean up `dashboard/next.config.ts`**

Remove the `env` block per ADR-03.

**Task 2.3 — Add `NEXT_PUBLIC_DEMO_MODE` to `.env.example` and `dashboard/.env.example`**

```bash
# api/.env.example
DEMO_MODE=false

# dashboard/.env.local.example  (create if not exists)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEMO_MODE=false
```

**Task 2.4 — Deploy Next.js dashboard to Vercel**

Steps (manual — agent documents, user executes or agent uses browser):
1. `vercel login` (if not logged in)
2. `cd ~/Projects/chatbot-widget/dashboard && vercel --prod`
   - When prompted "Set up and deploy?" → Yes
   - Project name: `chatbot-widget-dashboard`
   - Root directory: detected as `.` (already in dashboard/)
3. In Vercel dashboard → Project Settings → Environment Variables:
   - `NEXT_PUBLIC_API_URL` = `https://chatbot-widget-api.onrender.com` (Production + Preview)
   - `NEXT_PUBLIC_DEMO_MODE` = `true` (Production + Preview)
4. Trigger redeploy: `vercel --prod` again (env vars bake at build time)
5. Confirm: `curl https://chatbot-widget-dashboard.vercel.app` returns 200

**Task 2.5 — Confirm FastAPI backend is live on Render**

Check `https://chatbot-widget-api.onrender.com/health`. If not deployed:
1. Ensure `render.yaml` exists at repo root
2. Go to dashboard.render.com → New → Blueprint → connect `chatbot-widget` repo
3. Set env vars: `ANTHROPIC_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `ADMIN_KEY`, `SECRET_KEY`, `DEMO_MODE=true`, `GEMINI_API_KEY`

Note: If Render account has billing issues, document the steps and skip deployment; mark Wave 2 as partially complete.

---

### Wave 2 Exit Gate

- `curl https://chatbot-widget-api.onrender.com/health` → `{"status":"healthy",...}`
- `curl https://chatbot-widget-dashboard.vercel.app` → 200
- Open dashboard URL in browser → login page loads, "Try Demo" button visible
- Click "Try Demo" → redirects to `/dashboard` with chatbot list visible

---

### Wave 3: Polish

**Task 3.1 — Screenshots via Playwright**

Run with `DEMO_MODE=true uvicorn api.main:app` on port 8000.

Screenshots to take:
1. `docs/screenshots/demo-page.png` — full demo page (hero + widget open)
2. `docs/screenshots/dashboard-login.png` — login page with "Try Demo" button
3. `docs/screenshots/dashboard-chatbots.png` — `/dashboard` with demo chatbot card

Playwright script (create as `scripts/take_screenshots.py`, delete after use):
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800})

    # Demo page
    page.goto("http://localhost:8000/demo")
    page.wait_for_timeout(2000)
    page.screenshot(path="docs/screenshots/demo-page.png", full_page=True)

    # Dashboard login
    page.goto("http://localhost:3000/login")
    page.wait_for_timeout(1000)
    page.screenshot(path="docs/screenshots/dashboard-login.png")

    browser.close()
```

**Files:** Create `docs/screenshots/` + 2-3 PNG files

---

**Task 3.2 — Update README.md**

Add:
- Live URL badge at top: `[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://chatbot-widget-dashboard.vercel.app)`
- Dashboard URL badge: `[![Dashboard](https://img.shields.io/badge/dashboard-Vercel-black)](https://chatbot-widget-dashboard.vercel.app)`
- "Live Demo" section after features list:
  ```
  ## Live Demo
  - **Widget demo**: [chatbot-widget-api.onrender.com/demo](https://chatbot-widget-api.onrender.com/demo)
  - **Admin dashboard**: [chatbot-widget-dashboard.vercel.app](https://chatbot-widget-dashboard.vercel.app) (click "Try Demo")
  ```
- Screenshot images for demo page and dashboard
- `GET /demo` added to API Reference
- `NEXT_PUBLIC_DEMO_MODE` added to environment variables table
- Test count updated: 119 → actual count after Wave 1

**Files:** Modify `README.md`

---

**Task 3.3 — Update portfolio site**

In `~/Projects/personal/chunkytortoise.github.io/projects.html`, update the chatbot-widget project card:
- Add live demo URL (Render API) and dashboard URL (Vercel)
- Update test count to actual passing count

**Files:** Modify `projects.html` in portfolio repo

---

### Wave 3 Exit Gate

- README has live URLs, screenshots render in GitHub
- Portfolio site links to live demo and dashboard
- `pytest tests/ -v` still green

---

## 6. Files Summary

| File | Action | Wave |
|------|--------|------|
| `api/static/demo.html` | **Create** | 1 |
| `api/routes/demo.py` | **Create** | 1 |
| `api/routes/__init__.py` | Modify (register demo router) | 1 |
| `tests/test_demo.py` | **Create** | 1 |
| `dashboard/app/login/page.tsx` | Modify (add demo login button) | 1 |
| `dashboard/vercel.json` | Modify (remove @api-url env block) | 2 |
| `dashboard/next.config.ts` | Modify (remove env block) | 2 |
| `.env.example` | Modify (add DEMO_MODE) | 2 |
| `dashboard/.env.local.example` | **Create** | 2 |
| `docs/screenshots/*.png` | **Create** | 3 |
| `README.md` | Modify | 3 |
| Portfolio `projects.html` | Modify | 3 |

---

## 7. Verification Plan

| Check | Command | Pass Criteria |
|-------|---------|---------------|
| Tests green | `pytest tests/ -v` | All 119 + new tests pass, exit 0 |
| Lint | `ruff check api/ --select E,W,F` | Exit 0 |
| Demo route | `curl -s http://localhost:8000/demo \| grep "chatbot.min.js"` | Match found |
| Demo hidden from schema | `curl -s http://localhost:8000/openapi.json \| python -m json.tool \| grep "/demo"` | No output (route hidden) |
| Demo login | `curl -s -X POST http://localhost:8000/auth/demo-login` | `{"access_token":"demo-token",...}` |
| Dashboard build | `cd dashboard && npm run build` | Exit 0, no TS errors |
| Dashboard tests | `cd dashboard && npm test` | All Vitest tests pass |
| Live API health | `curl https://chatbot-widget-api.onrender.com/health` | `{"status":"healthy"}` |
| Live dashboard | `curl -s https://chatbot-widget-dashboard.vercel.app \| grep "ChatWidget"` | Match found |

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Render account billing block (same issue as ghl-multi-vertical-kit) | Document steps; backend may already be deployed at chatbot-widget-api.onrender.com — check first |
| `DEMO_MODE=true` demo chatbot UUID not predictable | Use the seed's deterministic pattern or expose a `GET /demo/chatbot-id` endpoint; alternatively hardcode the demo UUID in `demo.html` after first seed |
| Widget cold-start makes demo look broken | The "waking up..." banner + pre-fetch on page load handles this |
| `NEXT_PUBLIC_*` baked at build time | Document clearly in README: must redeploy if API URL changes |
| Vercel subdirectory confusion | Root Directory must be set to `dashboard` in Vercel project settings — document in README |

---

## 9. Codebase Context

Key files to read before implementing:

| File | Why |
|------|-----|
| `api/routes/widget.py` | Existing FileResponse pattern to replicate |
| `api/routes/__init__.py` | Router registration pattern |
| `api/seed.py` | DEMO_CHATBOT_NAME, DEMO_API_KEY, chatbot UUID generation |
| `api/auth/routes.py` | `/auth/demo-login` response shape |
| `api/config.py` | `demo_mode: bool` setting |
| `dashboard/app/login/page.tsx` | Where to add demo login button |
| `dashboard/lib/api.ts` | `apiFetch` helper that uses `NEXT_PUBLIC_API_URL` |
| `tests/conftest.py` | Fixture patterns for new tests |
| `widget/index.html` | Existing minimal demo — do not overwrite, add separate route |
| `~/Projects/ghl-multi-vertical-kit/app/static/demo.html` | Reference for self-contained demo HTML pattern |

---

## 10. Seed Demo Data Dependency

The demo page needs a chatbot ID to inject into the widget embed. The seed (`api/seed.py`) creates a chatbot with a random UUID on each startup. Three options (choose at implementation time):

**Option A (recommended):** After seeding, expose `GET /demo/widget-config` that returns the demo chatbot's ID and API key. The demo.html fetches this on load. Secure: requires `DEMO_MODE=true` to return data.

**Option B:** Make the demo chatbot UUID deterministic — use `uuid.UUID('00000000-0000-0000-0000-000000000001')` in seed.py. Then hardcode it in demo.html.

**Option C:** Use `data-chatbot-id="demo"` and teach `widget.py` / chat routes to resolve the string "demo" to the seeded demo chatbot when `DEMO_MODE=true`.

Option A is cleanest; Option B is simplest. Implement whichever fits the time budget.

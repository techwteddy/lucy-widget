# ADR 0003: WebSocket over SSE for Chat Streaming

**Status:** Accepted  
**Date:** 2025-12-15  
**Decision Makers:** Cayman Roden

## Context

The chat widget needs to stream LLM-generated tokens to the user in real-time. Three approaches were evaluated:

| Approach | Direction | Reconnection | Connection Overhead | Browser Support |
|----------|-----------|-------------|--------------------|--------------------|
| **WebSocket** | Bidirectional | Manual (implemented) | Single TCP upgrade | Universal |
| **SSE** | Server → Client only | Auto-reconnect | New HTTP per stream | Universal |
| **REST Polling** | Request/response | N/A | New HTTP per poll | Universal |

## Decision

Use WebSocket for real-time token streaming between the widget and FastAPI backend.

The connection endpoint is `WS /ws/chat/{chatbot_id}?session_id=&api_key=`. The widget auto-detects the WebSocket host from the script's `src` attribute (`API_HOST.replace(/^http/, 'ws')`).

## Consequences

**Benefits:**
- Bidirectional communication enables features beyond streaming: typing indicators, session heartbeats, and real-time escalation notifications
- Single persistent connection per chat session reduces connection overhead vs. SSE (which opens a new HTTP connection per stream)
- Sub-100ms time-to-first-token perception due to pre-established connection
- Session persistence via `sessionStorage` -- sessions survive page navigation within the same tab

**Tradeoffs:**
- Manual reconnection logic required. The widget implements exponential backoff reconnection (the browser's built-in `EventSource` auto-reconnect is SSE-only)
- WebSocket connections are stateful, which complicates horizontal scaling. Current architecture is single-process; future scaling would require Redis pub/sub for WebSocket fanout (documented in CASE_STUDY.md as a planned improvement)
- Some corporate proxies/firewalls block WebSocket upgrades. The REST endpoint (`POST /api/v1/chat/{id}`) exists as a non-streaming fallback

**Implementation Details:**
- Session ID format: `sess_` + random alphanumeric + timestamp (base36)
- Connection lifecycle: upgrade → authenticate (API key) → stream tokens → close
- Message protocol: JSON frames with `type` field (token, done, error)

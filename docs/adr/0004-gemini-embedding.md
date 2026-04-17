# ADR 0004: Gemini Embedding over OpenAI for Vectors

**Status:** Accepted  
**Date:** 2025-12-15  
**Decision Makers:** Cayman Roden

## Context

The RAG pipeline requires an embedding model to convert document chunks and user queries into vectors for similarity search. Two primary options were evaluated:

| Model | Dimensions | Cost | Quality | Provider Lock-in |
|-------|-----------|------|---------|-----------------|
| **Gemini Embedding** | 768 | $0.004/1K tokens | Competitive | Google |
| **OpenAI text-embedding-3-small** | 1536 | $0.02/1K tokens | Benchmark leader | OpenAI |
| **Sentence Transformers (local)** | Variable | $0 (compute cost) | Variable | None |

## Decision

Use Google Gemini Embedding API (768-dim) via the `google-genai` SDK.

Implementation in `api/services/embedder.py`:
- Single and batch embedding functions with configurable task types (`RETRIEVAL_DOCUMENT` for ingestion, `RETRIEVAL_QUERY` for search)
- Output dimensionality fixed at 768
- Input truncation at 2,000 characters per chunk
- Client singleton with `lru_cache` to avoid repeated initialization

## Consequences

**Benefits:**
- 5x lower cost than OpenAI embeddings ($0.004 vs $0.02 per 1K tokens)
- 768-dim vectors use 50% less storage than OpenAI's 1536-dim, reducing pgvector index size and memory usage
- Decouples embedding provider from LLM provider (Claude for generation, Gemini for embeddings) -- no single-vendor dependency
- Task-type-aware embeddings (RETRIEVAL_DOCUMENT vs RETRIEVAL_QUERY) improve retrieval quality by optimizing for asymmetric search
- Free tier covers development and low-volume production use

**Tradeoffs:**
- Gemini embeddings score slightly lower on MTEB benchmarks than OpenAI's latest models. For our use case (document Q&A with ~400-char chunks), the quality difference is negligible in practice.
- Google API dependency for a critical pipeline component. Mitigated by the embedding interface being a single 42-line file -- swapping to OpenAI or a local model requires changing one function.
- 2,000 character truncation limit is conservative. Longer chunks would require splitting or a model with larger context. Current chunk size (~400 chars with 50-char overlap) stays well within this limit.

**Measured Results:**
- RAG confidence threshold: 0.7 cosine distance (configurable in chat_service.py)
- Retrieval precision: Adequate for document Q&A across tested knowledge bases
- Embedding latency: <200ms per query (single embedding), <500ms per batch of 10

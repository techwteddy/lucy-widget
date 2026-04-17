# ADR 0002: pgvector over Pinecone for Vector Storage

**Status:** Accepted  
**Date:** 2025-12-15  
**Decision Makers:** Cayman Roden

## Context

The RAG pipeline requires storing and querying 768-dimensional embedding vectors for document chunks. Three vector storage options were evaluated:

| Option | Infrastructure | Multi-Tenancy | Cost | Operational Complexity |
|--------|---------------|---------------|------|----------------------|
| **pgvector** | PostgreSQL extension | WHERE clause on chatbot_id | $0 (uses existing PG) | Low -- single database |
| **Pinecone** | Managed SaaS | Namespace-based | $70+/mo (Starter) | Medium -- separate service |
| **ChromaDB** | Self-hosted | Collection-based | $0 + server cost | Medium -- separate server |

## Decision

Use pgvector as a PostgreSQL 16 extension, co-located with all relational data in a single database.

Vector similarity search is implemented in `api/services/retriever.py` using cosine distance with an HNSW index. Multi-tenant isolation uses a simple `WHERE chatbot_id = :id` clause on every query -- no namespace configuration or separate indexes needed.

## Consequences

**Benefits:**
- Single database for relational data (chatbots, conversations, users, billing) and vector search -- one connection pool, one backup strategy, one migration tool (Alembic)
- Multi-tenant isolation via SQL WHERE clause is trivially auditable and testable
- Zero additional infrastructure cost -- pgvector is a free PostgreSQL extension
- ACID guarantees apply to vector operations alongside relational data
- HNSW index provides sub-millisecond retrieval for our document scale (hundreds to low thousands of chunks per chatbot)

**Tradeoffs:**
- pgvector's HNSW index is less optimized than Pinecone for billion-scale vector sets. At our scale (max ~50K chunks per tenant), this is not a bottleneck.
- No built-in vector-specific features like metadata filtering or hybrid search that Pinecone offers. We implement hybrid filtering in application code.
- PostgreSQL handles both OLTP and vector workloads on the same instance. For this product's scale, resource contention is negligible.

**Configuration:**
- Embedding dimensions: 768 (Gemini Embedding)
- Index type: HNSW (cosine distance)
- Top-k retrieval: configurable via `settings.retrieval_top_k` (default: 5)

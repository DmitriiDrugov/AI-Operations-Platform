# ADR-004: pgvector in Supabase for Semantic Retrieval

**Date:** 2026-04-23  
**Status:** Accepted; reviewed at 500K vectors  
**Deciders:** Platform Architect, AI Systems Lead  

---

## Context

The AI copilot needs semantic retrieval over SOPs, service descriptions, policies, and operational documentation. This requires a vector database. The choice is between a dedicated vector database (Pinecone, Qdrant, Weaviate) and pgvector running inside our existing Supabase Postgres instance.

## Decision

Use pgvector in Supabase Postgres for all vector storage and retrieval, with a documented migration path to Qdrant if needed.

## Reasoning

**For pgvector:**

- Zero additional infrastructure: pgvector is an extension in our existing Supabase instance
- Transactional consistency: vector upserts and metadata updates happen in the same transaction
- RLS works natively: `organisation_id` filtering in vector queries uses the same RLS policies as all other tables
- Metadata filtering before ANN search: Postgres `WHERE` clauses run before the vector index, which is the correct pattern for multi-tenant retrieval
- IVFFlat index supports approximate nearest-neighbour at our expected scale (< 100K vectors per organisation)
- LangChain has a first-class `PGVector` retriever integration

**Scale analysis:**
- Expected knowledge base: ~500 Notion pages × ~10 chunks/page = ~5,000 chunks per organisation
- At 10 organisations: 50,000 vectors — well within pgvector's optimal range
- Threshold for re-evaluation: query latency p99 > 500ms at current vector count
- CloudWatch alarm: `vector.search.latency_p99` > 500ms triggers a review

**Against dedicated vector DB:**
- Adds an external service to operate and monitor
- Requires data synchronisation with Postgres (metadata lives in Postgres; vectors in Pinecone creates a split-brain risk)
- Additional cost at current scale is not justified

## Migration Path to Qdrant

If pgvector latency exceeds the threshold:
1. Deploy Qdrant alongside pgvector (ECS on AWS)
2. Add a `VectorStore` interface to the RAG service (already isolated behind `RAGService`)
3. Dual-write to both stores during migration
4. Shift reads to Qdrant once indexes are verified
5. Deprecate pgvector index

The RAG service is designed with this migration path in mind: it never exposes pgvector types to callers.

## Alternatives Rejected

- **Pinecone**: Managed but external; no RLS; metadata stored separately from Postgres creates consistency risk
- **Weaviate**: Strong product but requires self-hosting at this scale; adds operational burden
- **Qdrant**: Best-in-class dedicated vector DB; chosen as the migration target if needed but not justified at current scale

## Consequences

- `knowledge.chunks.embedding` column is `vector(1536)` with IVFFlat index (lists=100)
- Index is rebuilt automatically when new chunks are added (IVFFlat requires a full rebuild at significant scale change — monitor this)
- Content hashes prevent re-embedding unchanged chunks, keeping the index stable
- Embedding model is `text-embedding-3-small` (1536 dimensions); changing the model requires a full re-index

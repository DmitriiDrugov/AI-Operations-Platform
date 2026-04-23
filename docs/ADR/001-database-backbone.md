# ADR-001: Supabase + PostgreSQL as Primary Data Backbone

**Date:** 2026-04-23  
**Status:** Accepted  
**Deciders:** Platform Architect, Backend Lead  

---

## Context

We need a database that handles: transactional operational data, auth with row-level security, real-time subscriptions for live schedule updates, file storage for documents, and vector search for RAG retrieval. These concerns are typically served by four separate tools (Postgres, Auth provider, WebSockets, object storage, vector DB).

## Decision

Use Supabase as the unified data backbone, providing Postgres, Auth, Realtime, Storage, and pgvector through a single managed service.

## Reasoning

**For:**
- pgvector eliminates a separate vector database for the expected scale (< 1M vectors)
- Built-in Row Level Security enforces multi-tenancy at the database layer, not application layer
- Realtime subscriptions eliminate a separate WebSocket server for schedule updates
- Storage with signed URLs handles secure document access without a separate S3 setup for the primary path
- Auth with JWT claims eliminates a separate auth service
- Reduced operational complexity is high-value at this team size

**Against / Mitigations:**
- Supabase pgvector performance degrades at > 1M vectors → migration path to Qdrant documented; monitored by vector search latency alert
- Supabase is a managed service → vendor lock-in mitigated by the fact that it's standard PostgreSQL; we can self-host or migrate to RDS with pgvector if needed
- Supabase Realtime has connection limits per plan → acceptable at current scale; upgrade path exists

## Alternatives Rejected

- **PlanetScale + separate auth**: More operational pieces; no RLS; no Realtime; no vector
- **Neon + Clerk + Pinecone + Pusher**: Four services to maintain; higher cost; more network hops
- **Firebase**: No SQL; no RLS; weak for complex relational queries; vendor lock-in worse

## Consequences

- Schema design uses Postgres schemas (namespaces) for bounded context separation
- All application code connects via Supabase client SDK or direct asyncpg (for Python services)
- Migration strategy: Supabase CLI manages migrations; all schema changes are versioned SQL files
- Future: If vector search SLA degrades, pgvector is replaced by a dedicated service without affecting the rest of the stack

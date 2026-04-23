# ADR-002: Claude API as Primary AI Model with LangChain for Orchestration

**Date:** 2026-04-23  
**Status:** Accepted  
**Deciders:** Platform Architect, AI Systems Lead  

---

## Context

The platform requires several AI capabilities: text generation (summaries, drafts), semantic retrieval (RAG), structured output (classification), and multi-step tool use (agent workflows). The AI layer must be production-safe, testable in isolation, and replaceable if model or framework quality changes.

## Decision

Use Anthropic Claude API (claude-sonnet-4-6) as the primary model for all generation tasks. Use LangChain for RAG pipelines and multi-step agent workflows. Use Claude directly (via the `anthropic` SDK) for single-turn tasks that don't require retrieval or tool use.

## Reasoning

### Why Claude (Anthropic)?

- Strongest instruction-following for business-context tasks at the time of writing
- Extended context window handles long guest histories and large SOP documents
- Structured output mode reduces parsing failures for classification tasks
- Safety mitigations align with handling sensitive wellness/clinical information

### When LangChain vs Claude directly

**LangChain for:**
- RAG pipelines (retrieval → prompt construction → generation): `RetrievalQA` chain handles context injection, source tracking, and prompt templating
- Multi-step agents: when the AI needs to call tools (check package inclusions, look up appointment status) before generating a response
- Conversation memory: for the AI copilot, which needs to maintain context across a session

**Claude directly (anthropic SDK) for:**
- Single-turn completions: lead classification, message drafting, guest summarisation
- These tasks have well-defined inputs and outputs; LangChain adds latency and complexity without benefit

### LangChain isolation principle

All LangChain code is encapsulated behind service class interfaces. Callers (FastAPI routes) never import LangChain types directly. This means we can:
- Replace LangChain with a direct implementation without changing routes
- Mock chains in unit tests without a live LLM
- Upgrade LangChain versions without cascading changes

## Alternatives Rejected

- **OpenAI GPT-4**: Evaluated; Claude shows better instruction compliance for the structured output tasks in this domain. We use OpenAI's `text-embedding-3-small` for embeddings only because it's cost-effective and the model distinction doesn't affect business logic.
- **Llama 3 (self-hosted)**: Operational complexity of hosting + serving at production scale is not justified at this stage. Re-evaluate if Claude API cost becomes significant.
- **Direct anthropic SDK throughout**: No retrieval orchestration; writing custom RAG plumbing from scratch adds risk and maintenance burden. LangChain's `PGVector` retriever is well-tested.
- **LlamaIndex**: Considered; LangChain has a wider ecosystem for agent tool use, which is the primary non-retrieval AI use case here.

## Consequences

- LangChain is pinned to a specific minor version; upgrades require regression testing of all chains
- All agents have a `max_iterations` limit (10) to prevent runaway loops
- All AI interactions are logged to `public.ai_interactions` for cost tracking and quality review
- Prompt templates live in `packages/prompts/` to enable non-developer editing and version control

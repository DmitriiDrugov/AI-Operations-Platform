# AI Operations Platform

Production-oriented operations backbone for wellness / clinic / hotel businesses. Unifies lead intake, guest/patient profiles, booking lifecycle, scheduling, billing signals, and AI-assisted operations.

## Quick Navigation

| What you need | Where to look |
|---|---|
| Product requirements | [docs/PRD.md](docs/PRD.md) |
| System architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Data model and SQL schema | [docs/DATA_MODEL.md](docs/DATA_MODEL.md) |
| Application design | [docs/APPLICATION_DESIGN.md](docs/APPLICATION_DESIGN.md) |
| Automation layer design | [docs/AUTOMATION_LAYER.md](docs/AUTOMATION_LAYER.md) |
| Security and quality | [docs/SECURITY.md](docs/SECURITY.md) |
| Architecture decisions | [docs/ADR/](docs/ADR/) |
| 90-day roadmap | [ROADMAP.md](ROADMAP.md) |
| MVP tickets | [TICKETS.md](TICKETS.md) |

## Monorepo Structure

```
/
├── apps/
│   ├── web/              # Guest-facing portal (Next.js / TypeScript)
│   └── admin/            # Staff and admin dashboard (Next.js / TypeScript)
├── services/
│   ├── ai-core/          # AI endpoints: copilot, RAG, lead classification (Python / FastAPI)
│   └── worker/           # Background jobs: outbox, ingestion, analytics (Python / ARQ)
├── packages/
│   ├── shared-types/     # Zod schemas and TypeScript types shared across apps
│   └── prompts/          # Prompt templates (editable by product team)
├── infra/
│   ├── db/               # SQL migrations and seeds
│   ├── terraform/        # AWS infrastructure as code
│   └── aws/              # Lambda function code
├── automations/
│   ├── n8n/              # n8n workflow JSONs (developer-owned)
│   ├── make/             # Make scenario blueprints (operations-owned)
│   └── zapier/           # Zapier zap documentation (operations-owned)
└── docs/                 # All design documentation
```

## Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | Next.js 14 + TypeScript + Tailwind | App Router for server components; Supabase SSR for auth |
| Backend AI | Python 3.12 + FastAPI + LangChain | Type-safe AI service; LangChain for RAG and agents |
| Background Jobs | Python + ARQ + Redis | Asyncio-native job queue with cron support |
| Database | Supabase Postgres + pgvector | Single service: SQL + Auth + Realtime + Storage + vector search |
| Async Events | AWS SQS + Lambda | Durable queuing + serverless handlers for external API calls |
| AI Model | Anthropic Claude (claude-sonnet-4-6) | Primary reasoning model |
| Embeddings | OpenAI text-embedding-3-small | Cost-effective; 1536d; stable |
| Complex Automation | n8n (self-hosted) | Notion sync, escalations, reports |
| Quick Integrations | Zapier | Lead intake from forms, CRM triggers |
| Visual Workflows | Make | Communication sequences (business team editable) |
| Knowledge Base | Notion | Editable SOPs and service descriptions |

## Getting Started

### Prerequisites
- Node.js 20+
- Python 3.12+
- Docker and Docker Compose
- Supabase CLI

### Local development setup

```bash
# 1. Clone and install dependencies
npm install

# 2. Copy environment variables
cp .env.example .env.local
# Fill in your Supabase, Anthropic, and OpenAI keys

# 3. Start local Supabase
supabase start

# 4. Apply database migrations
supabase db push

# 5. Start the admin app
cd apps/admin && npm run dev

# 6. Start the AI core service
cd services/ai-core
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn main:app --reload --port 8000

# 7. Start the worker
cd services/worker
pip install -e ".[dev]"
arq main.WorkerConfig
```

### Running tests

```bash
# TypeScript (all packages)
npm test

# Python AI core
cd services/ai-core && pytest

# Python worker
cd services/worker && pytest
```

## Core Principles

1. **Deterministic over AI** — billing logic, scheduling conflict checks, and data validation are always deterministic code. AI is for language tasks only.
2. **Outbox pattern for reliability** — every event that triggers an external side effect goes through the outbox table, ensuring no silent data loss.
3. **RLS is the security boundary** — multi-tenant isolation is enforced at the database level, not the application level.
4. **Prompt injection protection** — user-supplied text is always in the `user` message, never in the `system` prompt. AI suggestions require human approval before any state change.
5. **Testable by design** — all AI service code is behind interfaces with injected dependencies; chains can be tested with mocked LLMs.

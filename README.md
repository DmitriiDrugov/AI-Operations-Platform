# AI Operations Platform

Operations backend for wellness clinics, medical spas, and hotel businesses. Covers lead intake, guest profiles, booking lifecycle, scheduling, billing, clinical records, multi-channel comms, and an AI copilot for staff.

Target scale: 10–200 staff, 5–500 concurrent guests, single or small multi-location.

## Repository layout

```
.
├── apps/
│   └── admin/              # Staff dashboard (Next.js 14)
├── services/
│   ├── ai-core/            # Copilot, RAG, lead classification (FastAPI)
│   └── worker/             # Background jobs: outbox, Notion sync, analytics (ARQ)
├── packages/
│   ├── shared-types/       # Zod schemas and TypeScript types shared across apps
│   └── prompts/            # Prompt templates — editable without a deploy
├── infra/
│   └── db/
│       ├── migrations/     # SQL migrations (Supabase CLI)
│       └── seeds/
├── automations/
│   ├── n8n/                # Complex workflows (Notion sync, escalations)
│   ├── make/               # Communication sequences
│   └── zapier/             # Third-party intake integrations
└── docs/                   # Design docs, ADRs
```

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Radix UI, React Query, Zod |
| AI service | Python 3.12, FastAPI, LangChain, Claude (`claude-sonnet-4-6`), OpenAI embeddings |
| Background jobs | ARQ, Redis |
| Database | Supabase — Postgres + pgvector + Auth + Realtime |
| Async events | AWS SQS + Lambda |
| Payments | Stripe |
| Messaging | Twilio (SMS, WhatsApp), SendGrid |
| Automation | n8n, Make, Zapier |

The schema is split across 11 Postgres schemas (crm, guests, bookings, scheduling, clinical, billing, comms, knowledge, analytics, audit, shared). Multi-tenant isolation is enforced via RLS on every table.

## Getting started

**Prerequisites:** Node.js 20+, Python 3.12+, Docker, Supabase CLI

```bash
# 1. Install dependencies
npm install

# 2. Environment variables
cp .env.example .env.local
# Fill in Supabase, Anthropic, OpenAI, AWS, Redis keys — see .env.example for all 57 vars

# 3. Start local Supabase and apply migrations
supabase start
npm run db:migrate

# 4. Run all services
npm run dev

# Or individually:
cd apps/admin       && npm run dev                           # :3001
cd services/ai-core && uvicorn main:app --reload --port 8000
cd services/worker  && arq main.WorkerConfig
```

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Start all services via Turbo |
| `npm run build` | Build all packages |
| `npm test` | Vitest (TS) + Pytest (Python) |
| `npm run lint` | ESLint + Ruff |
| `npm run db:migrate` | Apply SQL migrations |
| `npm run db:generate-types` | Generate TypeScript types from Supabase schema |

## Architecture notes

**AI copilot** — RAG over pgvector with a Notion knowledge base. Staff asks a question; the service retrieves relevant SOP chunks and passes them with the guest's history summary to Claude. User-supplied text is always in the `user` role, never injected into the `system` prompt.

**Outbox pattern** — every side effect that touches an external API (email, SMS, Stripe) is written to an `outbox` table first. The worker polls it every 5 seconds and publishes to SQS. This means no silent data loss on network failures.

**Determinism boundary** — billing calculations, scheduling conflict checks, and all state transitions are deterministic code. AI is used only for language tasks (summarisation, classification, search).

**RLS as the security boundary** — tenant isolation is enforced at the Postgres level via JWT claims, not in application code.

## Deployment targets

| Service | Platform |
|---|---|
| Admin app | Vercel |
| AI core | AWS ECS Fargate |
| Worker | AWS ECS Fargate |
| Database | Supabase |
| Queues | AWS SQS + Lambda |
| Secrets | AWS Secrets Manager (staging/prod), `.env.local` (dev) |

## Documentation

| | |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Product requirements, user roles, workflows |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, bounded contexts |
| [docs/APPLICATION_DESIGN.md](docs/APPLICATION_DESIGN.md) | API design, request/response models |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | Entity relationships and full schema |
| [docs/AUTOMATION_LAYER.md](docs/AUTOMATION_LAYER.md) | n8n / Make / Zapier integration strategy |
| [docs/SECURITY.md](docs/SECURITY.md) | Auth, RLS, encryption, secret management |
| [docs/ADR/](docs/ADR/) | Architecture decision records |
| [ROADMAP.md](ROADMAP.md) | 90-day build plan |
| [TICKETS.md](TICKETS.md) | MVP ticket list |

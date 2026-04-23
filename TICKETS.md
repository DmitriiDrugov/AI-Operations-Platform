# MVP Tickets — First 10 Prioritised

**Priority order:** Infrastructure first → data layer → core flows → AI layer → polish

---

## TICKET-001: Monorepo CI/CD Foundation

**Type:** Infrastructure  
**Priority:** P0 — Blocking everything else  
**Estimate:** 3 days  

Set up GitHub Actions workflows:
- `ci.yml`: Run lint + typecheck + unit tests on all PRs
- `deploy-ai-core.yml`: Build Docker image → push to ECR → deploy to ECS on merge to main
- `deploy-admin.yml`: Build Next.js → deploy to Vercel (or ECS) on merge to main
- `deploy-worker.yml`: Build worker image → deploy on merge to main
- `supabase-migrations.yml`: Apply migrations to staging on PR, production on merge

**Acceptance criteria:** PRs show pass/fail on lint, typecheck, and tests. Merging to main deploys all services.

---

## TICKET-002: Supabase Schema + Auth Setup

**Type:** Backend  
**Priority:** P0  
**Estimate:** 2 days  

- Apply `001_initial_schema.sql` migration to Supabase staging project
- Configure Supabase Auth: enable email magic link, set JWT expiry to 8h
- Add JWT custom claims hook (Edge Function): inject `organisation_id` and `role` into JWT on sign-in
- Test RLS policies with a multi-tenant fixture (two organisations, verify data isolation)
- Generate TypeScript types from schema: `supabase gen types typescript`

**Acceptance criteria:** Two test users in different organisations cannot see each other's data. Clinical data is invisible to front_desk role.

---

## TICKET-003: Guest Profile CRUD

**Type:** Backend + Frontend  
**Priority:** P0  
**Estimate:** 3 days  

- Supabase Edge Function: `POST /guests`, `GET /guests/:id`, `PATCH /guests/:id`
- PII encryption: implement `encrypt_pii` / `decrypt_pii` in Edge Function (AES-256 via Web Crypto API)
- Search: SHA-256 hash of email stored in `guests.search_tokens` for lookup
- Admin app: Guest list page with search, Guest detail page with tabs
- Unit test: encryption round-trip, RLS isolation

**Acceptance criteria:** Create a guest, view in admin, search by email hash. Verify email field is encrypted in the database.

---

## TICKET-004: Booking Lifecycle (Stay CRUD + Status Transitions)

**Type:** Backend + Frontend  
**Priority:** P0  
**Estimate:** 4 days  

- Edge Functions: create stay, update status (confirm, check-in, check-out, cancel)
- Status transition validation: enforced at Edge Function level (cannot check-in without confirming first)
- Outbox events written for: `booking.confirmed`, `booking.checked_in`, `booking.checked_out`
- Admin app: Stay list, create/edit form, status badge, quick check-in/out button on dashboard
- Unit test: status transitions, outbox event creation

**Acceptance criteria:** Full lifecycle from enquiry to checkout. Each status change writes an outbox event. Invalid transitions are rejected with a clear error.

---

## TICKET-005: Outbox Worker + SQS Integration

**Type:** Infrastructure + Backend  
**Priority:** P0  
**Estimate:** 3 days  

- Deploy Python worker service (Docker → ECS)
- Create SQS queues: `outbox-dispatch`, `notification-queue`, DLQs for both
- Implement `process_outbox_events` job (code exists in `services/worker/jobs/outbox_processor.py`)
- Implement Lambda `send-email` handler (SendGrid integration)
- Implement Lambda `post-to-slack` handler
- CloudWatch alarms: DLQ depth, Lambda error rate

**Acceptance criteria:** Create a booking → confirmation email is delivered within 60 seconds. DLQ alarm fires when a test message is forced to fail.

---

## TICKET-006: Appointment Scheduling

**Type:** Backend + Frontend  
**Priority:** P1  
**Estimate:** 4 days  

- Edge Functions: create appointment, list by date/practitioner/guest, cancel/reschedule
- Conflict detection: SQL query to check practitioner and room availability for the requested time slot
- Admin app: Day/week schedule view (using a React calendar component), drag-to-reschedule
- Realtime: Supabase Realtime subscription on `scheduling.appointments` for live schedule updates
- Outbox event: `appointment.completed` triggers billable event creation

**Acceptance criteria:** Scheduling a conflicting appointment is rejected. Schedule updates appear in real-time for all connected staff sessions.

---

## TICKET-007: Package + Billing Signal Engine

**Type:** Backend  
**Priority:** P1  
**Estimate:** 5 days  

- Edge Functions: create package assignment for a stay, log billable event (with idempotency_key)
- Billing classifier (Python, deterministic): given a billable event and a package assignment, determine `is_included_in_package` by checking `inclusions_snapshot`
- Admin app: Billing reconciliation page for a stay (included vs. chargeable table, approve/waive controls)
- Invoice generation: `POST /billing/invoices` creates an invoice from all approved billable events for a stay
- Unit test: 15 test scenarios covering package inclusion edge cases

**Acceptance criteria:** Package inclusions correctly classified. Billing reconciliation shows correct split. Invoice line items match approved billable events exactly.

---

## TICKET-008: AI Copilot (SOP Lookup + Guest Summary)

**Type:** Backend + Frontend  
**Priority:** P1  
**Estimate:** 5 days  

- Deploy ai-core service (Docker → ECS)
- Implement RAG service (`services/ai-core/services/rag_service.py` — exists)
- Implement Copilot service (`services/ai-core/services/copilot_service.py` — exists)
- Admin app: Copilot panel component (chat UI, citations display, suggested actions)
- Integration test: SOP question returns a relevant chunk from the test knowledge base

**Acceptance criteria:** Staff can ask "What is the cancellation policy?" and receive an answer citing the relevant SOP chunk. Guest summary correctly uses guest context. No raw clinical data surfaces unless the user has a clinical role.

---

## TICKET-009: Notion → Vector Index Ingestion

**Type:** Backend + Infrastructure  
**Priority:** P1  
**Estimate:** 4 days  

- Implement `sync_notion_page` worker job (`services/worker/jobs/notion_ingestion.py` — exists)
- Initial bulk ingestion script: scan all pages in the knowledge base database and enqueue sync jobs
- n8n workflow: Notion webhook → validate → call worker (exists as JSON stub in `automations/n8n/`)
- Admin app: Knowledge base page showing ingestion jobs, chunk count, last sync time
- Monitor: CloudWatch alarm if ingestion job failure rate > 1/hour

**Acceptance criteria:** Editing a Notion SOP page triggers re-indexing within 2 minutes. The updated content is retrievable by the copilot immediately after indexing.

---

## TICKET-010: Analytics Dashboard + Daily Report

**Type:** Backend + Frontend  
**Priority:** P2  
**Estimate:** 4 days  

- Materialise analytics views: `daily_utilisation`, `billing_summary` as scheduled materialised views
- Nightly analytics job (`services/worker/main.py` — registered): runs SQL aggregations, calls Claude to generate a narrative summary
- Admin app: Dashboard charts (utilisation bar chart, revenue trend, upsell rate)
- n8n: Daily report workflow (format structured data → post to Slack + email)
- Unit test: Analytics aggregation SQL against test fixture data

**Acceptance criteria:** Dashboard shows real data for the last 30 days. Nightly report is delivered to Slack by 07:30 UTC. No manual data extraction required.

---

## Ticket Dependencies

```
TICKET-002 (Schema)
  └── TICKET-003 (Guest)
        └── TICKET-004 (Booking)
              ├── TICKET-005 (Outbox)
              ├── TICKET-006 (Scheduling)
              └── TICKET-007 (Billing)
                    └── TICKET-010 (Analytics)
TICKET-001 (CI/CD) ─────── Unblocks deployment of all others
TICKET-009 (Notion Sync)
  └── TICKET-008 (Copilot) — can be developed in parallel after TICKET-002
```

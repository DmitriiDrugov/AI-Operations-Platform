# Data Model and Backend Design
## AI Operations Platform — Wellness / Clinic / Hotel

**Version:** 1.0  
**Date:** 2026-04-23  

---

## 1. Schema Overview

All tables live in a single Postgres database (Supabase). Each bounded context has a schema prefix for clarity. Row Level Security is applied at the Postgres level using `organisation_id` and JWT claims.

| Schema | Purpose |
|---|---|
| `public` | Supabase default; used for cross-context entities (orgs, users) |
| `crm` | Leads, lead sources, qualification |
| `guests` | Guest/patient profiles, health data, preferences |
| `bookings` | Stays, check-in/out, room assignments |
| `scheduling` | Appointments, practitioner schedules, resource allocation |
| `clinical` | Treatment notes, health assessments, consent |
| `billing` | Packages, inclusions, billable events, invoices |
| `comms` | Notification log, message threads, templates |
| `knowledge` | Vector chunks, ingestion jobs, source metadata |
| `analytics` | Materialised views and aggregation tables |
| `audit` | Immutable audit log |

---

## 2. Core Entity Relationships

```
organisations (1)
    ├── users (N)           -- staff accounts
    ├── guests (N)          -- guest/patient profiles
    │   ├── leads (N)       -- pre-booking CRM record
    │   ├── stays (N)       -- accommodation bookings
    │   │   └── appointments (N)
    │   ├── package_assignments (N)
    │   │   └── package_inclusions (via package definition)
    │   └── billable_events (N)
    │       └── invoice_line_items (N)
    ├── services (N)        -- treatment / service catalogue
    ├── packages (N)        -- package definitions
    ├── practitioners (N)   -- staff with schedules
    └── rooms (N)           -- treatment/accommodation resources
```

---

## 3. Key Table Definitions (Conceptual)

### `public.organisations`
Multi-tenancy root. Every other table has `organisation_id` as a foreign key and RLS policy.

Fields: `id`, `name`, `slug`, `plan`, `settings (jsonb)`, `created_at`

### `public.users`
Extends `auth.users` (Supabase). Staff accounts only — guests use a separate flow.

Fields: `id` (= auth.users.id), `organisation_id`, `role`, `full_name`, `email`, `practitioner_id (nullable)`, `is_active`, `created_at`

### `guests.guests`
Unified guest/patient profile. Contains only non-clinical structured data at this level; clinical details live in `clinical.*`.

Fields: `id`, `organisation_id`, `external_id (nullable)`, `first_name`, `last_name`, `date_of_birth`, `email`, `phone`, `nationality`, `preferred_language`, `referral_source`, `tags (text[])`, `notes`, `gdpr_consented_at`, `marketing_consent`, `created_at`, `updated_at`

**PII note:** `email`, `phone`, `date_of_birth` are encrypted at the application layer before insert (pgcrypto or application-level AES-256).

### `crm.leads`
A lead has a lifecycle that ends when it converts to a guest booking or is closed.

Fields: `id`, `organisation_id`, `guest_id (nullable)`, `source` (enum: web_form, email, whatsapp, referral, walk_in), `status` (enum: new, contacted, qualified, proposal_sent, converted, closed_lost), `inquiry_text`, `preferred_programme`, `inquiry_date`, `assigned_to (user_id)`, `converted_at`, `created_at`, `updated_at`

### `bookings.stays`
Represents a guest's accommodation period.

Fields: `id`, `organisation_id`, `guest_id`, `room_id`, `status` (enum: enquiry, confirmed, checked_in, checked_out, cancelled, no_show), `check_in_date`, `check_out_date`, `actual_check_in_at`, `actual_check_out_at`, `programme_id (nullable)`, `package_assignment_id (nullable)`, `adults`, `children`, `special_requests`, `internal_notes`, `created_by (user_id)`, `created_at`, `updated_at`

### `scheduling.appointments`
A single scheduled service delivery with a practitioner and optionally a room.

Fields: `id`, `organisation_id`, `guest_id`, `stay_id (nullable)`, `service_id`, `practitioner_id`, `room_id (nullable)`, `status` (enum: scheduled, confirmed, in_progress, completed, cancelled, no_show), `scheduled_start_at`, `scheduled_end_at`, `actual_start_at`, `actual_end_at`, `notes`, `billable_event_id (nullable)`, `created_at`, `updated_at`

### `billing.packages`
Definition of a package offering (not a guest's purchase of one).

Fields: `id`, `organisation_id`, `name`, `description`, `duration_nights`, `price`, `currency`, `is_active`, `created_at`

### `billing.package_inclusions`
What is included in a package (service type × quantity).

Fields: `id`, `package_id`, `service_id`, `quantity`, `notes`

### `billing.package_assignments`
A guest's active package for a specific stay.

Fields: `id`, `organisation_id`, `guest_id`, `stay_id`, `package_id`, `inclusions_snapshot (jsonb)`, `started_at`, `expires_at`, `created_at`

**Note:** `inclusions_snapshot` captures the package definition at assignment time — prevents retroactive billing changes when packages are modified.

### `billing.billable_events`
Every service delivery or charge trigger. Source of truth for invoicing.

Fields: `id`, `organisation_id`, `guest_id`, `stay_id`, `appointment_id (nullable)`, `service_id`, `event_type` (enum: treatment, product_sale, room_charge, extra_service, penalty, adjustment), `quantity`, `unit_price`, `currency`, `is_included_in_package`, `package_assignment_id (nullable)`, `approval_status` (enum: pending, approved, waived, disputed), `approved_by (user_id, nullable)`, `idempotency_key`, `occurred_at`, `created_at`

### `billing.invoices` and `billing.invoice_line_items`
Final billing documents. Generated from approved billable events.

Invoice fields: `id`, `organisation_id`, `guest_id`, `stay_id`, `invoice_number`, `status` (enum: draft, sent, paid, partially_paid, voided), `total_amount`, `currency`, `due_date`, `sent_at`, `paid_at`, `stripe_invoice_id (nullable)`, `created_at`

Line item fields: `id`, `invoice_id`, `billable_event_id`, `description`, `quantity`, `unit_price`, `total`, `tax_rate`, `tax_amount`

### `knowledge.chunks`
Vectorised knowledge content for RAG retrieval.

Fields: `id`, `organisation_id`, `source_type` (enum: notion_page, uploaded_doc, manual), `source_id`, `source_url`, `page_title`, `section_heading`, `content_text`, `content_hash`, `embedding (vector(1536))`, `token_count`, `metadata (jsonb)`, `last_indexed_at`, `created_at`

### `knowledge.ingestion_jobs`
Tracks sync jobs from Notion and other sources.

Fields: `id`, `organisation_id`, `source_type`, `source_id`, `status` (enum: pending, running, completed, failed), `pages_processed`, `chunks_upserted`, `error_message`, `started_at`, `completed_at`, `created_at`

### `audit.log`
Immutable record of all write operations. Populated by Postgres triggers.

Fields: `id`, `organisation_id`, `table_name`, `record_id`, `operation` (INSERT/UPDATE/DELETE), `old_values (jsonb)`, `new_values (jsonb)`, `changed_by (user_id)`, `changed_at`, `ip_address`, `user_agent`

### `public.outbox_events`
Transactional outbox for reliable event publishing.

Fields: `id`, `organisation_id`, `event_type`, `aggregate_type`, `aggregate_id`, `payload (jsonb)`, `version`, `status` (enum: pending, processing, processed, failed), `attempts`, `last_error`, `created_at`, `processed_at`

---

## 4. RLS Strategy

Every table uses two-layer RLS:

**Layer 1 — Organisation isolation:**
```sql
CREATE POLICY org_isolation ON guests.guests
  USING (organisation_id = (current_setting('app.organisation_id'))::uuid);
```

The `app.organisation_id` setting is injected by the Edge Function from the JWT claim before any query.

**Layer 2 — Role-based access within organisation:**
```sql
CREATE POLICY guest_data_access ON clinical.assessments
  USING (
    (current_setting('app.role') IN ('admin', 'manager', 'nurse', 'practitioner'))
    OR
    (current_setting('app.role') = 'front_desk'
     AND current_setting('app.user_id')::uuid IN (
       SELECT assigned_to FROM bookings.stays WHERE guest_id = assessments.guest_id
     ))
  );
```

**Service account (backend Python services):** Uses a `service_role` key; bypasses RLS but all writes go through a wrapper that injects `organisation_id` explicitly.

**Audit trigger (all write tables):**
```sql
CREATE TRIGGER audit_trigger
  AFTER INSERT OR UPDATE OR DELETE ON guests.guests
  FOR EACH ROW EXECUTE FUNCTION audit.log_change();
```

---

## 5. Vector Indexing Strategy

**Storage:** pgvector extension in Supabase Postgres  
**Embedding model:** OpenAI `text-embedding-3-small` (1536 dimensions) via LangChain  
**Index type:** IVFFlat with `lists = 100` (suitable for up to ~1M vectors)

```sql
CREATE INDEX knowledge_chunks_embedding_idx
  ON knowledge.chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

**Retrieval query pattern:**
```sql
SELECT id, page_title, section_heading, content_text,
       1 - (embedding <=> $1::vector) AS similarity
FROM knowledge.chunks
WHERE organisation_id = $2
  AND (1 - (embedding <=> $1::vector)) > 0.75
ORDER BY embedding <=> $1::vector
LIMIT 8;
```

**Chunking strategy:**
- Notion pages → split by heading (H2/H3 boundaries)
- Target chunk size: 400–600 tokens
- 50-token overlap between consecutive chunks
- Each chunk stores: source page title, heading path, parent section, content hash
- Content hash is used for incremental updates (skip re-embedding if unchanged)

**Metadata filtering:** All queries filter by `organisation_id` before vector search. Optionally filter by `source_type` (e.g., only SOPs for a policy question, only service descriptions for a treatment question).

---

## 6. Event Model (Outbox / Inbox Pattern)

### Why Outbox Pattern?
Without the outbox pattern, a failed external notification after a successful database write creates a silent inconsistency. The outbox ensures exactly-once delivery semantics by writing the event and the business record in the same database transaction.

### Event Types

| Event Type | Aggregate | Triggers |
|---|---|---|
| `lead.created` | Lead | Welcome email, Slack alert, AI lead summary |
| `lead.converted` | Lead | CRM update, remove from lead nurture |
| `booking.confirmed` | Stay | Confirmation email, calendar invite, deposit invoice |
| `booking.checked_in` | Stay | Welcome pack, schedule notification, room charge start |
| `booking.checked_out` | Stay | Final invoice, review request, follow-up sequence |
| `appointment.completed` | Appointment | Billable event creation, practitioner note prompt |
| `billable_event.created` | BillableEvent | Finance alert if above threshold |
| `invoice.sent` | Invoice | Payment tracking start, Stripe intent creation |
| `payment.received` | Invoice | Invoice status update, receipt email |
| `knowledge.chunk_upserted` | KnowledgeChunk | Cache invalidation (if any) |

### Event Payload Schema (versioned)
```json
{
  "id": "uuid",
  "version": "1",
  "event_type": "booking.confirmed",
  "aggregate_type": "stay",
  "aggregate_id": "uuid",
  "organisation_id": "uuid",
  "occurred_at": "2026-04-23T10:00:00Z",
  "payload": {
    "guest_id": "uuid",
    "guest_name": "Jane Smith",
    "check_in_date": "2026-05-01",
    "check_out_date": "2026-05-08",
    "programme_name": "7-Day Detox Retreat"
  },
  "metadata": {
    "source_service": "edge-function",
    "trace_id": "uuid"
  }
}
```

### Processing Flow
1. Worker polls `outbox_events WHERE status = 'pending' AND created_at < NOW() - INTERVAL '1 second'`
2. Marks event as `processing` (atomic UPDATE with status check to prevent double-processing)
3. Dispatches to SQS with the event payload
4. On SQS success: marks `processed`; on failure: marks `failed`, increments `attempts`
5. Dead letter queue captures events with `attempts >= 5`
6. CloudWatch alarm fires on DLQ depth > 0

---

## 7. Background Job Strategy

**Runtime:** ARQ (asyncio job queue for Python) backed by Redis (AWS ElastiCache)

| Job | Schedule | Description |
|---|---|---|
| `process_outbox` | Every 5s | Poll and dispatch pending outbox events |
| `sync_notion_pages` | On-demand (webhook-triggered) | Incremental Notion → vector sync |
| `nightly_analytics` | 02:00 UTC | Aggregate KPIs into analytics tables |
| `billing_reconciliation_reminders` | 08:00 UTC | Alert finance on stays checking out today |
| `clean_stale_processing_events` | Hourly | Reset stuck `processing` events older than 10 min |
| `reindex_failed_chunks` | Daily 03:00 UTC | Retry failed ingestion jobs |
| `purge_expired_sessions` | Daily | Supabase session hygiene |

---

## 8. Storage Strategy (Supabase Storage + S3)

| Asset Type | Storage | Access | Notes |
|---|---|---|---|
| Guest consent forms | Supabase Storage | Private, signed URL (1 hour TTL) | Encrypted bucket |
| Treatment notes attachments | Supabase Storage | Private, signed URL | Restricted to clinical roles |
| Invoice PDFs | Supabase Storage → S3 archive | Private | Moved to S3 after 90 days |
| Knowledge base documents (uploaded PDFs) | Supabase Storage | Service-role only | Processed by ingestion pipeline |
| Exported reports | S3 | Pre-signed URL, 24h TTL | Generated by nightly job |
| Lambda deployment packages | S3 | IAM-restricted | CI/CD managed |

**Supabase Storage bucket policy example:**
```
Bucket: guest-documents
Policies:
  - Read: user must be authenticated + same org + role IN (admin, manager, nurse, front_desk, practitioner)
  - Write: user must be authenticated + same org + role IN (admin, manager, nurse)
  - Guests: read-only access to their own documents via signed URL issued by Edge Function
```

---

## 9. Migration Strategy

- All schema changes managed by Supabase migrations (`supabase/migrations/`)
- Migrations are additive-first: add columns before removing old ones
- Breaking changes require a two-phase migration:
  1. Phase A: Add new structure, dual-write
  2. Phase B (next deploy): Remove old structure
- `NOT NULL` constraints added via:
  1. Add column as NULLABLE
  2. Backfill
  3. Add constraint
- RLS policies tested in a staging environment before production apply
- Migration files are named: `{timestamp}_{bounded_context}_{description}.sql`

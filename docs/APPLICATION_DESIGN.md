# Application Design
## AI Operations Platform — Wellness / Clinic / Hotel

**Version:** 1.0  
**Date:** 2026-04-23  

---

## 1. Frontend Application Modules

### apps/web — Guest-Facing Portal

| Module | Route | Functionality |
|---|---|---|
| **Booking** | `/book` | Programme selection, availability check, booking form |
| **My Stay** | `/stay` | Today's schedule, room info, treatment list |
| **Profile** | `/profile` | Personal details, health intake form, preferences |
| **Messages** | `/messages` | Thread view with staff; read-only notification history |
| **Documents** | `/documents` | Consent forms, invoices, welcome pack |
| **Check-in** | `/checkin` | Pre-arrival digital check-in flow |

**Tech stack:** Next.js 14 (App Router), Tailwind CSS, Supabase JS client, Zod for form validation, React Query for server state.

**Auth:** Supabase Auth magic link + optional OAuth. Guest role enforced via RLS.

### apps/admin — Staff and Admin Dashboard

| Module | Route | Functionality |
|---|---|---|
| **Dashboard** | `/` | Daily overview: arrivals, departures, utilisation summary |
| **Guests** | `/guests` | Guest list, search, profile detail, timeline view |
| **Leads** | `/leads` | Lead pipeline (Kanban + list), AI-assisted lead summary |
| **Schedule** | `/schedule` | Day/week view, drag-drop appointments, room grid |
| **AI Copilot** | `/copilot` | Chat interface with context switching (guest, SOP, general) |
| **Billing** | `/billing` | Billable events review, package reconciliation, invoice list |
| **Knowledge** | `/knowledge` | Notion sync status, chunk browser, ingestion history |
| **Reports** | `/reports` | KPI charts, utilisation graphs, export |
| **Settings** | `/settings` | Organisation config, user management, integrations |

**Tech stack:** Next.js 14 (App Router), Tailwind CSS + shadcn/ui component library, TanStack Table, Recharts, Supabase JS client for Realtime updates, Zod, React Query.

---

## 2. Supabase Edge Functions

Edge functions handle webhook ingestion and auth-adjacent logic. They run on the Supabase edge network, close to the database.

| Function | Trigger | Responsibility |
|---|---|---|
| `inbound-webhook` | POST from Zapier / external | Validate HMAC signature; write to outbox; return 200 immediately |
| `whatsapp-inbound` | POST from Twilio | Parse WhatsApp message; create/update lead; enqueue AI response |
| `stripe-webhook` | POST from Stripe | Verify Stripe signature; update invoice/payment status; write outbox event |
| `notion-sync-trigger` | POST from Notion webhook | Validate; enqueue ingestion job in Python worker |
| `auth-hook-on-signup` | Supabase Auth event | Assign default role; create `users` record; log |
| `generate-signed-url` | POST from admin app | Verify permission; return time-limited storage URL |

---

## 3. Python Backend Services

### services/ai-core (FastAPI)

```
POST /v1/copilot/query          — Staff AI assistant query (RAG + agent)
POST /v1/copilot/summarise      — Summarise guest history
POST /v1/copilot/draft-message  — Draft a guest-facing message
POST /v1/leads/classify         — Classify lead intent from inquiry text
POST /v1/leads/suggest-action   — Suggest next action for a lead
POST /v1/knowledge/search       — Semantic search over knowledge chunks
POST /v1/notes/generate-draft   — Generate treatment note draft from appointment
GET  /v1/health                 — Liveness probe
GET  /v1/metrics                — Prometheus metrics
```

### services/worker (ARQ + asyncio)

```
Jobs:
  process_outbox_events         — Poll and dispatch outbox events to SQS
  sync_notion_page              — Fetch, chunk, embed, upsert a Notion page
  run_nightly_analytics         — Aggregate KPIs into analytics tables
  send_billing_reminders        — Alert finance on same-day checkouts
  reindex_failed_chunks         — Retry failed ingestion
  clean_stale_processing        — Reset stuck outbox events
```

---

## 4. API Contracts

### Copilot Query — Request/Response

**Request:**
```typescript
interface CopilotQueryRequest {
  query: string;                       // Staff's natural language question
  context: {
    guest_id?: string;                 // If asking about a specific guest
    stay_id?: string;
    interaction_type: 'general' | 'guest_summary' | 'sop_lookup' | 'billing_query' | 'draft_message';
  };
  organisation_id: string;
  user_id: string;
}
```

**Response:**
```typescript
interface CopilotQueryResponse {
  response_text: string;
  citations: Array<{
    chunk_id: string;
    page_title: string;
    section_heading?: string;
    similarity_score: number;
  }>;
  suggested_actions: Array<{
    action_type: string;
    label: string;
    payload: Record<string, unknown>;
  }>;
  interaction_id: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
}
```

### Billable Events — Creation

**Request:**
```typescript
interface CreateBillableEventRequest {
  organisation_id: string;
  guest_id: string;
  stay_id?: string;
  appointment_id?: string;
  service_id?: string;
  event_type: BillableEventType;
  description: string;
  quantity: number;
  unit_price: number;
  currency: string;
  idempotency_key: string;             // Client-generated; server enforces uniqueness
  occurred_at: string;                 // ISO 8601
}
```

### Lead Classification — Request/Response

**Request:**
```typescript
interface ClassifyLeadRequest {
  inquiry_text: string;
  organisation_id: string;
  available_programmes: Array<{ id: string; name: string; description: string }>;
}
```

**Response:**
```typescript
interface ClassifyLeadResponse {
  intent: 'booking_inquiry' | 'general_question' | 'complaint' | 'referral' | 'other';
  urgency: 'high' | 'medium' | 'low';
  suggested_programme_ids: string[];
  budget_indicator: 'budget' | 'mid' | 'premium' | 'unknown';
  summary: string;
  suggested_reply_draft: string;
}
```

---

## 5. Admin Dashboard Pages — Detailed Spec

### Dashboard (/)
- **Today's widget**: arrivals (count + names), departures (count), active guests
- **Schedule widget**: Gantt-style room utilisation for today (real-time via Supabase Realtime)
- **Alerts widget**: Pending billable events needing approval; leads with overdue follow-up
- **AI summary**: Nightly-generated narrative of key operational metrics (cached, not live)

### Guest Profile (/guests/:id)
- Header: name, stay status badge, programme tag, VIP indicator
- Tabs:
  - **Overview**: Contact info, current stay dates, next appointment
  - **Timeline**: Chronological activity feed (stays, appointments, messages, billing events)
  - **Clinical**: Health assessments, contraindications, treatment notes (role-gated)
  - **Billing**: Package assignments, billable events table, invoices
  - **AI Copilot**: Inline copilot pre-loaded with this guest's context
- Actions: "Draft message", "Add appointment", "Log billable event", "Generate summary"

### AI Copilot (/copilot)
- Split pane: left = conversation history; right = context panel showing retrieved sources
- Context selector: switch between "This guest", "Operations", "Billing policy", "General SOP"
- Inline actions: Accept/reject suggestions; copy to notes; create task from suggestion
- Interaction log: All past AI interactions browsable by user and date
- Feedback button: thumb up/down on each response (feeds into quality monitoring)

### Billing Reconciliation (/billing/stays/:stay_id)
- Guest header with stay dates and package summary
- Two-column table: left = included services (green), right = chargeable extras (amber)
- Package inclusion tracker: "3 of 5 massage sessions used"
- Override controls: Finance can reclassify an event
- Approve all / approve individual buttons
- "Generate Invoice" button (disabled until all events are approved or waived)

---

## 6. AI Copilot UX Flows

### Flow 1: Summarise Guest Before Appointment
```
Practitioner opens appointment → clicks "Prepare" →
  System: loads guest profile + last 3 appointments + health notes + any SOP relevant to service →
  Claude: generates a structured briefing (health considerations, preferences, previous notes, suggested approach) →
  Display: shows as a card the practitioner can expand, dismiss, or add to session notes
```

### Flow 2: Answer SOP Question
```
Staff types: "What is our cancellation policy for programme packages?" →
  LangChain: embeds query → retrieves top 5 matching knowledge chunks →
  Claude: synthesises answer with citations →
  Display: response with expandable source cards showing the actual Notion content
  Staff can: accept, copy to clipboard, or "share with guest"
```

### Flow 3: Draft Guest-Facing Message
```
Staff clicks "Draft Message" on a lead →
  System: passes lead inquiry text + guest name + available programmes + tone preference →
  Claude: generates draft reply →
  Display: editable text area with the draft pre-filled →
  Staff edits and sends; accepted/sent message logged with original AI draft
```

### Flow 4: Billing Anomaly Investigation
```
Finance opens reconciliation → sees a disputed charge →
  Clicks "Ask AI": "Why was this massage charged as extra?" →
  LangChain Agent: checks package assignment inclusions snapshot + appointment details + package policy SOP →
  Claude: explains the classification with evidence →
  Finance: accepts explanation or overrides with a note
```

---

## 7. Operational Notifications Design

### Notification Channels

| Channel | Use Case | Delivery | Tool |
|---|---|---|---|
| Email | Booking confirmations, invoices, follow-up sequences | Async via SQS → Lambda → SendGrid | AWS Lambda |
| WhatsApp | Lead first contact, appointment reminders | Async via SQS → Lambda → Twilio | AWS Lambda |
| Slack | Staff alerts, escalations, daily report | Async via SQS → Lambda → Slack webhook | AWS Lambda |
| In-App | Real-time schedule changes, new messages, billing alerts | Supabase Realtime | Edge + Realtime |
| Push (future) | Mobile schedule reminders | Not in MVP | — |

### Notification Templates (stored as structured data, not hardcoded)

```typescript
interface NotificationTemplate {
  key: string;                         // e.g., 'booking.confirmed'
  channel: 'email' | 'whatsapp' | 'slack';
  subject_template?: string;           // Handlebars syntax
  body_template: string;
  variables: string[];                 // Required template variables
  active: boolean;
}
```

Templates live in the database and are editable by `org_admin` role via the Settings UI.

### Notification Delivery Guarantee
1. Edge Function writes notification request to `outbox_events`
2. Worker reads outbox → publishes to SQS `notification-queue`
3. Lambda handler processes delivery → logs to `comms.notification_log`
4. On Lambda failure: SQS retries 3× with exponential backoff
5. After 3 failures: moves to SQS Dead Letter Queue
6. CloudWatch alarm: DLQ depth > 0 triggers PagerDuty/Slack alert

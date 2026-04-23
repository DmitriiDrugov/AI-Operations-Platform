# Automation Layer Design
## AI Operations Platform — Wellness / Clinic / Hotel

**Version:** 1.0  
**Date:** 2026-04-23  

---

## Decision Framework

Before assigning any workflow to an automation tool, three questions are applied:

1. **Complexity**: Does the workflow have branching, conditional logic, or multiple retry strategies?  
2. **Ownership**: Should a developer control this, or does a business team need to edit it independently?  
3. **Observability**: Is it critical to see per-run execution history, step-level errors, and rerun failed executions?

| Tool | Best For | Not For |
|---|---|---|
| **n8n** | Complex multi-step workflows, developer-controlled, retry logic, conditional branching, third-party API calls requiring oauth tokens, scheduled jobs | Simple single-step triggers, real-time synchronous paths |
| **Zapier** | Fast third-party connector setup, business-team-managed, pre-built triggers from form/CRM/calendar tools | Workflows needing loops, advanced error handling, or secrets management |
| **Make** | Visual cross-app scenarios editable by operations team without developer help, booking/guest communication sequences | Latency-sensitive paths, complex data transformation |
| **Application backend** | Logic that must be transactional, idempotent, auditable, part of core business state, or latency-sensitive | External tool coordination |

---

## Workflow Classification

### W1 — New Lead Intake (from web form)

**Tool: Zapier**

**Justification:** The business team needs to add/change web form sources (Typeform, Jotform, Tally) without developer involvement. Zapier has native connectors for all these tools with a simple form submission → database row pattern. The logic is: receive form data → POST to Supabase Edge Function `inbound-webhook` → Edge Function validates and creates lead record. No branching or complex retry is needed because the Edge Function handles idempotency. If the form provider changes, a Zapier Zap can be updated in minutes.

**Flow:**
```
[Typeform submission] → Zapier → POST /edge/inbound-webhook → Supabase writes lead + outbox event
                                                              → Worker reads outbox → SQS → Lambda → Slack #new-leads
                                                                                             → Lambda → AI lead classification (async)
```

**What Zapier does NOT own:** The AI classification, the lead record creation, and the notification delivery. Zapier is a trusted entry point that hands off immediately.

---

### W2 — Booking Confirmation Sequence

**Tool: Make**

**Justification:** The booking confirmation sequence involves 4–6 steps (confirmation email, calendar invite, welcome pack PDF generation, pre-arrival questionnaire link, WhatsApp message 48h before arrival). The operations team needs to edit the timing and messaging of these steps quarterly. Make's visual scenario editor is accessible to a non-developer operations manager. The workflow is not latency-sensitive (all steps are async post-booking) and does not require transactional guarantees (individual step failures are retried by Make).

**Flow:**
```
[Supabase webhook: booking.confirmed] → Make webhook trigger
  → Step 1: Fetch full booking details from Supabase
  → Step 2: Generate and send confirmation email (SendGrid module)
  → Step 3: Create Google Calendar event for guest
  → Step 4: POST to /v1/copilot/draft-message for personalised welcome message
  → Step 5: Schedule WhatsApp reminder message 48h before check-in (via Twilio module)
```

---

### W3 — Missed Payment Reminder

**Tool: n8n**

**Justification:** Payment status requires polling Stripe, comparing against the invoice due date, applying conditional logic (first reminder vs. second vs. escalation), and having a clear audit trail. n8n provides per-execution history, making it easy to see "did we send reminder #2 to guest X on date Y?". The workflow needs developer-level control over the retry behaviour and the fallback when Stripe returns unexpected states.

**Flow:**
```
[n8n schedule: daily 09:00] →
  → Query Supabase: invoices WHERE status = 'sent' AND due_date < TODAY
  → For each invoice:
    → Check Stripe payment intent status
    → Branch: if still unpaid:
      → days_overdue < 3: send reminder email via SendGrid
      → days_overdue 3-7: send WhatsApp + email
      → days_overdue > 7: create internal escalation task + Slack alert to finance manager
    → Branch: if paid:
      → Update invoice status in Supabase
  → Log execution summary to Supabase ingestion_jobs table
```

---

### W4 — Failed Webhook Retry

**Tool: Application backend (SQS + Lambda DLQ handling)**

**Justification:** Webhook retry is a reliability concern, not a business logic concern. Retrying failed external webhooks belongs inside the infrastructure layer — SQS built-in retry with exponential backoff, DLQ for permanently failed messages, and CloudWatch alarms for visibility. Externalising this to an automation tool would create a dependency on that tool's uptime and introduce latency.

**Flow:**
```
SQS message delivery failure → SQS retries 3× (30s, 60s, 120s backoff) → DLQ
CloudWatch alarm: DLQ depth > 0 → SNS → Slack alert → engineer reviews DLQ messages
Engineer: replay from DLQ manually or via a Lambda "DLQ replay" function
```

---

### W5 — Internal Escalation (e.g., guest complaint, clinical concern)

**Tool: n8n**

**Justification:** Escalation flows are conditional and stateful: an escalation must be assigned to a specific person, must change state if acknowledged, and must re-escalate if not acknowledged within a time window. n8n's built-in execution history makes it possible to audit "when was this escalation acknowledged and by whom." The business logic here is complex enough that a visual no-code tool like Zapier or Make would hit its limits.

**Flow:**
```
[Trigger: POST from app when escalation_event created in Supabase] → n8n webhook
  → Fetch escalation details + guest context
  → Determine escalation level (operational / clinical / safety)
  → Level operational: Slack DM to operations manager + task in system
  → Level clinical: Slack DM to senior nurse + urgent email
  → Level safety: Immediate Slack @channel + phone call trigger via Twilio
  → Wait node: 30 minutes
  → Check: escalation acknowledged in system?
    → Yes: log acknowledgement, end
    → No: re-escalate to next level and repeat
```

---

### W6 — Sync Notion SOP Update into Vector Index

**Tool: n8n**

**Justification:** This workflow involves Notion API calls (which require OAuth token management), chunking logic decisions, calling the Python ingestion service, handling failures in individual chunk embeddings, and maintaining a sync log. n8n can manage the Notion OAuth token, handle pagination through Notion block content, and provide per-page execution history. The actual embedding work is delegated to the Python ingestion service — n8n is the orchestrator, not the processor.

**Flow:**
```
[Notion webhook: page.updated] → n8n webhook trigger
  → Validate: is this page in our known knowledge base?
  → Fetch full page content + blocks via Notion API
  → POST to Python worker: POST /jobs/sync-notion-page {page_id, content}
  → Poll job status with timeout (max 5 min)
  → On success: update knowledge.ingestion_jobs record via Supabase
  → On failure: post error to Slack #engineering-alerts
  → Log execution metrics
```

---

### W7 — Daily Management Report

**Tool: n8n (generation) + Python worker (data aggregation)**

**Justification:** The data aggregation step belongs in the Python worker (it runs complex SQL against analytics views and formats structured data). n8n orchestrates the scheduling, calls the Python endpoint, receives the structured report data, formats it, and distributes it to the right channels (Slack + email). Separation allows the report format to change (n8n edit) without touching the aggregation logic (Python).

**Flow:**
```
[n8n schedule: daily 07:00] →
  → POST to Python worker: GET /v1/analytics/daily-report?date=today
  → Receive structured JSON report
  → Format report as Slack message (using n8n's text manipulation nodes)
  → POST formatted report to Slack #management-daily
  → Generate email version → send via SendGrid to management distribution list
  → Store report record in Supabase (for audit + admin dashboard history)
```

---

### W8 — Anomaly Detection Alert

**Tool: Application backend (Python worker) + n8n for distribution**

**Justification:** Anomaly detection logic (statistical thresholds, rate-of-change comparisons) belongs in deterministic Python code, not in a visual automation tool. The Python worker runs the detection logic on a schedule; when an anomaly is detected it writes an alert record to the database and fires a webhook to n8n. n8n handles the routing (who gets notified, at what severity) and provides a visual history of alerts dispatched.

**Flow:**
```
[Python worker: nightly_analytics job] →
  → Compute KPI deltas vs 7-day rolling average
  → For each anomaly detected: INSERT into analytics.alerts table + fire outbox event
  → Outbox event → SQS → Lambda → POST to n8n webhook
  → n8n: route by anomaly type
    → utilisation drop: Slack #operations + operations manager email
    → billing gap: Slack #finance + finance manager email
    → system error pattern: Slack #engineering + PagerDuty
```

---

## Summary: Tool Responsibility Map

| Workflow | Primary Tool | Secondary |
|---|---|---|
| New lead intake | Zapier | Supabase Edge Function |
| Lead AI classification | Application backend (Python) | — |
| Booking confirmation sequence | Make | Supabase Edge Function (trigger) |
| Missed payment reminder | n8n | Stripe API, SendGrid |
| Failed webhook retry | AWS SQS + DLQ | CloudWatch alarm |
| Internal escalation | n8n | Application backend (creates record) |
| Notion SOP → vector sync | n8n (orchestration) + Python (processing) | Supabase |
| Daily management report | n8n (scheduling + distribution) + Python (aggregation) | Slack, SendGrid |
| Anomaly detection | Application backend (Python) + n8n (routing) | Slack, PagerDuty |
| Check-in/out notifications | Application backend (outbox → SQS → Lambda) | — |
| Billing reconciliation reminders | Application backend (Python worker job) | Slack, Email |
| Review request post-stay | Make | SendGrid, Typeform |

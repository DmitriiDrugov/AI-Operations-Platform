# 90-Day Product Roadmap

**Start date:** 2026-04-23  
**Goal:** Operational MVP running in production with real guests

---

## Month 1 (Days 1–30): Infrastructure and Core Data Layer

**Theme: Build the foundation so nothing needs to be undone.**

### Week 1–2
- [ ] TICKET-001: CI/CD pipeline (GitHub Actions → ECS/Vercel)
- [ ] TICKET-002: Supabase schema, auth, RLS, JWT claims hook
- [ ] Development environment setup (Docker Compose: Postgres + Redis + worker)
- [ ] `.env.example` documentation, secrets strategy implemented
- [ ] Team access to staging Supabase project

### Week 3–4
- [ ] TICKET-003: Guest profile CRUD with PII encryption
- [ ] TICKET-004: Booking lifecycle (Stay CRUD, status transitions, outbox)
- [ ] TICKET-005: Outbox worker deployed, SQS queues live, booking confirmation email working
- [ ] Basic admin app navigation shell (auth, sidebar, routing)
- [ ] First staging deployment verified end-to-end

**Month 1 milestone:** Staff can create a guest, create a booking, and receive a confirmation email.

---

## Month 2 (Days 31–60): Scheduling, Billing, and AI Foundation

**Theme: Core operational workflows running; AI copilot usable for early adopters.**

### Week 5–6
- [ ] TICKET-006: Appointment scheduling with conflict detection and Realtime updates
- [ ] TICKET-007: Package + billing signal engine, reconciliation UI
- [ ] Invoice generation and Stripe payment intent creation

### Week 7–8
- [ ] TICKET-008: AI copilot deployed (SOP lookup + guest summary)
- [ ] TICKET-009: Notion → vector ingestion pipeline live
- [ ] Initial knowledge base indexed (all SOPs, service descriptions, policies)
- [ ] Copilot panel integrated into guest profile page and schedule view
- [ ] Lead intake via Zapier (Typeform → Supabase Edge Function)
- [ ] Lead classification AI (auto-classifies new leads on creation)

**Month 2 milestone:** Staff can schedule treatments, reconcile billing at checkout, and ask the AI copilot SOP questions. Leads are auto-classified on intake.

---

## Month 3 (Days 61–90): Automation Sequences, Analytics, and Hardening

**Theme: Business team autonomy, management visibility, production readiness.**

### Week 9–10
- [ ] TICKET-010: Analytics dashboard (utilisation, revenue, upsell rate)
- [ ] n8n: Missed payment reminder workflow live
- [ ] Make: Booking confirmation sequence + post-stay follow-up live
- [ ] WhatsApp integration (Twilio BSP): appointment reminders
- [ ] Guest-facing portal MVP: view schedule, read messages, digital check-in

### Week 11–12
- [ ] Load testing: 100 concurrent users, 50 simultaneous schedule queries
- [ ] Security review: RLS audit, PII handling review, prompt injection testing
- [ ] Staff training documentation
- [ ] Operations team onboarded to Make and Zapier
- [ ] Monitoring dashboards and on-call runbook
- [ ] Production deployment with real data migration (if applicable)
- [ ] Soft launch: 1 full programme cycle with a real guest cohort

**Month 3 milestone:** Production system handling a full guest cohort. Management receives daily automated reports. Finance completes billing reconciliation in < 15 minutes per checkout.

---

## Post-90 Days (Backlog)

| Feature | Estimated Quarter |
|---|---|
| Mobile-responsive guest portal (PWA) | Q3 2026 |
| Multi-location support (multi-tenancy UI) | Q3 2026 |
| Clinical assessment module (SOAP notes, outcome tracking) | Q4 2026 |
| Revenue management: dynamic pricing recommendations | Q4 2026 |
| Guest self-service appointment rescheduling | Q3 2026 |
| Referral tracking and affiliate programme | Q4 2026 |
| LangChain Agent for full billing investigation (multi-tool) | Q3 2026 |
| Migrate pgvector to Qdrant if latency SLA exceeded | Triggered by metric |
| Native mobile app (iOS/Android) | 2027 |
| Multi-currency invoicing | Q4 2026 |
| HIPAA compliance audit and certification | 2027 (if US clinical market targeted) |

---

## Risk Triggers (Conditions That Change the Roadmap)

| Trigger | Response |
|---|---|
| pgvector p99 search latency > 500ms | Initiate ADR-004 migration path to Qdrant |
| Staff AI copilot adoption < 20% after 60 days | UX research sprint; simplify onboarding |
| Stripe webhook processing backlog > 100 messages | Lambda concurrency limit increase + SQS batching review |
| Billing dispute rate > 5% | Rules engine review; add more explicit inclusion logic |
| Notion API quota errors during ingestion | Implement request throttling + incremental batching |

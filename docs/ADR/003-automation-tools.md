# ADR-003: Three-Tool Automation Strategy (n8n + Zapier + Make)

**Date:** 2026-04-23  
**Status:** Accepted  
**Deciders:** Platform Architect, Product Analyst, Operations Lead  

---

## Context

The platform has many cross-system automation workflows ranging from simple third-party integrations (web form → database) to complex multi-step orchestrations (Notion sync, payment reminders with escalation logic). Different stakeholders need to own different workflows: developers need reliability and observability; business teams need to edit communication sequences without developer involvement.

## Decision

Use three automation tools, each for a distinct ownership and complexity tier.

| Tool | Tier | Owned By | Use For |
|---|---|---|---|
| **n8n** (self-hosted) | Complex / developer | Engineering | Multi-step, conditional, stateful workflows needing retry logic and audit history |
| **Zapier** | Simple / business | Operations team | Fast no-code third-party connectors; form-to-database, CRM triggers, calendar sync |
| **Make** | Visual / business | Operations team | Visual multi-step sequences that business teams edit; communication journeys |

## Why All Three?

The alternative is picking one tool for everything. Each single-tool option fails for at least one tier:

- **n8n only**: Business teams cannot use it independently; all workflow changes require a developer
- **Zapier only**: Cannot handle complex conditional logic, retry strategies, or long-running workflows
- **Make only**: No developer-grade observability; harder to manage secrets; slower API call performance under load

The three-tool strategy assigns each workflow to the tool that best serves its operational ownership model.

## n8n Justification

- Self-hosted: keeps credentials and workflow execution logs inside our infrastructure
- Per-execution history: critical for the Notion sync audit trail and escalation acknowledgement tracking
- Native retry policies: exponential backoff for external API calls
- Developer-friendly: workflows are stored as JSON and version-controlled in `/automations/n8n/`
- **Risk**: n8n uptime is our responsibility. Mitigated by: redundant container deployment, health monitoring, and the fact that n8n handles non-critical paths (reporting, sync) — booking confirmation is handled by Make, not n8n

## Zapier Justification

- Pre-built connectors for Typeform, Jotform, Tally, Google Sheets, Calendly reduce integration time to hours
- Business team can add a new lead source without engineering involvement
- **Risk**: Zapier outage affects lead intake. Mitigated by: all Zapier actions write to Supabase Edge Functions (idempotent endpoints), so if Zapier retries a form submission, the Edge Function deduplicates

## Make Justification

- Visual scenario editor is genuinely accessible to non-developers for editing communication timing and messaging
- Booking confirmation and follow-up sequences change frequently (seasonal offers, new programme launches)
- **Risk**: Make stores credentials externally. Mitigated by: using API keys scoped to minimum permissions; no access to clinical data

## What Stays in Application Backend

- All billing logic (transactional, auditable)
- Outbox event processing (reliability requirement: must not depend on external tool uptime)
- Anomaly detection (deterministic algorithm, not workflow logic)
- Anything that touches clinical data (regulatory boundary)

## Consequences

- Automation workflows are documented in `/automations/` with a README per tool
- n8n workflows are exported as JSON and committed to version control
- Each tool has a named owner in the team
- The automation layer is treated as a first-class integration surface with its own error budget

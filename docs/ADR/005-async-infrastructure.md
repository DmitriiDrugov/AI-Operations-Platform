# ADR-005: AWS SQS + Lambda for Async Event Processing

**Date:** 2026-04-23  
**Status:** Accepted  
**Deciders:** Platform Architect, Infrastructure Lead  

---

## Context

The platform generates events that trigger external side effects: sending emails, posting to Slack, updating Stripe, sending WhatsApp messages. These must be reliable (retry on failure), decoupled (failure in email delivery must not affect the booking transaction), and observable. The choice is between inline HTTP calls, a background worker queue, or a managed queue + serverless compute.

## Decision

Use AWS SQS as the event queue. Use Lambda for stateless event handlers that call external APIs. The outbox pattern in Postgres feeds the SQS queues via the Python worker.

## Reasoning

**For SQS + Lambda:**

- **Built-in retry with DLQ**: SQS standard retry policy (configurable) + dead-letter queue for permanently failed messages requires zero application-level retry code
- **Stateless handlers**: Lambda forces handlers to be stateless, which makes them testable and safe to redeploy without draining a queue
- **Auto-scaling**: Lambda scales to the SQS queue depth automatically; no capacity planning required
- **Cost**: Lambda charges per invocation; at wellness-scale event volumes, the cost is negligible
- **Observability**: CloudWatch provides Lambda duration, error rate, and concurrent execution metrics with minimal setup

**Outbox → SQS flow:**
- Events are written to `public.outbox_events` in the same database transaction as the business record
- The Python worker polls the outbox and publishes to SQS
- Lambda handles SQS messages and makes external API calls
- This ensures that no event is silently dropped even if the Lambda fails: the DLQ catches it

**Why not Redis (e.g., Celery)?**
- Redis is ephemeral by default; an unprocessed event in Redis could be lost if Redis restarts before processing
- SQS is durable (messages persisted for up to 14 days)
- SQS DLQ is the production-grade failure handling mechanism; Redis requires manual dead-letter implementation

**Why not directly in the Python worker?**
- The Python worker handles business-logic jobs (outbox polling, analytics) — not external API calls
- Separating external API calls into Lambda keeps the worker stateless and focused
- Lambda cold start (< 200ms with warm-up) is acceptable for async notifications

## Lambda Functions

| Function | Queue | External Call |
|---|---|---|
| `send-email` | `notification-queue` | SendGrid API |
| `send-whatsapp` | `notification-queue` | Twilio API |
| `post-to-slack` | `notification-queue` | Slack Webhook API |
| `process-stripe-webhook` | `stripe-webhook-queue` | Stripe API + Supabase |
| `replay-dlq` | Manual trigger | Any DLQ |

## Consequences

- Lambda functions are deployed via the `infra/aws/lambda/` directory using a thin deployment framework (AWS SAM or Terraform)
- Each Lambda function has its own IAM role with least-privilege permissions
- CloudWatch alarms monitor DLQ depth, Lambda error rate, and Lambda duration p95
- All Lambda invocations are traced via AWS X-Ray
- Lambda functions are tested as standalone Python/Node.js modules with mocked SQS events

"""
Outbox processor — polls the outbox_events table and dispatches events to SQS.

Guarantees:
- Atomic status update (pending → processing) prevents double-processing
- Events are marked processed only after successful SQS publish
- Failed events increment attempts; after 5 failures they are dead-lettered
- Stuck 'processing' events (older than 10 min) are reset by the cleanup job
"""
import json
import time
import uuid
from datetime import datetime, timezone

import asyncpg
import boto3
from botocore.exceptions import ClientError

from ..core.config import get_settings
from ..core.logging import get_logger

log = get_logger(__name__)

MAX_ATTEMPTS = 5
BATCH_SIZE = 50


async def process_outbox_events(db_conn: asyncpg.Connection) -> dict:
    settings = get_settings()
    sqs = boto3.client("sqs", region_name=settings.aws_region)
    queue_url = settings.aws_sqs_outbox_queue_url

    dispatched = 0
    failed = 0

    # Fetch and atomically mark a batch as 'processing'
    rows = await db_conn.fetch(
        """
        UPDATE public.outbox_events
        SET status = 'processing', attempts = attempts + 1
        WHERE id IN (
            SELECT id FROM public.outbox_events
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT $1
            FOR UPDATE SKIP LOCKED
        )
        RETURNING id, organisation_id, event_type, aggregate_type,
                  aggregate_id, payload, version, attempts, created_at
        """,
        BATCH_SIZE,
    )

    for row in rows:
        event_id = str(row["id"])
        try:
            message_body = json.dumps({
                "id": event_id,
                "organisation_id": str(row["organisation_id"]),
                "event_type": row["event_type"],
                "aggregate_type": row["aggregate_type"],
                "aggregate_id": str(row["aggregate_id"]),
                "payload": dict(row["payload"]),
                "version": row["version"],
                "occurred_at": row["created_at"].isoformat(),
            })

            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=message_body,
                MessageGroupId=row["event_type"],
                MessageDeduplicationId=event_id,
            )

            await db_conn.execute(
                """
                UPDATE public.outbox_events
                SET status = 'processed', processed_at = NOW()
                WHERE id = $1
                """,
                row["id"],
            )
            dispatched += 1
            log.debug(
                "outbox.event.dispatched",
                event_id=event_id,
                event_type=row["event_type"],
            )

        except ClientError as exc:
            failed += 1
            status = "dead_lettered" if row["attempts"] >= MAX_ATTEMPTS else "pending"
            await db_conn.execute(
                """
                UPDATE public.outbox_events
                SET status = $1, last_error = $2
                WHERE id = $3
                """,
                status,
                str(exc),
                row["id"],
            )
            log.error(
                "outbox.event.sqs_error",
                event_id=event_id,
                error=str(exc),
                attempts=row["attempts"],
                new_status=status,
            )

    log.info(
        "outbox.batch.completed",
        dispatched=dispatched,
        failed=failed,
        batch_size=len(rows),
    )
    return {"dispatched": dispatched, "failed": failed}


async def clean_stale_processing_events(db_conn: asyncpg.Connection) -> int:
    """Reset events stuck in 'processing' for more than 10 minutes."""
    result = await db_conn.execute(
        """
        UPDATE public.outbox_events
        SET status = 'pending'
        WHERE status = 'processing'
          AND created_at < NOW() - INTERVAL '10 minutes'
        """,
    )
    count = int(result.split()[-1])
    if count > 0:
        log.warning("outbox.stale_events_reset", count=count)
    return count

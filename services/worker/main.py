"""
Worker Service — ARQ-based background job runner.

Jobs are registered here and triggered either:
- On a schedule (cron-like via ARQ)
- On demand (enqueued by the application layer or n8n)
"""
import asyncio
from typing import Any

import asyncpg
from arq import create_pool
from arq.connections import RedisSettings

from .core.config import get_settings
from .core.logging import configure_logging, get_logger
from .jobs.notion_ingestion import sync_notion_page
from .jobs.outbox_processor import clean_stale_processing_events, process_outbox_events

settings = get_settings()
configure_logging(settings.log_level, settings.is_production)
log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Job handlers (thin wrappers; logic lives in jobs/)
# ---------------------------------------------------------------------------

async def job_process_outbox(ctx: dict[str, Any]) -> dict:
    async with asyncpg.connect(settings.database_url) as conn:
        return await process_outbox_events(conn)


async def job_sync_notion_page(
    ctx: dict[str, Any],
    page_id: str,
    organisation_id: str,
) -> dict:
    async with asyncpg.connect(settings.database_url) as conn:
        return await sync_notion_page(conn, page_id, organisation_id)


async def job_clean_stale_processing(ctx: dict[str, Any]) -> int:
    async with asyncpg.connect(settings.database_url) as conn:
        return await clean_stale_processing_events(conn)


async def job_nightly_analytics(ctx: dict[str, Any]) -> dict:
    log.info("nightly_analytics.started")
    async with asyncpg.connect(settings.database_url) as conn:
        await conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.daily_summary")
    log.info("nightly_analytics.completed")
    return {"status": "completed"}


async def job_billing_reminders(ctx: dict[str, Any]) -> dict:
    """Alert finance team about stays checking out today with pending billable events."""
    log.info("billing_reminders.started")
    async with asyncpg.connect(settings.database_url) as conn:
        rows = await conn.fetch(
            """
            SELECT s.id AS stay_id, g.first_name, g.last_name,
                   COUNT(be.id) AS pending_events
            FROM bookings.stays s
            JOIN guests.guests g ON g.id = s.guest_id
            JOIN billing.billable_events be ON be.stay_id = s.id
              AND be.approval_status = 'pending'
            WHERE s.check_out_date = CURRENT_DATE
              AND s.status = 'checked_in'
            GROUP BY s.id, g.first_name, g.last_name
            HAVING COUNT(be.id) > 0
            """,
        )
        count = len(rows)
        if count > 0:
            log.info("billing_reminders.sent", stays_with_pending=count)
        return {"stays_with_pending_billing": count}


# ---------------------------------------------------------------------------
# ARQ WorkerSettings — registered jobs and cron schedule
# ---------------------------------------------------------------------------

class WorkerConfig:
    """ARQ worker configuration class (consumed by `arq` CLI)."""
    functions = [
        job_process_outbox,
        job_sync_notion_page,
        job_clean_stale_processing,
        job_nightly_analytics,
        job_billing_reminders,
    ]

    # Cron schedule (UTC)
    cron_jobs = [
        # Process outbox every 5 seconds
        {"coroutine": job_process_outbox, "second": {0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}},
        # Clean stale processing events every hour
        {"coroutine": job_clean_stale_processing, "minute": 0},
        # Nightly analytics aggregation
        {"coroutine": job_nightly_analytics, "hour": 2, "minute": 0},
        # Billing reminders at 08:00 UTC
        {"coroutine": job_billing_reminders, "hour": 8, "minute": 0},
    ]

    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 50
    job_timeout = 300
    keep_result = 86400  # 24 hours
    max_tries = 3

    @classmethod
    async def on_startup(cls, ctx: dict[str, Any]) -> None:
        log.info("worker.startup", environment=settings.app_env)

    @classmethod
    async def on_shutdown(cls, ctx: dict[str, Any]) -> None:
        log.info("worker.shutdown")

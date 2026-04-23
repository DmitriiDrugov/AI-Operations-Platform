"""
AI Core Service — FastAPI application entry point.

Exposes AI endpoints consumed by Supabase Edge Functions and the admin app.
"""
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import anthropic
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .api.routes import copilot, knowledge, leads
from .core.config import get_settings
from .core.logging import configure_logging, get_logger
from .models.responses import HealthResponse, ReadyResponse

settings = get_settings()
configure_logging(log_level=settings.log_level, is_production=settings.is_production)
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    log.info("ai_core.starting", environment=settings.app_env)
    yield
    log.info("ai_core.shutdown")


app = FastAPI(
    title="AI Operations Platform — AI Core Service",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
    lifespan=lifespan,
)

# CORS: only allow requests from the admin app and edge functions
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.supabase_url,
        # admin app origins are added via env var in production
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Trace-Id"],
)


@app.middleware("http")
async def add_trace_id_and_timing(request: Request, call_next: Any) -> Response:
    import uuid
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    request.state.trace_id = trace_id

    t_start = time.monotonic()
    response = await call_next(request)
    duration_ms = int((time.monotonic() - t_start) * 1000)

    response.headers["X-Trace-Id"] = trace_id
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    return response


# Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Routers
app.include_router(copilot.router, prefix="/v1")
app.include_router(knowledge.router, prefix="/v1")
app.include_router(leads.router, prefix="/v1")


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="0.1.0",
        environment=settings.app_env,
    )


@app.get("/ready", response_model=ReadyResponse, tags=["Health"])
async def ready() -> ReadyResponse:
    checks: dict[str, bool] = {}

    # Check database connectivity
    try:
        import asyncpg
        conn = await asyncpg.connect(settings.database_url, timeout=3)
        await conn.execute("SELECT 1")
        await conn.close()
        checks["database"] = True
    except Exception:
        checks["database"] = False

    # Check Claude API connectivity (lightweight)
    try:
        client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )
        await client.models.list()
        checks["claude_api"] = True
    except Exception:
        checks["claude_api"] = False

    all_ok = all(checks.values())
    return ReadyResponse(
        status="ok" if all_ok else "degraded",
        checks=checks,
    )

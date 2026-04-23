import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from ...core.database import get_db_session, set_session_context
from ...core.logging import get_logger
from ...models.requests import CopilotQueryRequest, DraftMessageRequest, SummariseGuestRequest
from ...models.responses import CopilotQueryResponse, DraftMessageResponse, GuestSummaryResponse
from ...services.copilot_service import CopilotService
from ..middleware.auth import RequestContext, get_request_context

router = APIRouter(prefix="/copilot", tags=["AI Copilot"])
log = get_logger(__name__)


@router.post("/query", response_model=CopilotQueryResponse)
async def copilot_query(
    request: CopilotQueryRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> CopilotQueryResponse:
    """Staff AI assistant query with RAG retrieval."""
    # Enforce that the request organisation matches the authenticated user's org
    if str(request.organisation_id) != ctx.organisation_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organisation mismatch",
        )

    try:
        async with get_db_session() as session:
            conn = await session.connection()
            raw_conn = await conn.get_raw_connection()
            await set_session_context(
                raw_conn,
                organisation_id=ctx.organisation_id,
                user_id=ctx.user_id,
                role=ctx.role,
                trace_id=ctx.trace_id,
            )
            service = CopilotService(raw_conn)
            return await service.query(request)
    except Exception as exc:
        log.error("copilot.query.error", error=str(exc), trace_id=ctx.trace_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI service temporarily unavailable",
        ) from exc


@router.post("/summarise", response_model=GuestSummaryResponse)
async def summarise_guest(
    request: SummariseGuestRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> GuestSummaryResponse:
    """Generate a structured AI summary of a guest's history."""
    if str(request.organisation_id) != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organisation mismatch")

    if request.include_clinical and ctx.role not in {
        "org_admin", "manager", "nurse", "practitioner"
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinical summaries require clinical staff role",
        )

    try:
        async with get_db_session() as session:
            conn = await session.connection()
            raw_conn = await conn.get_raw_connection()
            await set_session_context(raw_conn, ctx.organisation_id, ctx.user_id, ctx.role, ctx.trace_id)
            service = CopilotService(raw_conn)
            # Delegate to copilot with GUEST_SUMMARY interaction type
            from ...models.requests import CopilotContext, InteractionType
            query_req = CopilotQueryRequest(
                query=f"Summarise this guest's history, current stay status, and any important notes.",
                context=CopilotContext(
                    guest_id=request.guest_id,
                    interaction_type=InteractionType.GUEST_SUMMARY,
                ),
                organisation_id=request.organisation_id,
                user_id=request.user_id,
            )
            copilot_response = await service.query(query_req)
            return GuestSummaryResponse(
                guest_name="",  # Populated by copilot context fetch
                summary=copilot_response.response_text,
                key_notes=[],
                upcoming_appointments=[],
                package_status=None,
                interaction_id=copilot_response.interaction_id,
                model=copilot_response.model,
                latency_ms=copilot_response.latency_ms,
            )
    except HTTPException:
        raise
    except Exception as exc:
        log.error("copilot.summarise.error", error=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) from exc

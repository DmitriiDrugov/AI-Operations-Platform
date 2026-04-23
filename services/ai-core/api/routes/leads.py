from fastapi import APIRouter, Depends, HTTPException, status

from ...core.database import get_db_session, set_session_context
from ...models.requests import ClassifyLeadRequest
from ...models.responses import ClassifyLeadResponse
from ...services.lead_service import LeadService
from ..middleware.auth import RequestContext, get_request_context

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.post("/classify", response_model=ClassifyLeadResponse)
async def classify_lead(
    request: ClassifyLeadRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> ClassifyLeadResponse:
    """AI classification of a lead inquiry."""
    if str(request.organisation_id) != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organisation mismatch")

    async with get_db_session() as session:
        conn = await session.connection()
        raw_conn = await conn.get_raw_connection()
        await set_session_context(raw_conn, ctx.organisation_id, ctx.user_id, ctx.role, ctx.trace_id)
        service = LeadService(raw_conn)
        return await service.classify_lead(request)
